import { createWriteStream, existsSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { spawn, spawnSync } from "node:child_process"
import Database from "better-sqlite3"
import {
  createOnceFinalizer,
  resolvePipelinePython,
  resolvePipelineSourceDirectory,
} from "$lib/server/pipeline-runtime"
import { ensurePipelineStoragePaths, getPipelineStoragePaths } from "$lib/server/pipeline-storage"
import {
  evaluateCommandReadiness,
  getPipelineCommand as getConfiguredPipelineCommand,
  getPipelineCommandList as getConfiguredPipelineCommandList,
  type PipelineCommandName,
  type PipelineCommandReadiness,
  type PipelineCommandSpec,
  type PipelinePreflightSnapshot,
} from "$lib/server/pipeline-command-config"
import { env as privateEnv } from "$env/dynamic/private"

export type { PipelineCommandName, PipelineCommandSpec } from "$lib/server/pipeline-command-config"

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
  preflight: PipelinePreflightSnapshot
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
const PIPELINE_DIR = resolvePipelineSourceDirectory({
  explicit: privateEnv.PIPELINE_SOURCE_DIR,
  repoRoot: REPO_ROOT,
  cwd: process.cwd(),
  exists: existsSync,
})
const ADMIN_DB_PATH = STORAGE_PATHS.adminDbPath
const PIPELINE_LOG_DIR = STORAGE_PATHS.logDir
const PIPELINE_PYTHON = resolvePipelinePython({
  explicit: privateEnv.PIPELINE_PYTHON,
  repoRoot: REPO_ROOT,
  pipelineDir: PIPELINE_DIR,
  platform: process.platform,
  exists: existsSync,
})

const PREFLIGHT_CACHE_MS = 30_000
let preflightCache: { checkedAt: number; snapshot: PipelinePreflightSnapshot } | null = null

function failedPreflight(reason: string): PipelinePreflightSnapshot {
  const failed = { ok: false, reason }
  const groqConfigured = Boolean(privateEnv.GROQ_API_KEY?.trim())
  return {
    python: failed,
    storage: failed,
    scraper: failed,
    groq: {
      ok: groqConfigured,
      reason: groqConfigured
        ? "GROQ_API_KEY is configured."
        : "GROQ_API_KEY is not configured in the application environment.",
    },
    residential: { ok: true, reason: "Residential configuration was not checked." },
  }
}

export function getPipelinePreflightSnapshot(force = false): PipelinePreflightSnapshot {
  if (!force && preflightCache && Date.now() - preflightCache.checkedAt < PREFLIGHT_CACHE_MS) {
    return preflightCache.snapshot
  }
  if (!existsSync(PIPELINE_PYTHON)) {
    return failedPreflight(`Pipeline Python executable is missing: ${PIPELINE_PYTHON}`)
  }
  if (!existsSync(PIPELINE_DIR)) {
    return failedPreflight(`Pipeline source directory is missing: ${PIPELINE_DIR}`)
  }

  const result = spawnSync(PIPELINE_PYTHON, ["-m", "src.preflight", "--json"], {
    cwd: PIPELINE_DIR,
    env: {
      ...process.env,
      PIPELINE_DATA_DIR: STORAGE_PATHS.dataDir,
      PIPELINE_DB_PATH: STORAGE_PATHS.pipelineDbPath,
      PYTHONIOENCODING: "utf-8",
      PYTHONUTF8: "1",
    },
    encoding: "utf8",
    timeout: 20_000,
  })

  let snapshot: PipelinePreflightSnapshot
  try {
    const jsonLine = result.stdout
      ?.split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .at(-1)
    if (!jsonLine) throw new Error("Preflight produced no JSON output.")
    snapshot = JSON.parse(jsonLine) as PipelinePreflightSnapshot
  } catch {
    const detail =
      result.error?.message || result.stderr?.trim() || `preflight exited ${result.status ?? "without a status"}`
    snapshot = failedPreflight(`Pipeline preflight failed: ${detail}`)
  }
  preflightCache = { checkedAt: Date.now(), snapshot }
  return snapshot
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
    preflight: getPipelinePreflightSnapshot(),
  }
}

export function getPipelineCommandList(scope: "v1" | "v2" = "v1"): PipelineCommandSpec[] {
  return getConfiguredPipelineCommandList(scope)
}

export function getPipelineCommand(command: PipelineCommandName): PipelineCommandSpec {
  return getConfiguredPipelineCommand(command)
}

export function getPipelineCommandReadiness(command: PipelineCommandName, force = false): PipelineCommandReadiness {
  return evaluateCommandReadiness(command, getPipelinePreflightSnapshot(force))
}

export function getPipelineRunSnapshot(): PipelineRunSnapshot {
  const db = getDb()
  bootstrapDb(db)

  const lockRow = db.prepare("SELECT id, run_id, command, pid, acquired_at FROM pipeline_locks WHERE id = 1").get() as
    | PipelineLockRow
    | undefined
  const currentRun = lockRow?.run_id
    ? (db
        .prepare(
          "SELECT id, command, status, started_at, finished_at, exit_code, log_path, pid, error FROM pipeline_runs WHERE id = ?"
        )
        .get(lockRow.run_id) as PipelineRunRow | undefined)
    : undefined

  const recentRuns = db
    .prepare(
      "SELECT id, command, status, started_at, finished_at, exit_code, log_path, pid, error FROM pipeline_runs ORDER BY id DESC LIMIT 12"
    )
    .all() as PipelineRunRow[]

  const lock = lockRow
    ? {
        ...lockRow,
        stale:
          !isProcessAlive(lockRow.pid) ||
          Date.now() - new Date(lockRow.acquired_at).getTime() > STALE_LOCK_THRESHOLD_MS,
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
    "UPDATE pipeline_runs SET status = 'failed', finished_at = ?, error = ? WHERE id = ? AND status = 'running'"
  ).run(isoNow(), "Stale lock cleared automatically.", lock.run_id)
  db.prepare("DELETE FROM pipeline_locks WHERE id = 1").run()
}

export type StartPipelineRunResult = {
  run: PipelineRunRow
  command: PipelineCommandSpec
}

export function startPipelineRun(commandName: PipelineCommandName): StartPipelineRunResult {
  const command = getPipelineCommand(commandName)
  const readiness = getPipelineCommandReadiness(commandName, true)
  if (!readiness.ready) {
    throw new Error(`Pipeline command is not ready: ${readiness.reasons.join(" ")}`)
  }
  const db = getDb()
  bootstrapDb(db)

  const existingLock = db
    .prepare("SELECT id, run_id, command, pid, acquired_at FROM pipeline_locks WHERE id = 1")
    .get() as PipelineLockRow | undefined

  if (existingLock) {
    clearStaleLock(db, existingLock)
  }

  const activeLock = db
    .prepare("SELECT id, run_id, command, pid, acquired_at FROM pipeline_locks WHERE id = 1")
    .get() as PipelineLockRow | undefined

  if (activeLock) {
    throw new Error(`Pipeline is already running ${activeLock.command} (PID ${activeLock.pid ?? "?"})`)
  }

  const startedAt = isoNow()
  const logFileName = `${startedAt.replaceAll(":", "-")}-${commandName}.log`
  const logPath = path.join(PIPELINE_LOG_DIR, logFileName)

  const insertRun = db
    .prepare("INSERT INTO pipeline_runs (command, status, started_at, log_path) VALUES (?, 'running', ?, ?)")
    .run(commandName, startedAt, logPath)
  const runId = Number(insertRun.lastInsertRowid)

  const runRow = db
    .prepare(
      "SELECT id, command, status, started_at, finished_at, exit_code, log_path, pid, error FROM pipeline_runs WHERE id = ?"
    )
    .get(runId) as PipelineRunRow

  db.prepare("INSERT INTO pipeline_locks (id, run_id, command, pid, acquired_at) VALUES (1, ?, ?, ?, ?)").run(
    runId,
    commandName,
    null,
    startedAt
  )

  const output = createWriteStream(logPath, { flags: "a" })
  output.write(`[${startedAt}] start ${commandName}\n`)
  output.write(`cwd=${PIPELINE_DIR}\n`)
  output.write(`python=${PIPELINE_PYTHON}\n`)
  output.write(`args=${command.args.join(" ")}\n\n`)

  const child = spawn(PIPELINE_PYTHON, command.args, {
    cwd: PIPELINE_DIR,
    env: {
      ...process.env,
      PIPELINE_DATA_DIR: STORAGE_PATHS.dataDir,
      PIPELINE_DB_PATH: STORAGE_PATHS.pipelineDbPath,
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
        : `\n[${finishedAt}] exit code ${exitCode ?? "null"}\n`
    )
    output.end()
    db.prepare("UPDATE pipeline_runs SET status = ?, finished_at = ?, exit_code = ?, error = ? WHERE id = ?").run(
      success ? "succeeded" : "failed",
      finishedAt,
      exitCode,
      errorMessage,
      runId
    )
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
