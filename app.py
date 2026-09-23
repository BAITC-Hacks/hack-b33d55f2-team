"""Run with: python -m streamlit run app.py"""

import streamlit as st
from pydantic import ValidationError

from src.config import get_data_dir
from src.demo import DEMO_DATE, DEMO_NAMES
from src.orchestrator import STAGES, run_pipeline
from src.schemas import MeetingMetadata

st.set_page_config(page_title="Quryltai AI", page_icon="📝", layout="wide")
st.title("Quryltai AI")
st.caption("A local AI meeting protocol assistant · Локальный помощник для протоколов встреч")
st.info("Phase 1 · DEMO: fictional Russian/Kazakh meeting. No speech or AI models are connected.")

with st.sidebar:
    st.header("Local processing")
    demo_mode = st.toggle("Demo mode", value=True)
    try:
        data_dir = get_data_dir()
        config_valid = True
        st.caption("Configured future storage directory")
        st.code(str(data_dir), language=None)
    except (ValueError, OSError) as exc:
        config_valid = False
        st.error(str(exc))
    st.caption("Phase 1 keeps results in session memory. No meeting files are saved.")
    st.caption("Use a non-synced local folder. Set QURYLTAI_DATA_DIR before starting the app to change it.")

uploaded_audio = st.file_uploader("Meeting audio", type=["wav", "mp3", "m4a"],
                                help="Optional in demo mode. Uploads are held in memory and are not analyzed or saved.")
if uploaded_audio is not None:
    st.warning("Your uploaded audio will not be analyzed. Demo results always come from the fictional sample.")

with st.form("meeting_form"):
    meeting_title = st.text_input("Meeting title", value="Пилот сервиса для магазинов")
    meeting_date = st.date_input("Meeting date", value=DEMO_DATE)
    participants_text = st.text_area("Participants", value=", ".join(DEMO_NAMES),
                                     help="Separate names with commas or newlines. This is metadata; rename detected speakers below.")
    analyze = st.form_submit_button("Analyze meeting", disabled=not config_valid)

if not demo_mode:
    st.warning("Real audio analysis is planned for a later phase. Enable Demo mode to run the sample.")

st.subheader("Processing status")
if analyze:
    if not demo_mode:
        st.session_state.pop("protocol", None)
        st.error("Real audio analysis is not implemented. Enable Demo mode.")
    else:
        try:
            metadata = MeetingMetadata(title=meeting_title, meeting_date=meeting_date,
                participants=[name.strip() for name in participants_text.replace("\n", ",").split(",") if name.strip()])
            with st.status("Running local demo workflow…", expanded=True) as status:
                protocol = run_pipeline(metadata, demo_mode=True,
                    on_stage=lambda stage: st.write(f"✓ {stage} — demo"))
                st.session_state.protocol = protocol
                for speaker in protocol.speakers:
                    st.session_state[f"name_{speaker.id}"] = speaker.name
                status.update(label="Demo complete · all 7 stages finished", state="complete", expanded=False)
        except (ValidationError, ValueError) as exc:
            st.session_state.pop("protocol", None)
            st.error(f"Please check the meeting metadata: {exc}")
elif "protocol" in st.session_state:
    st.success("Demo complete · results are retained in this session.")
else:
    st.caption("Ready. Enable Demo mode and select Analyze meeting.")

protocol = st.session_state.get("protocol")
if protocol:
    st.caption(f"Showing demo: {protocol.metadata.title} · {protocol.metadata.meeting_date.isoformat()}. "
               "Submit Analyze meeting again to apply metadata changes.")

st.subheader("Speaker mapping")
names = {}
if protocol:
    for speaker in protocol.speakers:
        names[speaker.id] = st.text_input(speaker.id, key=f"name_{speaker.id}").strip() or speaker.name
    st.caption("Names update the transcript and demo task assignees below. Voice identity is not inferred.")
else:
    st.caption("Speaker labels and editable names will appear after analysis.")

st.subheader("Transcript")
if protocol:
    for segment in protocol.transcript:
        st.text(f"{segment.id} · {segment.start:05.1f}–{segment.end:05.1f}s · "
                f"{names[segment.speaker_id]} · {segment.language}")
        st.text(segment.text)
else:
    st.caption("The timestamped Russian/Kazakh demo transcript will appear here.")

st.subheader("Action items")
if protocol:
    assignee_names = {speaker.name: names[speaker.id] for speaker in protocol.speakers}
    st.dataframe([{
        "Responsible person": assignee_names.get(item.assignee, item.assignee) or "Not specified",
        "Task": item.task,
        "Deadline (original)": item.deadline_original or "Not specified",
        "Deadline (date)": item.deadline_normalized.isoformat() if item.deadline_normalized else "Not specified",
        "Evidence": ", ".join(item.evidence_segment_ids),
        "Status": item.status,
    } for item in protocol.action_items], hide_index=True, width="stretch")
    st.caption("Relative deadlines use the submitted meeting date. Explicit 2026 dates remain fixed in this fictional example.")
else:
    st.caption("Tasks, responsible people, deadlines, and evidence will appear here.")

st.subheader("Meeting summary")
if protocol:
    st.write(protocol.summary.overview)
    st.markdown("**Discussion points**")
    for point in protocol.summary.discussion_points:
        st.write(f"• {point}")
    st.markdown("**Decisions**")
    for decision in protocol.summary.decisions:
        st.write(f"• {decision}")
else:
    st.caption("A demo summary and decisions will appear here.")

st.subheader("Export protocol")
left, right = st.columns(2)
left.button("Export DOCX", disabled=True, width="stretch")
right.button("Export PDF", disabled=True, width="stretch")
st.caption("Export placeholders only. Document generation will be implemented in a later phase.")

with st.expander("Workflow stages"):
    st.code(" → ".join(STAGES), language=None)
