import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const html = readFileSync(new URL("../src/app.html", import.meta.url), "utf8")
const trackerTags = [...html.matchAll(/<script\b[^>]*>/gi)]
  .map(([tag]) => tag)
  .filter((tag) => /\bsrc=["']https:\/\/analytics\.is-ai-good-yet\.com\//.test(tag))

assert.equal(trackerTags.length, 1, "Load the self-hosted tracker exactly once")
const [trackerTag = ""] = trackerTags
assert.match(
  trackerTag,
  /\bsrc=["']https:\/\/analytics\.is-ai-good-yet\.com\/api\/script\.js["']/,
  "Use the canonical Rybbit API path without the legacy proxy route"
)
assert.match(trackerTag, /\bdata-site-id=["']1["']/, "Keep the registered production site ID")
assert.match(trackerTag, /\sdefer(?:\s|>)/, "Keep tracker loading deferred")

console.log("analytics script tests passed")
