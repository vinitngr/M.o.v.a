"""Live webcam preview with a grayscale relative-depth view."""

from pathlib import Path
import time

import cv2
import numpy as np
import onnxruntime as ort


EXPERIMENT_DIR = Path(__file__).resolve().parent
MODEL_PATH = EXPERIMENT_DIR / "models" / "depth_anything_v2_small_quantized.onnx"
CAPTURES_DIR = EXPERIMENT_DIR / "captures"
INPUT_SIZE = 518

# Standard ImageNet normalization used by the Depth Anything image encoder.
IMAGE_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGE_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def prepare_input(frame_bgr):
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(frame_rgb, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_AREA)
    image = resized.astype(np.float32) / 255.0
    image = (image - IMAGE_MEAN) / IMAGE_STD
    image = np.transpose(image, (2, 0, 1))
    return image[None, ...].astype(np.float32)


def extract_depth(output):
    depth = np.asarray(output)
    depth = np.squeeze(depth)

    # The exported model normally returns HxW after squeeze. This fallback
    # keeps the preview usable if the output includes a singleton channel.
    if depth.ndim == 3:
        depth = depth[0]
    if depth.ndim != 2:
        raise RuntimeError(f"Unexpected depth output shape: {depth.shape}")

    depth = np.nan_to_num(depth, nan=0.0, posinf=0.0, neginf=0.0)
    depth_min = float(depth.min())
    depth_max = float(depth.max())
    if depth_max - depth_min < 1e-6:
        normalized = np.zeros_like(depth, dtype=np.uint8)
    else:
        normalized = ((depth - depth_min) / (depth_max - depth_min) * 255.0).astype(np.uint8)
    return normalized


def add_label(image, label):
    cv2.rectangle(image, (0, 0), (image.shape[1], 36), (20, 20, 20), -1)
    cv2.putText(
        image,
        label,
        (12, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return image


def main():
    if not MODEL_PATH.exists():
        print(f"[ERROR] Model not found: {MODEL_PATH}")
        print("Run: python download_model.py")
        return 1

    print(f"Loading ONNX model: {MODEL_PATH}")
    session = ort.InferenceSession(str(MODEL_PATH), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    print(f"Input: {input_name} {session.get_inputs()[0].shape}")
    print(f"Output: {session.get_outputs()[0].name} {session.get_outputs()[0].shape}")

    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("[ERROR] Could not open camera.")
        return 1

    CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
    frame_number = 0
    previous_time = time.perf_counter()

    print("Depth preview started. Press 'q' to quit, 's' to save a capture.")
    try:
        while True:
            success, frame = camera.read()
            if not success:
                print("[ERROR] Could not read camera frame.")
                return 1

            input_tensor = prepare_input(frame)
            raw_output = session.run(None, {input_name: input_tensor})[0]
            depth_small = extract_depth(raw_output)
            depth = cv2.resize(depth_small, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_CUBIC)

            now = time.perf_counter()
            fps = 1.0 / max(now - previous_time, 1e-6)
            previous_time = now

            camera_view = add_label(frame.copy(), f"CAMERA  |  {fps:.1f} FPS")
            depth_view = cv2.cvtColor(depth, cv2.COLOR_GRAY2BGR)
            depth_view = add_label(depth_view, "RELATIVE DEPTH")
            preview = np.hstack((camera_view, depth_view))

            cv2.imshow("MOVA - Depth Preview", preview)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("s"):
                frame_number += 1
                cv2.imwrite(str(CAPTURES_DIR / f"camera_{frame_number:04d}.png"), camera_view)
                cv2.imwrite(str(CAPTURES_DIR / f"depth_{frame_number:04d}.png"), depth)
                print(f"Saved capture #{frame_number} to {CAPTURES_DIR}")
    finally:
        camera.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
