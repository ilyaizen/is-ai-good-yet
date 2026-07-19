import { redirect, type RequestEvent } from "@sveltejs/kit"
import { getV2AdminData } from "$lib/server/v2-admin-data"
import { getV2Methodology } from "$lib/server/v2-methodology"
import { ADMIN_COOKIE_NAME } from "$lib/server/admin-auth"
import type { Actions } from "./$types"

export const load = () => ({
  v2: getV2AdminData(),
  methodology: getV2Methodology(),
})

// The shell bar's `?/logout` form (in +layout.svelte) resolves to this action.
export const actions: Actions = {
  logout: async (event: RequestEvent) => {
    event.cookies.delete(ADMIN_COOKIE_NAME, { path: "/" })
    throw redirect(303, "/v2/admin/login")
  },
}
