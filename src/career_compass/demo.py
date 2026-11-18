"""Local, research-only demo page for the v1 engine.

Run:  uv run python -I -m career_compass.demo        then open http://127.0.0.1:8765

- Listens on 127.0.0.1 only. Not for deployment: release blockers are open (ROADMAP v1).
- Stores nothing: answers arrive in a POST body, are scored in memory and are not logged (ADR 0014). The request log
  prints only method and path. No cookies, no analytics, no external resources.
- Gender-blind (ADR 0015): the page asks no demographic question.
- Question wording comes from the OpenPsychometrics codebook in data/raw (research-only, ADR 0002). It is read as
  text at start-up and never copied into the repo. Without it, item IDs are shown.
- All user-facing copy here is DRAFT. Copy, family labels and help links need counsellor review (blockers 4 and 7).
"""

from __future__ import annotations

import html
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from . import engine as E

ROOT = Path(__file__).resolve().parents[2]
CODEBOOK = ROOT / "data" / "raw" / "openpsych_riasec_2018" / "RIASEC_data12Dec2018" / "codebook.txt"
HOST, PORT = "127.0.0.1", 8765
MAX_BODY = 20_000

TYPE_NAMES = {"R": "Realistic (hands-on, tools, outdoors)", "I": "Investigative (ideas, research, analysis)",
              "A": "Artistic (creating, designing, expressing)", "S": "Social (helping, teaching, caring)",
              "E": "Enterprising (leading, persuading, starting things)",
              "C": "Conventional (organising, data, detail)"}
SHORT = {"R": "Realistic", "I": "Investigative", "A": "Artistic", "S": "Social", "E": "Enterprising",
         "C": "Conventional"}
JOB_ZONE = {1: "little or no preparation", 2: "some preparation", 3: "medium preparation",
            4: "considerable preparation", 5: "extensive preparation"}  # O*NET Job Zone names
SCALE_LABELS = {1: "Dislike", 2: "", 3: "Neutral", 4: "", 5: "Enjoy"}  # codebook anchors

NOTICE_TEXT = {  # DRAFT copy (honesty rules, RESEARCH §9); counsellor review pending
    "careers_worth_exploring": "These are careers worth exploring, not a verdict. Try them out, read about them, "
                               "talk to people who do them.",
    "not_ability_or_satisfaction": "Interests are only one part of a good fit. This doesn't measure ability, and "
                                   "it can't promise you'd enjoy a job.",
    "us_occupational_data_onet": "Careers and their interest ratings come from US occupational data (O*NET 31.0); "
                                 "the ratings are estimates.",
    "human_help_links": "Want to talk it through? A school or career counsellor can help. "
                        "[Local help links pending counsellor review.]",
    "mixed_profile": "Your answers point in several directions, so the groups below are broad.",
    "low_interest_talk_to_someone": "Feeling uninterested in most things can be worth talking to someone about.",
    "top_type_thin_pool": "Few careers in this data centre on your strongest interest, so these groups also draw "
                          "on your other interests.",
}
TRY_OUTS = {  # DRAFT next steps for the explore arm (MODELS L3 "concrete next steps"); counsellor review pending
    "R": "Try something hands-on: a repair, building or gardening workshop, or helping on a practical project.",
    "I": "Try a puzzle you can dig into: a short online course, a science or coding club, or a small investigation.",
    "A": "Try making something: a writing, drawing, music, design or photography project, even a small one.",
    "S": "Try helping or teaching: volunteering, tutoring, mentoring or supporting someone with a task.",
    "E": "Try leading or persuading: organising an event, selling something, or running a small group project.",
    "C": "Try organising: keeping records for a club, planning a budget, or tidying up a messy process.",
}
ATTRIBUTION = ("This page includes information from the O*NET 31.0 Database by the U.S. Department of Labor, "
               "Employment and Training Administration (USDOL/ETA). Used under the CC BY 4.0 license "
               "(https://creativecommons.org/licenses/by/4.0/). O*NET is a trademark of USDOL/ETA. The Career Compass "
               "project has modified all or some of this information. USDOL/ETA has not approved, endorsed, or "
               "tested these modifications.")  # same text as README


def load_item_texts(path: Path = CODEBOOK) -> dict[str, str]:
    """Parse 'R1<TAB>text' lines from the codebook as plain text. Untrusted input: escaped at render time."""
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^([RIASEC][1-8])\t(.{1,200})$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def esc(s) -> str:
    return html.escape(str(s), quote=True)


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Career Compass (research demo)</title>
<style>
:root{{--bg:#fff;--fg:#1d1d1f;--muted:#5f6368;--card:#f5f5f7;--accent:#2b59c3;--warn:#8a5a00;--warnbg:#fff4dc}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151517;--fg:#ececf1;--muted:#a0a3aa;--card:#222226;
--accent:#8fb0ff;--warn:#ffd27a;--warnbg:#3a2e12}}}}
body{{background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif;max-width:760px;margin:0 auto;padding:16px}}
.banner{{background:var(--warnbg);color:var(--warn);padding:10px 12px;border-radius:8px;font-size:14px}}
.q{{background:var(--card);border-radius:8px;padding:10px 12px;margin:10px 0}}
.q p{{margin:0 0 6px}} .opts{{display:flex;flex-wrap:wrap;gap:6px}}
.opts label{{border:1px solid var(--muted);border-radius:6px;padding:4px 10px;cursor:pointer;font-size:14px}}
.fam{{background:var(--card);border-radius:8px;padding:12px;margin:12px 0}} .muted{{color:var(--muted);font-size:14px}}
button{{background:var(--accent);color:var(--bg);border:0;border-radius:8px;padding:10px 16px;font-size:16px;cursor:pointer}}
small{{color:var(--muted)}}
</style></head><body>
<p class="banner"><b>Research demo, not a product.</b> Runs only on this computer and stores nothing. Question
wording and scoring come from research-only data; copy and labels are drafts awaiting counsellor review.</p>
{body}
<hr><p><small>{attribution}</small></p></body></html>"""


def page(body: str) -> str:
    return PAGE.format(body=body, attribution=esc(ATTRIBUTION))


def _question(it: str, texts: dict[str, str]) -> str:
    opts = "".join(
        f'<label><input type="radio" name="{esc(it)}" value="{v}" required> {v}'
        f'{" " + esc(SCALE_LABELS[v]) if SCALE_LABELS[v] else ""}</label>'
        for v in range(1, 6))
    return f'<div class="q"><p>{esc(texts.get(it, it))}</p><div class="opts">{opts}</div></div>'


def render_form(form: list[str], texts: dict[str, str], hidden: dict[str, int] | None = None,
                refine: bool = False) -> str:
    hid = "".join(f'<input type="hidden" name="{esc(k)}" value="{int(v)}">' for k, v in (hidden or {}).items())
    qs = "".join(_question(it, texts) for it in form)
    jz = "".join(f'<label><input type="checkbox" name="jz" value="{z}" checked> {esc(JOB_ZONE[z])}</label> '
                 for z in (2, 3, 4, 5))
    intro = ("<h1>A few more questions</h1><p>These 6 questions sharpen your results.</p>" if refine else
             "<h1>What would you enjoy doing?</h1><p>For each activity, how much would you like doing it? "
             "There are no right answers, and it doesn't matter whether you know how.</p>")
    return page(f'<form method="post" action="/result">{intro}{hid}{qs}'
                f'<p class="muted">Show careers needing: {jz}</p><button type="submit">See careers to explore</button>'
                f"</form>")


def render_result(r: E.Result, answers: dict[str, int], can_refine: bool) -> str:
    notes = "".join(f"<p>{esc(NOTICE_TEXT[n])}</p>" for n in r.notices if n in NOTICE_TEXT
                    and n not in ("careers_worth_exploring",))
    if r.status == "lost" and r.arm is None:
        hid = "".join(f'<input type="hidden" name="{esc(k)}" value="{int(v)}">' for k, v in answers.items())
        arms = "".join(
            f'<form method="post" action="/result">{hid}<input type="hidden" name="arm" value="{a}">'
            f'<button type="submit">{esc(lbl)}</button></form><p></p>'
            for a, lbl in (("usual", "Study arm A: usual broad groups"), ("explore", "Study arm B: explore (draft)")))
        body = ("<h1>Your answers don't point one way yet</h1>"
                "<p>That's common, and it's useful to know. Rather than guess, the best next step is to try a few "
                "different things and talk them over with someone.</p>"
                "<p class='muted'>[Reviewer view. In the study (S3) one of these is assigned at random; the "
                "person never chooses or sees both. ADR 0028.]</p>" + arms)
        return page(body + notes)
    mine = ", ".join(esc(TYPE_NAMES[t]) for t in r.top_types)
    fams = []
    for f in r.families:
        ex = "".join(f"<li>{esc(e['title'])} <span class='muted'>({esc(JOB_ZONE[e['job_zone']])})</span></li>"
                     for e in f.examples)
        shared = (f"It shares your interest in {esc(' and '.join(SHORT[t] for t in f.shared_types))} work."
                  if f.shared_types else "It draws on the overall pattern of your answers.")
        work = " and ".join(SHORT[t] for t in f.family_types)
        try_out = (f"<p><b>Something to try:</b> {esc(TRY_OUTS[f.family_types[0]])}</p>"
                   if r.arm == "explore" else "")
        fams.append(f'<div class="fam"><h3>{esc(f.label)} <small>and related careers</small></h3>'
                    f"<p>This group is mostly {esc(work)} work. {shared}</p><ul>{ex}</ul>{try_out}</div>")
    refine = ""
    if can_refine:
        hid = "".join(f'<input type="hidden" name="{esc(k)}" value="{int(v)}">' for k, v in answers.items())
        refine = (f'<form method="post" action="/refine">{hid}<button type="submit">'
                  f"Answer 6 more questions to sharpen this</button></form>")
    if r.arm == "explore":
        return page(render_explore(r, mine, fams, notes))
    body = (f"<h1>Careers worth exploring</h1><p>{esc(NOTICE_TEXT['careers_worth_exploring'])}</p>"
            f"<p>Your strongest interests: {mine}.</p>"
            f"<p class='muted'>These groups are in no particular order.</p>{''.join(fams)}{notes}{refine}")
    return page(body)


def render_explore(r: E.Result, mine: str, fams: list[str], notes: str) -> str:
    """Draft new lost-user flow (S3 arm B, ADR 0028): explicit uncertainty, a wider spread of groups, a try-out per
    group and a plain summary the person can take to a counsellor. No numbers anywhere (ADR 0006)."""
    summary = "\n".join([
        "Career Compass summary (research draft)",
        "My answers were fairly even across interest areas, so nothing stood out clearly yet.",
        "Areas that came out slightly ahead: " + ", ".join(SHORT[t] for t in r.top_types) + ".",
        "Career groups I was shown to explore: " + "; ".join(f.label for f in r.families) + ".",
        "I'd like help choosing one or two things to try first.",
    ])
    return (f"<h1>Let's explore</h1><p>Your answers were fairly even, so we can't say yet which kind of work "
            f"suits you best. That's common, and it often changes once you try a few things. Below are "
            f"{len(r.families)} quite different groups, each with something small you could try.</p>"
            f"<p>Areas that came out slightly ahead: {mine}. Treat this as a starting guess.</p>"
            f"<p class='muted'>These groups are in no particular order.</p>{''.join(fams)}{notes}"
            f"<h2>To take to a counsellor</h2><p class='muted'>Nothing is saved. Copy or print this if it helps.</p>"
            f"<pre style='white-space:pre-wrap'>{esc(summary)}</pre>")


def parse_answers(body: bytes, bank: E.ItemBank) -> tuple[dict[str, int], list[int] | None]:
    q = parse_qs(body.decode("utf-8", errors="replace"), max_num_fields=100)
    ans = {}
    for k, v in q.items():
        if k in bank.items:
            x = int(v[0]) if v[0].isdigit() else 0
            if not 1 <= x <= 5:
                raise ValueError("answers must be 1-5")
            ans[k] = x
    jz = sorted({int(z) for z in q.get("jz", []) if z in {"2", "3", "4", "5"}}) or None
    return ans, jz


def parse_arm(body: bytes) -> str | None:
    arm = parse_qs(body.decode("utf-8", errors="replace"), max_num_fields=100).get("arm", [None])[0]
    if arm is not None and arm not in E.LOST_ARMS:
        raise ValueError("unknown arm")
    return arm


class App:
    def __init__(self):
        self.bank = E.ItemBank.from_e4()
        self.cat = E.Catalogue.load()
        self.texts = load_item_texts()
        self.form = E.build_fixed_form(self.bank)
        self.refine = E.refine_form(self.bank)

    def handle(self, method: str, path: str, body: bytes = b"") -> tuple[int, str]:
        if method == "GET" and path == "/":
            return 200, render_form(self.form, self.texts)
        if method == "POST" and path in ("/result", "/refine"):
            try:
                ans, jz = parse_answers(body, self.bank)
                if path == "/refine":
                    new = [it for it in self.refine if it not in ans]
                    return 200, render_form(new, self.texts, hidden=ans, refine=True)
                form = self.refine if all(it in ans for it in self.refine) else self.form
                r = E.assess(ans, self.bank, self.cat, job_zones=jz, form=form, lost_arm=parse_arm(body))
                return 200, render_result(r, ans, can_refine=form is self.form)
            except (ValueError, KeyError):
                return 400, page("<h1>Please answer every question</h1><p><a href='/'>Start again</a></p>")
        return 404, page("<h1>Not found</h1><p><a href='/'>Start</a></p>")


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, text):
            data = text.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._send(*app.handle("GET", self.path.split("?")[0]))

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                self._send(413, page("<h1>Request too large</h1>"))
                return
            self._send(*app.handle("POST", self.path.split("?")[0], self.rfile.read(n)))

        def log_message(self, fmt, *args):  # method + path only; never answers or client address
            print(f"{self.command} {self.path.split('?')[0]}", flush=True)

    return Handler


def main():
    app = App()
    if not app.texts:
        print("Codebook not found; showing item IDs instead of question text.")
    srv = ThreadingHTTPServer((HOST, PORT), make_handler(app))
    print(f"Career Compass research demo on http://{HOST}:{PORT}  (Ctrl+C to stop)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
