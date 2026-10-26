import json
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from threading import RLock


class GestureStore:    # Runtime roles. "normal" = standard matching pool; everything else
    # belongs to a sign space (see docs/005-spell-mode.md).
    ROLES = {"normal", "space-sign", "space-entry", "space-exit", "space-toggle"}

    def __init__(self, filepath: str = "data/gestures.json"):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        # `load()` may initialize a new file via `save()`.  Both operations
        # protect shared state, so this must allow the same thread to re-enter.
        self._lock = RLock()
        self._data = {"schema_version": 2, "gestures": []}
        self.load()

    def load(self) -> None:
        with self._lock:
            if self.filepath.exists():
                with open(self.filepath, 'r') as f:
                    self._data = json.load(f)
                # Preview images used to be embedded in JSON. Discard those
                # bulky legacy values; previews are now stored as image files.
                removed_legacy_previews = False
                for gesture in self._data.get("gestures", []):
                    if gesture.pop("preview_image", None) is not None:
                        removed_legacy_previews = True
                if removed_legacy_previews:
                    self.save()
                # Backfill sign-space roles for gestures saved before this
                # feature existed. Migration is idempotent.
                missing_roles = [
                    g for g in self._data.get("gestures", [])
                    if g.get("role") not in self.ROLES
                ]
                if missing_roles:
                    for g in missing_roles:
                        g["role"] = "normal"
                    self.save()
            else:
                self._data = {"schema_version": 2, "gestures": []}
                self.save()

    def save(self) -> None:
        with self._lock:
            with open(self.filepath, 'w') as f:
                json.dump(self._data, f, indent=2)

    def get_all(self) -> List[Dict[str, Any]]:
        with self._lock:
            return self._data.get("gestures", [])

    def get_by_role(self, roles: Any) -> List[Dict[str, Any]]:
        """Return gestures whose role is in `roles` (str or iterable)."""
        wanted = {roles} if isinstance(roles, str) else set(roles)
        with self._lock:
            return [g for g in self._data.get("gestures", []) if g.get("role") in wanted]

    def get_by_id(self, gesture_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for g in self._data.get("gestures", []):
                if g.get("id") == gesture_id:
                    return g
        return None

    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for g in self._data.get("gestures", []):
                if g.get("name") == name:
                    return g
        return None

    def create(self, name: str, landmarks: List[List[float]], hand_count: int, 
               features: List[float], labels: List[str] = None,
               preview_path: Optional[str] = None,
               gesture_id: Optional[str] = None,
               handedness: Optional[Any] = None,
               role: str = "normal") -> Dict[str, Any]:
        with self._lock:
            gesture = {
                "id": gesture_id or str(uuid.uuid4())[:8],
                "name": name,
                "role": role if role in self.ROLES else "normal",
                "hand_count": hand_count,
                "handedness": handedness,
                "feature_version": 2,
                "features": features,
                "landmarks": landmarks,
                "labels": labels or [],
                "preview_path": preview_path,
                "created_at": __import__('time').time()
            }
            self._data.setdefault("gestures", []).append(gesture)
            self.save()
            return gesture

    def update(self, gesture_id: str, name: str = None, labels: List[str] = None) -> Optional[Dict[str, Any]]:
        with self._lock:
            for g in self._data.get("gestures", []):
                if g.get("id") == gesture_id:
                    if name is not None:
                        g["name"] = name
                    if labels is not None:
                        g["labels"] = labels
                    g["updated_at"] = __import__('time').time()
                    self.save()
                    return g
        return None

    def delete(self, gesture_id: str) -> bool:
        with self._lock:
            gestures = self._data.get("gestures", [])
            for i, g in enumerate(gestures):
                if g.get("id") == gesture_id:
                    gestures.pop(i)
                    self.save()
                    return True
        return False

    def set_role(self, gesture_id: str, role: str) -> bool:
        with self._lock:
            for g in self._data.get("gestures", []):
                if g.get("id") == gesture_id:
                    g["role"] = role if role in self.ROLES else "normal"
                    g["updated_at"] = __import__('time').time()
                    self.save()
                    return True
        return False


_store_instance = None

def get_store() -> GestureStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = GestureStore()
    return _store_instance
