# Live Depth Preview

This experiment opens the webcam and displays two views side by side:

```text
┌──────────────────────┬──────────────────────┐
│ Original camera      │ Relative depth       │
│ frame                │ grayscale map        │
└──────────────────────┴──────────────────────┘
```

It uses the quantized Depth Anything V2 Small model through CPU ONNX Runtime.
It does not require PyTorch, CUDA, Transformers, or a GPU.

The depth image is monocular relative depth, not measured distance in meters.
It shows the model's estimate of nearer and farther regions in the scene.

## Install

Activate the project virtual environment and install the runtime dependencies:

```bash
python -m pip install numpy opencv-python onnxruntime
```

The ONNX Runtime package is the CPU package. Do not install
`onnxruntime-gpu` for this experiment.

## Download the model

From this directory, run:

```bash
python download_model.py
```

The quantized model is downloaded once to:

```text
experiments/depth_preview/models/depth_anything_v2_small_quantized.onnx
```

## Run the preview

```bash
python depth_preview.py
```

Controls:

- `q` — quit
- `s` — save the current camera frame and depth map to `captures/`

The first inference can take longer while ONNX Runtime initializes. Later
frames are processed continuously on the CPU.

## Depth display

The model output is normalized independently for each frame into grayscale:

```text
dark pixels   → lower relative depth value
bright pixels → higher relative depth value
```

This is useful for seeing the depth structure, but it is not a calibrated
measurement of physical distance.
