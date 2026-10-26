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
from src.storage.sign_space_store import get_space_store
from src.spaces.space_tracker import SpaceTracker
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
        space_store: Optional[Any] = None,
    ):
        self.store = store
        self.processor_getter = processor_getter
        self.threshold = threshold
        self.buffer = buffer or GestureBuffer()
        # Sign spaces: while a space is active, only its members (+ controls)
        # are scored. group-vs-group competition never enters the scorer.
        self.space_store = space_store or get_space_store()
        self.spaces = SpaceTracker(store, self.space_store)
        # Space tokens captured during the CURRENT collection span, each with
        # the raw sequence index where it happened — the queue renders rows
        # chronologically from this.
        self._span_serial = 0
        self._prev_buffer_status = 'idle'
        self.space_tokens: List[Dict[str, Any]] = []

    def set_threshold(self, threshold: float) -> None:
        self.threshold = float(np.clip(threshold, 10.0, 95.0))

    def set_window_size(self, size: int) -> None:
        self.buffer.set_window_size(int(size))

    def reset_buffer(self) -> None:
        self.buffer.clear()
        self.spaces.on_reset()
        self._begin_span()

    def _begin_span(self) -> None:
        self._span_serial += 1
        self.space_tokens = []

    def _space_token_frame(self, token: Dict[str, Any]) -> Dict[str, Any]:
        return {"pos": len(self.buffer.accepted_sequence), **token}

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

        # Match features against the scoped gesture library: while a sign
        # space is active, only that space's members compete.
        scores: List[Dict[str, Any]] = []
        if live_features:
            candidates = self.spaces.scoped_candidates()
            scores = score_gestures(live_features, candidates, live_handedness=handedness)

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

        # New collection span begins when a sequence restarts after
        # completion — tokens from the previous sentence stop being shown.
        prev_status = self._prev_buffer_status
        cur_status = self.buffer.status
        if prev_status == "completed" and cur_status == "collecting":
            self._begin_span()
        self._prev_buffer_status = cur_status

        # Space transitions ride on buffer events (same acceptance logic the
        # window analyzer already computed). Tokens are stamped with their
        # position in the raw sequence so the queue can interleave them.
        space_token: Optional[Dict[str, Any]] = None
        if buffer_event is not None:
            if buffer_event.event_type == "accepted":
                space_token = self.spaces.on_accepted(buffer_event.gesture)
            elif buffer_event.event_type == "completed":
                space_token = self.spaces.on_completed()
            if space_token:
                self.space_tokens.append(self._space_token_frame(space_token))

        # Build landmarks for overlay rendering
        simplified_landmarks = [
            [[point[0], point[1]] for point in hand]
            for hand in hands
        ]

        buffer_state = self.buffer.get_state()
        buffer_state.update(self.spaces.get_state())
        buffer_state["sequence_tokens"] = list(self.space_tokens)

        return {
            "hand_count": hand_count,
            "landmarks": simplified_landmarks,
            "scores": scores[:5],  # top 5 matches
            "best_match": best_match,
            "threshold": self.threshold,
            "buffer_state": buffer_state,
            "space_token": space_token,
            "latest_event": {
                "event_type": buffer_event.event_type,
                "gesture": buffer_event.gesture,
                "message": buffer_event.message,
                "timestamp": buffer_event.timestamp,
                "details": buffer_event.details,
            } if buffer_event else None,
        }
