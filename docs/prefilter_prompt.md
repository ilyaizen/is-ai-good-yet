# Prefilter Content Analysis Prompt (v4.2 - Enhanced Research Handling & Strictness)

Updated: 2026-04-19

This prompt is used by Phase 3 of the pipeline to classify scraped article content into categories. It filters for articles where developers share **personal experience or substantive opinion** about AI coding tools, OR **research with clear findings** about AI's impact on coding. Excludes product announcements, tutorials, and general AI news.

## Key Changes in v4.2

1. **Strict Research Handling**: Academic/research articles must have EXPLICIT findings about AI coding utility to qualify as AI_DISCOURSE
2. **Methodology-Only Excluded**: Research that is purely methodological or theoretical without clear utility findings is now AI_OTHER
3. **Double Negative Logic**: Added "NOT...UNLESS" structure for clarity
4. **Prioritize Experience**: If article has BOTH research + developer experience, prioritize the experience
5. **Conservative Threshold**: Lowered confidence threshold for "Substantive Analysis" from 0.6 to 0.55

## Key Changes in v4.1 (Retained from v4.1)

1. **Research with Findings Included**: Research articles with clear conclusions about AI coding tools now qualify as AI_DISCOURSE
2. **First-person OR Clear Verdict**: Requires personal experience OR substantive analysis with clear opinion/findings
3. **Explicit Decision Rules**: Priority-ordered rules to handle edge cases
4. **Conservative Bias**: When uncertain between AI_DISCOURSE and AI_NEWS, choose AI_NEWS
5. **Better Examples**: Includes research articles with findings (Anthropic skills study)

## Truncation Strategy

Articles are truncated to fit within the 4,000 character limit using a **head + tail** approach:

- **Opening (60%)**: Captured from the beginning to preserve introduction and thesis.
- **Closing (40%)**: Captured from the end to preserve conclusions and final verdicts.
- **Separator**: `[… middle section omitted …]` is used between the head and tail.

## Prompt

```text
Act as a strict Content Filter for a project tracking developer sentiment about AI coding tools.

CRITICAL: We ONLY want articles where developers share their PERSONAL EXPERIENCE or SUBSTANTIVE OPINION about using AI for coding. Product announcements, tutorials, and general AI news should be EXCLUDED.

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

## Output Validation Rules (0% Tolerance)

If the article is ANY of the following, RETURN AI_DISCOURSE REGARDLESS of other factors:
- ❌ First-person developer experience ("I used X...", "My team...", "We tried...")
- ❌ Comparative review with clear verdict ("X vs Y: Here's What I Think")
- ❌ Success/failure story with lessons learned (even if company blog)
- ❌ Research with clear findings about AI coding utility (e.g., "X improved productivity by Y%")

If the article is ANY of the following, RETURN AI_OTHER REGARDLESS of other factors:
- ❌ Pure tutorial/how-to guide (focus on teaching, not evaluating)
- ❌ Methodology-only research (no clear findings/conclusions about utility)
- ❌ General AI news without developer perspective
- ❌ Non-coding AI (audio, image, video, robotics)

## Edge Case Priority (Order of Operations)

If an article has multiple characteristics:

1. If FIRST-PERSON DEVELOPER EXPERIENCE → AI_DISCOURSE (even if company blog or research included)
2. If RESEARCH WITH CLEAR FINDINGS → AI_DISCOURSE (even if company blog)
3. If PURE TUTORIAL/HOW-TO → AI_OTHER (even if AI coding tools)
4. If METHODOLOGY-ONLY RESEARCH → AI_OTHER (no findings on utility)
5. If PRODUCT ANNOUNCEMENT (no findings) → AI_NEWS
6. Otherwise, follow general rules

## Confidence Score Meaning

- 0.8-1.0: Strong signal detected (clear first-person experience or strong findings)
- 0.6-0.79: Substantive analysis with clear opinion but less personal
- 0.5-0.59: Borderline case with some indicators (use conservative rule)
- 0.0-0.49: Weak signal or ambiguous (default to AI_OTHER or AI_NEWS)

## Output Validation Rules (0% Tolerance)

For AI_DISCOURSE:
- MUST contain author opinion, personal experience, OR empirical findings
- Topic relevance alone is NOT enough
- If unsure, choose AI_NEWS

For AI_NEWS:
- MUST NOT contain author opinion or findings (only factual reporting)
- If any personal experience detected, switch to AI_DISCOURSE

For AI_OTHER:
- MUST NOT have author opinion/experience (focus on teaching or methodology)
- If any personal evaluation detected, switch to AI_DISCOURSE

For NOISE:
- Must be completely unrelated to AI/ML

Example: "We Switched to Cursor - Productivity Doubled" → AI_DISCOURSE (first-person + clear result)
Example: "How to Use Cursor" → AI_OTHER (tutorial, no evaluation)
Example: "Research Shows AI Coding Tools Improve Speed" → AI_DISCOURSE (research with findings)
Example: "Research: AI Coding Tools Improve Speed (Methodology Only)" → AI_OTHER (methodology only, no findings on utility)
Example: "Cursor 3.0 Announced" → AI_NEWS (product announcement)

Article:
{
  "title": "{title}",
  "content": "{content}"
}

Return valid JSON only:
{
  "category": "AI_DISCOURSE" | "AI_NEWS" | "AI_OTHER" | "NOISE",
  "confidence": 0.0-1.0,
  "reasoning": "<20 words max. Why this category?>"
}
```

## Category Summary

| Category       | Include in Verdict? | Key Signal                                                         |
| :------------- | :------------------ | :----------------------------------------------------------------- |
| `AI_DISCOURSE` | Yes                 | First-person experience, substantive opinion, OR research findings |
| `AI_NEWS`      | No                  | Announcements without developer opinion or findings                |
| `AI_OTHER`     | No                  | AI content not about coding (tutorials, methodology papers)        |
| `NOISE`        | No                  | Not AI-related                                                     |
