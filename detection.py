"""MediaPipe Tasks pose wrapper: decides whether arms are raised.

Uses the Tasks Vision API (PoseLandmarker) since `mediapipe.solutions.pose`
was removed in mediapipe 0.10.33+.
"""
from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

import config

# BlazePose landmark indices (same in both legacy and Tasks APIs).
_LEFT_SHOULDER = 11
_RIGHT_SHOULDER = 12
_LEFT_WRIST = 15
_RIGHT_WRIST = 16
_LEFT_HIP = 23
_RIGHT_HIP = 24

# Maximum frame-to-frame jump (in normalized units) that Moses can make
# before we consider him "lost" and re-anchor on whoever is closest to center.
# With typical 30 FPS this is ~30% of the frame — generous for natural motion
# but tight enough to reject swapping to a helper on the other side of the room.
_MAX_MOSES_JUMP = 0.30

_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)
_MODEL_PATH = config.ROOT / "models" / "pose_landmarker_lite.task"


def _ensure_model() -> Path:
    if _MODEL_PATH.exists():
        return _MODEL_PATH
    _MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _MODEL_PATH.with_suffix(".task.tmp")
    urllib.request.urlretrieve(_MODEL_URL, tmp)
    tmp.rename(_MODEL_PATH)
    return _MODEL_PATH


@dataclass
class DetectionResult:
    arms_up: bool
    pose_found: bool
    # Normalized 0..1 (x, y) for overlay drawing.
    left_wrist: Optional[Tuple[float, float]] = None
    right_wrist: Optional[Tuple[float, float]] = None
    left_shoulder: Optional[Tuple[float, float]] = None
    right_shoulder: Optional[Tuple[float, float]] = None


class PoseDetector:
    """Single-person pose detector with a hysteresis-smoothed arms-up flag."""

    def __init__(self) -> None:
        model_path = _ensure_model()
        options = mp_vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp_vision.RunningMode.VIDEO,
            # Detect several people so helpers (Aaron and Hur) can enter the
            # frame without MediaPipe silently swapping "who" we track.
            num_poses=5,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = mp_vision.PoseLandmarker.create_from_options(options)
        self._frame_ms = 0
        # Last committed arms_up state, used for hysteresis.
        self._arms_up_state: bool = False
        # Last known Moses torso center in normalized frame coords. Initial
        # anchor is the frame center — stand in the middle at the start and
        # you'll be the one we follow.
        self._moses_center: Tuple[float, float] = (0.5, 0.5)
        # Once we've seen a real pose, we prefer staying with nearby poses
        # over re-anchoring on the center.
        self._has_locked_on: bool = False

    def close(self) -> None:
        self._landmarker.close()

    def process(self, frame_bgr) -> DetectionResult:
        """Run pose on a BGR frame (as from OpenCV). Returns DetectionResult."""
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        # Monotonic timestamp in milliseconds for VIDEO mode.
        self._frame_ms += 33
        result = self._landmarker.detect_for_video(mp_image, self._frame_ms)

        if not result.pose_landmarks:
            self._arms_up_state = False
            # Don't reset the Moses anchor — he might just have stepped out
            # briefly. Keep his last-known position so re-entering near the
            # same spot re-locks onto him.
            return DetectionResult(arms_up=False, pose_found=False)

        # Pick "Moses" from the detected poses: the one whose torso center is
        # closest to his last-known position. This survives helpers (Aaron
        # and Hur) stepping into the frame to lift his arms.
        lms = self._pick_moses(result.pose_landmarks)

        left_wrist = (lms[_LEFT_WRIST].x, lms[_LEFT_WRIST].y)
        right_wrist = (lms[_RIGHT_WRIST].x, lms[_RIGHT_WRIST].y)
        left_shoulder = (lms[_LEFT_SHOULDER].x, lms[_LEFT_SHOULDER].y)
        right_shoulder = (lms[_RIGHT_SHOULDER].x, lms[_RIGHT_SHOULDER].y)

        arms_up = self._classify_with_hysteresis(
            left_wrist_y=left_wrist[1],
            right_wrist_y=right_wrist[1],
            left_shoulder_y=left_shoulder[1],
            right_shoulder_y=right_shoulder[1],
        )

        return DetectionResult(
            arms_up=arms_up,
            pose_found=True,
            left_wrist=left_wrist,
            right_wrist=right_wrist,
            left_shoulder=left_shoulder,
            right_shoulder=right_shoulder,
        )

    def _pose_center(self, pose) -> Tuple[float, float]:
        """Torso midpoint (between the hips) in normalized frame coords."""
        lh = pose[_LEFT_HIP]
        rh = pose[_RIGHT_HIP]
        return ((lh.x + rh.x) / 2, (lh.y + rh.y) / 2)

    def _pick_moses(self, poses):
        """Select the pose closest to the last-known Moses position.

        On first detection, `_moses_center` is the frame center so whoever
        stands closest to the middle becomes Moses. After that, the anchor
        tracks him from frame to frame; helpers stepping in won't hijack the
        selection unless Moses himself has fully vanished.
        """
        ax, ay = self._moses_center
        best_idx = 0
        best_dist_sq = float("inf")
        for i, pose in enumerate(poses):
            cx, cy = self._pose_center(pose)
            d = (cx - ax) ** 2 + (cy - ay) ** 2
            if d < best_dist_sq:
                best_dist_sq = d
                best_idx = i

        chosen = poses[best_idx]
        new_center = self._pose_center(chosen)

        # If the "closest" pose is suspiciously far from last anchor (Moses
        # probably left the frame and someone else walked in), re-anchor on
        # the center rather than blindly following the newcomer. Only applies
        # once we've had a real lock before.
        if self._has_locked_on:
            jump = (
                (new_center[0] - ax) ** 2 + (new_center[1] - ay) ** 2
            ) ** 0.5
            if jump > _MAX_MOSES_JUMP:
                # Gracefully recenter.
                self._moses_center = (0.5, 0.5)
                return chosen

        self._moses_center = new_center
        self._has_locked_on = True
        return chosen

    def _classify_with_hysteresis(
        self,
        left_wrist_y: float,
        right_wrist_y: float,
        left_shoulder_y: float,
        right_shoulder_y: float,
    ) -> bool:
        # In image coordinates, y=0 is top. Wrist above shoulder => smaller y.
        # Down->up requires BOTH wrists clearly above shoulders; up->down
        # requires EITHER arm to clearly drop below its shoulder. In between
        # is the hysteresis dead band where we keep the current state.
        h = config.HYSTERESIS
        left_above = left_wrist_y < (left_shoulder_y - h)
        right_above = right_wrist_y < (right_shoulder_y - h)
        left_below = left_wrist_y > (left_shoulder_y + h)
        right_below = right_wrist_y > (right_shoulder_y + h)

        if self._arms_up_state:
            if left_below or right_below:
                self._arms_up_state = False
        else:
            if left_above and right_above:
                self._arms_up_state = True

        return self._arms_up_state
