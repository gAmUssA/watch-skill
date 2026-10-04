"""Ported from steipete/summarize: summary length presets and frame/transcript windows."""
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

import summary_prompt  # noqa: E402
import timeline  # noqa: E402


class TestSummaryPrompt(unittest.TestCase):
    def test_length_follows_duration(self):
        self.assertEqual(summary_prompt.length_for_duration(480), "long")
        self.assertEqual(summary_prompt.length_for_duration(1800), "xl")
        self.assertEqual(summary_prompt.length_for_duration(6270), "xxl")

    def test_hint_caps_length_at_transcript_size(self):
        hint = summary_prompt.pending_hint(480, transcript_chars=12000)
        self.assertIn("12,000 characters; never exceed", hint)
        self.assertIn("sponsor", hint)


class TestTimeline(unittest.TestCase):
    segs = [
        {"start": 0.0, "end": 4.0, "text": "intro words"},
        {"start": 4.0, "end": 9.0, "text": "first topic"},
        {"start": 9.0, "end": 14.0, "text": "second topic"},
    ]

    def test_window_runs_to_next_frame_with_lead_in(self):
        frames = [{"path": "a.jpg", "timestamp_seconds": 5.0},
                  {"path": "b.jpg", "timestamp_seconds": 10.0}]
        out = timeline.build_timeline(frames, self.segs, "long", 14.0)
        self.assertEqual(out[0]["text"], "intro words first topic second topic")
        self.assertEqual(out[1]["text"], "second topic")

    def test_rolling_caption_overlap_is_merged(self):
        self.assertEqual(
            timeline.merge_rolling(["you want to be able to create", "to be able to create branches on the fly"]),
            "you want to be able to create branches on the fly",
        )

    def test_text_budget_truncates_on_a_word_boundary(self):
        self.assertEqual(timeline.truncate("alpha beta gamma delta", 12), "alpha beta...")

    def test_long_videos_are_subsampled_evenly(self):
        frames = [{"path": f"{i}.jpg", "timestamp_seconds": float(i)} for i in range(100)]
        picked = timeline.pick_frames(frames, limit=5)
        self.assertEqual([f["timestamp_seconds"] for f in picked], [0.0, 25.0, 50.0, 74.0, 99.0])


if __name__ == "__main__":
    unittest.main()
