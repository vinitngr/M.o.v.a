# MOVA: Motion-Oriented Virtual Interface & Automation

## Overview
MOVA is an integrated hardware and software project. The software layer runs a hand-gesture recognition pipeline that detects motions and sends structured events (actions, data) over Wi-Fi. The hardware layer (MCU) receives these events, interprets them via embedded drivers/adapters, and executes the physical automation.

## Repository Structure
This project utilizes a **Monorepo** approach. Keeping hardware, software, and testing environments in the same repository ensures that when the event communication protocol changes, both the software dispatcher and hardware receiver remain perfectly in sync.

### Directory Layout

* **`experiments/`**
  The pre-project testing and benchmarking layer. A sandbox for prototyping abstract features and evaluating hardware capabilities (e.g., camera FPS, processing latency) before integrating them into the main pipeline.

* **`hardware/`**
  The embedded systems codebase. Contains C/C++ source code for the MCU, including sensor adapters, device drivers, Wi-Fi communication interfaces, and the logic to interpret software events.

* **`software/`**
  The software implementation layer. Houses the core hand-gesture recognition pipeline. It is structured to support multiple potential implementations (desktop, web, etc.), with one primary implementation serving the main hardware project.

* **`assets/`**
  A flexible storage directory for project assets and references. Includes miscellaneous CAD models, PCB designs, reference images, hardware simulation environments, and links to external resources.

* **`docs/`**
  Project documentation, protocol definitions, and architectural guidelines.
