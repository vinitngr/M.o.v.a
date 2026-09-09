# FPP Hand Gesture Matching Experiment (Extensive Blueprint)

## 1. Core Philosophy & Architecture

This experiment serves as the testing and benchmarking layer for the MOVA gesture recognition pipeline, utilizing a **First-Person Perspective (FPP)** camera.

### The "No Jugaad" (No Hacks) Rule for Occlusion
In FPP, fingers will inevitably occlude (block) each other (e.g., pointing straight down away from the camera). 
**Our rule:** We do not write complex, hacky mathematical workarounds ("jugaad") to guess where hidden fingers are. 
* If MediaPipe cannot see it clearly, the system will naturally output a lower confidence score for that specific gesture.
* **The Fallback:** The system does not output a single "winner". It outputs the **Top-N Matches** (e.g., `[{"Closed Palm": 88%}, {"Pointing Down": 82%}]`).
* **The Final Resolution:** Because the ultimate project will feed a sequence of these Top-N matches into an LLM (Large Language Model), the LLM will use contextual natural language processing to deduce the correct sentence. We keep the vision layer fast, simple, and strictly mathematical.

---

## 2. The Math Engine (Feature Engineering)

To ensure the system works regardless of hand distance or slight shifts, we do not match raw XYZ coordinates. We use deterministic feature engineering.

### Pre-Computation Optimization
Math costs compute. Therefore, heavy calculations are done **only once during registration**. The `register.py` script calculates the geometric features and saves the final numbers to JSON. During live inference (`live_test.py`), the math engine only calculates features for the single live frame and runs a fast vector distance comparison against the JSON.

### Extracted Features per Frame
1. **Handshape (Joint Angles)**
   * We calculate the 3D angles between the bone segments of the fingers (e.g., Angle at the PIP joint, DIP joint, and MCP joint).
   * *Benefit:* Angles do not change whether the hand is 5 inches or 15 inches from the camera (Scale/Translation invariant).
2. **Orientation (Palm Normal Vector)**
   * We use three points (Wrist `0`, Index Knuckle `5`, Pinky Knuckle `17`) to compute the cross-product, resulting in a 3D Normal Vector pointing out of the palm.
   * *Benefit:* Solves the "You vs Me" problem. Pointing forward and pointing at your chest have the same finger angles, but opposite Palm Normals.
3. **Spatial Relation (Two-Handed Gestures)**
   * If both hands are present, we calculate the normalized 3D directional vector from the Left Wrist `0` to the Right Wrist `0`.
   * *Benefit:* Solves the "Cup and Tray" problem. We evaluate the left hand's shape, the right hand's shape, and simply check if the left hand is *above/below/beside* the right hand, allowing for flexible distances.

---

## 3. Codebase Architecture

The code is strictly decoupled to ensure the Math and Vision engines can be dropped directly into the final hardware/software repositories later.

* **`vision_engine.py`**
  * Initializes MediaPipe Hands.
  * Handles reading camera frames, running inference, and returning the raw 42 XYZ landmarks (21 per hand).
* **`math_engine.py`**
  * Takes raw XYZ landmarks and converts them into the feature vector (Angles + Palm Normal + Relative Vector).
  * Contains the `compare_features(live_vec, stored_vec)` function using Cosine Similarity or Euclidean Distance.
* **`gesture_manager.py`**
  * File I/O handler. Loads and saves the pre-computed features to `gestures.json`.
* **`register.py`** (The CLI Tool)
  * Prompts: `Enter gesture name:`.
  * Captures $N$ frames of the user holding the pose.
  * Averages the features across the frames for a stable template.
  * Calls `gesture_manager.py` to append to the database.
* **`live_test.py`** (The UI Testing Tool)
  * Loads `gestures.json` into memory.
  * Runs continuous FPP camera feed.
  * UI Overlays: Bounding boxes, MediaPipe skeleton, System FPS.
  * **Leaderboard Overlay:** Displays the Top 5 gesture matches and their scores to visually verify if the LLM fallback strategy will have the correct data.

---

## 4. Data Storage Schema (`gestures.json`)

The database stores pre-computed features, not raw coordinates. 

```json
{
  "gestures": [
    {
      "name": "water",
      "hand_count": 1,
      "features": {
        "angles": [12.4, 45.1, 88.0, ...], 
        "palm_normal": [0.1, -0.9, 0.2],
        "relative_vector": null
      }
    },
    {
      "name": "cup_and_tray",
      "hand_count": 2,
      "features": {
        "left_angles": [...],
        "right_angles": [...],
        "left_normal": [...],
        "right_normal": [...],
        "relative_vector": [0.0, 1.0, 0.0] 
      }
    }
  ]
}
```
