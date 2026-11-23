import type { Person3D } from "./types";

export type Zone = "far" | "near" | "close" | "touch";
export type Pt = [number, number];

/** Zone boundaries in metres (PLAN: far >2.0, near 1.0-2.0, close 0.3-1.0, touch <0.3). */
export const BOUNDARIES: { zone: Zone; max: number }[] = [
  { zone: "touch", max: 0.3 },
  { zone: "close", max: 1.0 },
  { zone: "near", max: 2.0 },
  { zone: "far", max: Infinity },
];
export const HYSTERESIS_M = 0.15;
const ORDER: Zone[] = ["far", "near", "close", "touch"]; // increasing closeness

export interface ZoneEvent {
  person_id: number;
  object_id: string;
  from: Zone;
  to: Zone;
  distance: number;
  t: number;
}

/** Distance from a point to a convex or concave polygon outline; 0 if the point is inside. */
export function distanceToPolygon(p: Pt, poly: Pt[]): number {
  let inside = false;
  let best = Infinity;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [ax, ay] = poly[j];
    const [bx, by] = poly[i];
    if (ay > p[1] !== by > p[1] && p[0] < ((bx - ax) * (p[1] - ay)) / (by - ay) + ax) inside = !inside;
    const dx = bx - ax;
    const dy = by - ay;
    const len2 = dx * dx + dy * dy;
    const u = len2 === 0 ? 0 : Math.max(0, Math.min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / len2));
    best = Math.min(best, Math.hypot(p[0] - (ax + u * dx), p[1] - (ay + u * dy)));
  }
  return inside ? 0 : best;
}

/** Pelvis = mean of the hip joints (COCO 11, 12), projected to the floor. */
export function pelvisXY(joints: Person3D["joints"]): Pt | null {
  const l = joints[11];
  const r = joints[12];
  if (l && r) return [(l[0] + r[0]) / 2, (l[1] + r[1]) / 2];
  const one = l ?? r;
  return one ? [one[0], one[1]] : null;
}

function zoneAt(d: number): Zone {
  return BOUNDARIES.find((b) => d < b.max)!.zone;
}

/** Zone with hysteresis: entering a closer zone needs the plain boundary, leaving needs boundary + margin. */
export function nextZone(current: Zone, d: number): Zone {
  const raw = zoneAt(d);
  const ci = ORDER.indexOf(current);
  const ri = ORDER.indexOf(raw);
  if (ri > ci) return raw; // moved closer: immediate
  if (ri === ci) return current;
  // moved away: only leave if beyond the outer boundary of the current zone plus the margin
  const outer = BOUNDARIES.find((b) => b.zone === current)!.max;
  return d >= outer + HYSTERESIS_M ? raw : current;
}

export class ZoneTracker {
  private state = new Map<string, Zone>();

  update(personId: number, objectId: string, distance: number, t: number): ZoneEvent | null {
    const key = `${personId}|${objectId}`;
    const from = this.state.get(key) ?? "far";
    const to = nextZone(from, distance);
    this.state.set(key, to);
    return to === from ? null : { person_id: personId, object_id: objectId, from, to, distance, t };
  }
}
