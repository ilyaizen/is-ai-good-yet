# Architecture & Data Flow

## Table of Contents

1. [System Design](#system-design)
2. [Frontend Architecture](#frontend-architecture)
3. [E2E Pipelines](#e2e-pipelines)
4. [Pipeline Phases](#pipeline-phases)
5. [Verdict Scoring](#verdict-scoring)
6. [Database Schema](#database-schema)

---

## System Design

The system uses a **Linear Phase Pipeline** architecture. It is designed to be interruptible and resumable. It supports both **fresh full-database scrapes** (see [Initial E2E Pipeline](#initial-e2e-pipeline-fresh-start)) and **incremental updates** (see [Catch-Up E2E Pipeline](#catch-up-e2e-pipeline-incremental)).

### Core Philosophy: Split Storage

To ensure performance and maintainability, data is split between:

1. **SQLite (`pipeline/data/pipeline.db`)**: Mutable metadata (status flags, HN scores, computed sentiment scores). Fast relational queries.
2. **Parquet (`pipeline/data/articles/*.parquet`)**: Canonical scraped article content. Columnar storage using `zstd` compression.

Legacy plain-text copies remain in `pipeline/data/articles-text/` and
`pipeline/data/articles-text-backup/` for recovery, but new scrapes do not write them and exports do
not use their presence as a curation signal.

### Directory Structure

```text
is-ai-good-yet/                # repo root = SvelteKit frontend (PRODUCTION)
├── src/
│   ├── lib/
│   │   ├── components/      # landing/ + ui/ (shadcn-svelte)
│   │   ├── composables/     # Svelte 5 composables
│   │   ├── data/            # Static JSON files (exported from pipeline)
│   │   ├── server/          # Server utilities (db.ts — dev admin only)
│   │   ├── convex/          # Convex visitor-counter client
│   │   ├── types/
│   │   ├── static-data.ts   # Static JSON loader (production)
│   │   └── constants.ts, version.ts, utils.ts
│   ├── routes/
│   │   ├── +page.svelte     # Landing page (static data)
│   │   ├── details/[id]/    # Article details (static data)
│   │   ├── admin/           # Admin / pipeline-control (dev-only, SQLite)
│   │   ├── api/             # API routes
│   │   └── v2/, lab/
│   └── styles/              # tokens.css (design tokens), terminal.css, base.css, ...
├── pipeline/                # Python data pipeline
│   ├── src/                 # Pipeline phase modules
│   ├── data/                # SQLite, parquet, text files (gitignored)
│   └── requirements.txt
├── convex/                  # Convex visitor-counter backend
├── docs_internal/           # Operational docs (this directory)
├── docs/                    # Public docs
├── scripts/                 # tsx helper scripts
├── static/                  # favicon, OG images
├── cli.ts                   # Pipeline CLI wrapper
├── nixpacks.toml            # Coolify deployment config (Node 22.18)
└── package.json
```

---

## Frontend Architecture

### Data Access Model: Static vs. Development

The frontend uses a **dual data access model**:

| Mode                         | Data Source       | Module           | Routes                         |
| :--------------------------- | :---------------- | :--------------- | :----------------------------- |
| **Production** (static host) | Static JSON files | `static-data.ts` | `/`, `/details/[id]`, `/api/*` |
| **Development** (local)      | SQLite database   | `db.ts`          | `/admin` only                  |

#### Production Data Flow

```text
Pipeline (Python)                    Frontend (SvelteKit)
     │                                     │
     │  export.py                          │
     ▼                                     │
┌─────────────────────┐                    │
│  pipeline/data/     │                    │
│  pipeline.db        │                    │
└─────────┬───────────┘                    │
          │                                │
          │  python -m src.export          │
          ▼                                │
┌─────────────────────────────────────┐    │
│  src/lib/data/                      │    │
│  ├── articles.json   (987KB)        │◄───┤ Imported by
│  ├── verdict.json    (656B)         │    │ static-data.ts
│  ├── historical.json (5.0KB)        │    │
│  ├── weekly.json     (56KB)         │    │
│  ├── themes.json     (9.5KB)        │    │
│  └── llm-metrics.json (1.8MB)       │    │
└─────────────────────────────────────┘    │
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │  Static Build (Coolify)│
                              │  (No SQLite access)    │
                              └────────────────────────┘
```

**Key Insight:** The production frontend is **completely static**. It never queries SQLite. All data is pre-computed by `export.py` and embedded as JSON files at build time.

#### Development Data Flow (Pipeline Admin Only)

```text
┌─────────────────────┐
│  pipeline/data/     │
│  pipeline.db        │
└─────────┬───────────┘
          │
          │  better-sqlite3
          │  (direct import)
          ▼
┌─────────────────────────────────────┐
│  src/lib/server/     │
│  db.ts (1,812 lines)                │
│  └── getPipelineTableData()         │
│  └── getPipelineStats()             │
└─────────────────────────────────────┘
          │
          │  Only used by:
          ▼
┌─────────────────────────────────────┐
│  /admin route                       │
│  (blocked in production via guard)  │
└─────────────────────────────────────┘
```

### Static Data Files

| File               | Contents                                                                           | Size   |
| :----------------- | :--------------------------------------------------------------------------------- | :----- |
| `articles.json`    | All AI_DISCOURSE articles with quotes, summary, topic, sentiment scores, influence | ~987KB |
| `verdict.json`     | Current verdict (12-month window) + permanent record (all-time) + counts           | ~656B  |
| `historical.json`  | Monthly verdict snapshots for history chart                                        | ~5.0KB |
| `weekly.json`      | Weekly rolling window snapshots with contribution breakdown                        | ~56KB  |
| `themes.json`      | Synthesized themes grouped by sentiment                                            | ~9.5KB |
| `llm-metrics.json` | LLM response data with speed metrics (keyed by hn_id)                              | ~1.8MB |

### Admin Route

The `/admin` route provides a development-only interface to inspect the raw pipeline data in SQLite.

**Access Control:**

- **Production:** Returns 404 (route guard blocks access)
- **Development:** Full access to live SQLite data

**Why it exists:** When running the pipeline locally, you need visibility into:

- Which URLs are pending, scraped, failed
- Content classification status
- Sentiment analysis coverage

---

## E2E Pipelines

### Initial E2E Pipeline (Fresh Start)

- **Goal:** Full database scrape for initial setup or disaster recovery.
- **Primary Module:** `initial_e2e.py`
- **Concurrency:** High (200-400 tabs)
- **Strategy:** Two-pass scraping (Headless → Headful Retry)

#### CLI Usage

```bash
python -m src.initial_e2e -v -c 200            # Balanced (200 tabs)
python -m src.initial_e2e -v -c 400 --use-proxy # Aggressive (400 tabs + proxy)
```

### Catch-Up E2E Pipeline (Incremental)

- **Goal:** End-to-end processing for recent articles in a single automated run.
- **Primary Module:** `catch_up.py`
- **When to Run:** Daily or weekly to keep data current with recent Hacker News discussions.
- **Strategy:** Sequential execution of phases 2 through 7 for recent content.

#### Automated Sequence

The catch-up pipeline runs phases in sequence:

1. **Backfill Histre** (Phase 2) - Scrape recent pages (default: 5)
2. **Resolve HN Links** (Phase 3) - Query Algolia for new URLs
3. **Scrape Content** (Phase 4) - Fetch article text for NEW URLs only (not retrying failures)
4. **Content Prefilter** (Phase 5) - Classify with Groq API
5. **Sentiment Analysis** (Phase 6) - Score with Groq API
6. **Export to Frontend** (Phase 7) - Generate static JSON for production deployment

> **Scraping Behavior:** The catch-up pipeline does NOT retry previously failed URLs to avoid wasteful retries of known-broken pages. To retry failures, use the standalone scraper with `--retry-failed`.

#### CLI Usage

```bash
cd pipeline
python -m src.catch_up -v                  # Quick update (5 pages)
python -m src.catch_up -v --pages 10       # Standard update (10 pages)
python -m src.catch_up -v --pages 25       # Deep backfill (25 pages)
python -m src.catch_up --dry-run           # Show what would run
python -m src.catch_up --skip-scrape       # Skip scraping phase
python -m src.catch_up --skip-analyze      # Skip prefilter + sentiment
```

#### Error Handling

- Continues on errors (logs failures, proceeds to next phase)
- Shows summary between phases with 2-second pause
- Displays final summary with success/failure per phase
- Graceful Ctrl+C handling (finishes current phase, then stops)

---

## Pipeline Phases

### Phase 2: Ingestion & HN Resolution

#### Histre Backfill

- **Primary Module:** `backfill_histre.py`
- **Input:** Histre.com pages (configurable range, default 1-10)
- **Output:** `pipeline/data/histre_feed.json` with discovered URLs

#### Algolia Discovery (supplementary)

- **Primary Module:** `algolia_discover.py`
- **Goal:** Find AI-related stories missed by Histre by querying Algolia directly
- **Input:** Algolia HN API (`search_by_date`)
- **Output:** Insert discovered URLs directly into SQLite `urls` table

### Phase 3: HN Resolution

- **Primary Module:** `hn_resolver.py`
- **Input:** `pipeline/data/histre_feed.json`
- **Goal:** Resolve raw URLs to their most impactful Hacker News appearance.
- **Logic:** Query Algolia API with the URL.
- **Deduplication:** If a URL appears in multiple HN threads, identify the `objectID` with the highest score/comment count.
- **Output:** Populate `urls` table in SQLite with `hn_id`, `hn_score`, `hn_comments`, and `hn_timestamp`.

#### Update Recent Mode

Recent articles continue to accumulate votes and comments on HN. Use `--update-recent` to refresh metadata:

```bash
cd pipeline
python -m src.hn_resolver --update-recent -v           # Refresh last 30 days (default)
python -m src.hn_resolver --update-recent --recent-days 7 -v  # Refresh last 7 days
```

### Phase 4: Content Scraping

- **Goal:** Robust HTML retrieval with modern bot evasion.
- **Primary Module:** `scraper.py`

#### Unified Scraper Architecture

The scraper (`src/scraper.py`) combines direct scraping with an archive.is fallback:

```text
┌─────────────────────────────────────────────────────────────────┐
│                           SCRAPER                               │
├─────────────────────────────────────────────────────────────────┤
│  1. Direct Playwright Access (with stealth)                     │
│     └─► If blocked/failed/timeout                               │
│  2. Archive Fallback Chain                                      │
│     ├─► Tier 1: Archive.is (Playwright + stealth)               │
│     └─► Tier 2: Archive.is (Selenium/undetected-chromedriver)   │
│         └─► If all automated methods fail AND interactive mode  │
│  3. Interactive Archive Session (Optional)                      │
│     └─► Manual CAPTCHA solving with session persistence         │
└─────────────────────────────────────────────────────────────────┘
```

#### Fallback Strategy Details

1. **Direct Access:** Vanilla Playwright (Chromium) + playwright-stealth patches + human-like timing.
   - **Stealth Patches:** Masks automation signals (webdriver, navigator properties, canvas fingerprints)
   - **Timing Patterns:** Random delays (2-8 sec), mouse movements, scrolling simulation
   - **Fingerprint Randomization:** Rotates user agents, viewports, language settings
   - **Residential Proxies (Optional):** Rotate real IPs to avoid datacenter blocks
   - **Early Exit:** If extraction fails with bad content patterns (e.g., "enable javascript"), immediately falls back to archive (no retries)

2. **Retry Logic:** Network/timeout retries only (max 3 attempts per URL)
   - Does NOT retry on extraction failures (e.g., bad patterns detected)
   - Proceeds to archive fallback if content extraction yields no valid text

3. **Automated Archive Fallback Chain:** If Direct Access fails (Block/403/429/extraction failure):
   - **Tier 1: Archive.is (Playwright)** - With stealth patches
   - **Tier 2: Archive.is (Selenium)** - `undetected-chromedriver` for Cloudflare bypass
   - **Rate Limit Handling:** If archive.is returns 429, URL is marked as "archive_rate_limited" and skipped (no retries in same session)

4. **Interactive Archive Session (Optional):** When `--interactive` flag is used:
   - Opens a persistent browser window for manual CAPTCHA solving
   - Saves session cookies to `pipeline/data/archive_session.json`
   - Subsequent runs can reuse the session for automated archive.is access
   - Best for processing URLs that consistently fail due to Cloudflare protection
   - NOT attempted for extraction failures (where content isn't actually available)

5. **Forced Overrides:** Specific domains (e.g. `nytimes.com`, `wsj.com`) bypass Direct Access and use the fallback chain immediately.

#### Anti-Bot Measures

- `playwright-stealth`: Evasion patches for Playwright automation detection
- **User Agent Pool:** 12+ real browser signatures (Chrome, Firefox, Edge, Mobile)
- **Viewport Randomization:** 6 common desktop resolutions
- **Human-like Timing:** Random delays, mouse movements, scroll patterns
- **Proxy Support:** Optional residential proxy rotation via environment config
- **Headful Mode:** Occasional headful runs for heavily protected sites
- **Session Persistence:** Archive.is cookies saved between runs

#### CLI Usage

```bash
# Recommended: Scraper with all fallbacks
vp run pipeline:scrape        # or: cd pipeline && python -m src.scraper

# Or run directly:
python -m src.scraper                    # Default automated mode
python -m src.scraper --interactive      # With CAPTCHA solving
python -m src.scraper --retry-failed     # Retry previously failed URLs
```

#### Output

Append extracted article content and metadata to compressed Parquet shards in
`pipeline/data/articles/`. SQLite is marked successful only after the Parquet buffer flushes.

### Legacy Text Recovery Utilities

- **Goal:** Recover or inspect article data written before Parquet became canonical.
- **Primary Modules:** `clean_articles.py`, `uptake_ground_truth.py`
- **When to Run:** Only when deliberately restoring the legacy plain-text dataset.

These utilities are no longer part of the active scrape or catch-up pipeline. In particular,
`uptake_ground_truth.py` replaces canonical Parquet shards from legacy text files and should not be
used as a routine synchronization step.

#### Data Cleaning Script (`clean_articles.py`)

**Features:**

- **Incremental mode (default in catch-up):** Only process files added since last clean run
  - Uses `pipeline/data/last_clean_timestamp.json` to track last clean time
  - Dramatically speeds up catch-up runs (seconds instead of minutes)
- **Configurable cleaning patterns** (extensible for future additions):
  - Curly quotes (`"`, `"`, `'`, `'`) → straight quotes (`"`, `'`)
  - Em dashes (`—`) and en dashes (`–`) → regular dash (`-`)
  - Multiple consecutive newlines (`\n\n\n+`) → double newline (`\n\n`)
  - Short standalone title-like lines (4-15 words followed by `\n`, isolated from context)
- **Preserve emojis**: Use Unicode range filtering to keep emoji characters
- **Backup strategy**: Create `pipeline/data/articles-text-backup/` folder and copy originals before cleaning
- **Format simplification**: Remove unused Author/Date fields from article headers
- **CLI output**: Progress bar for cleaning process with success message

**Usage:**

```bash
cd pipeline
python src/clean_articles.py --new-only     # Only clean new files (fast, for catch-up)
python src/clean_articles.py --clean-all    # Clean all article files (full run)
python src/clean_articles.py                # Auto-detect based on timestamp
```

#### Ground-Truth Uptake Script (`uptake_ground_truth.py`)

**Purpose**: Synchronize database and parquet with the current state of article-text files (ground truth)

**Features:**

- **Identify deleted articles**: Compare article-text files vs SQLite DB
  - Get all `hn_id` values where `scraped_status = 'success'` from DB
  - Check which ones no longer have corresponding `.txt` files
  - Reset their `scraped_status` to `NULL` so they can be scraped again
- **Flush old parquet data**: Delete all `pipeline/data/articles/*.parquet` files
- **Rebuild parquet from ground truth**: Call existing `rebuild_parquet.py` logic
- **CLI output**: Count of articles marked for re-scraping, parquet files deleted, and articles rebuilt

**Usage:**

```bash
cd pipeline
python src/uptake_ground_truth.py         # Sync database and parquet with cleaned ground truth
```

### Phase 4.7: Consistency Verification

- **Goal:** Verify data consistency across all storage layers before proceeding to analysis.
- **Primary Module:** `check_consistency.py`
- **When to Run:** After Phase 4.5 uptake, or any time you suspect data inconsistency.

#### Consistency Check Script (`check_consistency.py`)

**Purpose:** Detect and optionally fix phantom articles (DB says success but content missing) and orphans (content exists but DB doesn't reflect it).

**Features:**

- **Phantom Detection**: Find articles marked `scraped_status = 'success'` in DB but missing from parquet/text files
- **Orphan Detection**: Find articles in parquet that aren't marked as success in DB
- **Auto-fix Mode**: Use `--fix` flag to reset phantom articles to `pending` for re-scraping

**Usage:**

```bash
cd pipeline
python src/check_consistency.py           # Check for inconsistencies
python src/check_consistency.py --fix     # Fix phantom articles by resetting status
```

### Phase 5: Content Pre-filtering (Post-Scrape)

- **Goal:** Strictly classify scraped articles to include ONLY developer experiences/opinions about AI coding tools.
- **Primary Module:** `prefilter_content.py`
- **When to Run:** After scraping and cleaning are complete. Uses Groq API (llama-3.1-8b-instant).
- **Why Post-Scrape:** Analyzing actual article content provides much more accurate classification than title-only analysis.
- **Streaming:** Token-by-token output in verbose mode for real-time feedback.

#### Content Classification Categories (v4.0 - Strict)

| Category       | Include in Verdict? | Description                                                                               |
| :------------- | :------------------ | :---------------------------------------------------------------------------------------- |
| `AI_DISCOURSE` | Yes                 | First-person developer experience OR substantive analysis with clear opinion on AI coding |
| `AI_NEWS`      | No                  | Product announcements, launches, funding, benchmarks without author experience/opinion    |
| `AI_OTHER`     | No                  | Tutorials, courses, research papers, non-coding AI (audio/image), AGI philosophy          |
| `NOISE`        | No                  | Standard tech news without an AI angle (pure React updates, crypto)                       |

#### Key Filtering Rules

1. Product announcements → `AI_NEWS` (not AI_DISCOURSE, even if about coding tools)
2. Educational content (courses, tutorials, books) → `AI_OTHER`
3. AI_DISCOURSE requires AUTHOR OPINION or PERSONAL EXPERIENCE - topic relevance alone is NOT enough
4. When uncertain between AI_DISCOURSE and AI_NEWS → choose AI_NEWS (be conservative)

#### Golden Examples

| Title                                                   | Category       | Reasoning                                  |
| :------------------------------------------------------ | :------------- | :----------------------------------------- |
| "I Used Cursor for 3 Months - Here's My Verdict"        | `AI_DISCOURSE` | First-person experience with conclusion    |
| "Windsurf Codemaps: Understand Code Before You Vibe It" | `AI_NEWS`      | Product marketing, no developer experience |
| "Neural Networks: Zero to Hero"                         | `AI_OTHER`     | Educational course, not opinion            |
| "Our New SAM Audio Model Transforms Audio Editing"      | `AI_OTHER`     | Non-coding AI (audio)                      |
| "Postgres 17 Released"                                  | `NOISE`        | Database news, no AI component             |

#### Pre-filter Logic

- **Input:** Articles with `scraped_status = 'success'` that haven't been content-filtered
- **Truncation:** Head+tail (60% opening + 40% closing) with `[… middle section omitted …]` separator, max 8000 chars
- **Processing:** Groq API (llama-3.1-8b-instant) analyzes truncated content with streaming output
- **Output:** Update `content_category`, `content_confidence`, and `content_filter_json` columns in SQLite

**Usage:**

```bash
cd pipeline
python -m src.prefilter_content -v                          # Run with streaming output (recommended)
python -m src.prefilter_content -v --reset                  # Reset and re-filter all articles
python -m src.prefilter_content --reset-only                # Clear filter data and exit
python -m src.prefilter_content --stats                     # Show classification stats
```

### V2 Two-Tier Sentiment Analysis

V2 is additive and does not modify the v1 `sentiment_score`, `classification_json`, or static JSON
contracts. It stores source data and analyses in separate `hn_*` and `v2_*` tables and exports to
`src/lib/data/v2/`.

The normative prompt and methodology contract is
[`docs/v2-sentiment-prompt.md`](../docs/v2-sentiment-prompt.md).

1. `hn_comments_v2.py` preserves every parent's public ranked `kids` order, local sibling rank,
   ancestry, and snapshot time. Adaptive sampling targets 12–32 accepted comments with deterministic
   top-level/branch waves, author and branch caps, and refill after rejection or non-addressing.
2. Account karma is absent from v2.2 selection, prompts, annotation, aggregation, confidence, and
   export. Public sibling rank is an ordinal visibility signal, not a reconstruction of private votes.
3. `sentiment_v2.py` analyzes the article independently and sends one isolated request per voting
   comment. Structured article thesis/evidence, immediate parent, and distinct root are context-only;
   only the voting comment receives an annotation.
4. Absolute AI stance, article relation, and parent relation remain separate. Only applicable
   absolute stances enter per-dimension aggregation. Missing dimensions are `not_addressed`, not zero.
5. Community aggregation produces a primary visibility-weighted estimate and a diversity-balanced
   diagnostic. It exports ranking sensitivity, direction shares, disagreement, polarization, ESS,
   coverage/counts, clarity, and per-dimension dissent. Disagreement and sentiment direction or
   magnitude never reduce measurement confidence.
6. `export_v2.py` starts from 40% article and 60% community priors. Per-dimension source confidence
   changes effective influence without changing a source's sentiment or pulling it toward neutral.
7. Prompt, input, contract, parser, selection, and aggregation versions or hashes are persisted for
   reproducibility. Article and community runs are saved independently, including valid rejections.

The estimand is visible expressed HN discussion at collection time, not silent readers, all HN users,
or public opinion. Story comment volume may enlarge the sample but does not directly affect sentiment
or global influence; existing story score/time decay remains the engagement signal. The three
dimension verdicts are primary. The equal-weight composite is a secondary summary.
The `/v2` route remains on its existing static data until this contract has reviewed initial data.

### Phase 6: Sentiment Analysis

- **Goal:** 2-dimension sentiment analysis for AI coding workflow content with explicit rejection.
- **Engine:** Groq API with `openai/gpt-oss-20b` model (fast streaming inference).
- **Primary Module:** `sentiment_analyzer.py`
- **Prompt Source:** `pipeline/src/sentiment_analyzer.py` (`SENTIMENT_SYSTEM_PROMPT`)
- **Target Articles:** `content_category = 'AI_DISCOURSE'` only (AI_NEWS excluded) with `hn_score >= 20` and `hn_comments >= 5`.
- **Truncation Strategy:** Head+tail (40% intro + 60% conclusion) with `[… middle section omitted …]` separator.
- **Two-Layer Defense:** Analyzer can reject articles back to AI_OTHER if they lack developer opinion.

#### 2-Dimension Analysis Approach (v4.0 - Simplified)

**Utility (Is it useful NOW?)** - 5-tier scale evaluating current practical value:

| Value    | Meaning                   | Score | Signals                                        |
| :------- | :------------------------ | :---- | :--------------------------------------------- |
| `magic`  | Game-changer              | +2.0  | "Can't imagine going back", "10x productivity" |
| `tool`   | Net positive with caveats | +1.0  | "Saves time but needs oversight"               |
| `mixed`  | Genuinely balanced        | 0.0   | "Great for X, terrible for Y"                  |
| `toil`   | Net negative              | -1.0  | "Spent more time fixing than it saved"         |
| `hazard` | Actively harmful          | -2.0  | "Broke production", "Created tech debt"        |

**Trajectory (Where is it heading?)** - 3-tier scale evaluating future direction:

| Value         | Meaning              | Score | Signals                                        |
| :------------ | :------------------- | :---- | :--------------------------------------------- |
| `optimistic`  | Improving rapidly    | +2.0  | "Each version better", "Limitations temporary" |
| `uncertain`   | Genuine wait-and-see | 0.0   | "Too early to tell", "Jury's out"              |
| `pessimistic` | Stalled or limiting  | -2.0  | "Fundamental problem", "Same bugs since v1"    |

> **Independence**: These dimensions are orthogonal. An author can be negative on utility but optimistic on trajectory ("not ready yet, but improving fast") or positive on utility but pessimistic on trajectory ("useful now, but plateauing").

#### Score Derivation Formula (v4.0 - Equal Weighting)

```python
UTILITY_SCORES = {"magic": +2.0, "tool": +1.0, "mixed": 0.0, "toil": -1.0, "hazard": -2.0}
TRAJECTORY_SCORES = {"optimistic": +2.0, "uncertain": 0.0, "pessimistic": -2.0}

score = (utility_score * 0.5) + (trajectory_score * 0.5)  # Equal weighting
```

| Utility | Trajectory  | Score |
| :------ | :---------- | :---- |
| magic   | optimistic  | +2.00 |
| tool    | optimistic  | +1.50 |
| tool    | uncertain   | +0.50 |
| mixed   | uncertain   | 0.00  |
| toil    | uncertain   | -0.50 |
| toil    | pessimistic | -1.50 |
| hazard  | pessimistic | -2.00 |

#### Topic Field (v4.0 - Simplified)

Single `topic` field replaces previous `subtopic` + `primary_theme` + `secondary_theme`:

| Topic          | What it captures                                      |
| :------------- | :---------------------------------------------------- |
| `productivity` | Speed, efficiency, shipping faster, time saved        |
| `quality`      | Correctness, bugs, hallucinations, reliability, trust |
| `workflow`     | Integration, context, ergonomics, learning curve      |
| `evaluation`   | Tool comparisons, recommendations, adoption decisions |

#### Additional Extracted Fields

- **topic:** One of 4 values (productivity, quality, workflow, evaluation)
- **summary:** 25-word max author stance summary (specific verdict, not description)
- **quotes:** 1-2 verbatim quotes representing author sentiment

#### Rejection Criteria (Two-Layer Defense)

The analyzer will reject articles that slip through the prefilter:

- Product announcements without author experience/opinion
- Tutorial, course, book, or educational content
- Research paper or academic content
- AI news without developer perspective
- Not about coding/development workflows

When rejected, articles are automatically reclassified from `AI_DISCOURSE` to `AI_OTHER`.

#### Output

- `sentiment_score` (REAL): Derived numeric score (-2.0 to +2.0)
- `classification_json` (TEXT): Full structured response including all fields, model, and timestamp

#### CLI Usage

```bash
cd pipeline
python -m src.sentiment_analyzer -v                    # Run with streaming output (recommended)
python -m src.sentiment_analyzer --stats               # Show statistics
python -m src.sentiment_analyzer -v --limit 10         # Test with 10 articles
python -m src.sentiment_analyzer -v --reset            # Clear scores and re-analyze
python -m src.sentiment_analyzer --reset-only          # Clear scores and exit
python -m src.sentiment_analyzer --reanalyze -v        # Include already-analyzed
```

### Phase 7: Export (Static Data Generation)

- **Goal:** Generate static JSON files for production deployment.
- **Primary Module:** `export.py`
- **Output:** `src/lib/data/*.json`
- **When to Run:** After sentiment analysis is complete, before deploying frontend.

#### Exported Files

| File               | Contents                                                                              |
| :----------------- | :------------------------------------------------------------------------------------ |
| `articles.json`    | All AI_DISCOURSE articles with quotes, summary, topic, scores, influence              |
| `verdict.json`     | Current verdict (12-month window) + permanent record (all-time) + contribution stats  |
| `historical.json`  | Monthly verdict snapshots for history chart                                           |
| `weekly.json`      | Weekly rolling window snapshots with positive/negative/neutral contribution breakdown |
| `themes.json`      | Synthesized themes grouped by sentiment                                               |
| `llm-metrics.json` | LLM response data with speed metrics                                                  |

#### Filtering Criteria (Matches Frontend)

- `content_category = 'AI_DISCOURSE'`
- `hn_score >= 20`
- `topic != 'business'` (v4) OR `subtopic != 'business'` (v3)
- `sentiment_score IS NOT NULL`
- `scraped_status = 'success'`

#### CLI Usage

```bash
cd pipeline
python -m src.export -v                    # Default export to src/lib/data/
python -m src.export -v -o /custom/path    # Custom output directory
```

Or via a Vite+ script:

```bash
vp run pipeline:export
```

#### Version Bumping (Post-Export)

After a successful export, the CLI prompts to bump the frontend version. This tracks when new data was exported and deployed.

**Files Updated:**

- `package.json` - Package version
- `src/lib/version.ts` - Exported version constant

**Bump Types:**

| Type    | When to Use                              |
| :------ | :--------------------------------------- |
| `minor` | New data export (recommended)            |
| `patch` | Bug fixes or small updates               |
| `major` | Breaking changes to frontend/data schema |

**Manual Version Bump:**

```bash
node scripts/bump-version.mjs minor    # Bump minor version (0.x.0)
node scripts/bump-version.mjs patch    # Bump patch version (0.0.x)
node scripts/bump-version.mjs major    # Bump major version (x.0.0)
```

### Utilities

#### Theme Synthesis

- **Goal:** Extract recurring themes from grouped sentiment summaries.
- **Primary Module:** `summary_summarizer.py`
- **API:** Groq API (llama-3.3-70b-versatile)
- **Input:** Grouped articles from SQLite by sentiment category
- **Output:** Themes stored in SQLite `themes` table and exported to `themes.json`
- **When to Run:** After sentiment analysis is complete, before export.

**CLI Usage:**

```bash
cd pipeline
python -m src.summary_summarizer -v           # Run with verbose output
python -m src.summary_summarizer --stats      # Show theme statistics
python -m src.summary_summarizer --reset -v   # Clear and regenerate themes
```

---

## Verdict Scoring

The verdict scoring system evaluates AI coding discourse using power law + decay weighted analysis.

### Power Law + Decay Weighting

Articles are weighted using two factors:

1. **Power Law (Exponent 0.85):** Amplifies high-engagement articles while compressing low-engagement ones.
   - 20 upvotes → ~13 influence
   - 200 upvotes → ~89 influence (7× more)
   - 1000 upvotes → ~355 influence (27× more)
   - 4000 upvotes → ~1,189 influence (91× more)

2. **Time Decay (Half-life 24 months):** Articles lose influence over time, with a 2-year half-life.
   - Today: 100% influence
   - 6 months ago: 84% influence
   - 12 months ago: 71% influence
   - 24 months ago: 50% influence
   - 36 months ago: 35% influence

### Weighted Sentiment Calculation

Each article contributes `sentiment × influence` to the final score. This is the same formula displayed in the Recent Influential Articles table.

```typescript
// Influence score (power law + decay)
influence = hn_score^0.85 × 0.5^(months_ago / 24)

// Article contribution to verdict
contribution = sentiment_score × influence

// Final weighted sentiment
weighted_sentiment = sum(contributions) / sum(influence)
```

**Example with 1000 upvotes, recent article (influence = 355):**

- sentiment +0.9 → contributes +319.5 to weighted sum
- sentiment +0.2 → contributes +71 to weighted sum
- sentiment -0.8 → contributes -284 to weighted sum

**Rationale:**

- **Power law** ensures that high-engagement discussions have meaningful impact without extreme dominance (a 1000↑ article doesn't have 1000× the influence of a 10↑ article, just 27× more).
- **Time decay** recognizes that older discourse reflects outdated tool capabilities and community consensus. Recent discussions are more relevant to the question "Is AI good **yet**?"
- **Direct multiplication** (`sentiment × influence`) provides an intuitive metric that's consistent between the articles table and the verdict calculation.

### Configurable Parameters

| Constant                  | Default | Description                                             | Location             |
| :------------------------ | :------ | :------------------------------------------------------ | :------------------- |
| `VERDICT_WINDOW_MONTHS`   | 12      | Rolling window for primary verdict calculation (months) | `db.ts`, `export.py` |
| `TIMELINE_DISPLAY_MONTHS` | 36      | How many months to show in the timeline visualization   | `db.ts`, `export.py` |

### Scoring Process

1. **Calculate Contributions:** All articles contribute to the verdict calculation:
   - **Positive/Negative articles:** `contribution = sentiment × influence` (full strength)
   - **Neutral articles (-0.2 to +0.2):** `contribution = influence × NEUTRAL_MULTIPLIER` (configurable via `src/lib/constants.ts`)
   - Note: Neutral articles always have `sentiment = 0` (only `mixed + uncertain` combination), so influence is used directly
2. **Sum Contributions Separately:** Track positive and negative contributions separately.
3. **Calculate Score (Contribution Ratio):** `score = |positiveContribution| / (|positiveContribution| + |negativeContribution|) × 100`

**Example:** If +83k positive contribution and -66k negative contribution:

- score = 83k / (83k + 66k) = 83k / 149k ≈ **55.7%**

**Interpretation:**

- **50** = Balanced (equal positive and negative contributions)
- **100** = All positive contributions
- **0** = All negative contributions

### Sentiment Scale

The sentiment analyzer uses a 2-dimension formula (v4.0 - equal weighting):

- **Utility (5-tier):** magic(+2.0), tool(+1.0), mixed(0), toil(-1.0), hazard(-2.0)
- **Trajectory (3-tier):** optimistic(+2.0), uncertain(0), pessimistic(-2.0)
- **Formula:** `sentiment = utility × 0.5 + trajectory × 0.5` (equal weighting)

This creates a full range of **-2.0 to +2.0**:

- **Max:** magic(2.0) × 0.5 + optimistic(2.0) × 0.5 = +2.0
- **Min:** hazard(-2.0) × 0.5 + pessimistic(-2.0) × 0.5 = -2.0

### Verdict Thresholds

| Score Range | Verdict | Meaning                         |
| :---------- | :------ | :------------------------------ |
| ≥ 55        | **YES** | Passing grade - AI is good      |
| 45-55       | NOT YET | Too close to call               |
| < 45        | **NO**  | Failing grade - AI not good yet |

### Confidence Levels

- **High:** Score > 15 points from neutral AND 100+ articles analyzed
- **Medium:** Score > 8 points from neutral OR 50+ articles analyzed
- **Low:** Otherwise

### Momentum Calculation

Compares last 3 months' weighted sentiment against previous 3 months:

```
momentum = (recent_sentiment - previous_sentiment) / 0.2
```

Clamped to [-1, +1]. A 0.2 sentiment swing equals 100% momentum.

### Timeline Visualization

The timeline displays **TIMELINE_DISPLAY_MONTHS** (default: 36 months) of weekly sentiment data, providing historical context.

**Visual Encoding:**

- **Bar Height:** Proportional to total engagement weight (HN upvotes) for that week
- **Bar Color:** Based on sentiment (positive=green, negative=red, neutral=yellow)

**Article Influence Display:**
Recent influential articles are displayed in chronological order (newest first). The "influence score" is calculated using the power law + decay formula, showing the weighted contribution of each article to the verdict.

### Article Filtering

Only `AI_DISCOURSE` articles are included in the verdict calculation. `AI_NEWS` articles are analyzed but do not affect the final score. This ensures the verdict reflects subjective community opinion about AI's practical utility, not just objective news coverage.

---

## Database Schema

### SQLite Table: `urls`

| Column                | Type       | Description                                                             |
| :-------------------- | :--------- | :---------------------------------------------------------------------- |
| `id`                  | INTEGER PK | Auto-increment ID                                                       |
| `url`                 | TEXT       | Unique canonical URL                                                    |
| `hn_id`               | INTEGER    | Best performing HN Story ID                                             |
| `hn_score`            | INTEGER    | Upvotes                                                                 |
| `hn_comments`         | INTEGER    | Comment count                                                           |
| `hn_timestamp`        | INTEGER    | Unix epoch of post time                                                 |
| `hn_author`           | TEXT       | HN poster username                                                      |
| `hn_title`            | TEXT       | Original HN title                                                       |
| `status`              | TEXT       | Pipeline state (`pending`, `resolved`, `scraped`, `analyzed`)           |
| `scraped_status`      | TEXT       | `success`, `failed`, `paywall`                                          |
| `filter_score`        | INTEGER    | Legacy title-based filter (1=opinion, 0=neutral, -1=unclear)            |
| `content_category`    | TEXT       | Content classification (`AI_DISCOURSE`, `AI_NEWS`, `AI_OTHER`, `NOISE`) |
| `content_confidence`  | REAL       | Classification confidence (0.0-1.0)                                     |
| `content_filter_json` | TEXT       | Full content classification output (JSON)                               |
| `sentiment_score`     | FLOAT      | LLM derived sentiment (-2.0 to 2.0)                                     |
| `classification_json` | TEXT       | Full sentiment analysis output (JSON string)                            |
| `retry_count`         | INTEGER    | Number of scraping retry attempts                                       |
| `last_retry_at`       | INTEGER    | Unix timestamp of last retry                                            |
| `failure_category`    | TEXT       | Type of scraping failure                                                |
| `extract_error`       | TEXT       | Detailed error message                                                  |

### SQLite Table: `themes`

| Column          | Type       | Description                       |
| :-------------- | :--------- | :-------------------------------- |
| `id`            | INTEGER PK | Auto-increment ID                 |
| `title`         | TEXT       | Theme title                       |
| `description`   | TEXT       | Theme description                 |
| `sentiment`     | TEXT       | `positive`, `neutral`, `negative` |
| `article_count` | INTEGER    | Number of articles in theme       |
| `created_at`    | INTEGER    | Unix timestamp                    |

### Parquet Schema

- `url_id` (fk) - Foreign key to urls table
- `url` (str) - Canonical URL
- `title` (str) - Article title
- `full_text` (str) - Complete article text
- `domain` (str) - Domain name
