import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const adminPage = readFileSync("src/routes/admin/+page.svelte", "utf8")
const v2LayoutServer = readFileSync("src/routes/v2/admin/+layout.server.ts", "utf8")
const v2Server = readFileSync("src/routes/v2/admin/+page.server.ts", "utf8")
const v2Page = readFileSync("src/routes/v2/admin/+page.svelte", "utf8")
const v2Observability = readFileSync("src/lib/components/v2/v2-admin-observability.svelte", "utf8")
const v2StoryEndpoint = readFileSync("src/routes/api/v2/admin/stories/[id]/+server.ts", "utf8")

assert.match(v2Server, /getV2AdminData/)
assert.match(v2Server, /v2:\s*getV2AdminData\(\)/)
// Auth gating moved to the shared layout load, re-exported here; the page
// load only assembles V2 data + methodology.
assert.match(v2LayoutServer, /export\s*\{\s*load\s*\}/)
assert.match(v2LayoutServer, /admin\/\+layout\.server/)
assert.match(v2Page, /V2AdminObservability/)
assert.match(v2Observability, /fetch\(`\/api\/v2\/admin\/stories\/\$\{storyId\}`\)/)
assert.match(v2Observability, /ontoggle=/)
assert.match(v2StoryEndpoint, /isValidAdminCookie/)
assert.match(v2StoryEndpoint, /throw error\(401/)
assert.match(v2StoryEndpoint, /getV2AdminStoryDetails/)
assert.match(adminPage, /overflow-x-auto[^\n"]*whitespace-pre/)
assert.doesNotMatch(adminPage, /whitespace-pre-wrap[^\n"]*wrap-break-word/)
assert.match(adminPage, /\{#if !data\.v2\}/)

console.log("V2 admin layout regression passed")
