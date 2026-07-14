# CLI Reference

Integrated Vite+ scripts for development, testing, and pipeline management.

## Development

```bash
vp dev                 # Start dev server
vp build              # Production build
vp run start              # Run production server (HOST=0.0.0.0)
vp preview            # Preview production build
vp run check          # Vite+ checks plus Svelte type checking
vp run check:watch    # Svelte type checking in watch mode
vp lint               # Run Vite+ linting
vp fmt             # Auto-format code
```

## Utilities & Scripts

```bash
vp run diagnose:schema-migration    # Check schema migration status
vp run verify:fix                   # Verify fixes applied
vp run test:article-display         # Test article display rendering
```

## Pipeline: Core Operations

```bash
vp run pipeline:run       # Run all pipeline phases (ingest → scrape → analyze)
vp run pipeline:ingest    # Ingest data from external sources
vp run pipeline:scrape    # Scrape article content
vp run pipeline:analyze   # Analyze articles with LLM
```

## Pipeline: Setup & Utilities

```bash
vp run pipeline:bootstrap          # Bootstrap pipeline database from static data
vp run pipeline:stats              # Check pipeline statistics & progress
vp run pipeline:consistency        # Verify database consistency
vp run pipeline:catch-up           # Catch up missing articles
vp run pipeline:export             # Export processed articles
vp run pipeline:export-titles      # Export article titles
vp run pipeline:analyze-single     # Analyze a single article
vp run pipeline:backfill           # Backfill historical data
vp run pipeline:clean-articles     # Clean article data
vp run pipeline:clean-text         # Clean text extraction
```

## Debug Commands

```bash
vp run debug:cost-monitor          # Monitor API costs
vp run debug:db-details            # Inspect database structure
vp run debug:db-state              # Check database state
vp run debug:inspect-stealth       # Inspect Stealth class methods
vp run debug:verify-stealth        # Verify Stealth implementation
```

## Reset Commands

⚠️ **Destructive Operations**

```bash
vp run reset:opinions              # Reset opinion data for re-analysis
vp run reset:sentiment             # Reset sentiment data for re-analysis
vp run reset:prefilter             # Reset prefilter & restart pipeline
```

## Pipeline Environment

Pipeline scripts use Python 3.11 from `.venv`:

```bash
source .venv/bin/activate           # Activate venv
pip install -r requirements.txt     # Install dependencies
deactivate                          # Deactivate venv
```

See `pipeline/README.md` for pipeline-specific documentation.
