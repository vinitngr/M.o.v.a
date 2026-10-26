#!/usr/bin/env python3
"""Standalone browser microphone server for the streaming STT adaptor.

Run with a Vosk model directory.  ``--port 0`` (the default) asks the OS for
an unused port; Uvicorn prints the exact localhost URL to open.
"""

from __future__ import annotations

import argparse
import dataclasses
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from speech_to_text_adaptor import SpeechToTextError, VoskStreamingProvider

BASE_DIR = Path(__file__).resolve().parent


def create_app(model: Path, speaker_model: Path | None, max_speakers: int) -> FastAPI:
    """Create a single-model server; every browser socket gets its own recognizer."""
    # Validate models at startup instead of after the browser opens its mic.
    VoskStreamingProvider(model, speaker_model_path=speaker_model, max_speakers=max_speakers)
    app = FastAPI(title="MOVA Speech-to-Text Demo")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(BASE_DIR / "stt_demo.html")

    @app.websocket("/ws/transcribe")
    async def transcribe(websocket: WebSocket) -> None:
        await websocket.accept()
        provider = VoskStreamingProvider(model, speaker_model_path=speaker_model, max_speakers=max_speakers)
        await websocket.send_json({"type": "ready", "sample_rate": provider.sample_rate})
        try:
            while True:
                # The browser sends 16-bit, mono, little-endian PCM at 16 kHz.
                event = provider.accept_audio(await websocket.receive_bytes())
                if event is not None:
                    await websocket.send_json({"type": "transcript", **dataclasses.asdict(event)})
        except WebSocketDisconnect:
            # A disconnect normally means the user pressed Stop; no server state
            # needs to be retained between browser sessions.
            provider.finish()

    return app


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the local browser STT demo.")
    parser.add_argument("--model", required=True, type=Path, help="Unzipped Vosk speech-model directory")
    parser.add_argument("--speaker-model", type=Path, help="Optional unzipped Vosk speaker-model directory")
    parser.add_argument("--max-speakers", type=int, default=3, choices=(1, 2, 3))
    parser.add_argument("--port", type=int, default=0, help="Local port; 0 chooses a free port (default)")
    args = parser.parse_args()
    try:
        app = create_app(args.model, args.speaker_model, args.max_speakers)
    except SpeechToTextError as exc:
        parser.error(str(exc))
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
