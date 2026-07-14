# Changelog

All notable changes to this project will be documented in this file.

This changelog was restored from the legacy/private project history and normalized into the public repo docs.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Expand V2 article summaries to 50 words and individual HN comment summaries to 30 words.
- Make compressed Parquet the canonical store for scraped article bodies and stop writing duplicate plain-text copies.
- Export analyzed articles independently of legacy `articles-text` files.
- Constrain V2 Groq responses with strict JSON schemas, normalize nullable relation metadata, retry transient prefilter generation failures, and cap comment refill at `2T` candidates per story to prevent runaway model-call loops.
- Replace fragmented SSRF private-address check with `ip.is_global` policy that covers CGNAT `100.64.0.0/10` and other non-global ranges.
- Wire `TextArticleStore` in `sentiment_v2` through configurable `paths.py` instead of a hardcoded default.
- Count community-analysis model attempts only after deterministic eligibility passes so cap-ineligible rows never consume API budget.
- Validate V2 generation SHA-256 hashes at build time in the page adapter and keep manifest hashes in sync during status-only exports.
- Keep the initial V2 admin response lightweight and load full per-story analysis properties only when a ledger row opens.
- Keep V2 admin rows and expanded dimensions version-consistent, deduplicate repeated URL records per HN story, and reject incompatible legacy V2 schemas before querying them.

### Added

- Add command-specific production preflight diagnostics and block pipeline commands with missing imports, browsers, storage, or API keys.
- Add a V2 operations dashboard with persisted prefilter, analysis, dimension, token, model, version, hash, and orchestration telemetry.
- Add a bounded `curl_cffi` article fetch path and optional authenticated residential rendered-HTML service before archive fallback.
- Implement the public V2 broadcast-terminal dashboard with typed static contracts, bot-feed and HN evidence cards, source-tension diagnostics, dimensional history, persisted `lil-gui` controls, reduced-motion canvas effects, and explicit unavailable states.
- Add the isolated broad-scope V2 prefilter, immutable global-influence version, orchestration records, cron-safe locking, public pipeline telemetry, manifest hashing, and atomic generation publication with rollback.
- Vendor the Natural Earth 110m land asset for the dotted canvas globe.
- Add a live v2 admin methodology ledger with the exact versioned article and comment prompts.
- Add manual v2 comment-collection and analysis controls backed by the existing server pipeline runner.
- Add an isolated v2 two-tier sentiment pipeline for broader AI capability, trajectory, and societal-impact analysis.
- Add strict versioned article and per-comment prompt contracts with explicit missing-dimension handling.
- Add deterministic adaptive Hacker News ranked-tree sampling with isolated context-aware comment annotation.
- Add visibility-weighted and diversity-balanced community estimates, disagreement/polarization diagnostics, and broad-capture v2 prompt contracts without commenter-karma influence.
- Add normalized v2 analysis storage with prompt/input hashes and confidence-aware source aggregation.
- Add separate v2 static exports so existing sentiment data and frontend consumers remain backward compatible.

- **Phase 1.5 (Algolia Discovery)**: New pipeline phase to directly query HN Algolia API for high-signal AI stories.
- **Token Streaming**: Implemented token-by-token text streaming effects for verdict animations.
- **Replay Functionality**: Added replay button for verdict veil with reset mechanism.
- **AnimatedButton**: Created reusable `AnimatedButton` component and global loader.
- **Theme Export**: Added theme export functionality to pipeline.
- **LLM Metrics**: Added metrics display (tokens/sec) to article details sheet.
- Premium UI animations with consistent `cubic-bezier(0, 0.7, 0.1, 1)` easing across all components.
- Star ratings and mini history chart integrated into verdict display.
- Glow pulse animation on verdict answer text.
- Fade effects for historical data in timeline chart.
- **Dual Homepage**: Split frontpage into v1 (plain native scroll) and v2 (Lenis + Threlte 3D background) variants.
- **Lenis Smooth Scroll**: Integrated Lenis for smooth scroll with RAF loop and `scrollDelta` store.
- **Low-Poly 3D Background**: Threlte-based animated low-poly graph scene on homepage v2.
- **CRT Scanline Overlay**: Pixel-accurate scrolling CRT scanlines overlay component.
- **Glass Effect**: Theme-aware glass effect (backdrop-blur + opacity) on header, footer, and card backgrounds.
- **Custom Scrollbar**: Smooth-scroll-integrated custom scrollbar with drag and absolute position tracking.
- **Admin Pipeline Control**: Durable `/admin` page merging pipeline control and content table.
- **Pipeline Log Tail Viewer**: Real-time log tail viewer in admin UI.
- **Pipeline DB Bootstrap Recovery**: Recovery script for pipeline database bootstrap failures.
- **Anchor Smooth Scroll**: `scrollToId` / `handleAnchorClick` helpers for in-page anchor navigation.
- **CLI Automation Scripts**: Command-line interface and automation scripts for pipeline operations.
- **Pipeline Merged to Public Repo**: Pipeline code merged from private repo into public monorepo.
- **Coolify Deploy Support**: `@sveltejs/adapter-node` wired for Coolify/Nixpacks runtime; Node version pinned.
- **Drive Sync**: Docs and metadata synced into Google Drive mount.

### Changed

- **Docs Consolidation**: Rebuilt `AGENTS.md` as a single source of truth — stripped an obsolete Tauri/habit-tracker template (bun commands, `src-tauri/`, habits/calendars stores, `develop/0.1.0` branches) and fixed literal `TODO`s. Consolidated `docs_internal/` from 11 files (176K) into 4 focused docs (`README.md`, `ARCHITECTURE.md`, `GUIDE.md`, `TROUBLESHOOTING.md`) plus an `archive/` for completed history (`tasks.md`, `progress.md`, `plan.md`). Fixed all stale references: Bun→bun, nested `is-ai-good-yet/src/`→`src/`, dead `agents/` and `docs/*_prompt.md` paths, `vercel.json`/Vercel→Coolify/nixpacks, `/pipeline-admin`→`/admin`, old monorepo layout→flat.

- **Groq Migration**: Migrated summary summarizer and theme synthesis from Anthropic Claude to Groq (`openai/gpt-oss-20b`).
- **Frontend Refactor**: Removed direct Groq API integration/types from frontend core; switched to generic analysis fields.
- **UI Refinements**: Refined focus handling, accessibility (semantic section), and scroll behavior.
- **Landing Page**: cleanup of old components and renaming of composables.
- Redesigned verdict display with terminal-style container.
- Updated green accent colors with refined OKLCH values.
- Refactored header component to `app-header.svelte`.
- Improved chart interactions with fade zones for older data.
- **Scroll Architecture**: Replaced `scrollBus` pub/sub with direct `scrollDelta` Svelte store.
- **BackgroundEffects Removed**: Replaced `BackgroundEffects` component with pixel-accurate scanlines overlay.
- **Article Title Links**: Article title links now open detail sheet instead of navigating to details page.
- **SceneBackground Theme**: Wired `mode-watcher` dark/light theme into `SceneBackground` prop.
- **Admin Theme**: Admin pages made fully light-theme compatible with terminal-style chrome.
- **v1 Frontpage Restored**: v1 (native scroll, fullveil, working header) reinstated as default homepage.

### Fixed

- Keep pipeline logs full-width and preserve long lines with horizontal scrolling instead of wrapping them.
- Normalize overlong V2 article evidence quotes and summaries after strict generation so Groq boundary overages do not discard otherwise valid analyses.
- Publish V2 export files atomically with the manifest last instead of renaming an image-layer directory, which fails with `EXDEV` on production OverlayFS.
- Let the isolated V2 pipeline read reconciled article-text files when a scraped article is not yet present in Parquet, and process duplicate `hn_id` rows only once.
- Launch the installed Nix Chromium wrapper for scraping and make preflight perform a real browser launch, replacing the broken duplicate Playwright Chromium download.
- Resolve the production pipeline source from the real runtime filesystem instead of the bundled `/app/build` path, and add an article-text reconciliation command for registering orphan files without replacing canonical duplicate-URL rows.
- Restore `libstdc++.so.6` availability for Playwright/greenlet in Nixpacks and declare Newspaper's modern `lxml-html-clean` dependency.
- Keep V1 catch-up and analysis commands out of `/v2/admin`, expose the isolated V2 prefilter/orchestrator/export, and align Node/Python storage paths.
- Restore intentional phosphor city highlights on the V2 globe and remove the unintended whole-landmass flicker.
- Fix unreadable black age values in the admin content table and expand table search to titles and authors.
- Scroll inversion and verdict veil placement outside smooth-scroll container.
- SSR guard for `pointTexture` in 3D background scene.
- Light-theme node colors and info card values in admin views.
- Glass effect: opacity-only mode, correct `backdrop-filter` selector, dark/light theme colors.
- Scrollbar drag, thumb positioning, and scroll overshoot.
- Footer placement on all pages.
- CRT horizontal lines, `backdrop-blur` on terminal panels, header reactivity.
- Anchor links using smooth scroll on frontpage.
- Pipeline DB and admin views after Coolify deploy changes.

### Performance

- Reduced CPU usage in scene background component.

## [0.1.2] - 2026-01-18

### Added

- Version bump prompt after export and catch-up operations in CLI
- Export timestamp utility for tracking data updates (`exportedAt` field)
- Interactive version selection (patch/minor/major) in CLI workflow

### Changed

- Updated default output path from `frontend` to `is-ai-good-yet`
- Export phase (Phase 7) now runs as part of catch-up pipeline
- Renamed CSS classes from `.veil*` to `.verdict-veil*` namespace
- Documentation updated to reflect phases 2-7 pipeline structure

### Removed

- Legacy `veil.svelte` and `top-articles-table.svelte` components
- `--no-headful-switch` flag from scraper arguments

## [0.1.1] - 2026-01-17

### Added

- Static data export module (`export.py`) generating JSON for Vercel deployment
- `static-data.ts` for reading exported JSON data in frontend
- Weekly snapshots with 6-month rolling window for historical trends
- Article author and truncated excerpt (500 chars) in export data
- Phase 7: Export to Frontend in CLI menu

### Changed

- Simplified veil animation from word-by-word to line-by-line reveal
- Reorganized articles table with new column ordering and URL sorting
- Removed time window filtering to display all analyzed articles
- Updated all page server routes to use static data sources

### Fixed

- Dev server usage guidelines added to documentation

## [0.1.0] - 2026-01-16

### Added

- Incremental cleaning mode (`--new-only` flag) for article text processing
- Timestamp tracking for last clean time (`last_clean_timestamp.json`)
- Terminal-style typing animation for veil component
- Live article count and last update time display
- Interactive CLI selection between new-only and clean-all modes

### Changed

- Renamed "Recent Influential Articles" to "Top Articles" throughout codebase
- `clean_articles.py` now defaults to incremental mode in catch-up

### Breaking Changes

- `clean_articles.py` defaults to incremental mode; use `--clean-all` for full cleaning

## [0.0.9] - 2026-01-15

### Added

- `--update-recent` flag to HN resolver for refreshing metadata (default 30 days)
- Neutral articles now included in verdict calculations via `NEUTRAL_MULTIPLIER`
- Time-decay color indicators (green→yellow→red) in content table
- Article details sheet with `vaul-svelte` drawer component
- `fix_hn_id.py` utility for correcting HN ID mismatches
- IsMobile utility class for responsive components

### Changed

- Improved styling in content-table and recent-articles-table components
- Updated dependencies: `better-sqlite3` v12.6.0, `bits-ui` v2.15.4

## [0.0.8] - 2026-01-13

### Added

- V4.0 Schema with backward compatibility for v3 articles
- Catch-Up Pipeline (`catch_up.py`) running phases 2-6 in sequence
- Normalization helper (`normalizeAnalysis()`) for schema migration
- Diagnostic scripts for schema verification

### Changed

- Sentiment analysis schema simplified: single `topic` field replaces `subtopic/primary_theme/secondary_theme`
- Utility scale reduced from 7 to 5 tiers (magic/tool/mixed/toil/hazard)
- Sentiment weighting changed from trajectory-biased (40/60) to equal (50/50)
- Groq model upgraded from `llama-3.1-8b-instant` to `openai/gpt-oss-20b`
- WHERE clauses updated to handle both v3 and v4 schema articles

### Fixed

- 340 old-schema articles (33% of total) now included in verdict calculations
- Business topic exclusion works for both schema versions

### Breaking Changes

- `classification_json` schema changed from v3 to v4 format

## [0.0.7] - 2026-01-12

### Added

- Speed metrics tracking in Groq API calls (inference time, tokens/sec)
- `groq_metrics_json` database column for performance data
- Retry logic with exponential backoff for JSON validation failures
- Tabbed interface (analysis, prompts, content, speed) on details page

### Changed

- Switched from streaming to JSON response format for Groq API
- Expanded sentiment scale from ±0.8 to ±1.0
- Increased summary word limit from 15 to 25 words
- Redesigned frontend details page with terminal-style aesthetic

### Breaking Changes

- Renamed content_category value from 'OPINION_CODING' to 'AI_DISCOURSE'
- Sentiment score range expanded from [-0.8, 0.8] to [-1.0, 1.0]

## [0.0.6] - 2026-01-10

### Added

- Groq API integration replacing Mistral/Anthropic APIs
- Streaming support for real-time LLM output
- `informational` and `speculative` utility values for broader AI content
- Historical verdict snapshots (`getHistoricalVerdictSnapshots()`)
- Permanent record score (`getPermanentRecordScore()`)

### Changed

- Migrated to 3-category system (AI_DISCOURSE, AI_NEWS, NOISE)
- Redesigned homepage as minimal verdict site
- Replaced hero, methodology, topics, timeline, verdict sections with new landing components
- Adjusted sentiment range to -0.8 to +0.8

### Removed

- `/verdict` route (consolidated to homepage)
- Legacy hero, methodology, topics, timeline, verdict components

### Breaking Changes

- Content categories renamed (OPINION_CODING→AI_DISCOURSE, NEWS_CODING→AI_NEWS)

## [0.0.5] - 2026-01-08

### Added

- 4-category content classification system (AI_DISCOURSE, AI_NEWS, AI_OTHER, NOISE)
- Content-based prefiltering using actual article content (not just titles)
- Category filter dropdown and badges in content table
- `--min-score`, `--min-comments`, `--all-domains` CLI flags
- `--stats` mode for classification statistics

### Changed

- Prefilter renamed from `prefilter.py` to `prefilter_content.py`
- Head+tail truncation (60% opening + 40% closing) with `[… middle section omitted …]` separator

### Breaking Changes

- Phase 3 prefilter uses new column schema and classification output format

## [0.0.4] - 2026-01-06

### Added

- Sentiment analyzer using Anthropic Claude Haiku 4.5 API
- 2-dimension analysis: utility (positive/mixed/negative) + trajectory (optimistic/uncertain/pessimistic)
- Score derivation formula: `score = (utility * 0.6) + (trajectory * 0.4)`
- Subtopic, primary/secondary themes, summary, key quotes extraction
- Phase 5: Theme Summarization with sentiment grouping
- Dynamic topics section on homepage with sentiment icons

### Changed

- Verdict scoring from linear to "Forgetful Critic" logarithmic weighting
- Time decay window extended from 9 to 18 months
- Sentiment formula weights adjusted from 0.7/0.3 to 0.6/0.4

## [0.0.3] - 2026-01-04

### Added

- Unified scraper with automatic fallback chain
- Multi-tier archive fallback (Wayback → Google Cache → Archive.is Playwright → Selenium)
- Interactive archive session with CAPTCHA solving capability
- Session persistence for archive.is cookies
- Randomized URL selection to avoid detection patterns
- Human-like timing patterns and mouse movements

### Changed

- Replaced Camoufox with vanilla Playwright + playwright-stealth
- Simplified failover from legacy scraper modules

### Removed

- Legacy `archive_interactive.py` and `unified_scraper.py` modules
- Wayback/Google fallbacks initially, then restored multi-tier

## [0.0.2] - 2026-01-02

### Added

- Ground truth text storage in `articles-text/*.txt` files
- `rebuild_parquet.py` tool for syncing parquet from text files
- Article text data cleaning script (`clean_articles.py`)
- Uptake system for synchronizing database with cleaned files
- Consistency verification (`check_consistency.py`) with phantom/orphan detection

### Changed

- Text store format simplified to Title + URL only (removed Author/Date)
- Backup strategy with automatic `articles-text-backup/` creation

## [0.0.1] - 2025-12-28

### Added

- Initial project structure with Python pipeline and SvelteKit frontend
- Histre backfill system scraping 340+ pages
- HN Resolver querying Algolia API for metadata
- SQLite database schema for URL tracking
- Basic Playwright scraper with stealth patches
- Interactive CLI menu (`cli.ts`) for pipeline operations
- Rich progress bars and verbose mode in CLI tools

---

## Legend

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Vulnerability fixes
- **Breaking Changes**: Changes requiring migration

[Unreleased]: https://github.com/ilyaizen/is-ai-good-yet/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/ilyaizen/is-ai-good-yet/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/ilyaizen/is-ai-good-yet/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/ilyaizen/is-ai-good-yet/compare/v0.0.9...v0.1.0
[0.0.9]: https://github.com/ilyaizen/is-ai-good-yet/compare/v0.0.8...v0.0.9
[0.0.8]: https://github.com/ilyaizen/is-ai-good-yet/compare/v0.0.7...v0.0.8
[0.0.7]: https://github.com/ilyaizen/is-ai-good-yet/compare/v0.0.6...v0.0.7
[0.0.6]: https://github.com/ilyaizen/is-ai-good-yet/compare/v0.0.5...v0.0.6
[0.0.5]: https://github.com/ilyaizen/is-ai-good-yet/compare/v0.0.4...v0.0.5
[0.0.4]: https://github.com/ilyaizen/is-ai-good-yet/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/ilyaizen/is-ai-good-yet/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/ilyaizen/is-ai-good-yet/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/ilyaizen/is-ai-good-yet/releases/tag/v0.0.1
