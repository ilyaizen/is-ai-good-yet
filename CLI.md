# CLI Reference

Integrated npm scripts for development, testing, and pipeline management.

## Development

```bash
npm run dev                 # Start dev server
npm run build              # Production build
npm run start              # Run production server (HOST=0.0.0.0)
npm run preview            # Preview production build
npm run check              # Type check & lint
npm run check:watch        # Type check with watch mode
npm run lint               # Run Prettier & ESLint
npm run format             # Auto-format code
```

## Utilities & Scripts

```bash
npm run diagnose:schema-migration    # Check schema migration status
npm run verify:fix                   # Verify fixes applied
npm run test:article-display         # Test article display rendering
```

## Pipeline: Core Operations

```bash
npm run pipeline:run       # Run all pipeline phases (ingest → scrape → analyze)
npm run pipeline:ingest    # Ingest data from external sources
npm run pipeline:scrape    # Scrape article content
npm run pipeline:analyze   # Analyze articles with LLM
```

## Pipeline: Setup & Utilities

```bash
npm run pipeline:bootstrap          # Bootstrap pipeline database from static data
npm run pipeline:stats              # Check pipeline statistics & progress
npm run pipeline:consistency        # Verify database consistency
npm run pipeline:catch-up           # Catch up missing articles
npm run pipeline:export             # Export processed articles
npm run pipeline:export-titles      # Export article titles
npm run pipeline:analyze-single     # Analyze a single article
npm run pipeline:backfill           # Backfill historical data
npm run pipeline:clean-articles     # Clean article data
npm run pipeline:clean-text         # Clean text extraction
```

## Debug Commands

```bash
npm run debug:cost-monitor          # Monitor API costs
npm run debug:db-details            # Inspect database structure
npm run debug:db-state              # Check database state
npm run debug:inspect-stealth       # Inspect Stealth class methods
npm run debug:verify-stealth        # Verify Stealth implementation
```

## Reset Commands

⚠️ **Destructive Operations**

```bash
npm run reset:opinions              # Reset opinion data for re-analysis
npm run reset:sentiment             # Reset sentiment data for re-analysis
npm run reset:prefilter             # Reset prefilter & restart pipeline
```

## Pipeline Environment

Pipeline scripts use Python 3.11 from `.venv`:

```bash
source .venv/bin/activate           # Activate venv
pip install -r requirements.txt     # Install dependencies
deactivate                          # Deactivate venv
```

See `pipeline/README.md` for pipeline-specific documentation.
