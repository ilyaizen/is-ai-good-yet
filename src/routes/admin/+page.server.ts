import { fail, redirect, type RequestEvent } from "@sveltejs/kit"
import { existsSync, readFileSync } from "fs"
import { PIPELINE_DB_PATH, getPipelineTableData, type UrlEntry } from "$lib/server/db"
import { ADMIN_COOKIE_NAME, adminAccessConfigured } from "$lib/server/admin-auth"
import type { Actions } from "./$types"
import {
  getPipelineCommandList,
  getPipelineEnvironmentStatus,
  getPipelineRunSnapshot,
  startPipelineRun,
  type PipelineCommandName,
} from "$lib/server/pipeline-runner"

type AdminLinkRow = {
  title: string
  url: string
  domain: string
  hnId: number | null
  hnScore: number | null
  hnComments: number | null
  hnTimestamp: number | null
  category: string | null
  status: string
  opinion: string | null
  summary: string
  reason: string
  refusalStage: "prefilter" | "classifier" | "category" | "unknown"
}

type AnalysisJson = Record<string, unknown> & {
  reason?: unknown
  reasoning?: unknown
  summary?: unknown
  note?: unknown
  reject?: unknown
  category?: unknown
}

function parseJson(value: string | null): AnalysisJson | null {
  if (!value) return null
  try {
    const parsed = JSON.parse(value)
    return parsed && typeof parsed === "object" ? (parsed as AnalysisJson) : null
  } catch {
    return null
  }
}

function getDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "")
  } catch {
    return url
  }
}

function firstString(...values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) {
      return value.trim()
    }
  }
  return null
}

function getRefusalDetails(row: UrlEntry): { reason: string; refusalStage: AdminLinkRow["refusalStage"] } {
  const filter = parseJson(row.content_filter_json)
  const classification = parseJson(row.classification_json)

  const filterRejected = filter?.reject === true
  const classifierRejected = classification?.reject === true

  if (filterRejected) {
    return {
      refusalStage: "prefilter",
      reason:
        firstString(filter?.reason, filter?.reasoning, filter?.summary, filter?.note) ??
        "Rejected by prefilter",
    }
  }

  if (classifierRejected) {
    return {
      refusalStage: "classifier",
      reason:
        firstString(classification?.reason, classification?.reasoning, classification?.summary, classification?.note) ??
        "Rejected by classifier",
    }
  }

  if (row.content_category && row.content_category !== "AI_DISCOURSE") {
    return {
      refusalStage: "category",
      reason:
        firstString(classification?.reason, classification?.reasoning, filter?.reason, filter?.reasoning) ??
        `Classified as ${row.content_category}`,
    }
  }

  return {
    refusalStage: "unknown",
    reason:
      firstString(classification?.summary, classification?.reason, filter?.reason, filter?.summary) ??
      "No analysis reason stored",
  }
}

function mapRow(row: UrlEntry): AdminLinkRow {
  const refusal = getRefusalDetails(row)

  return {
    title: row.hn_title || "Untitled",
    url: row.url,
    domain: getDomain(row.url),
    hnId: row.hn_id,
    hnScore: row.hn_score,
    hnComments: row.hn_comments,
    hnTimestamp: row.hn_timestamp,
    category: row.content_category,
    status: row.status,
    opinion: row.opinion,
    summary: firstString(parseJson(row.classification_json)?.summary) ?? "",
    reason: refusal.reason,
    refusalStage: refusal.refusalStage,
  }
}

function isRefused(row: UrlEntry): boolean {
  const filter = parseJson(row.content_filter_json)
  const classification = parseJson(row.classification_json)

  return (
    filter?.reject === true ||
    classification?.reject === true ||
    (row.content_category !== null && row.content_category !== "AI_DISCOURSE")
  )
}

const pipelineCommandNames = new Set<PipelineCommandName>(getPipelineCommandList().map((command) => command.name))

function readLogTail(logPath: string | null, lines = 120): { exists: boolean; tail: string } {
  if (!logPath || !existsSync(logPath)) {
    return {
      exists: false,
      tail: "Log file not found yet.",
    }
  }

  const content = readFileSync(logPath, "utf8")
  const parts = content.split(/\r?\n/)
  const tail = parts.slice(Math.max(0, parts.length - lines)).join("\n").trimEnd() || "(log is empty)"

  return {
    exists: true,
    tail,
  }
}

export const load = (event: RequestEvent) => {
  const configured = adminAccessConfigured()
  const dbExists = existsSync(PIPELINE_DB_PATH)
  const rows = getPipelineTableData()
  const snapshot = getPipelineRunSnapshot()

  const refusedRows = rows.filter(isRefused)
  const pendingRows = rows.filter((row) => row.content_category === null)
  const approvedRows = rows.filter((row) => row.content_category === "AI_DISCOURSE")

  const requestedRunId = Number.parseInt(event.url.searchParams.get("run") ?? "", 10)
  const requestedRun = Number.isFinite(requestedRunId)
    ? [snapshot.currentRun, ...snapshot.recentRuns].find((run) => run?.id === requestedRunId) ?? null
    : null
  const selectedRun = requestedRun ?? snapshot.currentRun ?? snapshot.recentRuns[0] ?? null
  const logViewer = selectedRun
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

  return {
    configured,
    dbExists,
    counts: {
      total: rows.length,
      approved: approvedRows.length,
      refused: refusedRows.length,
      pending: pendingRows.length,
      other: Math.max(0, rows.length - approvedRows.length - refusedRows.length - pendingRows.length),
    },
    refusedLinks: refusedRows.slice(0, 60).map(mapRow),
    recentLinks: rows.slice(0, 30).map(mapRow),
    pipeline: {
      env: getPipelineEnvironmentStatus(),
      snapshot,
      commands: getPipelineCommandList(),
      logViewer,
    },
  }
}

export const actions: Actions = {
  logout: async (event: RequestEvent) => {
    event.cookies.delete(ADMIN_COOKIE_NAME, { path: "/" })
    throw redirect(303, "/admin/login")
  },
  run: async (event: RequestEvent) => {
    const form = await event.request.formData()
    const commandName = form.get("command")

    if (typeof commandName !== "string" || !pipelineCommandNames.has(commandName as PipelineCommandName)) {
      return fail(400, { message: "Unknown pipeline command." })
    }

    let result

    try {
      result = startPipelineRun(commandName as PipelineCommandName)
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to start pipeline run."
      return fail(/already running/i.test(message) ? 409 : 500, { message })
    }

    throw redirect(303, `/admin?run=${result.run.id}`)
  },
}
