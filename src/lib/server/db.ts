import Database from "better-sqlite3"
import path from "path"
import { NEUTRAL_MULTIPLIER } from "$lib/constants"
import { existsSync } from "fs"
import { fileURLToPath } from "url"

const DB_PATH = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../pipeline/data/pipeline.db")

let _db: Database.Database | null = null

export function getDb(): Database.Database {
  if (_db !== null) {
    return _db
  }

  // Check if database file exists before trying to open it
  if (!existsSync(DB_PATH)) {
    throw new Error(`Database file not found at ${DB_PATH}`)
  }

  _db = new Database(DB_PATH)
  return _db
}

// Export db for backward compatibility, but make it lazy
export const db = new Proxy({} as Database.Database, {
  get(_target, prop) {
    const dbInstance = getDb()
    return dbInstance[prop as keyof Database.Database]
  },
})

export type UrlEntry = {
  id: number
  url: string
  hn_id: number | null
  hn_score: number | null
  hn_comments: number | null
  hn_title: string | null
  hn_timestamp: number | null
  hn_author: string | null
  status: string
  scraped_status: string | null
  filter_score: number | null
  opinion: string | null
  is_opinion: boolean | null
  sentiment_score: number | null
  content_category: string | null
  content_confidence: number | null
  classification_json: string | null
  content_filter_json: string | null
}

export function getLastCatchUp(): number | null {
  const stmt = db.prepare("SELECT value FROM prefilter_state WHERE key = 'last_catch_up'")
  const result = stmt.get() as { value: string } | undefined
  if (result) {
    return parseInt(result.value, 10)
  }
  return null
}

export function getTimeAgo(timestamp: number): string {
  const now = Date.now() / 1000
  const diff = now - timestamp

  const minute = 60
  const hour = 60 * minute
  const day = 24 * hour
  const week = 7 * day
  const month = 30 * day
  const year = 365 * day

  if (diff < minute) {
    return "just now"
  } else if (diff < hour) {
    const minutes = Math.floor(diff / minute)
    return `${minutes}m ago`
  } else if (diff < day) {
    const hours = Math.floor(diff / hour)
    return `${hours}h ago`
  } else if (diff < week) {
    const days = Math.floor(diff / day)
    return `${days}d ago`
  } else if (diff < month) {
    const weeks = Math.floor(diff / week)
    return `${weeks}w ago`
  } else if (diff < year) {
    const months = Math.floor(diff / month)
    return `${months}mo ago`
  } else {
    const years = Math.floor(diff / year)
    return `${years}y ago`
  }
}

export function getPendingUrls(): UrlEntry[] {
  const stmt = db.prepare("SELECT * FROM urls WHERE status = ? OR status = ? ORDER BY hn_score DESC LIMIT 100")
  return stmt.all("pending", "resolved") as UrlEntry[]
}

export function getAllUrls(): UrlEntry[] {
  const stmt = db.prepare("SELECT * FROM urls ORDER BY hn_score DESC")
  return stmt.all() as UrlEntry[]
}

export function getPipelineTableData(): UrlEntry[] {
  try {
    const db = getDb()
    const stmt = db.prepare("SELECT * FROM urls ORDER BY hn_timestamp DESC")
    return stmt.all() as UrlEntry[]
  } catch (error) {
    // Return empty array if database is not available (e.g., during build)
    return []
  }
}

export type VerdictStats = {
  averageSentiment: number // Weighted by engagement
  positiveWeight: number // Weighted sum for positive articles
  negativeWeight: number // Weighted sum for negative articles
  neutralWeight: number // Weighted sum for neutral articles
  totalAnalyzed: number // Raw count
  positiveCount: number // Raw count
  negativeCount: number // Raw count
  neutralCount: number // Raw count
}

export function getVerdictStats(): VerdictStats {
  // Weighted sentiment calculation using POWER LAW + DECAY weighting
  const stmt = db.prepare(`
    SELECT
      sentiment_score,
      hn_score,
      hn_comments,
      hn_timestamp
    FROM urls
    WHERE sentiment_score IS NOT NULL
      AND content_category = 'AI_DISCOURSE'
      AND hn_score IS NOT NULL
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

  const articles = stmt.all() as Array<{
    sentiment_score: number
    hn_score: number
    hn_comments: number
    hn_timestamp: number
  }>

  // Calculate power law + decay weighted sums
  // IMPORTANT: All articles (positive, negative, neutral) now contribute to verdict calculation
  // Neutral articles (-0.2 to +0.2) use NEUTRAL_MULTIPLIER to adjust their contribution
  let totalWeightedSentiment = 0
  let totalWeight = 0
  let positiveWeight = 0
  let negativeWeight = 0
  let neutralWeight = 0
  let positiveCount = 0
  let negativeCount = 0
  let neutralCount = 0

  for (const article of articles) {
    // For category weights, use base influence (for bar heights)
    // Weight = influence score (power law + decay)
    // Contribution = sentiment × influence (same as articles table)
    const baseWeight = calculateInfluenceScore(article.hn_score, article.hn_timestamp)

    if (article.sentiment_score > 0.2) {
      // POSITIVE: Include in verdict calculation at full strength
      totalWeightedSentiment += article.sentiment_score * baseWeight
      totalWeight += baseWeight
      positiveWeight += baseWeight
      positiveCount += 1
    } else if (article.sentiment_score < -0.2) {
      // NEGATIVE: Include in verdict calculation at full strength
      totalWeightedSentiment += article.sentiment_score * baseWeight
      totalWeight += baseWeight
      negativeWeight += baseWeight
      negativeCount += 1
    } else {
      // NEUTRAL: Use influence directly (sentiment is always 0 for mixed+uncertain)
      // Contribution = influence × NEUTRAL_MULTIPLIER (negative since multiplier = -0.5)
      const neutralContribution = baseWeight * NEUTRAL_MULTIPLIER
      totalWeightedSentiment += neutralContribution
      totalWeight += baseWeight * Math.abs(NEUTRAL_MULTIPLIER)
      neutralWeight += baseWeight
      neutralCount += 1
    }
  }

  const result = {
    avg_sentiment: totalWeight > 0 ? totalWeightedSentiment / totalWeight : 0,
    positive_weight: positiveWeight,
    negative_weight: negativeWeight,
    neutral_weight: neutralWeight,
    total: articles.length,
    positive_count: positiveCount,
    negative_count: negativeCount,
    neutral_count: neutralCount,
  }

  return {
    averageSentiment: result.avg_sentiment || 0,
    positiveWeight: result.positive_weight || 0,
    negativeWeight: result.negative_weight || 0,
    neutralWeight: result.neutral_weight || 0,
    totalAnalyzed: result.total || 0,
    positiveCount: result.positive_count || 0,
    negativeCount: result.negative_count || 0,
    neutralCount: result.neutral_count || 0,
  }
}

export type PipelineStats = {
  totalUrls: number
  resolved: number
  scraped: number
  relevant: number
  analyzed: number
  failed: number
}

export function getPipelineStats(): PipelineStats {
  try {
    const db = getDb()
    const stmt = db.prepare(`
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN hn_id IS NOT NULL THEN 1 ELSE 0 END) as resolved,
            SUM(CASE WHEN scraped_status = 'success' THEN 1 ELSE 0 END) as scraped,
            SUM(CASE
                WHEN hn_score >= 20
                AND hn_comments >= 5
                AND scraped_status = 'success'
                AND content_category = 'AI_DISCOURSE'
                THEN 1 ELSE 0
            END) as relevant,
            SUM(CASE WHEN sentiment_score IS NOT NULL THEN 1 ELSE 0 END) as analyzed,
            SUM(CASE WHEN scraped_status = 'failed' THEN 1 ELSE 0 END) as failed
        FROM urls
    `)

    const result = stmt.get() as {
      total: number
      resolved: number
      scraped: number
      relevant: number
      analyzed: number
      failed: number
    }

    return {
      totalUrls: result.total || 0,
      resolved: result.resolved || 0,
      scraped: result.scraped || 0,
      relevant: result.relevant || 0,
      analyzed: result.analyzed || 0,
      failed: result.failed || 0,
    }
  } catch (error) {
    // Return empty stats if database is not available (e.g., during build)
    return {
      totalUrls: 0,
      resolved: 0,
      scraped: 0,
      relevant: 0,
      analyzed: 0,
      failed: 0,
    }
  }
}

export type TimelineDataPoint = {
  date: string
  positive: number // Weighted sum (for bar heights)
  negative: number // Weighted sum (for bar heights)
  neutral: number // Weighted sum (for bar heights)
  positiveCount: number // Raw count (for tooltips)
  negativeCount: number // Raw count (for tooltips)
  neutralCount: number // Raw count (for tooltips)
  unanalyzed: number
  total: number
  averageSentiment: number // Weighted average
}

export function getTimelineStats(): TimelineDataPoint[] {
  // Weighted timeline stats using POWER LAW + DECAY weighting
  const stmt = db.prepare(`
    SELECT
      strftime('%Y-%W', datetime(hn_timestamp, 'unixepoch')) as date,
      sentiment_score,
      hn_score,
      hn_comments,
      hn_timestamp
    FROM urls
    WHERE hn_timestamp IS NOT NULL
      AND hn_score >= 20
      AND hn_comments >= 5
      AND content_category = 'AI_DISCOURSE'
      AND scraped_status = 'success'
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
    ORDER BY hn_timestamp ASC
  `)

  const rawArticles = stmt.all() as Array<{
    date: string
    sentiment_score: number
    hn_score: number
    hn_comments: number
    hn_timestamp: number
  }>

  // Apply power law + decay weighting
  const articles = rawArticles.map((a) => ({
    ...a,
    engagement_weight: calculateInfluenceScore(a.hn_score, a.hn_timestamp),
  }))

  // Group by week/date
  const dateData = new Map<
    string,
    {
      date: string
      positive: number
      negative: number
      neutral: number
      positive_count: number
      negative_count: number
      neutral_count: number
      unanalyzed: number
      total: number
      weighted_sentiment_sum: number
      total_weight: number
    }
  >()

  for (const article of articles) {
    if (!dateData.has(article.date)) {
      dateData.set(article.date, {
        date: article.date,
        positive: 0,
        negative: 0,
        neutral: 0,
        positive_count: 0,
        negative_count: 0,
        neutral_count: 0,
        unanalyzed: 0,
        total: 0,
        weighted_sentiment_sum: 0,
        total_weight: 0,
      })
    }

    const data = dateData.get(article.date)!
    data.total += 1

    if (article.sentiment_score === null) {
      data.unanalyzed += 1
    } else {
      // IMPORTANT: All articles (positive, negative, neutral) now contribute to verdict calculation
      // Neutral articles (-0.2 to +0.2) use NEUTRAL_MULTIPLIER to adjust their contribution
      // Weight = influence score (power law + decay)
      // Contribution = sentiment × influence (same as articles table)
      if (article.sentiment_score > 0.2) {
        // POSITIVE: Include in verdict calculation at full strength
        data.total_weight += article.engagement_weight
        data.weighted_sentiment_sum += article.sentiment_score * article.engagement_weight
        data.positive += article.engagement_weight
        data.positive_count += 1
      } else if (article.sentiment_score < -0.2) {
        // NEGATIVE: Include in verdict calculation at full strength
        data.total_weight += article.engagement_weight
        data.weighted_sentiment_sum += article.sentiment_score * article.engagement_weight
        data.negative += article.engagement_weight
        data.negative_count += 1
      } else {
        // NEUTRAL: Use influence directly (sentiment is always 0 for mixed+uncertain)
        // Contribution = influence × NEUTRAL_MULTIPLIER (negative since multiplier = -0.5)
        const neutralContribution = article.engagement_weight * NEUTRAL_MULTIPLIER
        data.total_weight += article.engagement_weight * Math.abs(NEUTRAL_MULTIPLIER)
        data.weighted_sentiment_sum += neutralContribution
        data.neutral += article.engagement_weight
        data.neutral_count += 1
      }
    }
  }

  const results = Array.from(dateData.values()).sort((a, b) => a.date.localeCompare(b.date)) as {
    date: string
    positive: number
    negative: number
    neutral: number
    positive_count: number
    negative_count: number
    neutral_count: number
    unanalyzed: number
    total: number
    weighted_sentiment_sum: number
    total_weight: number
  }[]

  const mapped = results.map((r) => ({
    date: r.date,
    positive: r.positive || 0,
    negative: r.negative || 0,
    neutral: r.neutral || 0,
    positiveCount: r.positive_count || 0,
    negativeCount: r.negative_count || 0,
    neutralCount: r.neutral_count || 0,
    unanalyzed: r.unanalyzed || 0,
    total: r.total || 0,
    averageSentiment: r.total_weight > 0 ? r.weighted_sentiment_sum / r.total_weight : 0,
  }))

  return mapped
}

export function getUrlByHnId(hnId: number): UrlEntry | undefined {
  const stmt = db.prepare("SELECT * FROM urls WHERE hn_id = ?")
  return stmt.get(hnId) as UrlEntry | undefined
}

export type SentimentAnalysis = {
  utility: "magic" | "tool" | "mixed" | "toil" | "hazard"
  trajectory: "optimistic" | "uncertain" | "pessimistic"
  topic: string // v4.0+ uses single 'topic' field, backward compatible with v3 'subtopic'
  summary: string
  quotes: string[]
  // Legacy fields (v3 schema) - for reference only, not displayed
  subtopic?: string
  primary_theme?: string
  secondary_theme?: string
}

export type UrlWithAnalysis = UrlEntry & {
  analysis: SentimentAnalysis | null
}

// Helper to normalize analysis JSON from old schema (v3) to new schema (v4)
function normalizeAnalysis(raw: any): SentimentAnalysis {
  // If using new schema (v4.0+), return as-is
  if (raw.topic) {
    return raw as SentimentAnalysis
  }

  // Convert old schema (v3) to new schema
  return {
    ...raw,
    topic: raw.subtopic || raw.primary_theme || "", // Fall back to subtopic or primary_theme
  } as SentimentAnalysis
}

export function getUrlWithAnalysis(hnId: number): UrlWithAnalysis | undefined {
  const entry = getUrlByHnId(hnId)
  if (!entry) return undefined

  let analysis: SentimentAnalysis | null = null
  if (entry.classification_json) {
    try {
      const raw = JSON.parse(entry.classification_json)
      analysis = normalizeAnalysis(raw)
    } catch {
      analysis = null
    }
  }

  return { ...entry, analysis }
}

export type SummaryEntry = {
  hn_id: number
  hn_title: string
  sentiment_score: number
  topic: string
  summary: string
}

export function getSummariesList(): SummaryEntry[] {
  const stmt = db.prepare(`
    SELECT hn_id, hn_title, sentiment_score, classification_json
    FROM urls
    WHERE classification_json IS NOT NULL
      AND content_category = 'AI_DISCOURSE'
      AND sentiment_score IS NOT NULL
    ORDER BY hn_timestamp DESC
  `)

  const rows = stmt.all() as Array<{
    hn_id: number
    hn_title: string
    sentiment_score: number
    classification_json: string
  }>

  return rows
    .map((row) => {
      try {
        const raw = JSON.parse(row.classification_json)
        const analysis = normalizeAnalysis(raw)
        return {
          hn_id: row.hn_id,
          hn_title: row.hn_title || "Untitled",
          sentiment_score: row.sentiment_score,
          topic: analysis.topic || "",
          summary: analysis.summary || "",
        }
      } catch {
        return null
      }
    })
    .filter((entry): entry is SummaryEntry => entry !== null && entry.summary.length > 0)
}

export type ThemeEntry = {
  id: number
  sentiment_group: "positive" | "neutral" | "negative"
  theme_title: string
  theme_description: string
  sentiment_verdict: string
  article_count: number
}

export function getThemes(): ThemeEntry[] {
  try {
    const stmt = db.prepare(`
      SELECT id, sentiment_group, theme_title, theme_description, sentiment_verdict, article_count
      FROM themes
      ORDER BY article_count DESC
      LIMIT 8
    `)

    return stmt.all() as ThemeEntry[]
  } catch {
    // Table might not exist yet
    return []
  }
}

// ============================================
// VERDICT SCORING SYSTEM
// ============================================
//
// Articles are weighted by their HN engagement using POWER LAW + DECAY.
// A 4000-upvote article has ~91x more influence than a 20-upvote article.
// Articles lose 50% influence over 24 months.
//
// ENGAGEMENT WEIGHT FORMULA:
// engagement_weight = hn_score^0.85 × 0.5^(months_ago / 24)
//
// SENTIMENT SCALE:
// The sentiment analyzer uses utility (5-tier) × trajectory (3-tier) dimensions:
//   utility:    magic(+2.0), tool(+1.0), mixed(0), toil(-1.0), hazard(-2.0)
//   trajectory: optimistic(+2.0), uncertain(0), pessimistic(-2.0)
//   formula:    sentiment = utility × 0.5 + trajectory × 0.5
//
// This creates a full range of -2.0 to +2.0:
//   Max: magic(2.0) × 0.5 + optimistic(2.0) × 0.5 = +2.0
//   Min: hazard(-2.0) × 0.5 + pessimistic(-2.0) × 0.5 = -2.0
//
// CONTRIBUTION CALCULATION:
// Each article's contribution = sentiment × influence
//   - Positive articles (sentiment > 0.2) contribute positive values
//   - Negative articles (sentiment < -0.2) contribute negative values
//   - Neutral articles (sentiment between -0.2 and 0.2) are excluded
//
// VERDICT SCORE FORMULA (Contribution Ratio):
// score = |positiveContribution| / (|positiveContribution| + |negativeContribution|) × 100
//   - 50 = balanced (equal positive and negative contributions)
//   - 100 = all positive contributions
//   - 0 = all negative contributions
//
// Example: If +83k positive contribution and -66k negative contribution:
//   score = 83k / (83k + 66k) = 83k / 149k ≈ 55.7%
// ============================================

// ============================================
// CONFIGURABLE PARAMETERS
// ============================================

/** How many months of history to display in the timeline visualization */
const TIMELINE_DISPLAY_MONTHS = 48

/** How many months of history to include in the PRIMARY verdict calculation */
const VERDICT_WINDOW_MONTHS = 12

// ============================================
// SENTIMENT SCALE BOUNDS
// ============================================
// These match the sentiment_analyzer.py formula:
//   score = (utility_score × 0.5) + (trajectory_score × 0.5)
// where utility ∈ [-2.0, +2.0] and trajectory ∈ [-2.0, +2.0]

const SENTIMENT_MIN = -2.0 // hazard(-2.0) × 0.5 + pessimistic(-2.0) × 0.5
const SENTIMENT_MAX = 2.0 // magic(+2.0) × 0.5 + optimistic(+2.0) × 0.5
const SENTIMENT_RANGE = SENTIMENT_MAX - SENTIMENT_MIN // 4.0

/**
 * Map raw sentiment (-2.0 to +2.0) to display score (0 to 100)
 * Uses the full range from the utility×trajectory formula
 */
function sentimentToScore(sentiment: number): number {
  // Clamp to valid range
  const clamped = Math.max(SENTIMENT_MIN, Math.min(SENTIMENT_MAX, sentiment))
  // Map to 0-100
  return ((clamped - SENTIMENT_MIN) / SENTIMENT_RANGE) * 100
}

// ============================================
// INFLUENCE SCORING (Power Law + Decay)
// ============================================
// Formula: influence = hn_score^0.85 × decay_factor
// Decay factor: 0.5^(months_ago / 24)
// This means articles from 2 years ago have 50% influence
//
// WEIGHTED SENTIMENT CALCULATION:
// Each article contributes: sentiment_score × influence_score
// Final sentiment = sum(sentiment × influence) / sum(influence)
//
// Example with 1000 upvotes, recent article (influence = 355):
//   - sentiment +0.9 → contributes +319.5 to weighted sum
//   - sentiment +0.2 → contributes +71 to weighted sum
//   - sentiment -0.8 → contributes -284 to weighted sum
//
// This is the same formula displayed in the Articles table.

/**
 * Calculate decay factor for articles based on age.
 * Half-life is 24 months: articles from 2 years ago have 50% influence.
 * Formula: decay_factor = 0.5^(months_ago / 24)
 */
function getDecayFactor(timestampSeconds: number): number {
  const now = Date.now() / 1000 // Current time in seconds
  const ageSeconds = now - timestampSeconds
  const ageMonths = ageSeconds / (30.44 * 24 * 3600) // Convert to months (30.44 = avg days per month)
  const decayFactor = Math.pow(0.5, ageMonths / 24)
  return decayFactor
}

/**
 * Calculate BASE influence score using power law + decay.
 * This is the raw engagement influence BEFORE sentiment magnitude scaling.
 * Formula: influence = hn_score^0.85 × decay_factor
 * Example: 1000 upvotes today = 355 influence
 *          1000 upvotes 2 years ago = 178 influence (50% decay)
 */
function calculateInfluenceScore(hnScore: number, timestampSeconds: number): number {
  const powerLaw = Math.pow(hnScore, 0.85)
  const decayFactor = getDecayFactor(timestampSeconds)
  return powerLaw * decayFactor
}

/**
 * Calculate the weighted contribution of an article to the verdict.
 * Formula: contribution = sentiment_score × influence_score
 * This is the same calculation shown in the Articles table.
 *
 * @param hnScore - HN upvotes
 * @param timestampSeconds - Unix timestamp
 * @param sentimentScore - Sentiment from -2.0 to +2.0
 * @returns Weighted contribution (can be negative for negative sentiment)
 */
function calculateWeightedContribution(hnScore: number, timestampSeconds: number, sentimentScore: number): number {
  const influence = calculateInfluenceScore(hnScore, timestampSeconds)
  return sentimentScore * influence
}

export type VerdictScore = {
  // Final answer
  verdict: "YES" | "NO" | "NOT_YET"
  verdictConfidence: "high" | "medium" | "low"

  // Core metrics (0-100 scale)
  finalScore: number // The final score (0-100, 50 = neutral)
  rawSentiment: number // Weighted average sentiment before scaling (-2.0 to +2.0)

  // Trajectory analysis
  momentum: number // -1 to +1 (negative = declining, positive = improving)
  momentumLabel: "improving" | "stable" | "declining"
  recentSentiment: number // Last 3 months weighted sentiment
  previousSentiment: number // Previous 3 months weighted sentiment

  // Raw counts (unweighted)
  totalAnalyzed: number
  positiveCount: number
  negativeCount: number
  neutralCount: number

  // Weighted influence (linear engagement weight)
  positiveInfluence: number // Sum of weights for positive articles
  negativeInfluence: number // Sum of weights for negative articles
  neutralInfluence: number // Sum of weights for neutral articles
  totalInfluence: number // Total weight

  // Contribution totals (sentiment × influence)
  positiveContribution: number // Sum of (sentiment × influence) for positive articles
  negativeContribution: number // Sum of (sentiment × influence) for negative articles
  neutralContribution: number // Sum of (influence × NEUTRAL_MULTIPLIER) for neutral articles

  // Engagement metrics
  totalEngagement: number // Sum of all HN scores
  averageEngagement: number // Average HN score per article

  // Time range
  oldestArticleDate: string
  newestArticleDate: string
  monthsAnalyzed: number

  // Monthly breakdown for transparency
  monthlyBreakdown: Array<{
    month: string
    sentiment: number // Weighted average sentiment for the month
    weight: number // Total weight for this month
    articleCount: number
  }>
}

export function getVerdictScore(): VerdictScore {
  const now = new Date()

  // Calculate cutoff for rolling window (VERDICT_WINDOW_MONTHS)
  const verdictCutoff = new Date(now)
  verdictCutoff.setMonth(verdictCutoff.getMonth() - VERDICT_WINDOW_MONTHS)
  const verdictCutoffTimestamp = Math.floor(verdictCutoff.getTime() / 1000)

  // Step 1: Get articles within the verdict window (recency-focused)
  // Weight = hn_score^0.85 × decay_factor (POWER LAW + DECAY)
  const articlesStmt = db.prepare(`
    SELECT
      strftime('%Y-%m', datetime(hn_timestamp, 'unixepoch')) as month,
      sentiment_score,
      hn_score,
      hn_comments,
      hn_timestamp,
      datetime(hn_timestamp, 'unixepoch') as article_date
    FROM urls
    WHERE sentiment_score IS NOT NULL
      AND content_category = 'AI_DISCOURSE'
      AND hn_score IS NOT NULL
      AND hn_score >= 20
      AND hn_timestamp IS NOT NULL
      AND hn_timestamp >= ?
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
    ORDER BY hn_timestamp ASC
  `)

  const articles = articlesStmt.all(verdictCutoffTimestamp) as Array<{
    month: string
    sentiment_score: number
    hn_score: number
    hn_comments: number
    hn_timestamp: number
    article_date: string
  }>

  // Apply power law + decay weighting in JavaScript
  const articlesWithWeight = articles.map((a) => ({
    ...a,
    engagement_weight: calculateInfluenceScore(a.hn_score, a.hn_timestamp),
  }))

  // Get overall stats for counts (within the same window)
  const statsStmt = db.prepare(`
    SELECT
      COUNT(*) as total,
      SUM(CASE WHEN sentiment_score > 0.2 THEN 1 ELSE 0 END) as positive_count,
      SUM(CASE WHEN sentiment_score < -0.2 THEN 1 ELSE 0 END) as negative_count,
      SUM(CASE WHEN sentiment_score >= -0.2 AND sentiment_score <= 0.2 THEN 1 ELSE 0 END) as neutral_count,
      SUM(hn_score) as total_engagement,
      AVG(hn_score) as avg_engagement,
      MIN(datetime(hn_timestamp, 'unixepoch')) as oldest_date,
      MAX(datetime(hn_timestamp, 'unixepoch')) as newest_date
    FROM urls
    WHERE sentiment_score IS NOT NULL
      AND content_category = 'AI_DISCOURSE'
      AND hn_score IS NOT NULL
      AND hn_score >= 20
      AND hn_timestamp IS NOT NULL
      AND hn_timestamp >= ?
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

  const stats = statsStmt.get(verdictCutoffTimestamp) as {
    total: number
    positive_count: number
    negative_count: number
    neutral_count: number
    total_engagement: number
    avg_engagement: number
    oldest_date: string
    newest_date: string
  }

  // Step 2: Group by month and calculate weighted sentiment per month
  const monthlyData = new Map<
    string,
    {
      totalWeight: number
      weightedSentimentSum: number
      positiveWeight: number
      negativeWeight: number
      neutralWeight: number
      positiveContribution: number // Sum of (sentiment × influence) for positive articles
      negativeContribution: number // Sum of (sentiment × influence) for negative articles
      neutralContribution: number // Sum of (influence × NEUTRAL_MULTIPLIER) for neutral articles
      articleCount: number
    }
  >()

  for (const article of articlesWithWeight) {
    const baseWeight = article.engagement_weight // POWER LAW + DECAY weight (for category bars)

    if (!monthlyData.has(article.month)) {
      monthlyData.set(article.month, {
        totalWeight: 0,
        weightedSentimentSum: 0,
        positiveWeight: 0,
        negativeWeight: 0,
        neutralWeight: 0,
        positiveContribution: 0,
        negativeContribution: 0,
        neutralContribution: 0,
        articleCount: 0,
      })
    }

    const data = monthlyData.get(article.month)!
    data.articleCount += 1

    // IMPORTANT: All articles (positive, negative, neutral) now contribute to verdict calculation
    // Neutral articles (-0.2 to +0.2) use NEUTRAL_MULTIPLIER to adjust their contribution
    // Weight = influence score (power law + decay)
    // Contribution = sentiment × influence (same as articles table)
    if (article.sentiment_score > 0.2) {
      // POSITIVE: Include in verdict calculation at full strength
      const contribution = article.sentiment_score * baseWeight
      data.totalWeight += baseWeight
      data.weightedSentimentSum += contribution
      data.positiveWeight += baseWeight
      data.positiveContribution += contribution
    } else if (article.sentiment_score < -0.2) {
      // NEGATIVE: Include in verdict calculation at full strength
      const contribution = article.sentiment_score * baseWeight
      data.totalWeight += baseWeight
      data.weightedSentimentSum += contribution
      data.negativeWeight += baseWeight
      data.negativeContribution += contribution
    } else {
      // NEUTRAL: Use influence directly (sentiment is always 0 for mixed+uncertain)
      // Contribution = influence × NEUTRAL_MULTIPLIER (negative since multiplier = -0.5)
      const contribution = baseWeight * NEUTRAL_MULTIPLIER
      data.totalWeight += baseWeight * Math.abs(NEUTRAL_MULTIPLIER)
      data.weightedSentimentSum += contribution
      data.neutralWeight += baseWeight
      data.neutralContribution += contribution
    }
  }

  // Step 3: Aggregate all months (no decay - all history counts equally)
  let totalWeight = 0
  let totalWeightedSentiment = 0
  let positiveInfluence = 0
  let negativeInfluence = 0
  let neutralInfluence = 0
  let positiveContribution = 0
  let negativeContribution = 0
  let neutralContribution = 0

  const monthlyBreakdown: VerdictScore["monthlyBreakdown"] = []

  // Sort months chronologically
  const sortedMonths = Array.from(monthlyData.keys()).sort()

  for (const month of sortedMonths) {
    const data = monthlyData.get(month)!

    const monthSentiment = data.totalWeight > 0 ? data.weightedSentimentSum / data.totalWeight : 0

    totalWeight += data.totalWeight
    totalWeightedSentiment += data.weightedSentimentSum

    positiveInfluence += data.positiveWeight
    negativeInfluence += data.negativeWeight
    neutralInfluence += data.neutralWeight
    positiveContribution += data.positiveContribution
    negativeContribution += data.negativeContribution
    neutralContribution += data.neutralContribution || 0

    monthlyBreakdown.push({
      month,
      sentiment: monthSentiment,
      weight: data.totalWeight,
      articleCount: data.articleCount,
    })
  }

  // Step 4: Calculate final weighted sentiment (for momentum calculation)
  const rawSentiment = totalWeight > 0 ? totalWeightedSentiment / totalWeight : 0

  // Step 5: Calculate score using CONTRIBUTION RATIO formula
  // This directly reflects the balance of positive vs negative contributions:
  // Score = |positiveContribution| / (|positiveContribution| + |negativeContribution|) × 100
  // - 50 = balanced (equal positive and negative contributions)
  // - 100 = all positive contributions
  // - 0 = all negative contributions
  const absPositive = Math.abs(positiveContribution)
  const absNegative = Math.abs(negativeContribution)
  const totalAbsContribution = absPositive + absNegative
  const finalScore = totalAbsContribution > 0 ? (absPositive / totalAbsContribution) * 100 : 50

  // Step 6: Calculate momentum (compare recent 3 months vs previous 3 months)
  const recentMonths = monthlyBreakdown.slice(-3)
  const previousMonths = monthlyBreakdown.slice(-6, -3)

  function calculatePeriodSentiment(months: typeof monthlyBreakdown): number {
    const periodWeight = months.reduce((sum, m) => sum + m.weight, 0)
    const weightedSum = months.reduce((sum, m) => sum + m.sentiment * m.weight, 0)
    return periodWeight > 0 ? weightedSum / periodWeight : 0
  }

  const recentSentiment = calculatePeriodSentiment(recentMonths)
  const previousSentiment = previousMonths.length >= 2 ? calculatePeriodSentiment(previousMonths) : recentSentiment

  // Momentum: difference in sentiment scaled
  // A 0.2 sentiment swing = 1.0 momentum (full swing)
  const rawMomentum = (recentSentiment - previousSentiment) / 0.2
  const momentum = Math.max(-1, Math.min(1, rawMomentum))

  // Determine momentum label
  let momentumLabel: "improving" | "stable" | "declining"
  if (momentum > 0.15) {
    momentumLabel = "improving"
  } else if (momentum < -0.15) {
    momentumLabel = "declining"
  } else {
    momentumLabel = "stable"
  }

  // Step 7: Determine final verdict
  // YES: finalScore >= 55 (passing grade)
  // NO: finalScore < 45
  // NOT_YET: 45-55 (too close to call)
  let verdict: "YES" | "NO" | "NOT_YET"
  if (finalScore >= 55) {
    verdict = "YES"
  } else if (finalScore < 45) {
    verdict = "NO"
  } else {
    verdict = "NOT_YET"
  }

  // Step 8: Determine confidence
  // Based on data volume and score distance from threshold
  let verdictConfidence: "high" | "medium" | "low"
  const scoreDistance = Math.abs(finalScore - 50)
  const dataCount = stats.total || 0

  if (scoreDistance > 15 && dataCount >= 100) {
    verdictConfidence = "high"
  } else if (scoreDistance > 8 || dataCount >= 50) {
    verdictConfidence = "medium"
  } else {
    verdictConfidence = "low"
  }

  return {
    verdict,
    verdictConfidence,
    finalScore,
    rawSentiment,
    momentum,
    momentumLabel,
    recentSentiment,
    previousSentiment,
    totalAnalyzed: stats.total || 0,
    positiveCount: stats.positive_count || 0,
    negativeCount: stats.negative_count || 0,
    neutralCount: stats.neutral_count || 0,
    positiveInfluence,
    negativeInfluence,
    neutralInfluence,
    totalInfluence: totalWeight,
    positiveContribution,
    negativeContribution,
    neutralContribution,
    totalEngagement: stats.total_engagement || 0,
    averageEngagement: stats.avg_engagement || 0,
    oldestArticleDate: stats.oldest_date || "",
    newestArticleDate: stats.newest_date || "",
    monthsAnalyzed: monthlyBreakdown.length,
    monthlyBreakdown,
  }
}

// ============================================
// STACKED TIMELINE DATA FOR VISUALIZATION
// ============================================
// Weekly data with POWER LAW + DECAY engagement weighting for stacked bar charts
// Shows positive/neutral/negative influence over time

export type WeeklyVerdictData = {
  week: string
  month: string // For grouping labels (YYYY-MM)

  // Weighted values (LINEAR engagement weighting) - for stacked bar heights
  positiveWeight: number
  negativeWeight: number
  neutralWeight: number
  totalWeight: number

  // Normalized percentages (for 100% stacked bars)
  positivePercent: number
  negativePercent: number
  neutralPercent: number

  // Raw counts (for tooltips)
  positiveCount: number
  negativeCount: number
  neutralCount: number
  totalCount: number

  // Weekly sentiment (weighted average)
  sentiment: number // -2.0 to +2.0
  sentimentScore: number // 0-100 scale
}

export function getWeeklyVerdictData(): WeeklyVerdictData[] {
  const now = new Date()
  const displayCutoff = new Date(now)
  displayCutoff.setMonth(displayCutoff.getMonth() - TIMELINE_DISPLAY_MONTHS)
  const cutoffTimestamp = Math.floor(displayCutoff.getTime() / 1000)

  // Use POWER LAW + DECAY weighting: hn_score^0.85 × decay_factor
  const stmt = db.prepare(`
    SELECT
      strftime('%Y-%W', datetime(hn_timestamp, 'unixepoch')) as week,
      strftime('%Y-%m', datetime(hn_timestamp, 'unixepoch')) as month,
      sentiment_score,
      hn_score,
      hn_comments,
      hn_timestamp
    FROM urls
    WHERE sentiment_score IS NOT NULL
      AND content_category = 'AI_DISCOURSE'
      AND hn_score IS NOT NULL
      AND hn_score >= 20
      AND hn_timestamp IS NOT NULL
      AND hn_timestamp >= ?
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

  const rawArticles = stmt.all(cutoffTimestamp) as Array<{
    week: string
    month: string
    sentiment_score: number
    hn_score: number
    hn_comments: number
    hn_timestamp: number
  }>

  // Apply power law + decay weighting
  const articles = rawArticles.map((a) => ({
    ...a,
    engagement_weight: calculateInfluenceScore(a.hn_score, a.hn_timestamp),
  }))

  // Group by week
  const weeklyData = new Map<
    string,
    {
      week: string
      month: string
      positive_weight: number
      negative_weight: number
      neutral_weight: number
      total_weight: number
      positive_count: number
      negative_count: number
      neutral_count: number
      total_count: number
      weighted_sentiment_sum: number
    }
  >()

  for (const article of articles) {
    const key = article.week
    if (!weeklyData.has(key)) {
      weeklyData.set(key, {
        week: article.week,
        month: article.month,
        positive_weight: 0,
        negative_weight: 0,
        neutral_weight: 0,
        total_weight: 0,
        positive_count: 0,
        negative_count: 0,
        neutral_count: 0,
        total_count: 0,
        weighted_sentiment_sum: 0,
      })
    }

    const data = weeklyData.get(key)!
    data.total_count += 1

    // IMPORTANT: All articles (positive, negative, neutral) now contribute to verdict calculation
    // Neutral articles (-0.2 to +0.2) use NEUTRAL_MULTIPLIER to adjust their contribution
    // Weight = influence score (power law + decay)
    // Contribution = sentiment × influence (same as articles table)
    if (article.sentiment_score > 0.2) {
      // POSITIVE: Include in verdict calculation at full strength
      data.total_weight += article.engagement_weight
      data.weighted_sentiment_sum += article.sentiment_score * article.engagement_weight
      data.positive_weight += article.engagement_weight
      data.positive_count += 1
    } else if (article.sentiment_score < -0.2) {
      // NEGATIVE: Include in verdict calculation at full strength
      data.total_weight += article.engagement_weight
      data.weighted_sentiment_sum += article.sentiment_score * article.engagement_weight
      data.negative_weight += article.engagement_weight
      data.negative_count += 1
    } else {
      // NEUTRAL: Use influence directly (sentiment is always 0 for mixed+uncertain)
      // Contribution = influence × NEUTRAL_MULTIPLIER (negative since multiplier = -0.5)
      const neutralContribution = article.engagement_weight * NEUTRAL_MULTIPLIER
      data.total_weight += article.engagement_weight * Math.abs(NEUTRAL_MULTIPLIER)
      data.weighted_sentiment_sum += neutralContribution
      data.neutral_weight += article.engagement_weight
      data.neutral_count += 1
    }
  }

  // Convert map to sorted array
  const results = Array.from(weeklyData.values()).sort((a, b) => a.week.localeCompare(b.week)) as Array<{
    week: string
    month: string
    positive_weight: number
    negative_weight: number
    neutral_weight: number
    total_weight: number
    positive_count: number
    negative_count: number
    neutral_count: number
    total_count: number
    weighted_sentiment_sum: number
  }>

  return results.map((r) => {
    const posWeight = r.positive_weight || 0
    const negWeight = r.negative_weight || 0
    const neuWeight = r.neutral_weight || 0
    const totalWeight = r.total_weight || 1

    // Calculate percentages for 100% stacked bars
    const positivePercent = (posWeight / totalWeight) * 100
    const negativePercent = (negWeight / totalWeight) * 100
    const neutralPercent = (neuWeight / totalWeight) * 100

    // Calculate weighted sentiment
    const sentiment = totalWeight > 0 ? r.weighted_sentiment_sum / totalWeight : 0
    const sentimentScore = sentimentToScore(sentiment)

    return {
      week: r.week,
      month: r.month,
      positiveWeight: posWeight,
      negativeWeight: negWeight,
      neutralWeight: neuWeight,
      totalWeight,
      positivePercent,
      negativePercent,
      neutralPercent,
      positiveCount: r.positive_count || 0,
      negativeCount: r.negative_count || 0,
      neutralCount: r.neutral_count || 0,
      totalCount: r.total_count || 0,
      sentiment,
      sentimentScore,
    }
  })
}

// ============================================
// TOP ARTICLES
// ============================================
// Uses POWER LAW + DECAY engagement weighting
// A 4000-upvote article has ~91x influence of a 20-upvote article (power law 0.85 exponent)

export type InfluentialArticle = {
  hn_id: number
  hn_title: string
  hn_score: number
  hn_comments: number
  hn_date: string
  hn_timestamp: number // Unix timestamp for sorting/formatting
  sentiment_score: number
  sentiment_label: "positive" | "negative" | "neutral"
  summary: string // From classification_json analysis
  influenceScore: number // Power law + decay: hn_score^0.85 × decay_factor
  content_category: string | null
  topic: string | null
  url: string
}

export function getTopArticles(limit: number = 10): InfluentialArticle[] {
  // Get ALL articles with sentiment analysis (no time window filter)
  // Uses POWER LAW + DECAY weighting: hn_score^0.85 × decay_factor
  // Older articles will have lower influence scores due to decay, but are still displayed

  const stmt = db.prepare(`
    SELECT
      hn_id,
      hn_title,
      hn_score,
      hn_comments,
      hn_timestamp,
      sentiment_score,
      classification_json,
      content_category,
      url,
      datetime(hn_timestamp, 'unixepoch') as hn_date
    FROM urls
    WHERE sentiment_score IS NOT NULL
      AND content_category = 'AI_DISCOURSE'
      AND hn_score IS NOT NULL
      AND hn_score >= 20
      AND hn_timestamp IS NOT NULL
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
    ORDER BY hn_timestamp DESC
    LIMIT ?
  `)

  const allArticles = stmt.all(limit) as Array<{
    hn_id: number
    hn_title: string
    hn_score: number
    hn_comments: number
    hn_timestamp: number
    sentiment_score: number
    classification_json: string | null
    content_category: string | null
    hn_date: string
    url: string
  }>

  // Helper to extract summary from classification_json
  function extractSummary(json: string | null): string {
    if (!json) return ""
    try {
      const analysis = JSON.parse(json) as { summary?: string }
      return analysis.summary || ""
    } catch {
      return ""
    }
  }

  // Helper to extract topic from classification_json
  // Handles both v4.0 schema (topic) and v3 schema (subtopic)
  function extractTopic(json: string | null): string | null {
    if (!json) return null
    try {
      const analysis = JSON.parse(json) as { topic?: string; subtopic?: string }
      // Try new schema first (v4.0+), fall back to old schema (v3)
      return analysis.topic || analysis.subtopic || null
    } catch {
      return null
    }
  }

  // Map articles with power law + decay influence score
  return allArticles.map((r) => ({
    hn_id: r.hn_id,
    hn_title: r.hn_title || "Untitled",
    hn_score: r.hn_score,
    hn_comments: r.hn_comments,
    hn_date: r.hn_date,
    hn_timestamp: r.hn_timestamp,
    sentiment_score: r.sentiment_score,
    sentiment_label: (r.sentiment_score > 0.2 ? "positive" : r.sentiment_score < -0.2 ? "negative" : "neutral") as
      | "positive"
      | "negative"
      | "neutral",
    summary: extractSummary(r.classification_json),
    influenceScore: Math.round(calculateInfluenceScore(r.hn_score, r.hn_timestamp) * 100) / 100, // Power law + decay
    content_category: r.content_category,
    topic: extractTopic(r.classification_json),
    url: r.url,
  }))
}

// ============================================
// HISTORICAL VERDICT SNAPSHOTS
// ============================================
// For each month, calculate what the verdict WOULD HAVE BEEN
// if you checked the site on that date.
// This enables the timeline to show how the verdict evolved.

export type HistoricalSnapshot = {
  month: string // "2025-07"
  verdictScore: number // 0-100
  verdict: "YES" | "NO" | "NOT_YET"
  articleCount: number // Total articles up to that point
  rawSentiment: number // -2.0 to +2.0
}

export function getHistoricalVerdictSnapshots(): HistoricalSnapshot[] {
  // Get all articles with sentiment scores, ordered by date
  // Uses POWER LAW + DECAY weighting: hn_score^0.85 × decay_factor
  const stmt = db.prepare(`
    SELECT
      strftime('%Y-%m', datetime(hn_timestamp, 'unixepoch')) as month,
      sentiment_score,
      hn_score,
      hn_comments,
      hn_timestamp
    FROM urls
    WHERE sentiment_score IS NOT NULL
      AND content_category = 'AI_DISCOURSE'
      AND hn_score IS NOT NULL
      AND hn_score >= 20
      AND hn_timestamp IS NOT NULL
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
    ORDER BY hn_timestamp ASC
  `)

  const rawArticles = stmt.all() as Array<{
    month: string
    sentiment_score: number
    hn_score: number
    hn_comments: number
    hn_timestamp: number
  }>

  // Apply power law + decay weighting
  const allArticles = rawArticles.map((a) => ({
    ...a,
    engagement_weight: calculateInfluenceScore(a.hn_score, a.hn_timestamp),
  }))

  if (allArticles.length === 0) return []

  // Get unique months in chronological order
  const uniqueMonths = [...new Set(allArticles.map((a) => a.month))].sort()

  // Filter to only include the last TIMELINE_DISPLAY_MONTHS months
  const now = new Date()
  const displayCutoff = new Date(now)
  displayCutoff.setMonth(displayCutoff.getMonth() - TIMELINE_DISPLAY_MONTHS)
  const cutoffMonth = `${displayCutoff.getFullYear()}-${String(displayCutoff.getMonth() + 1).padStart(2, "0")}`

  // For each month, calculate what the verdict would have been
  // using ALL articles up to and including that month (no decay)
  const snapshots: HistoricalSnapshot[] = []

  // Cumulative tracking
  let cumulativeWeight = 0
  let cumulativeWeightedSentiment = 0
  let cumulativePositiveContribution = 0
  let cumulativeNegativeContribution = 0
  let cumulativeArticleCount = 0

  // Group articles by month first
  const articlesByMonth = new Map<string, typeof allArticles>()
  for (const article of allArticles) {
    if (!articlesByMonth.has(article.month)) {
      articlesByMonth.set(article.month, [])
    }
    articlesByMonth.get(article.month)!.push(article)
  }

  for (const targetMonth of uniqueMonths) {
    // Add this month's articles to cumulative totals
    const monthArticles = articlesByMonth.get(targetMonth) || []
    for (const article of monthArticles) {
      cumulativeArticleCount += 1

      // IMPORTANT: All articles (positive, negative, neutral) now contribute to verdict calculation
      // Neutral articles (-0.2 to +0.2) use NEUTRAL_MULTIPLIER to adjust their contribution
      // Weight = influence score (power law + decay)
      // Contribution = sentiment × influence (same as articles table)
      if (article.sentiment_score > 0.2) {
        const contribution = article.sentiment_score * article.engagement_weight
        cumulativeWeight += article.engagement_weight
        cumulativeWeightedSentiment += contribution
        cumulativePositiveContribution += contribution
      } else if (article.sentiment_score < -0.2) {
        const contribution = article.sentiment_score * article.engagement_weight
        cumulativeWeight += article.engagement_weight
        cumulativeWeightedSentiment += contribution
        cumulativeNegativeContribution += contribution // This will be negative
      } else {
        // NEUTRAL: Use influence directly (sentiment is always 0 for mixed+uncertain)
        // Contribution = influence × NEUTRAL_MULTIPLIER (negative since multiplier = -0.5)
        const contribution = article.engagement_weight * NEUTRAL_MULTIPLIER
        cumulativeWeight += article.engagement_weight * Math.abs(NEUTRAL_MULTIPLIER)
        cumulativeWeightedSentiment += contribution
      }
    }

    if (cumulativeWeight === 0) continue

    const rawSentiment = cumulativeWeightedSentiment / cumulativeWeight

    // Use CONTRIBUTION RATIO formula (same as getVerdictScore)
    // Score = |positiveContribution| / (|positiveContribution| + |negativeContribution|) × 100
    const absPositive = Math.abs(cumulativePositiveContribution)
    const absNegative = Math.abs(cumulativeNegativeContribution)
    const totalAbsContribution = absPositive + absNegative
    const verdictScore = totalAbsContribution > 0 ? (absPositive / totalAbsContribution) * 100 : 50

    let verdict: "YES" | "NO" | "NOT_YET"
    if (verdictScore >= 55) {
      verdict = "YES"
    } else if (verdictScore < 45) {
      verdict = "NO"
    } else {
      verdict = "NOT_YET"
    }

    snapshots.push({
      month: targetMonth,
      verdictScore,
      verdict,
      articleCount: cumulativeArticleCount,
      rawSentiment,
    })
  }

  // Filter snapshots to only include the last TIMELINE_DISPLAY_MONTHS months
  return snapshots.filter((s) => s.month >= cutoffMonth)
}

// ============================================
// WEEKLY ROLLING WINDOW SNAPSHOTS
// ============================================
// For each week, calculate sentiment using the same rolling window as verdict.
// This ensures the graph's latest point matches the displayed verdict score.

/** Rolling window size in months for weekly snapshots - matches VERDICT_WINDOW_MONTHS */
const ROLLING_WINDOW_MONTHS = VERDICT_WINDOW_MONTHS

export type WeeklySnapshot = {
  week: string // "2025-W07" (ISO week)
  weekStart: string // "2025-02-10" (Monday of the week)
  verdictScore: number // 0-100
  verdict: "YES" | "NO" | "NOT_YET"
  articleCount: number // Articles in the rolling window
  rawSentiment: number // -2.0 to +2.0
  // Sentiment breakdown counts (for stacked area visualization)
  positiveCount: number
  neutralCount: number
  negativeCount: number
  // Contribution scores (sentiment × influence)
  positiveContribution: number
  negativeContribution: number
  neutralContribution: number
}

export function getWeeklyRollingSnapshots(): WeeklySnapshot[] {
  // Get all articles with sentiment scores, ordered by date
  const stmt = db.prepare(`
    SELECT
      strftime('%Y-W%W', datetime(hn_timestamp, 'unixepoch')) as week,
      date(hn_timestamp, 'unixepoch', 'weekday 0', '-6 days') as week_start,
      sentiment_score,
      hn_score,
      hn_comments,
      hn_timestamp
    FROM urls
    WHERE sentiment_score IS NOT NULL
      AND content_category = 'AI_DISCOURSE'
      AND hn_score IS NOT NULL
      AND hn_score >= 20
      AND hn_timestamp IS NOT NULL
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
    ORDER BY hn_timestamp ASC
  `)

  const rawArticles = stmt.all() as Array<{
    week: string
    week_start: string
    sentiment_score: number
    hn_score: number
    hn_comments: number
    hn_timestamp: number
  }>

  if (rawArticles.length === 0) return []

  // Apply power law + decay weighting
  const allArticles = rawArticles.map((a) => ({
    ...a,
    engagement_weight: calculateInfluenceScore(a.hn_score, a.hn_timestamp),
  }))

  // Get unique weeks in chronological order
  const uniqueWeeks = [...new Set(allArticles.map((a) => a.week))].sort()

  // Filter to display range
  const now = new Date()
  const displayCutoff = new Date(now)
  displayCutoff.setMonth(displayCutoff.getMonth() - TIMELINE_DISPLAY_MONTHS)
  const cutoffTimestamp = Math.floor(displayCutoff.getTime() / 1000)

  // Rolling window cutoff (6 months before each target week)
  const rollingWindowSeconds = ROLLING_WINDOW_MONTHS * 30.44 * 24 * 3600

  const snapshots: WeeklySnapshot[] = []

  for (const targetWeek of uniqueWeeks) {
    // Find articles in this week to get the week's timestamp
    const weekArticles = allArticles.filter((a) => a.week === targetWeek)
    if (weekArticles.length === 0) continue

    // Use the latest article's timestamp as the "end" of this week for filtering
    const weekEndTimestamp = Math.max(...weekArticles.map((a) => a.hn_timestamp))
    const weekStartTimestamp = weekEndTimestamp - rollingWindowSeconds

    // Skip weeks before the display cutoff
    if (weekEndTimestamp < cutoffTimestamp) continue

    // Get all articles within the 6-month rolling window ending at this week
    const windowArticles = allArticles.filter(
      (a) => a.hn_timestamp >= weekStartTimestamp && a.hn_timestamp <= weekEndTimestamp
    )

    if (windowArticles.length === 0) continue

    // Calculate weighted sentiment for this window using CONTRIBUTION RATIO formula
    let windowWeight = 0
    let windowWeightedSentiment = 0
    let positiveContribution = 0
    let negativeContribution = 0
    let neutralContribution = 0
    let articleCount = 0
    let positiveCount = 0
    let neutralCount = 0
    let negativeCount = 0

    for (const article of windowArticles) {
      articleCount += 1

      // IMPORTANT: All articles (positive, negative, neutral) now contribute to verdict calculation
      // Neutral articles (-0.2 to +0.2) use NEUTRAL_MULTIPLIER to adjust their contribution
      // Weight = influence score (power law + decay)
      // Contribution = sentiment × influence (same as articles table)
      if (article.sentiment_score > 0.2) {
        const contribution = article.sentiment_score * article.engagement_weight
        windowWeight += article.engagement_weight
        windowWeightedSentiment += contribution
        positiveContribution += contribution
        positiveCount += 1
      } else if (article.sentiment_score < -0.2) {
        const contribution = article.sentiment_score * article.engagement_weight
        windowWeight += article.engagement_weight
        windowWeightedSentiment += contribution
        negativeContribution += contribution // This will be negative
        negativeCount += 1
      } else {
        // NEUTRAL: Use influence directly (sentiment is always 0 for mixed+uncertain)
        // Contribution = influence × NEUTRAL_MULTIPLIER (negative since multiplier = -0.5)
        const contribution = article.engagement_weight * NEUTRAL_MULTIPLIER
        windowWeight += article.engagement_weight * Math.abs(NEUTRAL_MULTIPLIER)
        windowWeightedSentiment += contribution
        neutralContribution += contribution
        neutralCount += 1
      }
    }

    if (windowWeight === 0) continue

    const rawSentiment = windowWeightedSentiment / windowWeight

    // Use CONTRIBUTION RATIO formula (same as getVerdictScore)
    // Score = |positiveContribution| / (|positiveContribution| + |negativeContribution|) × 100
    const absPositive = Math.abs(positiveContribution)
    const absNegative = Math.abs(negativeContribution)
    const totalAbsContribution = absPositive + absNegative
    const verdictScore = totalAbsContribution > 0 ? (absPositive / totalAbsContribution) * 100 : 50

    let verdict: "YES" | "NO" | "NOT_YET"
    if (verdictScore >= 55) {
      verdict = "YES"
    } else if (verdictScore < 45) {
      verdict = "NO"
    } else {
      verdict = "NOT_YET"
    }

    // Get week_start from one of the articles in this week
    const weekStart = weekArticles[0].week_start

    snapshots.push({
      week: targetWeek,
      weekStart: weekStart,
      verdictScore,
      verdict,
      articleCount,
      rawSentiment,
      positiveCount,
      neutralCount,
      negativeCount,
      positiveContribution,
      negativeContribution,
      neutralContribution,
    })
  }

  return snapshots
}

// ============================================
// PERMANENT RECORD SCORE
// ============================================
// All-time average sentiment weighted by engagement.
// Uses POWER LAW + DECAY weighting (hn_score^0.85 × decay_factor).

export type PermanentRecord = {
  score: number // 0-100
  verdict: "YES" | "NO" | "NOT_YET"
  totalArticles: number
  rawSentiment: number // -2.0 to +2.0
  positiveCount: number
  neutralCount: number
  negativeCount: number
}

export function getPermanentRecordScore(): PermanentRecord {
  // Use POWER LAW + DECAY engagement weighting: hn_score^0.85 × decay_factor
  const stmt = db.prepare(`
    SELECT
      sentiment_score,
      hn_score,
      hn_comments,
      hn_timestamp
    FROM urls
    WHERE sentiment_score IS NOT NULL
      AND content_category = 'AI_DISCOURSE'
      AND hn_score IS NOT NULL
      AND hn_score >= 20
  `)

  const articles = stmt.all() as Array<{
    sentiment_score: number
    hn_score: number
    hn_comments: number
    hn_timestamp: number
  }>

  // Calculate power law + decay weighted sums
  // IMPORTANT: All articles (positive, negative, neutral) now contribute to verdict calculation
  // Neutral articles (-0.2 to +0.2) use NEUTRAL_MULTIPLIER to adjust their contribution
  let weightedSum = 0
  let totalWeight = 0
  let positiveContribution = 0
  let negativeContribution = 0
  let positiveCount = 0
  let neutralCount = 0
  let negativeCount = 0

  for (const article of articles) {
    // Weight = influence score (power law + decay)
    // Contribution = sentiment × influence (same as articles table)
    const baseWeight = calculateInfluenceScore(article.hn_score, article.hn_timestamp)

    if (article.sentiment_score > 0.2) {
      // POSITIVE: Include in verdict calculation at full strength
      const contribution = article.sentiment_score * baseWeight
      weightedSum += contribution
      totalWeight += baseWeight
      positiveContribution += contribution
      positiveCount += 1
    } else if (article.sentiment_score < -0.2) {
      // NEGATIVE: Include in verdict calculation at full strength
      const contribution = article.sentiment_score * baseWeight
      weightedSum += contribution
      totalWeight += baseWeight
      negativeContribution += contribution // This will be negative
      negativeCount += 1
    } else {
      // NEUTRAL: Use influence directly (sentiment is always 0 for mixed+uncertain)
      // Contribution = influence × NEUTRAL_MULTIPLIER (negative since multiplier = -0.5)
      const contribution = baseWeight * NEUTRAL_MULTIPLIER
      weightedSum += contribution
      totalWeight += baseWeight * Math.abs(NEUTRAL_MULTIPLIER)
      neutralCount += 1
    }
  }

  const result = {
    weighted_sum: weightedSum,
    total_weight: totalWeight,
    total_count: articles.length,
    positive_contribution: positiveContribution,
    negative_contribution: negativeContribution,
    positive_count: positiveCount,
    neutral_count: neutralCount,
    negative_count: negativeCount,
  }

  if (!result || result.total_weight === 0) {
    return {
      score: 50,
      verdict: "NOT_YET",
      totalArticles: 0,
      rawSentiment: 0,
      positiveCount: 0,
      neutralCount: 0,
      negativeCount: 0,
    }
  }

  const rawSentiment = result.weighted_sum / result.total_weight

  // Use CONTRIBUTION RATIO formula (same as getVerdictScore)
  // Score = |positiveContribution| / (|positiveContribution| + |negativeContribution|) × 100
  const absPositive = Math.abs(result.positive_contribution)
  const absNegative = Math.abs(result.negative_contribution)
  const totalAbsContribution = absPositive + absNegative
  const score = totalAbsContribution > 0 ? (absPositive / totalAbsContribution) * 100 : 50

  let verdict: "YES" | "NO" | "NOT_YET"
  if (score >= 55) {
    verdict = "YES"
  } else if (score < 45) {
    verdict = "NO"
  } else {
    verdict = "NOT_YET"
  }

  return {
    score,
    verdict,
    totalArticles: result.total_count,
    rawSentiment,
    positiveCount: result.positive_count || 0,
    neutralCount: result.neutral_count || 0,
    negativeCount: result.negative_count || 0,
  }
}
