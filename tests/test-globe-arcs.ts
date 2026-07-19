/**
 * Invariant checks for the hero globe's pure arc geometry (slerp, sampling,
 * neighbor-weighted pair selection). Run via `vp run test:globe-arcs`.
 *
 * The globe-arcs module has no canvas/DOM deps, so it imports cleanly into a
 * plain tsx script — this catches slerp / weighting regressions without a
 * browser.
 */
import assert from "node:assert/strict"
import {
  chordLength,
  pickArcPair,
  sampleArc,
  slerp,
  toUnitVec,
  unitVecToLngLat,
} from "../src/lib/components/v2/effects/globe-arcs"

const NY = toUnitVec(-74, 40.7)
const TOKYO = toUnitVec(139.7, 35.7)

// slerp endpoints + unit length
assert.ok(chordLength(slerp(NY, TOKYO, 0), NY) < 1e-9, "slerp(0) returns the start vector")
assert.ok(chordLength(slerp(NY, TOKYO, 1), TOKYO) < 1e-9, "slerp(1) returns the end vector")
const mid = slerp(NY, TOKYO, 0.5)
assert.ok(Math.abs(Math.hypot(mid[0], mid[1], mid[2]) - 1) < 1e-9, "slerp output stays on the unit sphere")

// vec <-> lng/lat round trip
const [lng, lat] = unitVecToLngLat(NY)
assert.ok(Math.abs(lng - -74) < 1e-6 && Math.abs(lat - 40.7) < 1e-6, "unitVecToLngLat round trips")

// chord of identical points is zero
assert.equal(chordLength(NY, NY), 0)

// sampleArc: endpoints on the surface, midpoint lifted, long arcs lift higher
const shortArc = sampleArc([-74, 40.7], [-80, 41])
const longArc = sampleArc([-74, 40.7], [139.7, 35.7])
const last = (a: { elev: number }[]): number => a[a.length - 1].elev
assert.ok(shortArc[0].elev < 1e-9 && last(shortArc) < 1e-9, "short arc endpoints sit on the surface")
assert.ok(longArc[0].elev < 1e-9 && last(longArc) < 1e-9, "long arc endpoints sit on the surface")
const shortMid = shortArc[Math.floor(shortArc.length / 2)].elev
const longMid = longArc[Math.floor(longArc.length / 2)].elev
assert.ok(shortMid > 0 && longMid > 0, "arc midpoint is lifted off the surface")
assert.ok(longMid > shortMid, "a longer hop lifts higher than a short neighbor hop")

// pickArcPair validity
const vecs = Array.from({ length: 30 }, (_, i) => toUnitVec(i * 12, 0)) // 30 cities along the equator
for (let i = 0; i < 50; i++) {
  const { from, to } = pickArcPair(vecs, 0)
  assert.ok(from >= 0 && from < vecs.length && to >= 0 && to < vecs.length, "indices stay in range")
  assert.notEqual(from, to, "an arc never loops a city to itself")
}

// Near-weighting: with farChance 0, the source's nearest half dominates its far half.
let nearHits = 0
let farHits = 0
const SRC = 15
for (let i = 0; i < 6000; i++) {
  const { from, to } = pickArcPair(vecs, 0)
  if (from !== SRC) continue
  if (to >= 8 && to <= 22) nearHits++
  else farHits++
}
assert.ok(nearHits > farHits * 5, `neighbor weighting holds (near=${nearHits} far=${farHits})`)

// farChance 1 spreads targets broadly (uniform), proving the far branch engages
const targets = new Set<number>()
for (let i = 0; i < 200; i++) targets.add(pickArcPair(vecs, 1).to)
assert.ok(targets.size > 20, "farChance=1 produces widely spread targets")

// farMaxChord caps long-range hops so they stay long-range, never antipodal.
for (let i = 0; i < 300; i++) {
  const { from, to } = pickArcPair(vecs, 1, 1.2)
  const d = chordLength(vecs[from], vecs[to])
  assert.ok(d <= 1.2 + 1e-9, `far hop within cap (d=${d.toFixed(3)})`)
}

console.log("globe-arcs: all checks passed")
