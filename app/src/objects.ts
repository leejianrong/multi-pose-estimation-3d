import * as THREE from "three";
import type { Pt } from "./proximity";

export interface ObjectSpec {
  id: string;
  seed: number;
  position: [number, number];
  yaw_deg: number;
  size: [number, number, number]; // length, width, height in metres
  waves: number;
  amplitude: number; // fraction of the radius
  color: string;
}

export interface SculptureObject {
  spec: ObjectSpec;
  mesh: THREE.Mesh;
  footprint: Pt[]; // convex hull on the floor, room frame
  hash: string;
}

/** mulberry32: small seeded PRNG, so a seed always gives the same sculpture. */
export function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Andrew's monotone chain convex hull. */
export function convexHull(points: Pt[]): Pt[] {
  const p = [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  if (p.length < 3) return p;
  const cross = (o: Pt, a: Pt, b: Pt) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const build = (pts: Pt[]) => {
    const h: Pt[] = [];
    for (const q of pts) {
      while (h.length >= 2 && cross(h[h.length - 2], h[h.length - 1], q) <= 0) h.pop();
      h.push(q);
    }
    h.pop();
    return h;
  };
  return [...build(p), ...build([...p].reverse())];
}

/** A sofa-sized, wavy, resin-looking blob: a superellipsoid with sine ripples and seeded drift. */
export function buildSculpture(spec: ObjectSpec): SculptureObject {
  const rand = rng(spec.seed);
  const phase = [rand() * 6.28, rand() * 6.28, rand() * 6.28];
  const drift = [rand() * 0.4 + 0.6, rand() * 0.4 + 0.6];
  const geo = new THREE.SphereGeometry(1, 96, 64);
  const pos = geo.getAttribute("position") as THREE.BufferAttribute;
  const [L, W, H] = spec.size;
  const v = new THREE.Vector3();
  for (let i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i); // unit sphere, Y-up in three's sphere convention
    const theta = Math.atan2(v.z, v.x); // around the long axis
    const lat = Math.asin(THREE.MathUtils.clamp(v.y, -1, 1));
    const ripple =
      1 +
      spec.amplitude *
        (Math.sin(spec.waves * theta + phase[0]) * Math.cos(lat * drift[0] * 2) +
          0.6 * Math.sin((spec.waves + 2) * lat + phase[1]) * Math.cos(theta * drift[1]));
    // squarish cross-section (superellipsoid exponent) so it reads as a couch-like mass
    const e = 0.55;
    const sx = Math.sign(v.x) * Math.abs(v.x) ** e;
    const sy = Math.sign(v.y) * Math.abs(v.y) ** e;
    const sz = Math.sign(v.z) * Math.abs(v.z) ** e;
    pos.setXYZ(i, (sx * ripple * L) / 2, (sz * ripple * W) / 2, (sy * ripple * H) / 2); // x long, y wide, z up
  }
  geo.computeBoundingBox();
  geo.translate(0, 0, -geo.boundingBox!.min.z); // sit on the floor
  geo.computeVertexNormals();
  const mat = new THREE.MeshPhysicalMaterial({
    color: spec.color,
    roughness: 0.18,
    metalness: 0.0,
    clearcoat: 1,
    clearcoatRoughness: 0.08, // glossy resin over fibreglass
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.set(spec.position[0], spec.position[1], 0);
  mesh.rotation.z = THREE.MathUtils.degToRad(spec.yaw_deg);
  mesh.updateMatrixWorld(true);

  const world = new THREE.Vector3();
  const xy: Pt[] = [];
  let h = 0;
  for (let i = 0; i < pos.count; i++) {
    world.fromBufferAttribute(geo.getAttribute("position") as THREE.BufferAttribute, i).applyMatrix4(mesh.matrixWorld);
    xy.push([world.x, world.y]);
    h = (h * 31 + Math.round(world.x * 1000) * 7 + Math.round(world.y * 1000) * 13 + Math.round(world.z * 1000)) | 0;
  }
  return { spec, mesh, footprint: convexHull(xy), hash: (h >>> 0).toString(16) };
}
