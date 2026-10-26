"""MOVA One-shot speech layer.

A one-shot sign space (join_mode == "one_shot") holds gestures that each
carry a pre-baked spoken sentence (gesture["shot"]). While that space is
active, the FIRST accepted member gesture speaks its sentence immediately:

- there is no queue round-trip and no AI processing — the audio file was
  generated at registration time, so playback latency is zero;
- the space deactivates right after speaking, exactly like a spoken
  utterance: one sign, one sentence, done — re-activate to speak again;
- anything buffered BEFORE activation is irrelevant: candidate scoping
  already prevents foreign gestures from matching inside the space.

This module stays deliberately separate from SpaceTracker and the
detection pipeline beyond a single hook call per accepted gesture.
"""

from typing import Any, Dict, Optional


class OneShotSpeaker:
    """Detects one-shot speech moments and reports what the client should say."""

    def __init__(self, gesture_store, space_store, space_tracker):
        self.gestures = gesture_store
        self.spaces = space_store
        self.tracker = space_tracker
        # While True the spoken exchange is over but the user still has a
        # hand in frame — the space stays active so nothing re-registers
        # in Standard scope. Cleared once hands leave (pipeline calls flush).
        self.pending_hand_off = False

    def on_accepted(self, gesture_name: Optional[str]) -> Optional[Dict[str, Any]]:
        """Call after each accepted gesture.

        Returns a speech payload dict when the accepted gesture triggered a
        one-shot sentence, else None:
            {"source", "sentence", "gesture", "audio_url", "space", "space_id"}

        First accepted member sign speaks and marks the space for deferred
        deactivation; additional signs while the hand lingers are ignored —
        the exchange already happened and re-speaking needs re-activation.
        """
        if not gesture_name or not self.tracker.active_space_id:
            return None
        if self.pending_hand_off:
            return None  # wait for the hand to leave before closing out
        space = self.spaces.get_by_id(self.tracker.active_space_id)
        if not space or space.get("join_mode") != "one_shot":
            return None

        gesture = self.gestures.get_by_name(gesture_name)
        if not gesture:
            return None
        if gesture.get("id") not in set(space.get("gesture_ids", [])):
            return None

        shot = gesture.get("shot") or {}
        if not shot.get("ready", False) or not shot.get("sentence"):
            return None

        audio_key = shot.get("audio_key")
        payload = {
            "source": "one_shot",      # future layers: "ai", "converter", …
            "sentence": shot["sentence"],
            "gesture": gesture["name"],
            "audio_url": f"/audio/{audio_key}" if audio_key else None,
            "space": space.get("key"),
            "space_id": space["id"],
        }
        # One sign, one sentence — done, but stay scoped until the hand is
        # gone so the still-held pose can't leak into Standard mode.
        self.pending_hand_off = True
        return payload

    def flush_hand_off(self) -> bool:
        """Finish the exchange once no hands are visible: deactivate the
        space. The pipeline clears the buffer alongside this call."""
        if not self.pending_hand_off:
            return False
        self.tracker.deactivate()
        self.pending_hand_off = False
        return True

    def on_reset(self) -> None:
        """Hard reset: drop any pending hand-off immediately."""
        self.pending_hand_off = False
