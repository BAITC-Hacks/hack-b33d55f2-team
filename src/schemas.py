"""Typed boundaries shared by the UI and future local tools."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class MeetingMetadata(Schema):
    title: str = Field(min_length=1)
    meeting_date: date
    participants: list[str] = Field(default_factory=list)
    timezone: str = "Asia/Qyzylorda"


class TranscriptSegment(Schema):
    id: str
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    speaker_id: str
    text: str = Field(min_length=1)
    language: Literal["ru", "kk", "mixed"]

    @model_validator(mode="after")
    def valid_interval(self):
        if self.end <= self.start:
            raise ValueError("Segment end must be after start.")
        return self


class Speaker(Schema):
    id: str
    name: str = Field(min_length=1)


class ActionItem(Schema):
    assignee: str | None = None
    task: str = Field(min_length=1)
    deadline_original: str | None = None
    deadline_normalized: date | None = None
    evidence_segment_ids: list[str] = Field(min_length=1)
    status: Literal["open", "in_progress", "done"] = "open"


class MeetingSummary(Schema):
    overview: str
    discussion_points: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)


class Protocol(Schema):
    metadata: MeetingMetadata
    transcript: list[TranscriptSegment]
    speakers: list[Speaker]
    action_items: list[ActionItem]
    summary: MeetingSummary
    is_demo: bool = True

    @model_validator(mode="after")
    def valid_references(self):
        segment_ids = {segment.id for segment in self.transcript}
        speaker_ids = {speaker.id for speaker in self.speakers}
        if len(segment_ids) != len(self.transcript) or len(speaker_ids) != len(self.speakers):
            raise ValueError("Segment and speaker IDs must be unique.")
        if any(segment.speaker_id not in speaker_ids for segment in self.transcript):
            raise ValueError("Transcript references an unknown speaker.")
        if any(not set(item.evidence_segment_ids) <= segment_ids for item in self.action_items):
            raise ValueError("Action item references an unknown segment.")
        return self
