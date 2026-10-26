"""MOVA Sign Space tracker.

Owns the which-space-is-active state machine and computes the gesture
candidate list for scoped matching (docs/005-spell-mode.md):

- standard: all "normal" gestures + every space's entry/toggle (+ exit) signs
- space X:  X's members + X's control signs only

Because scoping happens before scoring, a letter sign can never collide with
a normal keyword — group-vs-group competition is eliminated at the source.
"""

from typing import Dict, Any, List, Optional

# Roles that stay scoreable outside any space.
CONTROL_ROLES = {"space-entry", "space-exit", "space-toggle"}


class SpaceTracker:
    def __init__(self, gesture_store, space_store):
        self.gestures = gesture_store
        self.spaces = space_store
        self.active_space_id: Optional[str] = None
        self.space_buffer: List[str] = []
        # name -> (id, role); rebuilt lazily
        self._role_by_name: Dict[str, Dict[str, str]] = {}

    # ------------------------------------------------------------------ index

    def refresh(self) -> None:
        """Rebuild the name -> {id, role} map from the gesture store."""
        self._role_by_name = {
            g["name"]: {"id": g["id"], "role": g.get("role", "normal")}
            for g in self.gestures.get_all()
            if g.get("name")
        }

    def _space_of_gesture_id(self, gesture_id: str) -> Optional[Dict[str, Any]]:
        return self.spaces.space_of_gesture(gesture_id)

    def _info(self, gesture_name: str) -> Optional[Dict[str, str]]:
        return self._role_by_name.get(gesture_name)

    # ------------------------------------------------------------- candidates

    def scoped_candidates(self) -> List[Dict[str, Any]]:
        """Gesture list handed to score_gestures for the current mode."""
        self.refresh()
        if self.active_space_id:
            space = self.spaces.get_by_id(self.active_space_id)
            if space is None:
                self.active_space_id = None
                return self._standard_candidates()
            member_ids = set(space.get("gesture_ids", []))
            return [g for g in self.gestures.get_all() if g.get("id") in member_ids]
        return self._standard_candidates()

    def _standard_candidates(self) -> List[Dict[str, Any]]:
        return [g for g in self.gestures.get_all() if g.get("role", "normal") in {"normal"} | CONTROL_ROLES]

    # ----------------------------------------------------------- state machine

    def on_accepted(self, gesture_name: Optional[str]) -> Optional[Dict[str, Any]]:
        """Feed an 'accepted' buffer event. Returns a space token dict when a
        space window closed and its letters flushed, else None."""
        if not gesture_name:
            return None
        self.refresh()
        info = self._info(gesture_name)
        if info is None:
            return None
        role = info["role"]

        if role == "space-sign":
            space = self._space_of_gesture_id(info["id"])
            if space and self.active_space_id == space["id"]:
                if space.get("join_mode", "words") == "spell":
                    self.space_buffer.append(gesture_name)
                else:
                    # Words mode: every accepted member is its own word
                    # token, emitted immediately — same packaging as a
                    # normal gesture, only namespaced.
                    return {
                        "type": "space",
                        "space": space.get("key"),
                        "space_id": space["id"],
                        "mode": "words",
                        "letters": [gesture_name],
                    }
            return None

        if role in CONTROL_ROLES:
            space = self._space_of_gesture_id(info["id"])
            if space is None:
                return None
            sid = space["id"]

            if role == "space-entry":
                if not self.active_space_id:
                    self._activate(sid)
                return None

            if role == "space-toggle":
                if self.active_space_id == sid:
                    return self._flush()
                if not self.active_space_id:
                    self._activate(sid)
                return None

            if role == "space-exit":
                if self.active_space_id == sid:
                    return self._flush()
                return None

        return None

    def on_completed(self) -> Optional[Dict[str, Any]]:
        """The buffer fired 'completed' (inactivity close). If a space was
        open it closes here too and flushes its letters."""
        if self.active_space_id:
            return self._flush()
        return None

    def on_reset(self) -> None:
        """Hard reset (client 'reset' action): back to standard, no token."""
        self.active_space_id = None
        self.space_buffer = []

    def deactivate(self) -> None:
        """Leave the active space silently (one-shot speech already spoke)."""
        self.active_space_id = None
        self.space_buffer = []

    def _activate(self, space_id: str) -> None:
        self.active_space_id = space_id
        self.space_buffer = []

    def _flush(self) -> Optional[Dict[str, Any]]:
        if not self.active_space_id:
            self.space_buffer = []
            return None
        space = self.spaces.get_by_id(self.active_space_id)
        token = None
        if space and self.space_buffer and space.get("join_mode", "words") == "spell":
            token = {
                "type": "space",
                "space": space.get("key"),
                "space_id": space["id"],
                "mode": "spell",
                "letters": list(self.space_buffer),
            }
        elif space and space.get("join_mode") == "words":
            # Words-mode members were already emitted per acceptance; the
            # bucket holds nothing to flush.
            token = None
        self.active_space_id = None
        self.space_buffer = []
        return token

    # ------------------------------------------------------------------- state

    def get_state(self) -> Dict[str, Any]:
        space = self.spaces.get_by_id(self.active_space_id) if self.active_space_id else None
        return {
            "active_space": space["key"] if space else None,
            "space_buffer": list(self.space_buffer),
        }
