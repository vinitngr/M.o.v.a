import cv2
import time
from vision_engine import VisionEngine
from math_engine import extract_features, extract_two_hand_features, score_against_templates
from gesture_manager import GestureManager


# ---- UI Drawing Helpers ----

def draw_score_leaderboard(frame, scores, x_offset, y_start):
    """
    Draws the gesture score leaderboard on the right side of the frame.
    """
    panel_w = 280
    panel_h = 40 + len(scores) * 35
    overlay = frame.copy()
    cv2.rectangle(overlay, (x_offset - 10, y_start - 30),
                  (x_offset + panel_w, y_start + panel_h), (30, 30, 30), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    cv2.putText(frame, "GESTURE SCORES", (x_offset, y_start),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    for i, (name, score) in enumerate(scores.items()):
        y = y_start + 35 + i * 35

        if score >= 70:
            color = (0, 255, 0)
        elif score >= 40:
            color = (0, 255, 255)
        else:
            color = (0, 0, 255)

        bar_width = int(score / 100 * 150)
        cv2.rectangle(frame, (x_offset, y + 5), (x_offset + bar_width, y + 20), color, -1)
        cv2.rectangle(frame, (x_offset, y + 5), (x_offset + 150, y + 20), (100, 100, 100), 1)

        label = f"{name}: {score:.1f}%"
        cv2.putText(frame, label, (x_offset + 160, y + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    return frame


def draw_stats_panel(frame, fps, latency_ms, hand_count):
    """
    Draws FPS, latency, and hand count on the top-left.
    """
    overlay = frame.copy()
    cv2.rectangle(overlay, (5, 5), (250, 100), (30, 30, 30), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    cv2.putText(frame, f"FPS: {fps:.1f}", (15, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.putText(frame, f"Latency: {latency_ms:.1f}ms", (15, 55),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    cv2.putText(frame, f"Hands: {hand_count}", (15, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    return frame


# ---- Main ----

def main():
    print("=== MOVA Live Gesture Testing ===\n")

    # Load stored gesture templates (one-time cost)
    manager = GestureManager(filepath="gestures.json")
    stored_gestures = manager.data.get("gestures", [])

    if not stored_gestures:
        print("[ERROR] No gestures found in gestures.json!")
        print("Run register.py first to record some gestures.")
        return

    unique_names = set(g["name"] for g in stored_gestures)
    print(f"Loaded {len(stored_gestures)} templates: {', '.join(unique_names)}")

    # Separate single-hand and two-hand templates for correct matching
    single_hand_gestures = [g for g in stored_gestures if g.get("hand_count", 1) == 1]
    two_hand_gestures = [g for g in stored_gestures if g.get("hand_count", 1) == 2]

    # Initialize engines
    vision = VisionEngine()

    # Adapter Layer: Webcam (swappable)
    cap = cv2.VideoCapture(0)

    print("Press 'q' to quit.\n")

    prev_time = time.time()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        frame_h, frame_w = frame.shape[:2]

        # ---- Pipeline Start ----
        t_start = time.time()

        results = vision.process_frame(frame)
        display_frame = vision.draw_landmarks(frame.copy(), results)

        hand_count = 0
        all_scores = {}

        if results.hand_landmarks:
            hand_count = len(results.hand_landmarks)

            # Score single-hand gestures (each hand independently)
            if single_hand_gestures:
                for hand_landmarks in results.hand_landmarks:
                    pts = [[lm.x, lm.y, lm.z] for lm in hand_landmarks]
                    live_features = extract_features(pts)
                    hand_scores = score_against_templates(live_features, single_hand_gestures)

                    for name, score in hand_scores.items():
                        if name not in all_scores or score > all_scores[name]:
                            all_scores[name] = score

            # Score two-hand gestures (if both hands detected)
            if two_hand_gestures and hand_count >= 2:
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
                    live_features = extract_two_hand_features(left_pts, right_pts)
                    two_scores = score_against_templates(live_features, two_hand_gestures)
                    for name, score in two_scores.items():
                        if name not in all_scores or score > all_scores[name]:
                            all_scores[name] = score

        # ---- Pipeline End ----
        t_end = time.time()
        latency_ms = (t_end - t_start) * 1000

        current_time = time.time()
        fps = 1.0 / (current_time - prev_time) if (current_time - prev_time) > 0 else 0
        prev_time = current_time

        # ---- Draw UI ----
        display_frame = draw_stats_panel(display_frame, fps, latency_ms, hand_count)

        if all_scores:
            leaderboard_x = frame_w - 300
            display_frame = draw_score_leaderboard(display_frame, all_scores, leaderboard_x, 40)

        if hand_count == 0:
            cv2.putText(display_frame, "No hands detected",
                        (frame_w // 2 - 120, frame_h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        cv2.imshow("MOVA - Live Gesture Test", display_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
