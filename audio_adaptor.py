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
import shutil
import subprocess
from dataclasses import dataclass
from typing import Protocol, Sequence


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
    """Local, non-AI provider backed by the ``espeak-ng`` executable."""

    # eSpeak NG has no Indian-English (en-IN) voice. British English is the
    # closest built-in baseline until this provider is replaced by neural TTS.
    DEFAULT_VOICE = "en-gb"
    DEFAULT_RATE = 175  # words per minute; espeak-ng's normal speaking rate
    MIN_RATE = 80
    MAX_RATE = 450

    def __init__(self, executable: str = "espeak-ng") -> None:
        self.executable = executable

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


# The default import for the backend. It creates no subprocess until called.
audio_adaptor = TextToSpeechAdapter()
