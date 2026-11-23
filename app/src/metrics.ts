import type { GtSkeleton, Person3D } from "./types";

/** COCO-17 joints the CesiumMan rig can supply ground truth for: shoulders to ankles. */
export const EVAL_JOINTS = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16];

export function mpjpe(gt: GtSkeleton, est: Person3D["joints"]): number | null {
  const d: number[] = [];
  for (const j of EVAL_JOINTS) {
    const g = gt[j];
    const e = est[j];
    if (g && e) d.push(Math.hypot(g[0] - e[0], g[1] - e[1], g[2] - e[2]));
  }
  if (d.length < 6) return null;
  return d.reduce((a, b) => a + b, 0) / d.length;
}

export function median(xs: number[]): number | null {
  if (xs.length === 0) return null;
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

export function percentile(xs: number[], p: number): number | null {
  if (xs.length === 0) return null;
  const s = [...xs].sort((a, b) => a - b);
  return s[Math.min(s.length - 1, Math.floor((p / 100) * s.length))];
}
