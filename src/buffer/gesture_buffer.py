"""MOVA Real-Time Gesture Buffer and Filtering Module.

Handles:
1. Continuous sliding-window outlier filtering.
2. Consecutive duplicate removal (deduplication).
3. Ordered unique gesture collection.
4. End-of-sequence detection based on configurable inactivity timeout.
5. Real-time event logging for the monitoring UI.
"""

from dataclasses import dataclass, field
import time
from typing import Dict, List, Optional, Any
from collections import deque


@dataclass
class Detection:
    gesture_name: Optional[str]
    confidence: float
    hand_count: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class BufferEvent:
    event_type: str  # "detected" | "outlier" | "duplicate" | "accepted" | "inactivity" | "completed"
    gesture: Optional[str]
    message: str
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


class GestureBuffer:
    def __init__(
        self,
        window_size: int = 5,
        end_signal_frames: int = 14,
        min_gesture_persistence: int = 3,
    ):
        """
        Args:
            window_size: Size of sliding window for outlier detection (default 5).
            end_signal_frames: Consecutive frames without hands to trigger end of sequence (~2s at 6 FPS).
            min_gesture_persistence: Minimum detections needed in window to confirm a deliberate gesture (default 3).
        """
        self.window_size = window_size if window_size % 2 == 1 else window_size + 1
        self.half_window = self.window_size // 2
        self.end_signal_frames = end_signal_frames
        self.min_gesture_persistence = min_gesture_persistence

        # Window storage: deque of Detection objects
        self.window: deque[Detection] = deque(maxlen=self.window_size)

        # Sequences
        self.accepted_sequence: List[str] = []
        self.completed_sequence: List[str] = []

        # Tracking state
        self.last_accepted_gesture: Optional[str] = None
        self.consecutive_duplicate_count: int = 0
        self.inactive_frames: int = 0
        self.candidate_streak: int = 0
        self.current_candidate: Optional[str] = None
        self.status: str = "idle"  # "idle" | "collecting" | "completed"

        # Event histories for real-time UI
        self.recent_detections: deque[Dict[str, Any]] = deque(maxlen=30)
        self.outliers: deque[Dict[str, Any]] = deque(maxlen=30)
        self.duplicates_log: deque[Dict[str, Any]] = deque(maxlen=30)
        self.events: deque[BufferEvent] = deque(maxlen=50)

    def add_detection(self, detection: Detection) -> Optional[BufferEvent]:
        """
        Process a single incoming frame detection.
        Returns a BufferEvent if an action occurred (outlier, accepted, duplicate, completed).
        """
        now = detection.timestamp

        # Record raw detection
        raw_info = {
            "gesture": detection.gesture_name,
            "confidence": round(detection.confidence, 1),
            "hand_count": detection.hand_count,
            "timestamp": now,
        }
        self.recent_detections.appendleft(raw_info)

        # Handle hand absence / inactivity
        if detection.hand_count == 0 or detection.gesture_name is None:
            self.inactive_frames += 1

            # Check if end of sequence reached
            if (
                self.status == "collecting"
                and len(self.accepted_sequence) > 0
                and self.inactive_frames >= self.end_signal_frames
            ):
                self.status = "completed"
                self.completed_sequence = list(self.accepted_sequence)
                event = BufferEvent(
                    event_type="completed",
                    gesture=None,
                    message=f"Sequence ended after {self.inactive_frames} inactive frames.",
                    timestamp=now,
                    details={"sequence": list(self.completed_sequence)},
                )
                self.events.appendleft(event)
                # Reset window and last accepted to allow clean next start
                self.window.clear()
                self.last_accepted_gesture = None
                return event

            # Append empty detection to window to keep time sliding
            self.window.append(detection)
            return None

        # Hands ARE present
        # If previous status was completed, and a new gesture starts, start a fresh sequence
        if self.status == "completed":
            self.accepted_sequence.clear()
            self.last_accepted_gesture = None
            self.consecutive_duplicate_count = 0

        self.status = "collecting"
        self.inactive_frames = 0
        self.window.append(detection)

        # If window is not yet full, wait until we have enough context
        if len(self.window) < self.window_size:
            # During warm-up, if we see consistent frames, we can process immediately if threshold met
            return None

        # Analyze center element of sliding window
        center_idx = self.half_window
        center_det = self.window[center_idx]
        candidate_gesture = center_det.gesture_name

        if not candidate_gesture:
            return None

        # Context surrounding the center element
        surrounding = [
            self.window[i].gesture_name
            for i in range(len(self.window))
            if i != center_idx and self.window[i].gesture_name is not None
        ]

        # Check for outlier:
        # If candidate appears only once in the entire window (or very low frequency)
        # while surrounding gestures are predominantly a different gesture:
        # Outlier condition: candidate occupies only 1-2 of the 5 window
        # frames while a different gesture dominates (>=3 occurrences).
        # Brief 2-frame jabs (quick hand passes) must be flagged too, not
        # just isolated single-frame spikes.
        window_counts: Dict[str, int] = {}
        for d in self.window:
            if d.gesture_name:
                window_counts[d.gesture_name] = window_counts.get(d.gesture_name, 0) + 1

        candidate_count = window_counts.get(candidate_gesture, 0)

        dominant_other = None
        for g, count in window_counts.items():
            if g != candidate_gesture and count >= (self.window_size - 2):
                dominant_other = g
                break

        if candidate_count <= 2 and dominant_other is not None:
            # Candidate is an outlier!
            outlier_info = {
                "gesture": candidate_gesture,
                "confidence": round(center_det.confidence, 1),
                "dominant_gesture": dominant_other,
                "reason": f"Isolated spike of '{candidate_gesture}' surrounded by '{dominant_other}'",
                "timestamp": now,
            }
            self.outliers.appendleft(outlier_info)
            event = BufferEvent(
                event_type="outlier",
                gesture=candidate_gesture,
                message=f"Removed outlier '{candidate_gesture}' (dominant: '{dominant_other}').",
                timestamp=now,
                details=outlier_info,
            )
            self.events.appendleft(event)
            return event

        # Check persistence: candidate must dominate the window (at least min_gesture_persistence)
        if candidate_count < self.min_gesture_persistence:
            return None

        # Now test against last accepted gesture (deduplication)
        if candidate_gesture == self.last_accepted_gesture:
            self.consecutive_duplicate_count += 1
            dup_info = {
                "gesture": candidate_gesture,
                "count": self.consecutive_duplicate_count,
                "confidence": round(center_det.confidence, 1),
                "timestamp": now,
            }
            self.duplicates_log.appendleft(dup_info)
            if self.consecutive_duplicate_count % 5 == 0:
                event = BufferEvent(
                    event_type="duplicate",
                    gesture=candidate_gesture,
                    message=f"Consecutive duplicate '{candidate_gesture}' filtered ({self.consecutive_duplicate_count} duplicate frames dropped).",
                    timestamp=now,
                    details=dup_info,
                )
                self.events.appendleft(event)
                return event
            return None

        # Deliberate gesture confirmed! Accept into sequence.
        self.last_accepted_gesture = candidate_gesture
        self.consecutive_duplicate_count = 0
        self.accepted_sequence.append(candidate_gesture)

        accept_info = {
            "gesture": candidate_gesture,
            "position": len(self.accepted_sequence),
            "confidence": round(center_det.confidence, 1),
            "timestamp": now,
        }
        event = BufferEvent(
            event_type="accepted",
            gesture=candidate_gesture,
            message=f"Accepted new gesture #{len(self.accepted_sequence)}: '{candidate_gesture}'.",
            timestamp=now,
            details=accept_info,
        )
        self.events.appendleft(event)
        return event

    def get_buffered_sequence(self) -> List[str]:
        """Return the current active sequence."""
        return list(self.accepted_sequence)

    def get_completed_sequence(self) -> List[str]:
        """Return the last completed sequence."""
        return list(self.completed_sequence)

    def has_end_signal(self) -> bool:
        """Check if an end signal has triggered."""
        return self.status == "completed"

    def clear(self) -> None:
        """Reset buffer to clean initial state."""
        self.window.clear()
        self.accepted_sequence.clear()
        self.completed_sequence.clear()
        self.last_accepted_gesture = None
        self.consecutive_duplicate_count = 0
        self.candidate_streak = 0
        self.current_candidate = None
        self.inactive_frames = 0
        self.status = "idle"
        self.recent_detections.clear()
        self.outliers.clear()
        self.duplicates_log.clear()
        self.events.clear()

    def get_state(self) -> Dict[str, Any]:
        """Return full state dictionary for real-time frontend monitoring."""
        inactivity_progress = min(1.0, self.inactive_frames / max(1, self.end_signal_frames))
        return {
            "status": self.status,
            "accepted_sequence": list(self.accepted_sequence),
            "completed_sequence": list(self.completed_sequence),
            "last_accepted_gesture": self.last_accepted_gesture,
            "duplicate_count": self.consecutive_duplicate_count,
            "inactive_frames": self.inactive_frames,
            "end_signal_frames": self.end_signal_frames,
            "inactivity_progress": round(inactivity_progress * 100, 1),
            "recent_detections": list(self.recent_detections)[:10],
            "outliers": list(self.outliers)[:10],
            "duplicates_log": list(self.duplicates_log)[:10],
            "events": [
                {
                    "event_type": e.event_type,
                    "gesture": e.gesture,
                    "message": e.message,
                    "timestamp": e.timestamp,
                    "details": e.details,
                }
                for e in list(self.events)[:15]
            ],
        }
