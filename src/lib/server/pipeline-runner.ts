import { createWriteStream, existsSync, mkdirSync } from "fs"
import path from "path"
import { spawn } from "child_process"
import Database from "better-sqlite3"
import { fileURLToPath } from "url"

export type PipelineCommandName =
  | "catch_up"
  | "scrape"
  | "clean_articles"
  | "prefilter_content"
  | "sentiment_analyzer"
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

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../../")
const PIPELINE_DIR = path.join(REPO_ROOT, "pipeline")
const ADMIN_DB_PATH = path.join(PIPELINE_DIR, "data", "admin.db")
const PIPELINE_LOG_DIR = path.join(PIPELINE_DIR, "data", "logs")
const VENV_PYTHON = path.join(REPO_ROOT, ".venv", "bin", "python")
const STALE_LOCK_THRESHOLD_MS = 6 * 60 * 60 * 1000

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
  export: {
    name: "export",
    label: "Export",
    description: "Rebuild static JSON for the SvelteKit app.",
    args: ["-m", "src.export", "-v"],
  },
}

function ensureDirectories(): void {
  mkdirSync(path.dirname(ADMIN_DB_PATH), { recursive: true })
  mkdirSync(PIPELINE_LOG_DIR, { recursive: true })
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
    venvPythonExists: existsSync(VENV_PYTHON),
    pipelineDirExists: existsSync(PIPELINE_DIR),
    adminDbExists: existsSync(ADMIN_DB_PATH),
    logDirExists: existsSync(PIPELINE_LOG_DIR),
    groqApiKeyConfigured: Boolean(process.env.GROQ_API_KEY?.trim()),
    mistralApiKeyConfigured: Boolean(process.env.MISTRAL_API_KEY?.trim()),
  }
}

export function getPipelineCommandList(): PipelineCommandSpec[] {
  return Object.values(COMMANDS)
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
  output.write(`python=${VENV_PYTHON}\n`)
  output.write(`args=${command.args.join(" ")}\n\n`)

  const child = spawn(VENV_PYTHON, command.args, {
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

  child.on("error", (error) => {
    const finishedAt = isoNow()
    output.write(`\n[${finishedAt}] spawn error: ${error.message}\n`)
    output.end()
    db.prepare(
      "UPDATE pipeline_runs SET status = 'failed', finished_at = ?, exit_code = NULL, error = ? WHERE id = ?",
    ).run(finishedAt, error.message, runId)
    db.prepare("DELETE FROM pipeline_locks WHERE id = 1 AND run_id = ?").run(runId)
  })

  child.on("close", (exitCode) => {
    const finishedAt = isoNow()
    const success = exitCode === 0
    output.write(`\n[${finishedAt}] exit code ${exitCode ?? "null"}\n`)
    output.end()
    db.prepare(
      "UPDATE pipeline_runs SET status = ?, finished_at = ?, exit_code = ?, error = ? WHERE id = ?",
    ).run(success ? "succeeded" : "failed", finishedAt, exitCode ?? null, success ? null : `Exited with code ${exitCode ?? "null"}`, runId)
    db.prepare("DELETE FROM pipeline_locks WHERE id = 1 AND run_id = ?").run(runId)
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
