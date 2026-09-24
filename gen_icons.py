#!/usr/bin/env python3
"""Build herman's icon sprite from Bootstrap Icons.

Run once when the icon set changes; the panel never fetches anything at runtime:

    python3 gen_icons.py [--version 1.13.1] [--out .]

It writes ``icons.svg`` (one <symbol> per name, id ``i-<name>``) and ``icons.LICENSE.txt`` next to
it. The panel serves the sprite inline into the page, so the icons need no font, no extra request
and no relaxation of the content policy.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_VERSION = "1.13.1"
SOURCE = "https://cdn.jsdelivr.net/npm/bootstrap-icons@{version}/icons/{name}.svg"

# Every name the panel references through <use href="#i-name"> or {{ICON:name}}.
ICONS = (
    # navigation
    "speedometer2", "folder2-open", "cpu", "graph-up", "key", "tools", "plug",
    # controls
    "x-lg", "pencil", "check-lg", "check-circle", "x-circle", "plus-lg", "dash-circle",
    "arrow-clockwise", "trash", "play-fill", "box-arrow-up-right", "three-dots",
    # theme
    "sun", "moon-stars",
    # boards
    "shield-check", "search", "globe2", "robot", "hdd-stack", "journal-text", "clock-history",
    "exclamation-triangle", "info-circle", "send", "telegram", "discord", "database", "wifi",
    "wifi-off", "cloud-arrow-down", "diagram-3", "terminal", "list-check", "lock", "unlock",
)

LICENSE = """Bootstrap Icons {version}
Copyright (c) 2019-2024 The Bootstrap Authors
Licensed under the MIT License (https://github.com/twbs/icons/blob/main/LICENSE.md)

The files in icons.svg are the unmodified glyph geometry of the icons named above, repacked as
<symbol> elements for inline use. No other change was made.
"""

SVG_HEAD = '<svg xmlns="http://www.w3.org/2000/svg" style="display:none" aria-hidden="true">'
TITLE_RE = re.compile(r"<title>.*?</title>", re.S)
VIEWBOX_RE = re.compile(r'viewBox="([^"]+)"')


def fetch(name: str, version: str, timeout: int = 20) -> str:
    url = SOURCE.format(version=version, name=name)
    req = urllib.request.Request(url, headers={"User-Agent": "herman-gen-icons"})
    with urllib.request.urlopen(req, timeout=timeout) as res:      # noqa: S310 - fixed https host
        return res.read().decode("utf-8")


def symbol(name: str, svg: str) -> str:
    box = VIEWBOX_RE.search(svg)
    if not box:
        raise ValueError(f"{name}: no viewBox in the upstream file")
    inner = TITLE_RE.sub("", svg[svg.index(">") + 1: svg.rindex("</svg>")]).strip()
    inner = re.sub(r"\s*\n\s*", " ", inner)
    return f'<symbol id="i-{name}" viewBox="{box.group(1)}">{inner}</symbol>'


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="build the Bootstrap Icons sprite herman serves")
    ap.add_argument("--version", default=DEFAULT_VERSION)
    ap.add_argument("--out", default=".")
    args = ap.parse_args(argv[1:])

    out = Path(args.out)
    parts, missing = [], []
    for name in ICONS:
        try:
            parts.append(symbol(name, fetch(name, args.version)))
        except (urllib.error.URLError, ValueError, OSError) as exc:
            missing.append(f"{name}: {exc}")
    if missing:
        print("could not build a complete sprite:")
        for m in missing:
            print("  " + m)
        return 1

    sprite = SVG_HEAD + "".join(parts) + "</svg>"
    (out / "icons.svg").write_text(sprite, encoding="utf-8")
    (out / "icons.LICENSE.txt").write_text(LICENSE.format(version=args.version), encoding="utf-8")
    size = len(sprite.encode())
    print(f"icons.svg       {size} bytes  {len(ICONS)} icons  Bootstrap Icons {args.version}")
    print(f"icons.LICENSE.txt written")
    print("rebuild the page's references with: grep -o 'i-[a-z0-9-]*' index.html | sort -u")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
