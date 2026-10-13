# ESP32-CAM Streaming Glasses — Architecture Plan

Status: firmware core DONE and verified in Velxio sim
(serial shows `frame #N captured, bytes=.. WxH` on STREAM toggle).

## 1. What works today

- Core: drivers (button, LED, camera) + adaptors + registries, flat layout.
- `SerialTestHook`: STREAM button -> camera on/off + LED, AI button -> mode flag,
  frames logged with count + bytes + resolution every 500ms (~2fps, readable serial).
- Camera driver tries the real OV2640, falls back to simulated frames with a warning.

## 2. FPS numbers (three different things)

| Stage     | Rate              | Notes                                  |
|-----------|-------------------|----------------------------------------|
| Capture   | 7–10 fps QVGA     | plain ESP32 limit (WiFi + JPEG bound)  |
| Send      | 5–10 fps          | throttle in hook, drop when busy       |
| Inference | 2–3 fps           | sample every 3rd–4th frame, 320px wide |

Test hook runs 2fps on purpose. Production hook: capture 100–150ms, infer on subset.

## 3. Partitioning (recommended: split in three, not all in one place)

```
[FIRMWARE esp32_cam]  --WS-->  [DIRECTOR laptop|phone]  --WS-->  [APP / INFERENCE]
  buttons/LED/camera             session + fan-out +        APK (control) +
  power, capture                 settings store             MediaPipe / laptop model
```

Rules:

- **Firmware owns hardware only.** Buttons, LED, camera gate, power.
  Exposes ONE socket: TEXT events (`hello`, `event`) + BINARY JPEG frames.
  Accepts commands back on the same socket (`{cmd:"stream",state:1}` …).
  Never owns: model choice, fps/quality values, URLs, AI logic.
- **Director owns session + settings.** Holds per-device state
  (`streaming`, `buttons`, `fps`, `quality`, `model`, `target`).
  Any laptop OR phone can be director — switchable without reflash.
- **App/APK owns control UI.** Buttons mirrored, toggles for fps/quality/model/
  target, viewer. Sends commands to director; never talks to device directly.
- **Inference owns models.** Subscribes to frames from director.
  Laptop now, phone (MediaPipe) later — same subscription, no firmware change.

## 4. Connection: who connects to whom

- Device NEVER needs a known IP. It connects **outbound** (DHCP is fine).
  It only needs the **director address**, provisioned once into NVS
  (WiFiManager field `host:port`), changeable later via app command.
- Director address, two modes:
  - **LAN mode (now):** phone hotspot (192.168.43.x) or laptop hotspot.
    Director runs on laptop (`:8080`) or phone. Device provisioned with that
    host:port. No internet needed.
  - **Cloud mode (product):** fixed domain `wss://api.yourdomain.com`,
    per-device token. Device + app both connect out. Works on any WiFi/NAT.
- Mobile in the middle is OPTIONAL and useful: hotspot source, and can host
  the director (then laptop connects to phone). Phone proximity = low latency
  for MediaPipe. Memory cost only while a model is loaded (load on AI-on,
  unload on AI-off).

## 5. App-controlled toggles (director settings, set from APK)

| Toggle  | Values                  | Effect                                     |
|---------|-------------------------|--------------------------------------------|
| stream  | on/off (button or app)  | camera init/deinit, radio up/down          |
| fps     | 2 / 5 / 10              | hook capture interval                      |
| quality | low/med/high (JPEG q)   | frame bytes vs clarity                     |
| model   | none / mediapipe / cloud| inference path, null skips all ML          |
| target  | laptop / phone          | where frames get fanned out                |

Physical buttons and app commands write the SAME adaptor state —
one code path in firmware, works offline when phone is absent.

## 6. Frames and models

- Streaming: QVGA JPEG q12 ≈ 10–20KB @ 5–10fps (fits ESP32 RAM + WiFi).
- Inference input: downscale to 320px, 2–3fps.
- Cloud API: NEVER per-frame. One snapshot on event (AI-on, motion) or
  max 1 per 5s, q60–70.
- Phone MediaPipe: load model only when `streaming && ai==1`; else the
  frame path is pure forward-or-drop (no decode cost).

## 7. Power story (unchanged)

- ESP32: radio + camera off when idle (deep sleep, GPIO wake).
  Connect on demand, disconnect after ~5s idle if not streaming.
- Phone/laptop: no inference, no decode, no model in RAM unless AI mode on;
  no viewers = drop frames right after counting bytes.

## 8. Build order

1. [done] Core + serial test hook + Velxio sim.
2. Net adaptor (single WS, hello/event/frame, commands in, idle disconnect).
3. Director (single WS server, per-device sessions, settings, fan-out).
4. Production hook (fps/quality from settings, backpressure drops).
5. APK (mirror buttons, toggles table, viewer) — laptop inference first.
6. Phone-as-director + MediaPipe inference; cloud mode + TLS + tokens.
