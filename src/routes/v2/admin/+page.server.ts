import type { RequestEvent } from "@sveltejs/kit"
import { getV2AdminData } from "$lib/server/v2-admin-data"
import { getV2Methodology } from "$lib/server/v2-methodology"
import { actions, load as loadAdmin } from "../../admin/+page.server"

export { actions }

export const load = (event: RequestEvent) => ({
  ...loadAdmin(event, { includeV1Data: false }),
  v2: getV2AdminData(),
  methodology: getV2Methodology(),
})
