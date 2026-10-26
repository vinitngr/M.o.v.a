"""MOVA Sign Space storage.

A sign space (docs/005-spell-mode.md) is a user-defined namespace of
gestures: while the space is active, matching is scoped to its members only.
Membership is by gesture id; the `key` field is display sugar only and is
never parsed at runtime.

Signup ships with one built-in space, Spell Mode, for fingerspelling words.
"""

import json
import re
import time
import uuid
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional, Any

CONTROL_ROLES = {"space-entry", "space-exit", "space-toggle"}


def make_key(name: str) -> str:
    """Human-readable machine key from a space name, e.g. "My Colors" -> MY_COLORS."""
    key = re.sub(r"[^A-Za-z0-9]+", "_", (name or "").strip().upper()).strip("_")
    return key or "SPACE"


class SignSpaceStore:
    def __init__(self, filepath: str = "data/sign_spaces.json"):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._data = {"schema_version": 1, "spaces": []}
        self.load()

    def load(self) -> None:
        with self._lock:
            if self.filepath.exists():
                with open(self.filepath, "r") as f:
                    self._data = json.load(f)
            else:
                self.save()
            # Backfill join_mode for spaces created before this field existed.
            migrated = False
            for s in self._data.setdefault("spaces", []):
                if s.get("join_mode") not in ("spell", "words"):
                    s["join_mode"] = "words"
                    migrated = True
            if migrated:
                self.save()

    def save(self) -> None:
        with self._lock:
            with open(self.filepath, "w") as f:
                json.dump(self._data, f, indent=2)

    def get_all(self) -> List[Dict[str, Any]]:
        with self._lock:
            return self._data.get("spaces", [])

    def _get_unlocked(self, space_id: str) -> Optional[Dict[str, Any]]:
        for s in self._data.get("spaces", []):
            if s.get("id") == space_id:
                return s
        return None

    def get_by_id(self, space_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._get_unlocked(space_id)

    def get_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for s in self._data.get("spaces", []):
                if s.get("key") == key:
                    return s
        return None

    def create(self, name: str, toggle_mode: str = "shared", join_mode: str = "words") -> Optional[Dict[str, Any]]:
        with self._lock:
            key = make_key(name)
            if self.get_by_key(key):
                return None
            space = {
                "id": f"spc_{str(uuid.uuid4())[:8]}",
                "key": key,
                "name": name,
                "join_mode": join_mode if join_mode in ("spell", "words") else "words",
                "toggle_mode": toggle_mode if toggle_mode in ("shared", "separate") else "shared",
                "created_at": time.time(),
                "gesture_ids": [],
            }
            self._data.setdefault("spaces", []).append(space)
            self.save()
            return space

    def update(
        self,
        space_id: str,
        name: Optional[str] = None,
        toggle_mode: Optional[str] = None,
        join_mode: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            space = self._get_unlocked(space_id)
            if not space:
                return None
            if name is not None:
                new_key = make_key(name)
                clash = self.get_by_key(new_key)
                if clash and clash["id"] != space_id:
                    return None
                space["name"] = name
                space["key"] = new_key
            if toggle_mode in ("shared", "separate"):
                space["toggle_mode"] = toggle_mode
            if join_mode in ("spell", "words"):
                space["join_mode"] = join_mode
            space["updated_at"] = time.time()
            self.save()
            return space

    def add_member(self, space_id: str, gesture_id: str, control: Optional[str] = None) -> bool:
        """Attach a gesture. `control` defaults to a plain member; "entry",
        "exit" or "toggle" mark the gesture as the space's control sign."""
        with self._lock:
            space = self._get_unlocked(space_id)
            if not space or gesture_id in space["gesture_ids"]:
                return False
            space["gesture_ids"].append(gesture_id)
            space["updated_at"] = time.time()
            self.save()
            return True

    def remove_member(self, space_id: str, gesture_id: str) -> bool:
        with self._lock:
            space = self._get_unlocked(space_id)
            if not space or gesture_id not in space["gesture_ids"]:
                return False
            space["gesture_ids"].remove(gesture_id)
            space["updated_at"] = time.time()
            self.save()
            return True

    def delete(self, space_id: str) -> List[str]:
        """Delete any space, returning its member gesture ids so callers can
        fall their roles back to `normal`. There are no protected defaults."""
        with self._lock:
            spaces = self._data.get("spaces", [])
            for i, s in enumerate(spaces):
                if s.get("id") == space_id:
                    spaces.pop(i)
                    self.save()
                    return list(s.get("gesture_ids", []))
            return []

    def space_of_gesture(self, gesture_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for s in self._data.get("spaces", []):
                if gesture_id in s.get("gesture_ids", []):
                    return s
        return None

    def get_state(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "id": s["id"],
                    "key": s["key"],
                    "name": s["name"],
                    "join_mode": s.get("join_mode", "words"),
                    "toggle_mode": s.get("toggle_mode", "shared"),
                    "member_count": len(s.get("gesture_ids", [])),
                    "gesture_ids": list(s.get("gesture_ids", [])),
                }
                for s in self._data.get("spaces", [])
            ]


_space_store_instance = None

def get_space_store() -> SignSpaceStore:
    global _space_store_instance
    if _space_store_instance is None:
        _space_store_instance = SignSpaceStore()
    return _space_store_instance
