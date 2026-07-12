import assert from "node:assert/strict"
import { createOnceFinalizer, resolvePipelinePython } from "../src/lib/server/pipeline-runtime"

let finalized = 0
const finalize = createOnceFinalizer(() => {
  finalized += 1
})

assert.equal(finalize(), true)
assert.equal(finalize(), false)
assert.equal(finalized, 1, "spawn error + close must finalize a run only once")

const existing = new Set(["/app/.venv/bin/python", "/usr/bin/python3"])
assert.equal(
  resolvePipelinePython({
    explicit: undefined,
    repoRoot: "/app",
    pipelineDir: "/app/pipeline",
    platform: "linux",
    exists: (candidate) => existing.has(candidate),
  }),
  "/app/.venv/bin/python",
)
assert.equal(
  resolvePipelinePython({
    explicit: "/opt/pipeline-venv/bin/python",
    repoRoot: "/app",
    pipelineDir: "/app/pipeline",
    platform: "linux",
    exists: (candidate) => candidate === "/opt/pipeline-venv/bin/python",
  }),
  "/opt/pipeline-venv/bin/python",
)

console.log("pipeline runner runtime tests passed")
