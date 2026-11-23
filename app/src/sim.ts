import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import type { GtSkeleton, RoomConfig } from "./types";

THREE.Object3D.DEFAULT_UP.set(0, 0, 1); // room frame: Z up, +Y front

// COCO-17 index -> CesiumMan joint node names (left/right resolved at load, see resolveSides).
const BONES = {
  shoulder: ["Skeleton_arm_joint_L__4_", "Skeleton_arm_joint_R"],
  elbow: ["Skeleton_arm_joint_L__3_", "Skeleton_arm_joint_R__2_"],
  wrist: ["Skeleton_arm_joint_L__2_", "Skeleton_arm_joint_R__3_"],
  hip: ["leg_joint_L_1", "leg_joint_R_1"],
  knee: ["leg_joint_L_2", "leg_joint_R_2"],
  ankle: ["leg_joint_L_3", "leg_joint_R_3"],
  toe: ["leg_joint_L_5", "leg_joint_R_5"],
} as const;
// COCO indices of [left, right] for each joint kind
const COCO: Record<string, [number, number]> = {
  shoulder: [5, 6],
  elbow: [7, 8],
  wrist: [9, 10],
  hip: [11, 12],
  knee: [13, 14],
  ankle: [15, 16],
};

export class Sim {
  readonly scene = new THREE.Scene();
  private avatar = new THREE.Group();
  private mixer?: THREE.AnimationMixer;
  private duration = 1;
  private nodes: Record<string, THREE.Object3D> = {};
  private swapSides = false;
  private yawOffset = 0;

  constructor(private cfg: RoomConfig) {
    const [W, D, H] = cfg.size;
    this.scene.background = new THREE.Color(0xd9dde3);
    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(W, D),
      new THREE.MeshStandardMaterial({ color: 0x9aa3ad, roughness: 0.9 }),
    );
    this.scene.add(floor);
    const grid = new THREE.GridHelper(Math.max(W, D), Math.max(W, D), 0x667, 0x889);
    grid.rotation.x = Math.PI / 2;
    grid.position.z = 0.002;
    this.scene.add(grid);
    const wallMat = new THREE.MeshStandardMaterial({ color: 0xe8e4dc, roughness: 1, side: THREE.DoubleSide });
    for (const [pos, rotZ, w] of [
      [[0, D / 2, H / 2], 0, W],
      [[0, -D / 2, H / 2], 0, W],
      [[W / 2, 0, H / 2], Math.PI / 2, D],
      [[-W / 2, 0, H / 2], Math.PI / 2, D],
    ] as [number[], number, number][]) {
      const wall = new THREE.Mesh(new THREE.PlaneGeometry(w, H), wallMat);
      wall.rotation.x = Math.PI / 2;
      wall.rotation.y = rotZ;
      wall.position.set(pos[0], pos[1], pos[2]);
      wall.layers.set(2); // seen by the sensor cameras only, so the dashboard can look inside
      this.scene.add(wall);
    }
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x667788, 1.4));
    const sun = new THREE.DirectionalLight(0xffffff, 1.6);
    sun.position.set(2, -3, 6);
    this.scene.add(sun);
    const box = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.BoxGeometry(W, D, H)),
      new THREE.LineBasicMaterial({ color: 0x556070 }),
    );
    box.position.z = H / 2;
    box.layers.set(1); // dashboard only
    this.scene.add(box);
    this.scene.add(this.avatar);
  }

  async load(url: string): Promise<void> {
    const gltf = await new GLTFLoader().loadAsync(url);
    const model = gltf.scene;
    model.rotation.x = Math.PI / 2; // glTF is Y-up, the room is Z-up
    this.avatar.add(model);
    model.traverse((o) => (this.nodes[o.name] = o));
    this.mixer = new THREE.AnimationMixer(model);
    const clip = gltf.animations[0];
    this.duration = clip.duration;
    this.mixer.clipAction(clip).play();
    this.pose(0);
    // Rescale so shoulder-to-ankle matches the config (CesiumMan is ~1.3 m tall). A correctly
    // authored avatar (~1.7 m) ends up with a scale of ~1.
    model.updateMatrixWorld(true);
    const span = Math.abs(this.world(BONES.shoulder[0]).z - this.world(BONES.ankle[0]).z);
    model.scale.setScalar(this.cfg.avatar.shoulder_to_ankle_m / span);
    this.resolveSides();
  }

  private world(name: string): THREE.Vector3 {
    return this.nodes[name].getWorldPosition(new THREE.Vector3());
  }

  /** Decide which named side is the person's anatomical left, and which way they face. */
  private resolveSides(): void {
    this.avatar.rotation.z = 0;
    this.avatar.position.set(0, 0, 0);
    this.avatar.updateMatrixWorld(true);
    const [tl, tr] = BONES.toe.map((n) => this.world(n));
    const [al, ar] = BONES.ankle.map((n) => this.world(n));
    // CesiumMan's "toe" joints sit behind the ankles, so the foot-forward direction is the inverse.
    // Verified against the pose model: with the sign the other way round, left/right were swapped.
    const fwd = tl.sub(al).add(tr.sub(ar)).negate();
    fwd.z = 0;
    fwd.normalize();
    // anatomical right-hand side of a person facing `fwd` with +Z up is fwd x up
    const rightVec = new THREE.Vector3().crossVectors(fwd, new THREE.Vector3(0, 0, 1));
    const [sl, sr] = BONES.shoulder.map((n) => this.world(n));
    this.swapSides = sr.sub(sl).dot(rightVec) < 0; // named "R" is actually on the left
    this.yawOffset = -Math.atan2(fwd.y, fwd.x); // rotate so the person faces +X at yaw 0
  }

  private pose(t: number): void {
    this.mixer?.setTime(t % this.duration);
  }

  /** Walk a circle of path_radius around the room centre; t in seconds. */
  update(t: number): void {
    const { path_radius: r, speed_mps: v } = this.cfg.avatar;
    const th = (v * t) / r;
    this.avatar.position.set(r * Math.cos(th), r * Math.sin(th), 0);
    this.avatar.rotation.z = th + Math.PI / 2 + this.yawOffset; // facing the tangent
    this.pose(t);
    this.avatar.updateMatrixWorld(true);
  }

  groundTruth(): GtSkeleton {
    const gt: GtSkeleton = Array(17).fill(null);
    for (const [kind, [iL, iR]] of Object.entries(COCO)) {
      const [nl, nr] = BONES[kind as keyof typeof BONES];
      const left = this.swapSides ? nr : nl;
      const right = this.swapSides ? nl : nr;
      gt[iL] = this.world(left).toArray() as [number, number, number];
      gt[iR] = this.world(right).toArray() as [number, number, number];
    }
    return gt;
  }
}
