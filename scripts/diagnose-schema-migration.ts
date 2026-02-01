/**
 * Diagnostic script to check how many articles are affected by the v4.0 schema migration
 * Old schema: subtopic, primary_theme, secondary_theme
 * New schema: topic
 */

import { Database } from "bun:sqlite"
import path from "path"

const dbPath = path.join(process.cwd(), "..", "pipeline", "data", "pipeline.db")
const db = new Database(dbPath, { readonly: true })

console.log("=== V4.0 Schema Migration Diagnostic ===\n")

// Total AI_DISCOURSE articles
const totalStmt = db.prepare(`
  SELECT COUNT(*) as count
  FROM urls
  WHERE content_category = 'AI_DISCOURSE'
    AND sentiment_score IS NOT NULL
    AND hn_score >= 20
`)
const total = (totalStmt.get() as { count: number }).count
console.log(`Total AI_DISCOURSE articles (scored, hn_score >= 20): ${total}`)

// Articles with new schema (has topic field)
const newSchemaStmt = db.prepare(`
  SELECT COUNT(*) as count
  FROM urls
  WHERE content_category = 'AI_DISCOURSE'
    AND sentiment_score IS NOT NULL
    AND hn_score >= 20
    AND classification_json IS NOT NULL
    AND json_extract(classification_json, '$.topic') IS NOT NULL
`)
const newSchema = (newSchemaStmt.get() as { count: number }).count
console.log(`Articles with NEW schema (has topic field): ${newSchema}`)

// Articles with old schema (has subtopic field but no topic)
const oldSchemaStmt = db.prepare(`
  SELECT COUNT(*) as count
  FROM urls
  WHERE content_category = 'AI_DISCOURSE'
    AND sentiment_score IS NOT NULL
    AND hn_score >= 20
    AND classification_json IS NOT NULL
    AND json_extract(classification_json, '$.subtopic') IS NOT NULL
    AND json_extract(classification_json, '$.topic') IS NULL
`)
const oldSchema = (oldSchemaStmt.get() as { count: number }).count
console.log(`Articles with OLD schema (has subtopic, no topic): ${oldSchema}`)

// Articles that pass the current filter (would be included in verdict)
const includedStmt = db.prepare(`
  SELECT COUNT(*) as count
  FROM urls
  WHERE content_category = 'AI_DISCOURSE'
    AND sentiment_score IS NOT NULL
    AND hn_score >= 20
    AND (classification_json IS NULL OR json_extract(classification_json, '$.topic') != 'business')
`)
const included = (includedStmt.get() as { count: number }).count
console.log(`Articles INCLUDED by current filter: ${included}`)

// Articles that fail the current filter (would be excluded)
const excluded = total - included
console.log(`Articles EXCLUDED by current filter: ${excluded}`)

console.log("\n=== Sample Old Schema Articles ===\n")

// Get some examples of old schema articles
const sampleStmt = db.prepare(`
  SELECT
    hn_id,
    hn_title,
    hn_score,
    sentiment_score,
    json_extract(classification_json, '$.subtopic') as subtopic,
    json_extract(classification_json, '$.primary_theme') as primary_theme,
    json_extract(classification_json, '$.topic') as topic
  FROM urls
  WHERE content_category = 'AI_DISCOURSE'
    AND sentiment_score IS NOT NULL
    AND hn_score >= 20
    AND classification_json IS NOT NULL
    AND json_extract(classification_json, '$.subtopic') IS NOT NULL
    AND json_extract(classification_json, '$.topic') IS NULL
  ORDER BY hn_score DESC
  LIMIT 5
`)

const samples = sampleStmt.all() as Array<{
  hn_id: number
  hn_title: string
  hn_score: number
  sentiment_score: number
  subtopic: string | null
  primary_theme: string | null
  topic: string | null
}>

samples.forEach((article) => {
  console.log(`ID: ${article.hn_id}`)
  console.log(`Title: ${article.hn_title}`)
  console.log(`HN Score: ${article.hn_score}`)
  console.log(`Sentiment: ${article.sentiment_score}`)
  console.log(`Old subtopic: ${article.subtopic}`)
  console.log(`Old primary_theme: ${article.primary_theme}`)
  console.log(`New topic: ${article.topic}`)
  console.log(`URL: http://localhost:3050/details/${article.hn_id}`)
  console.log("---")
})

// Check the specific article the user mentioned
console.log("\n=== Specific Article Check (45465098) ===\n")
const specificStmt = db.prepare(`
  SELECT
    hn_id,
    hn_title,
    hn_score,
    hn_comments,
    sentiment_score,
    content_category,
    classification_json
  FROM urls
  WHERE hn_id = 45465098
`)

const specific = specificStmt.get() as
  | {
      hn_id: number
      hn_title: string
      hn_score: number
      hn_comments: number
      sentiment_score: number | null
      content_category: string | null
      classification_json: string | null
    }
  | undefined

if (specific) {
  console.log(`ID: ${specific.hn_id}`)
  console.log(`Title: ${specific.hn_title}`)
  console.log(`HN Score: ${specific.hn_score}`)
  console.log(`HN Comments: ${specific.hn_comments}`)
  console.log(`Sentiment: ${specific.sentiment_score}`)
  console.log(`Category: ${specific.content_category}`)
  if (specific.classification_json) {
    const json = JSON.parse(specific.classification_json)
    console.log(`Classification JSON:`, JSON.stringify(json, null, 2))
  }
} else {
  console.log("Article not found in database")
}

db.close()
