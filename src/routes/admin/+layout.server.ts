import { redirect, type RequestEvent } from "@sveltejs/kit"
import { adminAccessConfigured, isValidAdminCookie, ADMIN_COOKIE_NAME } from "$lib/server/admin-auth"

export const load = (event: RequestEvent) => {
  const configured = adminAccessConfigured()
  const authenticated = isValidAdminCookie(event.cookies.get(ADMIN_COOKIE_NAME))

  if (event.url.pathname.endsWith("/admin/login")) {
    return { configured, authenticated }
  }

  if (!authenticated) {
    const loginPath = event.url.pathname.startsWith("/v2/") ? "/v2/admin/login" : "/admin/login"
    throw redirect(303, `${loginPath}?next=${encodeURIComponent(event.url.pathname)}`)
  }

  return {
    configured,
    authenticated,
  }
}
