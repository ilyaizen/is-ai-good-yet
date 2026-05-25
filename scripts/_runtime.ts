import { existsSync } from "node:fs"
import Database from "better-sqlite3"
import { getPipelineStoragePaths } from "../src/lib/server/pipeline-storage"

export const pipelineDbPath = getPipelineStoragePaths().pipelineDbPath

export function openPipelineDb(readonly = true): Database.Database {
  if (!existsSync(pipelineDbPath)) {
    throw new Error(`Pipeline database not found at ${pipelineDbPath}`)
  }

  return new Database(pipelineDbPath, { readonly })
}
