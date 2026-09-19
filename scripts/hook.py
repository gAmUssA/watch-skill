#!/usr/bin/env python3
"""Hook microscope: dense frames + word-level transcript over [0, 10s].

The first 10 seconds is where every retention curve gets decided. Treating
them like any other 10 seconds wastes the highest-leverage analysis budget.
This module re-runs frame extraction at 2 fps over the hook range and asks
Whisper for word-level timestamps so the reporter can align each frame to
the exact word being spoken.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from frames import extract  # noqa: E402
from whisper import load_api_key, transcribe_audio  # noqa: E402


HOOK_DURATION_SECONDS = 10.0
HOOK_FPS = 2.0


def analyse_hook(
    video_path: str,
    out_dir: Path,
    backend: str | None = None,
    api_key: str | None = None,
    full_video_duration: float = 0.0,
    allow_whisper: bool = True,
) -> dict:
    """Run hook microscope. Returns {frames, words, segments, ran}."""
    if full_video_duration > 0 and full_video_duration < 30.0:
        return {"frames": [], "words": [], "segments": [], "ran": False,
                "skipped_reason": "video <30s"}

    out_dir.mkdir(parents=True, exist_ok=True)
    hook_frames_dir = out_dir / "hook_frames"
    hook_frames = extract(
        video_path, hook_frames_dir,
        fps=HOOK_FPS, resolution=512, max_frames=25,
        start_seconds=0.0, end_seconds=HOOK_DURATION_SECONDS,
    )

    words: list[dict] = []
    segments: list[dict] = []
    if not allow_whisper:
        # --no-whisper means "do not send my audio anywhere". Re-detecting a
        # key here would silently upload the first 10s despite the opt-out.
        backend, api_key = None, None
    elif backend is None or api_key is None:
        backend, api_key = load_api_key()

    if backend and api_key:
        try:
            if shutil.which("ffmpeg") is None:
                raise SystemExit("ffmpeg required for hook microscope")
            hook_audio = out_dir / "hook_audio.mp3"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(Path(video_path).resolve()),
                "-vn", "-acodec", "libmp3lame", "-ar", "16000",
                "-ac", "1", "-b:a", "64k",
                "-t", str(HOOK_DURATION_SECONDS),
                str(hook_audio.resolve()),
            ], check=True, capture_output=True)
            segments, _, words = transcribe_audio(
                hook_audio, backend=backend, api_key=api_key,
                word_timestamps=True,
            )
        except SystemExit as exc:
            print(f"[hook] whisper failed: {exc}", file=sys.stderr)
        except subprocess.CalledProcessError as exc:
            print(f"[hook] ffmpeg slice failed: {exc.stderr}", file=sys.stderr)

    return {
        "frames": hook_frames,
        "words": words,
        "segments": segments,
        "ran": True,
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: hook.py <video-path> <out-dir>", file=sys.stderr)
        raise SystemExit(2)
    result = analyse_hook(sys.argv[1], Path(sys.argv[2]))
    print(json.dumps(result, indent=2, default=str))
