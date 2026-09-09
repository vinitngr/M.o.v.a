import cv2
import sys
from vision_engine import VisionEngine
from math_engine import extract_features, extract_two_hand_features, average_feature_sets
from gesture_manager import GestureManager


def main():
    print("=== MOVA Gesture Registration ===\n")
    gesture_name = input("Enter the name of the gesture to register: ").strip()
    if not gesture_name:
        print("Invalid name. Exiting.")
        sys.exit(0)

    hand_mode = input("How many hands? (1 or 2) [default: 1]: ").strip()
    hand_count = 2 if hand_mode == "2" else 1

    # Initialize engines
    vision = VisionEngine()
    manager = GestureManager(filepath="gestures.json")

    # Adapter Layer: Webcam (swappable in the future)
    cap = cv2.VideoCapture(0)

    print(f"\nRecording '{gesture_name}' ({hand_count}-hand gesture)")
    print("Instructions:")
    print("  - Hold your pose steady in front of the camera.")
    print("  - Press 'r' to capture a sample (do this 5-10 times with slight variation).")
    print("  - Press 's' to SAVE (averages all captures into one clean template).")
    print("  - Press 'q' to quit without saving.\n")

    captured_features = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)

        # 1. Vision Layer
        results = vision.process_frame(frame)

        # Draw for feedback
        display_frame = vision.draw_landmarks(frame.copy(), results)

        # Status bar
        cv2.putText(display_frame, f"Recording: {gesture_name} ({hand_count}H)",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display_frame, f"Samples captured: {len(captured_features)}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(display_frame, "'r' capture | 's' save | 'q' quit",
                    (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.imshow("MOVA - Registration", display_frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            print("Quit without saving.")
            break

        elif key == ord('r'):
            if not results.hand_landmarks:
                print("[WARNING] No hands detected!")
                continue

            detected_hands = len(results.hand_landmarks)

            if hand_count == 1:
                if detected_hands >= 1:
                    pts = [[lm.x, lm.y, lm.z] for lm in results.hand_landmarks[0]]
                    features = extract_features(pts)
                    captured_features.append(features)
                    print(f"  [+] Captured sample #{len(captured_features)}")
                else:
                    print("[WARNING] Need at least 1 hand visible!")

            elif hand_count == 2:
                if detected_hands >= 2:
                    # Determine left/right using handedness
                    left_pts = None
                    right_pts = None
                    for i, handedness in enumerate(results.handedness):
                        label = handedness[0].category_name
                        pts = [[lm.x, lm.y, lm.z] for lm in results.hand_landmarks[i]]
                        if label == "Left":
                            left_pts = pts
                        else:
                            right_pts = pts

                    if left_pts and right_pts:
                        features = extract_two_hand_features(left_pts, right_pts)
                        captured_features.append(features)
                        print(f"  [+] Captured sample #{len(captured_features)} (2 hands)")
                    else:
                        print("[WARNING] Could not identify both Left and Right hands!")
                else:
                    print(f"[WARNING] Need 2 hands visible, detected {detected_hands}!")

        elif key == ord('s'):
            if not captured_features:
                print("[ERROR] No samples captured yet! Press 'r' first.")
                continue

            # Average all captures into one clean template
            averaged = average_feature_sets(captured_features)
            manager.add_gesture(gesture_name, averaged, hand_count)
            print(f"\n[SUCCESS] Saved '{gesture_name}' from {len(captured_features)} samples "
                  f"({len(averaged)} features).")
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
