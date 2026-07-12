import type { RequestEvent } from "@sveltejs/kit"
import { getV2Methodology } from "$lib/server/v2-methodology"
import { actions, load as loadAdmin } from "../../admin/+page.server"

export { actions }

export const load = (event: RequestEvent) => ({
  ...loadAdmin(event),
  methodology: getV2Methodology()
})
