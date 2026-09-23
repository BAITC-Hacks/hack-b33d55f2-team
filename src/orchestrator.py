"""Fixed demo workflow. Real text understanding lives in src.understanding."""

from collections.abc import Callable

from src.demo import demo_speakers, demo_summary, demo_tasks, demo_transcript
from src.schemas import MeetingMetadata, Protocol

STAGES = (
    "normalize_audio", "transcribe_audio", "diarize_speakers", "align_speakers",
    "extract_tasks", "generate_summary", "generate_protocol",
)


def normalize_audio():
    # TODO: Decode actual local audio to 16 kHz mono, preserving its timeline.
    return None  # No uploaded audio is read or written in demo mode.


def transcribe_audio(_audio):
    # TODO: Connect faster-whisper using local model weights only.
    return demo_transcript()


def diarize_speakers(_audio):
    # TODO: Connect local pyannote Community-1; disable telemetry.
    return demo_speakers()


def align_speakers(transcript, _speakers):
    # TODO: Align ASR word timestamps with diarization intervals.
    return transcript  # Fictional segments already have speaker IDs.


def extract_tasks(_transcript, metadata):
    # Demo remains deterministic. Phase 2 text mode uses the local provider separately.
    return demo_tasks(metadata.meeting_date)


def generate_summary(_transcript):
    # Demo remains deterministic. Phase 2 text mode uses the local provider separately.
    return demo_summary()


def generate_protocol(metadata, transcript, speakers, action_items, summary):
    # TODO: Add python-docx and ReportLab exporters in a later phase.
    return Protocol(metadata=metadata, transcript=transcript, speakers=speakers,
                    action_items=action_items, summary=summary, is_demo=True)


def run_pipeline(metadata: MeetingMetadata, *, demo_mode: bool,
                 on_stage: Callable[[str], None] | None = None) -> Protocol:
    if not demo_mode:
        raise NotImplementedError("Real audio analysis is not available in Phase 1. Enable demo mode.")

    def run(name, *args):
        result = globals()[name](*args)
        if on_stage:
            on_stage(name)
        return result

    audio = run("normalize_audio")
    transcript = run("transcribe_audio", audio)
    speakers = run("diarize_speakers", audio)
    transcript = run("align_speakers", transcript, speakers)
    tasks = run("extract_tasks", transcript, metadata)
    summary = run("generate_summary", transcript)
    return run("generate_protocol", metadata, transcript, speakers, tasks, summary)
