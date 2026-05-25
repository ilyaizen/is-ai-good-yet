import { existsSync } from "fs"
import { redirect, type RequestEvent } from "@sveltejs/kit"
import { PIPELINE_DB_PATH, getPipelineStats, getPipelineTableData } from "$lib/server/db"
import { getPipelineStoragePaths } from "$lib/server/pipeline-storage"
import { ADMIN_COOKIE_NAME, adminAccessConfigured } from "$lib/server/admin-auth"
import { getPipelineEnvironmentStatus, getPipelineRunSnapshot } from "$lib/server/pipeline-runner"

export const load = (_event: RequestEvent) => {
  const rows = getPipelineTableData()
  const stats = getPipelineStats()
  const snapshot = getPipelineRunSnapshot()
  const env = getPipelineEnvironmentStatus()
  const storage = getPipelineStoragePaths()

  const total = rows.length
  const approved = rows.filter((row) => row.content_category === "AI_DISCOURSE").length
  const refused = rows.filter((row) => row.content_category !== null && row.content_category !== "AI_DISCOURSE").length
  const pending = rows.filter((row) => row.content_category === null).length

  return {
    configured: adminAccessConfigured(),
    dbExists: existsSync(PIPELINE_DB_PATH),
    counts: {
      total,
      approved,
      refused,
      pending,
      other: Math.max(0, total - approved - refused - pending),
    },
    stats,
    pipeline: {
      env,
      snapshot,
      storage,
    },
    controlHref: "/admin/pipeline-control",
  }
}

export const actions = {
  logout: async (event: RequestEvent) => {
    event.cookies.delete(ADMIN_COOKIE_NAME, { path: "/" })
    throw redirect(303, "/admin/login")
  },
}
