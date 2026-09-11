#!/usr/bin/env python3
"""herman security check: the panel's regression battery as one command.

Runs every access, origin, method, argument and limit probe against the running panel plus the
file permission checks, and optionally the publish pre-flight. Read-only on the machine: the
mutating probes are the ones that MUST be refused (405/400/403), so a passing run never changes
anything. Exit code 0 when every check behaves, 1 otherwise.

    python3 ~/.local/share/herman/security_check.py [--port 9120] [--host 127.0.0.1] [--json]
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import pathlib
import socket
import subprocess
import sys

HOME = pathlib.Path.home()
CACHE = HOME / ".cache" / "herman"
TOKEN_FILE = CACHE / "web-token"
SHARE = pathlib.Path(__file__).resolve().parent
RESULTS: list[tuple[bool, str, str]] = []


def record(ok: bool, name: str, detail: str = "") -> None:
    RESULTS.append((ok, name, detail))


def check(name: str, got, want) -> None:
    ok = got == want
    record(ok, name, f"got {got!r}, expected {want!r}" if not ok else f"{got!r}")


def call(method: str, path: str, *, port: int, host: str = "127.0.0.1",
         headers: dict | None = None, body: bytes | None = None):
    conn = http.client.HTTPConnection(host, port, timeout=15)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        res = conn.getresponse()
        payload = res.read()
        return res.status, {k.lower(): v for k, v in res.getheaders()}, payload
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9120)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not TOKEN_FILE.exists():
        print(f"no panel token at {TOKEN_FILE}: start the panel with `herman web` first")
        return 1
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    port, host = args.port, args.host
    base = f"http://{host}:{port}"

    # ---- is the panel even reachable? --------------------------------------------------------
    try:
        call("GET", "/api/status", port=port, host=host)
    except (ConnectionRefusedError, socket.timeout, OSError) as exc:
        print(f"no panel answering on {base} ({exc.__class__.__name__}): start it with `herman web`")
        return 1

    # ---- access -----------------------------------------------------------------------------
    st, _h, _b = call("GET", "/api/status", port=port, host=host)
    check("no token is refused", st, 403)
    st, _h, _b = call("GET", "/api/status?t=wrong-token", port=port, host=host)
    check("a wrong token is refused", st, 403)
    st, _h, _b = call("GET", f"/api/status?t={token}", port=port, host=host)
    check("the query token is accepted", st, 200)
    st, _h, _b = call("GET", "/api/status", port=port, host=host,
                      headers={"X-Herman-Token": token})
    check("the header token is accepted", st, 200)
    st, _h, _b = call("GET", "/api/status", port=port, host=host,
                      headers={"Cookie": "herman_session=wrong"})
    check("a wrong session cookie is refused", st, 403)

    st, hdrs, _b = call("GET", f"/?t={token}", port=port, host=host)
    check("the page URL with a token redirects", st, 302)
    check("the redirect points at the token-free path", hdrs.get("location"), "/")
    cookie = hdrs.get("set-cookie", "")
    check("the cookie is HttpOnly", "httponly" in cookie.lower(), True)
    check("the cookie is SameSite=Strict", "samesite=strict" in cookie.lower(), True)
    st, _h, _b = call("GET", "/api/status", port=port, host=host,
                      headers={"Cookie": cookie.split(";")[0]})
    check("the cookie authenticates on its own", st, 200)

    # ---- origin and host --------------------------------------------------------------------
    st, _h, _b = call("GET", f"/api/status?t={token}", port=port, host=host,
                      headers={"Host": "evil.example"})
    check("a foreign Host header is refused (DNS rebinding)", st, 403)
    st, _h, _b = call("GET", f"/api/status?t={token}", port=port, host=host,
                      headers={"Sec-Fetch-Site": "cross-site"})
    check("a cross-site request is refused (CSRF)", st, 403)
    st, _h, _b = call("GET", f"/api/status?t={token}", port=port, host=host,
                      headers={"Origin": "https://evil.example"})
    check("a foreign Origin is refused", st, 403)

    # ---- methods and argument shapes ---------------------------------------------------------
    st, _h, _b = call("GET", f"/api/action?t={token}&action=kill&name=default", port=port, host=host)
    check("a mutating action over GET is refused", st, 405)
    st, _h, _b = call("GET", f"/api/action?t={token}&action=list", port=port, host=host)
    check("a read-only action over GET is allowed", st, 200)
    for label, query in (("a name that looks like a flag", "action=tidy&name=--all"),
                         ("a session id that looks like a flag", "action=kill-session&name=default&session=--all"),
                         ("a search term that looks like a flag", "action=history-delete-matching&name=default&q=--delete-all"),
                         ("a name with a path separator", "action=tidy&name=../x"),
                         ("a session id that looks like a flag", "action=history-delete-session&name=default&session=--all")):
        st, _h, _b = call("POST", f"/api/action?t={token}&{query}", port=port, host=host)
        check(f"{label} is refused", st, 400)

    # ---- limits and traversal ----------------------------------------------------------------
    big = b'{"padding":"' + b"a" * (1024 * 1024) + b'"}'
    st, _h, _b = call("POST", f"/api/access-grant?t={token}", port=port, host=host,
                      headers={"Content-Type": "application/json"}, body=big)
    check("a request body over the cap is refused", st, 413)
    st, _h, _b = call("GET", f"/../../etc/passwd?t={token}", port=port, host=host)
    check("a traversal path is not served", st in (400, 404), True)
    st, _h, _b = call("GET", "/caduceus.png", port=port, host=host)
    check("the watermark image needs a token", st, 403)
    st, _h, _b = call("GET", f"/caduceus.png?t={token}", port=port, host=host)
    check("the watermark image loads with a token", st, 200)

    # ---- response hardening ------------------------------------------------------------------
    st, hdrs, _b = call("GET", f"/?t={token}", port=port, host=host)
    for name, key, needle in (("nosniff", "x-content-type-options", "nosniff"),
                              ("no-referrer", "referrer-policy", "no-referrer"),
                              ("no framing", "x-frame-options", "deny"),
                              ("a content security policy", "content-security-policy", "default-src 'none'"),
                              ("frame-ancestors in the CSP", "content-security-policy", "frame-ancestors 'none'")):
        check(f"the page sends {name}", needle in (hdrs.get(key) or "").lower(), True)
    check("no Python version in the Server header", "python" in (hdrs.get("server") or "").lower(), False)
    st, hdrs, _b = call("GET", "/api/status", port=port, host=host)
    check("API answers are not cached", (hdrs.get("cache-control") or ""), "no-store")

    # ---- files ------------------------------------------------------------------------------
    check("the cache directory is 0700", oct(CACHE.stat().st_mode & 0o777), "0o700")
    for path in sorted(CACHE.glob("*")):
        if path.is_file():
            mode = oct(path.stat().st_mode & 0o777)
            check(f"{path.name} is 0600", mode, "0o600")
    for backup in sorted((HOME / ".hermes" / "history-backups").glob("*.db"))[:3]:
        record((backup.stat().st_mode & 0o777) == 0o600, f"{backup.name} is 0600",
               oct(backup.stat().st_mode & 0o777))

    # ---- publishable files -------------------------------------------------------------------
    pre = SHARE / "preflight.py"
    if pre.exists():
        res = subprocess.run([sys.executable, str(pre)], capture_output=True, text=True)
        record(res.returncode == 0, "preflight: no operator data in the publishable files",
               "exit 1, see the preflight output")

    # ---- report ------------------------------------------------------------------------------
    bad = [x for x in RESULTS if not x[0]]
    if args.json:
        print(json.dumps({"panel": base, "checks": len(RESULTS), "failed": len(bad),
                          "results": [{"ok": ok, "check": n, "detail": d} for ok, n, d in RESULTS]},
                         indent=2, ensure_ascii=False))
    else:
        print(f"herman security check · panel {base}")
        for ok, name, detail in RESULTS:
            print(f"  [{'ok ' if ok else 'FAIL'}] {name}" + ("" if ok else f"  ({detail})"))
        print(f"\n{len(RESULTS)} checks · {len(RESULTS) - len(bad)} ok · {len(bad)} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
