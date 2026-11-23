import * as THREE from "three";
import type { Calibration } from "./types";
import { cameraFromCalibration } from "./cameras";

export interface CameraRig {
  calib: Calibration;
  camera: THREE.PerspectiveCamera;
  ws: WebSocket;
}

/** Wire format shared with python/posesim/messages.py: u32be header length, JSON header, JPEG. */
export function packFrame(header: object, jpeg: ArrayBuffer): ArrayBuffer {
  const h = new TextEncoder().encode(JSON.stringify(header));
  const out = new Uint8Array(4 + h.length + jpeg.byteLength);
  new DataView(out.buffer).setUint32(0, h.length, false);
  out.set(h, 4);
  out.set(new Uint8Array(jpeg), 4 + h.length);
  return out.buffer;
}

export class Streamer {
  readonly rigs: CameraRig[] = [];
  private renderer: THREE.WebGLRenderer;
  readonly canvas: HTMLCanvasElement;
  readonly sentAt = new Map<number, number>();

  constructor(
    calibs: Calibration[],
    ports: Record<string, number>,
    host = "127.0.0.1",
  ) {
    this.canvas = document.createElement("canvas");
    this.canvas.width = calibs[0].width;
    this.canvas.height = calibs[0].height;
    this.renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: true });
    this.renderer.setSize(this.canvas.width, this.canvas.height, false);
    for (const c of calibs) {
      const ws = new WebSocket(`ws://${host}:${ports[c.id]}/frames`);
      ws.binaryType = "arraybuffer";
      this.rigs.push({ calib: c, camera: cameraFromCalibration(c), ws });
    }
  }

  get connected(): boolean {
    return this.rigs.every((r) => r.ws.readyState === WebSocket.OPEN);
  }

  /** Render every camera for this frame, return the bitmaps (for tiles) and send the JPEGs. */
  async capture(scene: THREE.Scene, frameId: number, tCapture: number): Promise<Map<string, ImageBitmap>> {
    const bitmaps = new Map<string, ImageBitmap>();
    this.sentAt.set(frameId, performance.now());
    for (const rig of this.rigs) {
      this.renderer.render(scene, rig.camera);
      bitmaps.set(rig.calib.id, await createImageBitmap(this.canvas));
      const blob: Blob = await new Promise((res, rej) =>
        this.canvas.toBlob((b) => (b ? res(b) : rej(new Error("toBlob failed"))), "image/jpeg", 0.92),
      );
      if (rig.ws.readyState === WebSocket.OPEN) {
        rig.ws.send(
          packFrame({ camera_id: rig.calib.id, frame_id: frameId, t_capture: tCapture }, await blob.arrayBuffer()),
        );
      }
    }
    return bitmaps;
  }
}
