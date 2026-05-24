"""
Generate analysis prompts for a given article ID.

Returns the exact prompts that would be sent to LLMs for:
1. Prefilter (content classification via Mistral)
2. Classifier (sentiment analysis via Anthropic Claude)
"""

import argparse
import json
import sys
from pathlib import Path

import polars as pl

# Add src to path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from store.parquet import read_articles
from store.db import get_db_connection


def prepare_content_for_prompt(text: str) -> str:
    """
    Prepare text content for embedding in a JSON-like prompt format.
    - Strips/normalizes newlines (replaces with spaces)
    - Escapes double quotes
    """
    # Replace various newline types with single space
    cleaned = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    # Collapse multiple spaces
    while "  " in cleaned:
        cleaned = cleaned.replace("  ", " ")
    # Escape double quotes for JSON compatibility
    cleaned = cleaned.replace('"', '\\"')
    return cleaned.strip()


# Constants from prefilter_content.py
PREFILTER_MAX_LENGTH = 4000

# Constants from sentiment_analyzer.py
CLASSIFIER_MAX_LENGTH = 8000

# Separator for head/tail truncation
SNIP_SEPARATOR = "\n\n[… middle section omitted …]\n\n"

# Prefilter prompt template (v4.1 - Developer Experience + Research Findings)
PREFILTER_PROMPT_TEMPLATE = """Act as a strict Content Filter for a project tracking developer sentiment about AI coding tools.

CRITICAL: We ONLY want articles where developers share their PERSONAL EXPERIENCE or SUBSTANTIVE OPINION about using AI for coding, OR research with CLEAR FINDINGS about AI coding effectiveness. Product announcements, tutorials, and general AI news should be EXCLUDED.

## Categories

### AI_DISCOURSE (Include in Verdict)
First-person developer experience, substantive analysis with clear opinion, OR research with clear findings about AI coding tools.

MUST contain at least ONE of:
- First-person experience: "I used...", "We built...", "After 3 months with...", "My team switched to..."
- Critical evaluation with verdict: "X is better than Y because...", "Why X fails at..."
- Success/failure stories with lessons learned
- Productivity claims backed by personal anecdotes
- Workflow comparisons with personal recommendation
- **Research with clear findings**: Studies presenting empirical data about AI coding tool effectiveness, skill development, or productivity with explicit conclusions

Examples that QUALIFY:
- "I Replaced My Junior Dev With Cursor - Here's What Happened" (first-person experience)
- "Copilot vs Cursor: After Testing Both, Here's My Verdict" (comparative opinion)
- "Why I Stopped Using AI Coding Assistants" (personal decision with reasoning)
- "How Claude Helped Us Ship 2x Faster" (team experience with outcome)
- "AI Code Review Is Overrated - A Senior Dev's Perspective" (opinion piece)
- "How AI assistance impacts the formation of coding skills" (research with clear findings: 17% skill reduction)

### AI_NEWS (Exclude - No Developer Opinion)
Announcements, launches, or factual reporting WITHOUT author experience/opinion.

Characteristics:
- Press releases, company blog posts announcing features
- "Introducing X", "Announcing Y", "Now available: Z"
- Benchmark results presented without interpretation
- Funding/acquisition/hiring news
- Feature changelogs without usage commentary

Examples:
- "Windsurf Codemaps: Understand Code Before You Vibe It" (product marketing)
- "Cursor 2.0 Released with New Agent Features" (feature announcement)
- "GitHub Copilot Now Supports Multi-File Editing" (changelog)
- "Anthropic Raises $10B Series D" (funding news)

### AI_OTHER (Exclude - Wrong Topic)
AI/ML content NOT specifically about coding workflows with AI tools, OR methodology-focused academic content without clear findings.

Includes:
- Courses, tutorials, books, educational guides (even about LLMs/coding)
- Pure academic research (methodology-focused without clear findings about AI coding utility)
- Non-coding AI: audio, image, video generation, robotics
- AGI philosophy, AI ethics, job displacement debates
- General model capabilities without coding focus
- AI in healthcare/finance/legal/other industries

**NOTE**: Research WITH clear findings about AI coding effectiveness DOES qualify as AI_DISCOURSE.

Examples:
- "Neural Networks: Zero to Hero" (educational course)
- "Our New SAM Audio Model Transforms Audio Editing" (audio AI, not coding)
- "Will AI Replace Programmers?" (speculation, not experience)
- "Attention Is All You Need" (pure methodology paper, no coding tool findings)
- "Introduction to Prompt Engineering" (tutorial)
- "A Survey of LLM Architectures" (survey paper, no actionable findings)

### NOISE (Exclude - Not AI)
Content unrelated to AI/ML entirely.

Examples:
- "Postgres 17 Released" (database, no AI)
- "The State of JavaScript 2025" (web dev, no AI)

## Decision Rules (Apply in Order)

1. If it's a PRODUCT ANNOUNCEMENT or COMPANY BLOG POST (without findings) → AI_NEWS (not AI_DISCOURSE)
2. If it's EDUCATIONAL (course, tutorial, book, guide) → AI_OTHER (not AI_DISCOURSE)
3. If AI is mentioned but NOT about coding/development → AI_OTHER
4. If it's RESEARCH WITH CLEAR FINDINGS about AI coding utility → AI_DISCOURSE (even if company blog)
5. AI_DISCOURSE requires AUTHOR OPINION, PERSONAL EXPERIENCE, or EMPIRICAL FINDINGS - topic relevance alone is NOT enough
6. When uncertain between AI_DISCOURSE and AI_NEWS → choose AI_NEWS (be conservative)

Article:
{{
  "title": "{title}",
  "content": "{content}"
}}

Return valid JSON only:
{{
  "category": "AI_DISCOURSE" | "AI_NEWS" | "AI_OTHER" | "NOISE",
  "confidence": 0.0-1.0,
  "reasoning": "<20 words max. Why this category?>"
}}"""

# Classifier prompts (from sentiment_analyzer.py) - split into system and user
# Classifier System Prompt (v4.1 - Research Findings Support)
CLASSIFIER_SYSTEM_PROMPT = """Act as a Cynical Principal Engineer analyzing developer discourse about AI coding tools and workflows.

Your task: Extract the author's sentiment about AI coding tools from this article. If the article lacks developer opinion/experience/findings, REJECT it.

## REJECTION CHECK (Do First)

REJECT the article if ANY of these apply:
- Product announcement without author experience/opinion/findings
- Tutorial, course, book, or educational content
- Pure methodology research (no clear findings about AI coding effectiveness)
- AI news without developer perspective or empirical data
- Not about coding/development workflows

DO NOT REJECT if:
- Research presents CLEAR FINDINGS about AI coding tool effectiveness (e.g., "17% lower scores", "2x productivity")
- Article has explicit conclusions about whether AI helps or hinders coding

If rejecting, return: {"reject": true, "reason": "<why this isn't developer discourse>"}

## If NOT Rejecting, Analyze Sentiment

### Utility (Is it useful NOW?) - 5-tier scale:
- `magic`: Game-changer. "Can't imagine going back", "10x productivity"
- `tool`: Net positive with caveats. "Saves time but needs oversight"
- `mixed`: Genuinely balanced. "Great for X, terrible for Y"
- `toil`: Net negative. "Spent more time fixing than it saved"
- `hazard`: Actively harmful. "Broke production", "Created tech debt"

### Trajectory (Where is it heading?) - 3-tier scale:
- `optimistic`: "Each version better", "Limitations are temporary"
- `uncertain`: "Too early to tell", "Jury's still out"
- `pessimistic`: "Fundamental limits", "Same bugs for months"

### Topic (What aspect of AI coding?):
- `productivity`: Speed, efficiency, shipping faster, time saved
- `quality`: Correctness, bugs, hallucinations, reliability, trust
- `workflow`: Integration, context, ergonomics, learning curve
- `evaluation`: Tool comparisons, recommendations, adoption decisions

## Signal Words (require non-neutral classification):
NEGATIVE: rejected, failed, broken, frustrat, disappoint, skeptic, waste, useless
POSITIVE: love, excellent, breakthrough, productive, game-changer, amazing, 10x

## Decision Examples:

| Article                                                 | Utility | Trajectory  | Topic        |
| ------------------------------------------------------- | ------- | ----------- | ------------ |
| "Cursor ruined my workflow"                             | toil    | pessimistic | workflow     |
| "Shipped 2x faster with Claude"                         | tool    | optimistic  | productivity |
| "AI code review catches real bugs"                      | tool    | optimistic  | quality      |
| "Copilot vs Cursor: my verdict"                         | tool    | uncertain   | evaluation   |
| "AI hallucinations are a dealbreaker"                   | hazard  | pessimistic | quality      |
| "Study: AI assistance reduces skill mastery by 17%"     | mixed   | uncertain   | quality      |

## Summary Guidelines:
- Express a VERDICT, not a description
- Good: "Claude excels at refactoring but hallucinates API details"
- Bad: "Article discusses AI coding tools" (too vague)

Return valid JSON only:
```json
{
  "utility": "magic" | "tool" | "mixed" | "toil" | "hazard",
  "trajectory": "optimistic" | "uncertain" | "pessimistic",
  "topic": "productivity" | "quality" | "workflow" | "evaluation",
  "summary": "<max 25 words: blunt verdict>",
  "quotes": ["<relevant quote 1>", "<relevant quote 2>"]
}
```"""


CLASSIFIER_USER_PROMPT_TEMPLATE = """Title: "{title}"
Content: "{content}"
"""


def truncate_text(text: str, max_length: int) -> str:
    """Truncate text to max_length, trying to break at word boundaries."""
    if len(text) <= max_length:
        return text

    # Try to break at a space near the limit
    truncated = text[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.8:  # Only break at space if reasonable
        truncated = truncated[:last_space]

    return truncated + "..."


def truncate_head_tail(text: str, max_length: int, head_ratio: float = 0.6) -> str:
    """
    Truncate text using head/tail strategy for prefilter.

    Keeps the opening (60%) and closing (40%) portions of the text,
    replacing the middle with a separator. This preserves context from
    both the introduction and conclusion of articles.

    Args:
        text: Full article text
        max_length: Maximum character count
        head_ratio: Portion for opening (default 60%)

    Returns:
        Truncated text with middle replaced by separator
    """
    if len(text) <= max_length:
        return text

    separator = SNIP_SEPARATOR
    available = max_length - len(separator)
    head_len = int(available * head_ratio)
    tail_len = available - head_len

    # Extract head and tail
    head = text[:head_len]
    tail = text[-tail_len:]

    # Adjust head to word boundary
    head_space = head.rfind(" ")
    if head_space > head_len * 0.8:
        head = head[:head_space]

    # Adjust tail to word boundary
    tail_space = tail.find(" ")
    if 0 < tail_space < tail_len * 0.2:
        tail = tail[tail_space + 1 :]

    return head + separator + tail


def get_article_data(article_id: int) -> dict | None:
    """Get article title, text, and groq metrics from database and parquet."""
    conn = None
    try:
        # Get title and metrics from database
        conn = get_db_connection()
        cursor = conn.cursor()

        # First check if groq_metrics_json column exists
        cursor.execute("PRAGMA table_info(urls)")
        columns = [row[1] for row in cursor.fetchall()]
        has_groq_metrics = "groq_metrics_json" in columns

        # Build query based on available columns
        if has_groq_metrics:
            cursor.execute(
                "SELECT hn_title, groq_metrics_json FROM urls WHERE id = ?",
                (article_id,),
            )
        else:
            cursor.execute(
                "SELECT hn_title FROM urls WHERE id = ?",
                (article_id,),
            )

        row = cursor.fetchone()
        if not row:
            return None
        title = row[0] or "Untitled"
        groq_metrics_json = row[1] if has_groq_metrics else None

        # Get text from parquet
        data_dir = current_dir.parent / "data" / "articles"
        text = ""

        if data_dir.exists() and list(data_dir.glob("articles_*.parquet")):
            try:
                lf = read_articles(shard_dir=data_dir)
                result = lf.filter(pl.col("url_id") == article_id).collect()

                if result.height > 0:
                    text = result.row(0, named=True).get("text", "")
            except Exception:
                pass

        # Parse groq_metrics if present
        groq_metrics = None
        if groq_metrics_json:
            try:
                groq_metrics = json.loads(groq_metrics_json)
            except json.JSONDecodeError:
                pass

        return {
            "title": title,
            "text": text,
            "groq_metrics": groq_metrics,
            "text_missing": len(text) == 0,
        }

    except Exception as e:
        print(f"Exception in get_article_data: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        return None
    finally:
        if conn:
            conn.close()


def generate_prompts(article_id: int) -> dict:
    """Generate prefilter and classifier prompts for an article."""
    data = get_article_data(article_id)

    if not data:
        return {"error": "Article not found"}

    title = data["title"]
    text = data["text"]

    # Prepare title (escape quotes)
    prepared_title = title.replace('"', '\\"') if title else "Untitled"

    # Generate prompts (show placeholders if text missing)
    if text:
        prefilter_text = truncate_head_tail(text, PREFILTER_MAX_LENGTH)
        prefilter_content = prepare_content_for_prompt(prefilter_text)

        classifier_text = truncate_head_tail(
            text, CLASSIFIER_MAX_LENGTH, head_ratio=0.4
        )
        classifier_content = prepare_content_for_prompt(classifier_text)
    else:
        prefilter_content = (
            "[Article text not yet scraped. Run scraper to populate content.]"
        )
        classifier_content = (
            "[Article text not yet scraped. Run scraper to populate content.]"
        )

    prefilter_prompt = PREFILTER_PROMPT_TEMPLATE.format(
        title=prepared_title,
        content=prefilter_content,
    )

    classifier_user_prompt = CLASSIFIER_USER_PROMPT_TEMPLATE.format(
        title=prepared_title,
        content=classifier_content,
    )

    return {
        "prefilter": {
            "model": "llama-3.1-8b-instant",
            "prompt": prefilter_prompt,
            "truncation_limit": PREFILTER_MAX_LENGTH,
            "actual_length": len(prefilter_content),
        },
        "classifier": {
            "model": "openai/gpt-oss-20b",
            "system_prompt": CLASSIFIER_SYSTEM_PROMPT,
            "user_prompt": classifier_user_prompt,
            "truncation_limit": CLASSIFIER_MAX_LENGTH,
            "actual_length": len(classifier_content),
        },
        "groq_metrics": data.get("groq_metrics"),
        "text_missing": data.get("text_missing", False),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, required=True, help="Article ID (url_id)")
    args = parser.parse_args()

    result = generate_prompts(args.id)
    print(json.dumps(result, default=str))
