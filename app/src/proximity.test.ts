import { expect, test } from "vitest";
import { ZoneTracker, distanceToPolygon, nextZone, pelvisXY } from "./proximity";

const square: [number, number][] = [[0, 0], [1, 0], [1, 1], [0, 1]];

test("distance to a polygon: inside, outside, and on an edge", () => {
  expect(distanceToPolygon([0.5, 0.5], square)).toBe(0);
  expect(distanceToPolygon([2, 0.5], square)).toBeCloseTo(1, 9);
  expect(distanceToPolygon([1, 0.5], square)).toBeCloseTo(0, 9);
  expect(distanceToPolygon([2, 2], square)).toBeCloseTo(Math.SQRT2, 9);
});

test("approaching passes through every zone in order", () => {
  const tr = new ZoneTracker();
  const seq: string[] = [];
  for (const d of [3, 1.9, 0.9, 0.2]) {
    const e = tr.update(1, "a", d, 0);
    if (e) seq.push(`${e.from}>${e.to}`);
  }
  expect(seq).toEqual(["far>near", "near>close", "close>touch"]);
});

test("hysteresis suppresses flicker for a signal jittering +-0.1 m around a boundary", () => {
  const tr = new ZoneTracker();
  tr.update(1, "a", 1.5, 0); // near
  let events = 0;
  for (let i = 0; i < 20; i++) if (tr.update(1, "a", i % 2 ? 1.1 : 0.9, i)) events++;
  expect(events).toBe(1); // a single near>close, no flicker back
});

test("leaving needs the boundary plus the margin", () => {
  expect(nextZone("close", 1.05)).toBe("close");
  expect(nextZone("close", 1.2)).toBe("near");
  expect(nextZone("touch", 0.4)).toBe("touch");
  expect(nextZone("touch", 0.5)).toBe("close");
});

test("each person and object pair has its own state", () => {
  const tr = new ZoneTracker();
  expect(tr.update(1, "a", 0.5, 0)?.to).toBe("close");
  expect(tr.update(2, "a", 3, 0)).toBeNull();
  expect(tr.update(1, "b", 0.5, 0)?.to).toBe("close");
});

test("pelvis falls back to one hip and is null with none", () => {
  const j: (number[] | null)[] = Array(17).fill(null);
  expect(pelvisXY(j)).toBeNull();
  j[11] = [1, 2, 0.9, 1];
  expect(pelvisXY(j)).toEqual([1, 2]);
  j[12] = [3, 4, 0.9, 1];
  expect(pelvisXY(j)).toEqual([2, 3]);
});
