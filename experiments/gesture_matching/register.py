import cv2
import sys
from vision_engine import VisionEngine
from math_engine import extract_features
from gesture_manager import GestureManager

def main():
    print("--- MOVA Gesture Registration ---")
    gesture_name = input("Enter the name of the gesture to register: ").strip()
    if not gesture_name:
        print("Invalid name. Exiting.")
        sys.exit(0)

    # Initialize our decoupled engines
    vision = VisionEngine()
    manager = GestureManager(filepath="gestures.json")
    
    # Adapter Layer: We use the laptop webcam here, but the Vision Engine doesn't know or care.
    cap = cv2.VideoCapture(0)
    
    print(f"\nRecording '{gesture_name}'...")
    print("Instructions: Hold your pose in front of the camera, then press 'r' to capture.")
    print("Press 'q' to quit when finished.\n")
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        frame = cv2.flip(frame, 1) # Mirror image for easier user interaction
        
        # 1. Vision Layer: Pass frame, get data
        results = vision.process_frame(frame)
        
        # Draw for visual feedback
        display_frame = vision.draw_landmarks(frame.copy(), results)
        cv2.putText(display_frame, f"Recording: {gesture_name}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display_frame, "Press 'r' to capture | 'q' to quit", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                    
        cv2.imshow("Registration UI", display_frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            if results.hand_landmarks:
                # For Phase 1, we capture the first hand detected in the frame
                hand_landmarks = results.hand_landmarks[0]
                
                # Extract raw (x,y,z) points
                pts_3d = [[lm.x, lm.y, lm.z] for lm in hand_landmarks]
                
                # 2. Math Layer: Convert XYZ to invariant features
                features = extract_features(pts_3d)
                
                # 3. Storage Layer: Save to JSON
                manager.add_gesture(gesture_name, features)
                print(f"[SUCCESS] Saved 1 template for '{gesture_name}'!")
            else:
                print("[WARNING] No hands detected! Make sure your hand is visible.")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
