"""Low-latency, provider-swappable text-to-speech adaptor.

The default provider uses the local ``espeak-ng`` command.  It is a small,
non-AI speech synthesizer and returns WAV bytes directly, so it requires no
network call, model download, or server.  Install it on Debian/Ubuntu with:

    sudo apt install espeak-ng

Callers should depend on :class:`TextToSpeechAdapter`, not on a provider.  A
future API-backed or self-hosted provider only needs to implement
``TextToSpeechProvider``.
"""

from __future__ import annotations

import asyncio
import base64
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

import requests
from dotenv import load_dotenv

# Load the project .env (if present) without clobbering real env vars.
load_dotenv(Path(__file__).resolve().parent / ".env")


class AudioSynthesisError(RuntimeError):
    """Raised when a speech provider cannot create audio."""


@dataclass(frozen=True, slots=True)
class SynthesizedAudio:
    """In-memory audio suitable for a response body, queue, or storage."""

    data: bytes
    mime_type: str = "audio/wav"
    voice: str | None = None

    def as_data_url(self) -> str:
        """Return audio as a browser-ready ``data:`` URL when useful."""
        encoded = base64.b64encode(self.data).decode("ascii")
        return f"data:{self.mime_type};base64,{encoded}"


class TextToSpeechProvider(Protocol):
    """Contract for local, API-backed, or self-hosted TTS implementations."""

    def synthesize(self, text: str, *, voice: str | None = None, rate: int | None = None) -> SynthesizedAudio:
        """Create audio bytes for ``text``."""

    def available_voices(self) -> Sequence[str]:
        """Return voice identifiers understood by this provider."""


class EspeakNgProvider:
    """Local, non-AI provider backed by the ``espeak-ng`` executable.

    This is the classic lightweight "software voice" — robotic on purpose,
    free, offline and instant. Ideal while testing so demos don't sound
    polished. Set ``TTS_PROVIDER=espeak`` in ``.env`` to use it.
    """

    DEFAULT_VOICE = "en-gb"
    # eSpeak NG has no Indian-English (en-IN) voice. British English is the
    # closest built-in baseline until this provider is replaced by neural TTS.
    MALE_VOICE = "en-gb+m3"    # robotic software male variant
    FEMALE_VOICE = "en-gb+f4"  # robotic software female variant
    DEFAULT_RATE = 175  # words per minute; espeak-ng's normal speaking rate
    MIN_RATE = 80
    MAX_RATE = 450

    def __init__(self, executable: str = "espeak-ng") -> None:
        self.executable = executable

    def voice_for_gender(self, gender: str | None) -> str:
        return self.FEMALE_VOICE if (gender or "").lower() == "female" else self.MALE_VOICE

    def _executable_path(self) -> str:
        path = shutil.which(self.executable)
        if path is None:
            raise AudioSynthesisError(
                "espeak-ng is not installed or is not on PATH. "
                "Install it with: sudo apt install espeak-ng"
            )
        return path

    def available_voices(self) -> list[str]:
        """List installed eSpeak voice IDs (for example ``en-us`` or ``hi``)."""
        completed = subprocess.run(
            [self._executable_path(), "--voices"],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode:
            raise AudioSynthesisError(completed.stderr.strip() or "Could not list espeak-ng voices")

        # First line is a header.  The final whitespace-separated column is
        # the voice identifier for espeak-ng's stable tabular output.
        return [line.split()[-1] for line in completed.stdout.splitlines()[1:] if line.split()]

    def synthesize(self, text: str, *, voice: str | None = None, rate: int | None = None) -> SynthesizedAudio:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be a non-empty string")

        selected_voice = voice or self.DEFAULT_VOICE
        selected_rate = self.DEFAULT_RATE if rate is None else rate
        if not isinstance(selected_rate, int) or not self.MIN_RATE <= selected_rate <= self.MAX_RATE:
            raise ValueError(f"rate must be an integer from {self.MIN_RATE} to {self.MAX_RATE}")

        completed = subprocess.run(
            [
                self._executable_path(),
                "--stdout",
                "-v",
                selected_voice,
                "-s",
                str(selected_rate),
            ],
            input=text.encode("utf-8"),
            check=False,
            capture_output=True,
        )
        if completed.returncode or not completed.stdout:
            error = completed.stderr.decode("utf-8", errors="replace").strip()
            raise AudioSynthesisError(error or "espeak-ng returned no audio")
        return SynthesizedAudio(data=completed.stdout, voice=selected_voice)


class ElevenLabsProvider:
    """Provider backed by the ElevenLabs REST API (post-paid TTS).

    Reads configuration from the project ``.env``:

        ELEVENLABS_API_KEY       required
        TTS_PROVIDER             elevenlabs | espeak   (default: elevenlabs)
        ELEVENLABS_MODEL         default: eleven_flash_v2_5 (lowest latency)
        ELEVENLABS_VOICE_MALE    default: Adam (pNInz6obpgDQGcFmaJgB)
        ELEVENLABS_VOICE_FEMALE  default: Rachel (21m00Tcm4TlvDq8ikWAM)
    """

    DEFAULT_MODEL = "eleven_flash_v2_5"
    DEFAULT_MALE = "pNInz6obpgDQGcFmaJgB"      # pre-made voice "Adam"
    DEFAULT_FEMALE = "21m00Tcm4TlvDq8ikWAM"    # pre-made voice "Rachel"
    API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    def __init__(self, api_key: str | None = None, timeout: float = 30.0) -> None:
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY", "").strip()
        self.timeout = timeout

    # TextToSpeechProvider -------------------------------------------------
    def synthesize(self, text: str, *, voice: str | None = None, rate: int | None = None) -> SynthesizedAudio:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be a non-empty string")
        if not self.api_key:
            raise AudioSynthesisError(
                "ELEVENLABS_API_KEY is missing — add it to the project .env file"
            )
        voice_id = voice or os.environ.get("ELEVENLABS_VOICE_MALE", self.DEFAULT_MALE)
        model_id = os.environ.get("ELEVENLABS_MODEL", self.DEFAULT_MODEL) or self.DEFAULT_MODEL
        url = self.API_URL.format(voice_id=voice_id)
        completed = requests.post(
            url,
            json={
                "text": text.strip(),
                "model_id": model_id,
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
            headers={"xi-api-key": self.api_key, "accept": "audio/mpeg"},
            timeout=self.timeout,
        )
        if completed.status_code != 200 or not completed.content:
            detail = completed.text[:240] if completed.text else "empty response"
            raise AudioSynthesisError(f"ElevenLabs request failed ({completed.status_code}): {detail}")
        return SynthesizedAudio(data=completed.content, mime_type="audio/mpeg", voice=voice_id)

    def available_voices(self) -> Sequence[str]:
        return [self.DEFAULT_MALE, self.DEFAULT_FEMALE]

    # Convenience selectors ------------------------------------------------
    def voice_for_gender(self, gender: str | None) -> str:
        """Resolve "male"/"female" (from stored space fields) to a voice id."""
        env_key = "ELEVENLABS_VOICE_FEMALE" if (gender or "").lower() == "female" else "ELEVENLABS_VOICE_MALE"
        fallback = self.DEFAULT_FEMALE if (gender or "").lower() == "female" else self.DEFAULT_MALE
        return os.environ.get(env_key, fallback).strip() or fallback


class TextToSpeechAdapter:
    """Application-facing TTS API; replace ``provider`` without caller changes."""

    def __init__(self, provider: TextToSpeechProvider | None = None) -> None:
        self.provider = provider or EspeakNgProvider()

    def synthesize(self, text: str, *, voice: str | None = None, rate: int | None = None) -> SynthesizedAudio:
        return self.provider.synthesize(text, voice=voice, rate=rate)

    async def synthesize_async(
        self, text: str, *, voice: str | None = None, rate: int | None = None
    ) -> SynthesizedAudio:
        """Non-blocking version for async web handlers."""
        return await asyncio.to_thread(self.synthesize, text, voice=voice, rate=rate)

    def available_voices(self) -> Sequence[str]:
        return self.provider.available_voices()

    def voice_for_gender(self, gender: str | None) -> str:
        """Resolve "male"/"female" via the active provider (robotic or neural)."""
        resolver = getattr(self.provider, "voice_for_gender", None)
        if resolver:
            return resolver(gender)
        return voice or ""

    def synthesize_and_save(self, text: str, dest: Path | str, *, voice: str | None = None, rate: int | None = None) -> Path:
        """Synthesize ``text`` and atomically write it to ``dest``.

        Returns the destination path. The temporary file is removed on any
        failure so a previous recording is never overwritten by garbage.
        """
        audio = self.synthesize(text, voice=voice, rate=rate)
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        try:
            tmp.write_bytes(audio.data)
            tmp.replace(dest)
        finally:
            if tmp.exists():
                tmp.unlink()
        return dest


def get_speech_adaptor() -> TextToSpeechAdapter:
    """Adaptor chosen by ``TTS_PROVIDER``: ``espeak`` = lightweight robotic
    software voice (offline, free), ``elevenlabs`` = neural (default).
    Switch providers freely — any audio baked earlier keeps its .mp3 cache
    until regenerated."""
    provider_name = (os.environ.get("TTS_PROVIDER") or "elevenlabs").strip().lower()
    if provider_name in ("espeak", "espeak-ng", "espeakng"):
        return TextToSpeechAdapter(EspeakNgProvider())
    return TextToSpeechAdapter(ElevenLabsProvider())


# The default import for the backend. It creates no subprocess until called.
audio_adaptor = TextToSpeechAdapter()
