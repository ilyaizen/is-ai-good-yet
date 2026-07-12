# Summary Summarization Prompt (Phase 5)

This document contains the prompt used for synthesizing themes from grouped sentiment summaries.

## Purpose

Phase 5 takes the individual article summaries produced by Phase 4 sentiment analysis, groups them by sentiment (positive/neutral/negative), and synthesizes recurring themes from each group.

## Input

- **Sentiment group**: `positive`, `neutral`, or `negative`
- **Summaries**: Array of 15-word summary strings from Phase 4 analysis

## Prompt

```text
You are analyzing {n} developer opinions about AI coding tools.
These summaries have been classified as {sentiment_group} sentiment.

Your task is to identify 3-5 RECURRING THEMES that appear across these summaries.

## GUIDELINES

1. **Theme Titles**: Should be clear and descriptive (3-6 words)
   - Good: "Code Quality Concerns", "Productivity Speed Gains"
   - Bad: "Issues", "Positive Feedback"

2. **Descriptions**: Synthesize what developers are collectively saying (2-3 sentences)
   - Focus on specific, actionable insights
   - Capture nuance and common experiences

3. **Verdicts**: Short phrase summarizing the theme's conclusion (3-5 words)
   - For positive: "Productivity Gains Confirmed", "Worth the Learning Curve"
   - For neutral: "Mixed Results Depend on Context", "Benefits Require Expertise"
   - For negative: "High Frustration Risk", "Not Ready for Production"

4. **Related Count**: Estimate how many summaries relate to each theme

## INPUT SUMMARIES

{summaries}

## OUTPUT (JSON ONLY)

{
  "themes": [
    {
      "title": "Theme Title Here",
      "description": "2-3 sentence synthesis of what developers are saying about this topic across the summaries.",
      "related_count": <number>,
      "sentiment_verdict": "Short Verdict Phrase"
    }
  ],
  "meta": {
    "total_summaries": {n},
    "sentiment_group": "{sentiment_group}"
  }
}
```

## Edge Cases

1. **Few Summaries (<5)**: Return 1-2 themes maximum
2. **Highly Diverse**: Include "No Clear Consensus" as a theme if summaries are too varied
3. **Overlapping Topics**: Prefer distinct themes; merge similar concepts

## Example Output

```json
{
  "themes": [
    {
      "title": "Debugging Simple Errors",
      "description": "Developers consistently report success using AI tools to debug straightforward issues like syntax errors and simple logic bugs. However, complex debugging remains challenging.",
      "related_count": 8,
      "sentiment_verdict": "Best for Simple Cases"
    },
    {
      "title": "Boilerplate Code Generation",
      "description": "AI excels at generating repetitive code patterns, reducing tedious work. Developers appreciate the time saved on routine tasks.",
      "related_count": 6,
      "sentiment_verdict": "Clear Time Savings"
    }
  ],
  "meta": {
    "total_summaries": 15,
    "sentiment_group": "positive"
  }
}
```
