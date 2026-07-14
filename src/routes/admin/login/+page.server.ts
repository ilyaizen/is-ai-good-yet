import { fail, redirect, type RequestEvent } from "@sveltejs/kit"
import {
  ADMIN_COOKIE_NAME,
  adminAccessConfigured,
  adminCookieOptions,
  buildAdminCookieValue,
  getConfiguredPassword,
  isValidAdminCookie,
  sanitizeAdminNextPath,
} from "$lib/server/admin-auth"
import type { Actions } from "./$types"

export const load = (event: RequestEvent) => {
  const next = sanitizeAdminNextPath(event.url.searchParams.get("next"))

  if (isValidAdminCookie(event.cookies.get(ADMIN_COOKIE_NAME))) {
    throw redirect(303, next)
  }

  return {
    configured: adminAccessConfigured(),
    next,
  }
}

export const actions: Actions = {
  default: async (event: RequestEvent) => {
    const form = await event.request.formData()
    const next = sanitizeAdminNextPath(form.get("next"))
    const password = String(form.get("password") ?? "").trim()

    if (!adminAccessConfigured()) {
      return fail(503, {
        message: "Admin password is not configured.",
        next,
      })
    }

    const expected = getConfiguredPassword() ?? ""
    if (!expected || password !== expected) {
      return fail(401, {
        message: "Wrong password.",
        next,
      })
    }

    event.cookies.set(ADMIN_COOKIE_NAME, buildAdminCookieValue(password), adminCookieOptions())
    throw redirect(303, next)
  },
}
