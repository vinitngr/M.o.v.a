import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class VisionEngine:
    """
    A decoupled vision class using the modern MediaPipe Tasks API.
    """
    def __init__(self, model_asset_path='hand_landmarker.task', num_hands=2):
        base_options = python.BaseOptions(model_asset_path=model_asset_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=num_hands,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5)
        self.detector = vision.HandLandmarker.create_from_options(options)

    def process_frame(self, frame_bgr):
        """
        Takes a raw OpenCV BGR frame.
        Returns the MediaPipe detection result.
        """
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        
        detection_result = self.detector.detect(mp_image)
        return detection_result

    def draw_landmarks(self, frame_bgr, detection_result):
        """
        Utility to draw the skeleton on a frame for UI feedback.
        """
        if detection_result.hand_landmarks:
            for hand_landmarks in detection_result.hand_landmarks:
                # Draw joints
                for lm in hand_landmarks:
                    x = int(lm.x * frame_bgr.shape[1])
                    y = int(lm.y * frame_bgr.shape[0])
                    cv2.circle(frame_bgr, (x, y), 5, (0, 255, 0), -1)
                
                # Draw skeleton lines
                connections = [
                    (0,1), (1,2), (2,3), (3,4), # Thumb
                    (0,5), (5,6), (6,7), (7,8), # Index
                    (5,9), (9,10), (10,11), (11,12), # Middle
                    (9,13), (13,14), (14,15), (15,16), # Ring
                    (13,17), (17,18), (18,19), (19,20), # Pinky
                    (0,17) # Wrist to pinky base
                ]
                for p1, p2 in connections:
                    lm1 = hand_landmarks[p1]
                    lm2 = hand_landmarks[p2]
                    x1, y1 = int(lm1.x * frame_bgr.shape[1]), int(lm1.y * frame_bgr.shape[0])
                    x2, y2 = int(lm2.x * frame_bgr.shape[1]), int(lm2.y * frame_bgr.shape[0])
                    cv2.line(frame_bgr, (x1, y1), (x2, y2), (255, 0, 0), 2)
        return frame_bgr
