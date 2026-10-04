#!/usr/bin/env python3
"""Frame timeline: each frame paired with what's said while it's on screen.

Ported from steipete/summarize (MIT, (c) 2026 Peter Steinberger),
packages/core/src/slides/text-transcript.ts: a transcript window starts at the
frame (with a short lead-in) and runs until the next frame, clamped to a
per-length budget of seconds and characters.
"""
from __future__ import annotations

import re

WINDOW_SECONDS = {"long": 90, "xl": 120, "xxl": 180}
TEXT_BUDGET = {"long": 320, "xl": 480, "xxl": 700}
LEAD_IN_SECONDS = 3.0
MAX_ENTRIES = 24


def _fmt(seconds: float) -> str:
    s = max(0, int(seconds))
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


def truncate(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rstrip()
    cut = re.sub(r"\s+\S*$", "", cut).strip() or cut
    return f"{cut}..."


def merge_rolling(texts: list[str]) -> str:
    """Join caption lines, dropping the words a line repeats from the end of the previous one.

    YouTube rolling captions restate the tail of each cue at the start of the next.
    """
    words: list[str] = []
    for text in texts:
        new = text.split()
        if not new:
            continue
        overlap = 0
        for k in range(min(len(words), len(new)), 0, -1):
            if [w.lower() for w in words[-k:]] == [w.lower() for w in new[:k]]:
                overlap = k
                break
        words.extend(new[overlap:])
    return " ".join(words)


def pick_frames(frames: list[dict], limit: int = MAX_ENTRIES) -> list[dict]:
    """Evenly spaced subset in time order, so long videos don't produce huge timelines."""
    ordered = sorted(frames, key=lambda f: f.get("timestamp_seconds", 0.0))
    if len(ordered) <= limit:
        return ordered
    step = (len(ordered) - 1) / (limit - 1)
    return [ordered[round(i * step)] for i in range(limit)]


def build_timeline(frames: list[dict], segments: list[dict], preset: str,
                   duration_seconds: float) -> list[dict]:
    """Return [{path, timestamp, text}] with the transcript excerpt for each frame."""
    window = WINDOW_SECONDS.get(preset, 120)
    budget = TEXT_BUDGET.get(preset, 480)
    chosen = pick_frames(frames)
    out = []
    for i, frame in enumerate(chosen):
        start = float(frame.get("timestamp_seconds", 0.0))
        next_start = (float(chosen[i + 1].get("timestamp_seconds", duration_seconds))
                      if i + 1 < len(chosen) else duration_seconds)
        end = min(next_start, start + window)
        # Lines are assigned by start time so neighbouring frames don't repeat
        # them; the first frame also takes anything said before it.
        lo = 0.0 if i == 0 else max(0.0, start - LEAD_IN_SECONDS)
        words = [seg.get("text", "").strip() for seg in segments
                 if lo <= seg.get("start", 0) < end]
        out.append({
            "path": frame["path"],
            "timestamp": start,
            "text": truncate(merge_rolling(words), budget),
        })
    return out


def render(entries: list[dict]) -> list[str]:
    """Markdown lines: timestamp, image, excerpt per frame."""
    lines: list[str] = []
    for entry in entries:
        lines.append(f"**[{_fmt(entry['timestamp'])}]**")
        lines.append("")
        lines.append(f"![frame at {_fmt(entry['timestamp'])}]({entry['path']})")
        lines.append("")
        lines.append(entry["text"] or "_(no speech)_")
        lines.append("")
    return lines
