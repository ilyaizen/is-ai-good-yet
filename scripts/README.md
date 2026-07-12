# Frontend Diagnostic Scripts

This directory contains diagnostic and verification scripts for troubleshooting data migration and schema compatibility issues.

## Scripts

### `diagnose-schema-migration.ts`

Diagnoses v3→v4 schema migration impact by counting articles with old vs. new classification_json schema.

**Usage:**

```bash
bun run diagnose:schema-migration
```

**Output:**

- Total AI_DISCOURSE articles count
- Articles with new schema (has `topic` field)
- Articles with old schema (has `subtopic` but no `topic`)
- Articles currently included/excluded by filter
- Sample old-schema articles with high HN scores
- Specific article check (45465098)

### `verify-fix.ts`

Verifies that the backward compatibility fix correctly includes old-schema articles in verdict calculations.

**Usage:**

```bash
bun run verify:fix
```

**Output:**

- Total articles vs. included articles
- Business articles excluded (new schema + old schema)
- Verification that all non-business articles are included
- Specific article filter result (INCLUDED/EXCLUDED)

### `test-article-display.ts`

Tests that old-schema articles load correctly through SvelteKit's server-side data loading and display properly on the frontend.

**Usage:**

```bash
bun run test:article-display
```

**Note:** This script uses the app's server-side DB helpers and expects the pipeline database at `pipeline/data/pipeline.db`.

## Context

These scripts were created during the v4.0 schema migration (TSK-F28) to diagnose and verify the fix for 340 old-schema articles being excluded from verdict calculations.

**Problem:** Articles analyzed before v4.0 had `subtopic`/`primary_theme`/`secondary_theme` fields, but frontend queries expected the new `topic` field, causing 33% of articles to be excluded.

**Solution:** Backward-compatible SQL queries and schema normalization layer to handle both old and new schemas transparently.

See `agent_docs/tasks.md` (TSK-F28, TSK-F29) for full details.
