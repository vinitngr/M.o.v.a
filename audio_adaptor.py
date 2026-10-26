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


class PiperProvider:
    """Local neural provider backed by the ``piper`` package (already in the
    venv). Small VITS models run on plain CPU (no GPU needed) and sound
    natural, conversational, calm — a big step up from espeak-ng.

    Voice files live in ``data/piper/voices`` as ``<name>.onnx`` plus the
    matching ``.onnx.json``:

        en_US-amy-medium.onnx        (female, calm/neutral)
        en_US-hfc_male-medium.onnx   (male, calm/neutral)

    Models are loaded once and cached, so every sentence after the first
    synthesizes in well under a second. Set ``TTS_PROVIDER=piper``.
    """

    VOICES_DIR = Path(__file__).resolve().parent / "data" / "piper" / "voices"
    FEMALE_VOICE = "en_US-amy-medium"
    MALE_VOICE = "en_US-hfc_male-medium"
    AUDIO_EXT = "wav"
    # Slightly slower + steadier than model default = calm conversation,
    # not podcast energy. (1.0 = neutral, >1 = slower/calm.)
    LENGTH_SCALE = 1.08

    _voice_cache: dict[str, object] = {}

    def warm_up(self) -> list[str]:
        """Pre-load every voice model (male + female) into the cache so the
        first Generate in the app is already fast. Failures are reported as
        strings instead of raising — a missing voice must never break the
        server from starting."""
        problems: list[str] = []
        for name in (self.MALE_VOICE, self.FEMALE_VOICE):
            try:
                self._voice(name)
            except Exception as exc:
                problems.append(f"{name}: {exc}")
        return problems

    def voice_for_gender(self, gender: str | None) -> str:
        return self.FEMALE_VOICE if (gender or "").lower() == "female" else self.MALE_VOICE

    def _voice(self, name: str):
        cached = self._voice_cache.get(name)
        if cached is None:
            try:
                from piper import PiperVoice
            except ImportError as exc:  # pragma: no cover - env issue
                raise AudioSynthesisError(
                    "piper is not installed in the venv — run: venv/bin/pip install piper-tts"
                ) from exc
            model = self.VOICES_DIR / f"{name}.onnx"
            if not model.is_file():
                raise AudioSynthesisError(
                    f"Piper voice file missing: {model} — download it with curl "
                    f"(see data/piper/voices README section in audio_adaptor.py)"
                )
            cached = PiperVoice.load(model)
            self._voice_cache[name] = cached
        return cached

    def available_voices(self) -> Sequence[str]:
        return [self.MALE_VOICE, self.FEMALE_VOICE]

    def synthesize(self, text: str, *, voice: str | None = None, rate: int | None = None) -> SynthesizedAudio:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be a non-empty string")
        import io
        import wave as wave_mod

        from piper.config import SynthesisConfig

        voice_name = voice or self.MALE_VOICE
        wav_buffer = io.BytesIO()
        wav_writer = wave_mod.open(wav_buffer, "wb")
        try:
            self._voice(voice_name).synthesize_wav(
                text.strip(),
                wav_writer,
                syn_config=SynthesisConfig(length_scale=self.LENGTH_SCALE),
            )
        finally:
            wav_writer.close()
        return SynthesizedAudio(data=wav_buffer.getvalue(), voice=voice_name)


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

    def warm_up(self) -> list[str]:
        """Pre-load provider state (e.g. neural voice models). No-op for
        providers without a warm_up; returns human-readable problem strings."""
        warm = getattr(self.provider, "warm_up", None)
        if callable(warm):
            return warm()
        return []

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
    """Adaptor chosen by ``TTS_PROVIDER``:

        piper       local neural voice (calm, CPU, offline, free — default)
        espeak      lightweight robotic software voice (quick testing)
        elevenlabs  best-quality neural via API (needs key + internet)

    Switch providers freely — any audio baked earlier keeps its cache
    until regenerated."""
    provider_name = (os.environ.get("TTS_PROVIDER") or "piper").strip().lower()
    if provider_name in ("piper", "piper-tts"):
        return TextToSpeechAdapter(PiperProvider())
    if provider_name in ("espeak", "espeak-ng", "espeakng"):
        return TextToSpeechAdapter(EspeakNgProvider())
    return TextToSpeechAdapter(ElevenLabsProvider())


# The default import for the backend. It creates no subprocess until called.
audio_adaptor = TextToSpeechAdapter()
