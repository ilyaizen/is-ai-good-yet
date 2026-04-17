import { ConvexClient } from "convex/browser"
import { PUBLIC_CONVEX_URL } from "$env/static/public"

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
 * @returns ConvexClient singleton
 */
export function getConvexClient(): ConvexClient {
  if (!convexClient) {
    convexClient = new ConvexClient(PUBLIC_CONVEX_URL)
  }
  return convexClient
}
