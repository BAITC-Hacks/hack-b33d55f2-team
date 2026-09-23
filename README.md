# Quryltai AI

A privacy-first local AI meeting protocol assistant for HackAlem. The planned application turns Russian, Kazakh, and mixed-language meetings into speaker-labeled transcripts, action items, summaries, and DOCX/PDF protocols.

## Phase 1 status

The Streamlit foundation works with a **fictional, deterministic demo**, without any AI models or API calls. It includes meeting metadata, an optional WAV/MP3/M4A uploader, seven workflow stages, a bilingual transcript, editable speaker display names, five action items with evidence, and a summary. Relative deadlines follow the submitted meeting date; explicit dates stay fixed. Missing assignees/deadlines remain unspecified.

Uploaded audio is **not processed or saved**. Demo output never describes the uploaded recording. Turning demo mode off reports that real analysis is unavailable. DOCX/PDF buttons are disabled placeholders. Speaker edits change the displayed transcript and assignees; they are session-only display overrides, not persisted changes to the protocol object.

## Install (Windows PowerShell)

Use Python 3.11 or 3.12 for a straightforward path to later speech dependencies. Phase 1 only requires Streamlit and Pydantic; no model downloads are needed.

This checkout was verified with the already installed Python 3.13.15, Streamlit 1.64.0, and Pydantic 2.13.5. Its `.venv` is ready to run. A fresh installation can use the commands below.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If Python is installed as `python` instead of `py`, use `python -m venv .venv`. With uv already installed, an alternative is:

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

## Run

```powershell
$env:QURYLTAI_DATA_DIR = 'C:\HackAlemData'
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open http://127.0.0.1:8501, leave **Demo mode** enabled, and click **Analyze meeting**. No upload is required. Rename a speaker to see the transcript and task table update. Change the meeting date and analyze again to see relative deadlines change.

The default fictional date is September 23, 2026. Participants are metadata, not automatic voice identification. Input changes apply when the form is submitted. The app preserves results through normal widget reruns; a new session/server restart loses them.

## Privacy and local storage

- All Phase 1 processing runs inside the local Streamlit Python process. There are no external AI calls or network clients in application code.
- Streamlit binds to `127.0.0.1`, and usage statistics are disabled in `.streamlit/config.toml`. Run from the repository root so this configuration is loaded. Do not expose the development app through public tunnels or cloud hosting.
- Uploaded bytes remain in Streamlit session memory; the application does not copy them to disk. Avoid private uploads while testing this demo because they serve no purpose yet.
- The future data directory defaults to `C:\HackAlemData` on Windows (`~/HackAlemData` elsewhere). Override with `QURYLTAI_DATA_DIR` before launch. Phase 1 validates the location but **does not create it or write meeting files**.
- Repository paths, network shares, and known OneDrive locations are rejected. The user must verify the chosen directory is not synchronized by another backup/sync service. This repository itself may be in OneDrive; runtime meeting files must stay outside it.
- `.gitignore` excludes common audio, transcript, document, environment, model, and temporary file formats. It is a second guard, not a substitute for external storage; it does not protect already tracked files or forced Git additions.
- Package installation requires internet access unless using predownloaded packages. Runtime demo analysis can work offline. No database is used.

## Structure

```text
app.py                    Streamlit interface
src/config.py             External data path validation
src/schemas.py            Pydantic models and reference validation
src/demo.py               Fictional bilingual fixtures (safe source code)
src/orchestrator.py       Seven-stage deterministic workflow
.streamlit/config.toml    Loopback binding and telemetry opt-out
tests/test_foundation.py  Pipeline, schemas, privacy path checks
tests/test_app.py         Streamlit UI smoke checks
requirements.txt          Phase 1 dependencies only
```

## Planned local AI components

1. `normalize_audio`: decode local audio into 16 kHz mono with its timeline preserved.
2. `transcribe_audio`: faster-whisper with predownloaded multilingual local weights.
3. `diarize_speakers`: local pyannote Community-1 with telemetry disabled.
4. `align_speakers`: reconcile word timestamps and speaker intervals.
5. `extract_tasks`: local Ollama, structured output validation, evidence references.
6. `generate_summary`: local Ollama for Russian/Kazakh meeting summaries.
7. `generate_protocol`: a shared validated Protocol rendered with python-docx and ReportLab, including Kazakh-compatible fonts.

These integration points are marked TODO in `src/orchestrator.py`. None of these model packages, document exporters, or weights are installed by Phase 1. There will be no external cloud AI fallback.

## Basic checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Checks use only synthetic fixtures and do not create meeting files. The future model accuracy, real audio support, production security, and document layout are outside Phase 1.
