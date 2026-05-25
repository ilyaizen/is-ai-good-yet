import { redirect } from "@sveltejs/kit"

export const load = () => {
  throw redirect(303, "/admin/pipeline-control")
}
