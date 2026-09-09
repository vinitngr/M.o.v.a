# FPP Hand Gesture Matching Experiment (Version 2)

This experiment detects hand landmarks from a webcam frame, converts them into
normalized geometric features, and compares them with registered gesture
templates.

```text
Webcam frame
     │
     ▼
MediaPipe Hands
     │  21 landmarks per hand + handedness
     ▼
Feature extraction
     │  normalized shape, palm orientation, finger profile
     ▼
Template matching
     │  cosine similarity + weighted feature scores
     ▼
Gesture score leaderboard
```

## 1. Feature representation

The matcher does not compare raw webcam coordinates. Each hand is first
translated so that the wrist is at the origin and scaled by the greatest
wrist-to-landmark distance.

```text
                         Version 2 feature vector
 ┌──────────────────────┬───────────────┬──────────────────────────────┐
 │ Normalized landmarks │ Palm normal   │ Finger extension profile      │
 │ 21 × 3 = 63 values   │ 3 values      │ 5 values                     │
 │ Hand shape            │ Orientation   │ Thumb · Index · Middle       │
 │                      │               │ Ring · Pinky                 │
 └──────────────────────┴───────────────┴──────────────────────────────┘
                              71 values
```

### Normalized landmarks — 63 values

The 21 `(x, y, z)` landmarks are centered on the wrist (landmark `0`) and
divided by the furthest distance from the wrist. This makes the hand shape
comparable when the hand moves or changes distance from the camera.

### Palm normal — 3 values

The palm orientation is calculated using the wrist (`0`), index MCP (`5`), and
pinky MCP (`17`):

```text
                 Index MCP (5)
                       ●
                      / \
                     /   \   cross product
                    /     \       │
             Wrist (0)──────●─────▼  Palm normal (x, y, z)
                         Pinky MCP (17)
```

### Finger extension profile — 5 values

For each finger, the fingertip-to-wrist distance is compared with the
finger's MCP-to-wrist distance. The result is clamped to `0–1`.

| Profile position | Finger | Tip landmark | MCP landmark |
|---:|---|---:|---:|
| 1 | Thumb | 4 | 2 |
| 2 | Index | 8 | 5 |
| 3 | Middle | 12 | 9 |
| 4 | Ring | 16 | 13 |
| 5 | Pinky | 20 | 17 |

This gives the matcher a direct signal for which fingers are extended instead
of relying only on the complete landmark shape.

## 2. Single-hand matching

Version 2 uses a weighted score made from the hand shape and finger profile:

```text
Single-hand score
══════════════════════════════════════════════════
Hand shape + palm orientation       60%
Finger extension profile             40%
══════════════════════════════════════════════════
Total                               100%
```

The result is shown as a percentage. If multiple templates have the same name,
the highest score is kept.

## 3. Two-hand matching

A two-hand template contains the complete feature vector for both hands plus a
normalized direction vector from the left wrist to the right wrist.

```text
Left hand (71) ────────┐
                       ├── weighted two-hand score
Right hand (71) ───────┤
                       │
Wrist direction (3) ───┘
```

| Component | Weight |
|---|---:|
| Left-hand score | 40% |
| Right-hand score | 40% |
| Left-to-right wrist direction | 20% |

The two-hand mode uses MediaPipe handedness to identify the left and right
hands before extracting the combined feature vector.

## 4. Codebase architecture

| File | Responsibility |
|---|---|
| `vision_engine.py` | Runs MediaPipe Hands and returns landmarks and handedness. |
| `math_engine.py` | Normalizes landmarks, extracts features, and calculates scores. |
| `gesture_manager.py` | Loads and saves `gestures.json`. |
| `register.py` | Captures samples and creates averaged gesture templates. |
| `live_test.py` | Runs webcam matching and displays landmarks, FPS, latency, and scores. |
| `test_math_engine.py` | Tests version 2 scoring and version 1 compatibility. |

## 5. Registering a gesture

Run this from the experiment directory:

```bash
python register.py
```

Choose a gesture name and whether it uses one or two hands. While holding the
pose, use the following keys:

```text
 r  capture one sample
 s  average captured samples and save the template
 q  quit without saving
```

Capture several steady samples with small natural variations. Registration
averages the extracted feature vectors and stores the averaged template.

## 6. Live testing

```bash
python live_test.py
```

The live test draws the detected landmarks and displays a score leaderboard.
Single-hand templates are checked against each detected hand. Two-hand
templates are checked when both a left and right hand are detected. Press `q`
to exit.

## 7. Data Storage Schema (`gestures.json`)

The database stores pre-computed features, not raw coordinates. 

```json
{
  "gestures": [
    {
      "name": "water",
      "hand_count": 1,
      "feature_version": 2,
      "features": [71 values: normalized points, palm normal, finger profile]
    },
    {
      "name": "cup_and_tray",
      "hand_count": 2,
      "feature_version": 2,
      "features": [145 values: left hand, right hand, relative wrist direction]
    }
  ]
}
```

## 8. Version compatibility

Version 1 templates remain readable:

| Template type | Version 1 | Version 2 |
|---|---:|---:|
| Single hand | 66 values | 71 values |
| Two hands | 135 values | 145 values |

Version 1 templates use the legacy shape-only cosine similarity. New
registrations use the version 2 finger profile and weighted scoring.

## 9. Running the tests

```bash
python -m unittest discover -s . -p 'test_*.py'
```
