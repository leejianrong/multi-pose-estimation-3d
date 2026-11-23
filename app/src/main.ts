import { Dashboard } from "./dashboard";
import { buildSculpture, type ObjectSpec } from "./objects";
import { ZoneTracker, distanceToPolygon, pelvisXY } from "./proximity";
import { Sim } from "./sim";
import { Streamer } from "./streamer";
import type { Calibration, Pose2D, RoomConfig, Skeleton3D } from "./types";

const q = new URLSearchParams(location.search);
const scenario = q.get("scenario") !== null;
const duration = Number(q.get("duration") ?? 20); // sim seconds, scenario mode
const camFps = Number(q.get("fps") ?? 10);
const host = q.get("host") ?? "127.0.0.1";

async function json<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json() as Promise<T>;
}

function subscribe<T>(url: string, onMsg: (m: T) => void): void {
  const open = () => {
    const ws = new WebSocket(url);
    ws.onmessage = (e) => onMsg(JSON.parse(e.data as string) as T);
    ws.onclose = () => setTimeout(open, 1000);
  };
  open();
}

async function main(): Promise<void> {
  const root = document.getElementById("app")!;
  const cfg = await json<RoomConfig>("/repo/config/room.json");
  const calibs = await Promise.all(cfg.cameras.map((c) => json<Calibration>(`/repo/calibration/${c.id}.json`)));
  const sim = new Sim(cfg);
  const { objects: specs } = await json<{ objects: ObjectSpec[] }>("/repo/config/objects.json");
  const sculptures = specs.map(buildSculpture);
  for (const o of sculptures) sim.scene.add(o.mesh);
  const zones = new ZoneTracker();
  await sim.load(`/repo/${cfg.avatar.path}`);
  const streamer = new Streamer(calibs, cfg.services.nodes, host);
  const dash = new Dashboard(root, sim.scene, calibs.map((c) => c.id), !scenario);

  for (const c of calibs)
    subscribe<Pose2D>(`ws://${host}:${cfg.services.nodes[c.id]}/poses`, (m) => dash.onPose2D(m));
  subscribe<Skeleton3D>(`ws://${host}:${cfg.services.fusion}`, (m) => {
    dash.onSkeleton(m, streamer.sentAt.get(m.frame_id));
    for (const person of m.people) {
      const pelvis = pelvisXY(person.joints);
      if (!pelvis) continue;
      for (const o of sculptures) {
        const e = zones.update(person.track_id, o.spec.id, distanceToPolygon(pelvis, o.footprint), m.t_capture);
        if (e) dash.onZoneEvent(e);
      }
    }
  });

  while (!streamer.connected) await new Promise((r) => setTimeout(r, 200));
  await new Promise((r) => setTimeout(r, 500));

  let frameId = 0;
  let busy = false;
  const maxFrames = Math.round(duration * camFps);
  const tick = async () => {
    if (busy) return;
    busy = true;
    const t = frameId / camFps; // sim clock: deterministic regardless of wall pacing
    sim.update(t);
    const gt = sim.groundTruth();
    const bitmaps = await streamer.capture(sim.scene, frameId, t);
    dash.onFrameSent(frameId, gt, bitmaps);
    frameId++;
    busy = false;
    if (scenario && frameId >= maxFrames) {
      clearInterval(timer);
      await new Promise((r) => setTimeout(r, 3000)); // let the pipeline drain
      (window as unknown as { __report: unknown }).__report = dash.report();
      document.title = "DONE";
    }
  };
  const timer = setInterval(tick, 1000 / camFps);
  // Headless scenario runs share the CPU with the pose nodes, so the dashboard redraws rarely.
  const loop = () => {
    dash.draw();
    if (scenario) setTimeout(loop, 1000);
    else requestAnimationFrame(loop);
  };
  loop();
}

main().catch((e) => {
  document.body.textContent = `error: ${e}`;
  (window as unknown as { __error: string }).__error = String(e);
});
