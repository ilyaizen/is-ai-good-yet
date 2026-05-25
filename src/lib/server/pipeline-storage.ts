import { existsSync, mkdirSync } from "node:fs"
import path from "node:path"

type PipelineStoragePaths = {
  dataDir: string
  pipelineDbPath: string
  adminDbPath: string
  logDir: string
}

function uniquePaths(paths: Array<string | undefined>): string[] {
  const seen = new Set<string>()
  const result: string[] = []

  for (const candidate of paths) {
    const trimmed = candidate?.trim()
    if (!trimmed || seen.has(trimmed)) continue
    seen.add(trimmed)
    result.push(trimmed)
  }

  return result
}

function resolvePreferredPath(candidates: string[]): string {
  const existing = candidates.find((candidate) => existsSync(candidate))
  return existing ?? candidates[0]
}

function getBaseCandidates(): string[] {
  const appRoot = process.cwd()

  return uniquePaths([
    process.env.PIPELINE_DATA_DIR,
    process.env.PIPELINE_STORAGE_DIR,
    path.join(appRoot, "pipeline", "data"),
    "/app/pipeline/data",
    "/data/is-ai-good-yet/pipeline/data",
    "/var/lib/is-ai-good-yet/pipeline/data",
  ])
}

export function getPipelineStoragePaths(): PipelineStoragePaths {
  const explicitDbPath = process.env.PIPELINE_DB_PATH?.trim()
  const explicitDataDir =
    process.env.PIPELINE_DATA_DIR?.trim() || process.env.PIPELINE_STORAGE_DIR?.trim() || (explicitDbPath ? path.dirname(explicitDbPath) : "")
  const dataDir = explicitDataDir || resolvePreferredPath(getBaseCandidates())

  return {
    dataDir,
    pipelineDbPath: explicitDbPath || path.join(dataDir, "pipeline.db"),
    adminDbPath: process.env.PIPELINE_ADMIN_DB_PATH?.trim() || path.join(dataDir, "admin.db"),
    logDir: process.env.PIPELINE_LOG_DIR?.trim() || path.join(dataDir, "logs"),
  }
}

export function ensurePipelineStoragePaths(): PipelineStoragePaths {
  const paths = getPipelineStoragePaths()
  mkdirSync(paths.dataDir, { recursive: true })
  mkdirSync(paths.logDir, { recursive: true })
  return paths
}
