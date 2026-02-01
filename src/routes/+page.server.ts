import {
  getStaticVerdictScore,
  getStaticHistoricalSnapshots,
  getStaticWeeklySnapshots,
  getStaticPermanentRecord,
  getStaticTopArticles,
  getStaticPipelineStats,
  getStaticLastCatchUp,
  getStaticExportTimestamp,
} from "$lib/static-data"
import type { PageServerLoad } from "./$types"

export const load: PageServerLoad = async () => {
  try {
    const verdictScore = getStaticVerdictScore()
    const historicalSnapshots = getStaticHistoricalSnapshots()
    const weeklySnapshots = getStaticWeeklySnapshots()
    const permanentRecord = getStaticPermanentRecord()
    const topArticles = getStaticTopArticles(10000)
    const pipelineStats = getStaticPipelineStats()
    const lastCatchUpTimeAgo = getStaticLastCatchUp()
    const lastCatchUpTimestamp = getStaticExportTimestamp()

    return {
      verdictScore,
      historicalSnapshots,
      weeklySnapshots,
      permanentRecord,
      topArticles,
      pipelineStats,
      lastCatchUpTimeAgo,
      lastCatchUpTimestamp,
    }
  } catch (error) {
    console.error("Failed to load data:", error)
    return {
      verdictScore: {
        verdict: "NOT_YET" as const,
        verdictConfidence: "low" as const,
        finalScore: 50,
        rawSentiment: 0,
        momentum: 0,
        momentumLabel: "stable" as const,
        recentSentiment: 0,
        previousSentiment: 0,
        totalAnalyzed: 0,
        positiveCount: 0,
        negativeCount: 0,
        neutralCount: 0,
        positiveInfluence: 0,
        negativeInfluence: 0,
        neutralInfluence: 0,
        totalInfluence: 0,
        positiveContribution: 0,
        negativeContribution: 0,
        neutralContribution: 0,
        totalEngagement: 0,
        averageEngagement: 0,
        oldestArticleDate: "",
        newestArticleDate: "",
        monthsAnalyzed: 0,
        monthlyBreakdown: [],
      },
      historicalSnapshots: [],
      weeklySnapshots: [],
      permanentRecord: {
        score: 50,
        verdict: "NOT_YET" as const,
        totalArticles: 0,
        rawSentiment: 0,
        positiveCount: 0,
        neutralCount: 0,
        negativeCount: 0,
      },
      topArticles: [],
      pipelineStats: {
        totalUrls: 0,
        resolved: 0,
        scraped: 0,
        relevant: 0,
        analyzed: 0,
        failed: 0,
      },
      lastCatchUpTimeAgo: null,
      lastCatchUpTimestamp: null,
    }
  }
}
