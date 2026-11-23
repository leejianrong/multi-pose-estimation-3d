import { expect, test } from "vitest";
import { buildSculpture, convexHull, rng, type ObjectSpec } from "./objects";
import { distanceToPolygon } from "./proximity";

const spec: ObjectSpec = {
  id: "t", seed: 11, position: [1, 2], yaw_deg: 30, size: [1.8, 0.9, 0.8], waves: 3, amplitude: 0.16, color: "#fff",
};

test("same seed gives the same sculpture, a different seed a different one", () => {
  expect(buildSculpture(spec).hash).toBe(buildSculpture(spec).hash);
  expect(buildSculpture({ ...spec, seed: 12 }).hash).not.toBe(buildSculpture(spec).hash);
});

test("sculpture is sofa-sized and rests on the floor", () => {
  const o = buildSculpture({ ...spec, position: [0, 0], yaw_deg: 0 });
  o.mesh.geometry.computeBoundingBox();
  const b = o.mesh.geometry.boundingBox!;
  expect(b.min.z).toBeCloseTo(0, 6);
  const [dx, dy, dz] = [b.max.x - b.min.x, b.max.y - b.min.y, b.max.z - b.min.z];
  expect(dx).toBeGreaterThan(1.4);
  expect(dx).toBeLessThan(2.6);
  expect(dy).toBeGreaterThan(0.6);
  expect(dy).toBeLessThan(1.4);
  expect(dz).toBeGreaterThan(0.5);
  expect(dz).toBeLessThan(1.2);
});

test("footprint encloses the mesh's own floor projection", () => {
  const o = buildSculpture(spec);
  expect(distanceToPolygon([spec.position[0], spec.position[1]], o.footprint)).toBe(0);
  expect(distanceToPolygon([spec.position[0] + 5, spec.position[1]], o.footprint)).toBeGreaterThan(3);
});

test("convex hull of a square with an interior point", () => {
  const h = convexHull([[0, 0], [1, 0], [1, 1], [0, 1], [0.5, 0.5]]);
  expect(h).toHaveLength(4);
});

test("prng is deterministic and in [0,1)", () => {
  const a = rng(5);
  const b = rng(5);
  for (let i = 0; i < 20; i++) {
    const x = a();
    expect(x).toBe(b());
    expect(x).toBeGreaterThanOrEqual(0);
    expect(x).toBeLessThan(1);
  }
});
