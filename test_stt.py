#!/usr/bin/env python3
"""Listen to the default microphone and print a rough live transcript.

Example:
    python test_stt.py --model models/vosk-model-small-en-in-0.4
"""

from __future__ import annotations

import argparse
import queue
import sys
from pathlib import Path

from speech_to_text_adaptor import RealtimeSpeechToTextAdapter, SpeechToTextError, VoskStreamingProvider


def main() -> int:
    parser = argparse.ArgumentParser(description="Test real-time, offline speech-to-text from the microphone.")
    parser.add_argument("--model", required=True, type=Path, help="Unzipped Vosk speech-model directory")
    parser.add_argument("--speaker-model", type=Path, help="Optional unzipped Vosk speaker model directory")
    parser.add_argument("--max-speakers", type=int, default=3, choices=(1, 2, 3))
    parser.add_argument("--device", type=int, help="Input-device index; omit to use the system default microphone")
    args = parser.parse_args()

    try:
        import sounddevice as sd
        provider = VoskStreamingProvider(
            args.model, speaker_model_path=args.speaker_model, max_speakers=args.max_speakers
        )
    except (ImportError, OSError, SpeechToTextError) as exc:
        print(f"STT setup failed: {exc}", file=sys.stderr)
        if isinstance(exc, OSError) and "PortAudio" in str(exc):
            print("Install the system microphone dependency, then retry: "
                  "sudo apt install libportaudio2 portaudio19-dev", file=sys.stderr)
        return 1

    audio_chunks: queue.Queue[bytes] = queue.Queue()

    def callback(indata, frames, time_info, status) -> None:  # type: ignore[no-untyped-def]
        if status:
            print(status, file=sys.stderr)
        audio_chunks.put(bytes(indata))

    print("Listening... press Ctrl+C to stop.")
    print("Final sentences appear on new lines; partial text updates in place.")
    try:
        stream = sd.RawInputStream(
            device=args.device,
            samplerate=provider.sample_rate,
            blocksize=4_000,
            dtype="int16",
            channels=1,
            callback=callback,
        )
    except sd.PortAudioError as exc:
        print(f"Could not open a microphone: {exc}", file=sys.stderr)
        print("No default input device is visible to PortAudio. If this is a container or WSL, "
              "start the script on the host or expose its microphone to Linux first.", file=sys.stderr)
        return 1

    with stream:
        try:
            while True:
                event = provider.accept_audio(audio_chunks.get())
                if event is None:
                    continue
                label = f"[{event.speaker}] " if event.speaker else ""
                if event.is_final:
                    print(f"\r{label}{event.text}                    ")
                else:
                    print(f"\r{label}{event.text}", end="", flush=True)
        except KeyboardInterrupt:
            final_event = provider.finish()
            if final_event:
                label = f"[{final_event.speaker}] " if final_event.speaker else ""
                print(f"\r{label}{final_event.text}")
            print("Stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
