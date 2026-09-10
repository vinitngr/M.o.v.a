"""Register one gesture template from every image in signs/.

The filename stem becomes the gesture name:

    signs/thumbs_up.png  ->  thumbs_up

Usage:
    python register_image_signs.py path/to/images
    python register_image_signs.py path/to/images path/to/output.json
"""

import json
import sys
from pathlib import Path

import cv2

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from gesture_manager import SCHEMA_VERSION
from math_engine import extract_features, extract_two_hand_features
from vision_engine import VisionEngine


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def points_from_landmarks(hand_landmarks):
    return [[landmark.x, landmark.y, landmark.z] for landmark in hand_landmarks]


def extract_image_gesture(image_path, vision):
    frame = cv2.imread(str(image_path))
    if frame is None:
        raise ValueError("could not read image")

    results = vision.process_frame(frame)
    hands = results.hand_landmarks or []
    if not hands:
        raise ValueError("no hand detected")

    if len(hands) == 1:
        return 1, extract_features(points_from_landmarks(hands[0]))

    left_points = None
    right_points = None
    for index, handedness in enumerate(results.handedness):
        label = handedness[0].category_name
        points = points_from_landmarks(hands[index])
        if label == "Left":
            left_points = points
        elif label == "Right":
            right_points = points

    if left_points is None or right_points is None:
        raise ValueError("two hands detected, but left/right labels were unavailable")

    return 2, extract_two_hand_features(left_points, right_points)


def main():
    if len(sys.argv) not in (2, 3):
        print("Usage: python register_image_signs.py <image-folder> [output-json]")
        return 2

    signs_dir = Path(sys.argv[1]).expanduser().resolve()
    output_path = (
        Path(sys.argv[2]).expanduser().resolve()
        if len(sys.argv) > 2
        else signs_dir / "image_gestures.json"
    )

    if not signs_dir.is_dir():
        print(f"[ERROR] Signs directory not found: {signs_dir}")
        return 1

    image_paths = sorted(
        path for path in signs_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not image_paths:
        print(f"[ERROR] No supported images found in {signs_dir}")
        return 1

    vision = VisionEngine(model_asset_path=str(SCRIPT_DIR / "hand_landmarker.task"))
    gestures = []
    failures = []

    for image_path in image_paths:
        try:
            hand_count, features = extract_image_gesture(image_path, vision)
            gestures.append({
                "name": image_path.stem,
                "hand_count": hand_count,
                "feature_version": SCHEMA_VERSION,
                "features": features,
            })
            print(f"[OK] {image_path.name} -> {image_path.stem} ({hand_count} hand(s), {len(features)} features)")
        except ValueError as error:
            failures.append((image_path.name, str(error)))
            print(f"[SKIP] {image_path.name}: {error}")

    if not gestures:
        print("[ERROR] No usable gesture images were registered.")
        return 1

    data = {
        "schema_version": SCHEMA_VERSION,
        "source": "signs",
        "gestures": gestures,
    }
    output_path.write_text(json.dumps(data, indent=2) + "\n")

    print(f"\nSaved {len(gestures)} image gesture(s) to: {output_path}")
    if failures:
        print(f"Skipped {len(failures)} image(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
