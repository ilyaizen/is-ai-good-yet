# CLI Reference

Integrated bun scripts for development, testing, and pipeline management.

## Development

```bash
bun run dev                 # Start dev server
bun run build              # Production build
bun run start              # Run production server (HOST=0.0.0.0)
bun run preview            # Preview production build
bun run check              # Type check & lint
bun run check:watch        # Type check with watch mode
bun run lint               # Run Prettier & ESLint
bun run format             # Auto-format code
```

## Utilities & Scripts

```bash
bun run diagnose:schema-migration    # Check schema migration status
bun run verify:fix                   # Verify fixes applied
bun run test:article-display         # Test article display rendering
```

## Pipeline: Core Operations

```bash
bun run pipeline:run       # Run all pipeline phases (ingest → scrape → analyze)
bun run pipeline:ingest    # Ingest data from external sources
bun run pipeline:scrape    # Scrape article content
bun run pipeline:analyze   # Analyze articles with LLM
```

## Pipeline: Setup & Utilities

```bash
bun run pipeline:bootstrap          # Bootstrap pipeline database from static data
bun run pipeline:stats              # Check pipeline statistics & progress
bun run pipeline:consistency        # Verify database consistency
bun run pipeline:catch-up           # Catch up missing articles
bun run pipeline:export             # Export processed articles
bun run pipeline:export-titles      # Export article titles
bun run pipeline:analyze-single     # Analyze a single article
bun run pipeline:backfill           # Backfill historical data
bun run pipeline:clean-articles     # Clean article data
bun run pipeline:clean-text         # Clean text extraction
```

## Debug Commands

```bash
bun run debug:cost-monitor          # Monitor API costs
bun run debug:db-details            # Inspect database structure
bun run debug:db-state              # Check database state
bun run debug:inspect-stealth       # Inspect Stealth class methods
bun run debug:verify-stealth        # Verify Stealth implementation
```

## Reset Commands

⚠️ **Destructive Operations**

```bash
bun run reset:opinions              # Reset opinion data for re-analysis
bun run reset:sentiment             # Reset sentiment data for re-analysis
bun run reset:prefilter             # Reset prefilter & restart pipeline
```

## Pipeline Environment

Pipeline scripts use Python 3.11 from `.venv`:

```bash
source .venv/bin/activate           # Activate venv
pip install -r requirements.txt     # Install dependencies
deactivate                          # Deactivate venv
```

See `pipeline/README.md` for pipeline-specific documentation.
