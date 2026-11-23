import * as THREE from "three";
import type { Calibration } from "./types";

/** Build a three.js camera (room frame, Z up) matching an OpenCV calibration record (ADR-0003). */
export function cameraFromCalibration(c: Calibration): THREE.PerspectiveCamera {
  const fy = c.K[1][1];
  const vfov = (2 * Math.atan(c.height / 2 / fy) * 180) / Math.PI;
  const cam = new THREE.PerspectiveCamera(vfov, c.width / c.height, 0.1, 40);
  const [r0, r1, r2] = c.R.map((r) => new THREE.Vector3(...r)); // OpenCV axes in world coordinates
  const basis = new THREE.Matrix4().makeBasis(r0, r1.clone().negate(), r2.clone().negate());
  cam.quaternion.setFromRotationMatrix(basis);
  const Rt = new THREE.Matrix4().makeBasis(r0, r1, r2); // camera -> world rotation (columns of R^T)
  const t = new THREE.Vector3(...c.t);
  cam.position.copy(t.applyMatrix4(Rt).negate());
  cam.layers.enable(2); // walls
  cam.updateMatrixWorld(true);
  return cam;
}

export function projectToPixels(cam: THREE.PerspectiveCamera, p: THREE.Vector3, w: number, h: number): [number, number] {
  const v = p.clone().project(cam);
  return [((v.x + 1) / 2) * w, ((1 - v.y) / 2) * h];
}
