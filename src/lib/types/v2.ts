export const V2_DIMENSIONS = ["capability", "trajectory", "impact"] as const
export const V2_SCOPES = [
  "coding",
  "research",
  "education",
  "labor",
  "economy",
  "creativity",
  "safety",
  "governance",
  "environment",
  "general",
] as const

export type V2Dimension = (typeof V2_DIMENSIONS)[number]
export type V2Scope = (typeof V2_SCOPES)[number]
export type V2Applicability = "explicit" | "implicit" | "not_addressed"

export interface V2DimensionValue {
  applicability: V2Applicability
  score: number | null
  confidence: number
  rationale: string
}

export interface V2Evidence {
  id: string
  quote: string
  attribution: "author" | "reported_finding" | "quoted_source" | "headline"
  supports: V2Dimension[]
}

export interface V2SourceAnalysis {
  dimensions: Record<V2Dimension, V2DimensionValue>
  summary: string
  evidence: V2Evidence[]
}

export interface V2Dissent {
  commentId: number
  summary: string
  excerpt: string | null
  opposingInfluenceShare: number
}

export interface V2CommunityDimension {
  applicability: V2Applicability
  /** Continuous visibility-weighted mean of applicable comments (not integer -2..2). */
  score: number | null
  confidence: number
  visibilityWeightedScore: number | null
  diversityBalancedScore: number | null
  rankingSensitivity: number | null
  positiveShare: number
  neutralShare: number
  negativeShare: number
  disagreement: number | null
  polarization: number
  effectiveSampleSize: number
  applicableCommentCount: number
  applicableAuthorCount: number
  applicableBranchCount: number
  dimensionCoverage: number
  clarity: number
  dissent: V2Dissent | null
}

export interface V2CommunityAnalysis {
  dimensions: Record<V2Dimension, V2CommunityDimension>
  /** Aggregate summaries are not always exported; the card favors a dissent excerpt. */
  summary?: string
  analyzedCommentCount: number
}

export interface V2CombinedDimension {
  score: number | null
  confidence: number
  sources: Array<"article" | "community">
}

export interface V2StoryCard {
  hnId: number
  title: string
  url: string
  domain: string
  hnScore: number
  hnComments: number
  hnTimestamp: number
  scopes: V2Scope[]
  summary: string
  evidence: V2Evidence[]
  article: V2SourceAnalysis
  community: V2CommunityAnalysis | null
  combined: {
    dimensions: Record<V2Dimension, V2CombinedDimension>
    composite: number | null
    addressedDimensions: V2Dimension[]
  }
  sourceDivergence: Record<V2Dimension, number | null>
}

export interface BotFeedItem {
  id: string
  contractVersion: "bot-feed-v2.0.0"
  bot: "aipostsbot" | "aimediabot" | "ainewsbot"
  botPostUrl: string
  postedAt: string
  canonicalUrl: string
  canonicalUrlHash: string
  domain: string
  title: string
  description: string | null
  image: { url: string; width: number | null; height: number | null; alt: string } | null
  faviconUrl: string | null
  publishedAt: string | null
  author: string | null
  scopes: V2Scope[]
  previewStatus: "complete" | "partial" | "failed"
  duplicateCount: number
  matchedHnStoryId: number | null
}

export interface V2PipelineStatus {
  contractVersion: "pipeline-status-v2.0.0"
  generatedAt: string
  schedule: {
    expression: string
    timezone: string
    human: string
    nextRunAt: string
    graceMinutes: number
  }
  currentRun: null | {
    runId: string
    startedAt: string
    stage: "discover" | "scrape" | "prefilter" | "article" | "comments" | "export"
  }
  lastRun: null | {
    runId: string
    status: "succeeded" | "failed" | "partial"
    startedAt: string
    finishedAt: string
    durationSeconds: number
    storiesDiscovered: number
    articlesProcessed: number
    commentsAnalyzed: number
    errorCode: string | null
  }
  coverage: {
    corpusEligible: number
    articleAnalyzed: number
    communityAnalyzed: number
    botPreviewReady: number
    articlePercent: number
    communityPercent: number
    botPreviewPercent: number
  }
}

export interface V2AggregateDimension {
  rawScore: number
  score: number
  verdict: "YES" | "NO" | "NOT_YET"
  confidence: number
  articleCount: number
}

export interface V2Verdict {
  contractVersion: "verdict-v2.0.0"
  generatedAt: string
  influenceVersion: string
  windowMonths: number
  articleCount: number
  dimensions: Record<V2Dimension, V2AggregateDimension | null>
  composite: null | {
    rawScore: number
    score: number
    verdict: "YES" | "NO" | "NOT_YET"
    addressedDimensions: V2Dimension[]
  }
}

export interface V2HistoryPoint {
  date: string
  storyCount: number
  dimensions: Record<V2Dimension, { score: number | null; confidence: number; addressedCount: number }>
}

export interface V2PageData {
  available: boolean
  generatedAt: string
  verdict: V2Verdict
  botFeed: BotFeedItem[]
  stories: V2StoryCard[]
  history: V2HistoryPoint[]
  pipeline: V2PipelineStatus
}
