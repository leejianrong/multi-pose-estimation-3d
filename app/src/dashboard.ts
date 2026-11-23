import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { median, mpjpe, percentile } from "./metrics";
import type { ZoneEvent } from "./proximity";
import type { GtSkeleton, Pose2D, Skeleton3D } from "./types";

const BONES: [number, number][] = [
  [5, 7], [7, 9], [6, 8], [8, 10], [5, 6], [11, 12], [5, 11], [6, 12], [11, 13], [13, 15], [12, 14], [14, 16],
  [0, 1], [0, 2], [1, 3], [2, 4], [0, 5], [0, 6],
];

export interface Report {
  frames_sent: number;
  skeletons: number;
  frames_with_person: number;
  mpjpe_median_mm: number | null;
  mpjpe_p95_mm: number | null;
  node_fps: Record<string, number>;
  node_ms: Record<string, Record<string, number>>;
  e2e_ms_median: number | null;
  e2e_ms_p95: number | null;
  zone_events: ZoneEvent[];
  last_gt?: GtSkeleton;
  gt_by_frame: Record<number, GtSkeleton>;
}

function lines(color: number): THREE.LineSegments {
  const g = new THREE.BufferGeometry().setAttribute("position", new THREE.BufferAttribute(new Float32Array(BONES.length * 6), 3));
  const l = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color, depthTest: false }));
  l.frustumCulled = false;
  l.renderOrder = 10; // draw over the body: the skeleton is inside the mesh
  l.layers.set(1); // dashboard only: must never appear in the sensor cameras' images
  return l;
}

function setLines(l: THREE.LineSegments, joints: (ArrayLike<number> | null)[] | null): void {
  const a = l.geometry.getAttribute("position") as THREE.BufferAttribute;
  BONES.forEach(([i, j], k) => {
    const p = joints?.[i];
    const q = joints?.[j];
    const ok = !!p && !!q;
    a.setXYZ(2 * k, ok ? p[0] : 0, ok ? p[1] : 0, ok ? p[2] : 0);
    a.setXYZ(2 * k + 1, ok ? q[0] : 0, ok ? q[1] : 0, ok ? q[2] : 0);
  });
  a.needsUpdate = true;
}

export class Dashboard {
  readonly roomCanvas: HTMLCanvasElement;
  private renderer: THREE.WebGLRenderer;
  private view: THREE.PerspectiveCamera;
  private controls: OrbitControls;
  private gtLines = lines(0x1a9850);
  private estLines = lines(0xd73027);
  private tiles = new Map<string, HTMLCanvasElement>();
  private bitmaps = new Map<string, Map<number, ImageBitmap>>();
  private gtByFrame = new Map<number, GtSkeleton>();
  private errors: number[] = [];
  private e2e: number[] = [];
  private fpsTimes = new Map<string, number[]>();
  private nodeMs = new Map<string, Record<string, number>>();
  private stats: HTMLElement;
  private lastGt?: GtSkeleton;
  private zoneEvents: ZoneEvent[] = [];
  framesSent = 0;
  skeletons = 0;
  framesWithPerson = 0;

  constructor(root: HTMLElement, private scene: THREE.Scene, camIds: string[], interactive: boolean) {
    root.innerHTML = `<div style="display:flex;gap:8px;font:13px system-ui;padding:8px">
      <div><canvas id="room" width="720" height="520"></canvas></div>
      <div id="side" style="display:flex;flex-direction:column;gap:6px"></div></div>`;
    this.roomCanvas = root.querySelector("#room") as HTMLCanvasElement;
    const side = root.querySelector("#side") as HTMLElement;
    for (const id of camIds) {
      const c = document.createElement("canvas");
      c.width = 320;
      c.height = 240;
      c.title = id;
      side.appendChild(c);
      this.tiles.set(id, c);
      this.bitmaps.set(id, new Map());
    }
    this.stats = document.createElement("pre");
    this.stats.style.margin = "0";
    side.appendChild(this.stats);
    this.renderer = new THREE.WebGLRenderer({ canvas: this.roomCanvas, antialias: true });
    this.renderer.setSize(720, 520, false);
    this.view = new THREE.PerspectiveCamera(50, 720 / 520, 0.1, 60);
    this.view.layers.enable(1);
    this.view.position.set(0, -8.5, 6);
    this.controls = new OrbitControls(this.view, this.roomCanvas);
    this.controls.target.set(0, 0, 1);
    this.controls.enabled = interactive;
    this.controls.update();
    scene.add(this.gtLines, this.estLines);
  }

  onFrameSent(frameId: number, gt: GtSkeleton, bitmaps: Map<string, ImageBitmap>): void {
    this.framesSent++;
    this.lastGt = gt;
    this.gtByFrame.set(frameId, gt);
    this.gtByFrame.delete(frameId - 300);
    setLines(this.gtLines, gt);
    for (const [id, bm] of bitmaps) {
      const store = this.bitmaps.get(id)!;
      store.set(frameId, bm);
      const old = store.get(frameId - 8);
      old?.close();
      store.delete(frameId - 8);
    }
  }

  onPose2D(p: Pose2D): void {
    const times = this.fpsTimes.get(p.camera_id) ?? [];
    const now = performance.now();
    times.push(now);
    while (times.length && now - times[0] > 3000) times.shift();
    this.fpsTimes.set(p.camera_id, times);
    this.nodeMs.set(p.camera_id, p.timings_ms);
    const tile = this.tiles.get(p.camera_id);
    const bm = this.bitmaps.get(p.camera_id)?.get(p.frame_id);
    if (!tile || !bm) return;
    const ctx = tile.getContext("2d")!;
    ctx.drawImage(bm, 0, 0, tile.width, tile.height);
    const sx = tile.width / bm.width;
    ctx.fillStyle = "#fc0";
    for (const person of p.people)
      for (const [x, y, c] of person.keypoints) if (c > 0.3) ctx.fillRect(x * sx - 2, y * sx - 2, 4, 4);
    ctx.fillStyle = "#fff";
    ctx.fillText(`${p.camera_id} f${p.frame_id}`, 4, 12);
  }

  onSkeleton(s: Skeleton3D, sentAtMs?: number): void {
    this.skeletons++;
    if (sentAtMs !== undefined) this.e2e.push(performance.now() - sentAtMs);
    const person = s.people[0];
    setLines(this.estLines, person?.joints ?? null);
    if (!person) return;
    this.framesWithPerson++;
    const gt = this.gtByFrame.get(s.frame_id);
    const e = gt ? mpjpe(gt, person.joints) : null;
    if (e !== null) this.errors.push(e);
  }

  onZoneEvent(e: ZoneEvent): void {
    this.zoneEvents.push(e);
  }

  report(): Report {
    const node_fps: Report["node_fps"] = {};
    for (const [id, t] of this.fpsTimes) node_fps[id] = t.length > 1 ? ((t.length - 1) * 1000) / (t[t.length - 1] - t[0]) : 0;
    const mm = (x: number | null) => (x === null ? null : x * 1000);
    return {
      frames_sent: this.framesSent,
      skeletons: this.skeletons,
      frames_with_person: this.framesWithPerson,
      mpjpe_median_mm: mm(median(this.errors)),
      mpjpe_p95_mm: mm(percentile(this.errors, 95)),
      node_fps,
      node_ms: Object.fromEntries(this.nodeMs),
      e2e_ms_median: median(this.e2e),
      e2e_ms_p95: percentile(this.e2e, 95),
      zone_events: this.zoneEvents,
      last_gt: this.lastGt,
      gt_by_frame: Object.fromEntries(this.gtByFrame),
    };
  }

  draw(): void {
    this.renderer.render(this.scene, this.view);
    const r = this.report();
    const f = (x: number | null, d = 0) => (x === null ? "-" : x.toFixed(d));
    this.stats.textContent =
      `green = ground truth, red = estimated\nMPJPE median ${f(r.mpjpe_median_mm)} mm  p95 ${f(r.mpjpe_p95_mm)} mm\n` +
      `frames sent ${r.frames_sent}, with 3D person ${r.frames_with_person}\n` +
      Object.entries(r.node_fps).map(([k, v]) => `${k}: ${v.toFixed(1)} FPS ${JSON.stringify(r.node_ms[k] ? Object.fromEntries(Object.entries(r.node_ms[k]).map(([a, b]) => [a, Math.round(b)])) : {})}`).join("\n") +
      `\nzones: ${this.zoneEvents.slice(-5).map((e) => `${e.object_id} ${e.from}>${e.to}`).join(", ")}` +
      `\nend-to-end median ${f(r.e2e_ms_median)} ms p95 ${f(r.e2e_ms_p95)} ms`;
  }

  sentAtLookup(sentAt: Map<number, number>, frameId: number): number | undefined {
    return sentAt.get(frameId);
  }
}
