"""Regressions for defects found auditing v0.2.0 before install.

Each test fails against the code as it stood before its paired fix.
"""
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

import frames  # noqa: E402
import hook as hook_mod  # noqa: E402
from report import write_report  # noqa: E402


class TestFfmpegNineCompat(unittest.TestCase):
    """ffmpeg 7+ removed -vsync; hardcoding it aborted every scene-change run."""

    def test_frames_never_passes_removed_vsync_flag(self):
        source = (SCRIPT_DIR / "frames.py").read_text(encoding="utf-8")
        self.assertNotIn('"-vsync"', source)
        self.assertIn('"-fps_mode", "vfr"', source)


class TestNoWhisperIsHonoured(unittest.TestCase):
    """--no-whisper must mean no audio leaves the machine, hook pass included."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="watch-hook-test-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_allow_whisper_false_never_loads_a_key_or_uploads(self):
        with mock.patch.object(hook_mod, "extract", return_value=[]), \
             mock.patch.object(hook_mod, "load_api_key") as load_key, \
             mock.patch.object(hook_mod, "transcribe_audio") as upload, \
             mock.patch.object(hook_mod.subprocess, "run") as ffmpeg:
            result = hook_mod.analyse_hook(
                "video.mp4", self.tmp,
                backend=None, api_key=None,
                full_video_duration=120.0,
                allow_whisper=False,
            )
        load_key.assert_not_called()
        upload.assert_not_called()
        ffmpeg.assert_not_called()
        self.assertEqual(result["words"], [])

    def test_default_still_detects_a_key(self):
        with mock.patch.object(hook_mod, "extract", return_value=[]), \
             mock.patch.object(hook_mod, "load_api_key", return_value=("groq", "k")) as load_key, \
             mock.patch.object(hook_mod, "transcribe_audio", return_value=([], None, [])), \
             mock.patch.object(hook_mod.subprocess, "run"):
            hook_mod.analyse_hook(
                "video.mp4", self.tmp,
                full_video_duration=120.0,
            )
        load_key.assert_called_once()


class TestFrontmatterQuoting(unittest.TestCase):
    """A hostile video title must not be able to restructure the YAML."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="watch-yaml-test-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, title):
        return write_report(
            out_path=self.tmp / "report.md",
            source="https://youtu.be/x",
            title=title,
            duration_seconds=60.0,
            intent="test",
            transcript_segments=[],
            transcript_source=None,
            all_frames=[],
            hero_frames=[],
            pacing={"shot_count": 0, "cuts_per_min": 0.0, "mean_shot_length": 0.0,
                    "median_shot_length": 0.0, "shots": []},
            hook={"frames": [], "words": [], "ran": False, "skipped_reason": "n/a"},
        )

    def test_colon_in_title_does_not_split_the_key(self):
        out = self._write("Breaking: everything")
        self.assertIn('title: "Breaking: everything"', out.read_text(encoding="utf-8"))

    def test_newline_in_title_cannot_inject_a_key(self):
        out = self._write("Evil\nowner: attacker")
        text = out.read_text(encoding="utf-8")
        self.assertNotIn("\nowner: attacker", text)
        self.assertIn('\n', text)

    def test_newline_in_title_does_not_break_the_h1(self):
        out = self._write("Evil\nowner: attacker")
        body = out.read_text(encoding="utf-8").split("---", 2)[2]
        self.assertIn("# Evil owner: attacker", body)

    def test_frontmatter_parses_as_yaml_with_a_hostile_title(self):
        yaml = None
        try:
            import yaml  # noqa: F811
        except ImportError:
            self.skipTest("PyYAML not installed")
        out = self._write('He said "hi": *anchor & more')
        block = out.read_text(encoding="utf-8").split("---")[1]
        parsed = yaml.safe_load(block)
        self.assertEqual(parsed["title"], 'He said "hi": *anchor & more')


if __name__ == "__main__":
    unittest.main()
