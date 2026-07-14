import botFeedJson from "$lib/data/v2/bot-feed.json"
import botFeedRaw from "$lib/data/v2/bot-feed.json?raw"
import historyJson from "$lib/data/v2/history.json"
import historyRaw from "$lib/data/v2/history.json?raw"
import manifestJson from "$lib/data/v2/manifest.json"
import pipelineJson from "$lib/data/v2/pipeline-status.json"
import pipelineRaw from "$lib/data/v2/pipeline-status.json?raw"
import storiesJson from "$lib/data/v2/stories.json"
import storiesRaw from "$lib/data/v2/stories.json?raw"
import verdictJson from "$lib/data/v2/verdict.json"
import verdictRaw from "$lib/data/v2/verdict.json?raw"
import { validateManifestHashes } from "$lib/server/v2-generation-integrity"
import type { V2CommunityDimension, V2Dimension, V2PageData, V2SourceAnalysis, V2StoryCard } from "$lib/types/v2"
import { V2_DIMENSIONS } from "$lib/types/v2"

interface RawDimension {
  applicability?: string
  score?: number | null
  confidence?: number
  rationale?: string
  [key: string]: unknown
}

interface RawStory {
  hn_id?: number
  hnId?: number
  hn_title?: string
  title?: string
  url?: string
  hn_score?: number
  hnScore?: number
  hn_comments?: number
  hnComments?: number
  hn_timestamp?: number
  hnTimestamp?: number
  article?: Record<string, unknown>
  community?: Record<string, unknown> | null
  combined?: Record<string, unknown>
  sourceDivergence?: Record<string, number | null>
}

function number(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback
}

function domain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "")
  } catch {
    return "unknown"
  }
}

function rawDimensions(value: unknown): Record<string, RawDimension> {
  return value && typeof value === "object" ? (value as Record<string, RawDimension>) : {}
}

function mapSource(raw: Record<string, unknown> | undefined): V2SourceAnalysis {
  const result = (raw?.result ?? {}) as Record<string, unknown>
  const dimensions = rawDimensions(raw?.dimensions ?? result.dimensions)
  return {
    dimensions: Object.fromEntries(
      V2_DIMENSIONS.map((name) => {
        const value = dimensions[name] ?? {}
        return [
          name,
          {
            applicability:
              value.applicability === "explicit" || value.applicability === "implicit"
                ? value.applicability
                : "not_addressed",
            score: typeof value.score === "number" ? value.score : null,
            confidence: number(value.confidence),
            rationale: typeof value.rationale === "string" ? value.rationale : "No source evidence exported.",
          },
        ]
      })
    ) as V2SourceAnalysis["dimensions"],
    summary: typeof result.summary === "string" ? result.summary : "No source summary exported.",
    evidence: Array.isArray(result.evidence) ? (result.evidence as V2SourceAnalysis["evidence"]) : [],
  }
}

function mapCommunity(raw: Record<string, unknown> | null | undefined) {
  if (!raw) return null
  const result = (raw.result ?? {}) as Record<string, unknown>
  const dimensions = rawDimensions(raw.dimensions)
  const mapped = Object.fromEntries(
    V2_DIMENSIONS.map((name) => {
      const value = dimensions[name] ?? {}
      const dissent = value.dissent as Record<string, unknown> | null | undefined
      return [
        name,
        {
          ...mapSource({ dimensions: { [name]: value } }).dimensions[name],
          visibilityWeightedScore:
            typeof value.visibility_weighted_score === "number" ? value.visibility_weighted_score : null,
          diversityBalancedScore:
            typeof value.diversity_balanced_score === "number" ? value.diversity_balanced_score : null,
          rankingSensitivity: typeof value.ranking_sensitivity === "number" ? value.ranking_sensitivity : null,
          positiveShare: number(value.positive_share),
          neutralShare: number(value.neutral_share),
          negativeShare: number(value.negative_share),
          disagreement: typeof value.disagreement === "number" ? value.disagreement : null,
          polarization: number(value.polarization),
          effectiveSampleSize: number(value.effective_sample_size),
          applicableCommentCount: number(value.applicable_comment_count),
          applicableAuthorCount: number(value.applicable_author_count),
          applicableBranchCount: number(value.applicable_branch_count),
          dimensionCoverage: number(value.dimension_coverage),
          clarity: number(value.clarity),
          dissent: dissent
            ? {
                commentId: number(dissent.comment_id),
                summary: typeof dissent.summary === "string" ? dissent.summary : "",
                excerpt: typeof dissent.excerpt === "string" ? dissent.excerpt : null,
                opposingInfluenceShare: number(dissent.opposing_influence_share),
              }
            : null,
        } satisfies V2CommunityDimension,
      ]
    })
  ) as Record<V2Dimension, V2CommunityDimension>
  return {
    dimensions: mapped,
    summary: typeof result.summary === "string" ? result.summary : "Visible HN discussion analyzed by dimension.",
    analyzedCommentCount: number(result.accepted_comment_count),
  }
}

function mapStory(raw: RawStory): V2StoryCard {
  const url = raw.url ?? "https://news.ycombinator.com"
  const article = mapSource(raw.article)
  const community = mapCommunity(raw.community)
  const combinedRaw = (raw.combined ?? {}) as Record<string, unknown>
  const combinedDimensions = rawDimensions(combinedRaw.dimensions)
  const sourceDivergence = raw.sourceDivergence ?? {}
  const scopes = ((raw.article?.result as Record<string, unknown> | undefined)?.scopes ?? [
    "general",
  ]) as V2StoryCard["scopes"]
  return {
    hnId: number(raw.hnId ?? raw.hn_id),
    title: raw.title ?? raw.hn_title ?? "Untitled HN story",
    url,
    domain: domain(url),
    hnScore: number(raw.hnScore ?? raw.hn_score),
    hnComments: number(raw.hnComments ?? raw.hn_comments),
    hnTimestamp: number(raw.hnTimestamp ?? raw.hn_timestamp),
    scopes,
    summary: article.summary,
    evidence: article.evidence,
    article,
    community,
    combined: {
      dimensions: Object.fromEntries(
        V2_DIMENSIONS.map((name) => [
          name,
          {
            score: typeof combinedDimensions[name]?.score === "number" ? combinedDimensions[name].score : null,
            confidence: number(combinedDimensions[name]?.confidence),
            sources: Array.isArray(combinedDimensions[name]?.sources) ? combinedDimensions[name].sources : [],
          },
        ])
      ) as V2StoryCard["combined"]["dimensions"],
      composite: typeof combinedRaw.composite === "number" ? combinedRaw.composite : null,
      addressedDimensions: Array.isArray(combinedRaw.addressedDimensions)
        ? (combinedRaw.addressedDimensions as V2Dimension[])
        : [],
    },
    sourceDivergence: Object.fromEntries(
      V2_DIMENSIONS.map((name) => [name, typeof sourceDivergence[name] === "number" ? sourceDivergence[name] : null])
    ) as V2StoryCard["sourceDivergence"],
  }
}

function validateGeneration(): boolean {
  const files = manifestJson.files as Record<string, { contractVersion: string; recordCount: number; sha256: string }>
  const expected = {
    "verdict.json": "verdict-v2.0.0",
    "stories.json": "stories-v2.0.0",
    "history.json": "history-v2.0.0",
    "bot-feed.json": "bot-feed-v2.0.0",
    "pipeline-status.json": "pipeline-status-v2.0.0",
  } satisfies Record<string, string>
  const rawPayloads: Record<string, string> = {
    "verdict.json": verdictRaw,
    "stories.json": storiesRaw,
    "history.json": historyRaw,
    "bot-feed.json": botFeedRaw,
    "pipeline-status.json": pipelineRaw,
  }
  return (
    manifestJson.contractVersion === "v2-manifest-1" &&
    manifestJson.influenceVersion === verdictJson.influenceVersion &&
    Object.entries(expected).every(([filename, contract]) => files[filename]?.contractVersion === contract) &&
    validateManifestHashes(files, rawPayloads) &&
    files["stories.json"]?.recordCount === storiesJson.length &&
    files["history.json"]?.recordCount === historyJson.length &&
    files["bot-feed.json"]?.recordCount === botFeedJson.length
  )
}

export function loadV2PageData(): V2PageData {
  const generationValid = validateGeneration()
  const rawStories = generationValid && Array.isArray(storiesJson) ? (storiesJson as RawStory[]) : []
  const verdict = verdictJson as V2PageData["verdict"]
  return {
    available: generationValid && (verdict.composite !== null || rawStories.length > 0 || botFeedJson.length > 0),
    generatedAt: verdict.generatedAt,
    verdict,
    botFeed: generationValid ? (botFeedJson as V2PageData["botFeed"]) : [],
    stories: rawStories.map(mapStory),
    history: generationValid ? (historyJson as V2PageData["history"]) : [],
    pipeline: pipelineJson as V2PageData["pipeline"],
  }
}
