import type { Handle } from "@sveltejs/kit"
import { ConvexHttpClient } from "convex/browser"
import { api } from "../convex/_generated/api"
import { createHash } from "crypto"
import { existsSync, readFileSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { env as publicEnv } from "$env/dynamic/public"
import { env as privateEnv } from "$env/dynamic/private"

// adapter-node's standalone server doesn't load .env, and SvelteKit's
// $env/dynamic/* reads process.env live, so without this both the admin env
// checks and the spawned Python sidecar miss GROQ/MISTRAL keys (and the visitor
// salt). Parse repo-root .env once at boot; never override real shell env.
// Resolve .env from this module's location (src/hooks.server.ts → 1 dir up),
// NOT process.cwd() — which may be wrong under adapter-node standalone.
;(() => {
  const modulePath = fileURLToPath(import.meta.url)
  const repoRoot = path.resolve(path.dirname(modulePath))
  const envFile = path.join(repoRoot, ".env")
  if (!existsSync(envFile)) return
  const lines = readFileSync(envFile, "utf8").split("\n")
  for (const raw of lines) {
    const line = raw.trim()
    if (!line || line.startsWith("#")) continue
    const eq = line.indexOf("=")
    if (eq < 0) continue
    const key = line.slice(0, eq).trim()
    let value = line.slice(eq + 1).trim()
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1)
    }
    if (key && !(key in process.env)) process.env[key] = value
  }
})()

// Initialize Convex HTTP client for server-side mutations
// This client runs on the server only - prevents client-side spoofing of IP addresses
const convex = publicEnv.PUBLIC_CONVEX_URL ? new ConvexHttpClient(publicEnv.PUBLIC_CONVEX_URL) : null

/**
 * Hash IP address with salt for privacy-friendly storage.
 *
 * Instead of storing raw IP addresses (privacy concern, GDPR issues),
 * we hash them with a server-side salt before storage.
 *
 * Benefits:
 * - One-way hash: Cannot reverse to get original IP
 * - Salt prevents rainbow table attacks
 * - Different IP → different hash
 * - Same IP → same hash (enables duplicate detection)
 *
 * @param ip - Client IP address (IPv4 or IPv6)
 * @returns SHA-256 hash of (IP + salt)
 */
function hashIP(ip: string): string {
  const normalizedIP = ip === "::1" || ip === "127.0.0.1" ? "localhost-dev" : ip

  if (!privateEnv.VISITOR_IP_SALT) {
    return ""
  }

  return createHash("sha256").update(`${normalizedIP}:${privateEnv.VISITOR_IP_SALT}`).digest("hex")
}

/**
 * Detect bot traffic based on User-Agent header.
 *
 * Bots and crawlers should not be counted as "visitors" since they:
 * - Don't represent human interest in the content
 * - Inflate visitor counts artificially
 * - May be crawling for AI training data
 *
 * Patterns include:
 * - Search engine crawlers: Googlebot, Bingbot, etc.
 * - Monitoring bots: Lighthouse, monitoring services
 * - Headless browsers: Playwright, Puppeteer (likely scripts)
 * - Generic bot patterns: "bot", "spider", "crawler"
 *
 * @param userAgent - User-Agent header from request
 * @returns true if request is from a bot
 */
function isBot(userAgent: string | null): boolean {
  if (!userAgent) return false

  const botPatterns = [
    /bot/i, // Generic bot pattern
    /crawl/i, // Crawler
    /spider/i, // Web spider
    /slurp/i, // Yahoo slurp
    /mediapartners/i, // Google Image search
    /lighthouse/i, // Lighthouse auditing tool
    /headless/i, // Headless browser
  ]

  return botPatterns.some((pattern) => pattern.test(userAgent))
}

/**
 * SvelteKit server hook - intercepts every request to the application.
 *
 * This is where we:
 * 1. Detect bot traffic (exclude from counting)
 * 2. Check session cookie (prevent duplicate counts within 24hrs)
 * 3. Extract client IP (server-side, prevents spoofing)
 * 4. Hash IP for privacy (GDPR-compliant storage)
 * 5. Record visit to Convex (async, doesn't block page load)
 *
 * The three-layer filtering ensures accurate "unique visitor" counts:
 * Layer 1: Bot filtering (crawlers excluded)
 * Layer 2: Session deduplication (one count per IP per 24 hours)
 * Layer 3: IP hashing (privacy protection)
 */
export const handle: Handle = async ({ event, resolve }) => {
  const userAgent = event.request.headers.get("user-agent")

  // Filter 1: Skip tracking bot traffic
  if (isBot(userAgent)) {
    return resolve(event)
  }

  // Filter 2: Session deduplication - one visitor per IP per 24 hours
  const sessionCookie = event.cookies.get("visitor_session")

  if (!sessionCookie) {
    try {
      // Extract client IP address (server-side prevents spoofing)
      // Try X-Forwarded-For first (for proxies/load balancers)
      // Fall back to getClientAddress() (direct connection)
      const clientIP = event.request.headers.get("x-forwarded-for")?.split(",")[0].trim() || event.getClientAddress()

      // Hash IP for privacy (GDPR-friendly)
      const ipHash = hashIP(clientIP)
      if (!ipHash) return resolve(event)

      // Record visit to Convex asynchronously
      // Fire-and-forget: doesn't block page rendering
      // Errors are silently logged but don't break the site
      if (convex) {
        convex.mutation(api.visitors.recordVisit, { ipHash }).catch((err) => {
          console.error("Failed to record visitor:", err)
        })
      }

      event.cookies.set("visitor_session", "1", {
        path: "/",
        maxAge: 60 * 60 * 24,
        httpOnly: true,
        sameSite: "strict",
        secure: process.env.NODE_ENV === "production",
      })
    } catch (error) {
      // Silently fail - don't break site if visitor tracking fails
      // This ensures graceful degradation if Convex is down
      console.error("Visitor tracking error:", error)
    }
  }

  // Continue with normal request processing
  return resolve(event)
}
