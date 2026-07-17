/**
 * Pure derivations shared by the public V2 surface.
 *
 * Single source of truth for the "adequacy word", tension flag, and direction
 * labels the card and hero render. Nothing here reads JSON or knows Python
 * field names — callers pass already-typed values from {@link V2PageData}.
 *
 * The aggregation math stays in the backend; these only translate typed numbers
 * into the restrained, verdict-supporting labels the public card shows.
 */

import type { V2CommunityDimension, V2DimensionValue, V2HistoryPoint } from "$lib/types/v2"
import { V2_DIMENSIONS } from "$lib/types/v2"

export type Adequacy = "ROBUST" | "USABLE" | "THIN" | "NONE"

/**
 * Adequacy from ESS + branch spread. Mirrors the backend measurement
 * (ESS / 12 target, 6 branches target). `NONE` for unaddressed dimensions.
 */
export function adequacy(dimension: V2CommunityDimension): Adequacy {
  if (dimension.applicability === "not_addressed") return "NONE"
  if (dimension.effectiveSampleSize >= 12 && dimension.applicableBranchCount >= 6) return "ROBUST"
  if (dimension.effectiveSampleSize >= 6) return "USABLE"
  return "THIN"
}

/** Adequacy for an article-only dimension: no community sample to weigh. */
export function articleAdequacy(dimension: V2DimensionValue): Adequacy {
  return dimension.applicability === "not_addressed" ? "NONE" : "THIN"
}

export type Tension =
  | "SOURCES AGREE"
  | "SOURCES DIVERGE"
  | "OPPOSING DIRECTIONS"
  | "ARTICLE ONLY"
  | "COMMUNITY ONLY"
  | "NOT YET ANALYZED"

/**
 * One tension flag per dimension. A sign difference always wins; otherwise
 * divergence magnitude decides. Replaces the numeric divergence readout.
 */
export function tension(
  articleScore: number | null,
  communityScore: number | null,
  divergence: number | null
): Tension {
  const hasArticle = articleScore !== null
  const hasCommunity = communityScore !== null
  if (!hasArticle && !hasCommunity) return "NOT YET ANALYZED"
  if (hasArticle && !hasCommunity) return "ARTICLE ONLY"
  if (!hasArticle && hasCommunity) return "COMMUNITY ONLY"
  if (articleScore! * communityScore! < 0) return "OPPOSING DIRECTIONS"
  if (divergence === null) return "SOURCES AGREE"
  if (divergence >= 1) return "SOURCES DIVERGE"
  return "SOURCES AGREE"
}

export type Direction = "POSITIVE" | "NEGATIVE" | "MIXED"

/** Direction word for a signed score, using the same ±0.2 band as the rail. */
export function direction(score: number | null): Direction | null {
  if (score === null) return null
  if (score > 0.2) return "POSITIVE"
  if (score < -0.2) return "NEGATIVE"
  return "MIXED"
}

/** Floor below which a generation is flagged as a thin sample. */
export const THIN_SAMPLE_FLOOR = 8

export function isThinSample(articleCount: number): boolean {
  return articleCount < THIN_SAMPLE_FLOOR
}

const HISTORY_STALE_MS = 18 * 30 * 24 * 60 * 60 * 1000

/**
 * History renders only with real, recent data: at least one addressed point and
 * a newest point within 18 months. Otherwise the section is hidden entirely
 * (not an empty box) so stale fixture noise never plots as a trend.
 */
export function historyVisible(points: V2HistoryPoint[]): boolean {
  if (!points.length) return false
  if (!points.some((point) => V2_DIMENSIONS.some((name) => point.dimensions[name].addressedCount > 0))) {
    return false
  }
  const newest = Math.max(...points.map((point) => Date.parse(point.date)))
  return Number.isFinite(newest) && newest >= Date.now() - HISTORY_STALE_MS
}
