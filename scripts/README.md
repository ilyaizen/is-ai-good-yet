# Utility Scripts

One-off tooling and diagnostics. Run via `vp run <script-name>`.

| Script                         | Purpose                                                                         |
| ------------------------------ | ------------------------------------------------------------------------------- |
| `ship.sh`                      | End-to-end safe shipping workflow (typecheck -> PR -> HITL -> squash merge -> deploy monitor) |
| `monitor-deploy.sh`            | Polls Coolify deployment queue on Hetzner VPS (`coolify-db`) and verifies live site |
| `bump-version.mjs`             | Version bumper — updates version across package.json, svelte config, data files |
| `diagnose-schema-migration.ts` | Diagnoses v3→v4 schema migration impact on article classification               |

## History

Previously this directory also held `test-*.ts` smoke tests and `verify-fix.ts`. Those moved to [`tests/`](../tests/) or were deleted (superseded by newer contracts).
