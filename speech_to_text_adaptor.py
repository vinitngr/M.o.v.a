"""Streaming, provider-swappable speech-to-text with approximate speaker labels.

The first provider is Vosk: it runs entirely on the local machine and accepts
small PCM chunks as they arrive.  The application only talks to
``RealtimeSpeechToTextAdapter``, so Vosk can later be replaced with a cloud or
self-hosted neural provider without changing callers.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class SpeechToTextError(RuntimeError):
    """Raised when a speech-to-text provider cannot process audio."""


@dataclass(frozen=True, slots=True)
class TranscriptEvent:
    """One incremental or final transcription result."""

    text: str
    is_final: bool
    speaker: str | None = None
    speaker_similarity: float | None = None


class StreamingSpeechToTextProvider(Protocol):
    """Contract for any streaming STT implementation.

    Audio is signed 16-bit, mono PCM at the provider's configured sample rate.
    Feed chunks in their arrival order; do not concatenate an entire recording.
    """

    def accept_audio(self, pcm_chunk: bytes) -> TranscriptEvent | None: ...
    def finish(self) -> TranscriptEvent | None: ...
    def reset(self) -> None: ...


class SpeakerClusterer:
    """Groups similar voice embeddings into at most ``max_speakers`` labels.

    These labels are local session labels (``speaker_1``, ``speaker_2``), not
    a way to determine a person's real identity.  Very short speech, overlap,
    and similar voices can be assigned incorrectly.
    """

    def __init__(self, max_speakers: int = 3, similarity_threshold: float = 0.72) -> None:
        if not 1 <= max_speakers <= 3:
            raise ValueError("max_speakers must be from 1 to 3")
        self.max_speakers = max_speakers
        self.similarity_threshold = similarity_threshold
        self._centres: list[list[float]] = []

    @staticmethod
    def _normalise(vector: list[float]) -> list[float]:
        magnitude = math.sqrt(sum(value * value for value in vector))
        return [value / magnitude for value in vector] if magnitude else vector

    def assign(self, embedding: list[float]) -> tuple[str, float]:
        vector = self._normalise(embedding)
        if not vector:
            return "speaker_1", 0.0
        similarities = [sum(a * b for a, b in zip(vector, centre)) for centre in self._centres]
        best_index = max(range(len(similarities)), key=similarities.__getitem__) if similarities else -1
        best_similarity = similarities[best_index] if best_index >= 0 else 0.0

        if best_index < 0 or (best_similarity < self.similarity_threshold and len(self._centres) < self.max_speakers):
            self._centres.append(vector)
            return f"speaker_{len(self._centres)}", 1.0

        # Smooth the centre so a single phrase does not define a speaker.
        centre = self._centres[best_index]
        self._centres[best_index] = self._normalise([(old * 0.85) + (new * 0.15) for old, new in zip(centre, vector)])
        return f"speaker_{best_index + 1}", best_similarity

    def reset(self) -> None:
        self._centres.clear()


class VoskStreamingProvider:
    """Offline Vosk recognition provider for rough, low-latency transcripts."""

    def __init__(
        self,
        model_path: str | Path,
        *,
        speaker_model_path: str | Path | None = None,
        sample_rate: int = 16_000,
        max_speakers: int = 3,
    ) -> None:
        try:
            from vosk import KaldiRecognizer, Model, SpkModel  # type: ignore[import-not-found]
        except ImportError as exc:
            raise SpeechToTextError("Vosk is not installed. Run: pip install vosk") from exc

        self.sample_rate = sample_rate
        model_directory = Path(model_path)
        if not model_directory.is_dir():
            raise SpeechToTextError(f"Speech model directory does not exist: {model_directory}")
        self._model = Model(str(model_directory))
        self._recognizer = KaldiRecognizer(self._model, sample_rate)
        self._recognizer.SetWords(True)
        self._speaker_clusterer: SpeakerClusterer | None = None
        if speaker_model_path is not None:
            speaker_directory = Path(speaker_model_path)
            if not speaker_directory.is_dir():
                raise SpeechToTextError(f"Speaker model directory does not exist: {speaker_directory}")
            self._recognizer.SetSpkModel(SpkModel(str(speaker_directory)))
            self._speaker_clusterer = SpeakerClusterer(max_speakers=max_speakers)

    def _event_from_result(self, payload: dict[str, Any], *, is_final: bool) -> TranscriptEvent | None:
        text = (payload.get("text") if is_final else payload.get("partial")) or ""
        text = text.strip()
        if not text:
            return None
        speaker = None
        similarity = None
        embedding = payload.get("spk")
        if self._speaker_clusterer is not None and isinstance(embedding, list):
            speaker, similarity = self._speaker_clusterer.assign([float(value) for value in embedding])
        return TranscriptEvent(text=text, is_final=is_final, speaker=speaker, speaker_similarity=similarity)

    def accept_audio(self, pcm_chunk: bytes) -> TranscriptEvent | None:
        if not pcm_chunk:
            return None
        if self._recognizer.AcceptWaveform(pcm_chunk):
            return self._event_from_result(json.loads(self._recognizer.Result()), is_final=True)
        return self._event_from_result(json.loads(self._recognizer.PartialResult()), is_final=False)

    def finish(self) -> TranscriptEvent | None:
        return self._event_from_result(json.loads(self._recognizer.FinalResult()), is_final=True)

    def reset(self) -> None:
        self._recognizer.Reset()
        if self._speaker_clusterer:
            self._speaker_clusterer.reset()


class RealtimeSpeechToTextAdapter:
    """Stable application-facing API for real-time speech-to-text."""

    def __init__(self, provider: StreamingSpeechToTextProvider) -> None:
        self.provider = provider

    def accept_audio(self, pcm_chunk: bytes) -> TranscriptEvent | None:
        return self.provider.accept_audio(pcm_chunk)

    def finish(self) -> TranscriptEvent | None:
        return self.provider.finish()

    def reset(self) -> None:
        self.provider.reset()
