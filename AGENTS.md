# AGENTS.md

> Guidance for AI coding agents (Pi, Claude Code, Codex, Cursor, OpenCode, KiloCode, etc.) working on `is-ai-good-yet`.

## Project

**Is AI "Good" Yet?** — a terminal-themed dashboard that visualizes Hacker News sentiment toward AI. The legacy V1 experience focuses on AI coding tools. V2 broadens the question across capability, trajectory, and societal impact, combining article analysis with visible Hacker News discussion and a separate bot-discovered news feed.

- GitHub repo: `ilyaizen/is-ai-good-yet`
- Production deploy: repo root via Coolify/nixpacks (Node 22.12), `@sveltejs/adapter-node`
- Status: V1 remains stable; the isolated V2 pipeline, static export contracts, public `/v2` dashboard, and `/v2/admin` methodology controls are implemented

## Stack

- **Frontend** (repo root, _not_ a nested `frontend/` or `is-ai-good-yet/` dir): SvelteKit 2 + Svelte 5 (runes) + Tailwind CSS v4.1 + shadcn-svelte + D3/LayerCake
- **Backend pipeline** (`pipeline/`): Python 3.11+ — Polars, aiohttp, trafilatura, Playwright/camoufox scraping, Groq/Mistral/Anthropic LLM APIs
- **V2 analysis**: isolated broad-scope prefilter + article thesis analysis + deterministic ranked-tree HN comment sampling; versioned methodology lives in `docs/v2-*.md`
- **Visitor counter** (`convex/`): Convex backend
- **Package manager: Vite+ (pnpm)/Node 22.12** (pnpm-lock.yaml committed; `nixpacks.toml` uses `vp install` + `vp build`)
- **Data storage**: SQLite (`pipeline/data/pipeline.db`) + compressed Parquet article bodies + separate V1/V2 static JSON exports under `src/lib/data/`

## Project Structure

```
src/
  lib/
    components/
      landing/    # V1 verdict, article explorer, history, and supporting UI
      v2/         # V2 broadcast dashboard: shell, hero, evidence, bot-feed, history, effects, settings
      ui/         # shadcn-svelte primitives
    composables/  # Svelte 5 composables
    data/
      v2/         # atomic V2 generation: manifest, verdict, stories, history, bot-feed, pipeline status
      *.json      # V1 static exports
    server/       # DB/pipeline utilities plus V2 page adapter and methodology loader
    state/        # V2 persisted visual settings
    types/        # shared TypeScript contracts, including types/v2.ts
    convex/       # Convex client
    constants.ts, version.ts, utils.ts
  routes/
    +page.svelte  # V1 landing page
    v2/           # public V2 dashboard and authenticated admin methodology controls
    admin/, api/, details/[id], lab/
  styles/         # shared tokens plus V1/V2 route styles and effects
pipeline/
  src/            # V1 phases plus isolated V2 prefilter, comments, sentiment, orchestration, storage, export
  tests/          # pipeline tests, including V2 contract and comment-selection coverage
convex/           # Convex visitor-counter backend
docs/             # public docs and normative V2 methodology/prompt contracts
docs_internal/    # operational docs and V2 design specification
scripts/          # tsx helper scripts (bump-version, verify-fix, diagnose, tests)
static/           # favicon, OG images, and vendored visual assets
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

Use the narrowest relevant check. Frontend uses Vite+; pipeline uses Python from `.venv`.

```bash
vp run check        # Vite+ checks plus Svelte type checking
vp lint             # Vite+ linting
vp build            # production build (slow — only when deploying)
. .venv/bin/activate && python -m pytest pipeline/tests -q   # pipeline tests (may fail until pipeline.db exists)
```

Full command reference: see [`docs_internal/cli.md`](./docs_internal/cli.md) and [`docs_internal/guide.md`](./docs_internal/guide.md).

## Code Style

- **Indentation**: 2 spaces · **Line width**: 100 (frontend Oxfmt `printWidth: 120`)
- **Strings**: double quotes · **Semicolons**: always · **Trailing commas**: none
- **Files**: `kebab-case` · **Svelte components**: `kebab-case.svelte`
- **Variables/functions**: `camelCase` · **Types/interfaces**: `PascalCase` · **Constants**: `UPPER_SNAKE_CASE` · **Python/Rust modules**: `snake_case`
- **TypeScript**: strict mode, no unused vars, explicit return types for public functions, prefer `interface` over `type`, `satisfies` over type assertions, never `!` non-null assertion
- **Svelte 5**: use `$state`, `$derived`, `$props`, `$effect` (not `$:`); `onclick` not `on:click`; call derived signals as `doubled()` not `doubled`; import from `$app/state` not `$app/stores`
- **Styling**: Tailwind utility-first; design tokens live in `src/styles/tokens.css` (single source of truth — never hardcode OKLCH values); animation easing `cubic-bezier(0, 0.7, 0.1, 1)`
- **V2 isolation**: do not reuse V1 prompt, storage, export, or route contracts for V2; never silently fall back from V2 data to V1 data
- **V2 methodology**: preserve immutable contract/version identifiers and the documented capability/trajectory/impact semantics; update the normative `docs/v2-*.md` contract when changing analysis behavior
- **V2 publication**: publish `src/lib/data/v2/` as one manifest-validated atomic generation; keep explicit unavailable states for missing or invalid generations
- **CLI wrapper**: when adding arguments to a Python pipeline script, also expose them in `cli.ts`

## Git Workflow

- **NEVER commit directly to `main`** — all changes via PRs
- Work on feature branches: `feature/`, `fix/`, `refactor/`, `docs/`
- Open PRs targeting `main`
- Update [`CHANGELOG.md`](./CHANGELOG.md) under `[Unreleased]` for notable changes (Keep a Changelog: Added, Changed, Deprecated, Removed, Fixed, Security, Breaking Changes)

## Hard Rules

- Use Vite+/Node.
- Frontend is the repo-root SvelteKit app, not a nested `frontend/` directory.
- Production deploy uses `@sveltejs/adapter-node` via `nixpacks.toml`.
- Pipeline code stays in `pipeline/` and uses the repo-root `.venv` with Python 3.11. Run pipeline commands from `pipeline/` (or via the `vp run pipeline:*` scripts).
- V1 and V2 are additive, separate systems. V2 changes must not alter V1 sentiment fields or overwrite V1 static exports.
- `/v2` reads only the manifest-validated files in `src/lib/data/v2/` through `src/lib/server/v2-page-adapter.ts`.
- **Do not preserve or print secrets.** Replace credentials with `[REDACTED]`.

## Internal Docs (`docs_internal/`)

Operational documentation for agents and maintainers. Index + details:

- [`docs_internal/README.md`](./docs_internal/README.md) — index, project overview, pipeline phase status
- [`docs_internal/architecture.md`](./docs_internal/architecture.md) — system design, data flow, pipeline phases, verdict scoring
- [`docs_internal/guide.md`](./docs_internal/guide.md) — setup, usage, dev conventions, agent mandates
- [`docs_internal/troubleshooting.md`](./docs_internal/troubleshooting.md) — common issues and solutions
