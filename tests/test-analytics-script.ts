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
  /\bsrc=["']https:\/\/analytics\.is-ai-good-yet\.com\/api\/script\.js\?siteId=903a72fbf2be["']/,
  "Use the canonical Rybbit API path with the registered site identifier"
)
assert.match(trackerTag, /\sdefer(?:\s|>)/, "Keep tracker loading deferred")

console.log("analytics script tests passed")
