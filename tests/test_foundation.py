import os
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from src.config import PROJECT_ROOT, get_data_dir
from src.orchestrator import STAGES, run_pipeline
from src.schemas import MeetingMetadata, Protocol, TranscriptSegment


class FoundationTests(unittest.TestCase):
    def protocol(self, meeting_date=date(2026, 9, 23)):
        return run_pipeline(MeetingMetadata(title="Synthetic test", meeting_date=meeting_date), demo_mode=True)

    def test_all_stages_and_bilingual_evidence(self):
        stages = []
        protocol = run_pipeline(MeetingMetadata(title="Test", meeting_date=date(2026, 9, 23)),
                                demo_mode=True, on_stage=stages.append)
        self.assertEqual(stages, list(STAGES))
        self.assertEqual({s.language for s in protocol.transcript}, {"ru", "kk", "mixed"})
        self.assertEqual(len(protocol.speakers), 3)
        self.assertEqual(Protocol.model_validate_json(protocol.model_dump_json()), protocol)

    def test_relative_dates_and_missing_information(self):
        protocol = self.protocol(date(2026, 12, 31))
        self.assertEqual(protocol.action_items[0].deadline_normalized, date(2027, 1, 1))
        self.assertEqual(protocol.action_items[1].deadline_normalized, date(2027, 1, 3))
        self.assertEqual(protocol.action_items[2].deadline_normalized, date(2026, 9, 30))
        self.assertIsNone(protocol.action_items[-1].assignee)
        self.assertIsNone(protocol.action_items[-1].deadline_normalized)
        self.assertEqual(protocol.action_items[3].assignee, "Дана")

    def test_real_processing_is_explicitly_unavailable(self):
        with self.assertRaises(NotImplementedError):
            run_pipeline(MeetingMetadata(title="Test", meeting_date=date.today()), demo_mode=False)

    def test_invalid_evidence_is_rejected(self):
        data = self.protocol().model_dump()
        data["action_items"][0]["evidence_segment_ids"] = ["missing"]
        with self.assertRaises(ValidationError):
            Protocol.model_validate(data)

    def test_invalid_segment_is_rejected(self):
        with self.assertRaises(ValidationError):
            TranscriptSegment(id="bad", start=10, end=2, speaker_id="s", text="test", language="ru")

    def test_repository_and_relative_paths_are_rejected(self):
        for path in [str(PROJECT_ROOT), str(PROJECT_ROOT / "data"), "relative-data"]:
            with self.subTest(path=path), patch.dict(os.environ, {"QURYLTAI_DATA_DIR": path}):
                with self.assertRaises(ValueError):
                    get_data_dir()

    def test_onedrive_is_rejected(self):
        path = Path.home() / "OneDrive" / "private-meetings"
        with patch.dict(os.environ, {"QURYLTAI_DATA_DIR": str(path)}):
            with self.assertRaises(ValueError):
                get_data_dir()

    def test_local_path_validation_does_not_create_directory(self):
        path = Path(PROJECT_ROOT.anchor) / "Quryltai-Path-Validation-Only-9c74f"
        with patch.dict(os.environ, {"QURYLTAI_DATA_DIR": str(path)}):
            self.assertEqual(get_data_dir(), path.resolve())
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
