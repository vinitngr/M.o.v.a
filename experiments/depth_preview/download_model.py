"""Download the quantized Depth Anything V2 Small ONNX model."""

from pathlib import Path
from urllib.request import Request, urlopen


MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODEL_DIR / "depth_anything_v2_small_quantized.onnx"
MODEL_URL = (
    "https://huggingface.co/onnx-community/depth-anything-v2-small/"
    "resolve/main/onnx/model_quantized.onnx?download=true"
)


def main():
    if MODEL_PATH.exists():
        print(f"Model already exists: {MODEL_PATH}")
        return 0

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading model to {MODEL_PATH}")

    request = Request(MODEL_URL, headers={"User-Agent": "MOVA-depth-preview"})
    with urlopen(request) as response, MODEL_PATH.open("wb") as output:
        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            downloaded += len(chunk)
            if total:
                percent = downloaded * 100 / total
                print(f"\rProgress: {percent:5.1f}%", end="", flush=True)

    print(f"\nSaved {MODEL_PATH} ({downloaded / 1024 / 1024:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
