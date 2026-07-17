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
import type {
  BotFeedItem,
  V2Applicability,
  V2CommunityAnalysis,
  V2CommunityDimension,
  V2Dimension,
  V2Evidence,
  V2HistoryPoint,
  V2PageData,
  V2PipelineStatus,
  V2StoryCard,
  V2Verdict,
} from "$lib/types/v2"
import { V2_DIMENSIONS } from "$lib/types/v2"

/**
 * Strict, fail-closed V2 adapter.
 *
 * The pipeline exports a mixed snake_case/camelCase JSON. Rather than silently
 * coercing missing fields to `0` / placeholder strings (the pattern this rewrite
 * exists to kill), every required field is type-checked; a missing or wrongly
 * typed field throws and the route serves the explicit "generation unavailable"
 * state. Null is only ever returned where the V2 contract itself permits null
 * (not_addressed scores, empty-aggregate diagnostics, missing community).
 */

// ---- raw export shapes (the real snake_case contract the pipeline emits) ----

interface RawDimension {
  applicability: V2Applicability
  score: number | null
  confidence: number
  rationale: string
}

interface RawArticleDimension extends RawDimension {
  evidence_ids: string[]
}

interface RawEvidence {
  id: string
  quote: string
  attribution: V2Evidence["attribution"]
  supports: V2Dimension[]
}

interface RawArticleResult {
  contract_version: string
  reject: false
  scopes: V2StoryCard["scopes"]
  dimensions: Record<V2Dimension, RawArticleDimension>
  evidence: RawEvidence[]
  summary: string
}

interface RawArticle {
  result: RawArticleResult
}

interface RawDissent {
  comment_id: number
  summary: string
  excerpt: string | null
  opposing_influence_share: number
}

interface RawCommunityDimension {
  applicability: V2Applicability
  score: number | null
  confidence: number
  visibility_weighted_score: number | null
  diversity_balanced_score: number | null
  ranking_sensitivity: number | null
  positive_share: number
  neutral_share: number
  negative_share: number
  disagreement: number | null
  polarization: number
  effective_sample_size: number
  applicable_comment_count: number
  applicable_author_count: number
  applicable_branch_count: number
  dimension_coverage: number
  clarity: number
  dissent: RawDissent | null
}

interface RawCommunityResult {
  dimensions: Record<V2Dimension, RawCommunityDimension>
  summary?: string
  accepted_comment_count: number
}

interface RawCommunity {
  result?: RawCommunityResult
  dimensions: Record<V2Dimension, RawCommunityDimension>
  summary?: string
}

interface RawCombinedDimension {
  score: number | null
  confidence: number
  sources: Array<"article" | "community">
}

interface RawStory {
  hn_id: number
  hn_title: string
  hn_score: number
  hn_comments: number
  hn_timestamp: number
  url: string
  article: RawArticle
  community: RawCommunity | null
  combined: {
    dimensions: Record<V2Dimension, RawCombinedDimension>
    composite: number | null
    addressedDimensions: V2Dimension[]
  }
  sourceDivergence: Record<V2Dimension, number | null>
}

// ---- strict field guards: throw on absence instead of inventing a value ----

class V2ContractError extends Error {}

function req<T>(field: string, value: unknown, guard: (value: unknown) => value is T): T {
  if (!guard(value)) throw new V2ContractError(`V2 export field missing or invalid: ${field}`)
  return value
}

const isFiniteNumber = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value)
const isString = (value: unknown): value is string => typeof value === "string"
const isNonEmptyString = (value: unknown): value is string => typeof value === "string" && value.trim().length > 0

function reqFinite(field: string, value: unknown): number {
  return req(field, value, isFiniteNumber)
}

function reqNonEmpty(field: string, value: unknown): string {
  return req(field, value, isNonEmptyString)
}

/** Score is null iff not_addressed; otherwise an integer in -2..2. */
function mapScore(applicability: V2Applicability, raw: unknown, field: string): number | null {
  if (applicability === "not_addressed") {
    if (raw !== null) throw new V2ContractError(`${field}: not_addressed requires score null`)
    return null
  }
  if (typeof raw !== "number" || !Number.isInteger(raw) || raw < -2 || raw > 2) {
    throw new V2ContractError(`${field}: addressed score must be an integer -2..2`)
  }
  return raw
}

/** Continuous aggregate score (community mean): null iff not_addressed, else finite. */
function mapContinuousScore(applicability: V2Applicability, raw: unknown, field: string): number | null {
  if (applicability === "not_addressed") {
    if (raw !== null) throw new V2ContractError(`${field}: not_addressed requires score null`)
    return null
  }
  if (!isFiniteNumber(raw)) throw new V2ContractError(`${field}: addressed score must be a finite number`)
  return raw
}

function mapApplicability(raw: unknown, field: string): V2Applicability {
  if (raw !== "explicit" && raw !== "implicit" && raw !== "not_addressed") {
    throw new V2ContractError(`${field}: invalid applicability`)
  }
  return raw
}

/** Null where the contract allows null (empty-aggregate diagnostics); finite otherwise. */
function mapOptionalNumber(raw: unknown, field: string): number | null {
  if (raw === null) return null
  if (!isFiniteNumber(raw)) throw new V2ContractError(`${field}: expected number or null`)
  return raw
}

function domain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "")
  } catch {
    return "unknown"
  }
}

function mapArticle(raw: RawArticle | undefined, field: string): V2StoryCard["article"] {
  if (!raw) throw new V2ContractError(`${field}: article analysis missing`)
  const result = req(`${field}.result`, raw.result, (v): v is RawArticleResult => !!v && typeof v === "object")
  const dims = req(
    `${field}.result.dimensions`,
    result.dimensions,
    (v): v is Record<V2Dimension, RawArticleDimension> => !!v && typeof v === "object"
  )
  const evidence = req(`${field}.result.evidence`, result.evidence, Array.isArray) as RawEvidence[]
  return {
    dimensions: Object.fromEntries(
      V2_DIMENSIONS.map((name) => {
        const value = req(
          `${field}.dimensions.${name}`,
          dims[name],
          (v): v is RawArticleDimension => !!v && typeof v === "object"
        )
        const applicability = mapApplicability(value.applicability, `${field}.dimensions.${name}.applicability`)
        return [
          name,
          {
            applicability,
            score: mapScore(applicability, value.score, `${field}.dimensions.${name}.score`),
            confidence: reqFinite(`${field}.dimensions.${name}.confidence`, value.confidence),
            rationale: reqNonEmpty(`${field}.dimensions.${name}.rationale`, value.rationale),
          },
        ]
      })
    ) as V2StoryCard["article"]["dimensions"],
    summary: reqNonEmpty(`${field}.result.summary`, result.summary),
    evidence: evidence.map((item, index) => ({
      id: reqNonEmpty(`${field}.evidence[${index}].id`, item.id),
      quote: reqNonEmpty(`${field}.evidence[${index}].quote`, item.quote),
      attribution: mapAttribution(item.attribution, `${field}.evidence[${index}].attribution`),
      supports: req(`${field}.evidence[${index}].supports`, item.supports, Array.isArray),
    })),
  }
}

function mapAttribution(raw: unknown, field: string): V2Evidence["attribution"] {
  if (raw !== "author" && raw !== "reported_finding" && raw !== "quoted_source" && raw !== "headline") {
    throw new V2ContractError(`${field}: invalid attribution`)
  }
  return raw
}

function mapCommunity(raw: RawCommunity | null | undefined, field: string): V2CommunityAnalysis | null {
  if (!raw) return null
  const result = raw.result ?? {
    dimensions: raw.dimensions,
    summary: raw.summary,
    accepted_comment_count: 0,
  }
  const dims = req(
    `${field}.dimensions`,
    result.dimensions,
    (v): v is Record<V2Dimension, RawCommunityDimension> => !!v && typeof v === "object"
  )
  return {
    dimensions: Object.fromEntries(
      V2_DIMENSIONS.map((name) => {
        const value = req(
          `${field}.dimensions.${name}`,
          dims[name],
          (v): v is RawCommunityDimension => !!v && typeof v === "object"
        )
        const applicability = mapApplicability(value.applicability, `${field}.dimensions.${name}.applicability`)
        const dissent = value.dissent
        return [
          name,
          {
            applicability,
            score: mapContinuousScore(applicability, value.score, `${field}.dimensions.${name}.score`),
            confidence: reqFinite(`${field}.dimensions.${name}.confidence`, value.confidence),
            visibilityWeightedScore: mapOptionalNumber(
              value.visibility_weighted_score,
              `${field}.dimensions.${name}.visibility_weighted_score`
            ),
            diversityBalancedScore: mapOptionalNumber(
              value.diversity_balanced_score,
              `${field}.dimensions.${name}.diversity_balanced_score`
            ),
            rankingSensitivity: mapOptionalNumber(
              value.ranking_sensitivity,
              `${field}.dimensions.${name}.ranking_sensitivity`
            ),
            positiveShare: reqFinite(`${field}.dimensions.${name}.positive_share`, value.positive_share),
            neutralShare: reqFinite(`${field}.dimensions.${name}.neutral_share`, value.neutral_share),
            negativeShare: reqFinite(`${field}.dimensions.${name}.negative_share`, value.negative_share),
            disagreement: mapOptionalNumber(value.disagreement, `${field}.dimensions.${name}.disagreement`),
            polarization: reqFinite(`${field}.dimensions.${name}.polarization`, value.polarization),
            effectiveSampleSize: reqFinite(
              `${field}.dimensions.${name}.effective_sample_size`,
              value.effective_sample_size
            ),
            applicableCommentCount: reqFinite(
              `${field}.dimensions.${name}.applicable_comment_count`,
              value.applicable_comment_count
            ),
            applicableAuthorCount: reqFinite(
              `${field}.dimensions.${name}.applicable_author_count`,
              value.applicable_author_count
            ),
            applicableBranchCount: reqFinite(
              `${field}.dimensions.${name}.applicable_branch_count`,
              value.applicable_branch_count
            ),
            dimensionCoverage: reqFinite(`${field}.dimensions.${name}.dimension_coverage`, value.dimension_coverage),
            clarity: reqFinite(`${field}.dimensions.${name}.clarity`, value.clarity),
            dissent: dissent
              ? {
                  commentId: reqFinite(`${field}.dimensions.${name}.dissent.comment_id`, dissent.comment_id),
                  summary: reqNonEmpty(`${field}.dimensions.${name}.dissent.summary`, dissent.summary),
                  excerpt: isString(dissent.excerpt) ? dissent.excerpt : null,
                  opposingInfluenceShare: reqFinite(
                    `${field}.dimensions.${name}.dissent.opposing_influence_share`,
                    dissent.opposing_influence_share
                  ),
                }
              : null,
          } satisfies V2CommunityDimension,
        ]
      })
    ) as Record<V2Dimension, V2CommunityDimension>,
    summary: result.summary ? reqNonEmpty(`${field}.summary`, result.summary) : undefined,
    analyzedCommentCount: reqFinite(`${field}.accepted_comment_count`, result.accepted_comment_count),
  }
}

function mapStory(raw: unknown, index: number): V2StoryCard {
  const field = `stories[${index}]`
  const story = req(field, raw, (v): v is RawStory => !!v && typeof v === "object")
  const url = reqNonEmpty(`${field}.url`, story.url)
  const article = mapArticle(story.article, `${field}.article`)
  return {
    hnId: reqFinite(`${field}.hn_id`, story.hn_id),
    title: reqNonEmpty(`${field}.hn_title`, story.hn_title),
    url,
    domain: domain(url),
    hnScore: reqFinite(`${field}.hn_score`, story.hn_score),
    hnComments: reqFinite(`${field}.hn_comments`, story.hn_comments),
    hnTimestamp: reqFinite(`${field}.hn_timestamp`, story.hn_timestamp),
    scopes: req(`${field}.article.result.scopes`, story.article.result.scopes, Array.isArray),
    summary: article.summary,
    evidence: article.evidence,
    article,
    community: mapCommunity(story.community, `${field}.community`),
    combined: {
      dimensions: Object.fromEntries(
        V2_DIMENSIONS.map((name) => {
          const value = req(
            `${field}.combined.dimensions.${name}`,
            story.combined?.dimensions?.[name],
            (v): v is RawCombinedDimension => !!v && typeof v === "object"
          )
          return [
            name,
            {
              // Combined scores are weighted averages (not integer -2..2); null when no source is addressed.
              score: mapOptionalNumber(value.score, `${field}.combined.dimensions.${name}.score`),
              confidence: reqFinite(`${field}.combined.dimensions.${name}.confidence`, value.confidence),
              sources: req(`${field}.combined.dimensions.${name}.sources`, value.sources, Array.isArray),
            },
          ]
        })
      ) as V2StoryCard["combined"]["dimensions"],
      composite:
        story.combined?.composite === null ? null : reqFinite(`${field}.combined.composite`, story.combined?.composite),
      addressedDimensions: req(
        `${field}.combined.addressedDimensions`,
        story.combined?.addressedDimensions,
        Array.isArray
      ),
    },
    sourceDivergence: Object.fromEntries(
      V2_DIMENSIONS.map((name) => [
        name,
        mapOptionalNumber(story.sourceDivergence?.[name], `${field}.sourceDivergence.${name}`),
      ])
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
    manifestJson.influenceVersion === (verdictJson as V2Verdict).influenceVersion &&
    Object.entries(expected).every(([filename, contract]) => files[filename]?.contractVersion === contract) &&
    validateManifestHashes(files, rawPayloads) &&
    files["stories.json"]?.recordCount === storiesJson.length &&
    files["history.json"]?.recordCount === historyJson.length &&
    files["bot-feed.json"]?.recordCount === botFeedJson.length
  )
}

function unavailable(): V2PageData {
  return {
    available: false,
    generatedAt: "",
    verdict: pipelineJson as unknown as V2Verdict,
    botFeed: [],
    stories: [],
    history: [],
    pipeline: pipelineJson as V2PipelineStatus,
  }
}

export function loadV2PageData(): V2PageData {
  if (!validateGeneration()) return unavailable()
  try {
    const rawStories = req("stories", storiesJson, Array.isArray) as unknown[]
    const verdict = verdictJson as V2Verdict
    const stories = rawStories.map(mapStory)
    return {
      available: verdict.composite !== null || stories.length > 0 || botFeedJson.length > 0,
      generatedAt: verdict.generatedAt,
      verdict,
      botFeed: botFeedJson as BotFeedItem[],
      stories,
      history: historyJson as V2HistoryPoint[],
      pipeline: pipelineJson as V2PipelineStatus,
    }
  } catch (error) {
    // Fail closed: a broken V2 generation shows the unavailable state, never zeroes.
    if (error instanceof V2ContractError) {
      console.error(`[v2] refusing to render malformed generation: ${error.message}`)
    }
    return unavailable()
  }
}
