import { error, json } from "@sveltejs/kit"
import { ADMIN_COOKIE_NAME, isValidAdminCookie } from "$lib/server/admin-auth"
import { getV2AdminStoryDetails } from "$lib/server/v2-admin-data"
import type { RequestHandler } from "./$types"

export const GET: RequestHandler = ({ params, cookies }) => {
  if (!isValidAdminCookie(cookies.get(ADMIN_COOKIE_NAME))) {
    throw error(401, "Admin authentication required.")
  }

  const hnStoryId = Number.parseInt(params.id, 10)
  if (!Number.isInteger(hnStoryId) || hnStoryId <= 0) {
    throw error(400, "Invalid HN story ID.")
  }

  const story = getV2AdminStoryDetails(hnStoryId)
  if (!story) {
    throw error(404, "V2 story not found.")
  }

  return json({ story })
}
