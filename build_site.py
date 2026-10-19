#!/usr/bin/env python3
"""Build the static demo landing pages into docs/.

Version: 2026.10.19.1

Every page is fabricated, inert demo content: static HTML and inline CSS only.
No forms, inputs, buttons, scripts, iframes, external assets, trackers or cookies.
Each page carries a visible "Sublime Security Demo Asset" banner, a strict
Content-Security-Policy meta tag and noindex metadata.

The output is deterministic: running this twice produces byte-identical files.
routes.json is written alongside so check_site.py knows every published path.

Usage:
    python3 build_site.py            # writes docs/ and routes.json
"""

from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "docs"
BANNER_MARKER = "Sublime Security Demo Asset"

CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; "
    "base-uri 'none'; form-action 'none'"
)

STYLE = """
:root{--green:#04E69B;--green-neutral:#F0FBF6;--green-shade:#006D49;--ink:#000;--text:#575757;--muted:#7F7F7F;--border:#D6D6D6;--page:#FAFAFA}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;font-size:15px;line-height:1.55}
.demo-banner{background:var(--ink);color:#fff;padding:10px 20px;font-size:13px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.demo-banner strong{color:var(--green);letter-spacing:.02em}
.demo-banner .dot{width:10px;height:10px;border-radius:50%;background:var(--green);flex:none}
.wrap{max-width:760px;margin:28px auto;padding:0 16px}
.card{background:#fff;border:1px solid var(--border);border-radius:8px;overflow:hidden}
.card-head{padding:20px 28px;border-bottom:1px solid var(--border);background:var(--green-neutral)}
.kicker{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--green-shade);font-weight:600;margin:0 0 4px}
h1{font-size:22px;margin:0;font-weight:600}
.card-body{padding:24px 28px}
.card-body p{color:var(--text);margin:0 0 14px}
table{width:100%;border-collapse:collapse;margin:8px 0 18px;font-size:14px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--border)}
th{background:var(--page);font-weight:600;width:38%}
td{color:var(--text);font-family:"SF Mono",Menlo,Consolas,monospace;font-size:13px}
.doc{display:flex;gap:14px;align-items:center;border:1px solid var(--border);border-radius:8px;padding:14px 16px;margin:4px 0 18px}
.doc svg{flex:none}
.doc strong{display:block}
.doc span{font-size:13px;color:var(--muted)}
.explain{border-left:3px solid var(--green);background:var(--green-neutral);padding:12px 16px;border-radius:0 6px 6px 0;font-size:14px;color:var(--text);margin-top:6px}
.explain b{color:var(--ink)}
a{color:var(--green-shade)}
.foot{font-size:12px;color:var(--muted);margin:16px 4px 40px}
.route{font-family:"SF Mono",Menlo,Consolas,monospace}
""".strip()

DOC_ICON = (
    '<svg width="40" height="48" viewBox="0 0 40 48" aria-hidden="true">'
    '<path d="M4 2h22l10 10v32a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" '
    'fill="#F0FBF6" stroke="#006D49" stroke-width="2"/>'
    '<path d="M26 2v10h10" fill="none" stroke="#006D49" stroke-width="2"/>'
    '<rect x="9" y="22" width="20" height="3" rx="1.5" fill="#04E69B"/>'
    '<rect x="9" y="29" width="16" height="3" rx="1.5" fill="#D6D6D6"/>'
    '<rect x="9" y="36" width="18" height="3" rx="1.5" fill="#D6D6D6"/></svg>'
)

# Each page: route (directory path under the site), title, kicker, heading,
# paragraphs, optional document card, optional details table, explanation and
# the expected marker the health check asserts on.
PAGES: list[dict] = [
    {
        "route": "rfq-portal/",
        "kicker": "Secure Document Portal",
        "heading": "Q3_2026_Facilities_RFQ.pdf",
        "doc": ("Q3_2026_Facilities_RFQ.pdf", "Shared by Avery Demo, BuildRight Contractors (fictional) &middot; preview only"),
        "paragraphs": [
            "Document preview for the Q3 2026 facilities request for quote. This is a static, "
            "read-only rendering. There is nothing to download and nothing to submit.",
        ],
        "table": [
            ("Section 1", "Mechanical and electrical works"),
            ("Section 2", "Partitioning and joinery"),
            ("Section 3", "Server room cooling upgrade (provisional sum)"),
            ("Return quotes by", "Friday, end of business"),
        ],
        "explain": "This is the end page behind the bare URL and behind the mismatched link text in "
        "the <b>secure document share</b> sample. Link analysis should show this page as the "
        "effective URL with a 200 response.",
        "marker": "Secure Document Portal",
    },
    {
        "route": "sharepoint/sites/procurement/Q3-RFQ/",
        "kicker": "Company portal mirror",
        "heading": "Procurement: Q3 RFQ (mirror)",
        "paragraphs": [
            "This path is the text the email displays for its mirror link. The email's real link "
            "points somewhere else, to the Secure Document Portal page.",
        ],
        "table": [
            ("Displayed as", "company portal mirror"),
            ("Actually links to", "rfq-portal/"),
        ],
        "explain": "The <b>display text versus href mismatch</b> leg of the secure document share "
        "sample. Both the displayed path and the real destination are inert demo pages.",
        "marker": "Procurement: Q3 RFQ (mirror)",
    },
    {
        "route": "document-viewer/",
        "kicker": "Online Document Viewer",
        "heading": "Viewing: Q3_2026_Facilities_RFQ.pdf",
        "doc": ("Q3_2026_Facilities_RFQ.pdf", "4 pages &middot; read-only preview"),
        "paragraphs": [
            "Page 1 of 4. Request for quote, Q3 2026 facilities refresh, Tyrell Corporation "
            "(fictional). Scope: M&amp;E works, joinery, and a provisional server room cooling upgrade.",
        ],
        "table": [
            ("Viewer mode", "Read-only"),
            ("Pages", "4"),
            ("Classification", "Demo content, fabricated"),
        ],
        "explain": "The destination of the <b>quick-access link</b> in the secure document share "
        "sample. That link first opens a short hop page that forwards here with an HTML meta refresh.",
        "marker": "Online Document Viewer",
    },
    {
        "route": "account-verify/",
        "kicker": "Protected Document Access",
        "heading": "Protected document notice",
        "doc": ("Q3_2026_Facilities_RFQ.pdf", "Access via QR code &middot; mobile view"),
        "paragraphs": [
            "You reached this page by scanning the QR code inside a PDF attachment. In a real "
            "attack this is where a phone would be asked for credentials. This page asks for "
            "nothing and stores nothing.",
        ],
        "table": [
            ("Delivered as", "QR code inside a PDF attachment"),
            ("Document", "Q3_2026_Facilities_RFQ.pdf"),
            ("Access window", "24 hours (lure wording)"),
        ],
        "explain": "The decoded destination of the <b>QR quishing</b> sample: a QR code inside a "
        "PDF inside the email. Sublime extracts it and runs link analysis against this page.",
        "marker": "Protected document notice",
    },
    {
        "route": "teams-message/",
        "kicker": "Team chat notification",
        "heading": "Missed message from Rachael Demo",
        "paragraphs": [
            "&ldquo;I need you to look at this before the board meeting.&rdquo;",
            "This is the landing page for a fake chat notification. A real lure would ask the "
            "reader to re-enter account details here. This page has no fields at all.",
        ],
        "table": [
            ("Channel", "Direct message"),
            ("Received", "Today, 11:04"),
            ("Sender", "Rachael Demo (fictional)"),
        ],
        "explain": "End page for the <b>brand impersonation</b> sample. Detection comes from the "
        "lookalike sender, the freemail Reply-To and the message language, not from this page.",
        "marker": "Missed message from Rachael Demo",
    },
    {
        "route": "billing-review/invoice/NPS-2026-04721/",
        "kicker": "Billing Review",
        "heading": "Invoice NPS-2026-04721",
        "table": [
            ("Account", "Tyrell Corporation (fictional)"),
            ("Amount", "$3,249.00"),
            ("Status", "Payment processed (lure wording)"),
            ("Dispute line in the lure", "+1 (555) 010-5957 (fictional)"),
        ],
        "paragraphs": [
            "Invoice summary page referenced by a calendar invite. The lure tells the reader to "
            "phone a dispute line instead of using the meeting dial-in.",
        ],
        "explain": "Linked from the description and URL fields of the <b>calendar ICS abuse</b> "
        "sample. The payload story lives in the calendar object; this page is only the review link.",
        "marker": "Invoice NPS-2026-04721",
    },
    {
        "route": "billing-review/dispute/",
        "kicker": "Billing Review",
        "heading": "Dispute invoice NPS-2026-04721",
        "paragraphs": [
            "This page is the destination of the button inside the HTML invoice that is embedded, "
            "base64-encoded, in the calendar invite's attachment field.",
        ],
        "table": [
            ("Reached from", "HTML invoice embedded in the ICS ATTACH property"),
            ("Invoice", "NPS-2026-04721"),
        ],
        "explain": "Second link in the <b>calendar ICS abuse</b> sample. It only exists inside a "
        "document smuggled into the calendar file.",
        "marker": "Dispute invoice NPS-2026-04721",
    },
    {
        "route": "voicemail/play/",
        "kicker": "Voicemail",
        "heading": "Voicemail from +1 (555) 847-3201",
        "table": [
            ("Duration", "1:47"),
            ("Received", "10:02 AM"),
            ("Playback", "Not available on this demo page"),
        ],
        "paragraphs": [
            "A real voicemail lure hosts its page on trusted cloud storage so URL reputation sees a "
            "well-known provider. This page plays nothing and requests nothing.",
        ],
        "explain": "End page for the <b>service abuse</b> voicemail sample. The authentication "
        "failures on the claimed sender are the headline signal.",
        "marker": "Voicemail from +1 (555) 847-3201",
    },
    {
        "route": "voicemail/settings/",
        "kicker": "Voicemail",
        "heading": "Voicemail settings",
        "paragraphs": [
            "Secondary link from the voicemail lure footer. There are no settings to change here.",
        ],
        "table": [("Reached from", "Manage voicemail settings link")],
        "explain": "Secondary link in the <b>service abuse</b> voicemail sample.",
        "marker": "Voicemail settings",
    },
    {
        "route": "shared-workspace/rfq-documentation-q3-2026/",
        "kicker": "Shared design workspace",
        "heading": "RFQ Documentation, Q3 2026",
        "doc": ("RFQ-Documentation-Q3-2026", "Shared workspace file &middot; view only"),
        "paragraphs": [
            "A shared workspace file used as a staging point in the thread hijack story. Attackers "
            "stage lures on trusted collaboration platforms so the first hop looks legitimate.",
        ],
        "table": [
            ("Frames", "Quote pack, remittance advice, delivery schedule"),
            ("Shared by", "Avery Demo (fictional)"),
        ],
        "explain": "Primary link in the <b>vendor thread hijack</b> sample. The rule keys on the "
        "thread, the trusted sender, the banking-change language and the platforms named in the text.",
        "marker": "RFQ Documentation, Q3 2026",
    },
    {
        "route": "onedrive-mirror/rfq-q3-2026/",
        "kicker": "File share mirror",
        "heading": "Mirror: RFQ Q3 2026 pack",
        "doc": ("RFQ_Q3_2026_pack.zip", "Listed only &middot; no download available"),
        "paragraphs": [
            "Backup link from the hijacked vendor reply. A real lure would ask the reader to verify "
            "an account before the download. Nothing here can be downloaded.",
        ],
        "table": [("Reached from", "Backup mirror link in the hijacked reply")],
        "explain": "Secondary link in the <b>vendor thread hijack</b> sample.",
        "marker": "Mirror: RFQ Q3 2026 pack",
    },
    {
        "route": "remittance/updated-account/",
        "kicker": "Remittance Advice",
        "heading": "Updated remittance advice",
        "table": [
            ("Payee", "BuildRight Contractors (fictional)"),
            ("Reason given", "Bank details changed since last project"),
            ("Beneficiary details", "Withheld on this demo page"),
        ],
        "paragraphs": [
            "The lookalike-domain reply sends the reader here to collect new banking details. "
            "This page shows the story, not real account data.",
        ],
        "explain": "Primary link in the <b>trusted vendor lookalike hijack</b> sample.",
        "marker": "Updated remittance advice",
    },
    {
        "route": "quote-pack/q3-2026/",
        "kicker": "Quote Pack",
        "heading": "Revised quote pack, Q3 2026",
        "doc": ("BuildRight_Q3_2026_Quote_Pack.pdf", "Preview only"),
        "paragraphs": [
            "Backup link from the lookalike-domain reply. Read-only demo page.",
        ],
        "table": [("Reached from", "Backup link in the lookalike hijack")],
        "explain": "Secondary link in the <b>trusted vendor lookalike hijack</b> sample.",
        "marker": "Revised quote pack, Q3 2026",
    },
    {
        "route": "remittance/account-update/",
        "kicker": "Remittance Advice",
        "heading": "Remittance account update",
        "table": [
            ("Payee", "BuildRight Contractors (fictional)"),
            ("Instruction in the lure", "Move the deposit to a new settlement account"),
            ("Clearing time in the lure", "Two business days"),
            ("Beneficiary details", "Withheld on this demo page"),
        ],
        "paragraphs": [
            "Sent from the genuine vendor mailbox after it was compromised, with SPF, DKIM and DMARC "
            "all passing. Only the behaviour changed.",
        ],
        "explain": "Link in the <b>compromised vendor mailbox</b> sample.",
        "marker": "Remittance account update",
    },
    {
        "route": "esign/review/",
        "kicker": "Electronic Signature Review",
        "heading": "Q1 Executive Compensation Agreement",
        "doc": ("Q1_Executive_Compensation_Agreement.pdf", "Review copy &middot; signing disabled"),
        "paragraphs": [
            "Destination of the QR code embedded inline in an e-signature lure. A real lure would "
            "ask for mailbox details before showing the document.",
        ],
        "table": [
            ("Delivered as", "Inline QR image in the message body"),
            ("Expires (lure wording)", "48 hours"),
        ],
        "explain": "QR destination for the <b>e-signature inline QR</b> sample.",
        "marker": "Q1 Executive Compensation Agreement",
    },
]

REFRESH_HOPS: list[dict] = [
    {
        "route": "go/viewer/",
        "target": "document-viewer/",
        "heading": "Opening the document viewer",
        "explain": "This is an HTML <b>meta refresh</b> hop, not a server redirect. GitHub Pages "
        "cannot send HTTP 302 responses. Browsers and link detonation follow the refresh to the "
        "viewer page; the visible link below does the same thing by hand.",
        "marker": "Opening the document viewer",
    },
]


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
        "<span>Fabricated training page for email security demos. Static and inert: "
        "nothing on this page collects, stores or submits data.</span></div>\n"
    )


def footer(route: str) -> str:
    return (
        "<p class=\"foot\">Demo route <span class=\"route\">/"
        f"{html.escape(route)}</span>. All names, companies and figures are fictional.</p>\n"
    )


def render_page(page: dict) -> str:
    parts = [head(page["heading"]), "<body>\n", banner(), "<main class=\"wrap\">\n<div class=\"card\">\n"]
    parts.append(
        f"<div class=\"card-head\"><p class=\"kicker\">{page['kicker']}</p>"
        f"<h1>{page['heading']}</h1></div>\n<div class=\"card-body\">\n"
    )
    if page.get("doc"):
        name, meta = page["doc"]
        parts.append(f"<div class=\"doc\">{DOC_ICON}<div><strong>{name}</strong><span>{meta}</span></div></div>\n")
    for paragraph in page.get("paragraphs", []):
        parts.append(f"<p>{paragraph}</p>\n")
    if page.get("table"):
        rows = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in page["table"])
        parts.append(f"<table>{rows}</table>\n")
    parts.append(f"<div class=\"explain\">{page['explain']}</div>\n")
    parts.append("</div>\n</div>\n")
    parts.append(footer(page["route"]))
    parts.append("</main>\n</body>\n</html>\n")
    return "".join(parts)


def render_hop(hop: dict) -> str:
    depth = hop["route"].strip("/").count("/") + 1
    target = "../" * depth + hop["target"]
    refresh = f"<meta http-equiv=\"refresh\" content=\"0; url={target}\">\n"
    return (
        head(hop["heading"], refresh)
        + "<body>\n"
        + banner()
        + "<main class=\"wrap\">\n<div class=\"card\">\n"
        + f"<div class=\"card-head\"><p class=\"kicker\">Link hop</p><h1>{hop['heading']}</h1></div>\n"
        + "<div class=\"card-body\">\n"
        + f"<p>If nothing happens, <a href=\"{target}\">continue to the document viewer</a>.</p>\n"
        + f"<div class=\"explain\">{hop['explain']}</div>\n"
        + "</div>\n</div>\n"
        + footer(hop["route"])
        + "</main>\n</body>\n</html>\n"
    )


def render_index() -> str:
    items = "".join(
        f"<tr><th><a href=\"{p['route']}\">{p['heading']}</a></th><td>/{p['route']}</td></tr>"
        for p in PAGES
    )
    items += "".join(
        f"<tr><th><a href=\"{h['route']}\">{h['heading']} (meta refresh)</a></th><td>/{h['route']}</td></tr>"
        for h in REFRESH_HOPS
    )
    return (
        head("Index")
        + "<body>\n"
        + banner()
        + "<main class=\"wrap\">\n<div class=\"card\">\n"
        + "<div class=\"card-head\"><p class=\"kicker\">Index</p><h1>Demo landing pages</h1></div>\n"
        + "<div class=\"card-body\">\n"
        + "<p>Inert end pages for synthetic phishing samples used in email security demos. Every "
        "page is fabricated and static.</p>\n"
        + f"<table>{items}</table>\n"
        + "</div>\n</div>\n"
        + footer("")
        + "</main>\n</body>\n</html>\n"
    )


def render_404() -> str:
    return (
        head("Not found")
        + "<body>\n"
        + banner()
        + "<main class=\"wrap\">\n<div class=\"card\">\n"
        + "<div class=\"card-head\"><p class=\"kicker\">Not found</p><h1>No demo page at this path</h1></div>\n"
        + "<div class=\"card-body\"><p>This path is not part of the demo site.</p></div>\n"
        + "</div>\n</main>\n</body>\n</html>\n"
    )


def main() -> int:
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
        routes.append({"path": page["route"], "kind": "page", "marker": page["marker"]})
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
