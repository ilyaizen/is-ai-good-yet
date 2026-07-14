import Database from "better-sqlite3"
import { existsSync } from "node:fs"
import { getPipelineStoragePaths } from "$lib/server/pipeline-storage"

export interface V2RunMetrics {
  inputTokens: number
  outputTokens: number
  inferenceTimeMs: number
}

export interface V2AnalysisRun {
  source: string
  status: string
  analysisVersion: string
  selectionVersion: string
  contractVersion: string
  promptVersion: string
  parserVersion: string
  promptHash: string
  inputHash: string
  model: string
  parameters: Record<string, unknown>
  reasonCode: string | null
  reason: string | null
  result: Record<string, unknown>
  metrics: V2RunMetrics
  analyzedAt: string
}

export interface V2DimensionAnalysis {
  source: string
  dimension: string
  applicability: string
  score: number | null
  confidence: number
  disagreement: number | null
  evidenceCount: number
  rationale: string
}

export interface V2AdminStory {
  hnStoryId: number
  title: string
  url: string
  hnScore: number
  hnComments: number
  hnTimestamp: number
  eligible: boolean | null
  scopes: string[]
  articleStatus: string | null
  communityStatus: string | null
  selectedComments: number
  acceptedComments: number
}

export interface V2AdminStoryDetails {
  hnStoryId: number
  prefilterReasonCode: string | null
  prefilterReason: string | null
  prefilterModel: string | null
  decidedAt: string | null
  article: V2AnalysisRun | null
  community: V2AnalysisRun | null
  dimensions: V2DimensionAnalysis[]
}

export interface V2OrchestrationRun {
  runId: string
  status: string
  stage: string
  startedAt: string
  finishedAt: string | null
  storiesDiscovered: number
  articlesProcessed: number
  commentsAnalyzed: number
  errorCode: string | null
}

export interface V2AdminData {
  available: boolean
  summary: {
    eligibleStories: number
    articleAccepted: number
    communityAccepted: number
    commentsAccepted: number
    failedAnalyses: number
    inputTokens: number
    outputTokens: number
  }
  stories: V2AdminStory[]
  orchestrationRuns: V2OrchestrationRun[]
}

interface AnalysisRow {
  source: string
  status: string
  analysis_version: string
  selection_version: string
  contract_version: string
  prompt_version: string
  parser_version: string
  prompt_hash: string
  input_hash: string
  model: string
  parameters_json: string
  reason_code: string | null
  reason: string | null
  result_json: string
  metrics_json: string
  analyzed_at: string
}

function emptyData(): V2AdminData {
  return {
    available: false,
    summary: {
      eligibleStories: 0,
      articleAccepted: 0,
      communityAccepted: 0,
      commentsAccepted: 0,
      failedAnalyses: 0,
      inputTokens: 0,
      outputTokens: 0,
    },
    stories: [],
    orchestrationRuns: [],
  }
}

function parseObject(value: string | null | undefined): Record<string, unknown> {
  if (!value) return {}
  try {
    const parsed = JSON.parse(value) as unknown
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as Record<string, unknown>) : {}
  } catch {
    return {}
  }
}

function parseStrings(value: string | null | undefined): string[] {
  if (!value) return []
  try {
    const parsed = JSON.parse(value) as unknown
    return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === "string") : []
  } catch {
    return []
  }
}

function finiteNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0
}

function mapAnalysis(row: AnalysisRow): V2AnalysisRun {
  const metrics = parseObject(row.metrics_json)
  return {
    source: row.source,
    status: row.status,
    analysisVersion: row.analysis_version,
    selectionVersion: row.selection_version,
    contractVersion: row.contract_version,
    promptVersion: row.prompt_version,
    parserVersion: row.parser_version,
    promptHash: row.prompt_hash,
    inputHash: row.input_hash,
    model: row.model,
    parameters: parseObject(row.parameters_json),
    reasonCode: row.reason_code,
    reason: row.reason,
    result: parseObject(row.result_json),
    metrics: {
      inputTokens: finiteNumber(metrics.input_tokens),
      outputTokens: finiteNumber(metrics.output_tokens),
      inferenceTimeMs: finiteNumber(metrics.inference_time_ms),
    },
    analyzedAt: row.analyzed_at,
  }
}

const REQUIRED_V2_COLUMNS: Record<string, readonly string[]> = {
  v2_prefilter_decisions: ["hn_story_id", "eligible", "scopes_json", "reason_code", "reason", "model", "decided_at"],
  v2_analysis_runs: [
    "hn_story_id",
    "source",
    "status",
    "analysis_version",
    "selection_version",
    "contract_version",
    "prompt_version",
    "parser_version",
    "prompt_hash",
    "input_hash",
    "model",
    "parameters_json",
    "reason_code",
    "reason",
    "result_json",
    "metrics_json",
    "analyzed_at",
  ],
  v2_dimension_analyses: [
    "hn_story_id",
    "source",
    "analysis_version",
    "selection_version",
    "dimension",
    "applicability",
    "score",
    "confidence",
    "disagreement",
    "evidence_count",
    "diagnostics_json",
  ],
  v2_comment_analyses_normalized: ["hn_story_id", "status"],
  v2_comment_selections: ["hn_story_id"],
  v2_orchestration_runs: [
    "run_id",
    "status",
    "stage",
    "started_at",
    "finished_at",
    "stories_discovered",
    "articles_processed",
    "comments_analyzed",
    "error_code",
  ],
}

function hasCompatibleV2Schema(db: Database.Database): boolean {
  const tables = db.prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'v2_%'").all() as Array<{
    name: string
  }>
  const names = new Set(tables.map((row) => row.name))
  return Object.entries(REQUIRED_V2_COLUMNS).every(([table, requiredColumns]) => {
    if (!names.has(table)) return false
    const columns = db.prepare(`PRAGMA table_info("${table}")`).all() as Array<{ name: string }>
    const columnNames = new Set(columns.map((row) => row.name))
    return requiredColumns.every((column) => columnNames.has(column))
  })
}

export function getV2AdminData(databasePath = getPipelineStoragePaths().pipelineDbPath): V2AdminData {
  if (!existsSync(databasePath)) return emptyData()

  const db = new Database(databasePath, { readonly: true })
  try {
    if (!hasCompatibleV2Schema(db)) return emptyData()

    const summaryRow = db
      .prepare(`
        SELECT
          (SELECT COUNT(*) FROM (
            SELECT eligible, ROW_NUMBER() OVER (
              PARTITION BY hn_story_id ORDER BY decided_at DESC, rowid DESC
            ) AS recency_rank
            FROM v2_prefilter_decisions
          ) WHERE recency_rank = 1 AND eligible = 1) AS eligible_stories,
          (SELECT COUNT(*) FROM v2_analysis_runs WHERE source = 'article' AND status = 'accepted') AS article_accepted,
          (SELECT COUNT(*) FROM v2_analysis_runs WHERE source = 'community' AND status = 'accepted') AS community_accepted,
          (SELECT COUNT(*) FROM v2_comment_analyses_normalized WHERE status = 'accepted') AS comments_accepted,
          (SELECT COUNT(*) FROM v2_analysis_runs WHERE status != 'accepted') AS failed_analyses,
          (SELECT COALESCE(SUM(CAST(json_extract(metrics_json, '$.input_tokens') AS REAL)), 0) FROM v2_analysis_runs) AS input_tokens,
          (SELECT COALESCE(SUM(CAST(json_extract(metrics_json, '$.output_tokens') AS REAL)), 0) FROM v2_analysis_runs) AS output_tokens
      `)
      .get() as {
      eligible_stories: number
      article_accepted: number
      community_accepted: number
      comments_accepted: number
      failed_analyses: number
      input_tokens: number
      output_tokens: number
    }

    const stories = db
      .prepare(`
        WITH story_ids AS (
          SELECT hn_story_id FROM v2_prefilter_decisions
          UNION
          SELECT hn_story_id FROM v2_analysis_runs
        )
        SELECT
          story_ids.hn_story_id,
          COALESCE(urls.hn_title, 'HN story #' || story_ids.hn_story_id) AS title,
          COALESCE(urls.url, 'https://news.ycombinator.com/item?id=' || story_ids.hn_story_id) AS url,
          COALESCE(urls.hn_score, 0) AS hn_score,
          COALESCE(urls.hn_comments, 0) AS hn_comments,
          COALESCE(urls.hn_timestamp, 0) AS hn_timestamp,
          p.eligible,
          p.scopes_json,
          (
            SELECT status FROM v2_analysis_runs a
            WHERE a.hn_story_id = story_ids.hn_story_id AND a.source = 'article'
            ORDER BY a.analyzed_at DESC, a.rowid DESC LIMIT 1
          ) AS article_status,
          (
            SELECT status FROM v2_analysis_runs a
            WHERE a.hn_story_id = story_ids.hn_story_id AND a.source = 'community'
            ORDER BY a.analyzed_at DESC, a.rowid DESC LIMIT 1
          ) AS community_status,
          (SELECT COUNT(*) FROM v2_comment_selections s WHERE s.hn_story_id = story_ids.hn_story_id) AS selected_comments,
          (SELECT COUNT(*) FROM v2_comment_analyses_normalized c WHERE c.hn_story_id = story_ids.hn_story_id AND c.status = 'accepted') AS accepted_comments
        FROM story_ids
        LEFT JOIN urls ON urls.rowid = (
          SELECT latest_url.rowid
          FROM urls latest_url
          WHERE latest_url.hn_id = story_ids.hn_story_id
          ORDER BY latest_url.id DESC, latest_url.rowid DESC
          LIMIT 1
        )
        LEFT JOIN v2_prefilter_decisions p ON p.rowid = (
          SELECT latest_prefilter.rowid
          FROM v2_prefilter_decisions latest_prefilter
          WHERE latest_prefilter.hn_story_id = story_ids.hn_story_id
          ORDER BY latest_prefilter.decided_at DESC, latest_prefilter.rowid DESC
          LIMIT 1
        )
        ORDER BY COALESCE(urls.hn_timestamp, 0) DESC, story_ids.hn_story_id DESC
        LIMIT 100
      `)
      .all()
      .map((raw) => {
        const row = raw as {
          hn_story_id: number
          title: string
          url: string
          hn_score: number
          hn_comments: number
          hn_timestamp: number
          eligible: number | null
          scopes_json: string | null
          article_status: string | null
          community_status: string | null
          selected_comments: number
          accepted_comments: number
        }
        return {
          hnStoryId: row.hn_story_id,
          title: row.title,
          url: row.url,
          hnScore: row.hn_score,
          hnComments: row.hn_comments,
          hnTimestamp: row.hn_timestamp,
          eligible: row.eligible === null ? null : row.eligible === 1,
          scopes: parseStrings(row.scopes_json),
          articleStatus: row.article_status,
          communityStatus: row.community_status,
          selectedComments: row.selected_comments,
          acceptedComments: row.accepted_comments,
        } satisfies V2AdminStory
      })

    const orchestrationRuns = db
      .prepare(`
        SELECT run_id, status, stage, started_at, finished_at, stories_discovered,
               articles_processed, comments_analyzed, error_code
        FROM v2_orchestration_runs
        ORDER BY started_at DESC
        LIMIT 20
      `)
      .all()
      .map((raw) => {
        const row = raw as {
          run_id: string
          status: string
          stage: string
          started_at: string
          finished_at: string | null
          stories_discovered: number
          articles_processed: number
          comments_analyzed: number
          error_code: string | null
        }
        return {
          runId: row.run_id,
          status: row.status,
          stage: row.stage,
          startedAt: row.started_at,
          finishedAt: row.finished_at,
          storiesDiscovered: row.stories_discovered,
          articlesProcessed: row.articles_processed,
          commentsAnalyzed: row.comments_analyzed,
          errorCode: row.error_code,
        } satisfies V2OrchestrationRun
      })

    return {
      available: true,
      summary: {
        eligibleStories: finiteNumber(summaryRow.eligible_stories),
        articleAccepted: finiteNumber(summaryRow.article_accepted),
        communityAccepted: finiteNumber(summaryRow.community_accepted),
        commentsAccepted: finiteNumber(summaryRow.comments_accepted),
        failedAnalyses: finiteNumber(summaryRow.failed_analyses),
        inputTokens: finiteNumber(summaryRow.input_tokens),
        outputTokens: finiteNumber(summaryRow.output_tokens),
      },
      stories,
      orchestrationRuns,
    }
  } finally {
    db.close()
  }
}

export function getV2AdminStoryDetails(
  hnStoryId: number,
  databasePath = getPipelineStoragePaths().pipelineDbPath
): V2AdminStoryDetails | null {
  if (!Number.isInteger(hnStoryId) || hnStoryId <= 0 || !existsSync(databasePath)) return null

  const db = new Database(databasePath, { readonly: true })
  try {
    if (!hasCompatibleV2Schema(db)) return null

    const exists = db
      .prepare(`
        SELECT 1 FROM v2_prefilter_decisions WHERE hn_story_id = ?
        UNION ALL
        SELECT 1 FROM v2_analysis_runs WHERE hn_story_id = ?
        LIMIT 1
      `)
      .get(hnStoryId, hnStoryId)
    if (!exists) return null

    const prefilter = db
      .prepare(`
        SELECT reason_code, reason, model, decided_at
        FROM v2_prefilter_decisions
        WHERE hn_story_id = ?
        ORDER BY decided_at DESC, rowid DESC
        LIMIT 1
      `)
      .get(hnStoryId) as
      | { reason_code: string | null; reason: string | null; model: string | null; decided_at: string | null }
      | undefined

    const analysisRows = db
      .prepare(`
        SELECT * FROM (
          SELECT a.*, ROW_NUMBER() OVER (
            PARTITION BY a.source ORDER BY a.analyzed_at DESC, a.rowid DESC
          ) AS recency_rank
          FROM v2_analysis_runs a
          WHERE a.hn_story_id = ? AND a.source IN ('article', 'community')
        )
        WHERE recency_rank = 1
      `)
      .all(hnStoryId) as AnalysisRow[]
    const analyses = new Map(analysisRows.map((row) => [row.source, mapAnalysis(row)]))

    const dimensions = db
      .prepare(`
        WITH latest_runs AS (
          SELECT hn_story_id, source, analysis_version, selection_version
          FROM (
            SELECT a.*, ROW_NUMBER() OVER (
              PARTITION BY a.source ORDER BY a.analyzed_at DESC, a.rowid DESC
            ) AS recency_rank
            FROM v2_analysis_runs a
            WHERE a.hn_story_id = ? AND a.source IN ('article', 'community')
          )
          WHERE recency_rank = 1
        )
        SELECT d.source, d.dimension, d.applicability, d.score, d.confidence,
               d.disagreement, d.evidence_count, d.diagnostics_json
        FROM v2_dimension_analyses d
        INNER JOIN latest_runs r
          ON r.hn_story_id = d.hn_story_id
         AND r.source = d.source
         AND r.analysis_version = d.analysis_version
         AND r.selection_version = d.selection_version
        ORDER BY d.source, d.dimension
      `)
      .all(hnStoryId)
      .map((raw) => {
        const row = raw as {
          source: string
          dimension: string
          applicability: string
          score: number | null
          confidence: number
          disagreement: number | null
          evidence_count: number
          diagnostics_json: string
        }
        const diagnostics = parseObject(row.diagnostics_json)
        return {
          source: row.source,
          dimension: row.dimension,
          applicability: row.applicability,
          score: row.score,
          confidence: row.confidence,
          disagreement: row.disagreement,
          evidenceCount: row.evidence_count,
          rationale: typeof diagnostics.rationale === "string" ? diagnostics.rationale : "",
        } satisfies V2DimensionAnalysis
      })

    return {
      hnStoryId,
      prefilterReasonCode: prefilter?.reason_code ?? null,
      prefilterReason: prefilter?.reason ?? null,
      prefilterModel: prefilter?.model ?? null,
      decidedAt: prefilter?.decided_at ?? null,
      article: analyses.get("article") ?? null,
      community: analyses.get("community") ?? null,
      dimensions,
    }
  } finally {
    db.close()
  }
}
