import { createWriteStream, existsSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { spawn } from "node:child_process"
import Database from "better-sqlite3"
import { createOnceFinalizer, resolvePipelinePython } from "$lib/server/pipeline-runtime"
import { ensurePipelineStoragePaths, getPipelineStoragePaths } from "$lib/server/pipeline-storage"
import { env as privateEnv } from "$env/dynamic/private"

export type PipelineCommandName =
  | "catch_up"
  | "scrape"
  | "clean_articles"
  | "prefilter_content"
  | "sentiment_analyzer"
  | "v2_comments"
  | "v2_analyze"
  | "export"

export type PipelineCommandSpec = {
  name: PipelineCommandName
  label: string
  description: string
  args: string[]
}

export type PipelineRunRow = {
  id: number
  command: PipelineCommandName
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled"
  started_at: string
  finished_at: string | null
  exit_code: number | null
  log_path: string
  pid: number | null
  error: string | null
}

export type PipelineLockRow = {
  id: number
  run_id: number | null
  command: string
  pid: number | null
  acquired_at: string
}

export type PipelineRunSnapshot = {
  currentRun: PipelineRunRow | null
  lock: (PipelineLockRow & { stale: boolean }) | null
  recentRuns: PipelineRunRow[]
}

export type PipelineEnvironmentStatus = {
  repoRootExists: boolean
  venvPythonExists: boolean
  pipelineDirExists: boolean
  adminDbExists: boolean
  logDirExists: boolean
  groqApiKeyConfigured: boolean
  mistralApiKeyConfigured: boolean
}

/**
 * Resolve repo root from this module's location, not process.cwd().
 * This file lives at src/lib/server/pipeline-runner.ts → 3 dirs up = repo root.
 */
function getRepoRoot(): string {
  const modulePath = fileURLToPath(import.meta.url)
  return path.resolve(path.dirname(modulePath), "..", "..", "..")
}

const REPO_ROOT = getRepoRoot()
const STALE_LOCK_THRESHOLD_MS = 6 * 60 * 60 * 1000
const STORAGE_PATHS = getPipelineStoragePaths()
const PIPELINE_DIR = path.dirname(STORAGE_PATHS.dataDir)
const ADMIN_DB_PATH = STORAGE_PATHS.adminDbPath
const PIPELINE_LOG_DIR = STORAGE_PATHS.logDir
const PIPELINE_PYTHON = resolvePipelinePython({
  explicit: privateEnv.PIPELINE_PYTHON,
  repoRoot: REPO_ROOT,
  pipelineDir: PIPELINE_DIR,
  platform: process.platform,
  exists: existsSync,
})

const COMMANDS: Record<PipelineCommandName, PipelineCommandSpec> = {
  catch_up: {
    name: "catch_up",
    label: "Catch-up",
    description: "Run the full catch-up orchestrator.",
    args: ["-m", "src.catch_up", "-v"],
  },
  scrape: {
    name: "scrape",
    label: "Scrape",
    description: "Fetch article content with the normal browser-backed scraper.",
    args: ["-m", "src.scraper", "-v", "--lean", "--stealth-mode=seleniumbase", "--no-headful-switch", "-b", "50", "-c", "4"],
  },
  clean_articles: {
    name: "clean_articles",
    label: "Clean articles",
    description: "Normalize extracted article text files.",
    args: ["src/clean_articles.py"],
  },
  prefilter_content: {
    name: "prefilter_content",
    label: "Prefilter",
    description: "Classify article relevance before sentiment analysis.",
    args: ["-m", "src.prefilter_content", "-v"],
  },
  sentiment_analyzer: {
    name: "sentiment_analyzer",
    label: "Sentiment",
    description: "Score utility and trajectory with the Groq analyzer.",
    args: ["-m", "src.sentiment_analyzer", "-v"],
  },
  v2_comments: {
    name: "v2_comments",
    label: "Collect v2 comments",
    description: "Fetch and deterministically rank Hacker News comment candidates for v2.",
    args: ["-m", "src.hn_comments_v2", "-v"],
  },
  v2_analyze: {
    name: "v2_analyze",
    label: "Analyze v2 sentiment",
    description: "Run the versioned article and isolated-comment analysis against live pipeline data.",
    args: ["-m", "src.sentiment_v2", "-v"],
  },
  export: {
    name: "export",
    label: "Export",
    description: "Rebuild static JSON for the SvelteKit app.",
    args: ["-m", "src.export", "-v"],
  },
}

function ensureDirectories(): void {
  ensurePipelineStoragePaths()
}

function getDb(): Database.Database {
  ensureDirectories()
  return new Database(ADMIN_DB_PATH)
}

function bootstrapDb(db: Database.Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS pipeline_runs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      command TEXT NOT NULL,
      status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
      started_at TEXT NOT NULL,
      finished_at TEXT,
      exit_code INTEGER,
      log_path TEXT NOT NULL,
      pid INTEGER,
      error TEXT
    );

    CREATE TABLE IF NOT EXISTS pipeline_locks (
      id INTEGER PRIMARY KEY CHECK (id = 1),
      run_id INTEGER,
      command TEXT NOT NULL,
      pid INTEGER,
      acquired_at TEXT NOT NULL
    );
  `)
}

function isoNow(): string {
  return new Date().toISOString()
}

function isProcessAlive(pid: number | null): boolean {
  if (!pid || pid <= 0) return false

  try {
    process.kill(pid, 0)
    return true
  } catch {
    return false
  }
}

export function getPipelineEnvironmentStatus(): PipelineEnvironmentStatus {
  return {
    repoRootExists: existsSync(REPO_ROOT),
    venvPythonExists: existsSync(PIPELINE_PYTHON),
    pipelineDirExists: existsSync(PIPELINE_DIR),
    adminDbExists: existsSync(ADMIN_DB_PATH),
    logDirExists: existsSync(PIPELINE_LOG_DIR),
    groqApiKeyConfigured: Boolean(privateEnv.GROQ_API_KEY?.trim()),
    mistralApiKeyConfigured: Boolean(privateEnv.MISTRAL_API_KEY?.trim()),
  }
}

export function getPipelineCommandList(scope: "v1" | "v2" = "v1"): PipelineCommandSpec[] {
  const names: PipelineCommandName[] =
    scope === "v2"
      ? ["catch_up", "scrape", "clean_articles", "prefilter_content", "v2_comments", "v2_analyze"]
      : ["catch_up", "scrape", "clean_articles", "prefilter_content", "sentiment_analyzer", "export"]

  return names.map((name) => COMMANDS[name])
}

export function getPipelineCommand(command: PipelineCommandName): PipelineCommandSpec {
  return COMMANDS[command]
}

export function getPipelineRunSnapshot(): PipelineRunSnapshot {
  const db = getDb()
  bootstrapDb(db)

  const lockRow = db.prepare("SELECT id, run_id, command, pid, acquired_at FROM pipeline_locks WHERE id = 1").get() as
    | PipelineLockRow
    | undefined
  const currentRun = lockRow?.run_id
    ? (db.prepare("SELECT id, command, status, started_at, finished_at, exit_code, log_path, pid, error FROM pipeline_runs WHERE id = ?").get(lockRow.run_id) as PipelineRunRow | undefined)
    : undefined

  const recentRuns = db
    .prepare(
      "SELECT id, command, status, started_at, finished_at, exit_code, log_path, pid, error FROM pipeline_runs ORDER BY id DESC LIMIT 12",
    )
    .all() as PipelineRunRow[]

  const lock = lockRow
    ? {
        ...lockRow,
        stale: !isProcessAlive(lockRow.pid) || Date.now() - new Date(lockRow.acquired_at).getTime() > STALE_LOCK_THRESHOLD_MS,
      }
    : null

  return {
    currentRun: currentRun ?? null,
    lock,
    recentRuns,
  }
}

function clearStaleLock(db: Database.Database, lock: PipelineLockRow): void {
  const stale = !isProcessAlive(lock.pid) || Date.now() - new Date(lock.acquired_at).getTime() > STALE_LOCK_THRESHOLD_MS
  if (!stale) return

  db.prepare(
    "UPDATE pipeline_runs SET status = 'failed', finished_at = ?, error = ? WHERE id = ? AND status = 'running'",
  ).run(isoNow(), "Stale lock cleared automatically.", lock.run_id)
  db.prepare("DELETE FROM pipeline_locks WHERE id = 1").run()
}

export type StartPipelineRunResult = {
  run: PipelineRunRow
  command: PipelineCommandSpec
}

export function startPipelineRun(commandName: PipelineCommandName): StartPipelineRunResult {
  const command = getPipelineCommand(commandName)
  const db = getDb()
  bootstrapDb(db)

  const existingLock = db.prepare("SELECT id, run_id, command, pid, acquired_at FROM pipeline_locks WHERE id = 1").get() as
    | PipelineLockRow
    | undefined

  if (existingLock) {
    clearStaleLock(db, existingLock)
  }

  const activeLock = db.prepare("SELECT id, run_id, command, pid, acquired_at FROM pipeline_locks WHERE id = 1").get() as
    | PipelineLockRow
    | undefined

  if (activeLock) {
    throw new Error(`Pipeline is already running ${activeLock.command} (PID ${activeLock.pid ?? "?"})`)
  }

  const startedAt = isoNow()
  const logFileName = `${startedAt.replaceAll(":", "-")}-${commandName}.log`
  const logPath = path.join(PIPELINE_LOG_DIR, logFileName)

  const insertRun = db
    .prepare(
      "INSERT INTO pipeline_runs (command, status, started_at, log_path) VALUES (?, 'running', ?, ?)",
    )
    .run(commandName, startedAt, logPath)
  const runId = Number(insertRun.lastInsertRowid)

  const runRow = db.prepare(
    "SELECT id, command, status, started_at, finished_at, exit_code, log_path, pid, error FROM pipeline_runs WHERE id = ?",
  ).get(runId) as PipelineRunRow

  db.prepare(
    "INSERT INTO pipeline_locks (id, run_id, command, pid, acquired_at) VALUES (1, ?, ?, ?, ?)",
  ).run(runId, commandName, null, startedAt)

  const output = createWriteStream(logPath, { flags: "a" })
  output.write(`[${startedAt}] start ${commandName}\n`)
  output.write(`cwd=${PIPELINE_DIR}\n`)
  output.write(`python=${PIPELINE_PYTHON}\n`)
  output.write(`args=${command.args.join(" ")}\n\n`)

  const child = spawn(PIPELINE_PYTHON, command.args, {
    cwd: PIPELINE_DIR,
    env: {
      ...process.env,
      PYTHONUNBUFFERED: "1",
    },
    stdio: ["ignore", "pipe", "pipe"],
    detached: true,
  })

  db.prepare("UPDATE pipeline_runs SET pid = ? WHERE id = ?").run(child.pid, runId)
  db.prepare("UPDATE pipeline_locks SET pid = ? WHERE id = 1").run(child.pid)

  child.stdout?.pipe(output, { end: false })
  child.stderr?.pipe(output, { end: false })

  output.on("error", (error) => {
    console.error("Pipeline log stream error:", error)
  })

  const finalize = createOnceFinalizer((exitCode: number | null, errorMessage: string | null) => {
    const finishedAt = isoNow()
    const success = exitCode === 0 && errorMessage === null
    output.write(
      errorMessage
        ? `\n[${finishedAt}] error: ${errorMessage}\n`
        : `\n[${finishedAt}] exit code ${exitCode ?? "null"}\n`,
    )
    output.end()
    db.prepare(
      "UPDATE pipeline_runs SET status = ?, finished_at = ?, exit_code = ?, error = ? WHERE id = ?",
    ).run(success ? "succeeded" : "failed", finishedAt, exitCode, errorMessage, runId)
    db.prepare("DELETE FROM pipeline_locks WHERE id = 1 AND run_id = ?").run(runId)
  })

  child.on("error", (error) => {
    finalize(null, error.message)
  })

  child.on("close", (exitCode) => {
    finalize(exitCode, exitCode === 0 ? null : `Exited with code ${exitCode ?? "null"}`)
  })

  child.unref()

  return {
    run: {
      ...runRow,
      pid: child.pid ?? null,
      status: "running",
    },
    command,
  }
}
