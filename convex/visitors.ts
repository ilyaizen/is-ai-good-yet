import { v } from "convex/values"
import { mutation, query } from "./_generated/server"

/**
 * Simple hash function for sharding - distributes IPs across 16 shards.
 * Uses string character codes to create a numeric hash.
 * Different IPs will generally hash to different shards (reduces lock contention).
 */
function hashToShard(str: string, shards: number = 16): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i)
    hash = hash & hash // Convert to 32-bit integer
  }
  return Math.abs(hash) % shards
}

/**
 * Records a unique visitor visit to the site.
 *
 * Called from hooks.server.ts on every page load, but only:
 * - After bot filtering (crawlers/headless browsers excluded)
 * - After session deduplication (no duplicate within 24 hours)
 *
 * This mutation ensures:
 * - IP addresses are hashed server-side (privacy protection)
 * - Each unique IP is counted only once per session
 * - Counter updates are distributed across 16 shards (prevents bottlenecks)
 *
 * Manual Sharding Strategy:
 * - New visitors increment a counter shard based on their IP hash
 * - 16 shards allow 1000+ concurrent writes without lock contention
 * - Returning visitors just update their lastVisit timestamp (no shard write)
 *
 * @param ipHash - SHA-256 hash of (IP + salt) - never raw IP
 * @returns { isNewVisitor: boolean } - whether this IP is new or returning
 */
export const recordVisit = mutation({
  args: { ipHash: v.string() },
  handler: async (ctx, { ipHash }) => {
    const now = Date.now()

    // Check if this IP hash has visited before
    const existingVisitor = await ctx.db
      .query("unique_visitors")
      .withIndex("by_ip_hash", (q) => q.eq("ipHash", ipHash))
      .first()

    if (existingVisitor) {
      // Returning visitor - update last visit time and visit count
      await ctx.db.patch(existingVisitor._id, {
        lastVisit: now,
        visitCount: existingVisitor.visitCount + 1,
      })
      return { isNewVisitor: false }
    }

    // New visitor! Create record and increment counter shard
    await ctx.db.insert("unique_visitors", {
      ipHash,
      firstVisit: now,
      lastVisit: now,
      visitCount: 1,
    })

    // Increment the counter shard
    // Using IP hash to distribute writes across 16 shards prevents hot spots
    const shardId = hashToShard(ipHash, 16)
    const shard = await ctx.db
      .query("sharded_counter_shards")
      .withIndex("by_name_and_shard", (q) => q.eq("name", "visitors").eq("shardId", shardId))
      .first()

    if (shard) {
      // Shard exists - increment count
      await ctx.db.patch(shard._id, {
        count: shard.count + 1,
      })
    } else {
      // New shard - create it
      await ctx.db.insert("sharded_counter_shards", {
        name: "visitors",
        count: 1,
        shardId,
      })
    }

    return { isNewVisitor: true }
  },
})

/**
 * Gets the current total unique visitor count.
 *
 * This query is subscribed to from client-side components via Convex's
 * real-time watchQuery API, enabling live updates across all user browsers
 * without polling.
 *
 * Implementation: Sums all 16 counter shards to get total unique visitors.
 * Performance: O(16) - reads from all 16 shards and sums them
 *
 * @returns number - Total unique visitors counted
 */
export const getVisitorCount = query({
  args: {},
  handler: async (ctx) => {
    // Get all counter shards for "visitors"
    const shards = await ctx.db.query("sharded_counter_shards").collect()

    // Filter to only "visitors" shards and sum the counts
    const totalCount = shards.filter((shard) => shard.name === "visitors").reduce((sum, shard) => sum + shard.count, 0)

    return totalCount
  },
})
