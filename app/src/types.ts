export interface Calibration {
  version: number;
  id: string;
  width: number;
  height: number;
  K: number[][];
  dist: number[];
  R: number[][];
  t: number[];
}

export interface RoomConfig {
  size: [number, number, number];
  camera_width: number;
  camera_height: number;
  cameras: { id: string }[];
  avatar: { path: string; path_radius: number; speed_mps: number; shoulder_to_ankle_m: number };
  services: { nodes: Record<string, number>; fusion: number };
}

export type Joint3 = [number, number, number];
export type GtSkeleton = (Joint3 | null)[]; // 17 COCO joints, room frame, metres

export interface Person2D {
  bbox: number[];
  score: number;
  keypoints: number[][];
}
export interface Pose2D {
  camera_id: string;
  frame_id: number;
  t_capture: number;
  people: Person2D[];
  timings_ms: Record<string, number>;
}
export interface Person3D {
  track_id: number;
  joints: (number[] | null)[];
  partial: boolean;
  views: string[];
}
export interface Skeleton3D {
  frame_id: number;
  t_capture: number;
  people: Person3D[];
  cameras_used: string[];
  cameras_down: string[];
  timings_ms: Record<string, number>;
}
