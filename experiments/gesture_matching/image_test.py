"""Run gesture matching on one image and save an annotated copy.

Usage:
    python image_test.py path/to/image.png [gesture-json]
"""

import sys
from pathlib import Path

import cv2

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from gesture_manager import GestureManager
from live_test import draw_score_leaderboard
from math_engine import extract_features, extract_two_hand_features, score_against_templates
from vision_engine import VisionEngine


def output_path_for(image_path):
    return image_path.with_name(f"{image_path.stem}_output{image_path.suffix}")


def main():
    if len(sys.argv) not in (2, 3):
        print("Usage: python image_test.py <image-file> [gesture-json]")
        return 2

    image_path = Path(sys.argv[1]).expanduser().resolve()
    if not image_path.is_file():
        print(f"[ERROR] Image not found: {image_path}")
        return 1

    frame = cv2.imread(str(image_path))
    if frame is None:
        print(f"[ERROR] Could not read image: {image_path}")
        return 1

    # By default this behaves like live_test.py and uses the main database.
    # Pass a separate JSON path when testing image-created templates.
    gesture_database = (
        Path(sys.argv[2]).expanduser().resolve()
        if len(sys.argv) == 3
        else SCRIPT_DIR / "gestures.json"
    )
    manager = GestureManager(filepath=str(gesture_database))
    stored_gestures = manager.data.get("gestures", [])
    if not stored_gestures:
        print(f"[ERROR] No gestures found in {gesture_database}")
        print("Run register.py or register_image_signs.py first.")
        return 1

    single_hand_gestures = [
        gesture for gesture in stored_gestures
        if gesture.get("hand_count", 1) == 1
    ]
    two_hand_gestures = [
        gesture for gesture in stored_gestures
        if gesture.get("hand_count", 1) == 2
    ]

    vision = VisionEngine(model_asset_path=str(SCRIPT_DIR / "hand_landmarker.task"))
    results = vision.process_frame(frame)
    annotated = vision.draw_landmarks(frame.copy(), results)
    hand_count = len(results.hand_landmarks or [])
    all_scores = {}

    # Match each detected hand against single-hand templates.
    for hand_landmarks in results.hand_landmarks or []:
        points = [[landmark.x, landmark.y, landmark.z] for landmark in hand_landmarks]
        live_features = extract_features(points)
        hand_scores = score_against_templates(live_features, single_hand_gestures)
        for name, score in hand_scores.items():
            all_scores[name] = max(score, all_scores.get(name, 0))

    # Match the pair when both left and right hands are available.
    if two_hand_gestures and hand_count >= 2:
        left_points = None
        right_points = None
        for index, handedness in enumerate(results.handedness):
            label = handedness[0].category_name
            points = [
                [landmark.x, landmark.y, landmark.z]
                for landmark in results.hand_landmarks[index]
            ]
            if label == "Left":
                left_points = points
            elif label == "Right":
                right_points = points

        if left_points is not None and right_points is not None:
            live_features = extract_two_hand_features(left_points, right_points)
            pair_scores = score_against_templates(live_features, two_hand_gestures)
            for name, score in pair_scores.items():
                all_scores[name] = max(score, all_scores.get(name, 0))

    # Add a compact status label to the image.
    cv2.putText(
        annotated,
        f"Hands detected: {hand_count}",
        (15, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (0, 255, 255),
        2,
    )

    if all_scores:
        annotated = draw_score_leaderboard(
            annotated,
            dict(sorted(all_scores.items(), key=lambda item: item[1], reverse=True)),
            max(10, annotated.shape[1] - 300),
            70,
        )
    else:
        cv2.putText(
            annotated,
            "No compatible gesture match",
            (15, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2,
        )

    output_path = output_path_for(image_path)
    if not cv2.imwrite(str(output_path), annotated):
        print(f"[ERROR] Could not write output image: {output_path}")
        return 1

    print(f"Detected hands: {hand_count}")
    if all_scores:
        print("Scores:")
        for name, score in sorted(all_scores.items(), key=lambda item: item[1], reverse=True):
            print(f"  {name}: {score:.1f}%")
    print(f"Saved annotated image: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
