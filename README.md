# Qurylтай AI

**Qurylтай AI** is a privacy-first, local meeting-protocol assistant built for HackAlem. It helps a team turn a Russian, Kazakh, or mixed-language meeting into a readable transcript, a concise summary, decisions, and actionable follow-ups.

The goal is simple: reduce the manual work after a meeting while keeping agreements traceable. Each extracted action item can include an assignee, a deadline, a source quote, and a confidence score.

## What the MVP does

| Capability | Current status |
| --- | --- |
| Demo mode | Works offline with a deterministic fictional Russian/Kazakh meeting; no Ollama or audio model is required. |
| Text transcript analysis | Works with pasted text through a local Ollama model; supports `Name: message` and `[Name]: message` lines. |
| Action items and summary | Extracts tasks, responsible people, deadline phrases, source quotes, confidence, topics, problems, decisions, and a summary. Validation rejects unsupported evidence, invented assignees, and invented deadline phrases. |
| Local audio transcription | Works for WAV, MP3, and M4A when a local faster-whisper model path is configured. Audio is transcribed locally, then its text is analysed by local Ollama. Voice diarization is not implemented; audio uses a neutral speaker label. |
| DOCX/PDF export | Works after a successful analysis. Files are generated in memory and downloaded by the browser. |

## Privacy-first local architecture

Qurylтай AI is designed for a local-only workflow:

- Streamlit binds to `127.0.0.1`; telemetry is disabled in `.streamlit/config.toml`.
- Demo runs inside the local Python process.
- Text and audio analysis send meeting text only to Ollama on the same machine. The application accepts loopback Ollama URLs only (`127.0.0.1`, `localhost`, or `::1`) and has no cloud-AI fallback.
- Audio is written to an operating-system temporary file only while faster-whisper transcribes it; the file is then deleted. Results stay in Streamlit session memory.
- DOCX and PDF files are generated in memory for download. The app does not create a meeting database or persist protocols.

For a closed/offline presentation, set `OLLAMA_NO_CLOUD=1`, restart Ollama, and preload the model before the event.

## Quick start — Windows PowerShell

Run all commands from the repository root.

### 1. Create the environment and install the project

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If `py -3.12` is unavailable, use the installed Python 3.11+ executable instead.

### 2. Prepare local Ollama for text or audio analysis

Install Ollama for Windows from https://ollama.com/download/windows, then run:

```powershell
[Environment]::SetEnvironmentVariable('OLLAMA_NO_CLOUD', '1', 'User')
$env:OLLAMA_NO_CLOUD = '1'
ollama pull qwen3:4b-instruct-2507-q4_K_M
ollama list
```

Restart the Ollama application after setting the persistent variable. The default model is `qwen3:4b-instruct-2507-q4_K_M`; the repository does not download it automatically.

### 3. Optional: prepare a local audio model

Audio mode needs existing local faster-whisper weights. Point the app at the model folder:

```powershell
$env:QURYLTAI_WHISPER_MODEL_PATH = 'C:\HackAlemModels\faster-whisper-small'
```

If the model is not already available and an online download is acceptable, download it once:

```powershell
New-Item -ItemType Directory -Force C:\HackAlemModels | Out-Null
.\.venv\Scripts\hf.exe download Systran/faster-whisper-small --local-dir C:\HackAlemModels\faster-whisper-small
```

### 4. Start the application

```powershell
$env:QURYLTAI_DATA_DIR = 'C:\HackAlemData'
$env:OLLAMA_BASE_URL = 'http://127.0.0.1:11434'
$env:QURYLTAI_OLLAMA_MODEL = 'qwen3:4b-instruct-2507-q4_K_M'
$env:QURYLTAI_OLLAMA_TIMEOUT_SECONDS = '300'
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open http://127.0.0.1:8501. For the reliable presentation path, leave **Demo mode** enabled and select **Analyze meeting**; it needs neither Ollama nor a Whisper model.

## How to use the three modes

### Demo mode

The fastest presentation path. It displays a deterministic fictional bilingual meeting and its prepared protocol. No uploaded audio is analysed in this mode. You can rename displayed speakers; the display names update the transcript, action table, and exports for the current session.

### Text transcript

Turn Demo mode off, choose **Text transcript**, paste one utterance per line, add participants, and select **Analyze meeting**. For example:

```text
Алан: Тимур, подготовь бюджет до пятницы.
Тимур: Хорошо, сделаю до конца дня в четверг.
Арайлым: Решение принято: покажем протокол жюри в пятницу.
```

The text stays on the machine and is submitted only to the locally running Ollama service. The structured output is validated against the transcript before it is displayed.

### Audio (Phase 3)

Turn Demo mode off, choose **Audio (Phase 3)**, upload a WAV, MP3, or M4A file, and select **Analyze meeting**. This requires both a configured local faster-whisper model and local Ollama. The MVP transcribes the speech locally but does not identify speakers automatically; review the neutral transcript and speaker mapping before using assignments.

## Exports

After any successful Demo, text, or audio analysis, use **Export DOCX** or **Export PDF**. Both exports include meeting metadata, participants, speaker mapping, action items, summary, and transcript. Export buttons are disabled before an analysis succeeds.

## Project structure

```text
app.py                    Streamlit interface and mode selection
src/understanding.py      Grounded transcript analysis pipeline
src/llm/ollama.py         Loopback-only local Ollama client
src/transcription.py      Local faster-whisper audio transcription
src/exporters.py          In-memory DOCX and PDF generation
src/demo.py               Deterministic fictional demo data
src/schemas.py            Validated protocol data models
tests/                    MVP, privacy, analysis, audio, and export checks
docs/demo-guide.md        2–3 minute hackathon presentation script
```

## Checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The automated checks use fixtures and mocked providers. They do not require a downloaded Ollama or Whisper model and do not retain meeting files.
