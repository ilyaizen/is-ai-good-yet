import * as THREE from "three";
import { mergeVertices } from "three/examples/jsm/utils/BufferGeometryUtils.js";

// Inside-out icosphere "membrane". Camera sits at origin and looks outward;
// shaping happens radially along each vertex's base direction so the mesh
// keeps spherical silhouette while organic noise/pulses break uniformity.
// detail=2 → V=642, enough vertex density for readable noise.
// Tangential jitter spreads vertex layout so triangles aren't uniformly
// equilateral — without it the icosphere reads as a smooth shaded ball.
export const SPHERE_RADIUS = 36;
export const SPHERE_DETAIL = 2;
export const SPHERE_JITTER = 0.4;
export const DISPLACEMENT_AMP_MAX = 7;
export const RELAXATION_PASSES = 1;

export type MembraneNeighbor = {
  index: number;
  weight: number;
};

export type MembraneMeshData = {
  membraneGeo: THREE.BufferGeometry;
  baseDirections: Float32Array;
  edgePairs: Array<[number, number]>;
  vertexNeighbors: MembraneNeighbor[][];
  vertexInfluence: Float32Array;
};

export const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));

export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

function hashNoise2d(x: number, y: number) {
  let h = Math.imul(x, 374761393) ^ Math.imul(y, 668265263);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

export function smoothNoise2d(x: number, y: number) {
  const ix = Math.floor(x);
  const iy = Math.floor(y);
  const fx = x - ix;
  const fy = y - iy;
  const sx = fx * fx * (3 - 2 * fx);
  const sy = fy * fy * (3 - 2 * fy);
  const a = hashNoise2d(ix, iy);
  const b = hashNoise2d(ix + 1, iy);
  const c = hashNoise2d(ix, iy + 1);
  const d = hashNoise2d(ix + 1, iy + 1);

  return lerp(lerp(a, b, sx), lerp(c, d, sx), sy);
}

type BevelOptions = {
  enabled: boolean;
  strength: number;
  inset: number;
};

type CreateMembraneOptions = {
  radius?: number;
  detail?: number;
  jitter?: number;
  bevel?: BevelOptions;
};

function computeMembraneTopology(geo: THREE.BufferGeometry, radius: number) {
  const posAttr = geo.attributes.position;
  const vertCount = posAttr.count;
  const positions = posAttr.array as Float32Array;
  const idx = geo.index!;

  const baseDirections = new Float32Array(vertCount * 3);
  for (let i = 0; i < vertCount; i++) {
    const x = positions[i * 3];
    const y = positions[i * 3 + 1];
    const z = positions[i * 3 + 2];
    const len = Math.hypot(x, y, z) || 1;
    baseDirections[i * 3] = x / len;
    baseDirections[i * 3 + 1] = y / len;
    baseDirections[i * 3 + 2] = z / len;
  }

  const edgePairs: Array<[number, number]> = [];
  const vertexNeighbors: MembraneNeighbor[][] = Array.from({ length: vertCount }, () => []);
  const vertexEdgeTotals = new Float32Array(vertCount);
  const vertexEdgeCounts = new Uint16Array(vertCount);
  let totalEdgeLength = 0;
  const seen = new Set<string>();

  const addEdge = (p: number, q: number) => {
    const k = p < q ? `${p}_${q}` : `${q}_${p}`;
    if (seen.has(k)) return;
    seen.add(k);
    const ax = positions[p * 3];
    const ay = positions[p * 3 + 1];
    const az = positions[p * 3 + 2];
    const bx = positions[q * 3];
    const by = positions[q * 3 + 1];
    const bz = positions[q * 3 + 2];
    const edgeLength = Math.hypot(bx - ax, by - ay, bz - az);
    const neighborWeight = 1 / Math.sqrt(Math.max(edgeLength, 0.001));

    edgePairs.push(p < q ? [p, q] : [q, p]);
    vertexNeighbors[p].push({ index: q, weight: neighborWeight });
    vertexNeighbors[q].push({ index: p, weight: neighborWeight });
    vertexEdgeTotals[p] += edgeLength;
    vertexEdgeTotals[q] += edgeLength;
    vertexEdgeCounts[p]++;
    vertexEdgeCounts[q]++;
    totalEdgeLength += edgeLength;
  };

  for (let i = 0; i < idx.count; i += 3) {
    const a = idx.getX(i);
    const b = idx.getX(i + 1);
    const c = idx.getX(i + 2);
    addEdge(a, b);
    addEdge(b, c);
    addEdge(c, a);
  }

  const meanEdgeLength = edgePairs.length > 0 ? totalEdgeLength / edgePairs.length : 1;
  const vertexInfluence = new Float32Array(vertCount);
  for (let i = 0; i < vertCount; i++) {
    const averageEdgeLength =
      vertexEdgeCounts[i] > 0 ? vertexEdgeTotals[i] / vertexEdgeCounts[i] : meanEdgeLength;
    vertexInfluence[i] = clamp(averageEdgeLength / meanEdgeLength, 0.72, 1.65);
  }
  void radius;
  return { baseDirections, edgePairs, vertexNeighbors, vertexInfluence };
}

function applyBevel(geo: THREE.BufferGeometry, radius: number, bevel: BevelOptions): THREE.BufferGeometry {
  const posAttr = geo.attributes.position;
  const positions = posAttr.array as Float32Array;
  const idx = geo.index!;
  const inset = clamp(bevel.inset, 0, 0.49);
  const radialOffset = bevel.strength * radius * 0.01;

  const out: number[] = [];

  const pushTri = (
    ax: number, ay: number, az: number,
    bx: number, by: number, bz: number,
    cx: number, cy: number, cz: number
  ) => {
    out.push(ax, ay, az, bx, by, bz, cx, cy, cz);
  };

  for (let i = 0; i < idx.count; i += 3) {
    const ia = idx.getX(i);
    const ib = idx.getX(i + 1);
    const ic = idx.getX(i + 2);

    const ax = positions[ia * 3], ay = positions[ia * 3 + 1], az = positions[ia * 3 + 2];
    const bx = positions[ib * 3], by = positions[ib * 3 + 1], bz = positions[ib * 3 + 2];
    const cx = positions[ic * 3], cy = positions[ic * 3 + 1], cz = positions[ic * 3 + 2];

    const gx = (ax + bx + cx) / 3;
    const gy = (ay + by + cy) / 3;
    const gz = (az + bz + cz) / 3;

    // Inset corners toward centroid
    const apx = lerp(ax, gx, inset), apy = lerp(ay, gy, inset), apz = lerp(az, gz, inset);
    const bpx = lerp(bx, gx, inset), bpy = lerp(by, gy, inset), bpz = lerp(bz, gz, inset);
    const cpx = lerp(cx, gx, inset), cpy = lerp(cy, gy, inset), cpz = lerp(cz, gz, inset);

    // Inset corners nudged radially inward to form bevel facet
    const pull = (px: number, py: number, pz: number): [number, number, number] => {
      const len = Math.hypot(px, py, pz) || 1;
      const k = (len - radialOffset) / len;
      return [px * k, py * k, pz * k];
    };
    const [iax, iay, iaz] = pull(apx, apy, apz);
    const [ibx, iby, ibz] = pull(bpx, bpy, bpz);
    const [icx, icy, icz] = pull(cpx, cpy, cpz);

    pushTri(iax, iay, iaz, ibx, iby, ibz, icx, icy, icz);
    pushTri(ax, ay, az, bx, by, bz, bpx, bpy, bpz);
    pushTri(ax, ay, az, bpx, bpy, bpz, apx, apy, apz);
    pushTri(bx, by, bz, cx, cy, cz, cpx, cpy, cpz);
    pushTri(bx, by, bz, cpx, cpy, cpz, bpx, bpy, bpz);
    pushTri(cx, cy, cz, ax, ay, az, apx, apy, apz);
    pushTri(cx, cy, cz, apx, apy, apz, cpx, cpy, cpz);
    pushTri(apx, apy, apz, bpx, bpy, bpz, iax, iay, iaz);
    pushTri(bpx, bpy, bpz, ibx, iby, ibz, iax, iay, iaz);
    pushTri(bpx, bpy, bpz, cpx, cpy, cpz, ibx, iby, ibz);
    pushTri(cpx, cpy, cpz, icx, icy, icz, ibx, iby, ibz);
    pushTri(cpx, cpy, cpz, apx, apy, apz, icx, icy, icz);
    pushTri(apx, apy, apz, iax, iay, iaz, icx, icy, icz);
  }

  const beveled = new THREE.BufferGeometry();
  beveled.setAttribute("position", new THREE.Float32BufferAttribute(out, 3));
  const merged = mergeVertices(beveled, 1e-4);
  beveled.dispose();
  merged.computeVertexNormals();
  merged.computeBoundingSphere();
  return merged;
}

export function createMembraneMeshData(opts: CreateMembraneOptions = {}): MembraneMeshData {
  const radius = opts.radius ?? SPHERE_RADIUS;
  const detail = opts.detail ?? SPHERE_DETAIL;
  const jitterRatio = opts.jitter ?? SPHERE_JITTER;
  const bevel = opts.bevel;

  const raw = new THREE.IcosahedronGeometry(radius, detail);
  const membraneGeo = mergeVertices(raw, 1e-4);
  raw.dispose();

  const posAttr = membraneGeo.attributes.position;
  const vertCount = posAttr.count;
  const positions = posAttr.array as Float32Array;
  const idx = membraneGeo.index!;

  let preSum = 0;
  let preCount = 0;
  const preSeen = new Set<string>();
  const tallyEdge = (p: number, q: number) => {
    const k = p < q ? `${p}_${q}` : `${q}_${p}`;
    if (preSeen.has(k)) return;
    preSeen.add(k);
    const dx = positions[p * 3] - positions[q * 3];
    const dy = positions[p * 3 + 1] - positions[q * 3 + 1];
    const dz = positions[p * 3 + 2] - positions[q * 3 + 2];
    preSum += Math.hypot(dx, dy, dz);
    preCount++;
  };
  for (let i = 0; i < idx.count; i += 3) {
    const a = idx.getX(i);
    const b = idx.getX(i + 1);
    const c = idx.getX(i + 2);
    tallyEdge(a, b);
    tallyEdge(b, c);
    tallyEdge(c, a);
  }
  const baseEdgeLen = preCount > 0 ? preSum / preCount : 1;
  const jitterAmount = baseEdgeLen * jitterRatio;

  const tmpRef = new THREE.Vector3();
  const tmpN = new THREE.Vector3();
  const tmpT1 = new THREE.Vector3();
  const tmpT2 = new THREE.Vector3();

  for (let i = 0; i < vertCount; i++) {
    const x = positions[i * 3];
    const y = positions[i * 3 + 1];
    const z = positions[i * 3 + 2];
    const len = Math.hypot(x, y, z) || 1;
    const nx = x / len;
    const ny = y / len;
    const nz = z / len;

    tmpN.set(nx, ny, nz);
    if (Math.abs(ny) < 0.9) tmpRef.set(0, 1, 0);
    else tmpRef.set(1, 0, 0);
    tmpT1.crossVectors(tmpN, tmpRef).normalize();
    tmpT2.crossVectors(tmpN, tmpT1).normalize();

    const j1 = (smoothNoise2d(nx * 5.7 + 11.3, ny * 5.7 + nz * 3.1 - 7.1) - 0.5) * 2;
    const j2 = (smoothNoise2d(nz * 5.7 + 22.8, nx * 5.7 + ny * 3.1 + 5.6) - 0.5) * 2;

    const jx = tmpT1.x * j1 + tmpT2.x * j2;
    const jy = tmpT1.y * j1 + tmpT2.y * j2;
    const jz = tmpT1.z * j1 + tmpT2.z * j2;

    const px = x + jx * jitterAmount;
    const py = y + jy * jitterAmount;
    const pz = z + jz * jitterAmount;
    const pl = Math.hypot(px, py, pz) || 1;
    const scale = radius / pl;

    positions[i * 3] = px * scale;
    positions[i * 3 + 1] = py * scale;
    positions[i * 3 + 2] = pz * scale;
  }

  posAttr.needsUpdate = true;
  membraneGeo.computeVertexNormals();
  membraneGeo.computeBoundingSphere();

  let finalGeo = membraneGeo;
  if (bevel?.enabled) {
    finalGeo = applyBevel(membraneGeo, radius, bevel);
    membraneGeo.dispose();
  }

  const topology = computeMembraneTopology(finalGeo, radius);
  return { membraneGeo: finalGeo, ...topology };
}