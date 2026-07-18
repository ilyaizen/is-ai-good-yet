/**
 * Wireframe Dotted Globe — orthographic projection with graticule wireframe
 * and dotted landmasses. Auto-rotates with limb-darkening gradient fade so
 * wireframe lines and dots dissolve smoothly toward the sphere's edge.
 *
 * Adapted from shadway's wireframe-dotted-globe (21st.dev), reworked to
 * vanilla canvas + TS with a monochrome + blue-accent palette. No d3 dependency —
 * the orthographic projection is implemented directly.
 *
 * Land data is fetched once from Natural Earth 110m GeoJSON and cached.
 * Returns a dispose() handle that tears down observers + rAF.
 */

import { prefersReducedMotion } from "./runtime"
import { chordLength, pickArcPair, sampleArc, toUnitVec } from "./globe-arcs"
import type { ArcPair, ArcSample, Vec3 } from "./globe-arcs"

export interface GlobeOpts {
  /** Auto-rotation speed in degrees per second on the Y-axis / longitude (default 0.35). */
  rotationSpeed?: number
  /** Auto-rotation speed in degrees per second on the X-axis / latitude (default 0). */
  pitchSpeed?: number
  /** Graticule line spacing in degrees (default 15). */
  graticuleStep?: number
  /** Wireframe max alpha 0-1 (default 0.2). */
  wireAlpha?: number
  /** Land dot max alpha 0-1 (default 0.6). */
  dotAlpha?: number
  /** Land dot radius in CSS px (default 1.0). */
  dotRadius?: number
  /** Accent RGB (no alpha) for highlighted cities (default "163,230,53"). */
  color?: string
  /** RGB (no alpha) for land dots + graticule + sphere body (default "255,255,255"). */
  landColor?: string
  /** Major-city [lng, lat] coords that randomly light up in the accent color. */
  cities?: [number, number][]
  /** Highlighted city dot radius in CSS px (default 2.4). Slightly larger than
   *  land dots so a lit city reads, but still a flat dot — no glow shadow. */
  cityRadius?: number
  /** Land dot grid resolution in degrees (default 2). */
  landResolution?: number
  /** Globe radius as fraction of min(canvas dimension) (default 0.42). */
  radiusFraction?: number
  /** Extra padding around the drawn globe as a fraction of R (default 0.2).
   *  Softens the limb so wireframe/dots fade out before the clip edge. */
  limbPadding?: number
  /** If true, land dots shimmer independently like the dotted-glow field (default false). */
  flicker?: boolean
  /** Initial globe rotation in degrees [longitude, latitude] (default [0, 0]). */
  initialRotation?: [number, number]
  /** Nudge the projected globe center down by this many CSS px (default 0). */
  centerOffsetY?: number
  /** Draw great-circle arcs with traveling pulses between cities (default true). */
  arcs?: boolean
}

interface Dot {
  lng: number
  lat: number
  phase: number
  speed: number
}

interface GraticuleLine {
  points: [number, number][]
}

const DEG2RAD = Math.PI / 180
const TWO_PI = Math.PI * 2

// ── Math helpers ────────────────────────────────────────────────────────────

/** Hermite smoothstep — used for limb-darkening alpha curves. */
function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = Math.max(0, Math.min(1, (x - edge0) / (edge1 - edge0)))
  return t * t * (3 - 2 * t)
}

/**
 * Orthographic projection with rotation [lambda0, phi0] in degrees.
 * Returns [screenX, screenY, cosAngularDistance].
 * cosC > 0 → visible hemisphere; cosC ≈ 0 → at the limb (edge).
 */
function project(
  lng: number,
  lat: number,
  lambda0: number,
  phi0: number,
  R: number,
  cx: number,
  cy: number
): [number, number, number] {
  const dlng = (lng - lambda0) * DEG2RAD
  const phi1 = lat * DEG2RAD
  const p0 = phi0 * DEG2RAD

  const cosPhi0 = Math.cos(p0)
  const sinPhi0 = Math.sin(p0)
  const cosPhi1 = Math.cos(phi1)
  const sinPhi1 = Math.sin(phi1)
  const cosDlng = Math.cos(dlng)
  const sinDlng = Math.sin(dlng)

  const cosC = sinPhi0 * sinPhi1 + cosPhi0 * cosPhi1 * cosDlng
  const x = cx + R * cosPhi1 * sinDlng
  // Screen Y is inverted relative to math Y.
  const y = cy - R * (cosPhi0 * sinPhi1 - sinPhi0 * cosPhi1 * cosDlng)

  return [x, y, cosC]
}

// ── Arc lifecycle (route fade envelope + pulse position) ────────────────────

interface Arc {
  from: number
  to: number
  samples: ArcSample[]
  born: number
  fadeIn: number
  travel: number
  fadeOut: number
  life: number
}

/** Route alpha over an arc's life: fade in → hold → fade out. Returns 0 outside life. */
function routeAlpha(arc: Arc, tMs: number): number {
  const t = tMs - arc.born
  if (t < 0 || t > arc.life) return 0
  if (t < arc.fadeIn) return t / arc.fadeIn
  const fadeStart = arc.life - arc.fadeOut
  if (t > fadeStart) return (arc.life - t) / arc.fadeOut
  return 1
}

/** Pulse position along the route [0..1] during the travel phase, else -1. */
function pulseT(arc: Arc, tMs: number): number {
  const t = tMs - arc.born - arc.fadeIn
  if (t < 0 || t > arc.travel) return -1
  return t / arc.travel
}

// ── Graticule generation ────────────────────────────────────────────────────

function buildGraticule(step: number): { meridians: GraticuleLine[]; parallels: GraticuleLine[] } {
  const meridians: GraticuleLine[] = []
  const parallels: GraticuleLine[] = []

  // Meridians (constant longitude, spanning pole to pole)
  for (let lng = -180; lng <= 180; lng += step) {
    const points: [number, number][] = []
    for (let lat = -90; lat <= 90; lat += 5) {
      points.push([lng, lat])
    }
    meridians.push({ points })
  }

  // Parallels (constant latitude, spanning the full longitude range)
  for (let lat = -75; lat <= 75; lat += step) {
    const points: [number, number][] = []
    for (let lng = -180; lng <= 180; lng += 5) {
      points.push([lng, lat])
    }
    parallels.push({ points })
  }

  return { meridians, parallels }
}

// ── Point-in-polygon (ray casting) for land dot generation ───────────────────

function pointInRing(lng: number, lat: number, ring: number[][]): boolean {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const yi = ring[i][1]
    const yj = ring[j][1]
    if (yi > lat !== yj > lat) {
      const xi = ring[i][0]
      const xj = ring[j][0]
      const xInt = ((xj - xi) * (lat - yi)) / (yj - yi) + xi
      if (lng < xInt) inside = !inside
    }
  }
  return inside
}

/** Polygon = outer ring + holes. Inside if in outer ring and not in any hole. */
function pointInPolygon(lng: number, lat: number, rings: number[][][]): boolean {
  if (!pointInRing(lng, lat, rings[0])) return false
  for (let i = 1; i < rings.length; i++) {
    if (pointInRing(lng, lat, rings[i])) return false
  }
  return true
}

// ── Land dot generation from GeoJSON ─────────────────────────────────────────

interface GeoJSON {
  features: {
    geometry: {
      type: string
      coordinates: number[][][] | number[][][][]
    }
  }[]
}

function featureBBox(geometry: GeoJSON["features"][0]["geometry"]): [number, number, number, number] {
  let minLng = 180,
    minLat = 90,
    maxLng = -180,
    maxLat = -90
  const walk = (coords: number[][]) => {
    for (const pt of coords) {
      if (pt[0] < minLng) minLng = pt[0]
      if (pt[0] > maxLng) maxLng = pt[0]
      if (pt[1] < minLat) minLat = pt[1]
      if (pt[1] > maxLat) maxLat = pt[1]
    }
  }
  if (geometry.type === "Polygon") {
    for (const ring of geometry.coordinates as number[][][]) walk(ring)
  } else {
    for (const poly of geometry.coordinates as number[][][][]) for (const ring of poly) walk(ring)
  }
  return [minLng, minLat, maxLng, maxLat]
}

function generateLandDots(data: GeoJSON, resolution: number): Dot[] {
  const dots: Dot[] = []
  for (const feature of data.features) {
    const g = feature.geometry
    if (g.type !== "Polygon" && g.type !== "MultiPolygon") continue

    const [minLng, minLat, maxLng, maxLat] = featureBBox(g)
    const startLng = Math.ceil(minLng / resolution) * resolution
    const startLat = Math.ceil(minLat / resolution) * resolution

    if (g.type === "Polygon") {
      const coords = g.coordinates as number[][][]
      for (let lng = startLng; lng <= maxLng; lng += resolution) {
        for (let lat = startLat; lat <= maxLat; lat += resolution) {
          if (pointInPolygon(lng, lat, coords))
            dots.push({ lng, lat, phase: Math.random() * TWO_PI, speed: 0.4 + Math.random() * 0.9 })
        }
      }
    } else {
      const polys = g.coordinates as number[][][][]
      for (let lng = startLng; lng <= maxLng; lng += resolution) {
        for (let lat = startLat; lat <= maxLat; lat += resolution) {
          for (const poly of polys) {
            if (pointInPolygon(lng, lat, poly)) {
              dots.push({ lng, lat, phase: Math.random() * TWO_PI, speed: 0.4 + Math.random() * 0.9 })
              break
            }
          }
        }
      }
    }
  }
  return dots
}

// ── Land data cache (module-level singleton) ─────────────────────────────────

let dotsCache: Dot[] | null = null
let dotsCacheRes = 0
let dotsFetchInFlight: Promise<Dot[]> | null = null

async function loadLandDots(resolution: number): Promise<Dot[]> {
  // ponytail: single-entry cache keyed by resolution; the hero is the only
  // globe so one slot is enough, regenerated only if the requested step changes.
  if (dotsCache && dotsCacheRes === resolution) return dotsCache
  if (dotsFetchInFlight) return dotsFetchInFlight

  dotsFetchInFlight = (async () => {
    try {
      const res = await fetch("/data/ne-110m-land.json")
      if (!res.ok) return []
      const data = (await res.json()) as GeoJSON
      dotsCache = generateLandDots(data, resolution)
      dotsCacheRes = resolution
      return dotsCache
    } catch {
      return []
    } finally {
      dotsFetchInFlight = null
    }
  })()

  return dotsFetchInFlight
}

// ── Main renderer ─────────────────────────────────────────────────────────────

export function createWireframeGlobe(container: HTMLElement, opts: GlobeOpts = {}): () => void {
  const {
    rotationSpeed = 0.35,
    pitchSpeed = 0,
    graticuleStep = 15,
    wireAlpha = 0.2,
    dotAlpha = 0.6,
    dotRadius = 1.0,
    color = "163,230,53",
    landColor = "255,255,255",
    cities = [],
    cityRadius = 2.4,
    landResolution = 2,
    radiusFraction = 0.42,
    limbPadding = 0.2,
    flicker = false,
    initialRotation = [0, 0],
    centerOffsetY = 0,
    arcs: enableArcs = true,
  } = opts

  // Canvas setup
  const canvas = document.createElement("canvas")
  canvas.setAttribute("aria-hidden", "true")
  canvas.style.cssText = "position:absolute;inset:0;width:100%;height:100%;display:block;"
  container.appendChild(canvas)
  const ctx = canvas.getContext("2d")!

  // State
  const graticule = buildGraticule(graticuleStep)
  let dots: Dot[] = []
  let dotsLoaded = false

  // City highlight scheduler state. Lit cities pulse in the accent color
  // independently of the neutral land-dot field.
  interface LitCity {
    idx: number
    start: number
    dur: number
  }
  const litCities: LitCity[] = []
  let nextSpawn = 0
  const MAX_LIT = 260
  // Static subset shown when motion is reduced (no scheduler ticks).
  const staticCityIdxs = cities.length
    ? Array.from({ length: Math.min(5, cities.length) }, () => (Math.random() * cities.length) | 0)
    : []

  // ── Arc (route + pulse) setup ───────────────────────────────────────────
  // Unit vectors precomputed once so neighbor-weighted pair selection is a
  // tight dot-product loop, not per-spawn trig.
  const cityVecs: Vec3[] = enableArcs && cities.length >= 2 ? cities.map((c) => toUnitVec(c[0], c[1])) : []
  const MAX_ARCS = 24
  const ARC_FADE_IN = 220
  const ARC_FADE_OUT = 380
  const arcs: Arc[] = []
  let nextArc = 0

  function buildArc(pair: ArcPair): Arc {
    const samples = sampleArc(cities[pair.from], cities[pair.to])
    // Travel time scales with distance so a long hop takes longer to cross.
    const norm = Math.min(1, chordLength(cityVecs[pair.from], cityVecs[pair.to]) / 2)
    const travel = 900 + 1100 * norm
    return {
      from: pair.from,
      to: pair.to,
      samples,
      born: 0,
      fadeIn: ARC_FADE_IN,
      travel,
      fadeOut: ARC_FADE_OUT,
      life: ARC_FADE_IN + travel + ARC_FADE_OUT,
    }
  }

  // Static subset shown when motion is reduced (no scheduler ticks, frozen pulse).
  const staticArcs: Arc[] = cityVecs.length ? Array.from({ length: 4 }, () => buildArc(pickArcPair(cityVecs))) : []

  let dpr = Math.min(window.devicePixelRatio || 1, 2)
  let logicalW = 0
  let logicalH = 0
  const rotation: [number, number] = [initialRotation[0] % 360, initialRotation[1] % 360]

  // Alpha-bucket buffers for batched rendering (reused each frame)
  const NUM_BUCKETS = 16
  const segBuckets: [number, number, number, number][][] = Array.from({ length: NUM_BUCKETS }, () => [])
  const dotBuckets: [number, number][][] = Array.from({ length: NUM_BUCKETS }, () => [])

  function resize(): void {
    logicalW = container.clientWidth
    logicalH = container.clientHeight
    canvas.width = Math.max(1, logicalW * dpr)
    canvas.height = Math.max(1, logicalH * dpr)
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  }

  // ── Render ──────────────────────────────────────────────────────────────

  function draw(): void {
    const cx = logicalW / 2
    const cy = logicalH / 2 + centerOffsetY
    const R = Math.min(logicalW, logicalH) * radiusFraction
    if (R < 2) return // too small to bother
    const [lambda0, phi0] = rotation

    ctx.clearRect(0, 0, logicalW, logicalH)

    // --- Outer phosphor halo ---
    const halo = ctx.createRadialGradient(cx, cy, R * 0.85, cx, cy, R * 1.4)
    halo.addColorStop(0, `rgba(${landColor},0.05)`)
    halo.addColorStop(1, "rgba(0,0,0,0)")
    ctx.fillStyle = halo
    ctx.fillRect(0, 0, logicalW, logicalH)

    // --- Sphere body — subtle radial shading for depth ---
    const sphere = ctx.createRadialGradient(cx - R * 0.2, cy - R * 0.2, R * 0.05, cx, cy, R)
    sphere.addColorStop(0, `rgba(${landColor},0.035)`)
    sphere.addColorStop(0.65, `rgba(${landColor},0.012)`)
    sphere.addColorStop(1, "rgba(0,0,0,0)")
    ctx.fillStyle = sphere
    ctx.beginPath()
    ctx.arc(cx, cy, R, 0, TWO_PI)
    ctx.fill()

    // --- Sphere limb ring ---
    ctx.strokeStyle = `rgba(${landColor},0.1)`
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.arc(cx, cy, R, 0, TWO_PI)
    ctx.stroke()

    // --- Clear alpha buckets ---
    for (let i = 0; i < NUM_BUCKETS; i++) {
      segBuckets[i].length = 0
      dotBuckets[i].length = 0
    }

    // --- Graticule: bucket segments by alpha level ---
    const drawLineIntoBuckets = (line: GraticuleLine): void => {
      const pts = line.points
      for (let i = 0; i < pts.length - 1; i++) {
        const [x1, y1, c1] = project(pts[i][0], pts[i][1], lambda0, phi0, R, cx, cy)
        const [x2, y2, c2] = project(pts[i + 1][0], pts[i + 1][1], lambda0, phi0, R, cx, cy)
        const avgC = (c1 + c2) * 0.5
        if (avgC < -0.02) continue // both on far side
        // limbPadding widens the fade zone so dots/lines dissolve before the edge.
        const fadeEnd = 0.35 + limbPadding
        const a = smoothstep(0, fadeEnd, avgC)
        if (a < 0.02) continue
        const bucket = Math.min(NUM_BUCKETS - 1, (a * NUM_BUCKETS) | 0)
        segBuckets[bucket].push([x1, y1, x2, y2])
      }
    }

    for (const m of graticule.meridians) drawLineIntoBuckets(m)
    for (const p of graticule.parallels) drawLineIntoBuckets(p)

    // --- Draw batched graticule segments ---
    ctx.lineWidth = 0.6
    ctx.lineCap = "round"
    for (let b = 0; b < NUM_BUCKETS; b++) {
      const segs = segBuckets[b]
      if (!segs.length) continue
      const a = ((b + 1) / NUM_BUCKETS) * wireAlpha
      ctx.strokeStyle = `rgba(${landColor},${a.toFixed(3)})`
      ctx.beginPath()
      for (const [x1, y1, x2, y2] of segs) {
        ctx.moveTo(x1, y1)
        ctx.lineTo(x2, y2)
      }
      ctx.stroke()
    }

    // --- Land dots: bucket by alpha level ---
    // ponytail: radii scale with R so dots stay proportional to the globe at
    // any canvas size (the hero runs radiusFraction 0.85 → large R). Clamp
    // keeps tiny mobile globes from going sub-pixel.
    const rScale = Math.max(0.7, Math.min(2.2, R / 300))
    const landR = dotRadius * rScale
    if (dotsLoaded) {
      const t = performance.now() / 1000
      for (let i = 0; i < dots.length; i++) {
        const d = dots[i]
        const [x, y, c] = project(d.lng, d.lat, lambda0, phi0, R, cx, cy)
        if (c < 0) continue // far side
        const fadeEnd = 0.35 + limbPadding
        let a = smoothstep(0, fadeEnd, c)
        if (a < 0.03) continue
        // Flicker: independent triangle-wave alpha like the dotted-glow field.
        if (flicker) {
          const mod = (((t * d.speed + d.phase) % 2) + 2) % 2
          const lin = mod < 1 ? mod : 2 - mod
          a *= 0.35 + 0.65 * lin // 0.35..1.0 multiplier per dot
        }
        const bucket = Math.min(NUM_BUCKETS - 1, (a * NUM_BUCKETS) | 0)
        dotBuckets[bucket].push([x, y])
      }

      // --- Draw batched dots ---
      for (let b = 0; b < NUM_BUCKETS; b++) {
        const pts = dotBuckets[b]
        if (!pts.length) continue
        const a = ((b + 1) / NUM_BUCKETS) * dotAlpha
        ctx.fillStyle = `rgba(${landColor},${a.toFixed(3)})`
        ctx.beginPath()
        for (const [px, py] of pts) {
          ctx.moveTo(px + landR, py) // avoid connecting arcs
          ctx.arc(px, py, landR, 0, TWO_PI)
        }
        ctx.fill()
      }
    }

    // --- City highlights: land dots that briefly turn lime + pulse. ---
    // Rendered identically to land dots (same radius, no glow shadow) so a
    // lit city reads as "one of the gray dots just went lime," not a foreign
    // element. Only the color + an alpha envelope distinguish it.
    if (cities.length) {
      const tMs = performance.now()
      // Bright lime fill; globalAlpha carries the pulse so a lit city pops as
      // clearly lime (not a double-dimmed wash) while reusing land-dot radius.
      // City dots scale with R (same factor as land dots) and sit a touch
      // larger so a lit city reads as a distinct node, not a recolored dot.
      const cityR = cityRadius * rScale
      ctx.fillStyle = `rgba(${color},1)`
      const drawCity = (idx: number, env: number) => {
        const c0 = cities[idx]
        const [x, y, c] = project(c0[0], c0[1], lambda0, phi0, R, cx, cy)
        if (c < 0.05) return // far side / limb
        const fadeEnd = 0.35 + limbPadding
        const limb = smoothstep(0, fadeEnd, c)
        if (limb < 0.05) return
        ctx.globalAlpha = env * limb
        ctx.beginPath()
        ctx.moveTo(x + cityR, y)
        ctx.arc(x, y, cityR, 0, TWO_PI)
        ctx.fill()
      }

      if (prefersReducedMotion()) {
        ctx.globalAlpha = 0.85
        for (const idx of staticCityIdxs) {
          const c0 = cities[idx]
          const [x, y, c] = project(c0[0], c0[1], lambda0, phi0, R, cx, cy)
          if (c < 0.05) continue
          ctx.beginPath()
          ctx.moveTo(x + cityR, y)
          ctx.arc(x, y, cityR, 0, TWO_PI)
          ctx.fill()
        }
      } else {
        // ponytail: sin² envelope → quick rise, quick fall = a flash, not a
        // slow fade. Low floor (0.12) keeps the dot readable mid-pulse.
        for (const lc of litCities) {
          const u = (tMs - lc.start) / lc.dur
          if (u <= 0 || u >= 1) continue
          const s = Math.sin(u * Math.PI)
          drawCity(lc.idx, 0.12 + 0.88 * s * s)
        }
      }
      ctx.globalAlpha = 1
    }

    // --- Arcs: faint great-circle routes with a bright pulse + comet trail
    // zipping from one city to another. Per-segment limb fade tucks the route
    // behind the globe; the pulse is clipped when its position is far-side. ---
    if (cityVecs.length) {
      const reduced = prefersReducedMotion()
      const arcList = reduced ? staticArcs : arcs
      const tMsA = performance.now()
      const rScaleA = Math.max(0.7, Math.min(2.2, R / 300))
      const pulseR = 2.4 * rScaleA
      ctx.lineCap = "round"
      ctx.lineWidth = Math.max(1, 0.8 * rScaleA)
      ctx.fillStyle = `rgba(${color},1)`
      // Hoisted out of the per-arc loop: closes over the projection params once
      // per frame instead of allocating a closure per arc.
      const drawDot = (s: ArcSample[], frac: number, bright: number, rad: number): void => {
        if (frac < 0 || frac > 1) return
        const fi = frac * (s.length - 1)
        const i0 = Math.floor(fi)
        const f = fi - i0
        const sa = s[i0]
        const sb = s[Math.min(s.length - 1, i0 + 1)]
        // Unwrap longitude so a segment crossing the ±180° meridian
        // interpolates the short way (through 180°), not via 0°/Greenwich —
        // otherwise a dateline-crossing pulse teleports across the globe.
        // project()'s trig accepts any longitude, so values outside ±180 are fine.
        let dLng = sb.lng - sa.lng
        if (dLng > 180) dLng -= 360
        else if (dLng < -180) dLng += 360
        const lng = sa.lng + dLng * f
        const lat = sa.lat + (sb.lat - sa.lat) * f
        const elev = sa.elev + (sb.elev - sa.elev) * f
        const [x, y, c] = project(lng, lat, lambda0, phi0, R * (1 + elev), cx, cy)
        if (c < -0.02) return // far side
        ctx.globalAlpha = bright * smoothstep(0, 0.2, c)
        ctx.beginPath()
        ctx.moveTo(x + rad, y)
        ctx.arc(x, y, rad, 0, TWO_PI)
        ctx.fill()
      }
      for (const arc of arcList) {
        const a = reduced ? 0.45 : routeAlpha(arc, tMsA)
        if (a <= 0) continue
        const s = arc.samples
        // Route — per-segment stroke so each segment fades independently at the limb.
        for (let i = 0; i < s.length - 1; i++) {
          const p0 = s[i]
          const p1 = s[i + 1]
          const [x1, y1, c1] = project(p0.lng, p0.lat, lambda0, phi0, R * (1 + p0.elev), cx, cy)
          const [x2, y2, c2] = project(p1.lng, p1.lat, lambda0, phi0, R * (1 + p1.elev), cx, cy)
          // ponytail: limb fade approximates sphere occlusion for the lifted
          // arc — precise back-of-sphere clipping isn't worth the math here;
          // the eye reads this as the route tucking behind the globe.
          const limb = smoothstep(-0.06, 0.12, (c1 + c2) * 0.5)
          if (limb <= 0.02) continue
          ctx.strokeStyle = `rgba(${color},${(a * 0.4 * limb).toFixed(3)})`
          ctx.beginPath()
          ctx.moveTo(x1, y1)
          ctx.lineTo(x2, y2)
          ctx.stroke()
        }
        // Pulse + comet trail along the route.
        const pt = reduced ? 0.5 : pulseT(arc, tMsA)
        if (pt < 0) continue
        const env = 0.6 + 0.4 * Math.sin(Math.PI * pt)
        // Single crisp head + one tight dim streak directly behind for motion.
        // No leading halo (a big disc ahead of the head read as a second pulse)
        // and no spread trail (ghosted smear).
        drawDot(s, pt, env, pulseR)
        drawDot(s, Math.max(0, pt - 0.04), 0.3 * env, pulseR * 0.6)
        ctx.globalAlpha = 1
      }
    }
  }

  // ── Animation loop ──────────────────────────────────────────────────────
  // ponytail: runs at full rAF (not the grain heartbeat). Rotation is dt-based
  // so angular speed is unchanged, but the city pulse + land flicker sample at
  // display refresh → smooth flashes instead of 15fps strobing. The grain +
  // glow fields keep their own throttled loops; only the globe decoupled.

  let raf = 0
  let running = false
  let lastDraw = 0

  function loop(ts: number): void {
    if (!running) return
    raf = requestAnimationFrame(loop)
    if (lastDraw) {
      const dt = Math.min(0.1, (ts - lastDraw) / 1000) // clamp dt to avoid jumps
      rotation[0] = (rotation[0] + rotationSpeed * dt) % 360
      // Pitch accumulates on the X-axis; wrap to keep the value bounded.
      rotation[1] = (rotation[1] + pitchSpeed * dt) % 360
      // City scheduler: expire stale, spawn new flashes. Short duration + fast
      // spawn cadence = a lively twinkle field.
      for (let i = litCities.length - 1; i >= 0; i--) {
        if (ts - litCities[i].start > litCities[i].dur) litCities.splice(i, 1)
      }
      if (cities.length && ts >= nextSpawn && litCities.length < MAX_LIT) {
        litCities.push({
          idx: (Math.random() * cities.length) | 0,
          start: ts,
          dur: 600 + Math.random() * 700, // ~0.6–1.3s flash
        })
        nextSpawn = ts + 30 + Math.random() * 90 // dense, overlapping flashes
      }
      // Arc scheduler: expire finished arcs, spawn new ones (mostly near,
      // sometimes far). Capped so the globe never gets busy.
      if (cityVecs.length) {
        for (let i = arcs.length - 1; i >= 0; i--) {
          if (ts - arcs[i].born > arcs[i].life) arcs.splice(i, 1)
        }
        if (ts >= nextArc && arcs.length < MAX_ARCS) {
          const arc = buildArc(pickArcPair(cityVecs))
          arc.born = ts
          arcs.push(arc)
          nextArc = ts + 70 + Math.random() * 120
        }
      }
      draw()
    }
    lastDraw = ts
  }

  function start(): void {
    if (running || document.hidden || prefersReducedMotion()) return
    running = true
    lastDraw = 0
    raf = requestAnimationFrame(loop)
  }

  function stop(): void {
    running = false
    cancelAnimationFrame(raf)
  }

  // ── Observers ────────────────────────────────────────────────────────────

  const visObs = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (e.isIntersecting) start()
        else stop()
      }
    },
    { threshold: 0.1 }
  )
  visObs.observe(container)

  const resizeObs = new ResizeObserver(() => {
    resize()
    if (prefersReducedMotion()) draw()
    else if (!running) start()
  })
  resizeObs.observe(container)

  const onDocumentVisibility = (): void => {
    if (document.hidden) stop()
    else start()
  }
  document.addEventListener("visibilitychange", onDocumentVisibility)

  // ── Load land data ───────────────────────────────────────────────────────

  let disposed = false
  // void: loadLandDots never rejects (fetch/parse errors are caught → []), so
  // this is intentionally unhandled rather than silently swallowing an error.
  void loadLandDots(landResolution).then((d) => {
    if (disposed) return
    dots = d
    dotsLoaded = true
    if (prefersReducedMotion()) draw()
    // If animation is running, dots appear on the next frame automatically.
  })

  // ── Initial render ───────────────────────────────────────────────────────

  resize()

  if (prefersReducedMotion()) {
    draw() // single static frame
  } else {
    start()
  }

  // ── Dispose handle ───────────────────────────────────────────────────────

  return () => {
    disposed = true
    stop()
    visObs.disconnect()
    resizeObs.disconnect()
    document.removeEventListener("visibilitychange", onDocumentVisibility)
    canvas.remove()
  }
}
