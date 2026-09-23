import json
import os
import unittest
from datetime import date
from unittest.mock import patch
from urllib.error import URLError

from src.llm.base import LLMProvider, LLMProviderError
from src.llm.ollama import OllamaProvider
from src.config import get_ollama_settings
from src.schemas import MeetingMetadata, MeetingUnderstanding
from src.understanding import SYSTEM_PROMPT, prepare_text_transcript, run_text_pipeline


MIXED_TRANSCRIPT = """Айгерім: Тимур, подготовь бюджет до пятницы.
Тимур: Жақсы, жұмаға дейін дайындаймын.
Дана: Ещё нужно проверить договор, бірақ жауапты адам әлі жоқ.
Айгерім: Пилотты бес дүкенмен бастаймыз."""


VALID_OUTPUT = {
    "action_items": [
        {
            "assignee": "Тимур",
            "task": "Подготовить бюджет",
            "deadline_original": "до пятницы",
            "deadline_normalized": "2026-09-25",
            "evidence_segment_ids": ["seg_1"],
            "source_quote": "Тимур, подготовь бюджет до пятницы.",
            "confidence": 0.98,
        },
        {
            "assignee": None,
            "task": "Проверить договор",
            "deadline_original": None,
            "deadline_normalized": None,
            "evidence_segment_ids": ["seg_3"],
            "source_quote": "Ещё нужно проверить договор, бірақ жауапты адам әлі жоқ.",
            "confidence": 0.72,
        },
    ],
    "summary": {
        "overall_summary": "Команда согласовала пилот и обсудила бюджет пен шартты тексеру.",
        "main_topics": ["Бюджет", "Пилот", "Договор"],
        "key_problems": ["Для проверки договора не назначен ответственный"],
        "decisions": ["Пилотты бес дүкенмен бастау"],
    },
}


class FakeProvider(LLMProvider):
    def __init__(self, output):
        self.output = output
        self.last_system_prompt = None
        self.last_user_prompt = None

    def healthcheck(self):
        return None

    def generate_structured(self, *, system_prompt, user_prompt, response_model):
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return response_model.model_validate(self.output)


class StubOllama(OllamaProvider):
    response_content: str = ""

    def healthcheck(self):
        return None

    def _request(self, path, payload=None, *, timeout=None):
        return {"message": {"content": self.response_content}}


class UnderstandingTests(unittest.TestCase):
    def metadata(self):
        return MeetingMetadata(
            title="Смешанная встреча", meeting_date=date(2026, 9, 23),
            participants=["Айгерім", "Тимур", "Дана"],
        )

    def test_mixed_transcript_structured_output_and_nulls(self):
        provider = FakeProvider(VALID_OUTPUT)
        stages = []
        protocol = run_text_pipeline(self.metadata(), MIXED_TRANSCRIPT, provider, stages.append)
        self.assertFalse(protocol.is_demo)
        self.assertEqual(stages, ["prepare_transcript", "extract_tasks", "generate_summary", "generate_protocol"])
        self.assertEqual(protocol.action_items[0].assignee, "Тимур")
        self.assertEqual(protocol.action_items[0].deadline_normalized, date(2026, 9, 25))
        self.assertIsNone(protocol.action_items[1].assignee)
        self.assertIsNone(protocol.action_items[1].deadline_original)
        self.assertIsNone(protocol.action_items[1].deadline_normalized)
        self.assertIn("Russian, Kazakh", provider.last_system_prompt)
        self.assertIn("[seg_3] Дана:", provider.last_user_prompt)

    def test_speaker_lines_are_preserved(self):
        segments, speakers = prepare_text_transcript("[Алия]: Сәлем!\nБорис: Добрый день.")
        self.assertEqual([speaker.name for speaker in speakers], ["Алия", "Борис"])
        self.assertEqual([segment.text for segment in segments], ["Сәлем!", "Добрый день."])

    def test_malformed_ollama_output_is_rejected(self):
        provider = StubOllama()
        provider.response_content = "this is not JSON"
        with self.assertRaises(LLMProviderError):
            provider.generate_structured(
                system_prompt="local", user_prompt="local", response_model=MeetingUnderstanding,
            )

    def test_unknown_assignee_is_rejected(self):
        output = {**VALID_OUTPUT, "action_items": [{**VALID_OUTPUT["action_items"][0], "assignee": "Несуществующий человек"}]}
        with self.assertRaisesRegex(LLMProviderError, "assignee not found"):
            run_text_pipeline(self.metadata(), MIXED_TRANSCRIPT, FakeProvider(output))

    def test_invented_deadline_is_rejected(self):
        output = {**VALID_OUTPUT, "action_items": [{**VALID_OUTPUT["action_items"][1], "deadline_original": "через месяц"}]}
        with self.assertRaisesRegex(LLMProviderError, "deadline phrase"):
            run_text_pipeline(self.metadata(), MIXED_TRANSCRIPT, FakeProvider(output))

    def test_non_loopback_ollama_url_is_rejected(self):
        with self.assertRaises(ValueError):
            OllamaProvider(base_url="https://example.com")

    def test_documented_quryltay_model_alias_is_accepted(self):
        environment = {
            "OLLAMA_BASE_URL": " http://127.0.0.1:11434/ ",
            "QURYLTAY_OLLAMA_MODEL": " qwen3:4b-instruct-2507-q4_K_M ",
        }
        with patch.dict(os.environ, environment, clear=True):
            self.assertEqual(
                get_ollama_settings(),
                ("http://127.0.0.1:11434/", "qwen3:4b-instruct-2507-q4_K_M", 300.0),
            )

    def test_ollama_timeout_is_configurable(self):
        environment = {"QURYLTAI_OLLAMA_TIMEOUT_SECONDS": "420"}
        with patch.dict(os.environ, environment, clear=True):
            _, _, timeout_seconds = get_ollama_settings()
        self.assertEqual(timeout_seconds, 420.0)

    def test_invalid_ollama_timeout_is_rejected(self):
        for value in ("not-a-number", "0", "-1", "nan", "inf"):
            with self.subTest(value=value), patch.dict(
                os.environ, {"QURYLTAI_OLLAMA_TIMEOUT_SECONDS": value}, clear=True,
            ):
                with self.assertRaisesRegex(ValueError, "positive number"):
                    get_ollama_settings()

    def test_provider_default_generation_timeout_is_five_minutes(self):
        self.assertEqual(OllamaProvider().timeout_seconds, 300.0)

    def test_generation_uses_configured_timeout_without_output_cap(self):
        provider = OllamaProvider(timeout_seconds=420.0)
        output = json.dumps({
            "action_items": [],
            "summary": {
                "overall_summary": "Complete",
                "main_topics": [],
                "key_problems": [],
                "decisions": [],
            },
        })
        with patch.object(provider, "healthcheck"), patch.object(
            provider, "_request", return_value={"message": {"content": output}},
        ) as request:
            provider.generate_structured(
                system_prompt="local", user_prompt="local", response_model=MeetingUnderstanding,
            )
        path, payload = request.call_args.args
        self.assertEqual(path, "/api/chat")
        self.assertEqual(request.call_args.kwargs["timeout"], 420.0)
        self.assertNotIn("num_predict", payload["options"])

    def test_unavailable_ollama_has_setup_instructions(self):
        provider = OllamaProvider()
        with patch("src.llm.ollama._open_loopback", side_effect=URLError("offline")):
            with self.assertRaisesRegex(LLMProviderError, r"unavailable at http://127\.0\.0\.1:11434.*offline"):
                provider.healthcheck()

    def test_healthcheck_recognizes_configured_model_from_tags(self):
        provider = OllamaProvider(model="qwen3:4b-instruct-2507-q4_K_M")
        tags = {
            "models": [{
                "name": "qwen3:4b-instruct-2507-q4_K_M",
                "model": "qwen3:4b-instruct-2507-q4_K_M",
            }],
        }
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(tags).encode()
        with patch("src.llm.ollama._open_loopback", return_value=response) as open_loopback:
            provider.healthcheck()
        request = open_loopback.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/tags")

    def test_generation_connection_error_is_not_reported_as_healthcheck_failure(self):
        provider = OllamaProvider()
        with patch.object(provider, "healthcheck"), patch(
            "src.llm.ollama._open_loopback", side_effect=TimeoutError("generation timed out"),
        ):
            with self.assertRaisesRegex(LLMProviderError, r"/api/chat failed.*generation timed out"):
                provider.generate_structured(
                    system_prompt="local", user_prompt="local", response_model=MeetingUnderstanding,
                )

    def test_loopback_opener_disables_proxies(self):
        request = unittest.mock.MagicMock()
        opener = unittest.mock.MagicMock()
        with patch("src.llm.ollama.build_opener", return_value=opener) as build:
            from src.llm.ollama import _open_loopback

            _open_loopback(request, 5.0)
        proxy_handler = build.call_args.args[0]
        self.assertEqual(proxy_handler.proxies, {})
        opener.open.assert_called_once_with(request, timeout=5.0)

    def test_prompt_contains_no_invention_rules(self):
        self.assertIn("Never invent a responsible person", SYSTEM_PROMPT)
        self.assertIn("Never invent a deadline", SYSTEM_PROMPT)
        self.assertIn("до пятницы", SYSTEM_PROMPT)
        self.assertIn("келесі аптада", SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
