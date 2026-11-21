import { expect, test } from "vitest";
import * as THREE from "three";
import { cameraFromCalibration, projectToPixels } from "./cameras";
import type { Calibration } from "./types";

// cam0 from config/room.json: position (-3.6,-2.6,2.8), target (0,0,1), vfov 60, 640x480
function lookAt(pos: number[], target: number[], vfov: number, w = 640, h = 480): Calibration {
  const f = new THREE.Vector3(...target).sub(new THREE.Vector3(...pos)).normalize();
  const right = new THREE.Vector3().crossVectors(f, new THREE.Vector3(0, 0, 1)).normalize();
  const down = new THREE.Vector3().crossVectors(f, right);
  const R = [right, down, f].map((v) => v.toArray());
  const C = new THREE.Vector3(...pos);
  const t = R.map((row) => -new THREE.Vector3(...row).dot(C));
  const fy = h / 2 / Math.tan((vfov * Math.PI) / 360);
  return { version: 1, id: "t", width: w, height: h, K: [[fy, 0, w / 2], [0, fy, h / 2], [0, 0, 1]], dist: [0, 0, 0, 0, 0], R, t };
}

test("the target projects to the image centre", () => {
  const cam = cameraFromCalibration(lookAt([-3.6, -2.6, 2.8], [0, 0, 1], 60));
  const [u, v] = projectToPixels(cam, new THREE.Vector3(0, 0, 1), 640, 480);
  expect(u).toBeCloseTo(320, 3);
  expect(v).toBeCloseTo(240, 3);
});

test("a point above the target projects above centre and to the right projects right", () => {
  const cam = cameraFromCalibration(lookAt([0, -4, 1.5], [0, 0, 1.5], 60));
  const up = projectToPixels(cam, new THREE.Vector3(0, 0, 2.0), 640, 480);
  const right = projectToPixels(cam, new THREE.Vector3(0.5, 0, 1.5), 640, 480);
  expect(up[1]).toBeLessThan(240);
  expect(right[0]).toBeGreaterThan(320);
});

test("projection matches the OpenCV pinhole model", () => {
  const calib = lookAt([-3.6, -2.6, 2.8], [0, 0, 1], 60);
  const cam = cameraFromCalibration(calib);
  const X = new THREE.Vector3(0.4, -0.3, 1.2);
  const Xc = calib.R.map((r, i) => r[0] * X.x + r[1] * X.y + r[2] * X.z + calib.t[i]);
  const u = (calib.K[0][0] * Xc[0]) / Xc[2] + calib.K[0][2];
  const v = (calib.K[1][1] * Xc[1]) / Xc[2] + calib.K[1][2];
  const [pu, pv] = projectToPixels(cam, X, 640, 480);
  expect(pu).toBeCloseTo(u, 3);
  expect(pv).toBeCloseTo(v, 3);
});
