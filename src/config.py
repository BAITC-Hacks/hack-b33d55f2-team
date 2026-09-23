"""Storage configuration; importing this module never creates directories."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
