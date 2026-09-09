import json
import os


class GestureManager:
    """
    Handles loading and saving of pre-computed gesture features to JSON.
    """
    def __init__(self, filepath="gestures.json"):
        self.filepath = filepath
        self.data = {"gestures": []}
        self.load()

    def load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r') as f:
                self.data = json.load(f)

    def save(self):
        with open(self.filepath, 'w') as f:
            json.dump(self.data, f, indent=2)

    def add_gesture(self, name, features, hand_count=1):
        """
        Adds a single averaged gesture template and saves to disk.
        """
        self.data["gestures"].append({
            "name": name,
            "hand_count": hand_count,
            "features": features
        })
        self.save()

    def get_gesture_names(self):
        """
        Returns a list of unique gesture names in the database.
        """
        return list(set(g["name"] for g in self.data.get("gestures", [])))
