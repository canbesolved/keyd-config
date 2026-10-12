#!/usr/bin/env bash
# Regenerate assets/layout.svg after an agent edits the keyd config or the generator.
# Shared by Cursor (afterFileEdit) and Claude Code (PostToolUse); both send JSON on stdin.
# Fails open: it never blocks the edit, problems are reported on stderr.

cd "$(dirname "$0")/../.." || exit 0

file_path=$(python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except ValueError:
    sys.exit()
print(data.get("file_path") or (data.get("tool_input") or {}).get("file_path") or "")
' 2>/dev/null)

case "$file_path" in
  */default.conf | default.conf | */scripts/draw_layout.py | scripts/draw_layout.py) ;;
  *) echo '{}'; exit 0 ;;
esac

uv_bin=$(command -v uv || ls "$HOME/.local/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv 2>/dev/null | head -n 1)
if [ -z "$uv_bin" ]; then
  echo "regenerate-layout: uv not found, run 'uv run scripts/draw_layout.py' manually" >&2
  echo '{}'
  exit 0
fi

"$uv_bin" run --quiet scripts/draw_layout.py >&2 ||
  echo "regenerate-layout: layout image generation failed" >&2
echo '{}'
exit 0
