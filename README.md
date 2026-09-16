# MOVA: Motion-Oriented Versatile Automation

## 1. Overview & Dual Purpose

**MOVA** is built around two core pillars:

1. **A Modular Hardware & Peripheral Framework:** An embedded MCU architecture that abstracts physical microcontroller pins into reconfigurable logical sockets, standard drivers, adaptors, and event hooks. It allows arbitrary sensors and actuators to be plugged in, remapped, and controlled via wireless events without touching low-level pin logic.
2. **A Motion-Driven Interaction Pipeline:** A First-Person Perspective (FPP) computer-vision pipeline that normalizes hand gestures in real time, translating natural physical motions into structured action events.

---

## 2. Implementations & Use Cases

While MOVA provides a general-purpose hardware-software event architecture, its primary real-world implementation focuses on assistive tech:

* **Assistive Communication for the Mute & Speech-Impaired (Primary Implementation):** 
  A wearable, head-mounted FPP camera captures hand gestures as the user signs naturally over their chest area. The pipeline decodes the handshapes, spatial orientation, and multi-hand relationships, converting them into live speech synthesis and structured phrases via downstream language processing.
* **Touchless Hardware & Smart Device Automation:**
  Using the modular hardware layer, decoded gesture events (e.g. action commands, directional triggers) are broadcast over Wi-Fi to MCU-controlled devices—operating lights, appliances, robotics, or environment controls hands-free.
* **Plug-and-Play Embedded Prototyping:**
  The hardware socket/adaptor system serves as a standalone framework for rapid MCU prototyping, allowing developers to swap physical peripherals (I2C, GPIO, ultrasonic, LEDs, relays) across logical sockets with zero code rewrites.

---

## 2. System Architecture

```text
       [ Wearable FPP Camera ]
                  │ (Live Video Stream)
                  ▼
       [ Software & Vision Layer ]
       ├── MediaPipe Landmark Detection (21 points/hand)
       ├── Geometric Normalization (Wrist-centered, scale invariant)
       ├── Orientation Math (Palm normal vector)
       └── Gesture Scoring (Cosine similarity & template matching)
                  │ (Event / Action / Data over Wi-Fi)
                  ▼
       [ Hardware Layer (MCU) ]
       ├── Sockets (Physical pin abstraction)
       ├── Drivers (Component-level control)
       ├── Adaptors (Standardized interface API)
       └── Hooks / Actions (Event reactions, audio, LEDs, actuators)
```

---

## 3. Project Structure

```text
Mova/
├── docs/                        # Project & hardware documentation
│   ├── ARCHITECTURE.md          # High-level architecture blueprint
│   └── hardware/
│       ├── DEVELOPER_GUIDE.md   # Hardware framework internal architecture
│       └── USER_GUIDE.md        # Pin socket mapping & component usage
│
├── experiments/                 # Active testing & benchmarking modules
│   ├── gesture_matching/        # Hand gesture detection, recording & live test
│   │   ├── vision_engine.py     # Camera & MediaPipe task runner
│   │   ├── math_engine.py       # Geometric normalization & scoring math
│   │   ├── gesture_manager.py   # Template persistence (gestures.json)
│   │   ├── register.py          # CLI to capture & train new gestures
│   │   └── live_test.py         # Real-time scoring UI with FPS & latency
│   └── depth_preview/           # Camera depth evaluation experiments
│
├── hardware/                    # Embedded MCU & firmware layer
│   └── simulation/              # Velxio / Wokwi hardware simulation prototype
│       ├── sketch.ino           # Main MCU entrypoint
│       ├── diagram.json         # Circuit schematic & simulated wiring
│       ├── sockets/             # Logical pin abstraction (GPIO / I2C)
│       ├── drivers/             # Low-level hardware drivers (LED, Ultrasonic, etc.)
│       ├── adaptors/            # Clean adapter interfaces
│       └── hooks/               # Event reaction logic
│
└── assets/                      # CAD 3D models, PCB files, schematics, references
```

---

## 4. How the Key Layers Work

### A. The Hand Gesture Pipeline (`experiments/gesture_matching/`)
* **First-Person View (FPP):** Optimized for a user looking down at their own hands.
* **Why raw coordinates are NOT used:** Distance and position change as hands move. Instead, coordinates are centered on the wrist and scaled by the hand size.
* **Orientation Awareness:** Calculates a 3D Palm Normal vector so pointing forward ("You") and pointing backward ("Me") are never confused.
* **Two-Hand Support:** Evaluates each hand shape independently plus the relative direction vector between wrists (e.g. supporting gestures like "Cup & Tray" or "Namaste").
* **Top-N Output:** Returns a ranked list of scores rather than a hard single winner. This enables a downstream language model (LLM) to infer the intended sentence even if a finger is partially blocked.

### B. The Hardware Architecture (`hardware/simulation/`)
Instead of hardcoding pin numbers across the code:
* **Sockets:** MCU pins are mapped to logical sockets (`SOCKET_GPIO_1`, `SOCKET_I2C_1`).
* **Drivers:** Handle raw signal communication with physical components.
* **Adaptors:** Provide unified methods (e.g., `turnOn()`, `getDistanceCm()`).
* **Hooks:** Link events to actions cleanly without tight coupling.

---

## 5. Getting Started Quickstart

### Prerequisites
* Python 3.10+
* Virtual environment (`venv`)

### Setting Up the Gesture Experiment
```bash
# 1. Activate your virtual environment
source venv/bin/activate        # On Linux / WSL
# or: win_venv\Scripts\activate # On Windows

# 2. Install dependencies
pip install mediapipe opencv-python numpy

# 3. Navigate to experiment directory
cd experiments/gesture_matching

# 4. Record a new gesture (e.g. "hello", "fist", "thumbs_up")
python register.py

# 5. Run real-time detection & benchmarking
python live_test.py
```

### Running Hardware Simulation
The firmware prototype in `hardware/simulation/` can be opened directly in [Velxio](https://velxio.dev/editor) or Wokwi using the provided `diagram.json` and `sketch.ino`.

---

## 6. Documentation References
* [High-Level Architecture](docs/ARCHITECTURE.md)
* [Hardware Developer Guide](docs/hardware/DEVELOPER_GUIDE.md)
* [Hardware Socket & Component User Guide](docs/hardware/USER_GUIDE.md)
* [Gesture Matching Experiment Blueprint](experiments/gesture_matching/README.md)

```
 [ Motion-Oriented ]   +   [ Versatile ]   +   [ Automation ]
            ↓                       ↓                   ↓
      The Vision / Input     The Modular HW       The Physical Action
      (Hands, Gestures,      (Sockets, Adapters,  (MCU, Devices, Output,
       Human Interaction)     Swappable Sensors)   Hardware Execution)
```