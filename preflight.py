#!/usr/bin/env python3
"""Pre-flight check before publishing herman to a public repository.

Scans the files that would be published and reports anything that looks like operator data:
personal paths, host names, provider names, session ids, secrets or the author's own forked
catalog file. Exit code 1 when a blocking finding is present, so it can gate a release.

Usage:  python3 preflight.py [path ...]
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

DEFAULT_FILES = [
    Path.home() / ".local" / "bin" / "herman",
    Path.home() / ".local" / "share" / "herman" / "index.html",
    Path.home() / ".local" / "share" / "bash-completion" / "completions" / "herman",
]

# (label, pattern, severity) -- "block" stops a release, "warn" is a judgement call.
RULES = [
    ("personal path", r"/home/[a-z0-9._-]+|/Users/[A-Za-z0-9._-]+|C:\\\\Users\\\\", "block"),
    ("private host or IP", r"\b(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}\b", "block"),
    ("session id", r"\b20\d{6}_\d{6}_[0-9a-f]{4,}\b", "block"),
    ("secret-looking token", r"\b(?:sk|pk|ghp|gho|AIza|hf)_?[A-Za-z0-9_-]{12,}\b", "block"),
    ("email address", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "warn"),
    ("provider domain", r"\b(?:paas\.id|openrouter\.ai|api\.openai\.com|anthropic\.com)\b", "warn"),
    ("author name", r"\bLevay\b", "warn"),
    ("indonesian word", r"(?<![A-Za-z])(dengan|untuk|tidak|belum|riwayat|pemakaian|pesan|sesi|hari|"
                        r"terakhir|pertama|angka|gagal|dimuat|nama|mencari|berpikir|lintas|pangsa|"
                        r"estimasi|aktif|harga|kapan|contoh|jumlah|panggilan)(?![A-Za-z])", "warn"),
    ("placeholder that hints at a private project",
     r"\btitik\s?rusak\b|(?<![\w.-])hero(?![\w-])|/var/www/[a-z]", "block"),
]

# Allowed places for an otherwise suspicious token: localhost URLs, documentation IPs, example
# domains, and the CSS tokens / JS identifiers that merely look like a rule hit.
ALLOW = [
    r"127\.0\.0\.1", r"0\.0\.0\.0", r"localhost",
    r"\b(?:203|198|192)\.0\.2\.\d+\b",          # RFC 5737 documentation addresses
    r"example\.(?:com|org|net)", r"\b10\.0\.0\.5\b",
    r"@example\.(?:com|org)", r"you@", r"user@",
    r'class="[^"]*\bhero\b', r"\.hero\b", r"--hero-", r"hero-",
    r"/home/(?:me|you|user|someone)\b", r"~/Projects",
    r"/home/herman\b",            # the unprivileged user inside the published container image
]


def strip_own_rules(text: str, path: Path) -> str:
    """Blank the scanner's own RULES/ALLOW blocks when it scans itself.

    The words and regexes it looks for appear verbatim in this file, so a self-scan would report the
    pattern list as operator data and block every release over a file that holds no data at all. The
    line count is preserved so reported line numbers still match the real file.

    The name decides as well as the path: the release gate runs the INSTALLED scanner over the
    PUBLISHED copy in the working tree, so comparing paths alone made that run report a blocking
    finding against the scanner's own rule list (the docstring quotes nothing it hunts for).
    """
    try:
        if path.resolve() != Path(__file__).resolve() and path.name != Path(__file__).name:
            return text
    except OSError:
        return text
    out: list[str] = []
    skipping = False
    for line in text.split("\n"):
        if re.match(r"^(?:RULES|ALLOW)\s*=\s*\[", line):
            skipping = True
            out.append("")
            continue
        if skipping:
            if line.startswith("]"):
                skipping = False
            out.append("")
            continue
        out.append(line)
    return "\n".join(out)


def scan(path: Path) -> list[tuple[str, str, int, str]]:
    try:
        text = strip_own_rules(path.read_text(encoding="utf-8"), path)
    except (OSError, UnicodeDecodeError):
        return []        # unreadable or binary (caduceus.png): nothing textual to grep for
    findings: list[tuple[str, str, int, str]] = []
    for label, pattern, severity in RULES:
        rx = re.compile(pattern)
        for match in rx.finditer(text):
            token = match.group(0)
            window = text[max(0, match.start() - 60):match.end() + 60]
            if any(re.search(a, window) for a in ALLOW):
                continue
            line = text[: match.start()].count("\n") + 1
            findings.append((label, token, line, severity))
    return findings


def main(argv: list[str]) -> int:
    files = [Path(a) for a in argv[1:]] or [p for p in DEFAULT_FILES if p.exists()]
    if not files:
        print("nothing to scan: pass the files, or install herman first")
        return 2
    blocking = 0
    warnings = 0
    for path in files:
        findings = scan(path)
        print("=" * 78)
        print(f"{path}  ({os.path.getsize(path) if path.exists() else 0} bytes)")
        if not findings:
            print("   clean: no operator data found")
            continue
        for label, token, line, severity in findings:
            mark = "BLOCK" if severity == "block" else "warn "
            print(f"   {mark}  line {line:5d}  {label}: {token[:60]!r}")
            if severity == "block":
                blocking += 1
            else:
                warnings += 1
    print("=" * 78)
    print(f"{blocking} blocking finding(s), {warnings} warning(s)")
    if not blocking:
        print("Files are structured to publish: data files are read at runtime, never bundled.")
        print("Remember NOT to commit: ~/.local/share/herman/models-local.json (your catalog),")
        print("~/.cache/herman/* (panel token, pid, last project) and anything under ~/.hermes.")
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
