import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
from typing import List, Optional, Tuple
import os
from pathlib import Path


class MediaPipeProcessor:
    def __init__(self, model_path: str = None, num_hands: int = 2):
        if model_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            model_path = str(base_dir / "data" / "model" / "hand_landmarker.task")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"MediaPipe model not found at {model_path}")
        
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=num_hands,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

    def process_frame(self, frame_bgr: np.ndarray):
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        return self.detector.detect(mp_image)

    def draw_landmarks(self, frame_bgr: np.ndarray, detection_result) -> np.ndarray:
        if detection_result.hand_landmarks:
            for hand_landmarks in detection_result.hand_landmarks:
                for lm in hand_landmarks:
                    x = int(lm.x * frame_bgr.shape[1])
                    y = int(lm.y * frame_bgr.shape[0])
                    cv2.circle(frame_bgr, (x, y), 5, (0, 255, 0), -1)
                
                connections = [
                    (0,1), (1,2), (2,3), (3,4),
                    (0,5), (5,6), (6,7), (7,8),
                    (5,9), (9,10), (10,11), (11,12),
                    (9,13), (13,14), (14,15), (15,16),
                    (13,17), (17,18), (18,19), (19,20),
                    (0,17)
                ]
                for p1, p2 in connections:
                    lm1 = hand_landmarks[p1]
                    lm2 = hand_landmarks[p2]
                    x1, y1 = int(lm1.x * frame_bgr.shape[1]), int(lm1.y * frame_bgr.shape[0])
                    x2, y2 = int(lm2.x * frame_bgr.shape[1]), int(lm2.y * frame_bgr.shape[0])
                    cv2.line(frame_bgr, (x1, y1), (x2, y2), (255, 0, 0), 2)
        return frame_bgr

    def extract_landmarks(self, detection_result) -> List[List[List[float]]]:
        hands = []
        if detection_result.hand_landmarks:
            for hand_landmarks in detection_result.hand_landmarks:
                hands.append([[lm.x, lm.y, lm.z] for lm in hand_landmarks])
        return hands

    def get_handedness(self, detection_result) -> List[str]:
        handedness = []
        if detection_result.handedness:
            for h in detection_result.handedness:
                handedness.append(h[0].category_name)
        return handedness


def normalize_landmarks(landmarks_3d: List[List[float]]) -> np.ndarray:
    pts = np.array(landmarks_3d, dtype=np.float64)
    wrist = pts[0].copy()
    pts = pts - wrist
    max_dist = np.max(np.linalg.norm(pts, axis=1))
    if max_dist > 0:
        pts = pts / max_dist
    return pts


def compute_palm_normal(pts_normalized: np.ndarray) -> np.ndarray:
    v1 = pts_normalized[5] - pts_normalized[0]
    v2 = pts_normalized[17] - pts_normalized[0]
    normal = np.cross(v1, v2)
    norm_len = np.linalg.norm(normal)
    if norm_len > 0:
        normal = normal / norm_len
    return normal


FINGER_TIPS = (4, 8, 12, 16, 20)
FINGER_MCPS = (2, 5, 9, 13, 17)


def compute_finger_extension_profile(pts_normalized: np.ndarray) -> List[float]:
    wrist = pts_normalized[0]
    profile = []
    for tip_index, mcp_index in zip(FINGER_TIPS, FINGER_MCPS):
        tip_distance = np.linalg.norm(pts_normalized[tip_index] - wrist)
        mcp_distance = np.linalg.norm(pts_normalized[mcp_index] - wrist)
        ratio = tip_distance / mcp_distance if mcp_distance > 1e-8 else 0.0
        profile.append(float(np.clip(ratio / 2.0, 0.0, 1.0)))
    return profile


def extract_features(landmarks_3d: List[List[float]]) -> List[float]:
    pts = normalize_landmarks(landmarks_3d)
    palm_normal = compute_palm_normal(pts)
    finger_profile = compute_finger_extension_profile(pts)
    features = pts.flatten().tolist() + palm_normal.tolist() + finger_profile
    return features


def extract_two_hand_features(left_landmarks: List[List[float]], right_landmarks: List[List[float]]) -> List[float]:
    left_features = extract_features(left_landmarks)
    right_features = extract_features(right_landmarks)
    
    left_wrist = np.array(left_landmarks[0])
    right_wrist = np.array(right_landmarks[0])
    relative_vec = right_wrist - left_wrist
    rel_norm = np.linalg.norm(relative_vec)
    if rel_norm > 0:
        relative_vec = relative_vec / rel_norm
    
    return left_features + right_features + relative_vec.tolist()


def determine_hand_side(landmarks: List[List[float]]) -> str:
    """Determine whether landmarks correspond to a Left or Right hand using 3D palm geometry."""
    pts = np.array(landmarks)
    if pts.shape[0] < 21:
        return "Unknown"
    # Wrist 0, Index MCP 5, Pinky MCP 17, Thumb CMC 1
    v_index = pts[5] - pts[0]
    v_pinky = pts[17] - pts[0]
    palm_normal = np.cross(v_index, v_pinky)
    v_thumb = pts[1] - pts[0]
    side_vec = np.cross(v_index, palm_normal)
    val = float(np.dot(side_vec, v_thumb))
    return "Right" if val > 0 else "Left"


def get_gesture_handedness(gesture: dict) -> str:
    """Return stored handedness, or compute from landmarks for legacy gestures."""
    h = gesture.get("handedness")
    if h:
        return h if isinstance(h, str) else h[0]
    # Compute from landmarks if present
    lm = gesture.get("landmarks", [])
    if isinstance(lm, list) and len(lm) >= 21:
        return determine_hand_side(lm[:21])
    return "Unknown"


def score_gestures(
    live_features: List[float],
    gestures: List[dict],
    live_handedness: Optional[List[str]] = None,
) -> List[dict]:
    """
    Return every compatible stored gesture, ordered by similarity.
    Includes contrast separation, inter-finger gap metrics, and left/right handedness differentiation.
    """
    single_size = 71
    two_hand_size = 145

    def cosine_similarity(a, b):
        a, b = np.array(a, dtype=np.float64), np.array(b, dtype=np.float64)
        denominator = np.linalg.norm(a) * np.linalg.norm(b)
        return float(np.dot(a, b) / denominator) if denominator else 0.0

    def single_score(live, stored):
        if len(live) != single_size or len(stored) != single_size:
            return None
        # 1. Whole-hand shape cosine similarity (stretched range [0.55, 1.0])
        raw_cos = cosine_similarity(live[:66], stored[:66])
        shape = max(0.0, min(1.0, (raw_cos - 0.55) / 0.45))
        
        # 2. Finger extension profile (5 values: thumb, index, middle, ring, pinky)
        diff = np.abs(np.array(live[66:]) - np.array(stored[66:]))
        mean_diff = float(np.mean(diff))
        max_diff = float(np.max(diff))
        profile = float(np.clip(1.0 - (mean_diff * 0.70 + max_diff * 0.45), 0.0, 1.0))

        # 3. Inter-finger tip gap distances (from the 63 normalized coords)
        # Separates close poses like pinch_small vs pointing_towards_someone
        pts_l = np.array(live[:63]).reshape(21, 3)
        pts_s = np.array(stored[:63]).reshape(21, 3)
        gap_pairs = [(4, 8), (4, 12), (8, 12), (12, 16), (16, 20)]
        gap_diffs = [
            abs(np.linalg.norm(pts_l[p1] - pts_l[p2]) - np.linalg.norm(pts_s[p1] - pts_s[p2]))
            for p1, p2 in gap_pairs
        ]
        mean_gap_diff = float(np.mean(gap_diffs))
        max_gap_diff = float(np.max(gap_diffs))
        gap_score = float(np.clip(1.0 - (mean_gap_diff * 1.5 + max_gap_diff * 1.2), 0.0, 1.0))
        
        return (shape * 0.40 + profile * 0.35 + gap_score * 0.25) * 100.0

    scores = []
    live_side = live_handedness[0] if live_handedness and len(live_handedness) > 0 else None

    for gesture in gestures:
        stored = gesture.get("features", [])
        stored_side = get_gesture_handedness(gesture)
        score = None
        hand_match = True

        if len(live_features) == single_size:
            score = single_score(live_features, stored)
            if score is None and len(stored) == 66:
                raw = cosine_similarity(live_features[:66], stored)
                score = max(0.0, min(1.0, (raw - 0.55) / 0.45)) * 100.0

            # Handedness penalty for single-hand gestures
            # If live hand is Left and stored is Right (or vice versa), apply mismatch penalty
            if score is not None and live_side and stored_side and stored_side != "Unknown":
                if live_side != stored_side:
                    hand_match = False
                    score = score * 0.35  # Strong opposite-hand penalty

        elif len(live_features) == two_hand_size and len(stored) == two_hand_size:
            left = single_score(live_features[:single_size], stored[:single_size])
            right = single_score(live_features[single_size:single_size * 2], stored[single_size:single_size * 2])
            raw_rel = cosine_similarity(live_features[-3:], stored[-3:])
            relative = max(0.0, min(1.0, (raw_rel - 0.50) / 0.50)) * 100.0
            if left is not None and right is not None:
                score = left * 0.40 + right * 0.40 + relative * 0.20

        if score is not None:
            scores.append({
                "id": gesture.get("id"),
                "name": gesture["name"],
                "score": round(score, 1),
                "handedness": stored_side,
                "hand_match": hand_match,
            })

    return sorted(scores, key=lambda item: item["score"], reverse=True)
