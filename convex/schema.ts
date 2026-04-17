import { defineSchema, defineTable } from "convex/server"
import { v } from "convex/values"

export default defineSchema({
  // Track unique visitor hashes (privacy-friendly IP storage)
  unique_visitors: defineTable({
    ipHash: v.string(), // SHA-256(IP + salt) - hashed for privacy
    firstVisit: v.number(), // Unix timestamp of first visit
    lastVisit: v.number(), // Unix timestamp of most recent visit
    visitCount: v.number(), // Total number of visits from this IP
  }).index("by_ip_hash", ["ipHash"]), // Fast O(1) lookup by IP hash

  // Sharded counter shards (managed by @convex-dev/sharded-counter)
  // This table automatically created and managed by the sharded counter component
  sharded_counter_shards: defineTable({
    name: v.string(), // Counter name ("visitors")
    count: v.number(), // Current shard count
    shardId: v.number(), // Shard ID (0-15 for 16 shards)
  }).index("by_name_and_shard", ["name", "shardId"]),
})
