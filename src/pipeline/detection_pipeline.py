"""MOVA Real-Time Gesture Detection & Processing Pipeline.

Coordinates:
- MediaPipe hand landmark detection
- Feature extraction (1-hand 71-dim and 2-hand 145-dim)
- Similarity scoring against registered gestures
- Gesture thresholding and classification
- Continuous feeding to GestureBuffer (outlier removal, deduplication, buffering)
"""

from typing import Dict, Any, Optional, List
import numpy as np
import time

from src.buffer.gesture_buffer import GestureBuffer, Detection
from src.vision.mediapipe_processor import (
    extract_features,
    extract_two_hand_features,
    score_gestures,
)


class RealTimePipeline:
    def __init__(
        self,
        store,
        processor_getter,
        threshold: float = 72.0,
        buffer: Optional[GestureBuffer] = None,
    ):
        self.store = store
        self.processor_getter = processor_getter
        self.threshold = threshold
        self.buffer = buffer or GestureBuffer()

    def set_threshold(self, threshold: float) -> None:
        self.threshold = float(np.clip(threshold, 10.0, 95.0))

    def reset_buffer(self) -> None:
        self.buffer.clear()

    def process_frame(self, frame_bgr: np.ndarray) -> Dict[str, Any]:
        """
        Process a single BGR image frame through detection, matching, and buffering.
        Returns full analysis results and buffer states for UI visualization.
        """
        proc = self.processor_getter()
        result = proc.process_frame(frame_bgr)
        hands = proc.extract_landmarks(result)
        handedness = proc.get_handedness(result)

        live_features = None
        hand_count = len(hands)

        if hand_count == 1:
            live_features = extract_features(hands[0])
        elif hand_count >= 2:
            left, right = None, None
            for index, side in enumerate(handedness):
                if side == "Left":
                    left = hands[index]
                elif side == "Right":
                    right = hands[index]
            if left is not None and right is not None:
                live_features = extract_two_hand_features(left, right)

        # Match features against stored gesture library
        scores: List[Dict[str, Any]] = []
        if live_features:
            scores = score_gestures(live_features, self.store.get_all(), live_handedness=handedness)

        best_match: Optional[Dict[str, Any]] = None
        detected_name: Optional[str] = None
        detected_conf: float = 0.0

        if scores:
            top = scores[0]
            if top.get("score", 0.0) >= self.threshold:
                best_match = top
                detected_name = top["name"]
                detected_conf = float(top["score"])

        # Feed to gesture buffer
        detection = Detection(
            gesture_name=detected_name,
            confidence=detected_conf,
            hand_count=hand_count,
            timestamp=time.time(),
        )
        buffer_event = self.buffer.add_detection(detection)

        # Build landmarks for overlay rendering
        simplified_landmarks = [
            [[point[0], point[1]] for point in hand]
            for hand in hands
        ]

        return {
            "hand_count": hand_count,
            "landmarks": simplified_landmarks,
            "scores": scores[:5],  # top 5 matches
            "best_match": best_match,
            "threshold": self.threshold,
            "buffer_state": self.buffer.get_state(),
            "latest_event": {
                "event_type": buffer_event.event_type,
                "gesture": buffer_event.gesture,
                "message": buffer_event.message,
                "timestamp": buffer_event.timestamp,
                "details": buffer_event.details,
            } if buffer_event else None,
        }
