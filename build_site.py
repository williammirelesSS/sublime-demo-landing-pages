#!/usr/bin/env python3
"""Build the static demo landing pages into docs/.

Version: 2026.10.22.1

Every page is fabricated, inert demo content: static HTML and inline CSS only.
No forms, inputs, buttons, scripts, iframes, external assets, trackers or cookies.
Each page carries a visible "Sublime Security Demo Asset" banner, a strict
Content-Security-Policy meta tag and noindex metadata.

Pages are built inside a compact product "chrome" (a fake Google Drive, Figma,
Teams, calendar, DocuSign, voicemail or generic document shell) so the first
viewport of a roughly 700x520 link-preview crop is filled with a dense, inert
file UI instead of a small card over empty white. The hostname stays this GitHub
Pages site; only the path and on-page chrome read as the named product.

Short links: opaque, bit.ly-style hops live under /s/<code>/. GitHub Pages cannot
send an HTTP 302, so each hop is a same-site HTML meta refresh (delay 0) that also
renders its destination's dense UI in the first viewport and carries a visible
fallback link. Codes are derived deterministically from the target id, so a rebuild
is byte-identical. check_site.py re-asserts that every hop stays on this site and
targets a known route.

The output is deterministic: running this twice produces byte-identical files.
routes.json is written alongside so check_site.py knows every published path.

Usage:
    python3 build_site.py            # writes docs/ and routes.json
"""

from __future__ import annotations

import hashlib
import html
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "docs"
BANNER_MARKER = "Sublime Security Demo Asset"

# The only command a ClickFix demo page may ever present. It is deliberately
# constrained here, in source, so the page cannot drift into a real payload:
# it prints a fixed marker and exits. No download, no secondary execution, no
# network, no PowerShell, no encoding. check_site.py re-asserts this allowlist
# against the published HTML, so weakening it here fails the gate there too.
CLICKFIX_COMMAND = "cmd /c echo SUBLIME_CLICKFIX_DEMO"
CLICKFIX_ALLOWED_COMMANDS = ("cmd /c echo SUBLIME_CLICKFIX_DEMO",)
CLICKFIX_FORBIDDEN = (
    "powershell", "pwsh", "cmd.exe", "iex", "invoke-", "iwr", "curl", "wget",
    "certutil", "bitsadmin", "mshta", "rundll32", "regsvr32", "msiexec",
    "downloadstring", "frombase64", "base64", "-enc", "-encodedcommand",
    "http://", "https://", ".exe", ".dll", ".ps1", ".hta", ".vbs", ".bat", "&&", "|",
)
assert CLICKFIX_COMMAND in CLICKFIX_ALLOWED_COMMANDS, "ClickFix command must be allowlisted"
assert not any(
    token in CLICKFIX_COMMAND.lower() for token in CLICKFIX_FORBIDDEN
), "ClickFix command contains a forbidden token"

CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; "
    "base-uri 'none'; form-action 'none'"
)

# Opaque short-code derivation. Keyed on the link-target id (a stable string
# shared with the demo sample pack's link_map.json), so codes are deterministic,
# unique per click target, and identical on both sides. Six base62 characters
# read like a bit.ly / TinyURL slug without being a third-party shortener.
_SHORT_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def short_code(target_id: str) -> str:
    digest = hashlib.sha256(("sublime-demo-short-links/v1/" + target_id).encode("utf-8")).digest()
    number = int.from_bytes(digest[:8], "big")
    out = []
    for _ in range(6):
        number, remainder = divmod(number, 62)
        out.append(_SHORT_ALPHABET[remainder])
    return "".join(out)


STYLE = """
:root{--green:#04E69B;--green-neutral:#F0FBF6;--green-shade:#006D49;--ink:#0B0B0B;--text:#575757;--muted:#8A8A8A;--border:#E2E4E8;--page:#F3F4F6;--panel:#FFFFFF}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--page);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;font-size:14px;line-height:1.5}
.demo-banner{background:var(--ink);color:#fff;padding:7px 16px;font-size:12px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.demo-banner strong{color:var(--green);letter-spacing:.02em}
.demo-banner .dot{width:9px;height:9px;border-radius:50%;background:var(--green);flex:none}
.demo-banner .tag{color:#C9C9C9}
.app{max-width:1040px;margin:12px auto;padding:0 12px}
.appbar{display:flex;align-items:center;gap:14px;background:var(--bar,#111);color:var(--barink,#fff);padding:10px 16px;border-radius:10px 10px 0 0}
.appbar .brand{display:flex;align-items:center;gap:9px;font-weight:700;font-size:15px;letter-spacing:.01em}
.appbar .brand svg{flex:none;display:block}
.appbar .file{font-weight:600;font-size:14px;opacity:.95;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.appbar .sep{opacity:.4}
.appbar .spacer{flex:1}
.appbar .presence{display:flex;gap:-6px}
.appbar .ava{width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#fff;border:2px solid var(--bar,#111);margin-left:-6px}
.appbar .pill{font-size:12px;font-weight:600;padding:6px 12px;border-radius:7px;background:rgba(255,255,255,.16);color:inherit}
.appbar .pill.solid{background:var(--accent,#2684FF);color:#fff}
.subbar{display:flex;align-items:center;gap:10px;background:var(--panel);border:1px solid var(--border);border-top:none;padding:8px 16px;font-size:12px;color:var(--muted);flex-wrap:wrap}
.subbar .crumb{color:var(--text);font-weight:500}
.subbar .crumb b{color:var(--ink)}
.subbar .tool{padding:4px 10px;border:1px solid var(--border);border-radius:6px;color:var(--text);background:#fff;font-weight:500}
.subbar .spacer{flex:1}
.layout{display:flex;gap:14px;background:var(--panel);border:1px solid var(--border);border-top:none;border-radius:0 0 10px 10px;padding:14px;min-height:382px}
.rail{flex:none;width:176px;font-size:12px}
.rail h4{margin:0 0 8px;font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}
.rail .row{display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:6px;color:var(--text)}
.rail .row.active{background:var(--green-neutral);color:var(--green-shade);font-weight:600}
.rail .row .ico{width:16px;height:16px;flex:none;border-radius:3px;background:var(--border)}
.rail .row .ico.g{background:var(--green)}
.rail .divider{height:1px;background:var(--border);margin:10px 0}
.stage{flex:1;min-width:0}
.kicker{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--green-shade);font-weight:700;margin:0 0 3px}
h1{font-size:19px;margin:0 0 10px;font-weight:600;line-height:1.25}
.stage p{color:var(--text);margin:0 0 11px}
.doc{display:flex;gap:12px;align-items:center;border:1px solid var(--border);border-radius:8px;padding:11px 13px;margin:0 0 13px;background:#fff}
.doc svg{flex:none}
.doc strong{display:block;font-size:14px}
.doc span{font-size:12px;color:var(--muted)}
.frames{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin:0 0 13px}
.frame{border:1px solid var(--border);border-radius:7px;overflow:hidden;background:#fff}
.frame .thumb{height:92px;background:linear-gradient(180deg,#fbfbfc,#eef0f3);border-bottom:1px solid var(--border);position:relative}
.frame .thumb .ln{position:absolute;left:12px;right:12px;height:6px;border-radius:3px;background:#E4E7EB}
.frame .thumb .ln.a{top:16px}.frame .thumb .ln.b{top:30px;right:40px}.frame .thumb .ln.c{top:44px;right:26px}
.frame .thumb .chip{position:absolute;left:12px;bottom:12px;width:34px;height:20px;border-radius:4px;background:var(--accent,#2684FF);opacity:.85}
.frame .cap{padding:7px 10px;font-size:12px}
.frame .cap b{display:block;font-weight:600}
.frame .cap span{color:var(--muted);font-size:11px}
table.meta{width:100%;border-collapse:collapse;margin:4px 0 13px;font-size:13px}
table.meta th,table.meta td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--border);vertical-align:top}
table.meta th{background:#FAFBFC;font-weight:600;width:40%;color:var(--ink)}
table.meta td{color:var(--text);font-family:"SF Mono",Menlo,Consolas,monospace;font-size:12px}
.sections{margin:0 0 13px;border:1px solid var(--border);border-radius:8px;overflow:hidden}
.sections .s{display:flex;justify-content:space-between;gap:12px;padding:9px 13px;border-bottom:1px solid var(--border);font-size:13px}
.sections .s:last-child{border-bottom:none}
.sections .s b{font-weight:600}
.sections .s span{color:var(--text)}
.explain{border-left:3px solid var(--green);background:var(--green-neutral);padding:11px 14px;border-radius:0 6px 6px 0;font-size:13px;color:var(--text);margin:6px 0 0}
.explain b{color:var(--ink)}
a{color:var(--green-shade)}
.cta{display:inline-block;background:var(--accent,#2684FF);color:#fff;padding:9px 18px;border-radius:7px;text-decoration:none;font-weight:600;font-size:13px;margin:0 0 13px}
.alert{border-left:3px solid var(--ink);background:#FBF1F0;padding:11px 14px;border-radius:0 6px 6px 0;font-size:13px;color:var(--ink);margin:0 0 13px}
.steps{margin:0 0 13px;padding-left:20px;color:var(--text)}
.steps li{margin:5px 0}
.steps kbd{font-family:"SF Mono",Menlo,Consolas,monospace;font-size:12px;background:var(--page);border:1px solid var(--border);border-radius:4px;padding:1px 6px}
.cmd{margin:0 0 13px}
.cmd .cmd-label{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:0 0 5px}
.cmd code{display:block;font-family:"SF Mono",Menlo,Consolas,monospace;font-size:13px;background:var(--ink);color:var(--green);padding:12px 14px;border-radius:6px;word-break:break-all}
.hopnote{display:flex;gap:10px;align-items:center;background:var(--green-neutral);border:1px solid #BEEBD9;color:var(--green-shade);padding:9px 14px;border-radius:8px;font-size:13px;margin:12px auto 0;max-width:1040px}
.hopnote .sp{flex:1}
.foot{font-size:11px;color:var(--muted);margin:12px 4px 32px;max-width:1040px}
.route{font-family:"SF Mono",Menlo,Consolas,monospace}
.wrap{max-width:720px;margin:14px auto;padding:0 14px}
""".strip()

DOC_ICON = (
    '<svg width="34" height="42" viewBox="0 0 40 48" aria-hidden="true">'
    '<path d="M4 2h22l10 10v32a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" '
    'fill="#F0FBF6" stroke="#006D49" stroke-width="2"/>'
    '<path d="M26 2v10h10" fill="none" stroke="#006D49" stroke-width="2"/>'
    '<rect x="9" y="22" width="20" height="3" rx="1.5" fill="#04E69B"/>'
    '<rect x="9" y="29" width="16" height="3" rx="1.5" fill="#D6D6D6"/>'
    '<rect x="9" y="36" width="18" height="3" rx="1.5" fill="#D6D6D6"/></svg>'
)

# Product chrome definitions. Each controls the fake app bar colours, wordmark and
# left-rail items. Nothing here is a real logo asset or an external reference; the
# marks are small inline shapes so the shell reads as the product without claiming
# to be its domain.
DRIVE_MARK = (
    '<svg width="22" height="20" viewBox="0 0 24 22" aria-hidden="true">'
    '<path d="M8 1h8l7 12h-8z" fill="#FFCF3F"/>'
    '<path d="M1 20 8 8l4 7-3.5 5z" fill="#2684FF"/>'
    '<path d="M23 13 19.5 20h-11L12 13z" fill="#12A45A"/></svg>'
)
FIGMA_MARK = (
    '<svg width="16" height="24" viewBox="0 0 16 24" aria-hidden="true">'
    '<circle cx="4" cy="4" r="4" fill="#F24E1E"/><circle cx="12" cy="12" r="4" fill="#1ABCFE"/>'
    '<circle cx="4" cy="12" r="4" fill="#A259FF"/><circle cx="4" cy="20" r="4" fill="#0ACF83"/>'
    '<path d="M8 8h4a4 4 0 1 1-4 4z" fill="#FF7262"/></svg>'
)
TEAMS_MARK = (
    '<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">'
    '<rect x="1" y="5" width="13" height="13" rx="3" fill="#fff" opacity=".9"/>'
    '<text x="4" y="15" font-size="10" font-weight="700" fill="#5B5FC7">T</text>'
    '<circle cx="18" cy="8" r="5" fill="#fff" opacity=".9"/></svg>'
)
CAL_MARK = (
    '<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">'
    '<rect x="2" y="4" width="20" height="18" rx="3" fill="#fff" opacity=".95"/>'
    '<rect x="2" y="4" width="20" height="5" rx="3" fill="#D64B3C"/>'
    '<rect x="6" y="12" width="5" height="5" rx="1" fill="#D64B3C"/></svg>'
)
DS_MARK = (
    '<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">'
    '<rect x="2" y="2" width="20" height="20" rx="4" fill="#FFCF3F"/>'
    '<text x="6" y="17" font-size="13" font-weight="800" fill="#2B2B2B">D</text></svg>'
)
VM_MARK = (
    '<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M3 11a8 8 0 0 1 18 0" fill="none" stroke="#fff" stroke-width="2"/>'
    '<rect x="3" y="11" width="6" height="7" rx="2" fill="#fff"/>'
    '<rect x="15" y="11" width="6" height="7" rx="2" fill="#fff"/></svg>'
)
DOC_MARK = (
    '<svg width="18" height="20" viewBox="0 0 20 22" aria-hidden="true">'
    '<rect x="2" y="1" width="16" height="20" rx="2" fill="#fff" opacity=".95"/>'
    '<rect x="5" y="6" width="10" height="2" fill="#04E69B"/>'
    '<rect x="5" y="10" width="10" height="2" fill="#D6D6D6"/>'
    '<rect x="5" y="14" width="7" height="2" fill="#D6D6D6"/></svg>'
)

CHROMES: dict[str, dict] = {
    "drive": {
        "bar": "#FFFFFF", "barink": "#202124", "accent": "#1A73E8", "mark": DRIVE_MARK,
        "brand": "Drive", "border_bar": True,
        "rail_head": "My Drive", "rail": [
            ("Shared with me", False), ("BuildRight RFQ", True), ("Recent", False),
            ("Starred", False), ("Trash", False),
        ],
    },
    "figma": {
        "bar": "#2C2C2C", "barink": "#FFFFFF", "accent": "#0D99FF", "mark": FIGMA_MARK,
        "brand": "", "rail_head": "Pages", "rail": [
            ("Cover", False), ("RFQ Overview", True), ("Quote Pack", False),
            ("Remittance", False), ("Delivery Schedule", False),
        ],
    },
    "teams": {
        "bar": "#5B5FC7", "barink": "#FFFFFF", "accent": "#5B5FC7", "mark": TEAMS_MARK,
        "brand": "Teams", "rail_head": "Chat", "rail": [
            ("Activity", False), ("Chat", True), ("Teams", False), ("Calendar", False),
        ],
    },
    "calendar": {
        "bar": "#D64B3C", "barink": "#FFFFFF", "accent": "#D64B3C", "mark": CAL_MARK,
        "brand": "Billing Review", "rail_head": "Invoice", "rail": [
            ("Summary", True), ("Line items", False), ("Dispute", False), ("History", False),
        ],
    },
    "esign": {
        "bar": "#FFFFFF", "barink": "#2B2B2B", "accent": "#C9A227", "mark": DS_MARK,
        "brand": "DocuSign", "border_bar": True,
        "rail_head": "Envelope", "rail": [
            ("Overview", True), ("Document", False), ("Recipients", False), ("History", False),
        ],
    },
    "voicemail": {
        "bar": "#1F7A5A", "barink": "#FFFFFF", "accent": "#1F7A5A", "mark": VM_MARK,
        "brand": "Voicemail", "rail_head": "Mailbox", "rail": [
            ("Inbox", True), ("Saved", False), ("Deleted", False), ("Settings", False),
        ],
    },
    "doc": {
        "bar": "#111111", "barink": "#FFFFFF", "accent": "#006D49", "mark": DOC_MARK,
        "brand": "Secure Document Portal", "rail_head": "Document", "rail": [
            ("Preview", True), ("Details", False), ("Activity", False),
        ],
    },
}

# Each page: route (directory path under the site), the product chrome, title,
# kicker, heading, a breadcrumb, optional document card, a dense preview block
# (frames grid and/or section list), a metadata table, an explanation and the
# expected marker the health check asserts on.
PAGES: list[dict] = [
    # ---- Sample 02: Google Drive-style secure document share (direct, no hop) ----
    {
        "route": "drive/file/d/1A3fRQ2026FacilitiesRFQ/view/",
        "chrome": "drive",
        "kicker": "Google Drive &middot; file view",
        "heading": "Q3_2026_Facilities_RFQ.pdf",
        "crumb": "My Drive <b>&rsaquo; BuildRight RFQ &rsaquo; Q3_2026_Facilities_RFQ.pdf</b>",
        "doc": ("Q3_2026_Facilities_RFQ.pdf", "Shared by Avery Demo, BuildRight Contractors (fictional) &middot; PDF &middot; 1.2 MB"),
        "paragraphs": [
            "Read-only preview of the Q3 2026 facilities request for quote. This is a static, "
            "fabricated rendering on a Sublime demo host dressed as a Drive file view. Nothing "
            "here downloads, collects or submits anything.",
        ],
        "frames": [
            ("p1", "Scope &amp; schedule", "Page 1 of 4"),
            ("p2", "Mechanical &amp; electrical", "Page 2 of 4"),
            ("p3", "Partitioning &amp; joinery", "Page 3 of 4"),
            ("p4", "Server-room cooling", "Page 4 of 4"),
        ],
        "sections": [
            ("Section 1", "Mechanical and electrical works"),
            ("Section 2", "Partitioning and joinery"),
            ("Section 3", "Server room cooling upgrade (provisional sum)"),
            ("Return quotes by", "Friday, end of business"),
        ],
        "table": [
            ("Owner", "avery.demo@buildright-contractors.example"),
            ("Type", "PDF document"),
            ("Access", "Anyone with the link (lure wording)"),
        ],
        "explain": "This is the end page behind the bare URL and behind the mismatched link text in "
        "the <b>secure document share</b> sample. Link analysis should show this Drive-style page as "
        "the effective URL with a 200 response. The host is a Sublime demo site, not Google Drive.",
        "marker": "Q3_2026_Facilities_RFQ.pdf",
    },
    {
        "route": "drive/file/d/1A3fRQ2026FacilitiesRFQ/preview/",
        "chrome": "drive",
        "kicker": "Google Drive &middot; quick preview",
        "heading": "Q3_2026_Facilities_RFQ.pdf",
        "crumb": "My Drive <b>&rsaquo; BuildRight RFQ &rsaquo; Quick preview</b>",
        "doc": ("Q3_2026_Facilities_RFQ.pdf", "Quick-access preview &middot; read-only &middot; 4 pages"),
        "paragraphs": [
            "The quick-access leg of the secure document share points straight here, a Drive-style "
            "preview of the same request for quote. There is no shortener hop: the link resolves "
            "directly to this inert page with a 200 response.",
        ],
        "frames": [
            ("p1", "Scope &amp; schedule", "Page 1 of 4"),
            ("p2", "Pricing summary", "Page 2 of 4"),
            ("p3", "Lead times", "Page 3 of 4"),
        ],
        "sections": [
            ("Viewer mode", "Read-only preview"),
            ("Document", "Q3_2026_Facilities_RFQ.pdf"),
            ("Classification", "Demo content, fabricated"),
        ],
        "table": [
            ("Opened from", "Quick-access link in the share email"),
            ("Pages", "4"),
        ],
        "explain": "The destination of the <b>quick-access link</b> in the secure document share "
        "sample. In the previous revision this was a shortener hop; it is now a direct Drive-style "
        "preview URL on the controlled host.",
        "marker": "Q3_2026_Facilities_RFQ.pdf",
    },
    {
        "route": "drive/drive/folders/0B2vRFQProcurementQ3/",
        "chrome": "drive",
        "kicker": "Google Drive &middot; shared folder",
        "heading": "Procurement: Q3 RFQ (mirror)",
        "crumb": "Shared drives <b>&rsaquo; Procurement &rsaquo; Q3 RFQ</b>",
        "paragraphs": [
            "This Drive folder path is the text the email displays for its mirror link. The email's "
            "real link points somewhere else, to the Q3_2026_Facilities_RFQ.pdf file view.",
        ],
        "frames": [
            ("f1", "Q3_2026_Facilities_RFQ.pdf", "PDF &middot; 1.2 MB"),
            ("f2", "BuildRight_Quote_Pack.xlsx", "Sheet &middot; 88 KB"),
            ("f3", "Remittance_Advice.pdf", "PDF &middot; 41 KB"),
        ],
        "table": [
            ("Displayed as", "shared procurement folder"),
            ("Actually links to", "Q3_2026_Facilities_RFQ.pdf view"),
            ("Items", "3 files"),
        ],
        "explain": "The <b>display text versus href mismatch</b> leg of the secure document share "
        "sample. Both the displayed folder path and the real destination are inert demo pages on "
        "the controlled host.",
        "marker": "Procurement: Q3 RFQ (mirror)",
    },
    # ---- Sample 01: Figma-style shared workspace (direct, no hop) ----
    {
        "route": "figma/design/Fq2Kp9RmZ3Lw/RFQ-Documentation-Q3-2026/",
        "chrome": "figma",
        "kicker": "Figma &middot; shared design file",
        "heading": "RFQ Documentation, Q3 2026",
        "crumb": "Drafts <b>&rsaquo; BuildRight &rsaquo; RFQ Documentation, Q3 2026</b>",
        "paragraphs": [
            "A shared workspace file used as a staging point in the thread-hijack story. Attackers "
            "stage lures on trusted collaboration platforms so the first hop looks legitimate. This "
            "is a fabricated, inert page dressed as a Figma file; the host is a Sublime demo site.",
        ],
        "frames": [
            ("fr1", "Quote Pack", "Frame &middot; 1440&times;1024"),
            ("fr2", "Remittance Advice", "Frame &middot; 1440&times;1024"),
            ("fr3", "Delivery Schedule", "Frame &middot; 1440&times;1024"),
            ("fr4", "Bank Details", "Frame &middot; 1440&times;1024"),
        ],
        "table": [
            ("Shared by", "Avery Demo (fictional)"),
            ("Last edited", "Today"),
            ("Access", "Anyone with the link can view (lure wording)"),
        ],
        "explain": "Primary link in the <b>vendor thread hijack</b> sample, shown as a direct "
        "Figma-style file URL on the controlled host. The rule keys on the thread, the trusted "
        "sender, the banking-change language and the platforms named in the text, not on this page.",
        "marker": "RFQ Documentation, Q3 2026",
    },
    # ---- Legacy routes kept live so already-ingested EU copies still resolve ----
    {
        "route": "rfq-portal/",
        "chrome": "doc",
        "kicker": "Secure Document Portal",
        "heading": "Q3_2026_Facilities_RFQ.pdf",
        "crumb": "Secure Document Portal <b>&rsaquo; Q3_2026_Facilities_RFQ.pdf</b>",
        "doc": ("Q3_2026_Facilities_RFQ.pdf", "Shared by Avery Demo, BuildRight Contractors (fictional) &middot; preview only"),
        "paragraphs": [
            "Document preview for the Q3 2026 facilities request for quote. This is a static, "
            "read-only rendering. There is nothing to download and nothing to submit.",
        ],
        "sections": [
            ("Section 1", "Mechanical and electrical works"),
            ("Section 2", "Partitioning and joinery"),
            ("Section 3", "Server room cooling upgrade (provisional sum)"),
            ("Return quotes by", "Friday, end of business"),
        ],
        "explain": "Legacy route kept live so earlier ingested copies still resolve. The current "
        "secure document share sample points at the Drive-style file view instead.",
        "marker": "Secure Document Portal",
    },
    {
        "route": "sharepoint/sites/procurement/Q3-RFQ/",
        "chrome": "doc",
        "kicker": "Company portal mirror",
        "heading": "Procurement: Q3 RFQ (mirror)",
        "crumb": "Company portal <b>&rsaquo; Procurement &rsaquo; Q3 RFQ</b>",
        "paragraphs": [
            "This path is the text an earlier revision of the email displayed for its mirror link. "
            "The real link pointed elsewhere, to the Secure Document Portal page.",
        ],
        "sections": [
            ("Displayed as", "company portal mirror"),
            ("Actually links to", "rfq-portal/"),
        ],
        "explain": "Legacy route kept live for earlier ingested copies. The current sample uses a "
        "Drive-style folder for the display-text mismatch leg.",
        "marker": "Procurement: Q3 RFQ (mirror)",
    },
    {
        "route": "document-viewer/",
        "chrome": "doc",
        "kicker": "Online Document Viewer",
        "heading": "Viewing: Q3_2026_Facilities_RFQ.pdf",
        "crumb": "Online Document Viewer <b>&rsaquo; Q3_2026_Facilities_RFQ.pdf</b>",
        "doc": ("Q3_2026_Facilities_RFQ.pdf", "4 pages &middot; read-only preview"),
        "paragraphs": [
            "Page 1 of 4. Request for quote, Q3 2026 facilities refresh, Tyrell Corporation "
            "(fictional). Scope: M&amp;E works, joinery, and a provisional server room cooling upgrade.",
        ],
        "sections": [
            ("Viewer mode", "Read-only"),
            ("Pages", "4"),
            ("Classification", "Demo content, fabricated"),
        ],
        "explain": "Legacy route kept live for earlier ingested copies that reached it through the "
        "old quick-access hop.",
        "marker": "Online Document Viewer",
    },
    {
        "route": "shared-workspace/rfq-documentation-q3-2026/",
        "chrome": "figma",
        "kicker": "Shared design workspace",
        "heading": "RFQ Documentation, Q3 2026",
        "crumb": "Drafts <b>&rsaquo; BuildRight &rsaquo; RFQ Documentation, Q3 2026</b>",
        "paragraphs": [
            "A shared workspace file used as a staging point in the thread hijack story. Attackers "
            "stage lures on trusted collaboration platforms so the first hop looks legitimate.",
        ],
        "frames": [
            ("fr1", "Quote Pack", "Frame"),
            ("fr2", "Remittance Advice", "Frame"),
            ("fr3", "Delivery Schedule", "Frame"),
        ],
        "table": [
            ("Frames", "Quote pack, remittance advice, delivery schedule"),
            ("Shared by", "Avery Demo (fictional)"),
        ],
        "explain": "Legacy route kept live for the retired Figma-style vendor variant and earlier "
        "ingested copies. The current thread-hijack sample uses the figma/design/ file URL.",
        "marker": "RFQ Documentation, Q3 2026",
    },
    {
        "route": "onedrive-mirror/rfq-q3-2026/",
        "chrome": "drive",
        "kicker": "File share mirror",
        "heading": "Mirror: RFQ Q3 2026 pack",
        "crumb": "Shared <b>&rsaquo; RFQ Q3 2026 pack</b>",
        "doc": ("RFQ_Q3_2026_pack.zip", "Listed only &middot; no download available"),
        "paragraphs": [
            "Backup link from the hijacked vendor reply. A real lure would ask the reader to verify "
            "an account before the download. Nothing here can be downloaded.",
        ],
        "frames": [
            ("z1", "RFQ.pdf", "In archive"),
            ("z2", "Quote_Pack.xlsx", "In archive"),
            ("z3", "Remittance.pdf", "In archive"),
        ],
        "table": [("Reached from", "Backup mirror link in the hijacked reply")],
        "explain": "Secondary link in the <b>vendor thread hijack</b> sample, kept consistent with "
        "the thread as a mirrored file pack.",
        "marker": "Mirror: RFQ Q3 2026 pack",
    },
    # ---- Sample 03: QR quishing destination ----
    {
        "route": "account-verify/",
        "chrome": "doc",
        "kicker": "Protected Document Access",
        "heading": "Protected document notice",
        "crumb": "Protected delivery <b>&rsaquo; Q3_2026_Facilities_RFQ.pdf</b>",
        "doc": ("Q3_2026_Facilities_RFQ.pdf", "Access via QR code &middot; mobile view"),
        "paragraphs": [
            "You reached this page by scanning the QR code inside a PDF attachment. In a real "
            "attack this is where a phone would be asked for credentials. This page asks for "
            "nothing and stores nothing.",
        ],
        "sections": [
            ("Delivered as", "QR code inside a PDF attachment"),
            ("Document", "Q3_2026_Facilities_RFQ.pdf"),
            ("Access window", "24 hours (lure wording)"),
        ],
        "table": [
            ("Reached via", "Opaque short link, then this page"),
            ("Device", "Mobile camera scan"),
        ],
        "explain": "The decoded destination of the <b>QR quishing</b> sample: a QR code inside a "
        "PDF inside the email. The QR now encodes an opaque /s/ short link that hops here; Sublime "
        "extracts it and runs link analysis along the hop.",
        "marker": "Protected document notice",
    },
    # ---- ClickFix (kept from main; not part of this change, but must keep passing) ----
    {
        "route": "browser-verification/",
        "chrome": "doc",
        "kicker": "Document Verification",
        "heading": "Additional verification required to open this document",
        "crumb": "Document Verification <b>&rsaquo; Q3_2026_Facilities_RFQ.pdf</b>",
        "alert": "Verification failed: this browser could not be confirmed automatically. Complete the manual check below to finish loading the shared document.",
        "paragraphs": [
            "A real ClickFix lure claims the document cannot load until you prove you are "
            "not a bot, then walks you through pasting a command into the Windows Run dialog. "
            "The command is the whole attack: in the wild it fetches and runs malware.",
            "On this demo page the command is harmless and fixed. It prints a single marker "
            "and exits. It downloads nothing, changes nothing, needs no network and is shown "
            "for illustration only; this static page cannot copy anything to your clipboard.",
        ],
        "steps": [
            "Press <kbd>Win</kbd> + <kbd>R</kbd> to open the Run dialog.",
            "Press <kbd>Ctrl</kbd> + <kbd>V</kbd> to paste the verification command.",
            "Press <kbd>Enter</kbd> to finish the check.",
        ],
        "command": CLICKFIX_COMMAND,
        "table": [
            ("Technique", "ClickFix (paste-and-run social engineering)"),
            ("What a real lure runs", "A command that fetches and runs malware"),
            ("What this demo runs", "A fixed, inert marker that prints and exits"),
        ],
        "explain": "End page for the <b>ClickFix</b> browser-verification sample. The danger in a "
        "real ClickFix attack is the command the page instructs the victim to paste and run, not "
        "the page itself. This demo keeps that command constrained to one harmless marker so the "
        "technique is visible with no risk. Detection keys on the lure message and the paste-and-run "
        "instructions, not on anything this page does.",
        "marker": "Additional verification required to open this document",
    },
    # ---- Sample 05: Teams impersonation destination ----
    {
        "route": "teams-message/",
        "chrome": "teams",
        "kicker": "Team chat notification",
        "heading": "Missed message from Rachael Demo",
        "crumb": "Chat <b>&rsaquo; Rachael Demo</b>",
        "paragraphs": [
            "&ldquo;I need you to look at this before the board meeting.&rdquo;",
            "This is the landing page for a fake chat notification. A real lure would ask the "
            "reader to re-enter account details here. This page has no fields at all.",
        ],
        "sections": [
            ("Channel", "Direct message"),
            ("Received", "Today, 11:04"),
            ("Sender", "Rachael Demo (fictional)"),
        ],
        "table": [
            ("Reached via", "Opaque short link, then this page"),
            ("Workspace", "Tyrell Corporation (fictional)"),
        ],
        "explain": "End page for the <b>brand impersonation</b> sample, reached through an opaque "
        "/s/ short link. Detection comes from the lookalike sender, the freemail Reply-To and the "
        "message language, not from this page.",
        "marker": "Missed message from Rachael Demo",
    },
    # ---- Sample 06: calendar ICS destinations ----
    {
        "route": "billing-review/invoice/NPS-2026-04721/",
        "chrome": "calendar",
        "kicker": "Billing Review",
        "heading": "Invoice NPS-2026-04721",
        "crumb": "Billing Review <b>&rsaquo; Invoice NPS-2026-04721</b>",
        "sections": [
            ("Account", "Tyrell Corporation (fictional)"),
            ("Amount", "$3,249.00"),
            ("Status", "Payment processed (lure wording)"),
            ("Callback in the lure", "Phone billing, not the meeting dial-in"),
        ],
        "table": [
            ("Reached via", "Opaque short link from the calendar invite"),
            ("Invoice", "NPS-2026-04721"),
        ],
        "paragraphs": [
            "Invoice summary page referenced by a calendar invite. The lure tells the reader to "
            "phone a dispute line instead of using the meeting dial-in.",
        ],
        "explain": "Linked from the description and URL fields of the <b>calendar ICS abuse</b> "
        "sample through an opaque /s/ short link. The payload story lives in the calendar object; "
        "this page is only the review link.",
        "marker": "Invoice NPS-2026-04721",
    },
    {
        "route": "billing-review/dispute/",
        "chrome": "calendar",
        "kicker": "Billing Review",
        "heading": "Dispute invoice NPS-2026-04721",
        "crumb": "Billing Review <b>&rsaquo; Dispute NPS-2026-04721</b>",
        "paragraphs": [
            "This page is the destination of the button inside the HTML invoice that is embedded, "
            "base64-encoded, in the calendar invite's attachment field.",
        ],
        "sections": [
            ("Reached from", "HTML invoice embedded in the ICS ATTACH property"),
            ("Invoice", "NPS-2026-04721"),
        ],
        "table": [
            ("Reached via", "Opaque short link from the embedded invoice"),
        ],
        "explain": "Second link in the <b>calendar ICS abuse</b> sample, reached through its own "
        "opaque /s/ short link. It only exists inside a document smuggled into the calendar file.",
        "marker": "Dispute invoice NPS-2026-04721",
    },
    # ---- Sample 07: voicemail (retired from active set; route kept live) ----
    {
        "route": "voicemail/play/",
        "chrome": "voicemail",
        "kicker": "Voicemail",
        "heading": "Voicemail from +1 (555) 847-3201",
        "crumb": "Voicemail <b>&rsaquo; Inbox &rsaquo; +1 (555) 847-3201</b>",
        "sections": [
            ("Duration", "1:47"),
            ("Received", "10:02 AM"),
            ("Playback", "Not available on this demo page"),
        ],
        "paragraphs": [
            "A real voicemail lure hosts its page on trusted cloud storage so URL reputation sees a "
            "well-known provider. This page plays nothing and requests nothing.",
        ],
        "explain": "End page for the <b>service abuse</b> voicemail sample. Kept live for earlier "
        "ingested copies; this sample is not part of the current refresh set.",
        "marker": "Voicemail from +1 (555) 847-3201",
    },
    {
        "route": "voicemail/settings/",
        "chrome": "voicemail",
        "kicker": "Voicemail",
        "heading": "Voicemail settings",
        "crumb": "Voicemail <b>&rsaquo; Settings</b>",
        "paragraphs": [
            "Secondary link from the voicemail lure footer. There are no settings to change here.",
        ],
        "sections": [("Reached from", "Manage voicemail settings link")],
        "table": [("Preferences", "Read-only on this demo page")],
        "explain": "Secondary link in the <b>service abuse</b> voicemail sample. Kept live for "
        "earlier ingested copies.",
        "marker": "Voicemail settings",
    },
    # ---- Vendor trio (retired from active set; routes kept live) ----
    {
        "route": "remittance/updated-account/",
        "chrome": "doc",
        "kicker": "Remittance Advice",
        "heading": "Updated remittance advice",
        "crumb": "Remittance <b>&rsaquo; Updated account</b>",
        "sections": [
            ("Payee", "BuildRight Contractors (fictional)"),
            ("Reason given", "Bank details changed since last project"),
            ("Beneficiary details", "Withheld on this demo page"),
        ],
        "paragraphs": [
            "The lookalike-domain reply sends the reader here to collect new banking details. "
            "This page shows the story, not real account data.",
        ],
        "explain": "Primary link in the <b>trusted vendor lookalike hijack</b> sample. Kept live; "
        "this sample is not part of the current refresh set.",
        "marker": "Updated remittance advice",
    },
    {
        "route": "quote-pack/q3-2026/",
        "chrome": "doc",
        "kicker": "Quote Pack",
        "heading": "Revised quote pack, Q3 2026",
        "crumb": "Quote Pack <b>&rsaquo; Q3 2026</b>",
        "doc": ("BuildRight_Q3_2026_Quote_Pack.pdf", "Preview only"),
        "paragraphs": [
            "Backup link from the lookalike-domain reply. Read-only demo page.",
        ],
        "sections": [("Reached from", "Backup link in the lookalike hijack")],
        "explain": "Secondary link in the <b>trusted vendor lookalike hijack</b> sample. Kept live.",
        "marker": "Revised quote pack, Q3 2026",
    },
    {
        "route": "remittance/account-update/",
        "chrome": "doc",
        "kicker": "Remittance Advice",
        "heading": "Remittance account update",
        "crumb": "Remittance <b>&rsaquo; Account update</b>",
        "sections": [
            ("Payee", "BuildRight Contractors (fictional)"),
            ("Instruction in the lure", "Move the deposit to a new settlement account"),
            ("Clearing time in the lure", "Two business days"),
            ("Beneficiary details", "Withheld on this demo page"),
        ],
        "paragraphs": [
            "Sent from the genuine vendor mailbox after it was compromised, with SPF, DKIM and DMARC "
            "all passing. Only the behaviour changed.",
        ],
        "explain": "Link in the <b>compromised vendor mailbox</b> sample. Kept live; this sample is "
        "not part of the current refresh set.",
        "marker": "Remittance account update",
    },
    # ---- Sample 08 DocuSign QR destination ----
    {
        "route": "esign/review/",
        "chrome": "esign",
        "kicker": "Electronic Signature Review",
        "heading": "Q1 Executive Compensation Agreement",
        "crumb": "Envelope <b>&rsaquo; Q1 Executive Compensation Agreement</b>",
        "doc": ("Q1_Executive_Compensation_Agreement.pdf", "Review copy &middot; signing disabled"),
        "paragraphs": [
            "Destination of the QR code embedded inline in an e-signature lure. A real lure would "
            "ask for mailbox details before showing the document.",
        ],
        "frames": [
            ("d1", "Agreement", "Page 1 of 3"),
            ("d2", "Schedule A", "Page 2 of 3"),
            ("d3", "Signatures", "Page 3 of 3"),
        ],
        "sections": [
            ("Delivered as", "Inline QR image in the message body"),
            ("Expires (lure wording)", "48 hours"),
        ],
        "table": [
            ("Reached via", "Opaque short link from the inline QR"),
            ("Signer", "Casey Demo (fictional)"),
        ],
        "explain": "QR destination for the <b>e-signature inline QR</b> sample, reached through an "
        "opaque /s/ short link decoded from the inline QR image.",
        "marker": "Q1 Executive Compensation Agreement",
    },
]

# Opaque short links. Each maps a link-target id (the deterministic code seed,
# shared with the demo sample pack) to the route it hops to. The hop renders its
# destination's dense UI with a 0-second meta refresh and a visible fallback link.
SHORT_LINKS: list[dict] = [
    {"id": "qr_account_verify", "target": "account-verify/"},
    {"id": "teams_message", "target": "teams-message/"},
    {"id": "calendar_billing_review", "target": "billing-review/invoice/NPS-2026-04721/"},
    {"id": "calendar_embedded_dispute", "target": "billing-review/dispute/"},
    {"id": "calendar_tiff_portal_metadata", "target": "billing-review/invoice/NPS-2026-04721/"},
    {"id": "esign_inline_qr", "target": "esign/review/"},
]

# Legacy single hop kept live so earlier ingested copies of sample 02 still resolve.
REFRESH_HOPS: list[dict] = [
    {
        "route": "go/viewer/",
        "target": "document-viewer/",
        "heading": "Opening the document viewer",
        "explain": "Legacy HTML <b>meta refresh</b> hop kept live for earlier ingested copies. "
        "GitHub Pages cannot send HTTP 302 responses; browsers and link detonation follow the "
        "refresh, and the visible link below does the same thing by hand.",
        "marker": "Opening the document viewer",
    },
]

_PAGES_BY_ROUTE = {page["route"]: page for page in PAGES}


def head(title: str, extra: str = "") -> str:
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        f"<meta http-equiv=\"Content-Security-Policy\" content=\"{CSP}\">\n"
        "<meta name=\"referrer\" content=\"no-referrer\">\n"
        "<meta name=\"robots\" content=\"noindex, nofollow, noarchive, nosnippet\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"{extra}"
        f"<title>{html.escape(title)} | {BANNER_MARKER}</title>\n"
        f"<style>\n{STYLE}\n</style>\n</head>\n"
    )


def banner() -> str:
    return (
        "<div class=\"demo-banner\"><span class=\"dot\"></span>"
        f"<strong>{BANNER_MARKER}</strong>"
        "<span class=\"tag\">Fabricated training page for email security demos. Static and inert: "
        "nothing on this page collects, stores or submits data.</span></div>\n"
    )


def footer(route: str) -> str:
    return (
        "<p class=\"foot\">Demo route <span class=\"route\">/"
        f"{html.escape(route)}</span>. All names, companies and figures are fictional.</p>\n"
    )


_AVATAR_COLORS = ("#2684FF", "#12A45A", "#D64B3C", "#9B59B6")


def appbar(page: dict, chrome: dict) -> str:
    style = f"--bar:{chrome['bar']};--barink:{chrome['barink']};--accent:{chrome['accent']}"
    border = ";border:1px solid var(--border);border-bottom:none" if chrome.get("border_bar") else ""
    brand = chrome.get("brand", "")
    brand_html = f"<span class=\"brand\">{chrome['mark']}{html.escape(brand) if brand else ''}</span>"
    initials = ("AD", "CD", "RT")
    avatars = "".join(
        f"<span class=\"ava\" style=\"background:{_AVATAR_COLORS[i]}\">{txt}</span>"
        for i, txt in enumerate(initials)
    )
    pills = (
        "<span class=\"pill\">Comment</span>"
        "<span class=\"pill solid\">Share</span>"
    )
    return (
        f"<header class=\"appbar\" style=\"{style}{border}\">{brand_html}"
        f"<span class=\"sep\">/</span><span class=\"file\">{page['heading']}</span>"
        f"<span class=\"spacer\"></span><span class=\"presence\">{avatars}</span>{pills}</header>\n"
    )


def subbar(page: dict) -> str:
    crumb = page.get("crumb", page["heading"])
    tools = "".join(f"<span class=\"tool\">{t}</span>" for t in ("Open", "Details", "Activity"))
    return (
        f"<div class=\"subbar\"><span class=\"crumb\">{crumb}</span>"
        f"<span class=\"spacer\"></span>{tools}</div>\n"
    )


def rail(chrome: dict) -> str:
    rows = "".join(
        f"<div class=\"row{' active' if active else ''}\">"
        f"<span class=\"ico{' g' if active else ''}\"></span>{html.escape(label)}</div>"
        for label, active in chrome.get("rail", [])
    )
    return (
        f"<aside class=\"rail\"><h4>{html.escape(chrome.get('rail_head', 'Files'))}</h4>"
        f"{rows}<div class=\"divider\"></div>"
        "<div class=\"row\"><span class=\"ico\"></span>Shared</div>"
        "<div class=\"row\"><span class=\"ico\"></span>Recent</div></aside>\n"
    )


def frames_block(frames: list) -> str:
    cells = []
    for _key, title, meta in frames:
        cells.append(
            "<div class=\"frame\"><div class=\"thumb\"><span class=\"ln a\"></span>"
            "<span class=\"ln b\"></span><span class=\"ln c\"></span><span class=\"chip\"></span></div>"
            f"<div class=\"cap\"><b>{title}</b><span>{meta}</span></div></div>"
        )
    return f"<div class=\"frames\">{''.join(cells)}</div>\n"


def sections_block(rows: list) -> str:
    items = "".join(f"<div class=\"s\"><b>{k}</b><span>{v}</span></div>" for k, v in rows)
    return f"<div class=\"sections\">{items}</div>\n"


def stage(page: dict) -> str:
    parts = [
        "<main class=\"stage\">\n",
        f"<p class=\"kicker\">{page['kicker']}</p><h1>{page['heading']}</h1>\n",
    ]
    if page.get("doc"):
        name, meta = page["doc"]
        parts.append(f"<div class=\"doc\">{DOC_ICON}<div><strong>{name}</strong><span>{meta}</span></div></div>\n")
    if page.get("alert"):
        parts.append(f"<div class=\"alert\">{page['alert']}</div>\n")
    for paragraph in page.get("paragraphs", []):
        parts.append(f"<p>{paragraph}</p>\n")
    if page.get("steps"):
        steps = "".join(f"<li>{step}</li>" for step in page["steps"])
        parts.append(f"<ol class=\"steps\">{steps}</ol>\n")
    if page.get("command"):
        parts.append(
            "<div class=\"cmd\"><span class=\"cmd-label\">Command the lure tells you to paste</span>"
            f"<code>{html.escape(page['command'])}</code></div>\n"
        )
    if page.get("frames"):
        parts.append(frames_block(page["frames"]))
    if page.get("sections"):
        parts.append(sections_block(page["sections"]))
    if page.get("table"):
        rows = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in page["table"])
        parts.append(f"<table class=\"meta\">{rows}</table>\n")
    parts.append(f"<div class=\"explain\">{page['explain']}</div>\n")
    parts.append("</main>\n")
    return "".join(parts)


def render_page(page: dict, extra_head: str = "", hopnote: str = "") -> str:
    chrome = CHROMES[page["chrome"]]
    parts = [head(page["heading"], extra_head), "<body>\n", banner()]
    if hopnote:
        parts.append(hopnote)
    parts.append("<div class=\"app\">\n")
    parts.append(appbar(page, chrome))
    parts.append(subbar(page))
    parts.append("<div class=\"layout\">\n")
    parts.append(rail(chrome))
    parts.append(stage(page))
    parts.append("</div>\n")
    parts.append("</div>\n")
    parts.append(footer(page["route"]))
    parts.append("</body>\n</html>\n")
    return "".join(parts)


def render_short_hop(code: str, target_route: str) -> str:
    """Render an opaque /s/<code>/ hop: the destination's dense UI, a 0-second
    meta refresh and a visible fallback link. Depth of s/<code>/ is two segments."""
    target_page = _PAGES_BY_ROUTE[target_route]
    rel = "../../" + target_route
    refresh = f"<meta http-equiv=\"refresh\" content=\"0; url={rel}\">\n"
    hopnote = (
        "<div class=\"hopnote\"><span>Opening the shared item&hellip;</span><span class=\"sp\"></span>"
        f"<a href=\"{rel}\">continue if nothing happens</a></div>\n"
    )
    page = dict(target_page)
    page["route"] = f"s/{code}/"
    return render_page(page, extra_head=refresh, hopnote=hopnote)


def render_hop(hop: dict) -> str:
    depth = hop["route"].strip("/").count("/") + 1
    target = "../" * depth + hop["target"]
    refresh = f"<meta http-equiv=\"refresh\" content=\"0; url={target}\">\n"
    return (
        head(hop["heading"], refresh)
        + "<body>\n"
        + banner()
        + "<main class=\"wrap\">\n<div class=\"app\">\n"
        + "<header class=\"appbar\" style=\"--bar:#111;--barink:#fff;--accent:#006D49\">"
        + "<span class=\"brand\">" + DOC_MARK + "Link hop</span></header>\n"
        + "<div class=\"layout\"><main class=\"stage\">\n"
        + f"<p class=\"kicker\">Link hop</p><h1>{hop['heading']}</h1>\n"
        + f"<p>If nothing happens, <a href=\"{target}\">continue to the document viewer</a>.</p>\n"
        + f"<div class=\"explain\">{hop['explain']}</div>\n"
        + "</main></div>\n</div>\n"
        + footer(hop["route"])
        + "</main>\n</body>\n</html>\n"
    )


def render_index() -> str:
    items = "".join(
        f"<tr><th><a href=\"{p['route']}\">{p['heading']}</a></th><td>/{p['route']}</td></tr>"
        for p in PAGES
    )
    items += "".join(
        f"<tr><th><a href=\"s/{short_code(s['id'])}/\">Short link to {_PAGES_BY_ROUTE[s['target']]['heading']}</a></th>"
        f"<td>/s/{short_code(s['id'])}/</td></tr>"
        for s in SHORT_LINKS
    )
    items += "".join(
        f"<tr><th><a href=\"{h['route']}\">{h['heading']} (meta refresh)</a></th><td>/{h['route']}</td></tr>"
        for h in REFRESH_HOPS
    )
    return (
        head("Index")
        + "<body>\n"
        + banner()
        + "<main class=\"wrap\">\n<div class=\"app\">\n"
        + "<header class=\"appbar\" style=\"--bar:#111;--barink:#fff;--accent:#006D49\">"
        + "<span class=\"brand\">" + DOC_MARK + "Demo landing pages</span></header>\n"
        + "<div class=\"layout\"><main class=\"stage\">\n"
        + "<p class=\"kicker\">Index</p><h1>Demo landing pages</h1>\n"
        + "<p>Inert end pages for synthetic phishing samples used in email security demos. Every "
        "page is fabricated and static. Opaque /s/ short links hop to their destination with an "
        "HTML meta refresh.</p>\n"
        + f"<table class=\"meta\">{items}</table>\n"
        + "</main></div>\n</div>\n"
        + footer("")
        + "</main>\n</body>\n</html>\n"
    )


def render_404() -> str:
    return (
        head("Not found")
        + "<body>\n"
        + banner()
        + "<main class=\"wrap\">\n<div class=\"app\">\n"
        + "<header class=\"appbar\" style=\"--bar:#111;--barink:#fff;--accent:#006D49\">"
        + "<span class=\"brand\">" + DOC_MARK + "Not found</span></header>\n"
        + "<div class=\"layout\"><main class=\"stage\">"
        + "<h1>No demo page at this path</h1><p>This path is not part of the demo site. All demo "
        "routes are listed on the index page.</p></main></div>\n</div>\n"
        + "</main>\n</body>\n</html>\n"
    )


def main() -> int:
    # Fail fast if a short link targets a route that does not exist.
    for link in SHORT_LINKS:
        if link["target"] not in _PAGES_BY_ROUTE:
            raise SystemExit(f"short link {link['id']} targets unknown route {link['target']}")
    codes = [short_code(link["id"]) for link in SHORT_LINKS]
    if len(set(codes)) != len(codes):
        raise SystemExit("short-link codes are not unique")

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    (OUT / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    (OUT / "index.html").write_text(render_index(), encoding="utf-8")
    (OUT / "404.html").write_text(render_404(), encoding="utf-8")

    routes = [{"path": "", "kind": "page", "marker": "Demo landing pages"}]
    for page in PAGES:
        target = OUT / page["route"] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_page(page), encoding="utf-8")
        route = {"path": page["route"], "kind": "page", "marker": page["marker"]}
        if page.get("command"):
            route["kind"] = "clickfix"
            route["command"] = page["command"]
        routes.append(route)
    for link in SHORT_LINKS:
        code = short_code(link["id"])
        route_path = f"s/{code}/"
        target = OUT / route_path / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_short_hop(code, link["target"]), encoding="utf-8")
        routes.append(
            {
                "path": route_path,
                "kind": "meta-refresh",
                "marker": _PAGES_BY_ROUTE[link["target"]]["marker"],
                "refresh_to": link["target"],
            }
        )
    for hop in REFRESH_HOPS:
        target = OUT / hop["route"] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_hop(hop), encoding="utf-8")
        routes.append(
            {"path": hop["route"], "kind": "meta-refresh", "marker": hop["marker"], "refresh_to": hop["target"]}
        )
    (HERE / "routes.json").write_text(
        json.dumps({"banner_marker": BANNER_MARKER, "routes": routes}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(routes)} routes to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
