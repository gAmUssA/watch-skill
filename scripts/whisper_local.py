#!/usr/bin/env python3
"""Local Whisper transcription via whisper.cpp (`whisper-cli`). No API key, no upload.

The default transcription backend for this fork: audio never leaves the
machine and costs nothing. Cloud backends (Groq/OpenAI in whisper.py) are
opt-in only.

Model: a ggml file from huggingface.co/ggerganov/whisper.cpp, stored under
~/.cache/watch/models/. Override with WATCH_WHISPER_MODEL (absolute path to a
.bin) or WATCH_WHISPER_MODEL_NAME (e.g. "base.en", "large-v3-turbo").
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen

DEFAULT_MODEL_NAME = "large-v3-turbo-q5_0"  # ~550 MB, fast on Apple Silicon (Metal)
MODELS_DIR = Path.home() / ".cache" / "watch" / "models"
MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-{name}.bin"
CLI_NAMES = ("whisper-cli", "whisper-cpp")


def cli_path() -> str | None:
    override = os.environ.get("WATCH_WHISPER_CLI")
    if override and shutil.which(override):
        return shutil.which(override)
    for name in CLI_NAMES:
        found = shutil.which(name)
        if found:
            return found
    return None


def model_name() -> str:
    return os.environ.get("WATCH_WHISPER_MODEL_NAME", "").strip() or DEFAULT_MODEL_NAME


def model_path() -> Path:
    explicit = os.environ.get("WATCH_WHISPER_MODEL", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    return MODELS_DIR / f"ggml-{model_name()}.bin"


def available() -> tuple[bool, str]:
    """(ready, reason). Ready means whisper-cli is on PATH and the model file exists."""
    if cli_path() is None:
        return False, "whisper-cli not found (macOS: brew install whisper-cpp)"
    path = model_path()
    if not path.exists() or path.stat().st_size == 0:
        return False, f"model not downloaded: {path} (run setup.py --download-model)"
    return True, "ok"


def download_model(name: str | None = None) -> Path:
    """Download a ggml model into MODELS_DIR. Atomic: writes .part then renames."""
    name = name or model_name()
    dest = MODELS_DIR / f"ggml-{name}.bin"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    url = MODEL_URL.format(name=name)
    part = dest.with_suffix(".bin.part")
    print(f"[watch] downloading whisper model {name} from {url}", file=sys.stderr)
    with urlopen(url, timeout=60) as resp, open(part, "wb") as fh:
        shutil.copyfileobj(resp, fh, length=1 << 20)
    part.replace(dest)
    return dest


def _to_wav(audio_path: Path, wav_path: Path) -> Path:
    """whisper-cli wants 16 kHz mono PCM WAV."""
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg is required for local transcription")
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(audio_path), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
         str(wav_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"ffmpeg wav conversion failed: {result.stderr.strip()}")
    return wav_path


def parse_cli_json(data: dict) -> list[dict]:
    """whisper-cli -oj output → [{start, end, text}] in seconds, empty pieces dropped."""
    out: list[dict] = []
    for item in data.get("transcription") or []:
        text = (item.get("text") or "").strip()
        if not text:
            continue
        offsets = item.get("offsets") or {}
        out.append({
            "start": round(float(offsets.get("from") or 0) / 1000.0, 3),
            "end": round(float(offsets.get("to") or 0) / 1000.0, 3),
            "text": text,
        })
    return out


def transcribe(audio_path: Path, word_timestamps: bool = False) -> tuple[list[dict], list[dict]]:
    """Transcribe locally. Returns (segments, words); words empty unless requested."""
    ready, reason = available()
    if not ready:
        raise SystemExit(f"local whisper unavailable: {reason}")
    cli = cli_path()
    model = model_path()
    language = os.environ.get("WATCH_WHISPER_LANGUAGE", "auto")

    with tempfile.TemporaryDirectory(prefix="watch-whisper-") as tmp:
        tmpdir = Path(tmp)
        wav = _to_wav(Path(audio_path), tmpdir / "audio.wav")

        def run(extra: list[str], stem: str) -> dict:
            out_base = tmpdir / stem
            cmd = [cli, "-m", str(model), "-f", str(wav), "-l", language,
                   "-oj", "-of", str(out_base), "-np", *extra]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise SystemExit(f"whisper-cli failed: {result.stderr.strip()[-500:]}")
            json_path = out_base.with_suffix(".json")
            if not json_path.exists():
                raise SystemExit("whisper-cli produced no JSON output")
            return json.loads(json_path.read_text(encoding="utf-8", errors="replace"))

        segments = parse_cli_json(run([], "segments"))
        words: list[dict] = []
        if word_timestamps:
            words = [
                {"word": seg["text"], "start": seg["start"], "end": seg["end"]}
                for seg in parse_cli_json(run(["-ml", "1", "-sow"], "words"))
            ]
    return segments, words


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--download":
        print(download_model(sys.argv[2] if len(sys.argv) > 2 else None))
        raise SystemExit(0)
    if len(sys.argv) < 2:
        print("usage: whisper_local.py <audio> | --download [model-name]", file=sys.stderr)
        raise SystemExit(2)
    segs, _ = transcribe(Path(sys.argv[1]))
    print(json.dumps(segs, indent=2))
