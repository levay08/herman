#!/usr/bin/env bash
# The panel's JavaScript must PARSE. A syntax error in one branch takes the whole module down, and the
# page then renders nothing at all (exactly what "the panel is empty" looks like), while every API
# route keeps answering: the panel battery cannot see it, this can.
set -u
cd "$(dirname "$0")"
python3 - <<'PY'
import re, sys
html = open("index.html", encoding="utf-8").read()
blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S)
big = [b for b in blocks if len(b) > 200]
open("/tmp/herman_panel_check.js", "w", encoding="utf-8").write("\n".join(big))
print(f"  script blocks: {len(blocks)} ({len(big)} inline, {sum(len(b) for b in big)} chars)")
PY
if command -v node >/dev/null 2>&1; then
  if node --check /tmp/herman_panel_check.js 2>/tmp/herman_panel_check.err; then
    echo "  ✓ the panel's JavaScript parses (node --check)"
    exit 0
  fi
  echo "  ✗ SYNTAX ERROR in the panel's JavaScript:"
  sed 's/^/      /' /tmp/herman_panel_check.err | head -12
  exit 1
fi
echo "  ! node is not installed: the syntax check was skipped"
exit 0
