import { fail, redirect, type RequestEvent } from "@sveltejs/kit"
import { existsSync, readFileSync } from "fs"
import { PIPELINE_DB_PATH, getPipelineStats, getPipelineTableData, type UrlEntry } from "$lib/server/db"
import { getPipelineStoragePaths } from "$lib/server/pipeline-storage"
import { ADMIN_COOKIE_NAME, adminAccessConfigured } from "$lib/server/admin-auth"
import {
  getPipelineCommandList,
  getPipelineCommandReadiness,
  getPipelineEnvironmentStatus,
  getPipelineRunSnapshot,
  startPipelineRun,
  type PipelineCommandName,
} from "$lib/server/pipeline-runner"
import type { Actions } from "./$types"

type PipelineCommand = {
  name: string
  label: string
  description: string
  readiness: { ready: boolean; reasons: string[] }
}

type RunRow = {
  id: number
  command: string
  status: string
  started_at: string
  finished_at: string | null
  exit_code: number | null
  log_path: string
  pid: number | null
  error: string | null
}

type LockRow = {
  id: number
  run_id: number | null
  command: string
  pid: number | null
  acquired_at: string
  stale: boolean
}

type LogViewer = {
  run: RunRow | null
  path: string | null
  exists: boolean
  tail: string
}

function readLogTail(logPath: string | null, lines = 120): { exists: boolean; tail: string } {
  if (!logPath || !existsSync(logPath)) {
    return {
      exists: false,
      tail: "Log file not found yet.",
    }
  }

  const content = readFileSync(logPath, "utf8")
  const parts = content.split(/\r?\n/)
  const tail =
    parts
      .slice(Math.max(0, parts.length - lines))
      .join("\n")
      .trimEnd() || "(log is empty)"

  return {
    exists: true,
    tail,
  }
}

export const load = (event: RequestEvent) => {
  const commandScope = event.url.pathname.startsWith("/v2/") ? "v2" : "v1"
  const rows = getPipelineTableData()
  const stats = getPipelineStats()
  const snapshot = getPipelineRunSnapshot()
  const env = getPipelineEnvironmentStatus()
  const storage = getPipelineStoragePaths()

  const requestedRunId = Number.parseInt(event.url.searchParams.get("run") ?? "", 10)
  const requestedRun = Number.isFinite(requestedRunId)
    ? ([snapshot.currentRun, ...snapshot.recentRuns].find((run) => run?.id === requestedRunId) ?? null)
    : null
  const selectedRun = requestedRun ?? snapshot.currentRun ?? snapshot.recentRuns[0] ?? null

  const logViewer: LogViewer = selectedRun
    ? {
        run: selectedRun,
        path: selectedRun.log_path,
        ...readLogTail(selectedRun.log_path),
      }
    : {
        run: null,
        path: null,
        exists: false,
        tail: "No pipeline runs have been recorded yet.",
      }

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
    tableData: rows as UrlEntry[],
    pipeline: {
      env,
      snapshot,
      commands: getPipelineCommandList(commandScope).map((command) => ({
        ...command,
        readiness: getPipelineCommandReadiness(command.name),
      })) as PipelineCommand[],
      logViewer,
      storage,
    },
    controlHref: event.url.pathname,
  }
}

export const actions: Actions = {
  logout: async (event: RequestEvent) => {
    event.cookies.delete(ADMIN_COOKIE_NAME, { path: "/" })
    throw redirect(303, event.url.pathname.startsWith("/v2/") ? "/v2/admin/login" : "/admin/login")
  },
  run: async (event: RequestEvent) => {
    const form = await event.request.formData()
    const commandName = form.get("command")
    const confirmValue = form.get("confirm")

    const commandScope = event.url.pathname.startsWith("/v2/") ? "v2" : "v1"
    if (
      typeof commandName !== "string" ||
      !getPipelineCommandList(commandScope).some((command) => command.name === commandName)
    ) {
      return fail(400, { message: "Unknown pipeline command." })
    }

    if (typeof confirmValue !== "string" || confirmValue.trim().toLowerCase() !== commandName.toLowerCase()) {
      return fail(400, { message: `Type ${commandName} to confirm.` })
    }

    let result

    try {
      result = startPipelineRun(commandName as PipelineCommandName)
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to start pipeline run."
      return fail(/already running/i.test(message) ? 409 : 500, { message })
    }

    throw redirect(303, `${event.url.pathname}?run=${result.run.id}`)
  },
}
