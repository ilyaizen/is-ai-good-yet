import { getPipelineStats, getPipelineTableData } from "$lib/server/db"
import type { PageServerLoad } from "./$types"
import { redirect, error } from "@sveltejs/kit"
import { dev } from "$app/environment"

// Default URL parameters for the pipeline-admin table view
const DEFAULT_PARAMS = {
  min_score: "20",
  min_comments: "5",
  status: "scraped",
  category: "all",
  per_page: "100",
}

export const load: PageServerLoad = async ({ url }) => {
  // Block access in production - this route requires local SQLite access
  if (!dev) {
    throw error(404, "Not found")
  }

  // Redirect to defaults if user arrives without any filter params
  const hasParams = url.searchParams.has("min_score") || url.searchParams.has("status")
  if (!hasParams) {
    const newUrl = new URL(url)
    for (const [key, value] of Object.entries(DEFAULT_PARAMS)) {
      newUrl.searchParams.set(key, value)
    }
    throw redirect(302, newUrl.pathname + newUrl.search)
  }

  // Load live data from SQLite
  const stats = getPipelineStats()
  const tableData = getPipelineTableData()

  return {
    stats,
    tableData,
  }
}
