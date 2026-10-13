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
| Capture   | 7–8 fps VGA (640×480)   | gesture target; plain ESP32 WiFi+JPEG bound |
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
  Exposes ONE socket per device: BINARY JPEG frames + TEXT JSON for
  everything else (`hello`, `event`, `sample`). Commands come back on the
  same socket. Never one socket/server per sensor — see §6.
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
- Backend priority (fallback chain): **phone -> PC -> cloud.**
  - **Phone first (carry anywhere):** hotspot + director + inference
    (MediaPipe) all on the phone. Same network as the device, portable,
    low latency. Holds most things, including cloud-domain config.
    If the phone isn't running even the basic server, fall through:
  - **PC (show + local models):** close, same network. Runs director and
    heavier local models, big-screen display.
  - **Cloud (heavy processing):** fixed domain `wss://api.yourdomain.com`,
    per-device token. For heavy models where compute matters more than
    latency. Device + app both connect out. Works on any WiFi/NAT.
- Phone-as-hub (today) and cloud-as-hub (later) are the same shape, just
  a different address in `wifi_config.h`. Device connection count stays 1
  forever; a remote server just means the server sees 2 clients (device +
  app) instead of the phone seeing them locally.
- Sync is state-based (kubectl/etcd/kubelet): app writes desired state to
  the hub; device `hello`s on (re)connect and converges to last-known
  state. Offline changes wait at the hub and apply on return. Hotspot off
  or app closed is silence, never amnesia — NVS on device + copy in app.
- Network vs service are separate layers: hotspot on + app closed = device
  joins WiFi, knocks on :8080, nobody home → backoff retries, then camera
  + radio sleep. App opens → director starts → next retry connects.
- Phone memory cost applies only while a model is loaded (load on AI-on,
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

- Streaming: VGA 640×480 JPEG q12 ≈ 20–30KB @ 7–8fps (gesture target,
  ~2Mbps, fits ESP32 WiFi). Blind/low modes drop to QVGA @ 1–2fps.
  Promise "up to 8, floor of 5" — fps breathes with light (auto-exposure).
- Inference input: downscale to 320px, 2–3fps.
- Cloud API: NEVER per-frame. One snapshot on event (AI-on, motion) or
  max 1 per 5s, q60–70.
- Phone MediaPipe: load model only when `streaming && ai==1`; else the
  frame path is pure forward-or-drop (no decode cost).
- Transport: ONE server, ONE socket per device, typed messages —
  `frame` (BINARY JPEG) | `hello` (capabilities, incl. `sensors:[…]`) |
  `event` (buttons/mode) | `sample` (sensor readings, e.g. sonic cm) |
  `cmd`/`state` (back channel, incl. per-sensor rate). Frames get a
  dedicated *message type* (binary opcode), never a dedicated server.
- Why not a second server/endpoint per sensor: extra handshakes + RAM on
  ESP32, extra reconnect logic, extra phone ports, session-correlation pain —
  for zero benefit. A TEXT sample is tens of bytes on the already-open
  socket; a separate HTTP endpoint would pay handshake cost per reading and
  drain battery.
- Mode input contracts (director enforces, firmware just labels streams):
  gesture = frames@≥5fps + buttons; blind-assist = frames@2fps + sonic@10Hz
  (+ buzzer cmds back). Director forwards only what the active model needs;
  anything else is dropped at ingress.
- Sensor cadence is independent of camera: sonic sends on-change or throttled
  (default ≤10Hz, delta-gated, rate set via `cmd`); camera fps untouched.

## 7. Modes (same core, one hook per mode)

- A mode = preset bundle + hook implementation. Bundle: `{fps, quality,
  sensors on/off, sensor rates, model}` behind the scenes; phone can
  override any knob after (overrides win until next mode switch).
- Firmware DOES know the active mode: exactly one mode hook is fed
  `onFrame`/`onEvent` at a time; the rest sleep loaded. Shared plumbing
  (net sender, command handler) runs always beneath them. Hooks share
  helpers, never `switch(mode)`.
- Mode switch is live, never reboot: one `cmd` → camera reconfig (~200ms),
  hook swap, sensors on/off. Same socket stays open.
- STREAM = "start what this mode needs" (gesture: camera 8fps; blind:
  camera 2fps + sonic). LED on = this mode is flowing. No per-sensor
  buttons, ever; mid-mode overrides are phone toggles, not hardware.
- Now: hand-gesture comms. Later: blind-assist, snapshot/describe
  (event-triggered single frame + TTS, no stream). New mode = new hook
  file + bundle; core untouched.

## 8. Settings blackboard (single source of truth in firmware)

- One RAM struct: `{mode, fps, quality, target, sonic_rate, …}`. Hooks +
  director write it; drivers + adaptors only read it; changed fields bump
  a version so readers refresh.
- Persisted slice (mode, quality, target, wifi, host) → NVS on change.
  Defaults are first-boot values only; an offline reboot keeps YOUR values.
- Phone is source of truth when connected (wins conflicts on `hello`
  compare); NVS is the memory when it's not.

## 9. Generic commands (control without firmware changes)

- `{"t":"cmd","component":"status_led","action":"set","value":1}` routes by
  registry id → adaptor → driver. Read sensor, flip output, grab a frame —
  no C++, no reflash. New *usages* of existing drivers never need updates.
- Custom hooks (firmware change) are for on-device brains only
  (timing-critical, offline logic, sensor fusion). Open-source story:
  generic commands for instant control, one hook file per new behavior.
- App "custom mode": user-built button panels bound to
  (component, action, value) → generic `cmd`s. Phone-local parts
  (`phone.speaker`, `phone.mic`, …) execute via Android APIs in the same
  panel; `phone.*` runs here, rest goes down the wire.

## 10. Robustness (bad input never bricks)

- Parse layer validates every `cmd` (known component? known action? value
  in range?) → drops garbage with a log before touching drivers.
- Drivers clamp/bounds-check anyway (defense in depth).
- Hardware watchdog reboots a hung board in seconds. Worst case of bad
  input: one log line.

## 11. Power story

- ESP32: radio + camera off when idle (deep sleep, GPIO wake).
  Connect on demand, disconnect after ~5s idle if not streaming.
- Phone/laptop: no inference, no decode, no model in RAM unless AI mode on;
  no viewers = drop frames right after counting bytes.
- Phone screen-off: director runs in a foreground service + partial wake
  lock + battery-optimization exemption. Service, not screen, owns the
  socket — music-player pattern.
- Device retry loop is polite, not hot: fail → backoff (1s…minutes) →
  mostly modem-sleep between tries; past grace period with no network,
  deep sleep until button or network returns.

## 12. Build order

1. [done] Core + serial test hook + Velxio sim.
2. Net adaptor (single WS, hello/event/frame/sample, commands in, generic
   component dispatcher, settings blackboard + NVS slice, idle disconnect).
3. Director (single WS server, per-device sessions, settings, fan-out).
4. Production hook (fps/quality from settings, backpressure drops).
5. APK (mirror buttons, toggles table, viewer) — laptop inference first.
6. Phone-as-director + MediaPipe inference; cloud mode + TLS + tokens.
