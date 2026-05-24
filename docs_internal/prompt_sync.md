# Prompt Sync Guide

`docs/` contains the human-readable prompt specs used to keep pipeline prompt code honest.

## Canonical docs

- `docs/prefilter_prompt.md` — content relevance classifier: `AI_DISCOURSE`, `AI_NEWS`, `AI_OTHER`, `NOISE`.
- `docs/sentiment_prompt.md` — utility/trajectory sentiment scoring.
- `docs/summarization_prompt.md` — theme synthesis / summary prompt reference.

## Runtime prompt locations

Check the actual Python files before editing; do not trust stale line numbers.

Likely locations:

- `pipeline/src/prefilter_content.py`
- `pipeline/src/sentiment_analyzer.py`
- `pipeline/src/summary_summarizer.py`
- `pipeline/src/get_analysis_prompts.py`
- legacy/reference modules such as `pipeline/src/classifier.py` may still contain older/local prompt paths

## Current model/API posture

- Current analysis path primarily uses Groq where implemented.
- Ollama remains a dependency/reference path, not the default production analysis path.
- Older docs mentioning Mistral, Claude-only execution, Bun, or a nested frontend directory are stale unless verified in the code.

## Update rule

When changing a prompt:

1. Update the matching `docs/*.md` file.
2. Search the pipeline source for the prompt text/constant name.
3. Update every runtime copy that is actually used.
4. Update `get_analysis_prompts.py` if the UI preview depends on it.
5. Run a tiny smoke test, preferably with `--limit 1`, `--stats`, or a dry-run mode.
6. Mirror the docs to HyperVault after repo docs are correct.

## Useful searches

```bash
cd /srv/apps/is-ai-good-yet
rg "AI_DISCOURSE|utility|trajectory|CONTENT_CLASSIFICATION_PROMPT|SENTIMENT" pipeline/src docs
```

Use `npm run dev` only for UI preview work. Use npm, not Bun.
