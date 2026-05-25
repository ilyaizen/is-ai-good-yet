import { dev } from "$app/environment"
import { env as privateEnv } from "$env/dynamic/private"
import { createHash, timingSafeEqual } from "crypto"

export const ADMIN_COOKIE_NAME = "pipeline_admin_session"
export const ADMIN_SESSION_MAX_AGE = 60 * 60 * 12

function getConfiguredPassword(): string | null {
  const password = privateEnv.PIPELINE_ADMIN_PASSWORD?.trim()
  return password ? password : null
}

function sha256Hex(value: string): string {
  return createHash("sha256").update(value).digest("hex")
}

export function adminAccessConfigured(): boolean {
  return getConfiguredPassword() !== null
}

export function buildAdminCookieValue(password: string): string {
  return sha256Hex(password)
}

export function isValidAdminCookie(cookieValue: string | null | undefined): boolean {
  const password = getConfiguredPassword()
  if (!password || !cookieValue) return false

  const expected = sha256Hex(password)
  const received = cookieValue.trim()
  if (received.length !== expected.length) return false

  return timingSafeEqual(Buffer.from(received, "utf8"), Buffer.from(expected, "utf8"))
}

export function adminCookieOptions() {
  return {
    path: "/",
    httpOnly: true,
    sameSite: "lax" as const,
    secure: !dev,
    maxAge: ADMIN_SESSION_MAX_AGE,
  }
}

export function sanitizeAdminNextPath(value: FormDataEntryValue | string | null | undefined): string {
  const next = typeof value === "string" ? value.trim() : ""
  if (!next || !next.startsWith("/")) return "/admin"
  if (next.startsWith("//")) return "/admin"
  return next.startsWith("/admin") ? next : "/admin"
}
