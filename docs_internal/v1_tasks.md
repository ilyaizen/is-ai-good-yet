# Project Tasks

## Pipeline Phase Overview

The pipeline has been restructured for optimal workflow:

1. **Phase 1**: Ingestion & HN Resolution
2. **Phase 2**: Content Scraping (formerly Phase 3)
3. **Phase 2.5**: Data Cleaning & Ground-Truth Uptake
4. **Phase 2.7**: Consistency Verification
5. **Phase 3**: Pre-filtering (formerly Phase 2, now runs AFTER scraping)
6. **Phase 4**: LLM Analysis (Sentiment Classification)
7. **Phase 5**: Theme Summarization
8. **Phase 7**: Export & Static Data Generation (**NEW**)

## Phase 1: Backend & Data Pipeline (Setup & Ingestion)

| ID                           | Description                                            | Status   | Dependencies    | Acceptance Criteria                                                                                                                                                                                 |
| :--------------------------- | :----------------------------------------------------- | :------- | :-------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **TSK-B00**                  | **Histre Backfill (Legacy)**                           | **Done** | -               | *Deprecated*: Original backfill for Jan-June 2025.                                                                                                                                                  |
| **TSK-B00-REWORK**           | **Architecture Rework**                                | **Done** | TSK-B00         | Deprecate `posted_links.json`. Use `backfill_histre.py` (pages 1-340) as main ingestion source. Data reset.                                                                                         |
| **TSK-B00-LATEST**           | **Scrape Latest Pages**                                | **Done** | -               | Scrape Histre pages 1-2 to capture latest stories. Integrated into `backfill_histre.py`.                                                                                                            |
| **TSK-B01**                  | **Verify/Update Database Schema**                      | **Done** | -               | `pipeline.db` created with `urls` table; schema matches design (fields for HN metadata, scores, status).                                                                                            |
| **TSK-B02**                  | **Implement HN Resolver**                              | **Done** | TSK-B01         | `hn_resolver.py` runs against `posted_links.json`; populates SQLite with `hn_id`, `hn_score`, `hn_comments`.                                                                                        |
| **TSK-B02-F**                | **Fix Resolver Metadata/CLI**                          | **Done** | TSK-B02         | `hn_resolver.py` fetches `title`, `posted_at`; CLI reports accurate success/skip/fail counts.                                                                                                       |
| **TSK-B01-ALGOLIA**          | **Algolia Discovery (Phase 1.5)**                      | **Done** | TSK-B00         | `algolia_discover.py` implemented to directly query HN Algolia API for missed AI stories (Phase 1.5). Integrated into catch-up pipeline.                                                            |
| **TSK-B03**                  | **Implement Scraper**                                  | **Done** | TSK-B02         | `scraper.py` iterates `resolved` URLs; extracts text via Trafilatura; saves to Parquet; updates DB status.                                                                                          |
| **TSK-B03-TXT**              | **Ground Truth Text Storage**                          | **Done** | TSK-B03         | Scraper saves editable .txt files (`articles-text/`); `rebuild_parquet.py` created to sync Parquet from these files.                                                                                |
| **TSK-B03-RETRY**            | **Retry & Scraper Improvements**                       | **Done** | TSK-B03         | `scraper.py` supports `--retry-failed` and `Archive.is` fallback/forced domains.                                                                                                                    |
| **TSK-B03-FIX**              | **Modernize Scraper (Camoufox)**                       | **Done** | TSK-B03         | Replaced `playwright-stealth` with `camoufox` to fix import errors and improve bot evasion.                                                                                                         |
| **TSK-B03-MODERN**           | **Modernize Scraper (Playwright Best Practices 2025)** | **Done** | TSK-B03-FIX     | Replaced Camoufox with vanilla Playwright + stealth; added residential proxy support, smart timing patterns, enhanced retry logic with exponential backoff, and anti-bot fingerprint randomization. |
| **TSK-B03-ARCHIVE**          | **Interactive Archive.is Scraper**                     | **Done** | TSK-B03-MODERN  | `archive_interactive.py` provides robust, continuous scraping with manual CAPTCHA solving, pauses/resumes, and batch processing. CLI updated for ease of use.                                       |
| **TSK-B03-UNIFIED**          | **Unified Scraper Fallback**                           | **Done** | TSK-B03-ARCHIVE | Merged all scraping logic into `scraper.py` (formerly unified); removed Wayback/Google fallbacks; enforced Archive.is fallback with session validation. Legacy modules removed.                     |
| **TSK-B03-FALLBACK**         | **Improved Archive Fallback & Retry**                  | **Done** | TSK-B03-UNIFIED | Restored multi-tier archive fallback (Wayback→Playwright→Selenium opt-in); randomized URL selection; improved lean mode retries; CLI presets for retry modes.                                       |
| **TSK-B04**                  | **Implement Content Prefilter (Post-Scrape)**          | **Done** | TSK-B03-UPTACK  | `prefilter_content.py` uses Mistral API to classify scraped article content into categories (AI_DISCOURSE, AI_NEWS, AI_OTHER, NOISE). Runs AFTER scraping (Phase 3).                                |
| **TSK-B03-CONSIST**          | **Consistency Verification (Phase 2.7)**               | **Done** | TSK-B03-UPTACK  | `check_consistency.py` detects phantom articles (DB success but missing content) and can auto-fix by resetting status.                                                                              |
| **TSK-B03-CLEAN**            | **Article Text Data Cleaning**                         | **Done** | TSK-B03-TXT     | `clean_articles.py` implemented with configurable cleaning patterns, backup strategy, and simplified header format (Title + URL only).                                                              |
| **TSK-B03-UPTACK**           | **Ground-Truth Uptake**                                | **Done** | TSK-B03-CLEAN   | `uptake_ground_truth.py` synchronizes database and parquet with cleaned article text files, resets deleted article statuses.                                                                        |
| **TSK-B05**                  | **Implement Sentiment Analyzer (Anthropic)**           | **Done** | TSK-B04         | `sentiment_analyzer.py` uses Claude Haiku 4.5 API; 2-dimension analysis (utility/trajectory); saves sentiment_score and classification_json to DB.                                                  |
| **TSK-B05-REFINE**           | **Refine Sentiment Analysis Prompt**                   | **Done** | TSK-B05         | Restructured prompt to be more concise; added strict rejection criteria for non-AI-coding content; improved output format.                                                                          |
| **TSK-B05-THEMES**           | **Implement Theme Summarization (Phase 5)**            | **Done** | TSK-B05-REFINE  | `theme_summarizer.py` synthesizes themes from analyzed articles; groups by sentiment; stores in `themes` table with article counts. Was migrated from Anthropic to Groq.                            |
| **TSK-B05-RECLASS**          | **Reclassification Utility**                           | **Done** | TSK-B05-THEMES  | Utility to move irrelevant articles from AI_DISCOURSE to AI_OTHER category after analysis.                                                                                                          |
| **TSK-B04-REWORK**           | **Prefilter Prompt Rework**                            | **Done** | TSK-B04         | Replaced prefilter prompt with "Expert Content Analyst" version; implemented 60/40 head/tail truncation with `[… middle section omitted …]` separator; reduced reasoning to 15 words.               |
| **TSK-B05-SENTIMENT-REWORK** | **Sentiment Prompt Rework**                            | **Done** | TSK-B05-REFINE  | Synced new sentiment prompt with utility (positive/mixed/negative), trajectory (optimistic/uncertain/pessimistic), subtopic & theme classification.                                                 |
| **TSK-B06**                  | **Implement Export/API Logic**                         | **Done** | TSK-B05-THEMES  | `export.py` generates static JSON (articles, verdict, historical) for Vercel deployment. CLI integration complete.                                                                                  |

## Phase 2: Frontend Development (Dashboard)

| ID          | Description                              | Status   | Dependencies     | Acceptance Criteria                                                                                                       |
| :---------- | :--------------------------------------- | :------- | :--------------- | :------------------------------------------------------------------------------------------------------------------------ |
| **TSK-F01** | **Setup SvelteKit Project**              | **Done** | -                | Project initialized with Tailwind v4, shadcn-svelte, bits-ui; `package.json` deps installed.                              |
| **TSK-F02** | **Create Dashboard Skeleton**            | **Done** | TSK-F01, TSK-B01 | Homepage displays a list/table of articles reading directly from `pipeline.db` (via `better-sqlite3`).                    |
| **TSK-F03** | **Create "Verdict" View**                | **Done** | TSK-F02, TSK-B05 | UI component showing the aggregated “Is AI Good Yet?” result (Green/Red) based on sentiment scores.                       |
| **TSK-F04** | **Create Detailed Table View**           | **Done** | TSK-F02          | Interactive data table with sorting/filtering by HN Score, Sentiment, Date.                                               |
| **TSK-F05** | **Polish UI/UX**                         | **Done** | TSK-F04          | Applied consistent shadcn-svelte styling; responsive design; loading states.                                              |
| **TSK-F06** | **Display Metadata (Title/Date/Author)** | **Done** | TSK-B02-F        | Update `ContentTable` to show article title, posted date, and author; replaced Preview with Details route.                |
| **TSK-F07** | **Improve Pipeline Manager Table**       | **Done** | TSK-F04          | Update Opinion, Status, and Sentiment columns with correct badges and logic.                                              |
| **TSK-F08** | **Enhance Table Filters**                | **Done** | TSK-F07          | Fix filtering for all statuses including Failed and Skipped; add dropdown options.                                        |
| **TSK-F09** | **Display Source Domain**                | **Done** | TSK-F06          | Show TLD in "Visit Source" link in `ContentTable`.                                                                        |
| **TSK-F10** | **Fix Filters & Add Relevant Toggle**    | **Done** | TSK-F08          | Fixed scraped status detection; added "Relevant Only" filter toggle; reordered filter UI.                                 |
| **TSK-F11** | **Implement Timeline Chart**             | **Done** | TSK-F03          | Weekly sentiment timeline with stacked bars; uses d3-shape for area visualization; filtered to analyzed articles only.    |
| **TSK-F12** | **Dynamic Topics Section**               | **Done** | TSK-B05-THEMES   | Homepage topics area dynamically renders database themes with sentiment-grouped display and responsive grid layout.       |
| **TSK-F13** | **Article Details Analysis Display**     | **Done** | TSK-B05          | Details page shows full analysis: utility, trajectory, subtopic, themes, summary, and key quotes with color-coded badges. |
| **TSK-F14** | **Migrate CSS to Tailwind**              | **Done** | TSK-F05          | Migrated section components from custom CSS to Tailwind utility classes; refactored table to flexbox layout.              |
| **TSK-F15** | **Category Filter & Badges**             | **Done** | TSK-B04          | Added category dropdown filter and color-coded badges (Fuchsia/Cyan/Amber/Zinc) to content table.                         |
| **TSK-F16** | **Standardize Container Widths**         | **Done** | TSK-F05          | Removed nested wrappers; applied consistent max-width (64rem) and padding to content containers.                          |
| **TSK-F17** | **Refine Table Theme Styling**           | **Done** | TSK-F14          | Badge colors via Tailwind utilities; fixed responsiveness; column hiding on small viewports.                              |

## Phase 2b: Frontend Redesign (Minimal Verdict Site)

Complete redesign to transform the site from a data dashboard into a minimal verdict site. See `docs/redesign_spec.md` for full specification.

| ID          | Description                             | Status   | Dependencies | Acceptance Criteria                                                                                          |
| :---------- | :-------------------------------------- | :------- | :----------- | :----------------------------------------------------------------------------------------------------------- |
| **TSK-F18** | **Landing Veil Component**              | **Done** | -            | Full-viewport veil with "Is AI Good Yet?" title, tagline, reveal button. localStorage persistence.           |
| **TSK-F19** | **Verdict Display Component**           | **Done** | TSK-F18      | Minimal YES/NO/NOT YET display with score. No methodology, no confidence badges.                             |
| **TSK-F20** | **History Chart Component**             | **Done** | TSK-F19      | Line chart showing historical verdict snapshots. Hover shows score at each month. Threshold lines at 45/55.  |
| **TSK-F21** | **Stats Bar Component**                 | **Done** | TSK-F19      | One-line stats: "now X · all-time Y · Z articles". Simple counts, no weights.                                |
| **TSK-F22** | **Historical Verdict Snapshots (Data)** | **Done** | -            | New `getHistoricalVerdictSnapshots()` function. Calculates what verdict would have been at each month.       |
| **TSK-F23** | **Permanent Record Score (Data)**       | **Done** | -            | New `getPermanentRecordScore()` function. All-time sentiment with no time decay.                             |
| **TSK-F24** | **Homepage Rewrite**                    | **Done** | TSK-F18-F23  | Replace entire homepage with veil + verdict + chart + stats. Remove Hero, Methodology, Topics, old Timeline. |
| **TSK-F25** | **Remove /verdict Route**               | **Done** | TSK-F24      | Delete entire `/verdict` directory. All content now on homepage.                                             |
| **TSK-F26** | **Cleanup Unused Components**           | **Done** | TSK-F25      | Remove: hero.svelte, methodology.svelte, topics.svelte, old timeline.svelte, old verdict.svelte.             |
| **TSK-F27** | **Copy Rewrite (Human Voice)**          | **Done** | TSK-F24      | All UI text rewritten following Human Voice guidelines. No jargon, no methodology inline, direct statements. |

## Phase 2c: Frontend Data Migration & Backward Compatibility

Schema migration to handle v3→v4 data transition without re-analyzing old articles.

| ID          | Description                            | Status   | Dependencies | Acceptance Criteria                                                                                                                         |
| :---------- | :------------------------------------- | :------- | :----------- | :------------------------------------------------------------------------------------------------------------------------------------------ |
| **TSK-F28** | **V4.0 Schema Backward Compatibility** | **Done** | TSK-F27      | All 340 old-schema articles (v3: subtopic/primary_theme/secondary_theme) included in verdict alongside 678 new-schema articles (v4: topic). |
| **TSK-F29** | **Diagnostic & Verification Tools**    | **Done** | TSK-F28      | Created diagnostic scripts to detect schema migration issues, verify fix impact, and test article display with normalized data.             |
| **TSK-F30** | **Token Streaming & Replay**           | **Done** | TSK-F24      | Implemented token-by-token text streaming for verdict animations and replay functionality for the intro veil.                               |
| **TSK-F31** | **UI Refinements & Components**        | **Done** | TSK-F30      | Added `AnimatedButton`, consolidated scroll utilities, and refined accessibility/focus management.                                          |
| **TSK-F32** | **Remove Groq Metrics from Core**      | **Done** | TSK-F30      | Refactored frontend to use generic analysis fields and static data, removing direct dependencies on Groq types/metrics.                     |

## Phase 3: Documentation & Deployment

| ID          | Description                    | Status          | Dependencies | Acceptance Criteria                                                                     |
| :---------- | :----------------------------- | :-------------- | :----------- | :-------------------------------------------------------------------------------------- |
| **TSK-D01** | **Create Usage Documentation** | **Done**        | -            | `docs_internal/usage.md` created with installation, configuration, and execution steps. |
| **TSK-D02** | **Update README**              | **Done**        | TSK-D01      | Root `README.md` updated with badges, project summary, and links to docs.               |
| **TSK-D03** | **Prepare for Deployment**     | **In Progress** | All          | Build scripts verified; environment variable examples finalized.                        |
| **TSK-D04** | **Create CHANGELOG.md**        | **Done**        | -            | CHANGELOG.md following Keep a Changelog format with version history.                    |
| **TSK-D05** | **Update Progress Report**     | **Done**        | TSK-D04      | progress.md updated with Phase 7 completion and recent changes.                         |
| **TSK-D06** | **Frontend Directory Rename**  | **Done**        | -            | Renamed `frontend` to `is-ai-good-yet` across all documentation and code references.    |

## Detailed Task Breakdown

### TSK-B00-LATEST: Scrape Latest Pages

- [x] **Scrape Recent**: Created `pipeline/src/update_recent.py` to scrape pages 1-2 and manage refresh lists.
- [x] **Refresh Metadata**: Run `hn_resolver.py` in retry/update mode to fetch fresh upvote/comment counts for these recent items.

### TSK-B00-REWORK: Architecture Rework & Full Ingestion

- [x] **Deprecate Legacy**: Archived `posted_links.json` to `legacy_posted_links.json`.
- [x] **Update Scraper**: `backfill_histre.py` now scrapes pages 1-340+ and saves to `pipeline/data/histre_feed.json`.
- [x] **Reset Data**: `pipeline.db` and parquet storage reset for clean ingestion.
- [x] **Update Resolver**: `hn_resolver.py` reads from the new `histre_feed.json`.

### TSK-B00: Histre Backfill (Legacy)

- [x] **Identify Range**: Confirm page numbers on Histre.
- [x] **Create Scraper**: Write a script (python or node) to scrape `histre.com/hn/?tags=+ai&page=N`.
- [x] **Extract Links**: Parse HTML to get original URLs and/or HN discussion IDs.
- [x] **Merge Data**: Append unique new links to `posted_links.json`.

### TSK-B02-F: Fix Resolver Metadata & CLI

- [x] **Update Algolia Query**: Modify `hn_resolver.py` to request `title`, `created_at_i` (timestamp), and `author` (username) from Algolia APIs.
- [x] **Update DB Schema**: Ensure `urls` table has `title` (TEXT), `posted_at` (INTEGER/DATETIME), and `author` (TEXT) columns.
- [x] **Populate Data**: Update the update logic to save these fields.
- [x] **Fix CLI Stats**: Ensure the "Processed/Skipped/Failed" counters accurately reflect logic branches.

### TSK-F06: Display Metadata

- [x] **Update DB Query**: Modify `is-ai-good-yet/src/lib/server/db.ts` to select `title` and `posted_at`.
- [x] **Update Type Definitions**: Update TypeScript interfaces to include these new fields.
- [x] **Update Table Columns**: Add "Title", "Date", and "Author" columns to `content-table.svelte`.
- [x] **Format Date**: Display `posted_at` as "YYYY-MM-DD".
- [x] **Link to Details**: Replaced legacy 'preview' route with a new `details/[id]` route using the HN story ID.

### TSK-B03-TXT: Ground Truth Text Storage

- [x] **New Store Module**: Created `store/text_store.py` to handle read/write of structured `.txt` files.
- [x] **Modify Scraper**: Updated `scraper.py` to write to `pipeline/data/articles-text/` alongside Parquet.
- [x] **Rebuild Tool**: Created `src/rebuild_parquet.py` to regenerate Parquet shards from text files + SQLite metadata.

### TSK-B03-RETRY: Retry & Scraper Improvements

- [x] **Retry Logic**: Added `--retry-failed` flag to `scraper.py` to target failed URLs.
- [x] **Archive Fallback**: Implemented automatic fallback to `archive.is` (via `ArchiveScraper`) if Playwright fails or is blocked.
- [x] **Forced Domains**: Configured specific domains (e.g., NYT, WSJ) to always skip Playwright and use `archive.is`.
- [x] **Async Logic**: Updated `scraper.py` batch processor to handle fallback logic asynchronously.

### TSK-B03-FIX: Modernize Scraper (Deprecated)

- [x] **Replace Logic**: Swapped `playwright-stealth` for `camoufox` (Firefox-based stealth browser).
- [x] **Fix Imports**: Resolved `ImportError` by removing deprecated stealth module.
- [x] **Requirements**: Updated `requirements.txt` and installed `camoufox` binaries.
- **Note:** This approach was deprecated due to persistent stalling issues at 2% completion.

### TSK-B03-MODERN: Modernize Scraper (Playwright Best Practices 2025)

- [x] **Dependencies**: Removed `camoufox`, added `playwright-stealth` and `curl-cffi` to `requirements.txt`.
- [x] **Stealth Utilities**: Created `utils/stealth_utils.py` with:
  - Random user agent pool (12+ real browser signatures)
  - Random viewport selection (6 desktop resolutions)
  - Browser context options generator
  - Human-like timing function (2-8 sec delays, mouse movements)
  - Random scrolling simulator
- [x] **Proxy Management**: Created `utils/proxy_manager.py` with:
  - `ProxyRotator` class for proxy rotation
  - Environment variable configuration support
  - Proxy health tracking and failure reporting
  - Sequential and random rotation modes
- [x] **Database Schema**: Enhanced `store/db.py` with retry tracking:
  - Added `retry_count` column (INTEGER)
  - Added `last_retry_at` column (INTEGER)
  - Added `failure_category` column (TEXT)
  - Updated `update_scraped_status()` to track retry metadata
- [x] **Scraper Core**: Modernized `scraper.py`:
  - Replaced Camoufox with vanilla Playwright chromium
  - Applied `stealth_async` patches to mask automation signals
  - Implemented retry logic with exponential backoff (max 3 attempts)
  - Added human-like timing delays and mouse movements
  - Added random scrolling before extraction
  - Categorized failures (blocked, timeout, error, empty_content)
  - Integrated proxy rotation support
- [x] **CLI Enhancements**: Added new command-line flags:
  - `--use-proxy`: Enable proxy rotation
  - `--headful`: Run browser in headful mode
  - `--max-retries`: Configure retry attempts
- [x] **Environment Config**: Updated `.env.example` with proxy and scraper settings
- [x] **Documentation**: Updated `architecture.md`, `development.md`, and `tasks.md`

### TSK-B03-ARCHIVE: Interactive Archive.is Scraper (Manual CAPTCHA) — **Verify**

**Completed Work:**

- [x] **Problem Identified**: Archive.is behind Cloudflare protection returning 429 rate limits
- [x] **Interactive Script**: Created `src/archive_interactive.py` for manual CAPTCHA solving:
  - Headful browser stays open for user interaction
  - Detects Cloudflare challenge pages ("just a moment", "captcha")
  - Continues automatically after CAPTCHA is solved
- [x] **Search Results Handling**: Archive.is returns search page, script clicks first archive link
- [x] **Session Persistence**: Implemented storage state saving (`archive_session.json`) to remember CAPTCHA solutions.
- [x] **Scraper Integration**: Updated `scraper.py` (via `archive_scraper.py`) to:
  - Load the shared `archive_session.json`
  - **Crucial**: Force the same User-Agent as the interactive session to ensure Cloudflare cookies remain valid
- [x] **CLI Support**: Added "Interactive Archive Scraper" to the project CLI menu.

**Next Steps:**

- [x] **Validation**: Verified with user; batching works, CAPTCHA pauses work, and sessions persist.
- [x] **Maintenance**: Implemented continuous loop with resilient error handling and graceful interactive controls (Pause/Resume/Quit).

### TSK-B03-UNIFIED: Unified Scraper Fallback

- [x] **Unified Module**: Created `unified_scraper.py` (renamed to `scraper.py`) merging direct Playwright and Archive.is looping.
- [x] **Simplified Chain**: Removed Wayback Machine and Google Cache fallbacks (low success rate), strictly prioritizing `archive.is`.
- [x] **Session Validation**: Added startup check in interactive mode to navigate to `archive.ph` and force CAPTCHA solution before processing.
- [x] **Legacy Cleanup**: Deleted old `scraper.py` and `archive_interactive.py` modules.
- [x] **CLI Update**: Updated `cli.ts` to point to the simplified scraper and removed legacy options.
- [x] **Documentation**: Updated `architecture.md` and `usage.md` to reflect the new scraper flow.

### TSK-B03-FALLBACK: Improved Archive Fallback Chain & Retry Logic

**Problem:** The scraper was using Selenium exclusively for archive fallback, which is heavy and often blocked. Failed URLs were processed in predictable order, and lean mode had insufficient retry capability.

**Completed Work:**

- [x] **Randomized URL Selection**: Updated `get_urls_to_scrape()` in `store/db.py` to shuffle results by default, preventing predictable scraping patterns that trigger bot detection.
- [x] **Full Archive Fallback Chain**: Restored the multi-tier fallback in `archive_scraper.py`:
  1. **Wayback Machine** (fastest, no browser needed)
  2. **Google Cache** (fast, no browser needed)
  3. **archive.is with Playwright** (lighter than Selenium)
  4. **Selenium** (only if `--use-selenium` flag is passed)
- [x] **Selenium Made Optional**: Added `--use-selenium` CLI flag; Selenium is no longer used by default, reducing resource usage.
- [x] **Improved Lean Mode Settings**:
  - `LEAN_SCRAPE_TIMEOUT_MS`: 3000ms → 5000ms (more reasonable)
  - `LEAN_ARCHIVE_OP_TIMEOUT`: 5s → 20s (allows full fallback chain)
  - `LEAN_MAX_RETRIES`: 1 → 2 (actual retry capability)
- [x] **CLI Preset Modes**: Updated `cli.ts` with new scraper modes:
  - "Scrape New URLs" - Default, random order, Wayback/Playwright fallback
  - "Retry Failed URLs" - Re-scrape failed URLs with archive fallbacks
  - "Retry Failed + Selenium" - Heavy mode with Selenium as final fallback
  - "CAPTCHA Ready Mode" - Headful, interactive for manual solving
  - "Fast Mode" - High concurrency for bulk processing
- [x] **Console Output**: Added status messages showing which fallback mode is active.

**CLI Usage:**

```bash
# Default: Scrape new URLs with random order, no Selenium
python -m src.scraper -v --lean

# Retry failed with full fallback chain (no Selenium)
python -m src.scraper -v --lean --retry-failed

# Retry with Selenium as final resort (heavy)
python -m src.scraper -v --lean --retry-failed --use-selenium

# Via CLI menu
bun run cli  # Select "Phase 2: Scrape Content" → preset mode
```

### TSK-B04: Implement Content Prefilter (Post-Scrape - Phase 3)

**Note:** Content prefiltering runs AFTER scraping and cleaning. It analyzes actual article content (not just titles) for accurate classification.

#### Content Classification Categories

| Category       | Description                                                                    |
| :------------- | :----------------------------------------------------------------------------- |
| `AI_DISCOURSE` | Subjective views on AI coding workflows (copilots, LLM code gen, agentic dev)  |
| `AI_NEWS`      | Factual announcements about AI coding (product launches, features, benchmarks) |
| `AI_OTHER`     | About AI/ML but NOT about software development (AI art, AGI, regulation)       |
| `NOISE`        | Not about artificial intelligence                                              |

#### Completed Work

- [x] **Create `prefilter_content.py` module:** New content-based prefilter using refined prompts from `docs/refined_prompts.md`.
- [x] **Mistral API Integration:** Connect to Mistral API for content analysis (truncated to 6000 chars).
- [x] **Define 4-category classification:** AI_DISCOURSE, AI_NEWS, AI_OTHER, NOISE with confidence scores.
- [x] **DB Integration:** Added new columns `content_category`, `content_confidence`, `content_filter_json`.
- [x] **Processing Loop:** Batch processing of scraped articles with rate limiting and cost monitoring.
- [x] **CLI Filters:** Support for `--min-score` and `--min-comments` to match frontend view.
- [x] **Stats Mode:** Added `--stats` flag to display classification statistics.
- [x] **Graceful shutdown:** InteractiveSession support for pause/resume/quit.
- [x] **Cost tracking:** Token usage and estimated API cost reporting.

#### Frontend Integration

- [x] **Category badges:** Added color-coded badges (Fuchsia=Opinion, Cyan=News, Amber=AI Other, Zinc=Not AI).
- [x] **Category filter dropdown:** Added filter to show only specific categories.
- [x] **URL sync:** Category filter state synced with URL for bookmarking.
- [x] **Updated type definitions:** Added `content_category` and `content_confidence` to UrlEntry type.

#### CLI Integration

- [x] **Updated CLI menu:** Renamed to "Phase 3: Content Prefilter" with dedicated configuration.
- [x] **Preset modes:** "Run with defaults", "Filtered (score≥20, comments≥5)", and "Custom".
- [x] **Removed legacy prefilter:** Title-only prefilter removed from CLI (legacy code retained for reference).

### TSK-B03-CONSIST: Consistency Verification (Phase 2.7)

- [x] **Create `check_consistency.py` module:** Script to verify data consistency across storage layers.
- [x] **Phantom Detection:** Identify articles marked `scraped_status = 'success'` in DB but missing from parquet/text files.
- [x] **Orphan Detection:** Identify articles in parquet that aren't marked as success in DB.
- [x] **Auto-fix Mode:** Implement `--fix` flag to reset phantom articles to `pending` for re-scraping.

### TSK-B03-CLEAN: Article Text Data Cleaning

- [x] **Text Store Format Update:** Modified `store/text_store.py` to write simplified format (Title + URL only) with backward compatibility for reading both old and new formats.
- [x] **Cleaning Script:** Created `clean_articles.py` with extensible pattern registry for cleaning special characters (curly quotes, em dashes, multiple newlines).
- [x] **Backup Strategy:** Implemented automatic backup to `articles-text-backup/` folder with `--no-backup` flag option.
- [x] **Format Simplification:** Removed Author and Date fields from article headers, updated to Title + URL only format.
- [x] **CLI Interface:** Added progress bar and success messages with clean output.
- [x] **Short Line Removal:** Implemented detection and removal of short title-like lines isolated from context.

### TSK-B03-UPTACK: Ground-Truth Uptake

- [x] **Uptake Script:** Created `uptake_ground_truth.py` to synchronize database and parquet with current article text files.
- [x] **Deleted Article Detection:** Compare article-text files vs SQLite DB to identify articles that were deleted during cleaning.
- [x] **Database Reset:** Reset `scraped_status` to `NULL` for deleted articles so they can be re-scraped.
- [x] **Parquet Flush:** Delete all old parquet files before rebuilding from cleaned ground truth.
- [x] **Parquet Rebuild:** Call existing `rebuild_parquet.py` logic to regenerate parquet from cleaned text files.
- [x] **CLI Output:** Display counts of articles reset, parquet files deleted, and articles rebuilt with success messages.

### TSK-B05: Implement Sentiment Analyzer (Anthropic Claude)

**Completed Work:**

- [x] **Create `sentiment_analyzer.py` module:** New sentiment analysis module using Anthropic Claude Haiku 4.5 API.
- [x] **2-Dimension Analysis:** Implemented utility (positive/mixed/negative) and trajectory (optimistic/uncertain/pessimistic) dimensions.
- [x] **Score Derivation:** Formula: `score = (utility * 0.6) + (trajectory * 0.4)` producing -1 to +1 range.
- [x] **Additional Fields:** Extract subtopic, primary/secondary themes, summary (15 words), and 1-3 key quotes.
- [x] **API Integration:** Anthropic API with rate limiting (1 req/2 sec), cost tracking, and retry support.
- [x] **DB Integration:** Update `sentiment_score` (REAL) and `classification_json` (TEXT) columns.
- [x] **Interactive Controls:** InteractiveSession support for pause/resume/quit (q/p/r keys).
- [x] **CLI Arguments:** --reset, --reanalyze, --limit, --batch-size, --min-score, --min-comments, --stats, -v.
- [x] **CLI Menu Update:** Updated `cli.ts` with `configureSentimentAnalyzerArgs()` function and dedicated menu configuration.
- [x] **Environment Config:** Added `ANTHROPIC_API_KEY` to `.env.example`.
- [x] **Documentation:** Updated `architecture.md`, `usage.md`, and `tasks.md`.

### TSK-B06: Implement Export/API Logic

- [x] **Export Module Created:** `pipeline/src/export.py` generates static JSON files for frontend.
- [x] **Article Filtering:** Mirrors frontend logic (AI_DISCOURSE, hn_score≥20, excludes business topic).
- [x] **Rich Data Export:** Includes quotes, summary, topic, influenceScore for each article.
- [x] **Verdict Calculation:** Generates current verdict score and permanent record.
- [x] **Historical Snapshots:** Monthly verdict snapshots for history chart.
- [x] **CLI Integration:** Added "Phase 7: Export Data" to `cli.ts` with `configureExportArgs()`.
- [x] **Output Files:** Creates `articles.json`, `verdict.json`, `historical.json` in `is-ai-good-yet/src/lib/data/`.

### TSK-F03: Create "Verdict" View

- [x] **Component Design:** Created a Svelte component for the main "Verdict" using shadcn Card components.
- [x] **Aggregation Logic:** Implemented sentiment calculation and display logic.
- [x] **Integration:** Embedded the component in `+page.svelte` with proper styling.

### TSK-F04: Create Detailed Table View

- [x] **Enhance Table:** Updated table to use shadcn Table components with full functionality.
- [x] **Interactivity:** Added client-side sorting, filtering, and search capabilities.
- [x] **Pagination:** Implemented pagination using shadcn Pagination components.

### TSK-F05: Polish UI/UX

- [x] **Styling:** Applied consistent shadcn-svelte theme across all components.
- [x] **Responsive Design:** Ensured dashboard is responsive and mobile-friendly.
- [x] **Loading States:** Maintained existing loading states and animations.

### TSK-F07: Improve Pipeline Manager Table

- [x] **Opinion Column:** Updated to only show "Opinion" badge for filtered items.
- [x] **Status Column:** Added badges for "Failed", "Skipped", "Missing Metadata".
- [x] **Sentiment Column:** Implemented badges for Positive/Negative/Neutral/Unanalyzed.

### TSK-F08: Enhance Table Filters

- [x] **Filter Logic:** Updated `filteredItems` to check computed `displayStatus`.
- [x] **Dropdown:** Added "Failed", "Skipped", "Missing Metadata" to status options.

### TSK-F09: Display Source Domain

- [x] **Helper Function:** Added `getDomain` to extract hostname from URL.
- [x] **UI Update:** "Visit Source" link now includes `(example.com)`.

### TSK-F10: Fix Filters & Add Relevant Toggle

- [x] **Fixed getDisplayStatus:** Updated logic to properly detect scraped items by checking `scraped_status === "success"` after other status checks.
- [x] **Relevant Filter:** Added "Relevant Only" toggle that filters out non-article domains (GitHub, arXiv, Twitter, Reddit, YouTube, etc.).
- [x] **Irrelevant Domains List:** Created configurable list of 30+ domains that typically don't contain relevant sentiment analysis content.
- [x] **URL Sync:** Added `relevant` parameter to URL for bookmark/share support.
- [x] **UI Reorder:** Reorganized filter controls into two rows:
  - Row 1: Relevant toggle (pill badge), Status dropdown, Search
  - Row 2: Score threshold, Comments threshold, Items per page

### TSK-B05-REFINE: Refine Sentiment Analysis Prompt

- [x] **Prompt Restructure:** Made the prompt more concise and direct with clearer output format instructions.
- [x] **Rejection Criteria:** Added strict criteria to reject general AI/ML research, hardware news, business news, non-AI programming, and policy content.
- [x] **Documentation:** Updated `docs/sentiment_analysis_prompt.md` with refined prompt.

### TSK-B05-THEMES: Implement Theme Summarization (Phase 5)

- [x] **Theme Extractor Module:** Created theme synthesis pipeline that groups articles by sentiment.
- [x] **Database Migration:** Added `themes` table with `sentiment_group`, `theme_title`, `theme_description`, `sentiment_verdict`, `article_count` fields.
- [x] **Rejection Logic:** Filter out articles that don't focus on AI coding workflows.
- [x] **Cost Tracking:** Token usage and API cost reporting.

### TSK-B05-RECLASS: Reclassification Utility

- [x] **Category Migration:** Tool to move articles from OPINION_CODING to AI_OTHER after deeper analysis reveals irrelevance.
- [x] **Batch Processing:** Process multiple articles efficiently with progress tracking.

### TSK-B05-SENTIMENT-REWORK: Sentiment Prompt Rework

- [x] **New Prompt Structure:** Replaced old utility scale (magic/tool/noise/toil/hazard) with clearer positive/mixed/negative values.
- [x] **New Trajectory Values:** Replaced accelerating/stable/decelerating with optimistic/uncertain/pessimistic.
- [x] **Subtopic Classification:** Added autocomplete/chat/agentic/tooling/general subtopics for categorizing AI coding discussions.
- [x] **Theme Classification:** Added 9 theme categories (productivity, correctness, trust, skills, jobs, adoption, hype, workflow, autonomy).
- [x] **Summary Field:** Added 15-word summary field replacing reality_check field.
- [x] **Prompt Sync:** Updated `classifier.py` (lines 64-148) and `get_analysis_prompts.py` (lines 121-205) with identical prompts.
- [x] **Documentation:** Updated `docs_internal/prompt_sync.md` with new line references and marked prompts as requiring sync.

### TSK-F11: Implement Timeline Chart

- [x] **Data Query:** Backend query filters to analyzed articles only (score≥20, comments≥5, OPINION_CODING, scraped).
- [x] **Weekly Aggregation:** Group articles by week with sentiment counts.
- [x] **Stacked Bar Chart:** Positive/neutral/negative bars using d3-shape.
- [x] **Styling:** Week labels styled smaller (xs), proper y-axis scaling.
- [x] **Dependencies:** Added `@types/d3-shape` for TypeScript support.

### TSK-F12: Dynamic Topics Section

- [x] **Database Integration:** Fetch themes from `themes` table via `+page.server.ts`.
- [x] **Sentiment Grouping:** Separate columns for positive, neutral, and negative themes.
- [x] **Icon Selection:** Sentiment-appropriate icons (Sparkles, Scale, AlertTriangle).
- [x] **Responsive Layout:** Two-column grid with proper spacing.
- [x] **Fallback:** Static content displayed when themes unavailable.

### TSK-F13: Article Details Analysis Display

- [x] **Analysis Section:** New card showing utility, trajectory, subtopic, themes.
- [x] **Color-coded Badges:** Sentiment values displayed with appropriate colors.
- [x] **Summary Display:** 15-word summary prominently shown.
- [x] **Key Quotes:** 1-3 supporting quotes in styled blockquote format.
- [x] **Type Updates:** Added `classification_json` to `UrlWithAnalysis` type.

### TSK-F14: Migrate CSS to Tailwind

- [x] **Section Components:** Migrated header, footer, hero, methodology, timeline, topics, verdict from custom CSS.
- [x] **Table Refactor:** Changed from HTML table to flexbox-based layout.
- [x] **ARIA Attributes:** Added accessibility improvements.
- [x] **Prettier Config:** Added `.prettierrc` with project standards.

### TSK-F15: Category Filter & Badges

- [x] **Filter Dropdown:** Added category selection to content table filters.
- [x] **Badge Colors:** OPINION_CODING=Fuchsia, NEWS_CODING=Cyan, AI_OTHER=Amber, NOT_AI=Zinc.
- [x] **URL Sync:** Category filter state synced with URL parameters.
- [x] **Type Definitions:** Added `content_category` and `content_confidence` to `UrlEntry` type.

### TSK-F16: Standardize Container Widths

- [x] **Layout Audit:** Reviewed all section components for width inconsistencies.
- [x] **Container Cleanup:** Removed nested container wrappers.
- [x] **Consistent Styling:** Applied `max-w-5xl` (64rem) with consistent padding.
- [x] **Typography:** Adjusted font sizes for better mobile responsiveness.

### TSK-F17: Refine Table Theme Styling

- [x] **Badge Refactor:** Migrated from CSS variables to Tailwind color utilities.
- [x] **Light/Dark Mode:** Proper color contrast in both themes.
- [x] **Responsive Columns:** Opinion and Status columns hidden on small viewports.
- [x] **CSS Cleanup:** Removed ghost/unused CSS selectors.

### TSK-F18: Landing Veil Component

- [x] **Veil Component:** Created `landing/veil.svelte` with full-viewport overlay.
- [x] **Title/Tagline:** "Is AI Good Yet?" with "According to Hacker News" tagline.
- [x] **Reveal Button:** "show me" button triggers fade-out animation.
- [x] **localStorage Persistence:** Stores `isai_revealed` to skip veil on return visits.
- [x] **Animation:** 300ms ease-out opacity transition.

### TSK-F19: Verdict Display Component

- [x] **Verdict Display:** Created `landing/verdict-display.svelte` with large YES/NO/NOT YET text.
- [x] **Color Coding:** Green for YES, red for NO, amber for NOT YET.
- [x] **Score Display:** Shows numeric score below verdict.
- [x] **Responsive Typography:** Uses clamp() for viewport-responsive sizing.

### TSK-F20: History Chart Component

- [x] **Line Chart:** Created `landing/history-chart.svelte` with pure SVG.
- [x] **Threshold Lines:** Dashed lines at 45 (NO) and 55 (YES) boundaries.
- [x] **Background Regions:** Shaded zones for YES (green), NOT YET (amber), NO (red).
- [x] **Hover Tooltip:** Shows month, score, verdict, and article count on hover.
- [x] **Data Points:** Colored circles based on verdict at each month.
- [x] **Month Labels:** Shows month labels (Jan '24 format) at intervals.

### TSK-F21: Stats Bar Component

- [x] **Stats Bar:** Created `landing/stats-bar.svelte` with one-line display.
- [x] **Three Stats:** "now X", "all-time Y", "Z articles".
- [x] **Separator Dots:** Visual separators between stats.
- [x] **Monospace Font:** Uses mono font for numeric values.

### TSK-F22: Historical Verdict Snapshots (Data Layer)

- [x] **New Function:** Added `getHistoricalVerdictSnapshots()` to `db.ts`.
- [x] **Point-in-Time Calculation:** For each month, calculates what verdict would have been at that time.
- [x] **13-Month Window:** Applies same decay formula as current verdict, but from historical perspective.
- [x] **Type Definition:** `HistoricalSnapshot` with month, verdictScore, verdict, articleCount, rawSentiment.

### TSK-F23: Permanent Record Score (Data Layer)

- [x] **New Function:** Added `getPermanentRecordScore()` to `db.ts`.
- [x] **No Time Decay:** Calculates all-time average weighted only by upvotes.
- [x] **Type Definition:** `PermanentRecord` with score, verdict, totalArticles, counts.

### TSK-F24: Homepage Rewrite

- [x] **Page Rewrite:** Replaced entire `+page.svelte` with new minimal structure.
- [x] **New Components:** Veil, VerdictDisplay, StatsBar, HistoryChart, ArticleCounts, MinimalFooter.
- [x] **Removed:** Hero, Methodology, Topics, old Timeline, old Verdict sections.
- [x] **Server Data:** Updated `+page.server.ts` to load historicalSnapshots and permanentRecord.

### TSK-F25: Remove /verdict Route

- [x] **Route Deleted:** Removed entire `/routes/verdict/` directory.
- [x] **Content Consolidated:** All verdict functionality now on homepage.

### TSK-F26: Cleanup Unused Components

- [x] **Removed Components:** Deleted hero.svelte, methodology.svelte, timeline.svelte, topics.svelte, verdict.svelte.
- [x] **Layout Update:** Modified `+layout.svelte` to hide header/footer on homepage.
- [x] **Kept Components:** Retained header.svelte and footer.svelte for other pages.

### TSK-F27: Copy Rewrite (Human Voice)

- [x] **Veil Copy:** Simple "Is AI Good Yet?" / "According to Hacker News" / "show me".
- [x] **Footer Copy:** Two plain sentences about data source and methodology.
- [x] **No Jargon:** Removed "Forgetful Critic", "decay factor", and methodology explanations.

### TSK-F28: V4.0 Schema Backward Compatibility

**Problem Identified:**
- v4.0 architecture overhaul changed classification_json schema from v3 (subtopic/primary_theme/secondary_theme) to v4 (single topic field)
- 340 articles (33% of total) analyzed with old schema were being excluded from verdict calculations
- WHERE clauses in 8 database queries checked for `topic` field which didn't exist in old articles
- Specific example: Article 45465098 ("Be Worried", sentiment: -2.0, HN score: 106) was excluded despite being highly relevant

**Implementation:**
- [x] **Root Cause Analysis:** Identified 8 WHERE clauses in `db.ts` using `json_extract(classification_json, '$.topic')` that failed for old schema articles
- [x] **Backward-Compatible SQL:** Updated all 8 WHERE clauses to check both new (`$.topic`) and old (`$.subtopic`) schema fields:
  ```sql
  AND (
    -- New schema (v4.0+): exclude if topic = 'business'
    (json_extract(classification_json, '$.topic') IS NOT NULL AND json_extract(classification_json, '$.topic') != 'business')
    OR
    -- Old schema (v3): exclude if subtopic = 'business'
    (json_extract(classification_json, '$.topic') IS NULL AND json_extract(classification_json, '$.subtopic') IS NOT NULL AND json_extract(classification_json, '$.subtopic') != 'business')
    OR
    -- No classification JSON yet
    classification_json IS NULL
  )
  ```
- [x] **Type Updates:** Updated `SentimentAnalysis` type to include optional legacy fields (subtopic, primary_theme, secondary_theme)
- [x] **Schema Normalization:** Created `normalizeAnalysis()` helper function to convert old schema to new schema on read:
  - If article has `topic` field → use as-is
  - If article has `subtopic` but no `topic` → map `subtopic` to `topic`
  - Fall back to `primary_theme` if neither exists
- [x] **Frontend Integration:** Updated `extractTopic()` helper and `getUrlWithAnalysis()` function to use normalization
- [x] **Summaries Fix:** Updated `getSummariesList()` to normalize classification JSON before extracting topic field

**Results:**
- Before fix: 678 articles included in verdict (340 excluded)
- After fix: 939 articles included in verdict (only 79 business articles correctly excluded)
- All 340 old-schema articles now properly included in verdict calculations
- Article 45465098 now displays correctly with topic="society" (mapped from subtopic)

**Files Modified:**
- `is-ai-good-yet/src/lib/server/db.ts` (lines 67, 211, 347-357, 363-392, 419-430, 627, 664, 922, 1095, 1187, 1331)
  - 8 WHERE clause updates
  - Added normalizeAnalysis() helper
  - Updated SentimentAnalysis type
  - Updated getUrlWithAnalysis() and getSummariesList()

### TSK-F29: Diagnostic & Verification Tools

- [x] **Schema Migration Diagnostic:** Created `is-ai-good-yet/scripts/diagnose-schema-migration.ts`
  - Counts total AI_DISCOURSE articles vs. included articles
  - Identifies articles with old schema (subtopic) vs. new schema (topic)
  - Shows sample old-schema articles with high HN scores
  - Checks specific article (45465098) classification status
- [x] **Fix Verification:** Created `is-ai-good-yet/scripts/verify-fix.ts`
  - Validates backward-compatible WHERE clause works correctly
  - Confirms business articles are properly excluded in both schemas
  - Verifies specific article now passes filter
  - Shows final tally: 1018 total → 79 business excluded → 939 included ✓
- [x] **Article Display Test:** Created `is-ai-good-yet/scripts/test-article-display.ts`
  - Tests that old-schema articles load correctly through server-side data loading
  - Verifies topic field is populated from subtopic via normalization
  - Confirms analysis data displays correctly on frontend

## Additional Resources

For detailed troubleshooting information, see [troubleshooting.md](troubleshooting.md).
