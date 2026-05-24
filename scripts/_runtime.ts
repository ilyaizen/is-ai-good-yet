import { existsSync } from "node:fs"
import Database from "better-sqlite3"
import path from "node:path"
import { fileURLToPath } from "node:url"

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
export const pipelineDbPath = path.join(repoRoot, "pipeline", "data", "pipeline.db")

export function openPipelineDb(readonly = true): Database.Database {
  if (!existsSync(pipelineDbPath)) {
    throw new Error(`Pipeline database not found at ${pipelineDbPath}`)
  }

  return new Database(pipelineDbPath, { readonly })
}
