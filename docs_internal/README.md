# Internal Docs

Operational documentation for `is-ai-good-yet`. This directory is the canonical reference for agents and maintainers.

## Index

| Doc | Contents |
| --- | --- |
| [architecture.md](./architecture.md) | System design, data flow, pipeline phases, verdict scoring |
| [cli.md](./cli.md) | Vite+ command reference |
| [guide.md](./guide.md) | Setup, usage, dev conventions, agent mandates |
| [pipeline-admin-plan.md](./pipeline-admin-plan.md) | Admin pipeline control surface: lock architecture, DB schema, scheduling |
| [pipeline-production-reliability.md](./pipeline-production-reliability.md) | Production preflight, storage alignment, residential HTML fallback |
| [troubleshooting.md](./troubleshooting.md) | Common issues: prefilter JSON, archive CAPTCHA, HN ID mismatch |
| [v2-design-specification.md](./v2-design-specification.md) | V2 design specification: broad-scope analysis, HN comment sampling, methodology |

## Related

- [`../AGENTS.md`](../AGENTS.md) — agent guidance (single source of truth for agents)
- [`../README.md`](../README.md) — project README
- [`../CHANGELOG.md`](../CHANGELOG.md) — changelog
- [`../plans/`](../plans/) — implementation plans (active + archive)
- [`../tests/`](../tests/) — frontend smoke tests
