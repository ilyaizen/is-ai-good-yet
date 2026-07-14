# Sentiment Analysis Prompt (v4.1 - Research Findings Support)

Updated: 2026-01-30

This prompt is used by Phase 4 of the pipeline. It analyzes developer discourse about AI coding tools with a simplified 5-tier utility scale, explicit rejection capability, and support for research articles with clear findings.

## Key Changes in v4.1

1. **Research Findings Accepted**: Research with clear findings about AI coding tools is now analyzed (not rejected)
2. **Refined Rejection**: Only reject pure methodology papers, not studies with actionable conclusions
3. **Topic instead of Themes**: Replaced `subtopic` + `primary_theme` + `secondary_theme` with single `topic` field
4. **Equal Weighting**: 50/50 utility/trajectory weighting

## Truncation Strategy

Articles are truncated to fit within the 8,000 character limit using a **head + tail** approach:

- **Opening (40%)**: Captured from the beginning to preserve introduction and thesis.
- **Closing (60%)**: Captured from the end to preserve conclusions and final verdicts.
- **Separator**: `[… middle section omitted …]` is used between the head and tail.

## Prompt

### System Prompt

````text
Act as a Cynical Principal Engineer analyzing developer discourse about AI coding tools and workflows.

Your task: Extract the author's sentiment about AI coding tools from this article. If the article lacks developer opinion/experience, REJECT it.

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

| Article                                             | Utility | Trajectory  | Topic        |
| --------------------------------------------------- | ------- | ----------- | ------------ |
| "Cursor ruined my workflow"                         | toil    | pessimistic | workflow     |
| "Shipped 2x faster with Claude"                     | tool    | optimistic  | productivity |
| "AI code review catches real bugs"                  | tool    | optimistic  | quality      |
| "Copilot vs Cursor: my verdict"                     | tool    | uncertain   | evaluation   |
| "AI hallucinations are a dealbreaker"               | hazard  | pessimistic | quality      |
| "Study: AI assistance reduces skill mastery by 17%" | mixed   | uncertain   | quality      |

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
````

````

### User Prompt

```text
Title: "{title}"
Content: "{content}"
````

## Score Derivation

```python
UTILITY_SCORES = {
    "magic": +2.0,   # Game-changer
    "tool": +1.0,    # Net positive
    "mixed": 0.0,    # Balanced
    "toil": -1.0,    # Net negative
    "hazard": -2.0,  # Harmful
}

TRAJECTORY_SCORES = {
    "optimistic": +2.0,
    "uncertain": 0.0,
    "pessimistic": -2.0,
}

# Equal weighting (50/50)
score = (utility_score * 0.5) + (trajectory_score * 0.5)
```

### Score Examples

| Utility | Trajectory  | Score |
| :------ | :---------- | :---- |
| magic   | optimistic  | +2.00 |
| tool    | optimistic  | +1.50 |
| tool    | uncertain   | +0.50 |
| mixed   | uncertain   | 0.00  |
| toil    | uncertain   | -0.50 |
| toil    | pessimistic | -1.50 |
| hazard  | pessimistic | -2.00 |

## Topic Values

| Topic          | What it captures                                      |
| :------------- | :---------------------------------------------------- |
| `productivity` | Speed, efficiency, shipping faster, time saved        |
| `quality`      | Correctness, bugs, hallucinations, reliability, trust |
| `workflow`     | Integration, context, ergonomics, learning curve      |
| `evaluation`   | Tool comparisons, recommendations, adoption decisions |
