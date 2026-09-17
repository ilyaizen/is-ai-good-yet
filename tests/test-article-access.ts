/**
 * IAIGY-01: unified article-body access policy.
 *
 * Verifies both surfaces defer to the shared authorized loader:
 *  - unauthorized callers never receive full article bodies (metadata only)
 *  - authorized admin callers still receive permitted text
 */
import assert from "node:assert/strict"
import { mkdtempSync, writeFileSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { getAuthorizedArticleText } from "../src/lib/server/article-access"
import { readFileSync } from "node:fs"

const BODY = `Title: Test Article\nURL: https://example.com/a\n\nThis is the FULL copyrighted article body for authorized eyes only.`

// Build a fake store so the test never depends on pipeline data
const dir = mkdtempSync(join(tmpdir(), "iaigy01-"))
const fakeStore = (hnId: number) => {
	if (hnId !== 42) return null
	return { hn_id: 42, title: "Test Article", url: "https://example.com/a", text: BODY.slice(BODY.indexOf("\n\n") + 2).trim(), wordCount: 10 }
}
const reader = (hnId: number) => fakeStore(hnId) // stand-in for getArticleText

// 1. Unauthorized caller: store "has" the text, but they must get null
assert.equal(
	getAuthorizedArticleText(42, false, reader),
	null,
	"unauthorized caller must NEVER receive the full body"
)

// 2. Authorized caller: receives permitted text
const authed = getAuthorizedArticleText(42, true, reader)
assert.ok(authed, "authorized caller receives the text object")
assert.equal(authed!.text, "This is the FULL copyrighted article body for authorized eyes only.")
assert.equal(authed!.hn_id, 42)

// 3. Not-scraped article: authorized caller also gets null (still boolean-safe)
assert.equal(getAuthorizedArticleText(999, true, reader), null, "missing store entry stays null for authorized caller too")

// 4. Source-level guard for the details page server: it must not call
//    getArticleText directly, only the shared authorized loader.
const pageServer = readFileSync("src/routes/details/[id]/+page.server.ts", "utf8")
assert.ok(pageServer.includes("getAuthorizedArticleText"), "details page.server.ts must use the shared loader")
assert.ok(!pageServer.includes("getArticleText("), "details page.server.ts must NOT call getArticleText directly")

// 5. Source-level guard for the API route (same rule, on top of its own admin gate)
const apiRoute = readFileSync("src/routes/api/article-details/[id]/+server.ts", "utf8")
assert.ok(apiRoute.includes("getAuthorizedArticleText"), "api route must use the shared loader")
assert.ok(!/getArticleText\(/.test(apiRoute), "api route must NOT call getArticleText directly")

console.log("OK: article-body access policy unified (unauthenticated surfaces never see full bodies)")

rmSync(dir, { recursive: true, force: true })
