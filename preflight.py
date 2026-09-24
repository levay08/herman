#!/usr/bin/env python3
"""Pre-flight check before publishing herman to a public repository.

Scans the files that would be published and reports anything that looks like operator data:
personal paths, host names, provider names, session ids, secrets or the author's own forked
catalog file. Exit code 1 when a blocking finding is present, so it can gate a release.

It also refuses the operator's OWN free text (every project description in herman's state, and the
panel token): no pattern list can recognise a sentence someone wrote, so those strings are read from
~/.cache/herman at scan time and any file containing one is blocked.

Usage:  python3 preflight.py [path ...]
        python3 preflight.py --install-hook [repo]     git hook that scans what you stage
"""
from __future__ import annotations

import json
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
    ("private host or IP", r"\b(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}\b", "block"),
    ("session id", r"\b20\d{6}_\d{6}_[0-9a-f]{4,}\b", "block"),
    ("secret-looking token", r"\b(?:sk|pk|ghp|gho|AIza|hf)_?[A-Za-z0-9_-]{12,}\b", "block"),
    ("email address", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "warn"),
    ("provider domain", r"\b(?:paas\.id|openrouter\.ai|api\.openai\.com|anthropic\.com)\b", "warn"),
    ("author name", r"\bLevay\b", "warn"),
    ("indonesian word", r"(?<![A-Za-z])(dengan|untuk|tidak|belum|riwayat|pemakaian|pesan|sesi|hari|"
                        r"terakhir|pertama|angka|gagal|dimuat|nama|mencari|berpikir|lintas|pangsa|"
                        r"estimasi|aktif|harga|kapan|contoh|jumlah|panggilan|"
                        # added after a full sweep of the CLI: the panel and the command line speak
                        # English only, so any of these in a shipped file is a regression worth a warn
                        r"tanpa|kunci|bukan|atau|jika|sudah|hanya|semua|tiap|setiap|"
                        r"daftar|pilih|dipilih|coba|tambah|tambahnya|pasang|anggota|berbayar|butuh|"
                        r"gratis|sering|milik|sendiri|ulang|pemilih|resmi|interaktif|"
                        r"jalankan|menjalankan|menyambung|menyentuh|menulis|membuka|kedaluwarsa|"
                        r"berkas|halaman|baris|perintah|proyek|selesai|kembali|lanjut|mulai|"
                        r"simpan|hapus|ganti|cari|lihat|tampil|sambung|hitung|katalog|"
                        r"punya|taruh|ambil|biar|berapa|apakah|tersedia|terpasang)(?![A-Za-z])", "warn"),
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
    # Public API hosts herman ships on purpose in its endpoint picker: vendor-run, documented
    # addresses, so they are product data and not operator data. The provider-domain rule keeps its
    # teeth for everything else (a private aggregator, a self-hosted gateway), and the operator's own
    # free text is covered by operator_strings().
    r"api\.openai\.com", r"openrouter\.ai", r"anthropic\.com", r"ai\.paas\.id",
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


# Generated art herman ships as-is, with the reason it is exempt. An SVG sprite is full of coordinate
# runs and every so often one of them reads like an address (`M 2.164 205.148`), which is the kind of
# finding a shape rule cannot tell apart from the real thing. The exemption is by exact file name, not
# by extension, so nothing else can hide behind it - and only the rules that can have a benign twin
# step aside: personal paths, secrets, session ids and the operator's own strings keep their teeth.
VENDORED = {
    "icons.svg": "Bootstrap Icons sprite, generated by gen_icons.py (MIT), pure path data",
}
VENDOR_SKIP = ("private host or IP", "author name")


OPERATOR_FILE = Path.home() / ".cache" / "herman"


def operator_strings() -> list[str]:
    """Free text that belongs to the operator and must never reach a published file.

    Project descriptions are the case that matters: they are sentences, so the RULES above cannot
    catch them. The panel token is included because it is a credential by definition.
    """
    out: list[str] = []
    try:
        state = json.loads((OPERATOR_FILE / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    if isinstance(state, dict):
        for _name, text in (state.get("descriptions") or {}).items():
            t = str(text).strip()
            if len(t) >= 8:          # a three-character note would match half the file
                out.append(t)
    try:
        t = (OPERATOR_FILE / "web-token").read_text(encoding="utf-8").strip()
        if len(t) >= 8:
            out.append(t)
    except OSError:
        pass
    return out


def install_generated(path: Path, text: str) -> bool:
    """A per-project shortcut command is not publishable content: the Hermes profile alias writes it
    on this machine and it must name this machine's engine path, so its home directory is by design.

    Recognised by shape alone (a short /bin/sh stub that execs a hermes binary with `-p <profile>`),
    never by name, so a hand-written script that happens to sit in the same folder is still scanned.
    """
    if len(text) > 400 or not text.startswith("#!/bin/sh"):
        return False
    return bool(re.search(r"^exec\s+\S*hermes\S*\s+-p\s+[A-Za-z0-9][A-Za-z0-9._-]{0,63}", text, re.M))


def scan(path: Path) -> list[tuple[str, str, int, str]]:
    try:
        text = strip_own_rules(path.read_text(encoding="utf-8"), path)
    except (OSError, UnicodeDecodeError):
        return []        # unreadable or binary (caduceus.png): nothing textual to grep for
    if install_generated(path, text):
        return []
    findings: list[tuple[str, str, int, str]] = []
    for token in operator_strings():
        for match in re.finditer(re.escape(token), text):
            findings.append(("operator data (your own state)", token,
                             text[:match.start()].count("\n") + 1, "block"))
    vendored = path.name in VENDORED
    for label, pattern, severity in RULES:
        if vendored and label in VENDOR_SKIP:
            continue
        rx = re.compile(pattern)
        for match in rx.finditer(text):
            token = match.group(0)
            window = text[max(0, match.start() - 60):match.end() + 60]
            if any(re.search(a, window) for a in ALLOW):
                continue
            line = text[: match.start()].count("\n") + 1
            findings.append((label, token, line, severity))
    return findings


HOOK = """#!/bin/sh
# Installed by preflight.py --install-hook: refuse a commit that would publish operator data.
# Scans the staged files with the same rules the release gate uses (personal paths, hosts, secrets,
# session ids, project descriptions, the panel token) so nothing user-owned can reach the history.
set -e
repo=$(git rev-parse --show-toplevel)
scanner="$repo/preflight.py"
[ -f "$scanner" ] || scanner="__SCANNER__"
files=$(git diff --cached --name-only --diff-filter=ACMR)
[ -n "$files" ] || exit 0
ok=1
for f in $files; do
  [ -f "$repo/$f" ] || continue
  if ! python3 "$scanner" "$repo/$f" >/tmp/herman-preflight-hook.out 2>&1; then
    sed -n '1,6p' /tmp/herman-preflight-hook.out
    echo "pre-commit: refusing to commit $f (operator data). Nothing was committed."
    ok=0
  fi
done
[ "$ok" = 1 ] || exit 1
exit 0
"""


def install_hook(repo: Path) -> int:
    """Write the pre-commit hook into a working tree (local only, never committed)."""
    hooks = repo / ".git" / "hooks"
    if not hooks.is_dir():
        print(f"not a git working tree: {repo}")
        return 2
    target = hooks / "pre-commit"
    if target.exists() and "preflight" not in target.read_text(encoding="utf-8", errors="replace"):
        print(f"{target} already exists and is not ours: leaving it alone")
        return 2
    body = HOOK.replace("__SCANNER__", str(Path(__file__).resolve()))
    try:
        target.write_text(body, encoding="utf-8")
        target.chmod(0o755)
    except OSError as exc:
        print(f"could not write {target}: {exc}")
        return 2
    print(f"installed {target} (scans staged files with {Path(__file__).name})")
    return 0


def main(argv: list[str]) -> int:
    args = argv[1:]
    if args and args[0] == "--install-hook":
        repo = Path(args[1]) if len(args) > 1 else Path.cwd()
        return install_hook(repo)
    files = [Path(a) for a in args] or [p for p in DEFAULT_FILES if p.exists()]
    if not files:
        print("nothing to scan: pass the files, or install herman first")
        return 2
    blocking = 0
    warnings = 0
    for path in files:
        findings = scan(path)
        print("=" * 78)
        print(f"{path}  ({os.path.getsize(path) if path.exists() else 0} bytes)")
        try:
            generated = install_generated(path, path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            generated = False
        if generated:
            print("   skip: written at install (profile shortcut command, names this machine)")
            continue
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
        print("~/.cache/herman/* (panel token, pid, project descriptions) and anything under ~/.hermes.")
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
