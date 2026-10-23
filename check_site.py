#!/usr/bin/env python3
"""Health and safety check for every published demo landing page.

Version: 2026.10.23.1

Two modes, same assertions:

    python3 check_site.py --local docs
        Pre-publish gate. Reads the built files from disk.

    python3 check_site.py --base https://<user>.github.io/sublime-demo-landing-pages/
        Live check. Fetches every route over HTTPS with certificate verification,
        follows HTTP redirects and records the chain.

For every route in routes.json it fails on:
  - a final response other than HTTP 200, or a redirect that leaves the site
  - a blank page or a missing banner / route marker
  - forms, inputs, buttons, scripts, iframes, embeds, inline event handlers,
    javascript: URLs, <link> tags or any external http(s) reference
  - login, sign-in, password or CAPTCHA wording outside explicitly registered
    inert illustration pages, or a GitHub login wall
  - a missing Content-Security-Policy or noindex meta tag
  - a meta refresh that points outside the site or at an unknown route

Standard library only. Exit codes: 0 all passed, 1 at least one failure,
2 routes.json unreadable.
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

HERE = Path(__file__).resolve().parent
USER_AGENT = "Mozilla/5.0 (demo-landing-pages link-health check)"
MIN_TEXT_CHARS = 250

FORBIDDEN = [
    (re.compile(r"<\s*(form|input|button|select|textarea|script|iframe|object|embed|link|base)\b", re.I), "active or external element"),
    (re.compile(r"\son[a-z]+\s*=", re.I), "inline event handler"),
    (re.compile(r"javascript\s*:", re.I), "javascript: URL"),
    (re.compile(r"(?:src|href|action)\s*=\s*[\"']?\s*(?:https?:)?//", re.I), "external reference"),
    (re.compile(r"url\(\s*[\"']?\s*(?:https?:)?//", re.I), "external CSS resource"),
    (re.compile(r"@import", re.I), "CSS import"),
    (re.compile(r"github\.com/login", re.I), "GitHub login wall"),
]
INERT_WORDING = re.compile(r"captcha|cf-chl|turnstile|\b(?:sign|log)\s?-?in\b|password|passcode", re.I)
INERT_ILLUSTRATION_KINDS = {"google-login", "google-careers", "google-captcha-login"}
INERT_WORDING_KINDS = INERT_ILLUSTRATION_KINDS | {"catalog"}
DENSE_PREVIEW_MARKER = 'data-dense-preview="700x520"'
REQUIRED = [
    (re.compile(r"<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none';[^\"]*form-action 'none'", re.I), "strict CSP meta"),
    (re.compile(r"<meta name=\"robots\" content=\"noindex", re.I), "noindex meta"),
]
TAG_RE = re.compile(r"<style\b.*?</style>|<[^>]+>", re.I | re.S)
REFRESH_RE = re.compile(r"<meta http-equiv=\"refresh\" content=\"\d+;\s*url=([^\"]+)\"", re.I)

# ClickFix allowlist. A route of kind "clickfix" presents a command for a reader to
# paste and run, so it gets a stricter, explicit gate on top of the global checks:
# the shown command must match this allowlist exactly, and the page must contain no
# token that could turn a harmless demo into a real payload. This tightens the gate
# for command-bearing pages; it never relaxes the site-wide FORBIDDEN/REQUIRED rules.
CLICKFIX_ALLOWED_COMMANDS = ("cmd /c echo SUBLIME_CLICKFIX_DEMO",)
CLICKFIX_FORBIDDEN = (
    re.compile(
        r"powershell|pwsh|cmd\.exe|\biex\b|invoke-|\biwr\b|\bcurl\b|\bwget\b|certutil|"
        r"bitsadmin|mshta|rundll32|regsvr32|msiexec|downloadstring|frombase64|base64|"
        r"-enc\b|-encodedcommand|https?://|\.exe\b|\.dll\b|\.ps1\b|\.hta\b|\.vbs\b|\.bat\b",
        re.I,
    ),
    "forbidden command token",
)


class Colors:
    GREEN_BOLD = "\033[1;32m"
    YELLOW_BOLD = "\033[1;33m"
    RED_BOLD = "\033[1;31m"
    RESET = "\033[0m"

    @classmethod
    def green_bold(cls, text: str) -> str:
        return f"{cls.GREEN_BOLD}{text}{cls.RESET}"

    @classmethod
    def yellow_bold(cls, text: str) -> str:
        return f"{cls.YELLOW_BOLD}{text}{cls.RESET}"

    @classmethod
    def red_bold(cls, text: str) -> str:
        return f"{cls.RED_BOLD}{text}{cls.RESET}"


class RedirectTracker(urllib.request.HTTPRedirectHandler):
    def __init__(self) -> None:
        self.chain: list[dict[str, Any]] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        self.chain.append({"code": code, "to": newurl})
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url: str, timeout: int) -> dict[str, Any]:
    tracker = RedirectTracker()
    opener = urllib.request.build_opener(
        tracker, urllib.request.HTTPSHandler(context=ssl.create_default_context())
    )
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    result: dict[str, Any] = {"url": url}
    try:
        with opener.open(request, timeout=timeout) as response:
            result["status"] = response.status
            result["final_url"] = response.geturl()
            result["content_type"] = response.headers.get("Content-Type", "")
            result["body"] = response.read(500_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        result["status"] = exc.code
        result["final_url"] = url
        result["body"] = exc.read(50_000).decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, ssl.SSLError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["redirects"] = tracker.chain
    return result


def inside_site(url: str, base: str) -> bool:
    target, root = urlsplit(url), urlsplit(base)
    return (
        target.scheme == "https"
        and target.hostname == root.hostname
        and target.path.startswith(root.path)
    )


def content_problems(body: str, markers: list[str], content_kind: str = "standard") -> list[str]:
    problems = [label for pattern, label in FORBIDDEN if pattern.search(body)]
    text = re.sub(r"\s+", " ", TAG_RE.sub(" ", body)).strip()
    if content_kind not in INERT_WORDING_KINDS and INERT_WORDING.search(text):
        problems.append("login, credential, CAPTCHA or challenge wording")
    if content_kind in INERT_ILLUSTRATION_KINDS and DENSE_PREVIEW_MARKER not in body:
        problems.append("missing dense 700x520 preview marker")
    problems += [f"missing {label}" for pattern, label in REQUIRED if not pattern.search(body)]
    if len(text) < MIN_TEXT_CHARS:
        problems.append(f"blank or thin page ({len(text)} chars of text)")
    problems += [f"missing marker {marker!r}" for marker in markers if marker not in body]
    return problems


def check(routes_doc: dict[str, Any], base: str, local: Path | None, timeout: int) -> list[dict[str, Any]]:
    banner = routes_doc["banner_marker"]
    known = {route["path"] for route in routes_doc["routes"]}
    results = []
    for route in routes_doc["routes"]:
        url = urljoin(base, route["path"])
        record: dict[str, Any] = {"path": "/" + route["path"], "url": url, "kind": route["kind"]}
        problems: list[str] = []
        if local is not None:
            page = local / route["path"] / "index.html"
            body = page.read_text(encoding="utf-8") if page.is_file() else ""
            record["status"] = 200 if body else 404
            if not body:
                problems.append("file missing")
        else:
            fetched = fetch(url, timeout)
            body = fetched.get("body", "")
            record.update({k: fetched.get(k) for k in ("status", "final_url", "redirects", "error")})
            if fetched.get("error"):
                problems.append(fetched["error"])
            elif fetched["status"] != 200:
                problems.append(f"final HTTP {fetched['status']}")
            elif not inside_site(fetched["final_url"], base):
                problems.append(f"redirected off-site to {fetched['final_url']}")
            elif "text/html" not in fetched.get("content_type", ""):
                problems.append(f"unexpected content type {fetched.get('content_type')}")
        if body:
            problems += content_problems(
                body,
                [banner, route["marker"]],
                route.get("content_kind", "standard"),
            )
        if route["kind"] == "clickfix" or route.get("command"):
            command = route.get("command", "")
            if not command:
                problems.append("clickfix route has no command recorded in routes.json")
            elif command not in body:
                problems.append(f"clickfix command {command!r} is not shown on the page")
            if command and command not in CLICKFIX_ALLOWED_COMMANDS:
                problems.append(f"clickfix command {command!r} is not in the allowlist")
            pattern, label = CLICKFIX_FORBIDDEN
            if body:
                hit = pattern.search(body)
                if hit:
                    problems.append(f"{label}: {hit.group(0)!r}")
        if route["kind"] == "meta-refresh":
            match = REFRESH_RE.search(body)
            if not match:
                problems.append("meta refresh missing")
            else:
                destination = urljoin(url, match.group(1))
                record["refresh_to"] = destination
                relative = urlsplit(destination).path[len(urlsplit(base).path):]
                if not inside_site(destination, base) or relative not in known:
                    problems.append(f"meta refresh escapes the site or targets an unknown route: {destination}")
                elif relative != route.get("refresh_to"):
                    problems.append(f"meta refresh target changed to {relative}")
        record["problems"] = problems
        record["verdict"] = "FAIL" if problems else "PASS"
        results.append(record)

    robots: dict[str, Any] = {"path": "/robots.txt", "url": urljoin(base, "robots.txt"), "kind": "robots"}
    if local is not None:
        robots_body = (local / "robots.txt").read_text(encoding="utf-8") if (local / "robots.txt").is_file() else ""
    else:
        fetched = fetch(robots["url"], timeout)
        robots["status"] = fetched.get("status")
        robots_body = fetched.get("body", "") if fetched.get("status") == 200 else ""
    robots["problems"] = [] if re.search(r"^Disallow:\s*/\s*$", robots_body, re.M) else ["robots.txt missing Disallow: /"]
    robots["verdict"] = "FAIL" if robots["problems"] else "PASS"
    results.append(robots)

    if local is None:
        missing = fetch(urljoin(base, "this-path-does-not-exist/"), timeout)
        record = {"path": "/this-path-does-not-exist/", "kind": "negative", "status": missing.get("status")}
        record["problems"] = [] if missing.get("status") == 404 else [f"unknown path returned {missing.get('status')}, expected 404"]
        record["verdict"] = "FAIL" if record["problems"] else "PASS"
        results.append(record)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Check every demo landing page route.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--base", help="Live site base URL, ending in /")
    mode.add_argument("--local", type=Path, help="Built site directory, for the pre-publish gate")
    parser.add_argument("--routes", type=Path, default=HERE / "routes.json", help="Route list")
    parser.add_argument("--timeout", type=int, default=20, help="Per-request timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    try:
        routes_doc = json.loads(args.routes.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(Colors.red_bold(f"Could not read routes: {exc}"), file=sys.stderr)
        return 2

    base = args.base or "https://local.invalid/site/"
    if not base.endswith("/"):
        base += "/"
    results = check(routes_doc, base, args.local, args.timeout)
    failures = [r for r in results if r["verdict"] == "FAIL"]

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for record in results:
            tag = Colors.green_bold("PASS") if record["verdict"] == "PASS" else Colors.red_bold("FAIL")
            chain = " ".join(f"{hop['code']}->{hop['to']}" for hop in record.get("redirects") or [])
            extra = f" refresh->{record['refresh_to']}" if record.get("refresh_to") else ""
            print(f"[{tag}] {record.get('status')} {record['path']}{extra} {chain}".rstrip())
            for problem in record["problems"]:
                print(Colors.red_bold(f"       {problem}"))
        summary = f"{len(results) - len(failures)}/{len(results)} checks passed"
        print(Colors.red_bold(summary) if failures else Colors.green_bold(summary))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
