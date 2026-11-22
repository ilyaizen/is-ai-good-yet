import type { InfluentialArticle, WeeklySnapshot } from "$lib/server/db"

export const DAY_MS = 86_400_000
export const NO_CEILING = 45
export const YES_FLOOR = 55

export type StorySortKey = "hn_timestamp" | "hn_score" | "hn_comments" | "sentiment_score"

export interface ChartBounds {
  top: number
  bottom: number
  ticks: number[]
}

const MEDIUM_DATE = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
})

const MONTH_YEAR = new Intl.DateTimeFormat("en-US", {
  month: "short",
  year: "2-digit",
  timeZone: "UTC",
})

const INT_FORMAT = new Intl.NumberFormat("en-US")

export type VerdictBand = "yes" | "mid" | "no"

export function verdictBandFor(score: number): VerdictBand {
  return score >= YES_FLOOR ? "yes" : score < NO_CEILING ? "no" : "mid"
}

const BAND_ANSWER = {
  yes: "YES",
  mid: "NOT YET",
  no: "NO",
} as const satisfies Record<VerdictBand, string>

export function answerFor(score: number): "YES" | "NOT YET" | "NO" {
  return BAND_ANSWER[verdictBandFor(score)]
}

export function sentimentBand(score: number): "pos" | "neu" | "neg" {
  return score > 0.2 ? "pos" : score < -0.2 ? "neg" : "neu"
}

export function snapshotsWithin(
  snapshots: readonly WeeklySnapshot[],
  days: number,
  exportedAt: string | null
): WeeklySnapshot[] {
  const sorted = snapshots
    .filter((item) => Number.isFinite(Date.parse(item.weekStart)))
    .sort((a, b) => a.weekStart.localeCompare(b.weekStart))
  const last = sorted.at(-1)
  if (!last) return []
  const exportTime = Date.parse(exportedAt ?? "")
  const end = Number.isFinite(exportTime) ? exportTime : Date.parse(last.weekStart)
  const start = end - days * DAY_MS
  return sorted.filter((item) => {
    const time = Date.parse(item.weekStart)
    return time >= start && time <= end
  })
}

/**
 * Sort the eligible story set by actual HN submission time descending before any slicing.
 * Tie-breaks deterministically by hn_id descending.
 */
export function sortStories(articles: readonly InfluentialArticle[], key: StorySortKey): InfluentialArticle[] {
  return [...articles].sort((a, b) => {
    const primary = b[key] - a[key]
    if (primary !== 0) return primary
    return b.hn_timestamp - a.hn_timestamp || b.hn_id - a.hn_id
  })
}

export function weeklyRange(
  snapshots: readonly WeeklySnapshot[],
  days: number | null,
  exportedAt: string | null
): WeeklySnapshot[] {
  if (days !== null) {
    return snapshotsWithin(snapshots, days, exportedAt)
  }
  return snapshots
    .filter((item) => Number.isFinite(Date.parse(item.weekStart)))
    .sort((a, b) => a.weekStart.localeCompare(b.weekStart))
}

export function chartBounds(samples: readonly WeeklySnapshot[]): ChartBounds {
  const scores = samples.map((sample) => sample.verdictScore)
  const maxVal = scores.length ? Math.max(YES_FLOOR + 10, ...scores) : 75
  const minVal = scores.length ? Math.min(NO_CEILING - 5, ...scores) : 35
  const top = Math.min(100, Math.ceil((maxVal + 3) / 5) * 5)
  const bottom = Math.max(0, Math.floor((minVal - 3) / 5) * 5)
  const ticks = Array.from(new Set([top, YES_FLOOR, NO_CEILING, bottom])).sort((a, b) => b - a)
  return { top, bottom, ticks }
}

export function monthTicks(startMs: number, endMs: number, width: number, days: number | null): number[] {
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs) || endMs <= startMs) return []
  const spanDays = (endMs - startMs) / DAY_MS
  const strideMonths = days === 90 ? 1 : spanDays > 600 ? (width < 520 ? 12 : 6) : width < 480 ? 3 : 2

  const first = new Date(startMs)
  let cursor = Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 1)
  const result: number[] = []

  while (cursor < endMs) {
    const frac = (cursor - startMs) / (endMs - startMs)
    const px = frac * width
    if (px >= 28 && px <= width - 28) {
      result.push(cursor)
    }
    const next = new Date(cursor)
    cursor = Date.UTC(next.getUTCFullYear(), next.getUTCMonth() + strideMonths, 1)
  }
  return result
}

export function formatIsoDate(article: Pick<InfluentialArticle, "hn_timestamp" | "hn_date">): string {
  if (Number.isFinite(article.hn_timestamp) && article.hn_timestamp > 0) {
    return new Date(article.hn_timestamp * 1000).toISOString().slice(0, 10)
  }
  return article.hn_date || "—"
}

export function formatMediumDate(value: string | number): string {
  const parsed = new Date(value)
  return Number.isFinite(parsed.getTime()) ? MEDIUM_DATE.format(parsed) : String(value)
}

export function formatMonthLabel(ms: number): string {
  return MONTH_YEAR.format(ms).replace(/ (\d{2})$/, " '$1")
}

export function formatInt(value: number): string {
  return INT_FORMAT.format(value)
}

export function hostnameOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "")
  } catch {
    return ""
  }
}

/**
 * Band-consistent score token: "+1.5" / "±0.2" / "−1.5". The prefix reflects the
 * sentiment band rather than the raw sign, so it never contradicts the badge color.
 */
export function bandScore(score: number): string {
  const magnitude = Math.abs(score).toFixed(1)
  const prefix = sentimentBand(score) === "pos" ? "+" : sentimentBand(score) === "neg" ? "−" : "±"
  return `${prefix}${magnitude}`
}
