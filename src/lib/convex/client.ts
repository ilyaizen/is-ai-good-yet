import { env } from "$env/dynamic/public"
import { ConvexClient } from "convex/browser"

/**
 * Singleton Convex client for browser-side real-time subscriptions.
 *
 * This client is lazy-initialized on first use and cached globally.
 * It's used to subscribe to real-time updates like the visitor counter.
 *
 * The client handles:
 * - WebSocket connection to Convex backend
 * - Query execution and polling
 * - Query polling and caching
 * - Automatic reconnection on failure
 *
 * Note: This is separate from ConvexHttpClient used server-side in hooks.server.ts
 */
let convexClient: ConvexClient | null = null

/**
 * Get the global Convex client instance.
 * Creates and caches it on first call.
 *
 * Returns null when the public Convex URL is not configured so the app
 * can still build and run in environments without visitor tracking.
 */
export function getConvexClient(): ConvexClient | null {
  if (!env.PUBLIC_CONVEX_URL) {
    return null
  }

  if (!convexClient) {
    convexClient = new ConvexClient(env.PUBLIC_CONVEX_URL)
  }
  return convexClient
}
