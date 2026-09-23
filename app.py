"""Run with: python -m streamlit run app.py"""

import streamlit as st
from pydantic import ValidationError

from src.config import get_data_dir, get_ollama_settings
from src.demo import DEMO_DATE, DEMO_NAMES
from src.exporters import ExportError, create_docx, create_pdf
from src.llm import LLMProviderError, OllamaProvider
from src.orchestrator import STAGES, run_pipeline
from src.schemas import MeetingMetadata
from src.transcription import TranscriptionError, transcribe_audio
from src.understanding import TEXT_STAGES, run_text_pipeline

st.set_page_config(page_title="Quryltai AI", page_icon="📝", layout="wide")
st.title("Quryltai AI")
st.caption("A local AI meeting protocol assistant · Локальный помощник для протоколов встреч")

with st.sidebar:
    st.header("Local processing")
    # Kept as a toggle so the original Phase 1 demo remains one click away.
    demo_mode = st.toggle("Demo mode", value=True)
    if demo_mode:
        mode = "Demo"
    else:
        mode = st.radio("Input mode", ["Text transcript", "Audio (Phase 3)"], index=0)

    try:
        data_dir = get_data_dir()
        ollama_url, ollama_model, ollama_timeout = get_ollama_settings()
        config_valid = True
        st.caption("Configured future storage directory")
        st.code(str(data_dir), language=None)
        st.caption("Local LLM configuration")
        st.code(f"{ollama_url}\n{ollama_model}\nTimeout: {ollama_timeout:g} seconds", language=None)
    except (ValueError, OSError) as exc:
        config_valid = False
        st.error(str(exc))
    st.caption("Results remain in session memory. No meeting files are saved by the application.")

if mode == "Demo":
    st.info("Demo · fictional Russian/Kazakh meeting. It works without Ollama.")
elif mode == "Text transcript":
    st.info("Phase 2 · pasted transcript is sent only to the Ollama server on this machine.")
else:
    st.info("Phase 3 · audio is transcribed locally with faster-whisper, then analyzed by local Ollama.")

uploaded_audio = None
if mode in {"Demo", "Audio (Phase 3)"}:
    uploaded_audio = st.file_uploader(
        "Meeting audio", type=["wav", "mp3", "m4a"],
        help="Demo ignores audio. Phase 3 transcribes it locally and deletes its temporary copy.",
    )
    if uploaded_audio is not None and mode == "Demo":
        st.warning("Demo mode ignores uploaded audio. Select Audio (Phase 3) to transcribe it locally.")
    elif uploaded_audio is not None:
        st.caption("Audio is held temporarily for local transcription and is not saved by the app.")

with st.form("meeting_form"):
    meeting_title = st.text_input("Meeting title", value="Пилот сервиса для магазинов")
    meeting_date = st.date_input("Meeting date", value=DEMO_DATE)
    participants_text = st.text_area(
        "Participants", value=", ".join(DEMO_NAMES),
        help="Separate names with commas or newlines. Names are included only in the local Ollama prompt.",
    )
    transcript_text = ""
    if mode == "Text transcript":
        transcript_text = st.text_area(
            "Paste transcript",
            height=280,
            placeholder="Айгерім: Коллеги, начинаем встречу…\nТимур: Бюджетті жұмаға дейін дайындаймын…",
            help="Use one utterance per line and optional 'Name:' prefixes. The text stays on this machine.",
        )
    analyze = st.form_submit_button("Analyze meeting", disabled=not config_valid)

st.subheader("Processing status")
if analyze:
    try:
        metadata = MeetingMetadata(
            title=meeting_title,
            meeting_date=meeting_date,
            participants=[
                name.strip()
                for name in participants_text.replace("\n", ",").split(",")
                if name.strip()
            ],
        )
        if mode == "Demo":
            label = "Running local demo workflow…"
            with st.status(label, expanded=True) as status:
                protocol = run_pipeline(
                    metadata, demo_mode=True,
                    on_stage=lambda stage: st.write(f"✓ {stage} — demo"),
                )
                status.update(label="Demo complete · all 7 stages finished", state="complete", expanded=False)
        elif mode in {"Text transcript", "Audio (Phase 3)"}:
            provider = OllamaProvider(
                model=ollama_model, base_url=ollama_url, timeout_seconds=ollama_timeout,
            )
            label = "Running local audio transcription and Ollama analysis…" if mode == "Audio (Phase 3)" else "Running local Ollama analysis… Long transcripts may take several minutes."
            with st.status(label, expanded=True) as status:
                if mode == "Audio (Phase 3)":
                    if uploaded_audio is None:
                        raise TranscriptionError("Choose an audio file before analysis.")
                    transcript_text = transcribe_audio(uploaded_audio.getvalue(), uploaded_audio.name)
                    st.write("✓ transcribe_audio — local faster-whisper")
                protocol = run_text_pipeline(
                    metadata, transcript_text, provider,
                    on_stage=lambda stage: st.write(f"✓ {stage} — local"),
                )
                status.update(label="Local analysis complete", state="complete", expanded=False)
        else:
            raise NotImplementedError("Audio analysis is coming in Phase 3. Use Demo or Text transcript mode.")

        st.session_state.protocol = protocol
        st.session_state.result_mode = mode
        for speaker in protocol.speakers:
            st.session_state[f"name_{speaker.id}"] = speaker.name
    except LLMProviderError as exc:
        st.session_state.pop("protocol", None)
        st.session_state.pop("result_mode", None)
        st.error(str(exc))
        st.caption(f"Local Ollama configuration: `{ollama_url}` · `{ollama_model}`")
    except TranscriptionError as exc:
        st.session_state.pop("protocol", None)
        st.session_state.pop("result_mode", None)
        st.error(str(exc))
    except (ValidationError, ValueError) as exc:
        st.session_state.pop("protocol", None)
        st.session_state.pop("result_mode", None)
        st.error(f"Please check the meeting input: {exc}")
    except NotImplementedError as exc:
        st.session_state.pop("protocol", None)
        st.session_state.pop("result_mode", None)
        st.error(str(exc))
elif st.session_state.get("protocol") and st.session_state.get("result_mode") == mode:
    st.success("Analysis complete · results are retained in this session.")
else:
    st.caption("Ready. Select a mode and Analyze meeting.")

protocol = st.session_state.get("protocol")
if st.session_state.get("result_mode") != mode:
    protocol = None
if protocol:
    result_kind = "fictional demo" if protocol.is_demo else "local Ollama result"
    st.caption(
        f"Showing {result_kind}: {protocol.metadata.title} · "
        f"{protocol.metadata.meeting_date.isoformat()}. Analyze again to apply input changes."
    )

st.subheader("Speaker mapping")
names = {}
if protocol:
    for speaker in protocol.speakers:
        names[speaker.id] = st.text_input(speaker.id, key=f"name_{speaker.id}").strip() or speaker.name
    st.caption("Names update displayed results only. The local model does not identify voices.")
else:
    st.caption("Speaker labels and editable names will appear after analysis.")

st.subheader("Transcript")
if protocol:
    for segment in protocol.transcript:
        if protocol.is_demo:
            label = f"{segment.id} · {segment.start:05.1f}–{segment.end:05.1f}s · {names[segment.speaker_id]} · {segment.language}"
        else:
            label = f"{segment.id} · {names[segment.speaker_id]}"
        st.text(label)
        st.text(segment.text)
else:
    st.caption("The analyzed transcript will appear here.")

st.subheader("Action items")
if protocol:
    assignee_names = {speaker.name: names[speaker.id] for speaker in protocol.speakers}
    st.dataframe([{
        "Responsible person": assignee_names.get(item.assignee, item.assignee) or "Not specified",
        "Task": item.task,
        "Deadline (original)": item.deadline_original or "Not specified",
        "Deadline (date)": item.deadline_normalized.isoformat() if item.deadline_normalized else "Not specified",
        "Evidence IDs": ", ".join(item.evidence_segment_ids),
        "Source quote": item.source_quote or "See evidence segment",
        "Confidence": f"{item.confidence:.0%}" if item.confidence is not None else "Not scored",
        "Status": item.status,
    } for item in protocol.action_items], hide_index=True, width="stretch")
    if not protocol.action_items:
        st.info("No explicit action items were found.")
else:
    st.caption("Tasks, responsible people, deadlines, and transcript evidence will appear here.")

st.subheader("Meeting summary")
if protocol:
    st.write(protocol.summary.overview)
    topics = protocol.summary.main_topics or protocol.summary.discussion_points
    if topics:
        st.markdown("**Main topics**")
        for point in topics:
            st.write(f"• {point}")
    if protocol.summary.key_problems:
        st.markdown("**Key problems**")
        for problem in protocol.summary.key_problems:
            st.write(f"• {problem}")
    if protocol.summary.decisions:
        st.markdown("**Decisions**")
        for decision in protocol.summary.decisions:
            st.write(f"• {decision}")
else:
    st.caption("Overall summary, topics, problems, and decisions will appear here.")

st.subheader("Export protocol")
left, right = st.columns(2)
if protocol:
    try:
        docx_bytes = create_docx(protocol, names)
        pdf_bytes = create_pdf(protocol, names)
        filename = f"protocol-{protocol.metadata.meeting_date.isoformat()}"
        left.download_button(
            "Export DOCX", docx_bytes, file_name=f"{filename}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            width="stretch",
        )
        right.download_button(
            "Export PDF", pdf_bytes, file_name=f"{filename}.pdf",
            mime="application/pdf", width="stretch",
        )
        st.caption("Exports are generated in memory and downloaded by your browser.")
    except (ExportError, OSError, ValueError) as exc:
        left.button("Export DOCX", disabled=True, width="stretch")
        right.button("Export PDF", disabled=True, width="stretch")
        st.error(f"Document export failed: {exc}")
else:
    left.button("Export DOCX", disabled=True, width="stretch")
    right.button("Export PDF", disabled=True, width="stretch")
    st.caption("Analyze a meeting to enable DOCX and PDF export.")

with st.expander("Workflow stages"):
    stages = STAGES if mode == "Demo" else TEXT_STAGES if mode == "Text transcript" else ("transcribe_audio", *TEXT_STAGES)
    st.code(" → ".join(stages), language=None)
