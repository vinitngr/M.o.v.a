# Minimal Phone App — SPEC

## Goal
Android app = hotspot companion + director + viewer + MediaPipe inference
for the `esp32_cam` firmware. Minimal: one device, one mode (hand-gesture),
LAN only. No cloud, no auth, no release process.

## Non-goals
Cloud, login/accounts, multi-device mesh, iOS, Play Store release.

## Tech (fixed)
- Native Android, Kotlin, minSdk 26.
- WS server: Ktor (or Java-WebSocket) on port 8080.
  Routes: `/device` (ESP32: TEXT events + BINARY JPEG) and `/app` (UI socket;
  UI may also read the session in-process — either is fine v1).
- MediaPipe Tasks Vision: `HandLandmarker`, CPU delegate, model in assets.
- No CameraX — frames arrive from ESP32 over WS.

## App contents (minimal)
1. **Director service (foreground):** WS server `:8080` in a foreground
   service (persistent notification) + partial wake lock +
   battery-optimization exemption, so it survives screen-off. Per-device
   session `{streaming, buttons, mode, fps, quality, model, target,
   lastFrame}`; accepts `hello`/`event`/`sample`/frames; sends
   `cmd`/`state`; fans frames out to viewer. Offline edits wait in session
   and push on reconnect (`hello` → full `state` sync, app wins conflicts).
2. **Home screen:** hotspot IP display, director on/off, device row with
   pills (STREAM on/off, AI on/off, fps).
3. **Device screen:** toggles — stream, fps (2/5/10), quality (low/med/high),
   model (none/mediapipe); live JPEG viewer + landmark-overlay toggle;
   event log.
4. **Inference module:** sample ≤3fps → HandLandmarker → overlay landmarks →
   `interpretGesture(landmarks): String` STUB returning `"…"` for now
   (3D-point mapping + intent comes later, same function signature).
5. **Power rules:** model loads only when `streaming && ai==1`, unloads
   otherwise; no viewer + no model → drop frames right after counting bytes.
6. **Local-demo mode (future):** phone camera/mic/speaker/flashlight pose
   as a virtual device (`deviceId:"phone-local"`, same message shapes) so
   flows test with zero hardware. `phone.*` components execute in-app.

## Protocol (firmware net adaptor must implement exactly this later)
Device → director, TEXT:
`{"t":"hello","deviceId":"AA:BB:CC:DD:EE:FF","streaming":0,"buttons":{"stream":0,"ai":0},"sensors":["camera"],"fw":"1.0"}`
`{"t":"event","deviceId":"…","id":"stream"|"ai","state":0|1,"seq":12}`
`{"t":"sample","deviceId":"…","sensor":"sonic","v":[42.5],"unit":"cm","ts":12345}`
(future sensors reuse `sample` with their own `sensor` name + `v` array)
Device → director, BINARY: raw JPEG bytes (no header).
Director → device, TEXT:
`{"t":"cmd","id":"stream"|"fps"|"quality"|"model"|"target"|"mode","value":…}`
`{"t":"cmd","id":"sonic","state":1,"rate":10}` (per-sensor on/off + rate)
`{"t":"cmd","component":"status_led","action":"set","value":1}` (generic: any registry id, no firmware change)
`{"t":"cmd","id":"capture_one"}` (snapshot mode: one frame up, then idle)
`{"t":"state","streaming":…,"buttons":{…},"fps":5,"quality":"med","model":"mediapipe"}`
Director → app: same `state` JSON + forwarded BINARY JPEGs.

## Defaults
- Port 8080. Device default director = hotspot gateway (`192.168.43.1`);
  NVS override comes later with WiFiManager provisioning.
- VGA 640×480 JPEG q12 @ 7–8fps (floor 5 in poor light); infer ≤3fps @320px wide.

## Acceptance (testable)
1. Hotspot on → ESP32 joins → auto-connects to gateway:8080 → appears on
   Home with hello state.
2. App stream toggle → device reacts (LED + serial `camera STARTED/STOPPED`).
3. Physical STREAM button → frames render in app viewer in <500ms on LAN.
4. AI toggle on → model loads, landmarks overlay live frames; off → unloads.
5. Viewer closed + AI off → frames dropped without decode (logcat proves it).
6. App killed + restarted (hotspot kept on) → device auto-reconnects in
   seconds, `hello` → full `state` sync, streaming resumes with last values.

## Context to attach in the new session
`esp32_cam/ARCHITECTURE.md` + this file. (`esp32_cam.zip` = firmware
reference for the protocol only; app lives in its own repo/folder.)
