import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import {
  evaluateCommandReadiness,
  getPipelineCommandList,
  type PipelinePreflightSnapshot,
} from "../src/lib/server/pipeline-command-config"

const v1Names = getPipelineCommandList("v1").map((command) => command.name)
const v2Names = getPipelineCommandList("v2").map((command) => command.name)

assert(v1Names.includes("catch_up"), "V1 keeps the legacy catch-up orchestrator")
assert(!v2Names.includes("catch_up"), "V2 must never expose the V1 catch-up orchestrator")
assert(!v2Names.includes("prefilter_content"), "V2 must never expose the V1 prefilter")
assert(!v2Names.includes("sentiment_analyzer"), "V2 must never expose the V1 analyzer")
assert(v2Names.includes("v2_prefilter"), "V2 exposes its broad prefilter")
assert(v2Names.includes("v2_run"), "V2 exposes its isolated orchestrator")
assert(v2Names.includes("v2_export"), "V2 exposes its isolated export")

const baseSnapshot: PipelinePreflightSnapshot = {
  python: { ok: true, reason: "Python imports succeeded." },
  storage: { ok: true, reason: "Pipeline storage is aligned and writable." },
  scraper: { ok: true, reason: "Scraper imports and Chromium are available." },
  groq: { ok: true, reason: "GROQ_API_KEY is configured." },
  residential: { ok: true, reason: "Optional residential fetcher is disabled." },
}

assert.equal(evaluateCommandReadiness("scrape", baseSnapshot).ready, true)
assert.equal(
  evaluateCommandReadiness("scrape", {
    ...baseSnapshot,
    scraper: { ok: false, reason: "Playwright import failed: libstdc++.so.6 is missing." },
  }).ready,
  false
)
assert.match(
  evaluateCommandReadiness("scrape", {
    ...baseSnapshot,
    scraper: { ok: false, reason: "Playwright import failed: libstdc++.so.6 is missing." },
  }).reasons.join(" "),
  /libstdc\+\+\.so\.6/
)
assert.equal(
  evaluateCommandReadiness("v2_prefilter", {
    ...baseSnapshot,
    groq: { ok: false, reason: "GROQ_API_KEY is not configured." },
  }).ready,
  false
)
assert.equal(
  evaluateCommandReadiness("v2_comments", {
    ...baseSnapshot,
    groq: { ok: false, reason: "GROQ_API_KEY is not configured." },
  }).ready,
  true,
  "comment collection does not require Groq"
)

const cli = readFileSync(new URL("../cli.ts", import.meta.url), "utf8")
const packageJson = readFileSync(new URL("../package.json", import.meta.url), "utf8")
assert(cli.includes("pipeline-v2-run"), "interactive CLI exposes the isolated V2 orchestrator")
assert(packageJson.includes('"pipeline:preflight"'), "package scripts expose the production preflight")
assert(packageJson.includes('"pipeline:residential-fetcher"'), "package scripts expose the residential service")

console.log("pipeline command config tests passed")
