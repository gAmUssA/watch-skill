#!/usr/bin/env bash
# SessionStart hook for /watch — one-line status so users know what's wired up.
# Silent on ready state to avoid spam. Points at the installer when something
# is missing.
set -euo pipefail

CONFIG_FILE="$HOME/.config/watch/.env"

# Warn if the secrets file has loose permissions.
if [[ -f "$CONFIG_FILE" ]]; then
  perms=$(stat -c '%a' "$CONFIG_FILE" 2>/dev/null || stat -f '%Lp' "$CONFIG_FILE" 2>/dev/null || echo "")
  if [[ -n "$perms" && "$perms" != "600" && "$perms" != "400" ]]; then
    echo "/watch: WARNING — $CONFIG_FILE has permissions $perms (should be 600)."
    echo "  Fix: chmod 600 $CONFIG_FILE"
  fi
fi


HAS_FFMPEG=""
HAS_YTDLP=""
command -v ffmpeg >/dev/null 2>&1 && HAS_FFMPEG="yes"
command -v yt-dlp >/dev/null 2>&1 && HAS_YTDLP="yes"

# Local whisper.cpp: the default transcriber (no API key, no upload).
HAS_WHISPER=""
if command -v "${WATCH_WHISPER_CLI:-whisper-cli}" >/dev/null 2>&1 || command -v whisper-cpp >/dev/null 2>&1; then
  MODEL="${WATCH_WHISPER_MODEL:-$HOME/.cache/watch/models/ggml-${WATCH_WHISPER_MODEL_NAME:-large-v3-turbo-q5_0}.bin}"
  [[ -s "$MODEL" ]] && HAS_WHISPER="yes"
fi

# Fully configured → silent (Claude can surface status on demand via --check).
if [[ -n "$HAS_FFMPEG" && -n "$HAS_YTDLP" && -n "$HAS_WHISPER" ]]; then
  exit 0
fi

if [[ -z "$HAS_FFMPEG" || -z "$HAS_YTDLP" ]]; then
  echo "/watch: needs ffmpeg + yt-dlp. Run \`python3 \$CLAUDE_PLUGIN_ROOT/scripts/setup.py\` once to install them and local whisper."
else
  echo "/watch: ready for videos with captions. Run \`python3 \$CLAUDE_PLUGIN_ROOT/scripts/setup.py\` to install local whisper (whisper.cpp) for caption-less videos; no API key needed."
fi
