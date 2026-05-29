# Claude Code operational spec

This repo uses Claude Code as the default coding executor when Hermes is driving repo work on the Hetzner box.

Hermes stays the orchestrator: inspect state, write/verify handoffs, run final checks, and keep the repo/vault docs honest. Claude Code does repo-local code writing.

## Identity and repo paths

- public production repo: `ilyaizen/is-ai-good-yet`
- old private repo: `ilyaizen/is-ai-good-yet.com`
- old private repo purpose: Python scraper/analysis pipeline now being folded into the public repo
- target/current production checkout: `/srv/apps/is-ai-good-yet`
- old temporary working checkout during migration: `/tmp/is-ai-good-yet-public` (moved out of `/tmp`)
- canonical repo-local docs: `docs_internal/`, `docs/`, and `agents/`
- `agents/` contains Claude/Hermes execution specs; it does not replace project docs
- vault mirror: `HyperVault/Projects/is-ai-good-yet/`

Do not confuse the two GitHub repositories. The `.com` repo name is legacy/private history, not the production repo name.

## Default Claude Code lane

Use this for normal repo tasks:

```bash
claude -p "<specific repo task>" \
  --model anthropic/claude-opus-4-8 \
  --effort medium \
  --allowedTools 'Read,Edit,Write,Bash(git *),Bash(npm *),Bash(node *),Bash(python3 *),Bash(pytest *),Bash(pip *)' \
  --max-turns 8 \
  --max-budget-usd 1
```

Defaults:

- model: `anthropic/claude-opus-4-8`
- effort/thinking: `medium` (explicit — Opus 4.8 defaults to high)
- workdir: repo root
- mode: print mode (`claude -p`) for one-shot repo tasks
- interactive mode: tmux only, and only when the task needs iteration or slash commands
- permissions: narrow by default; never use blanket bypass for routine repo work

Use lower effort only for trivial tasks (typos, single-line fixes). medium Opus is the normal lane.

## Prerequisites on this box

Check these before trusting Claude Code work:

```bash
which claude
claude --version
claude auth status --text
which rtk
node --version
npm --version
python3 --version
git status --short --branch
```

Expected current shape:

- Claude Code installed at `/root/.local/bin/claude`
- Claude Code authenticated with Ilya's Claude API account
- Node/npm is the frontend/runtime path; do not use Bun for this repo
- RTK is installed at `/usr/local/bin/rtk`
- repo lives at `/srv/apps/is-ai-good-yet`

## Plugins and skills to wire first

### Required

1. Claude Code CLI authenticated and healthy.
2. Hermes `claude-code` skill available.
3. RTK shell hook active for Claude Code Bash output compression.
4. Repo-local `agents/` docs loaded/consulted before code changes.

### Useful but not mandatory

- Caveman style/skills for terse Claude-facing summaries when context gets noisy.
- Hermes `systematic-debugging` for bugs before handing a fix to Claude Code.
- Hermes `test-driven-development` for new behavior.
- Hermes `requesting-code-review` before commits touching runtime, scraping, scheduling, or admin controls.

### Not first-class yet

- `opencode`: future sibling lane, not current default.
- `pi`: future sibling lane, not current default.

Do not install random plugins just because they exist. If a plugin does not change the repo workflow, it is decoration.

## How Hermes should use Claude Code here

1. Inspect the repo state first:

   ```bash
   git status --short --branch
   git remote -v
   git log --oneline -5
   ```

2. Read relevant `agents/` docs before prompting Claude.
3. Give Claude Code a bounded, concrete task with exact files or commands when possible.
4. Restrict tools to the task.
5. Let Claude make repo-local edits.
6. Hermes verifies independently with the real commands.
7. Hermes commits only after verification, if the user asked for committed work or the workflow requires it.
8. Mirror durable repo docs into HyperVault only after the repo-local source is right.

Bad pattern:

```bash
claude -p "Improve the project" --dangerously-skip-permissions
```

Good pattern:

```bash
claude -p "Update agents/runtime.md so it documents the /srv/apps/is-ai-good-yet production checkout, npm/node runtime, and Python pipeline venv setup. Do not edit code." \
  --model anthropic/claude-opus-4-8 \
  --effort medium \
  --allowedTools 'Read,Edit' \
  --max-turns 4
```

## Repo work rules

- Use `npm`, not Bun.
- SvelteKit production deploy uses `@sveltejs/adapter-node`.
- Production start command is `HOST=0.0.0.0 node build/index.js`.
- Pipeline code stays in `pipeline/`.
- DB-backed scripts expect `pipeline/data/pipeline.db`.
- Runtime path resolution should be repo/module-relative, not `cwd`-relative.
- Internal project docs belong in `docs_internal/`; prompt/spec docs belong in `docs/`; agent execution specs belong in `agents/`.
- Vault mirrors are mirrors. They do not override repo-local docs.

## Python pipeline local setup lane

The pipeline has real Python dependencies and browser automation. On the Hetzner box, set it up explicitly:

```bash
cd /srv/apps/is-ai-good-yet
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r pipeline/requirements.txt
python -m playwright install chromium
python -m pytest pipeline/tests -q
```

Environment:

- `GROQ_API_KEY` is required for Groq-backed classification/analyzer phases.
- Optional proxy values belong in `.env`, not committed files.
- Browser/scraper phases should run with low concurrency. This box is small; don't stampede it.

Current caveat: `pipeline/run.py` is still a thin placeholder for `--phase ingest|scrape|analyze|all`. The real phase modules exist under `pipeline/src/`. Do not document `npm run pipeline:*` as fully functional orchestration until `pipeline/run.py` actually calls those modules.

## Verification commands

For docs-only changes:

```bash
npm run check
npm run build
```

For frontend/runtime changes:

```bash
npm run check
npm run build
HOST=0.0.0.0 node build/index.js
```

For pipeline changes:

```bash
. .venv/bin/activate
python -m pytest pipeline/tests -q
python -m src.catch_up -v      # from pipeline/ only, once DB/env are ready
python -m src.export -v        # from pipeline/ only, after data exists
```

For DB-backed Node scripts:

```bash
test -f pipeline/data/pipeline.db
npm run diagnose:schema-migration
npm run verify:fix
npm run test:article-display
```

If `pipeline/data/pipeline.db` is missing, fail clearly. Do not hide it behind a vague setup note.

## Interactive tmux lane

Use only for multi-turn work:

```bash
tmux new-session -d -s claude-is-ai-good-yet -x 140 -y 40

tmux send-keys -t claude-is-ai-good-yet 'cd /srv/apps/is-ai-good-yet && claude --model anthropic/claude-opus-4-8 --effort medium' Enter
```

Monitor:

```bash
tmux capture-pane -t claude-is-ai-good-yet -p -S -80
```

Exit and clean up:

```bash
tmux send-keys -t claude-is-ai-good-yet '/exit' Enter
tmux kill-session -t claude-is-ai-good-yet
```

## Future executor lanes

Add sibling docs only when they become executable lanes:

- `agents/opencode.md` for OpenCode repo execution.
- `agents/pi.md` for a `pi` executor lane.

Each future lane must include install/auth checks, exact command shape, allowed tools/scope, verification, and when not to use it. Otherwise it is just prose wearing a hard hat.
