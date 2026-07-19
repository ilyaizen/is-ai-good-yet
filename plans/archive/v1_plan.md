# Project Plan & Roadmap

## Overview

The goal is to answer "Is AI Good Yet?" by analyzing Hacker News discourse over the past few years.

## Current Phase: Phase 5 (Export & Frontend Finalization) - **ACTIVE**

### Completed

- [x] **TSK-B01: Schema Setup**: SQLite `urls` table created.
- [x] **TSK-B01-ALGOLIA: Algolia Discovery**: Implemented Phase 1.5 to query Algolia API directly.
- [x] **TSK-B02: HN Resolver**: `hn_resolver.py` implemented with Algolia API.
- [x] **TSK-B03: Scraper**: `scraper.py` implemented with Trafilatura and Parquet storage.
- [x] **TSK-B03-TXT: Text Files**: Implemented `.txt` ground truth storage and rebuild logic.
- [x] **TSK-B03-RETRY: Retry Logic**: Added retry capability and `archive.is` fallback for improved scraping success.
- [x] **TSK-B03-FIX: Scraper Modernization**: Replaced `playwright-stealth` with `camoufox` for better reliability.
- [x] **TSK-B04: Prefilter**: `prefilter.py` implemented with Mistral API opinion detection.
- [x] **TSK-F01-F06: Frontend Core**: Dashboard skeleton, "Verdict" view, Detailed Table, UI polish, and Metadata display.
- [x] **TSK-F07-F09: Table Improvements**: Enhanced Opinion/Status/Sentiment columns, filters, source domain display.
- [x] **TSK-B03-ARCHIVE: Interactive Archive Scraper**: Robust batching with graceful interrupts and session persistence.
- [x] **TSK-B03-CLEAN: Article Text Data Cleaning**: `clean_articles.py` with configurable cleaning patterns.
- [x] **TSK-B03-UPTACK: Ground-Truth Uptake**: `uptake_ground_truth.py` synchronizes database with cleaned text files.
- [x] **TSK-B05: Sentiment Analyzer**: LLM sentiment analysis with 2-dimension scoring (utility/trajectory).
- [x] **TSK-B05-THEMES**: Theme Summary migrated to Groq API.
- [x] **TSK-B06: Export Pipeline**: `export.py` generates static JSON for frontend (articles, verdict, historical).

### In Progress

1. **Git Submodule Setup**: Configure frontend as separate repo for Vercel deployment.
2. **Frontend Static Mode**: Modify frontend to read from exported JSON in production.
3. **Deployment (TSK-D03)**: Prepare build scripts for Vercel.

## Detailed Task References

See [tasks.md](./tasks.md) for the granular task list and status.

## Phase Overview

1. **Phase 1**: Ingestion & HN Resolution (Histre backfill, Algolia queries)
2. **Phase 2**: Content Scraping (Playwright + archive fallbacks)
3. **Phase 3**: Content Pre-filtering (LLM classification)
4. **Phase 4**: Sentiment Analysis (LLM 2-dimension scoring)
5. **Phase 5**: Export & Frontend Finalization (Static JSON, Git submodule) - **CURRENT**
6. **Phase 6**: Deployment (Vercel, documentation)
