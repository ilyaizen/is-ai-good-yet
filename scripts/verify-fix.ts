/**
 * Verify that the backward compatibility fix works
 * This should show that all 1018 articles are now included
 */

import { openPipelineDb } from "./_runtime"

const db = openPipelineDb(true)

console.log("=== Verification: Backward Compatibility Fix ===\n")

// Total AI_DISCOURSE articles (baseline)
const totalStmt = db.prepare(`
  SELECT COUNT(*) as count
  FROM urls
  WHERE content_category = 'AI_DISCOURSE'
    AND sentiment_score IS NOT NULL
    AND hn_score >= 20
`)
const total = (totalStmt.get() as { count: number }).count
console.log(`Total AI_DISCOURSE articles (baseline): ${total}`)

// Articles that pass the NEW filter (with backward compatibility)
const newFilterStmt = db.prepare(`
  SELECT COUNT(*) as count
  FROM urls
  WHERE content_category = 'AI_DISCOURSE'
    AND sentiment_score IS NOT NULL
    AND hn_score >= 20
    AND (
      -- New schema (v4.0+): exclude if topic = 'business'
      (json_extract(classification_json, '$.topic') IS NOT NULL AND json_extract(classification_json, '$.topic') != 'business')
      OR
      -- Old schema (v3): exclude if subtopic = 'business'
      (json_extract(classification_json, '$.topic') IS NULL AND json_extract(classification_json, '$.subtopic') IS NOT NULL AND json_extract(classification_json, '$.subtopic') != 'business')
      OR
      -- No classification JSON yet
      classification_json IS NULL
    )
`)
const included = (newFilterStmt.get() as { count: number }).count
console.log(`Articles passing NEW filter: ${included}`)

// How many business articles are excluded?
const businessNewStmt = db.prepare(`
  SELECT COUNT(*) as count
  FROM urls
  WHERE content_category = 'AI_DISCOURSE'
    AND sentiment_score IS NOT NULL
    AND hn_score >= 20
    AND json_extract(classification_json, '$.topic') = 'business'
`)
const businessNew = (businessNewStmt.get() as { count: number }).count

const businessOldStmt = db.prepare(`
  SELECT COUNT(*) as count
  FROM urls
  WHERE content_category = 'AI_DISCOURSE'
    AND sentiment_score IS NOT NULL
    AND hn_score >= 20
    AND json_extract(classification_json, '$.topic') IS NULL
    AND json_extract(classification_json, '$.subtopic') = 'business'
`)
const businessOld = (businessOldStmt.get() as { count: number }).count

console.log(`\nBusiness articles excluded:`)
console.log(`  - New schema (topic='business'): ${businessNew}`)
console.log(`  - Old schema (subtopic='business'): ${businessOld}`)
console.log(`  - Total excluded: ${businessNew + businessOld}`)

console.log(`\nFinal tally:`)
console.log(`  - Total articles: ${total}`)
console.log(`  - Business excluded: ${businessNew + businessOld}`)
console.log(`  - Included in verdict: ${included}`)
console.log(`  - Expected (total - business): ${total - businessNew - businessOld}`)
console.log(`  - Match: ${included === total - businessNew - businessOld ? "✓ YES" : "✗ NO"}`)

// Check the specific article from the user
console.log("\n=== Specific Article Check (45465098) ===")
const specificStmt = db.prepare(`
  SELECT
    hn_id,
    hn_title,
    CASE
      WHEN json_extract(classification_json, '$.topic') IS NOT NULL AND json_extract(classification_json, '$.topic') != 'business' THEN 'INCLUDED (new schema)'
      WHEN json_extract(classification_json, '$.topic') IS NULL AND json_extract(classification_json, '$.subtopic') IS NOT NULL AND json_extract(classification_json, '$.subtopic') != 'business' THEN 'INCLUDED (old schema)'
      WHEN classification_json IS NULL THEN 'INCLUDED (no json)'
      ELSE 'EXCLUDED'
    END as filter_result
  FROM urls
  WHERE hn_id = 45465098
    AND content_category = 'AI_DISCOURSE'
    AND sentiment_score IS NOT NULL
    AND hn_score >= 20
`)

const specific = specificStmt.get() as
  | {
      hn_id: number
      hn_title: string
      filter_result: string
    }
  | undefined

if (specific) {
  console.log(`ID: ${specific.hn_id}`)
  console.log(`Title: ${specific.hn_title}`)
  console.log(`Filter Result: ${specific.filter_result}`)
} else {
  console.log("Article not found or doesn't meet criteria")
}

db.close()
