/**
 * Great-circle arc geometry for the hero globe.
 *
 * Pure functions only — no canvas/DOM/state. Sampling and neighbor-weighted
 * pair selection live here so they stay decoupled from the orthographic
 * renderer (SRP) and reusable/testable in isolation. The renderer reuses its
 * own `project()` for the actual screen projection (DRY).
 *
 * A "route" is a great-circle path between two cities, sampled into points
 * that are lifted off the sphere surface by a sin parabola so the path reads
 * as an arcing flight path rather than a line glued to the globe.
 */

const DEG2RAD = Math.PI / 180
const RAD2DEG = 180 / Math.PI

export type Vec3 = [number, number, number]
export type LngLat = [number, number]

function clamp(x: number, lo: number, hi: number): number {
  return x < lo ? lo : x > hi ? hi : x
}

/** [lng, lat] in degrees → unit vector on the sphere. */
export function toUnitVec(lng: number, lat: number): Vec3 {
  const p = lat * DEG2RAD
  const l = lng * DEG2RAD
  const cp = Math.cos(p)
  return [cp * Math.cos(l), cp * Math.sin(l), Math.sin(p)]
}

/** Unit vector → [lng, lat] in degrees (inverse of toUnitVec). */
export function unitVecToLngLat(v: Vec3): LngLat {
  return [Math.atan2(v[1], v[0]) * RAD2DEG, Math.asin(clamp(v[2], -1, 1)) * RAD2DEG]
}

/** Chord length (0..2) between two unit vectors — monotonic with great-circle distance, cheap. */
export function chordLength(a: Vec3, b: Vec3): number {
  const dx = b[0] - a[0]
  const dy = b[1] - a[1]
  const dz = b[2] - a[2]
  return Math.sqrt(dx * dx + dy * dy + dz * dz)
}

/**
 * Spherical linear interpolation between two unit vectors — a true great-circle
 * path. Falls back to lerp+normalize when the endpoints are nearly identical
 * (where slerp's denominator collapses).
 */
export function slerp(a: Vec3, b: Vec3, t: number): Vec3 {
  const dot = clamp(a[0] * b[0] + a[1] * b[1] + a[2] * b[2], -1, 1)
  if (dot > 0.9995) {
    const x = a[0] + t * (b[0] - a[0])
    const y = a[1] + t * (b[1] - a[1])
    const z = a[2] + t * (b[2] - a[2])
    const m = Math.hypot(x, y, z) || 1
    return [x / m, y / m, z / m]
  }
  const omega = Math.acos(dot)
  const so = Math.sin(omega)
  const c0 = Math.sin((1 - t) * omega) / so
  const c1 = Math.sin(t * omega) / so
  return [c0 * a[0] + c1 * b[0], c0 * a[1] + c1 * b[1], c0 * a[2] + c1 * b[2]]
}

export interface ArcSample {
  lng: number
  lat: number
  /** Elevation as a fraction of globe radius added on top of R (0 at ends, peaks mid). */
  elev: number
}

export interface SampleArcOpts {
  /** Points along the path (default 28). */
  steps?: number
  /** Base lift fraction of R for the shortest arcs (default 0.08). */
  minLift?: number
  /** Extra lift fraction of R added for the longest arcs (default 0.22). */
  liftRange?: number
}

/**
 * Sample a great-circle arc between two cities, lifting each point off the
 * surface by a sin parabola. Lift scales with chord distance so a long hop
 * bulges higher than a short neighbor hop.
 */
export function sampleArc(from: LngLat, to: LngLat, opts: SampleArcOpts = {}): ArcSample[] {
  const { steps = 28, minLift = 0.08, liftRange = 0.22 } = opts
  const a = toUnitVec(from[0], from[1])
  const b = toUnitVec(to[0], to[1])
  const lift = minLift + liftRange * Math.min(1, chordLength(a, b) / 2)
  const out: ArcSample[] = new Array(steps)
  for (let i = 0; i < steps; i++) {
    const t = i / (steps - 1)
    const [lng, lat] = unitVecToLngLat(slerp(a, b, t))
    out[i] = { lng, lat, elev: lift * Math.sin(Math.PI * t) }
  }
  return out
}

export interface ArcPair {
  from: number
  to: number
}

/**
 * Pick a city pair for a new arc: mostly near neighbors, occasionally
 * long-range. `farChance` is the probability of a long-range hop; otherwise
 * the target is drawn weighted toward the source's nearest cities
 * (weight ∝ 1 / chord²). A long-range hop is uniform over cities within
 * `farMaxChord` of the source so it stays clearly long-range rather than
 * antipodal — a ~180° arc flattens into a line through the globe's center and
 * reads as a glitch.
 *
 * Expects precomputed unit vectors (one per city) so neighbor weighting and
 * the far-range filter are tight loops of dot products rather than per-spawn
 * trig.
 */
export function pickArcPair(cityVecs: Vec3[], farChance = 0.15, farMaxChord = 1.2): ArcPair {
  const n = cityVecs.length
  const from = (Math.random() * n) | 0
  const fa = cityVecs[from]
  if (Math.random() < farChance || n < 2) {
    // Reservoir-of-1 sampling → uniform over the in-range set in one O(n) pass
    // (no array alloc). Only cities within farMaxChord are eligible, so the
    // returned hop is guaranteed long-range-but-not-antipodal.
    let cnt = 0
    let to = -1
    for (let i = 0; i < n; i++) {
      if (i === from) continue
      if (chordLength(cityVecs[i], fa) <= farMaxChord && Math.random() * ++cnt < 1) to = i
    }
    if (to < 0) to = (from + 1) % n // degenerate: no city in range
    return { from, to }
  }
  const weights = new Float64Array(n)
  let total = 0
  for (let i = 0; i < n; i++) {
    if (i === from) continue
    const d = chordLength(cityVecs[i], fa)
    const w = 1 / (d * d + 0.02)
    weights[i] = w
    total += w
  }
  let r = Math.random() * total
  let to = from
  for (let i = 0; i < n; i++) {
    r -= weights[i]
    if (r <= 0) {
      to = i
      break
    }
  }
  if (to === from) to = (from + 1) % n
  return { from, to }
}
