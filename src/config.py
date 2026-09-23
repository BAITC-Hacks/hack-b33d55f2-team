"""Storage configuration; importing this module never creates directories."""

import math
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OLLAMA_MODEL = "qwen3:4b-instruct-2507-q4_K_M"
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 300.0


def get_data_dir() -> Path:
    default = r"C:\HackAlemData" if os.name == "nt" else str(Path.home() / "HackAlemData")
    path = Path(os.environ.get("QURYLTAI_DATA_DIR", default)).expanduser()
    if not path.is_absolute():
        raise ValueError("QURYLTAI_DATA_DIR must be an absolute local path.")
    path = path.resolve()
    if str(path).startswith(("\\\\", "//")):
        raise ValueError("Use a local disk, not a network share.")
    if path == PROJECT_ROOT or PROJECT_ROOT in path.parents:
        raise ValueError("Meeting data cannot be stored inside the Git repository.")
    for variable in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        value = os.environ.get(variable)
        if value:
            sync_root = Path(value).resolve()
            if path == sync_root or sync_root in path.parents:
                raise ValueError("Meeting data cannot be stored in OneDrive.")
    if any(part.lower().startswith("onedrive") for part in path.parts):
        raise ValueError("Meeting data cannot be stored in OneDrive.")
    if path.exists() and not path.is_dir():
        raise ValueError("The data path must be a directory.")
    return path


def get_ollama_settings() -> tuple[str, str, float]:
    """Return local Ollama URL, model, and generation timeout."""
    # QURYLTAY appeared in early setup notes; retain it as a compatibility alias.
    model = os.environ.get("QURYLTAI_OLLAMA_MODEL") or os.environ.get("QURYLTAY_OLLAMA_MODEL")
    timeout_text = (
        os.environ.get("QURYLTAI_OLLAMA_TIMEOUT_SECONDS")
        or os.environ.get("QURYLTAY_OLLAMA_TIMEOUT_SECONDS")
        or str(DEFAULT_OLLAMA_TIMEOUT_SECONDS)
    )
    try:
        timeout_seconds = float(timeout_text.strip())
    except ValueError as exc:
        raise ValueError("QURYLTAI_OLLAMA_TIMEOUT_SECONDS must be a positive number of seconds.") from exc
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("QURYLTAI_OLLAMA_TIMEOUT_SECONDS must be a positive number of seconds.")
    return (
        os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip(),
        (model or DEFAULT_OLLAMA_MODEL).strip(),
        timeout_seconds,
    )
