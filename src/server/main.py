from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import base64
import cv2
import numpy as np
import json
import asyncio
import time
import uuid
from pathlib import Path

from src.storage.gesture_store import get_store
from src.vision.mediapipe_processor import (
    MediaPipeProcessor, 
    extract_features, 
    extract_two_hand_features,
    normalize_landmarks,
    score_gestures,
)
from src.pipeline.detection_pipeline import RealTimePipeline
from src.buffer.gesture_buffer import GestureBuffer

app = FastAPI(title="MOVA Gesture Registration")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PREVIEW_DIR = BASE_DIR / "data" / "gesture_previews"
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/gesture-previews", StaticFiles(directory=str(PREVIEW_DIR)), name="gesture-previews")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Lazy-loaded processor
processor = None
store = get_store()

def get_processor():
    global processor
    if processor is None:
        processor = MediaPipeProcessor()
    return processor

active_captures: Dict[str, Dict] = {}


class CaptureStartRequest(BaseModel):
    # The UI detects the number of visible hands from each frame.
    hand_count: int = 2


class CaptureFrameRequest(BaseModel):
    image_base64: str
    capture_id: str


class DetectFrameRequest(BaseModel):
    image_base64: str


class SaveGestureRequest(BaseModel):
    capture_id: str
    name: str
    labels: List[str] = []


class UpdateGestureRequest(BaseModel):
    name: Optional[str] = None
    labels: Optional[List[str]] = None


def decode_base64_image(data: str) -> np.ndarray:
    if "," in data:
        data = data.split(",")[1]
    img_bytes = base64.b64decode(data)
    nparr = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)


def encode_image_to_base64(frame: np.ndarray) -> str:
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return base64.b64encode(buffer).decode('utf-8')


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
async def admin_root(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/admin/register", response_class=HTMLResponse)
async def admin_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/admin/gestures", response_class=HTMLResponse)
async def admin_gestures(request: Request):
    return templates.TemplateResponse("gestures.html", {"request": request})


@app.get("/admin/live-test", response_class=HTMLResponse)
async def admin_live_test(request: Request):
    return templates.TemplateResponse("live_test.html", {"request": request})


@app.get("/admin/pipeline", response_class=HTMLResponse)
async def admin_pipeline(request: Request):
    return templates.TemplateResponse("pipeline.html", {"request": request})


@app.get("/pipeline", response_class=HTMLResponse)
async def pipeline_page(request: Request):
    return templates.TemplateResponse("pipeline.html", {"request": request})


@app.get("/gestures", response_class=HTMLResponse)
async def gestures_page(request: Request):
    return templates.TemplateResponse("gestures.html", {"request": request})


@app.get("/playground", response_class=HTMLResponse)
async def playground_page(request: Request):
    return templates.TemplateResponse("playground.html", {"request": request})


@app.get("/api/playground/library")
async def playground_library():
    """Lightweight gesture metadata (no feature vectors) for playground cards."""
    return {
        "gestures": [
            {
                "id": g.get("id"),
                "name": g.get("name"),
                "hand_count": g.get("hand_count", 1),
                "preview_path": g.get("preview_path"),
                "landmarks": g.get("landmarks", []),
            }
            for g in store.get_all()
        ]
    }


@app.post("/api/capture/start")
async def start_capture(req: CaptureStartRequest):
    capture_id = str(int(time.time() * 1000))
    active_captures[capture_id] = {
        "hand_count": req.hand_count,
        "started_at": time.time(),
        "frames": [],
        "landmarks": None,
        "features": None
    }
    return {"capture_id": capture_id, "hand_count": req.hand_count}


@app.post("/api/capture/frame")
async def process_frame(req: CaptureFrameRequest):
    if req.capture_id not in active_captures:
        raise HTTPException(404, "Capture session not found")
    
    capture = active_captures[req.capture_id]
    frame = decode_base64_image(req.image_base64)
    
    if frame is None:
        raise HTTPException(400, "Invalid image data")
    
    proc = get_processor()
    result = proc.process_frame(frame)
    annotated = proc.draw_landmarks(frame.copy(), result)
    
    hands = proc.extract_landmarks(result)
    handedness = proc.get_handedness(result)
    
    capture["last_frame"] = annotated
    capture["last_result"] = result
    capture["hands"] = hands
    capture["handedness"] = handedness
    
    if hands:
        # A single gesture can use one or two hands.  Do not make the user
        # choose in advance; preserve the actual count from the good frame.
        if len(hands) == 1:
            features = extract_features(hands[0])
            capture["features"] = features
            capture["landmarks"] = hands[0]
            capture["hand_count"] = 1
        elif len(hands) >= 2:
            left_pts = None
            right_pts = None
            for i, h in enumerate(handedness):
                pts = hands[i]
                if h == "Left":
                    left_pts = pts
                else:
                    right_pts = pts
            if left_pts and right_pts:
                features = extract_two_hand_features(left_pts, right_pts)
                capture["features"] = features
                capture["landmarks"] = {"left": left_pts, "right": right_pts}
                capture["hand_count"] = 2
    
    return {
        "image_base64": encode_image_to_base64(annotated),
        "hand_count": len(hands),
        "handedness": handedness,
        "has_features": capture.get("features") is not None
    }


@app.post("/api/gestures/save")
async def save_gesture(req: SaveGestureRequest):
    if req.capture_id not in active_captures:
        raise HTTPException(404, "Capture session not found")
    
    capture = active_captures[req.capture_id]
    
    if not capture.get("features"):
        raise HTTPException(400, "No hand features captured. Make sure hand is visible.")
    
    if store.get_by_name(req.name):
        raise HTTPException(400, f"Gesture with name '{req.name}' already exists")
    
    landmarks = capture["landmarks"]
    if isinstance(landmarks, dict):
        landmarks_list = landmarks["left"] + landmarks["right"]
    else:
        landmarks_list = landmarks
    
    gesture_id = str(uuid.uuid4())[:8]
    preview_file = PREVIEW_DIR / f"{gesture_id}.jpg"
    if not cv2.imwrite(str(preview_file), capture["last_frame"]):
        raise HTTPException(500, "Could not save gesture preview")

    gesture = store.create(
        gesture_id=gesture_id,
        name=req.name,
        landmarks=landmarks_list,
        hand_count=capture["hand_count"],
        handedness=capture.get("handedness", ["Right"])[0] if capture.get("handedness") and len(capture["handedness"]) == 1 else capture.get("handedness"),
        features=capture["features"],
        labels=req.labels,
        preview_path=f"/gesture-previews/{preview_file.name}"
    )
    
    del active_captures[req.capture_id]
    
    return {"success": True, "gesture": gesture}


@app.post("/api/detect/frame")
async def detect_gesture_frame(req: DetectFrameRequest):
    """HTTP fallback for analysing a browser camera frame."""
    try:
        return analyse_live_frame(req.image_base64)
    except ValueError as error:
        raise HTTPException(400, str(error))


def analyse_live_frame(image_base64: str) -> Dict[str, Any]:
    """Extract features and rank saved gestures for one browser frame."""
    try:
        frame = decode_base64_image(image_base64)
    except (ValueError, base64.binascii.Error):
        frame = None
    if frame is None:
        raise ValueError("Invalid image data")

    proc = get_processor()
    result = proc.process_frame(frame)
    hands = proc.extract_landmarks(result)
    handedness = proc.get_handedness(result)
    live_features = None

    if len(hands) == 1:
        live_features = extract_features(hands[0])
    elif len(hands) >= 2:
        left, right = None, None
        for index, side in enumerate(handedness):
            if side == "Left":
                left = hands[index]
            elif side == "Right":
                right = hands[index]
        if left is not None and right is not None:
            live_features = extract_two_hand_features(left, right)

    return {
        "hand_count": len(hands),
        "landmarks": [[[point[0], point[1]] for point in hand] for hand in hands],
        "scores": score_gestures(live_features, store.get_all(), live_handedness=handedness) if live_features else [],
    }


@app.websocket("/ws/detect")
async def detect_gesture_stream(websocket: WebSocket):
    """Persistent live gesture-score stream for the admin test screen."""
    await websocket.accept()
    try:
        while True:
            payload = json.loads(await websocket.receive_text())
            image_base64 = payload.get("image_base64")
            if not image_base64:
                await websocket.send_json({"error": "A camera frame is required"})
                continue
            try:
                await websocket.send_json(analyse_live_frame(image_base64))
            except (ValueError, cv2.error) as error:
                await websocket.send_json({"error": str(error)})
    except (WebSocketDisconnect, json.JSONDecodeError):
        return


@app.websocket("/ws/pipeline")
async def pipeline_stream(websocket: WebSocket):
    """Real-time gesture detection and buffering WebSocket stream."""
    await websocket.accept()
    pipeline = RealTimePipeline(store=store, processor_getter=get_processor)
    try:
        while True:
            raw_text = await websocket.receive_text()
            payload = json.loads(raw_text)

            # Handle control commands
            action = payload.get("action")
            if action in ("reset", "clear"):
                pipeline.reset_buffer()
                await websocket.send_json({
                    "action_acknowledged": action,
                    "buffer_state": pipeline.buffer.get_state()
                })
                continue
            elif action == "set_threshold":
                pipeline.set_threshold(float(payload.get("threshold", 60.0)))
                continue
            elif action == "set_timeout":
                pipeline.buffer.end_signal_frames = int(payload.get("frames", 25))
                continue
            elif action == "init":
                if "threshold" in payload:
                    pipeline.set_threshold(float(payload["threshold"]))
                if "frames" in payload:
                    pipeline.buffer.end_signal_frames = int(payload["frames"])
                if "window" in payload:
                    pipeline.set_window_size(int(payload["window"]))
                continue

            image_base64 = payload.get("image_base64")
            if not image_base64:
                continue

            try:
                frame = decode_base64_image(image_base64)
                if frame is None:
                    await websocket.send_json({"error": "Invalid camera frame"})
                    continue
                result = pipeline.process_frame(frame)
                await websocket.send_json(result)
            except (ValueError, cv2.error) as error:
                await websocket.send_json({"error": str(error)})
    except (WebSocketDisconnect, json.JSONDecodeError):
        return


@app.get("/api/pipeline/state")
async def get_pipeline_state():
    """Diagnostic check for pipeline module."""
    sample_buf = GestureBuffer()
    return {"status": "ok", "default_buffer": sample_buf.get_state()}


@app.get("/api/gestures")
async def list_gestures():
    gestures = store.get_all()
    return {"gestures": gestures}


@app.get("/api/gestures/{gesture_id}")
async def get_gesture(gesture_id: str):
    gesture = store.get_by_id(gesture_id)
    if not gesture:
        raise HTTPException(404, "Gesture not found")
    return gesture


@app.patch("/api/gestures/{gesture_id}")
async def update_gesture(gesture_id: str, req: UpdateGestureRequest):
    gesture = store.update(gesture_id, name=req.name, labels=req.labels)
    if not gesture:
        raise HTTPException(404, "Gesture not found")
    return {"success": True, "gesture": gesture}


@app.delete("/api/gestures/{gesture_id}")
async def delete_gesture(gesture_id: str):
    if store.delete(gesture_id):
        return {"success": True}
    raise HTTPException(404, "Gesture not found")


@app.post("/api/capture/cancel/{capture_id}")
async def cancel_capture(capture_id: str):
    if capture_id in active_captures:
        del active_captures[capture_id]
    return {"success": True}


@app.get("/health")
async def health():
    return {"status": "ok", "gestures_count": len(store.get_all())}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
