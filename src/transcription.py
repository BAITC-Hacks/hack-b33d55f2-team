"""Local-only audio transcription using caller-supplied faster-whisper weights."""

import os
import tempfile
from functools import lru_cache
from pathlib import Path


class TranscriptionError(RuntimeError):
    """A recoverable local transcription failure."""


def get_whisper_model_path() -> Path:
    value = os.environ.get("QURYLTAI_WHISPER_MODEL_PATH", "").strip()
    if not value:
        raise TranscriptionError(
            "Audio transcription needs a local faster-whisper model folder. "
            "Set QURYLTAI_WHISPER_MODEL_PATH and restart Streamlit."
        )
    try:
        path = Path(value).expanduser().resolve()
    except OSError as exc:
        raise TranscriptionError(f"Cannot access the local Whisper model folder: {exc}") from exc
    if not path.is_dir():
        raise TranscriptionError(f"Local Whisper model folder does not exist: {path}")
    return path


@lru_cache(maxsize=1)
def _load_model(model_path: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise TranscriptionError(
            "faster-whisper is not installed. Install the project requirements and restart Streamlit."
        ) from exc
    try:
        return WhisperModel(model_path, device="cpu", compute_type="int8", local_files_only=True)
    except Exception as exc:
        raise TranscriptionError(f"Could not load the local Whisper model: {exc}") from exc


def transcribe_audio(audio: bytes, filename: str) -> str:
    """Transcribe uploaded audio locally; temporary audio is deleted immediately."""
    if not audio:
        raise TranscriptionError("Choose an audio file before analysis.")
    suffix = Path(filename).suffix.lower()
    if suffix not in {".wav", ".mp3", ".m4a"}:
        raise TranscriptionError("Use a WAV, MP3, or M4A audio file.")
    model = _load_model(str(get_whisper_model_path()))
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as stream:
            stream.write(audio)
            temp_path = Path(stream.name)
        segments, _ = model.transcribe(
            str(temp_path), beam_size=1, vad_filter=True, condition_on_previous_text=False,
        )
        lines = [segment.text.strip() for segment in segments if segment.text.strip()]
    except TranscriptionError:
        raise
    except Exception as exc:
        raise TranscriptionError(f"Local audio transcription failed: {exc}") from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
    if not lines:
        raise TranscriptionError("No speech was detected in the audio file.")
    return "\n".join(lines)
