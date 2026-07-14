import { redirect, type RequestEvent } from "@sveltejs/kit"

export const load = (event: RequestEvent) => {
  const runParam = event.url.searchParams.get("run")
  const qs = runParam ? `?run=${runParam}` : ""
  throw redirect(303, `/admin${qs}`)
}
