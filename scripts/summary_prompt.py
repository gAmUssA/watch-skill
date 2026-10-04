#!/usr/bin/env python3
"""Rules for the report's "Full summary" section.

Adapted from steipete/summarize (MIT, (c) 2026 Peter Steinberger):
packages/core/src/prompts/summary-system.ts, summary-lengths.ts and
link-summary.ts. Only the video/transcript path is ported; the agent running
/watch writes the section itself, so no extra model call or API key is used.
"""
from __future__ import annotations

# (preset, guidance, formatting, target_chars, min_chars, max_chars)
LENGTH_SPECS = {
    "long": (
        "Write a detailed summary that prioritizes the most important points first, followed by "
        "key supporting facts or events, then secondary details or conclusions stated in the source.",
        "Use up to 3 short paragraphs of 2-4 sentences.",
        4200, 2500, 6000,
    ),
    "xl": (
        "Write a detailed summary that captures the main points, supporting facts, and concrete "
        "numbers or quotes when present.",
        "Use 2-5 short paragraphs of 2-4 sentences.",
        9000, 6000, 14000,
    ),
    "xxl": (
        "Write a comprehensive summary that covers background, main points, evidence, and stated "
        "outcomes in the source; do not add implications or recommendations the source doesn't state.",
        "Use 3-7 short paragraphs of 2-4 sentences.",
        17000, 14000, 22000,
    ),
}


def length_for_duration(duration_seconds: float) -> str:
    """Pick a length preset from video length: <=10 min long, <=60 min xl, longer xxl."""
    if duration_seconds <= 600:
        return "long"
    if duration_seconds <= 3600:
        return "xl"
    return "xxl"


def summary_rules(duration_seconds: float, transcript_chars: int = 0) -> list[str]:
    """The instructions the agent follows when filling "## Full summary"."""
    preset = length_for_duration(duration_seconds)
    guidance, formatting, target, low, high = LENGTH_SPECS[preset]
    rules = [
        f"Length preset {preset}. {guidance} {formatting}",
        f"Target about {target:,} characters (range {low:,}-{high:,}); a soft guideline, clarity first.",
    ]
    if transcript_chars:
        rules.append(
            f"The transcript is {transcript_chars:,} characters; never exceed that. If the target is "
            "larger, finish early instead of padding."
        )
    rules += [
        "Audience: a curious reader who wants the key ideas before deciding whether to watch.",
        "Lead with the central claim or takeaway, then group supporting details by theme or "
        "chronology. Use at least 3 '### ' headings, starting with one; never bold as a heading.",
        "Keep paragraphs short; use a short bullet list when the source enumerates steps or items.",
        "Include 1-2 exact excerpts (max 25 words each) in single-asterisk italics when the source "
        "has a strong line. Straight quotes only.",
        "Omit sponsor reads, ads, promos and calls to action entirely; don't mention skipping them.",
        "Base everything strictly on the transcript and frames; never invent details. No emojis, "
        "disclaimers or speculation.",
        "Don't repeat the Key moments list here; the report already has one.",
    ]
    return rules


def pending_hint(duration_seconds: float, transcript_chars: int = 0) -> str:
    return "Full summary. " + " ".join(summary_rules(duration_seconds, transcript_chars))
