/**
 * Static data loader for standalone frontend deployment.
 * Reads from exported JSON files instead of SQLite.
 */

import articlesData from "$lib/data/articles.json"
import verdictData from "$lib/data/verdict.json"
import historicalData from "$lib/data/historical.json"
import weeklyData from "$lib/data/weekly.json"

import type { InfluentialArticle } from "$lib/server/db"

// Types for exported JSON data
type ExportedVerdict = {
  current: {
    verdict: "YES" | "NO" | "NOT_YET"
    score: number
    rawSentiment: number
    totalArticles: number
    positiveCount: number
    negativeCount: number
    neutralCount: number
    positiveContribution: number
    negativeContribution: number
    neutralContribution: number
    windowMonths: number
    exportedAt: string
  }
  permanent: {
    score: number
    verdict: "YES" | "NO" | "NOT_YET"
    totalArticles: number
    positiveCount: number
    negativeCount: number
    neutralCount: number
  }
}

type ExportedHistoricalSnapshot = {
  month: string
  score: number
  verdict: "YES" | "NO" | "NOT_YET"
  articleCount: number
}

type ExportedArticle = {
  hn_id: number
  hn_title: string
  hn_score: number
  hn_comments: number
  hn_timestamp: number
  hn_author: string
  sentiment_score: number
  sentiment_label: "positive" | "negative" | "neutral"
  influenceScore: number
  url: string
  summary: string
  topic: string
  utility: "magic" | "tool" | "mixed" | "toil" | "hazard"
  trajectory: "optimistic" | "uncertain" | "pessimistic"
  quotes: string[]
  excerpt?: string
}

// Cast imported data to correct types
const verdict = verdictData as ExportedVerdict
const historical = historicalData as ExportedHistoricalSnapshot[]
const articles = articlesData as ExportedArticle[]

/**
 * Get verdict score from static data
 */
export function getStaticVerdictScore() {
  const v = verdict.current

  // Calculate confidence based on distance from neutral and article count
  const distanceFromNeutral = Math.abs(v.score - 50)
  let verdictConfidence: "high" | "medium" | "low"
  if (distanceFromNeutral > 15 && v.totalArticles >= 100) {
    verdictConfidence = "high"
  } else if (distanceFromNeutral > 8 || v.totalArticles >= 50) {
    verdictConfidence = "medium"
  } else {
    verdictConfidence = "low"
  }

  // Calculate momentum (not available in static export, default to stable)
  return {
    verdict: v.verdict,
    verdictConfidence,
    finalScore: v.score,
    rawSentiment: v.rawSentiment,
    momentum: 0,
    momentumLabel: "stable" as const,
    recentSentiment: 0,
    previousSentiment: 0,
    totalAnalyzed: v.totalArticles,
    positiveCount: v.positiveCount,
    negativeCount: v.negativeCount,
    neutralCount: v.neutralCount,
    positiveInfluence: 0,
    negativeInfluence: 0,
    neutralInfluence: 0,
    totalInfluence: 0,
    positiveContribution: v.positiveContribution,
    negativeContribution: v.negativeContribution,
    neutralContribution: v.neutralContribution,
    totalEngagement: 0,
    averageEngagement: 0,
    oldestArticleDate: "",
    newestArticleDate: "",
    monthsAnalyzed: v.windowMonths,
    monthlyBreakdown: [],
  }
}

/**
 * Get historical snapshots from static data
 */
export function getStaticHistoricalSnapshots() {
  return historical.map((h) => ({
    month: h.month,
    verdictScore: h.score,
    verdict: h.verdict,
    articleCount: h.articleCount,
    rawSentiment: 0, // Not available in static export
  }))
}

/**
 * Get weekly snapshots from static data
 */
export function getStaticWeeklySnapshots() {
  // Use pre-calculated weekly snapshots from export
  return weeklyData as Array<{
    week: string
    weekStart: string
    verdictScore: number
    verdict: "YES" | "NO" | "NOT_YET"
    articleCount: number
    rawSentiment: number
    positiveCount: number
    neutralCount: number
    negativeCount: number
    positiveContribution: number
    negativeContribution: number
    neutralContribution: number
  }>
}

/**
 * Get permanent record from static data
 */
export function getStaticPermanentRecord() {
  const p = verdict.permanent
  return {
    score: p.score,
    verdict: p.verdict,
    totalArticles: p.totalArticles,
    rawSentiment: 0, // Not available in static export
    positiveCount: p.positiveCount,
    neutralCount: p.neutralCount,
    negativeCount: p.negativeCount,
  }
}

/**
 * Get top articles from static data
 */
export function getStaticTopArticles(limit: number = 10000): InfluentialArticle[] {
  return articles.slice(0, limit).map((a) => ({
    hn_id: a.hn_id,
    hn_title: a.hn_title,
    hn_score: a.hn_score,
    hn_comments: a.hn_comments,
    hn_date: new Date(a.hn_timestamp * 1000).toISOString().split("T")[0],
    hn_timestamp: a.hn_timestamp,
    sentiment_score: a.sentiment_score,
    sentiment_label: a.sentiment_label,
    summary: a.summary,
    influenceScore: a.influenceScore,
    content_category: "AI_DISCOURSE",
    topic: a.topic,
    url: a.url,
  }))
}

/**
 * Get pipeline stats (static placeholder)
 */
export function getStaticPipelineStats() {
  return {
    totalUrls: articles.length,
    resolved: articles.length,
    scraped: articles.length,
    relevant: articles.length,
    analyzed: articles.length,
    failed: 0,
  }
}

/**
 * Get export timestamp as "time ago"
 */
export function getStaticLastCatchUp() {
  const exportedAt = new Date(verdict.current.exportedAt)
  const now = new Date()
  const diff = now.getTime() - exportedAt.getTime()

  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  const week = 7 * day
  const month = 30 * day

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
  } else {
    const months = Math.floor(diff / month)
    return `${months}mo ago`
  }
}

/**
 * Get export timestamp as Unix timestamp (seconds)
 */
export function getStaticExportTimestamp(): number | null {
  try {
    const exportedAt = new Date(verdict.current.exportedAt)
    return Math.floor(exportedAt.getTime() / 1000)
  } catch {
    return null
  }
}

/**
 * Get article by HN ID from static data (for details page)
 */
export function getStaticArticleById(hnId: number) {
  const article = articles.find((a) => a.hn_id === hnId)
  if (!article) return null

  return {
    hn_id: article.hn_id,
    hn_title: article.hn_title,
    hn_score: article.hn_score,
    hn_comments: article.hn_comments,
    hn_timestamp: article.hn_timestamp,
    hn_author: article.hn_author || "",
    url: article.url,
    sentiment_score: article.sentiment_score,
    analysis: {
      utility: article.utility || "mixed",
      trajectory: article.trajectory || "uncertain",
      topic: article.topic,
      summary: article.summary,
      quotes: article.quotes,
    },
    content_category: "AI_DISCOURSE",
    excerpt: article.excerpt || "",
  }
}
