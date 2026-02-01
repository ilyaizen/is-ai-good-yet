/**
 * Test that the specific article (45465098) now loads correctly with normalized schema
 */

import { getUrlWithAnalysis } from "../src/lib/server/db"

const testArticleId = 45465098

console.log("=== Testing Article Display ===\n")
console.log(`Testing article ID: ${testArticleId}`)

const article = getUrlWithAnalysis(testArticleId)

if (!article) {
  console.error("❌ Article not found!")
  process.exit(1)
}

console.log("\n✓ Article loaded successfully")
console.log(`Title: ${article.hn_title}`)
console.log(`HN Score: ${article.hn_score}`)
console.log(`Sentiment: ${article.sentiment_score}`)
console.log(`Category: ${article.content_category}`)

if (article.analysis) {
  console.log("\n✓ Analysis data loaded")
  console.log(`Utility: ${article.analysis.utility}`)
  console.log(`Trajectory: ${article.analysis.trajectory}`)
  console.log(`Topic: ${article.analysis.topic}`)
  console.log(`Summary: ${article.analysis.summary}`)
  console.log(`Quotes: ${article.analysis.quotes.length} quotes`)

  if (article.analysis.topic) {
    console.log("\n✓ Topic field is populated (backward compatibility working!)")
  } else {
    console.error("\n❌ Topic field is empty (backward compatibility failed)")
    process.exit(1)
  }

  // Check if old schema fields are preserved
  if (article.analysis.subtopic) {
    console.log(`\nℹ️  Old schema detected:`)
    console.log(`   - subtopic: ${article.analysis.subtopic}`)
    console.log(`   - primary_theme: ${article.analysis.primary_theme}`)
    console.log(`   - secondary_theme: ${article.analysis.secondary_theme}`)
  }
} else {
  console.error("\n❌ Analysis data is null")
  process.exit(1)
}

console.log("\n✅ All tests passed! Article will display correctly on frontend.")
