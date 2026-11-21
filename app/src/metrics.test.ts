import { expect, test } from "vitest";
import { median, mpjpe, percentile } from "./metrics";
import type { GtSkeleton } from "./types";

const gt: GtSkeleton = Array.from({ length: 17 }, (_, i) => [i, 0, 0] as [number, number, number]);

test("mpjpe is zero for a perfect estimate and the offset for a shifted one", () => {
  const perfect = gt.map((g) => [g![0], 0, 0, 1]);
  expect(mpjpe(gt, perfect)).toBeCloseTo(0, 9);
  const shifted = gt.map((g) => [g![0], 0.1, 0, 1]);
  expect(mpjpe(gt, shifted)).toBeCloseTo(0.1, 9);
});

test("mpjpe ignores joints without ground truth and needs at least 6 comparable joints", () => {
  const est = gt.map((g) => [g![0], 0, 0, 1]);
  const sparse: GtSkeleton = gt.map((g, i) => (i < 12 ? null : g));
  expect(mpjpe(sparse, est)).toBeNull();
});

test("median and percentile", () => {
  expect(median([3, 1, 2])).toBe(2);
  expect(median([1, 2, 3, 4])).toBe(2.5);
  expect(median([])).toBeNull();
  expect(percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 95)).toBe(10);
});
