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
from src.storage.sign_space_store import get_space_store
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
AUDIO_DIR = BASE_DIR / "data" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/gesture-previews", StaticFiles(directory=str(PREVIEW_DIR)), name="gesture-previews")
app.mount("/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Lazy-loaded processor
processor = None
store = get_store()
space_store = get_space_store()

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
    role: str = "normal"          # see GestureStore.ROLES
    space_id: Optional[str] = None  # required for any space-* role
    sentence: Optional[str] = None  # one-shot members: spoken transcript
    voice_gender: str = "male"      # "male" | "female"


class UpdateGestureRequest(BaseModel):
    name: Optional[str] = None
    labels: Optional[List[str]] = None
    role: Optional[str] = None
    space_id: Optional[str] = None


class SpaceRequest(BaseModel):
    name: str
    toggle_mode: str = "shared"
    join_mode: str = "words"  # "spell", "words", "one_shot"


class SpaceUpdateRequest(BaseModel):
    name: Optional[str] = None
    toggle_mode: Optional[str] = None
    join_mode: Optional[str] = None


class GestureSentenceRequest(BaseModel):
    sentence: str
    gender: str = "male"  # "male" | "female"


def _link_gesture_to_space(gesture_id: str, space_id: str, role: str) -> Optional[str]:
    """Attach a gesture to a space and set its role. Returns an error message
    or None on success."""
    space = space_store.get_by_id(space_id)
    if not space:
        return "Sign space not found"
    if gesture_id not in space["gesture_ids"]:
        space_store.add_member(space_id, gesture_id)
    store.set_role(gesture_id, role)
    return None


def _unlink_gesture_from_all_spaces(gesture_id: str) -> None:
    for space in space_store.get_all():
        space_store.remove_member(space["id"], gesture_id)


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


@app.get("/admin/groups", response_class=HTMLResponse)
async def admin_groups(request: Request):
    return templates.TemplateResponse("groups.html", {"request": request})


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
                "role": g.get("role", "normal"),
            }
            for g in store.get_all()
        ],
        "spaces": space_store.get_state(),
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

    role = req.role if req.role in store.ROLES else "normal"
    is_space_role = role.startswith("space-")
    if is_space_role and not req.space_id:
        raise HTTPException(400, "A sign space must be selected for space roles")

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
        preview_path=f"/gesture-previews/{preview_file.name}",
        role=role
    )

    if is_space_role:
        error = _link_gesture_to_space(gesture_id, req.space_id, role)
        if error:
            store.delete(gesture_id)
            raise HTTPException(400, error)

    # One-shot members get their sentence baked as audio right at save time
    speech_error = None
    if req.sentence is not None and req.sentence.strip():
        space = space_store.get_by_id(req.space_id) if req.space_id else None
        if not space or space.get("join_mode") != "one_shot":
            store.delete(gesture_id)
            raise HTTPException(400, "Spoken sentences belong to one_shot groups")
        try:
            await _bake_gesture_speech(gesture_id, req.sentence, req.voice_gender)
            store.set_shot(gesture_id, sentence=req.sentence, gender=req.voice_gender,
                           audio_key=f"gest_{gesture_id}.mp3", ready=True)
        except Exception as exc:
            speech_error = str(exc.detail if hasattr(exc, "detail") else exc)

    del active_captures[req.capture_id]

    if speech_error:
        return {"success": True, "gesture": gesture, "speech_error": speech_error}

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

    if req.role is not None:
        if req.role in store.ROLES:
            if req.role.startswith("space-"):
                if req.space_id:
                    _unlink_gesture_from_all_spaces(gesture_id)
                    error = _link_gesture_to_space(gesture_id, req.space_id, req.role)
                    if error:
                        raise HTTPException(400, error)
                else:
                    raise HTTPException(400, "A sign space must be selected for space roles")
            elif req.role == "normal":
                _unlink_gesture_from_all_spaces(gesture_id)
                store.set_role(gesture_id, "normal")
        return {"success": True, "gesture": store.get_by_id(gesture_id)}

    return {"success": True, "gesture": gesture}


@app.delete("/api/gestures/{gesture_id}")
async def delete_gesture(gesture_id: str):
    _unlink_gesture_from_all_spaces(gesture_id)
    if store.delete(gesture_id):
        return {"success": True}
    raise HTTPException(404, "Gesture not found")


@app.post("/api/capture/cancel/{capture_id}")
async def cancel_capture(capture_id: str):
    if capture_id in active_captures:
        del active_captures[capture_id]
    return {"success": True}


@app.get("/api/spaces")
async def list_spaces():
    """Sign spaces with lightweight display fields."""
    return {"spaces": space_store.get_state()}


@app.post("/api/spaces")
async def create_space(req: SpaceRequest):
    space = space_store.create(req.name, req.toggle_mode, req.join_mode)
    if not space:
        raise HTTPException(400, f"Space key already exists for '{req.name}'")
    return {"success": True, "space": space}


@app.patch("/api/spaces/{space_id}")
async def update_space(space_id: str, req: SpaceUpdateRequest):
    space = space_store.update(space_id, name=req.name, toggle_mode=req.toggle_mode, join_mode=req.join_mode)
    if not space:
        raise HTTPException(404, "Space not found")
    return {"success": True, "space": space}


@app.delete("/api/spaces/{space_id}")
async def delete_space(space_id: str):
    member_ids = space_store.delete(space_id)
    for gid in member_ids:
        store.set_role(gid, "normal")
    return {"success": True, "released": member_ids}


async def _bake_gesture_speech(gesture_id: str, sentence: str, gender: str):
    """Synthesize & cache a gesture's one-shot sentence speech (ElevenLabs)."""
    sentence = sentence.strip()
    if not sentence:
        raise HTTPException(400, "Sentence cannot be empty")
    if len(sentence) > 300:
        raise HTTPException(400, "Sentence too long (max 300 chars)")

    from audio_adaptor import get_speech_adaptor
    adaptor = get_speech_adaptor()
    audio_key = f"gest_{gesture_id}.mp3"
    dest = AUDIO_DIR / audio_key
    try:
        voice = adaptor.voice_for_gender(gender)
        await asyncio.to_thread(adaptor.synthesize_and_save, sentence, dest, voice=voice)
    except Exception as exc:  # API/auth errors surface to the admin UI
        raise HTTPException(400, f"Speech generation failed: {exc}")
    return audio_key


def _one_shot_space_of_gesture(gesture_id: str):
    """Return the gesture's space when it belongs to a one_shot group, else None."""
    space = space_store.space_of_gesture(gesture_id)
    return space if space and space.get("join_mode") == "one_shot" else None


@app.post("/api/gestures/{gesture_id}/sentence")
async def set_gesture_sentence(gesture_id: str, req: GestureSentenceRequest):
    """(Re)generate & cache the one-shot sentence audio for a gesture."""
    gesture = store.get_by_id(gesture_id)
    if not gesture:
        raise HTTPException(404, "Gesture not found")
    if not _one_shot_space_of_gesture(gesture_id):
        raise HTTPException(400, "Spoken sentences belong to gestures inside one_shot groups")
    audio_key = await _bake_gesture_speech(gesture_id, req.sentence, req.gender)
    updated = store.set_shot(gesture_id, sentence=req.sentence, gender=req.gender,
                             audio_key=audio_key, ready=True)
    return {"success": True, "gesture": updated, "audio_url": f"/audio/{audio_key}"}


@app.get("/api/gestures/{gesture_id}/sentence/audio")
async def get_gesture_sentence_audio(gesture_id: str):
    """Serve the cached speech file (used later by the playground runtime card)."""
    gesture = store.get_by_id(gesture_id)
    shot = (gesture or {}).get("shot") or {}
    if not shot.get("audio_key"):
        raise HTTPException(404, "No speech generated for this gesture")
    path = AUDIO_DIR / shot["audio_key"]
    if not path.exists():
        raise HTTPException(404, "Speech file missing — regenerate it")
    from fastapi.responses import FileResponse
    return FileResponse(path, media_type="audio/mpeg", filename=shot["audio_key"])


@app.get("/health")
async def health():
    return {"status": "ok", "gestures_count": len(store.get_all())}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
