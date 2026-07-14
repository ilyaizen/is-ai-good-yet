import assert from "node:assert/strict"
import { copyFileSync, mkdtempSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import path from "node:path"
import Database from "better-sqlite3"
import { getV2AdminData, getV2AdminStoryDetails } from "../src/lib/server/v2-admin-data"

const directory = mkdtempSync(path.join(tmpdir(), "v2-admin-data-"))
const databasePath = path.join(directory, "pipeline.db")
const db = new Database(databasePath)

db.exec(`
  CREATE TABLE urls (
    id INTEGER PRIMARY KEY,
    hn_id INTEGER,
    hn_title TEXT,
    url TEXT,
    hn_score INTEGER,
    hn_comments INTEGER,
    hn_timestamp INTEGER
  );
  CREATE TABLE v2_prefilter_decisions (
    hn_story_id INTEGER,
    eligible INTEGER,
    scopes_json TEXT,
    reason_code TEXT,
    reason TEXT,
    model TEXT,
    contract_version TEXT,
    prompt_version TEXT,
    prompt_hash TEXT,
    input_hash TEXT,
    decided_at TEXT,
    PRIMARY KEY (hn_story_id, contract_version)
  );
  CREATE TABLE v2_analysis_runs (
    hn_story_id INTEGER,
    source TEXT,
    analysis_version TEXT,
    selection_version TEXT,
    contract_version TEXT,
    prompt_version TEXT,
    prompt_hash TEXT,
    input_hash TEXT,
    input_snapshot_json TEXT,
    parser_version TEXT,
    model TEXT,
    parameters_json TEXT,
    status TEXT,
    reason_code TEXT,
    reason TEXT,
    result_json TEXT,
    metrics_json TEXT,
    analyzed_at TEXT
  );
  CREATE TABLE v2_dimension_analyses (
    hn_story_id INTEGER,
    source TEXT,
    analysis_version TEXT,
    selection_version TEXT,
    dimension TEXT,
    applicability TEXT,
    score REAL,
    confidence REAL,
    disagreement REAL,
    evidence_count INTEGER,
    diagnostics_json TEXT
  );
  CREATE TABLE v2_comment_analyses_normalized (
    hn_story_id INTEGER,
    hn_comment_id INTEGER,
    analysis_version TEXT,
    selection_version TEXT,
    status TEXT,
    result_json TEXT,
    analyzed_at TEXT
  );
  CREATE TABLE v2_comment_selections (
    hn_story_id INTEGER,
    hn_comment_id INTEGER,
    selection_version TEXT,
    selection_rank INTEGER,
    selection_reason TEXT,
    selection_weight REAL,
    candidate_rank INTEGER,
    selection_pass TEXT,
    refill_status TEXT,
    selected_at TEXT
  );
  CREATE TABLE v2_orchestration_runs (
    run_id TEXT,
    status TEXT,
    stage TEXT,
    started_at TEXT,
    finished_at TEXT,
    stories_discovered INTEGER,
    articles_processed INTEGER,
    comments_analyzed INTEGER,
    error_code TEXT
  );
`)

db.prepare("INSERT INTO urls VALUES (?, ?, ?, ?, ?, ?, ?)").run(
  1,
  42,
  "A measured AI story",
  "https://example.com/story",
  321,
  87,
  1_700_000_000
)
db.prepare("INSERT INTO urls VALUES (?, ?, ?, ?, ?, ?, ?)").run(
  2,
  42,
  "Canonical measured AI story",
  "https://example.com/story-canonical",
  322,
  88,
  1_700_000_001
)
db.prepare("INSERT INTO v2_prefilter_decisions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)").run(
  42,
  1,
  '["coding","research"]',
  "AI_CAPABILITY_REPORT",
  "Substantive AI claims.",
  "prefilter-model",
  "prefilter-v2",
  "prefilter-prompt-v2",
  "prompt-hash",
  "input-hash",
  "2026-07-14T01:00:00Z"
)
db.prepare("INSERT INTO v2_prefilter_decisions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)").run(
  42,
  0,
  '["stale-scope"]',
  "OLD_DECISION",
  "Superseded prefilter decision.",
  "old-prefilter-model",
  "prefilter-v1",
  "prefilter-prompt-v1",
  "old-prompt-hash",
  "old-input-hash",
  "2026-07-14T00:00:00Z"
)
const insertAnalysis = db.prepare(`
  INSERT INTO v2_analysis_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`)
const fullResultSentinel = "FULL_RESULT_SENTINEL".repeat(100_000)
insertAnalysis.run(
  42,
  "article",
  "v2.2.0",
  "",
  "article-v2.2.0",
  "article-prompt-v2.2.0",
  "article-prompt-hash",
  "article-input-hash",
  "{}",
  "v2.2.0",
  "analysis-model",
  '{"temperature":0.2}',
  "accepted",
  null,
  null,
  JSON.stringify({ summary: "Article summary", scopes: ["coding"], raw: fullResultSentinel }),
  '{"input_tokens":100,"output_tokens":50,"inference_time_ms":900}',
  "2026-07-14T02:00:00Z"
)
insertAnalysis.run(
  42,
  "article",
  "v2.1.0",
  "",
  "article-v2.1.0",
  "article-prompt-v2.1.0",
  "old-article-prompt-hash",
  "old-article-input-hash",
  "{}",
  "v2.1.0",
  "old-analysis-model",
  '{"temperature":0.1}',
  "accepted",
  null,
  null,
  '{"summary":"Superseded article result"}',
  '{"input_tokens":10,"output_tokens":5,"inference_time_ms":100}',
  "2026-07-14T01:00:00Z"
)
insertAnalysis.run(
  42,
  "community",
  "v2.2.0",
  "ranked-tree-v2.2.0",
  "community-v2.2.0",
  "community-prompt-v2.2.0",
  "community-prompt-hash",
  "community-input-hash",
  "{}",
  "v2.2.0",
  "analysis-model",
  '{"temperature":0.2}',
  "accepted",
  null,
  null,
  '{"summary":"Community summary","accepted_comment_count":1}',
  '{"input_tokens":300,"output_tokens":120,"inference_time_ms":1800}',
  "2026-07-14T03:00:00Z"
)
db.prepare("INSERT INTO v2_dimension_analyses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)").run(
  42,
  "article",
  "v2.2.0",
  "",
  "capability",
  "explicit",
  1.5,
  0.8,
  null,
  2,
  '{"rationale":"Strong capability evidence."}'
)
db.prepare("INSERT INTO v2_dimension_analyses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)").run(
  42,
  "article",
  "v2.1.0",
  "",
  "capability",
  "explicit",
  -2,
  0.1,
  null,
  1,
  '{"rationale":"Superseded dimension evidence."}'
)
db.prepare("INSERT INTO v2_comment_analyses_normalized VALUES (?, ?, ?, ?, ?, ?, ?)").run(
  42,
  99,
  "v2.2.0",
  "ranked-tree-v2.2.0",
  "accepted",
  "{}",
  "2026-07-14T03:00:00Z"
)
db.prepare("INSERT INTO v2_comment_selections VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)").run(
  42,
  99,
  "ranked-tree-v2.2.0",
  1,
  "top_level_diversity",
  1.2,
  1,
  "top_level",
  "accepted",
  "2026-07-14T02:30:00Z"
)
db.prepare("INSERT INTO v2_orchestration_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)").run(
  "run-1",
  "partial",
  "article",
  "2026-07-14T00:00:00Z",
  "2026-07-14T03:00:00Z",
  1,
  1,
  1,
  null
)
db.close()

try {
  const result = getV2AdminData(databasePath)
  assert.equal(result.available, true)
  assert.deepEqual(result.summary, {
    eligibleStories: 1,
    articleAccepted: 2,
    communityAccepted: 1,
    commentsAccepted: 1,
    failedAnalyses: 0,
    inputTokens: 410,
    outputTokens: 175,
  })
  assert.equal(result.stories.length, 1)
  assert.equal(result.stories[0].title, "Canonical measured AI story")
  assert.equal(result.stories[0].url, "https://example.com/story-canonical")
  assert.deepEqual(result.stories[0].scopes, ["coding", "research"])
  assert.equal(result.stories[0].articleStatus, "accepted")
  assert.equal(result.stories[0].communityStatus, "accepted")
  assert.equal(result.stories[0].selectedComments, 1)
  assert.equal(result.orchestrationRuns[0].runId, "run-1")

  const initialPayload = JSON.stringify(result)
  assert.ok(initialPayload.length < 20_000, `initial payload was ${initialPayload.length} bytes`)
  assert.doesNotMatch(initialPayload, /FULL_RESULT_SENTINEL/)

  const details = getV2AdminStoryDetails(42, databasePath)
  assert.ok(details)
  assert.equal(details.article?.model, "analysis-model")
  assert.equal(details.article?.metrics.inputTokens, 100)
  assert.equal(details.article?.result.raw, fullResultSentinel)
  assert.equal(details.community?.result.summary, "Community summary")
  assert.equal(details.prefilterReasonCode, "AI_CAPABILITY_REPORT")
  assert.equal(details.prefilterModel, "prefilter-model")
  assert.equal(details.dimensions.length, 1)
  assert.equal(details.dimensions[0].dimension, "capability")
  assert.equal(details.dimensions[0].rationale, "Strong capability evidence.")

  const incompatibleDatabasePath = path.join(directory, "pipeline-without-diagnostics.db")
  copyFileSync(databasePath, incompatibleDatabasePath)
  const incompatibleDb = new Database(incompatibleDatabasePath)
  incompatibleDb.exec("ALTER TABLE v2_dimension_analyses DROP COLUMN diagnostics_json")
  incompatibleDb.close()
  assert.equal(getV2AdminData(incompatibleDatabasePath).available, false)
  assert.equal(getV2AdminStoryDetails(42, incompatibleDatabasePath), null)
  console.log("V2 admin data regression passed")
} finally {
  rmSync(directory, { recursive: true, force: true })
}
