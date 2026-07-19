# Frontend & Integration Tests

Assert-based smoke tests for invariant checking. Run via `vp run test:*`.

| Test | What it checks |
| --- | --- |
| `globe-arcs.ts` | Pure arc geometry (slerp, sampling, neighbor-weighted pairs) |
| `pipeline-command-config.ts` | Named command list and readiness evaluation |
| `pipeline-runner-runtime.ts` | Python resolution, once-finalizer, source directory |
| `v2-generation-integrity.ts` | Manifest hash validation for V2 data exports |
| `v2-admin-data.ts` | Admin DB loader with temp database fixture |
| `v2-admin-layout.ts` | Admin page SvelteKit route structure |
