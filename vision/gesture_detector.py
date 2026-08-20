"""
vision/gesture_detector.py

Encapsulates all computer-vision logic for ELEMENTX:
    Webcam -> OpenCV -> MediaPipe -> landmark geometry -> Gesture

Exposes a single reusable class, GestureDetector, so that no CV code
needs to live inside the main game loop.

Supported gestures:
    NONE, OPEN_PALM, FIST, ONE_FINGER, TWO_FINGERS, THREE_FINGERS,
    THUMBS_UP, ULTIMATE (both hands open)

Design notes:
- Gesture classification is done from landmark geometry (finger
  extension tests based on joint angles / relative Y positions),
  not raw pixel thresholds, so it's resilient to different hand sizes
  and camera distances.
- A short rolling-window majority vote (GESTURE_SMOOTHING_FRAMES) is
  used to debounce noisy per-frame classification so a held FIST
  doesn't rapid-fire during landmark jitter.
- A cooldown (GESTURE_COOLDOWN) is applied by the caller (GameController)
  before triggering repeated actions from a held gesture.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Optional, Tuple

import cv2
import numpy as np

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:  # pragma: no cover - handled gracefully at runtime
    MEDIAPIPE_AVAILABLE = False

from config import (
    CAMERA_INDEX,
    CAMERA_WIDTH,
    CAMERA_HEIGHT,
    GESTURE_CONFIDENCE_THRESHOLD,
    GESTURE_SMOOTHING_FRAMES,
    MAX_HANDS,
)

# Gesture name constants
GESTURE_NONE = "NONE"
GESTURE_OPEN_PALM = "OPEN_PALM"
GESTURE_FIST = "FIST"
GESTURE_ONE_FINGER = "ONE_FINGER"
GESTURE_TWO_FINGERS = "TWO_FINGERS"
GESTURE_THREE_FINGERS = "THREE_FINGERS"
GESTURE_THUMBS_UP = "THUMBS_UP"
GESTURE_ULTIMATE = "ULTIMATE"

# MediaPipe hand landmark indices we rely on
WRIST = 0
THUMB_TIP, THUMB_IP, THUMB_MCP = 4, 3, 2
INDEX_TIP, INDEX_PIP, INDEX_MCP = 8, 6, 5
MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP = 12, 10, 9
RING_TIP, RING_PIP, RING_MCP = 16, 14, 13
PINKY_TIP, PINKY_PIP, PINKY_MCP = 20, 18, 17


@dataclass
class HandReading:
    """A single hand's landmark-derived state for one frame."""
    landmarks: List[Tuple[float, float, float]]  # normalized (x, y, z)
    handedness: str  # "Left" or "Right" (as reported by MediaPipe, mirrored)
    fingers_extended: List[bool]  # [thumb, index, middle, ring, pinky]
    palm_center: Tuple[float, float]


@dataclass
class GestureResult:
    """Output of a single detection pass, consumed by the game controller."""
    gesture: str = GESTURE_NONE
    confidence: float = 0.0
    hand_count: int = 0
    primary_hand_x: Optional[float] = None  # normalized 0..1, for movement
    hands: List[HandReading] = field(default_factory=list)


class GestureDetector:
    """Reusable webcam + MediaPipe hand-gesture detector."""

    def __init__(
        self,
        camera_index: int = CAMERA_INDEX,
        cam_width: int = CAMERA_WIDTH,
        cam_height: int = CAMERA_HEIGHT,
        max_hands: int = MAX_HANDS,
    ) -> None:
        self.camera_index = camera_index
        self.cam_width = cam_width
        self.cam_height = cam_height
        self.max_hands = max_hands

        self.cap: Optional[cv2.VideoCapture] = None
        self.camera_ok = False

        self._hands = None
        self._mp_drawing = None
        self._mp_hands = None
        self.mediapipe_ok = False

        self._history: Deque[str] = deque(maxlen=GESTURE_SMOOTHING_FRAMES)
        self.last_frame_bgr: Optional[np.ndarray] = None
        self.last_result: GestureResult = GestureResult()

    # ------------------------------------------------------------------
    # Setup / teardown
    # ------------------------------------------------------------------
    def initialize_camera(self) -> bool:
        """Attempt to open the webcam. Returns True on success."""
        try:
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW) \
                if hasattr(cv2, "CAP_DSHOW") else cv2.VideoCapture(self.camera_index)
            if not self.cap or not self.cap.isOpened():
                self.camera_ok = False
                return False
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cam_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cam_height)
            self.camera_ok = True
        except Exception:
            self.camera_ok = False
        return self.camera_ok

    def initialize_mediapipe(self) -> bool:
        """Attempt to initialize the MediaPipe Hands solution."""
        if not MEDIAPIPE_AVAILABLE:
            self.mediapipe_ok = False
            return False
        try:
            self._mp_hands = mp.solutions.hands
            self._mp_drawing = mp.solutions.drawing_utils
            self._hands = self._mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=self.max_hands,
                min_detection_confidence=0.6,
                min_tracking_confidence=0.5,
            )
            self.mediapipe_ok = True
        except Exception:
            self.mediapipe_ok = False
        return self.mediapipe_ok

    def initialize(self) -> Tuple[bool, bool]:
        """Convenience: init both camera and MediaPipe. Returns (cam_ok, mp_ok)."""
        cam_ok = self.initialize_camera()
        mp_ok = self.initialize_mediapipe()
        return cam_ok, mp_ok

    def release(self) -> None:
        """Cleanly release the webcam and MediaPipe resources."""
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        if self._hands is not None:
            try:
                self._hands.close()
            except Exception:
                pass
            self._hands = None

    # ------------------------------------------------------------------
    # Per-frame processing
    # ------------------------------------------------------------------
    def read_frame(self) -> Optional[np.ndarray]:
        """Grab a single BGR frame from the webcam, or None if unavailable."""
        if not self.camera_ok or self.cap is None:
            return None
        ok, frame = self.cap.read()
        if not ok:
            return None
        frame = cv2.flip(frame, 1)  # mirror for intuitive control
        self.last_frame_bgr = frame
        return frame

    def process_frame(self, frame: Optional[np.ndarray] = None) -> GestureResult:
        """
        Full pipeline for one frame: detect hands, classify gesture,
        smooth/debounce, and return a GestureResult.
        """
        if frame is None:
            frame = self.read_frame()

        if frame is None or not self.mediapipe_ok:
            result = GestureResult(gesture=GESTURE_NONE, confidence=0.0, hand_count=0)
            self._push_history(GESTURE_NONE)
            self.last_result = result
            return result

        hands_data = self.detect_hands(frame)
        raw_gesture, confidence, primary_x = self.classify_gesture(hands_data)

        self._push_history(raw_gesture)
        smoothed_gesture = self._majority_vote()

        result = GestureResult(
            gesture=smoothed_gesture,
            confidence=confidence,
            hand_count=len(hands_data),
            primary_hand_x=primary_x,
            hands=hands_data,
        )
        self.last_result = result
        return result

    def detect_hands(self, frame_bgr: np.ndarray) -> List[HandReading]:
        """Run MediaPipe on a frame and return structured hand readings."""
        if not self.mediapipe_ok or self._hands is None:
            return []

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._hands.process(rgb)
        rgb.flags.writeable = True

        hands_out: List[HandReading] = []
        if not results.multi_hand_landmarks:
            return hands_out

        handedness_list = results.multi_handedness or []
        for i, hand_landmarks in enumerate(results.multi_hand_landmarks):
            pts = [(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark]
            label = "Right"
            if i < len(handedness_list):
                label = handedness_list[i].classification[0].label
            fingers = self._fingers_extended(pts, label)
            palm_center = self._palm_center(pts)
            hands_out.append(
                HandReading(
                    landmarks=pts,
                    handedness=label,
                    fingers_extended=fingers,
                    palm_center=palm_center,
                )
            )
        return hands_out

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _palm_center(pts: List[Tuple[float, float, float]]) -> Tuple[float, float]:
        xs = [pts[i][0] for i in (WRIST, INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP)]
        ys = [pts[i][1] for i in (WRIST, INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP)]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    @staticmethod
    def _finger_extended(pts, tip_idx: int, pip_idx: int, mcp_idx: int) -> bool:
        """
        A finger (index/middle/ring/pinky) is considered extended if its
        tip is meaningfully further from the MCP joint (knuckle) than the
        PIP joint is -- i.e. the finger is straightened, using normalized
        y-distance which is robust to hand rotation about the camera axis.
        """
        tip_y = pts[tip_idx][1]
        pip_y = pts[pip_idx][1]
        mcp_y = pts[mcp_idx][1]
        # In image space, y decreases upward. An extended finger's tip is
        # notably higher (smaller y) than both its pip and mcp joints.
        return tip_y < pip_y < mcp_y or (mcp_y - tip_y) > 0.06

    @staticmethod
    def _thumb_extended(pts, handedness: str) -> bool:
        """Thumb extension uses x-distance from the palm since it moves
        sideways rather than up/down."""
        tip = pts[THUMB_TIP]
        mcp = pts[THUMB_MCP]
        wrist = pts[WRIST]
        # Distance from wrist normalized against hand span
        span = max(abs(pts[INDEX_MCP][0] - pts[PINKY_MCP][0]), 1e-4)
        extension = abs(tip[0] - wrist[0]) / span
        return extension > 0.55

    def _fingers_extended(self, pts, handedness: str) -> List[bool]:
        thumb = self._thumb_extended(pts, handedness)
        index = self._finger_extended(pts, INDEX_TIP, INDEX_PIP, INDEX_MCP)
        middle = self._finger_extended(pts, MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP)
        ring = self._finger_extended(pts, RING_TIP, RING_PIP, RING_MCP)
        pinky = self._finger_extended(pts, PINKY_TIP, PINKY_PIP, PINKY_MCP)
        return [thumb, index, middle, ring, pinky]

    @staticmethod
    def _is_thumbs_up(pts, fingers: List[bool]) -> bool:
        """Thumb extended & pointing up, all other fingers curled."""
        thumb, index, middle, ring, pinky = fingers
        if not thumb or any((index, middle, ring, pinky)):
            return False
        return pts[THUMB_TIP][1] < pts[THUMB_MCP][1] - 0.03  # thumb tip above mcp

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------
    def classify_gesture(
        self, hands: List[HandReading]
    ) -> Tuple[str, float, Optional[float]]:
        """
        Classify the overall gesture from 1-2 detected hands.
        Returns (gesture_name, confidence, primary_hand_normalized_x).

        Priority: two-hands-open (ULTIMATE) > single-hand gestures.
        Left hand is reserved primarily for movement; if only one hand
        is visible it is used for gestures too, per spec.
        """
        if not hands:
            return GESTURE_NONE, 0.0, None

        if len(hands) == 2:
            open_count = sum(1 for h in hands if sum(h.fingers_extended) >= 4)
            if open_count == 2:
                avg_x = sum(h.palm_center[0] for h in hands) / 2
                return GESTURE_ULTIMATE, 0.95, avg_x

        # Prefer the "Right" hand for gesture classification if present,
        # otherwise use whichever hand is available.
        primary = next((h for h in hands if h.handedness == "Right"), hands[0])
        move_hand = next((h for h in hands if h.handedness == "Left"), primary)

        gesture, confidence = self._classify_single_hand(primary)
        return gesture, confidence, move_hand.palm_center[0]

    def _classify_single_hand(self, hand: HandReading) -> Tuple[str, float]:
        thumb, index, middle, ring, pinky = hand.fingers_extended
        extended_count = sum(hand.fingers_extended)

        if self._is_thumbs_up(hand.landmarks, hand.fingers_extended):
            return GESTURE_THUMBS_UP, 0.9

        if extended_count == 0:
            return GESTURE_FIST, 0.9

        if extended_count >= 4:
            return GESTURE_OPEN_PALM, 0.9

        if index and not middle and not ring and not pinky:
            return GESTURE_ONE_FINGER, 0.85

        if index and middle and not ring and not pinky:
            return GESTURE_TWO_FINGERS, 0.85

        if index and middle and ring and not pinky:
            return GESTURE_THREE_FINGERS, 0.8

        return GESTURE_NONE, 0.4

    # ------------------------------------------------------------------
    # Smoothing / debouncing
    # ------------------------------------------------------------------
    def _push_history(self, gesture: str) -> None:
        self._history.append(gesture)

    def _majority_vote(self) -> str:
        if not self._history:
            return GESTURE_NONE
        counts = {}
        for g in self._history:
            counts[g] = counts.get(g, 0) + 1
        best = max(counts.items(), key=lambda kv: kv[1])
        # Require the majority to be a clear plurality to avoid flicker
        if best[1] / len(self._history) >= 0.5:
            return best[0]
        return GESTURE_NONE

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------
    def get_gesture(self) -> str:
        return self.last_result.gesture

    def get_confidence(self) -> float:
        return self.last_result.confidence

    def get_hand_position(self) -> Optional[float]:
        return self.last_result.primary_hand_x

    def draw_debug_overlay(self, frame_bgr: np.ndarray, result: GestureResult) -> np.ndarray:
        """Draw hand landmarks + gesture/confidence text onto a copy of the frame."""
        annotated = frame_bgr.copy()
        if self.mediapipe_ok and self._mp_drawing is not None:
            for hand in result.hands:
                h, w = annotated.shape[:2]
                for (x, y, _z) in hand.landmarks:
                    cv2.circle(annotated, (int(x * w), int(y * h)), 3, (60, 220, 255), -1)

        cv2.putText(
            annotated,
            f"GESTURE: {result.gesture}",
            (10, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (60, 220, 255),
            2,
        )
        cv2.putText(
            annotated,
            f"CONFIDENCE: {int(result.confidence * 100)}%",
            (10, 48),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (200, 200, 200),
            1,
        )
        return annotated
