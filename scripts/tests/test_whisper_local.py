"""Local-first transcription: whisper.cpp output parsing and backend resolution."""
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

import whisper  # noqa: E402
import whisper_local  # noqa: E402


class TestParseCliJson(unittest.TestCase):
    def test_converts_ms_offsets_and_drops_empty_pieces(self):
        data = {"transcription": [
            {"offsets": {"from": 0, "to": 50}, "text": ""},
            {"offsets": {"from": 50, "to": 1120}, "text": " Hi everyone."},
        ]}
        self.assertEqual(
            whisper_local.parse_cli_json(data),
            [{"start": 0.05, "end": 1.12, "text": "Hi everyone."}],
        )


class TestResolveBackend(unittest.TestCase):
    def test_local_wins_by_default_even_with_a_key(self):
        with mock.patch.object(whisper_local, "available", return_value=(True, "ok")), \
             mock.patch.object(whisper, "load_api_key", return_value=("openai", "sk-x")):
            self.assertEqual(whisper.resolve_backend()[:2], ("local", None))

    def test_key_alone_never_triggers_an_upload(self):
        with mock.patch.object(whisper_local, "available", return_value=(False, "no model")), \
             mock.patch.object(whisper, "load_api_key", return_value=("openai", "sk-x")), \
             mock.patch.object(whisper, "_config_flag", return_value=False):
            self.assertEqual(whisper.resolve_backend()[:2], (None, None))

    def test_allow_api_flag_enables_cloud_fallback(self):
        with mock.patch.object(whisper_local, "available", return_value=(False, "no model")), \
             mock.patch.object(whisper, "load_api_key", return_value=("groq", "gsk")), \
             mock.patch.object(whisper, "_config_flag", return_value=True):
            self.assertEqual(whisper.resolve_backend()[:2], ("groq", "gsk"))

    def test_explicit_cloud_request_uses_that_key(self):
        with mock.patch.object(whisper, "load_api_key", return_value=("openai", "sk-x")):
            self.assertEqual(whisper.resolve_backend("openai")[:2], ("openai", "sk-x"))


if __name__ == "__main__":
    unittest.main()
