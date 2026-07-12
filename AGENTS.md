# AGENTS.md

> Guidance for AI coding agents (Pi, Claude Code, Codex, Cursor, OpenCode, KiloCode, etc.) working on `is-ai-good-yet`.

## Project

**Is AI "Good" Yet?** — a terminal-themed dashboard that visualizes Hacker News sentiment toward AI coding tools. A Python pipeline scrapes and LLM-analyzes AI-tagged HN submissions; a SvelteKit frontend renders the verdict, timeline, and article explorer.

- GitHub repo: `ilyaizen/is-ai-good-yet`
- Production deploy: repo root via Coolify/nixpacks (Node 22.12), `@sveltejs/adapter-node`
- Status: all 7 backend pipeline phases complete; frontend live with static JSON data export

## Stack

- **Frontend** (repo root, _not_ a nested `frontend/` or `is-ai-good-yet/` dir): SvelteKit 2 + Svelte 5 (runes) + Tailwind CSS v4.1 + shadcn-svelte + D3/LayerCake
- **Backend pipeline** (`pipeline/`): Python 3.11+ — Polars, aiohttp, trafilatura, Playwright/camoufox scraping, Groq/Mistral/Anthropic LLM APIs
- **Visitor counter** (`convex/`): Convex backend
- **Package manager: bun/Node 22.12** (bun.lock committed; `nixpacks.toml` uses `bun install` + `bun run build`)
- **Data storage**: SQLite (`pipeline/data/pipeline.db`) + Parquet + exported static JSON (`src/lib/data/`)

## Project Structure

```
src/
  lib/
    components/   # landing/ (verdict-veil, verdict-display, articles-table, history-chart), ui/ (shadcn)
    composables/  # Svelte 5 composables (useTokenStream, etc.)
    data/         # static JSON exported by the pipeline (articles, themes, verdict)
    server/       # server-side DB utilities
    types/        # TypeScript types
    convex/       # Convex client
    constants.ts, version.ts, utils.ts
  routes/         # +page (landing), +layout, details/[id], admin/, api/, v2/, lab/
  styles/         # tokens.css (design tokens — single source of truth), terminal.css, base.css, animations.css, components.css, crt-effect.css
pipeline/         # Python data pipeline source + CLI (run from pipeline/, see pipeline/README.md)
convex/           # Convex visitor-counter backend
docs/             # Public docs (README only)
docs_internal/    # Operational/internal docs (see below)
scripts/          # tsx helper scripts (bump-version, verify-fix, diagnose, tests)
static/           # favicon, OG images
cli.ts            # Pipeline CLI wrapper
```

## Core Development Rules

### Think Before Code

- Don't assume. Don't hide confusion. Surface tradeoffs.
- State assumptions. Uncertain? → ask.
- Multiple interpretations? → present, no silent pick.
- Simpler path exists? → say so. Push back.
- Unclear? → stop. Name confusion. Ask.

### Simplicity First

- Minimum code that solves the problem. Nothing speculative.
- No features beyond specifications. No abstractions for single-use code.
- No "flexibility"/"configurability" not requested.
- 200 lines could be 50? → rewrite.

### Goal-Driven Execution

- Define success. Loop until verified.
- "Add validation" → write failing tests, make pass.
- "Fix bug" → write reproducing test, make pass.
- "Refactor X" → tests pass before and after.
- Multi-step? → state plan: `[step] → verify: [check]`.

### Approach

- Think before acting. Read existing files before writing code.
- Concise output, thorough reasoning.
- Prefer editing over rewriting whole files. Don't re-read files unless changed.
- Test code before declaring done.
- User instructions always override this file.

### Efficiency

- Read before write. Each file once. Edit over rewrite.
- Never guess paths.
- Stuck? → ask. No dead ends.

## Testing / Committing

- **DON'T run checks unprompted.** ALWAYS ASK the user for explicit confirmation before running any verification, linting, type-check, or build commands.
- **DON'T commit without explicit user confirmation.**
- Before ending a task, ask whether to run checks and commit.
- If user confirms committing, generate a Conventional Commits message summarizing the diff concisely.
- Comments explain "why" not "what". Add them sparingly.

## Verification Commands

Use the narrowest relevant check. Frontend uses bun; pipeline uses Python from `.venv`.

```bash
bun run check        # svelte-kit sync + svelte-check (type checking)
bun run lint         # prettier --check + eslint
bun run build        # production build (slow — only when deploying)
. .venv/bin/activate && python -m pytest pipeline/tests -q   # pipeline tests (may fail until pipeline.db exists)
```

Full command reference: see [`docs_internal/cli.md`](./docs_internal/cli.md) and [`docs_internal/guide.md`](./docs_internal/guide.md).

## Code Style

- **Indentation**: 2 spaces · **Line width**: 100 (frontend prettier `printWidth: 120`)
- **Strings**: double quotes · **Semicolons**: always · **Trailing commas**: none
- **Files**: `kebab-case` · **Svelte components**: `kebab-case.svelte`
- **Variables/functions**: `camelCase` · **Types/interfaces**: `PascalCase` · **Constants**: `UPPER_SNAKE_CASE` · **Python/Rust modules**: `snake_case`
- **TypeScript**: strict mode, no unused vars, explicit return types for public functions, prefer `interface` over `type`, `satisfies` over type assertions, never `!` non-null assertion
- **Svelte 5**: use `$state`, `$derived`, `$props`, `$effect` (not `$:`); `onclick` not `on:click`; call derived signals as `doubled()` not `doubled`; import from `$app/state` not `$app/stores`
- **Styling**: Tailwind utility-first; design tokens live in `src/styles/tokens.css` (single source of truth — never hardcode OKLCH values); animation easing `cubic-bezier(0, 0.7, 0.1, 1)`
- **CLI wrapper**: when adding arguments to a Python pipeline script, also expose them in `cli.ts`

## Git Workflow

- **NEVER commit directly to `main`** — all changes via PRs
- Work on feature branches: `feature/`, `fix/`, `refactor/`, `docs/`
- Open PRs targeting `main`
- Update [`CHANGELOG.md`](./CHANGELOG.md) under `[Unreleased]` for notable changes (Keep a Changelog: Added, Changed, Deprecated, Removed, Fixed, Security, Breaking Changes)

## Hard Rules

- Use bun/Node, not Bun.
- Frontend is the repo-root SvelteKit app, not a nested `frontend/` directory.
- Production deploy uses `@sveltejs/adapter-node` via `nixpacks.toml`.
- Pipeline code stays in `pipeline/` and uses the repo-root `.venv` with Python 3.11. Run pipeline commands from `pipeline/` (or via the `bun run pipeline:*` scripts).
- **Do not preserve or print secrets.** Replace credentials with `[REDACTED]`.

## Internal Docs (`docs_internal/`)

Operational documentation for agents and maintainers. Index + details:

- [`docs_internal/README.md`](./docs_internal/README.md) — index, project overview, pipeline phase status
- [`docs_internal/architecture.md`](./docs_internal/architecture.md) — system design, data flow, pipeline phases, verdict scoring
- [`docs_internal/guide.md`](./docs_internal/guide.md) — setup, usage, dev conventions, agent mandates
- [`docs_internal/troubleshooting.md`](./docs_internal/troubleshooting.md) — common issues and solutions
