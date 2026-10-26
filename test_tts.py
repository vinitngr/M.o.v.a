#!/usr/bin/env python3
"""Speak a sentence locally using the project's text-to-speech adaptor.

Examples:
    python test_tts.py
    python test_tts.py "Hello, I can speak." --voice en-gb --rate 190
    python test_tts.py --list-voices
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from audio_adaptor import AudioSynthesisError, audio_adaptor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and play local TTS audio.")
    parser.add_argument("text", nargs="?", default="Hello from Mova. Text to speech is working.")
    parser.add_argument("--voice", help="eSpeak voice ID, such as en-us, en-gb, or hi")
    parser.add_argument("--rate", type=int, help="Words per minute (80–450)")
    parser.add_argument("--list-voices", action="store_true", help="Print installed voice IDs and exit")
    parser.add_argument("--save", type=Path, help="Also save the generated WAV to this path")
    return parser.parse_args()


def player_command(audio_path: Path) -> list[str] | None:
    """Find a commonly available WAV player without adding a Python package."""
    if sys.platform == "darwin" and shutil.which("afplay"):
        return ["afplay", str(audio_path)]
    if shutil.which("aplay"):
        return ["aplay", "--quiet", str(audio_path)]
    if shutil.which("paplay"):
        return ["paplay", str(audio_path)]
    if shutil.which("ffplay"):
        return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "error", str(audio_path)]
    return None


def main() -> int:
    args = parse_args()
    try:
        if args.list_voices:
            print("\n".join(audio_adaptor.available_voices()))
            return 0
        synthesis_started = time.perf_counter()
        audio = audio_adaptor.synthesize(args.text, voice=args.voice, rate=args.rate)
        synthesis_ms = (time.perf_counter() - synthesis_started) * 1_000
    except (AudioSynthesisError, ValueError) as exc:
        print(f"TTS failed: {exc}", file=sys.stderr)
        return 1

    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        args.save.write_bytes(audio.data)
        print(f"Saved WAV: {args.save}")

    # A named temporary file works with all common command-line players.
    with tempfile.NamedTemporaryFile(prefix="mova-tts-", suffix=".wav", delete=False) as temp:
        temp.write(audio.data)
        audio_path = Path(temp.name)
    try:
        command = player_command(audio_path)
        if command is None:
            print("Audio was generated, but no audio player was found. "
                  "Install ffmpeg (ffplay) or ALSA utilities (aplay).", file=sys.stderr)
            return 1
        print(f"Speaking with voice: {audio.voice}")
        print(f"TTS generation latency: {synthesis_ms:.1f} ms ({len(audio.data):,} WAV bytes)")
        sys.stdout.flush()
        playback_started = time.perf_counter()
        result = subprocess.run(command, check=False)
        playback_ms = (time.perf_counter() - playback_started) * 1_000
        print(f"Playback process time (includes spoken duration): {playback_ms:.1f} ms")
        return result.returncode
    finally:
        try:
            os.unlink(audio_path)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
