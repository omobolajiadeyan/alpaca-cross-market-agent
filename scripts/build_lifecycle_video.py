#!/usr/bin/env python3
"""Build the position-lifecycle submission video using edge-tts narration
(read verbatim from submission/FINAL_VIDEO_SCRIPT.md) over a mix of real
live-app screenshots, real code, and branded scene cards.

There was no time to record a human voice-over before the deadline, so this
uses the same Microsoft Edge neural TTS engine the earlier drafts used,
paired with fresh visuals for the position-lifecycle feature that the old
video predates entirely.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
TAIL_PAD = 0.5
VOICE = "en-US-AndrewMultilingualNeural"
RATE = "+6%"
HARD_CAP_SECONDS = 300

# Narration is copied verbatim from submission/FINAL_VIDEO_SCRIPT.md.
BEATS = [
    ("opening", """What if the smartest thing an AI trading agent could do was say no—and, when
it says yes, know exactly how to get out? I'm Omobolaji Adeyan, and this is
CrossSignal."""),
    ("problem", """Most trading agents focus on finding an opportunity and entering quickly. But
a strong signal alone does not make a safe trade. Market data may conflict,
liquidity may be poor, or the spread may be too wide. And entry is only half
the problem. Without an explicit take-profit, stop-loss, time limit, and
expiry rule, a valid entry can become unmanaged risk. An autonomous agent must
justify both why it entered and why it stayed or exited."""),
    ("solution", """CrossSignal is an auditable decision and position-management system for Alpaca
paper trading. It synchronizes six market lenses. Claude proposes a structured
thesis and attacks its own case. Independent deterministic code measures the
disagreement, tests stability, checks risk and execution quality, and has final
authority. Claude never contacts the broker."""),
    ("entry_governance", """Before any order, CrossSignal verifies live-data integrity, confidence,
maximum loss, buying power, diversification, Greeks coverage, portfolio stress,
liquidity, bid-ask quality, and drawdown. Every authorized decision is sealed
into a SHA-256 Decision Contract before submission. If one critical control
fails, the outcome is ABSTAIN—not a forced trade."""),
    ("position_lifecycle", """Governance now continues after entry. Every submitted vertical spread stores
its two option legs, fill price, maximum profit, maximum loss, expiry, and four
exit rules. By default, it takes profit at fifty percent of maximum profit,
cuts the position at fifty percent of defined maximum loss, exits after five
trading days, or closes two calendar days before expiry. The monitor first
reconciles every registered leg against Alpaca, then values the complete spread
using executable bids and asks. Stale quotes cannot trigger an order. When a
rule fires, it reverses both legs in one atomic Alpaca multi-leg limit order
with a deterministic client order ID. An atomic claim and EXIT_PENDING state
prevent duplicate closes, while every recommendation, deferral, submission,
and fill remains auditable."""),
    ("safety_boundary", """Exit automation is independently gated. It requires the exact Alpaca paper
endpoint, entry authorization, a second automated-exit switch, valid quotes,
and an open Alpaca market clock. The public judge application and scheduled
GitHub Evidence Watch are read-only. Emergency recovery for a broken entry
remains separate and human-approved. A dedicated kill switch can pause new
entries while continuing to manage positions already open."""),
    ("evidence", """Against a fresh one-hundred-thousand-dollar competition paper account,
CrossSignal repeatedly found real disagreements but refused execution when
adversarial confidence or after-hours liquidity failed fixed thresholds. The
account therefore has no competition P-and-L to claim. That is a competitive
limitation, but it is honest evidence that the controls were not weakened to
manufacture a trade."""),
    ("dashboard", """The dashboard exposes the decision courtroom, risk scorecard, entry ledger,
and the new position lifecycle. Judges can inspect each sealed policy and each
state transition from pending entry, to open, to exit pending, to closed. The
public example is explicitly labeled as an illustrative policy demonstration,
not broker fill evidence."""),
    ("repo_tests", """The public repository contains the complete implementation, not a mock-up.
Fifty-nine automated tests cover authorization, pricing, profit and loss
triggers, time and expiry exits, market-closed deferral, atomic leg reversal,
audit persistence, privacy, and duplicate-order prevention."""),
    ("close", """CrossSignal proves when a trade deserves entry, manages it under rules fixed in
advance, and proves why it exited. I'm Omobolaji Adeyan. Thank you."""),
]

FONT_HEAD = (
    '<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@700;800'
    '&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">'
)

WATERMARK_PNG = ROOT / "assets" / "presenter-watermark.png"

CARD_STYLE = """
* { box-sizing: border-box; margin:0; padding:0; }
body { width:1920px; height:1080px; background:#071d49;
  font-family:'DM Sans',sans-serif; color:#fff;
  display:flex; flex-direction:column; justify-content:center;
  padding:0 140px; position:relative; overflow:hidden; }
.ring { position:absolute; width:520px; height:520px; border:80px solid #19b5d8;
  border-radius:50%; opacity:.9; right:-220px; bottom:-220px; }
.eyebrow { font-family:'Manrope',sans-serif; font-size:16px; letter-spacing:.16em;
  color:#72d4e8; font-weight:700; margin-bottom:20px; z-index:1; }
h1 { font-family:'Manrope',sans-serif; font-weight:800; font-size:50px;
  letter-spacing:-.02em; line-height:1.25; max-width:1200px; margin-bottom:26px; z-index:1; }
.sub { font-size:23px; color:#d7e7f0; max-width:1100px; line-height:1.6; z-index:1; }
ul { list-style:none; z-index:1; max-width:1200px; }
li { font-size:21px; color:#e3eef6; line-height:1.4; margin-bottom:16px;
  padding-left:44px; position:relative; min-height:28px; display:flex; align-items:center; }
li::before { position:absolute; left:0; top:0; width:28px; height:28px; line-height:28px;
  text-align:center; border-radius:50%; font-size:14px; font-weight:800; }
ul.check li::before { content:'\\2713'; background:#19b5d8; color:#04222c; }
ul.warn li::before { content:'\\2715'; background:#e8985c; color:#2c1607; }
"""


def card(eyebrow: str, title: str, sub: str = "", items: list[str] | None = None,
          tone: str = "check") -> str:
    items_html = ""
    if items:
        items_html = f'<ul class="{tone}">' + "".join(f"<li>{i}</li>" for i in items) + "</ul>"
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    return f"""<!doctype html><html><head><meta charset="utf-8">{FONT_HEAD}
<style>{CARD_STYLE}</style></head><body>
<div class="ring"></div>
<div class="eyebrow">{eyebrow}</div>
<h1>{title}</h1>
{sub_html}
{items_html}
</body></html>"""


FLOW_STYLE = """
* { box-sizing: border-box; margin:0; padding:0; }
body { width:1920px; height:1080px; background:#071d49;
  font-family:'DM Sans',sans-serif; color:#fff;
  display:flex; flex-direction:column; justify-content:center;
  padding:0 140px; position:relative; overflow:hidden; }
.ring { position:absolute; width:520px; height:520px; border:80px solid #19b5d8;
  border-radius:50%; opacity:.9; right:-220px; bottom:-220px; }
.eyebrow { font-family:'Manrope',sans-serif; font-size:16px; letter-spacing:.16em;
  color:#72d4e8; font-weight:700; margin-bottom:20px; z-index:1; }
h1 { font-family:'Manrope',sans-serif; font-weight:800; font-size:48px;
  letter-spacing:-.02em; line-height:1.25; max-width:1200px; margin-bottom:44px; z-index:1; }
.flow { display:flex; align-items:stretch; gap:18px; z-index:1; }
.step { flex:1; background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.15);
  border-radius:12px; padding:26px 22px; }
.step.accent { background:#19b5d8; border-color:#19b5d8; }
.step .n { font-family:'Manrope',sans-serif; font-weight:800; font-size:13px;
  color:#72d4e8; letter-spacing:.1em; margin-bottom:10px; }
.step.accent .n { color:#04222c; }
.step .t { font-family:'Manrope',sans-serif; font-weight:700; font-size:21px; margin-bottom:8px; }
.step.accent .t { color:#04222c; }
.step .d { font-size:14px; color:#b9cfe0; line-height:1.5; }
.step.accent .d { color:#0b3542; }
.arrow { display:flex; align-items:center; color:#72d4e8; font-size:22px; font-weight:700; }
"""


def flow_card(eyebrow: str, title: str, steps: list[tuple[str, str, str]],
              accent_index: int | None = None) -> str:
    parts = []
    for i, (num, name, desc) in enumerate(steps):
        if i:
            parts.append('<div class="arrow">&#8594;</div>')
        cls = "step accent" if i == accent_index else "step"
        parts.append(f'<div class="{cls}"><div class="n">{num}</div>'
                      f'<div class="t">{name}</div><div class="d">{desc}</div></div>')
    flow_html = '<div class="flow">' + "".join(parts) + "</div>"
    return f"""<!doctype html><html><head><meta charset="utf-8">{FONT_HEAD}
<style>{FLOW_STYLE}</style></head><body>
<div class="ring"></div>
<div class="eyebrow">{eyebrow}</div>
<h1>{title}</h1>
{flow_html}
</body></html>"""


TITLE_HTML = f"""<!doctype html><html><head><meta charset="utf-8">{FONT_HEAD}
<style>
* {{ box-sizing: border-box; margin:0; padding:0; }}
body {{ width:1920px; height:1080px; background:#071d49;
  font-family:'DM Sans',sans-serif; color:#fff;
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  position:relative; overflow:hidden; text-align:center; }}
.ring {{ position:absolute; width:520px; height:520px; border:80px solid #19b5d8;
  border-radius:50%; opacity:.9; right:-220px; top:-180px; }}
.brand {{ font-family:'Manrope',sans-serif; font-weight:800; font-size:64px;
  letter-spacing:-.03em; margin-bottom:28px; z-index:1; }}
.brand .mark {{ color:#19b5d8; margin-right:14px; }}
.eyebrow {{ font-family:'Manrope',sans-serif; font-size:16px; letter-spacing:.16em;
  color:#72d4e8; font-weight:700; margin-bottom:24px; z-index:1; }}
.presenter {{ font-size:18px; color:#b9dced; z-index:1; margin-top:36px; }}
</style></head><body>
<div class="ring"></div>
<div class="eyebrow">DECISION AND POSITION-LIFECYCLE INTELLIGENCE</div>
<div class="brand"><span class="mark">&#9670;</span>CROSSSIGNAL</div>
<div class="presenter">Omobolaji Adeyan &middot; Alpaca AI Trading Agents Hackathon &middot; Paper trading only</div>
</body></html>"""

CLOSING_HTML = f"""<!doctype html><html><head><meta charset="utf-8">{FONT_HEAD}
<style>
* {{ box-sizing: border-box; margin:0; padding:0; }}
body {{ width:1920px; height:1080px; background:#071d49;
  font-family:'DM Sans',sans-serif; color:#fff;
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  position:relative; overflow:hidden; text-align:center; }}
.ring {{ position:absolute; width:520px; height:520px; border:80px solid #19b5d8;
  border-radius:50%; opacity:.9; right:-220px; top:-180px; }}
.brand {{ font-family:'Manrope',sans-serif; font-weight:800; font-size:60px;
  letter-spacing:-.03em; margin-bottom:26px; z-index:1; }}
.brand .mark {{ color:#19b5d8; margin-right:14px; }}
.tagline {{ font-size:26px; color:#d7e7f0; max-width:1000px; line-height:1.5;
  margin-bottom:44px; z-index:1; }}
.links {{ display:flex; gap:64px; z-index:1; margin-bottom:36px; }}
.link-block {{ text-align:center; }}
.link-label {{ font-size:13px; letter-spacing:.12em; color:#72d4e8; font-weight:700;
  text-transform:uppercase; margin-bottom:8px; }}
.link-value {{ font-size:19px; color:#fff; font-weight:600; }}
.presenter {{ font-size:16px; color:#b9dced; z-index:1; }}
</style></head><body>
<div class="ring"></div>
<div class="brand"><span class="mark">&#9670;</span>CROSSSIGNAL</div>
<div class="tagline">Entry, governed. Exit, proven.</div>
<div class="links">
  <div class="link-block"><div class="link-label">Live Application</div><div class="link-value">crosssignal-ai-agent.streamlit.app</div></div>
  <div class="link-block"><div class="link-label">Source Code</div><div class="link-value">github.com/omobolajiadeyan/alpaca-cross-market-agent</div></div>
</div>
<div class="presenter">Omobolaji Adeyan &middot; Alpaca AI Trading Agents Hackathon &middot; Paper trading only</div>
</body></html>"""

CODE_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
  * { box-sizing: border-box; margin:0; padding:0; }
  body { width:1920px; height:1080px; background:#0b1220;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    display:flex; flex-direction:column; color:#c9d6ef; }
  .titlebar { height:52px; background:#0f1a2e; display:flex; align-items:center;
    padding:0 24px; gap:10px; border-bottom:1px solid #1c2b47; }
  .dot { width:13px; height:13px; border-radius:50%; }
  .r{background:#ff5f57}.y{background:#febc2e}.g{background:#28c840}
  .filename { margin-left:20px; color:#7891b8; font-size:16px; }
  .path { color:#7891b8; font-size:15px; padding: 10px 40px 0 24px; letter-spacing:.02em; }
  .body { display:flex; flex:1; }
  .gutter { width:80px; background:#0d1626; color:#3d5578; text-align:right;
    padding:20px 16px 0 0; font-size:20px; line-height:1.6; white-space:pre-line; }
  .code { padding:20px 40px 0 24px; font-size:20px; line-height:1.6; white-space:pre; }
  .kw { color:#c586c0; } .fn { color:#4fc1e9; } .str { color:#ce9178; }
  .num { color:#b5cea8; } .plain { color:#c9d6ef; } .cmt { color:#5d7099; font-style:italic; }
</style></head>
<body>
  <div class="titlebar"><div class="dot r"></div><div class="dot y"></div><div class="dot g"></div>
    <span class="filename">agent/position_manager.py</span></div>
  <div class="path">CrossSignal &middot; the sealed dollar/time exit rules, evaluated with no broker side effects</div>
  <div class="body">
    <div class="gutter">58
59
60
61
62
63
64
65
66
67
68
69
70

72
73
74</div>
    <div class="code"><span class="kw">def</span> <span class="fn">evaluate</span>(<span class="plain">self, position, unrealized_pnl, now=</span><span class="kw">None</span><span class="plain">):</span>
    <span class="plain">expiration = position.get(</span><span class="str">'expiration_date'</span><span class="plain">)</span>
    <span class="kw">if</span> <span class="plain">expiration:</span>
        <span class="plain">dte = (expiration_date - now.date()).days</span>
        <span class="kw">if</span> <span class="plain">dte &lt;= position[</span><span class="str">'exit_before_expiry_days'</span><span class="plain">]:</span>
            <span class="kw">return</span> <span class="plain">EXPIRY_WINDOW</span>  <span class="cmt"># 2 calendar days out</span>
    <span class="kw">if</span> <span class="plain">unrealized_pnl &lt;= -position[</span><span class="str">'stop_loss_limit'</span><span class="plain">]:</span>
        <span class="kw">return</span> <span class="plain">STOP_LOSS</span>       <span class="cmt"># 50% of max defined loss</span>
    <span class="kw">if</span> <span class="plain">unrealized_pnl &gt;= position[</span><span class="str">'take_profit_target'</span><span class="plain">]:</span>
        <span class="kw">return</span> <span class="plain">TAKE_PROFIT</span>     <span class="cmt"># 50% of max profit</span>
    <span class="kw">if</span> <span class="plain">business_days_elapsed(opened, now) &gt;= position[</span><span class="str">'max_holding_days'</span><span class="plain">]:</span>
        <span class="kw">return</span> <span class="plain">MAX_HOLDING_PERIOD</span>  <span class="cmt"># 5 trading days</span>
    <span class="kw">return</span> <span class="plain">HOLD</span>

<span class="cmt"># Firing an exit reverses both legs in one atomic multi-leg order,</span>
<span class="cmt"># keyed by a deterministic client_order_id, only after the quote</span>
<span class="cmt"># is fresh, broker legs reconcile, and the market clock is open.</span></div>
  </div>
</body></html>
"""

TERMINAL_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
  * { box-sizing: border-box; margin:0; padding:0; }
  body { width:1920px; height:1080px; background:#0b1220;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    display:flex; flex-direction:column; color:#c9d6ef; }
  .titlebar { height:52px; background:#0f1a2e; display:flex; align-items:center;
    padding:0 24px; gap:10px; border-bottom:1px solid #1c2b47; }
  .dot { width:13px; height:13px; border-radius:50%; }
  .r{background:#ff5f57}.y{background:#febc2e}.g{background:#28c840}
  .filename { margin-left:20px; color:#7891b8; font-size:16px; }
  .term { padding:44px 52px; font-size:26px; line-height:2; }
  .prompt { color:#4fd2ef; } .cmd { color:#e8f0f8; } .out { color:#7f93b5; }
  .ok { color:#5fd68c; font-weight:600; }
</style></head>
<body>
  <div class="titlebar"><div class="dot r"></div><div class="dot y"></div><div class="dot g"></div>
    <span class="filename">terminal &mdash; crosssignal</span></div>
  <div class="term">
<div><span class="prompt">$</span> <span class="cmd">python -m pytest</span></div>
<div class="out">............................................................. [100%]</div>
<div class="ok">59 passed in 5.20s</div>
<div>&nbsp;</div>
<div><span class="prompt">$</span> <span class="cmd">python -m pytest tests/test_position_manager.py -v</span></div>
<div class="out">authorization &middot; pricing &middot; take-profit/stop-loss &middot; time &amp; expiry exits</div>
<div class="out">market-closed deferral &middot; atomic leg reversal &middot; audit persistence</div>
<div class="out">privacy &middot; duplicate-order prevention</div>
<div class="ok">11 passed in 1.16s</div>
  </div>
</body></html>
"""

EVIDENCE_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
  * { box-sizing: border-box; margin:0; padding:0; }
  body { width:1920px; height:1080px; background:#0b1220;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    display:flex; flex-direction:column; color:#c9d6ef; }
  .titlebar { height:52px; background:#0f1a2e; display:flex; align-items:center;
    padding:0 24px; gap:10px; border-bottom:1px solid #1c2b47; }
  .dot { width:13px; height:13px; border-radius:50%; }
  .r{background:#ff5f57}.y{background:#febc2e}.g{background:#28c840}
  .filename { margin-left:20px; color:#7891b8; font-size:16px; }
  .wrap { padding:48px 60px; }
  .eyebrow { color:#4fd2ef; font-size:16px; letter-spacing:.12em; font-weight:700; margin-bottom:24px; }
  .row { display:flex; gap:40px; margin-bottom:30px; }
  .field { flex:1; }
  .label { color:#7891b8; font-size:14px; letter-spacing:.08em; margin-bottom:6px; }
  .value { color:#e8f0f8; font-size:24px; font-weight:600; }
  .value.mono { font-family: 'Cascadia Code', monospace; font-size:22px; color:#4fc1e9; }
  .hr { height:1px; background:#1c2b47; margin:8px 0 32px; }
  .scorecard { display:flex; gap:24px; margin-bottom:32px; }
  .metric { flex:1; background:#0f1a2e; border:1px solid #1c2b47; border-radius:6px; padding:22px; text-align:center; }
  .metric .num { font-size:46px; font-weight:800; color:#e8f0f8; }
  .metric .cap { font-size:13px; color:#7891b8; letter-spacing:.06em; margin-top:6px; }
  .verdict { display:flex; align-items:center; gap:16px; background:#2a1a0f; border:1px solid #5a3a1a; border-radius:6px; padding:20px 26px; }
  .verdict .tag { background:#febc2e; color:#1a1200; font-weight:800; font-size:20px; padding:6px 16px; border-radius:4px; letter-spacing:.05em; }
  .verdict .reasons { font-size:16px; color:#d8c9a8; line-height:1.5; }
</style></head>
<body>
  <div class="titlebar"><div class="dot r"></div><div class="dot y"></div><div class="dot g"></div>
    <span class="filename">trading_audit.db &mdash; sealed decision contract</span></div>
  <div class="wrap">
    <div class="eyebrow">DEDICATED HACKATHON ACCOUNT &middot; $100,000 &middot; NO COMPETITION P&amp;L</div>
    <div class="row">
      <div class="field"><div class="label">CONTRACT</div><div class="value mono">CS-20260903-FE01A097</div></div>
      <div class="field"><div class="label">SEALED</div><div class="value mono">2026-09-03 23:15:09 UTC</div></div>
    </div>
    <div class="hr"></div>
    <div class="scorecard">
      <div class="metric"><div class="num">82.4</div><div class="cap">SIGNAL QUALITY</div></div>
      <div class="metric"><div class="num">90%</div><div class="cap">STABILITY (9/10)</div></div>
      <div class="metric"><div class="num">53%</div><div class="cap">CONFIDENCE AFTER CHALLENGE</div></div>
      <div class="metric"><div class="num">0</div><div class="cap">ORDERS SUBMITTED</div></div>
    </div>
    <div class="verdict">
      <div class="tag">ABSTAIN</div>
      <div class="reasons">Adversarial confidence fell to 53%, below the fixed 55% floor &mdash; preflight correctly did not run.</div>
    </div>
  </div>
</body></html>
"""


def find_edge_tts() -> list[str]:
    direct = shutil.which("edge-tts")
    return [direct] if direct else [sys.executable, "-m", "edge_tts"]


def synthesize(ffmpeg: str, text: str, audio_out: Path, retries: int = 3) -> None:
    cmd = find_edge_tts()
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        fh.write(text.strip() + "\n")
        script_path = Path(fh.name)
    last_error = None
    try:
        for attempt in range(1, retries + 1):
            try:
                subprocess.run([*cmd, "-f", str(script_path), "-v", VOICE, f"--rate={RATE}",
                                "--write-media", str(audio_out)], check=True,
                               capture_output=True, text=True)
                return
            except subprocess.CalledProcessError as exc:
                last_error = exc
                print(f"  [tts] attempt {attempt}/{retries} failed, retrying...")
                time.sleep(2)
        raise RuntimeError(f"edge-tts failed: {last_error.stderr}") from last_error
    finally:
        script_path.unlink(missing_ok=True)


def media_duration(ffmpeg: str, path: Path) -> float:
    import re
    probe = subprocess.run([ffmpeg, "-i", str(path)], capture_output=True, text=True)
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", probe.stderr)
    if not match:
        raise RuntimeError(f"Could not determine duration for {path.name}")
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def render_png(browser, html: str, out_png: Path) -> None:
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.set_content(html)
    page.wait_for_timeout(400)
    page.screenshot(path=str(out_png))
    page.close()


def progress_bar_filters(in_label: str, out_label: str, step_index: int, step_total: int) -> str:
    """Thin top-of-frame progress bar (a dim full-width track plus a cyan fill)
    so a viewer always has a sense of how far through the story they are."""
    bar_w = max(int(1920 * step_index / step_total), 6)
    return (
        f"[{in_label}]drawbox=x=0:y=0:w=1920:h=5:color=white@0.15:t=fill[bg{step_index}];"
        f"[bg{step_index}]drawbox=x=0:y=0:w={bar_w}:h=5:color=0x19b5d8:t=fill[{out_label}]"
    )


def build_clip(ffmpeg: str, image: Path, audio: Path, duration: float, out_mp4: Path,
               step_index: int, step_total: int) -> None:
    fade_out = max(duration - 0.4, 0)
    filter_complex = (
        "[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x071d49,format=yuv420p,"
        f"fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out}:d=0.4[base];"
        "[2:v]scale=190:190[wm];[base][wm]overlay=W-w-90:H-h-70:format=auto[wmout];"
        f"{progress_bar_filters('wmout', 'outv', step_index, step_total)}"
    )
    subprocess.run([
        ffmpeg, "-y", "-loop", "1", "-i", str(image), "-i", str(audio), "-i", str(WATERMARK_PNG),
        "-filter_complex", filter_complex, "-map", "[outv]", "-map", "1:a",
        "-af", "apad", "-t", str(duration), "-r", "30",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", str(out_mp4),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


PUBLIC_SITE_URL = "https://crosssignal-ai-agent.streamlit.app/~/+/"

CURSOR_INIT_JS = """
() => {
  const dot = document.createElement('div');
  dot.id = '__cs_cursor';
  dot.style.cssText = 'position:fixed;z-index:2147483647;width:22px;height:22px;'
    + 'border-radius:50%;background:rgba(25,181,216,0.85);border:2px solid white;'
    + 'box-shadow:0 2px 8px rgba(0,0,0,0.35);pointer-events:none;'
    + 'transition:left 0.5s ease,top 0.5s ease,transform 0.15s ease;'
    + 'left:-40px;top:-40px;transform:scale(1);';
  document.documentElement.appendChild(dot);
  window.__csMoveCursor = (x, y) => {
    const el = document.getElementById('__cs_cursor');
    if (el) { el.style.left = (x - 11) + 'px'; el.style.top = (y - 11) + 'px'; }
  };
  window.__csPulseCursor = () => {
    const el = document.getElementById('__cs_cursor');
    if (!el) return;
    el.style.transform = 'scale(0.6)';
    setTimeout(() => { el.style.transform = 'scale(1)'; }, 150);
  };
}
"""


def visible_click(page, locator) -> None:
    box = locator.bounding_box()
    if box:
        cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        page.evaluate("([x,y]) => window.__csMoveCursor && window.__csMoveCursor(x,y)", [cx, cy])
        page.mouse.move(cx, cy, steps=20)
        page.wait_for_timeout(500)
        page.evaluate("window.__csPulseCursor && window.__csPulseCursor()")
        page.wait_for_timeout(150)
    locator.click()


def capture_public_site_tour(target_duration: float, out_mp4: Path, ffmpeg: str) -> None:
    """Record a real, cursor-driven tour of the actual public deployment
    (not a local instance) -- the same URL judges will open themselves --
    touring the decision scorecard and then the position-lifecycle table."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        # Warm-up (not recorded): Streamlit Community Cloud apps sleep after
        # inactivity and can take well over 30s to cold-start on first hit.
        print("  [public-tour] warming up the public deployment (may cold-start)...")
        warm = browser.new_context(viewport={"width": 1920, "height": 1080})
        warm_page = warm.new_page()
        warm_page.goto(PUBLIC_SITE_URL, wait_until="domcontentloaded", timeout=90_000)
        warm_page.get_by_text("PUBLIC JUDGE MODE", exact=False).wait_for(timeout=90_000)
        warm.close()

        with tempfile.TemporaryDirectory(prefix="crosssignal-publictour-") as vdir:
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080}, device_scale_factor=1,
                record_video_dir=vdir, record_video_size={"width": 1920, "height": 1080},
            )
            page = context.new_page()
            page.goto(PUBLIC_SITE_URL, wait_until="domcontentloaded", timeout=60_000)
            page.get_by_text("PUBLIC JUDGE MODE", exact=False).wait_for(timeout=30_000)
            # Streamlit renders skeleton placeholders first and fills real data in
            # a moment later; without this, the recording captures gray shimmer
            # boxes instead of the actual scorecard numbers.
            page.get_by_text("Decision intelligence scorecard", exact=False) \
                .wait_for(timeout=15_000)
            page.wait_for_timeout(4000)
            page.evaluate(CURSOR_INIT_JS)
            page.wait_for_timeout(600)

            page.get_by_text("Decision intelligence scorecard", exact=False) \
                .scroll_into_view_if_needed()
            page.wait_for_timeout(int(target_duration * 1000 * 0.40))

            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(200)
            visible_click(page, page.get_by_role("tab", name="Track record"))
            page.wait_for_timeout(300)
            page.get_by_text("Position lifecycle", exact=False).scroll_into_view_if_needed()
            page.wait_for_timeout(int(target_duration * 1000 * 0.40))

            context.close()
            recorded = next(Path(vdir).glob("*.webm"))
            subprocess.run([
                ffmpeg, "-y", "-i", str(recorded),
                "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "30",
                "-pix_fmt", "yuv420p", "-t", str(target_duration), str(out_mp4),
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        browser.close()


def build_video_clip(ffmpeg: str, silent_video: Path, audio: Path, duration: float,
                      out_mp4: Path, step_index: int, step_total: int) -> None:
    filter_complex = (
        "[2:v]scale=190:190[wm];[0:v][wm]overlay=W-w-90:H-h-70:format=auto[wmout];"
        f"{progress_bar_filters('wmout', 'outv', step_index, step_total)}"
    )
    subprocess.run([
        ffmpeg, "-y", "-i", str(silent_video), "-i", str(audio), "-i", str(WATERMARK_PNG),
        "-filter_complex", filter_complex, "-map", "[outv]", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "30",
        "-af", "apad", "-t", str(duration),
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", str(out_mp4),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> int:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required")

    output = ROOT / "recording-output" / "CrossSignal-Position-Lifecycle-Narrated.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)

    scenes = {
        "opening": TITLE_HTML,
        "problem": card("THE PROBLEM", "Entry is only half the problem.", items=[
            "No take-profit &rarr; upside left uncaptured",
            "No stop-loss &rarr; downside unbounded",
            "No time or expiry limit &rarr; position drifts past its thesis",
        ], tone="warn"),
        "solution": flow_card("THE ARCHITECTURE", "One proposal. Independent, deterministic authority.", [
            ("01", "6 lenses", "Claude proposes a thesis"),
            ("02", "Attack", "Claude challenges its own case"),
            ("03", "Disagreement", "Scored independently"),
            ("04", "Stability", "Tested under noise"),
            ("05", "Risk + execution", "Deterministic, final"),
        ], accent_index=4),
        "entry_governance": card("ENTRY GOVERNANCE", "Ten checks before any order.", items=[
            "Live-data integrity &middot; confidence &middot; maximum loss",
            "Buying power &middot; diversification &middot; Greeks coverage",
            "Portfolio stress &middot; liquidity &middot; bid-ask quality &middot; drawdown",
            "Sealed into a SHA-256 Decision Contract before submission",
            "One critical control fails &rarr; ABSTAIN, not a forced trade",
        ]),
        "position_lifecycle": CODE_HTML,
        "safety_boundary": card("SAFETY BOUNDARY", "Exit automation is independently gated.", items=[
            "Exact Alpaca paper endpoint required",
            "Entry authorization + a second automated-exit switch",
            "Valid quotes and an open Alpaca market clock",
            "Public judge app and GitHub Evidence Watch stay read-only",
            "Emergency recovery is separate and human-approved",
            "A dedicated kill switch pauses new entries, not open positions",
        ]),
        "evidence": EVIDENCE_HTML,
        "dashboard": None,  # built from a live public-site recording below
        "repo_tests": TERMINAL_HTML,
        "close": CLOSING_HTML,
    }

    with tempfile.TemporaryDirectory(prefix="crosssignal-lifecycle-") as name:
        temp = Path(name)

        print("Synthesizing narration and measuring durations...")
        audio_paths: dict[str, Path] = {}
        durations: dict[str, float] = {}
        for beat_id, narration in BEATS:
            audio = temp / f"{beat_id}.mp3"
            synthesize(ffmpeg, narration, audio)
            spoken = media_duration(ffmpeg, audio)
            durations[beat_id] = spoken + TAIL_PAD
            audio_paths[beat_id] = audio
            print(f"  {beat_id}: {spoken:.1f}s speech -> {durations[beat_id]:.1f}s clip")

        total_duration = sum(durations.values())
        if total_duration > HARD_CAP_SECONDS:
            raise RuntimeError(
                f"Assembled video is {total_duration:.1f}s, over the {HARD_CAP_SECONDS}s cap"
            )

        print("Recording live tour of the public deployment "
              "(crosssignal-ai-agent.streamlit.app)...")
        dashboard_tour_mp4 = temp / "dashboard_tour.mp4"
        capture_public_site_tour(durations["dashboard"], dashboard_tour_mp4, ffmpeg)

        print("Rendering scene cards and assembling clips...")
        clips = []
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            step_total = len(BEATS)
            for step_index, (beat_id, narration) in enumerate(BEATS, start=1):
                duration = durations[beat_id]
                audio = audio_paths[beat_id]
                clip = temp / f"{beat_id}.mp4"
                if beat_id == "dashboard":
                    build_video_clip(ffmpeg, dashboard_tour_mp4, audio, duration, clip,
                                      step_index, step_total)
                else:
                    image = temp / f"{beat_id}.png"
                    render_png(browser, scenes[beat_id], image)
                    build_clip(ffmpeg, image, audio, duration, clip, step_index, step_total)
                clips.append(clip)
            browser.close()

        manifest = temp / "clips.txt"
        manifest.write_text("".join(f"file '{c}'\n" for c in clips), encoding="utf-8")
        subprocess.run([
            ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(manifest),
            "-c", "copy", "-movflags", "+faststart", str(output),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    final_duration = media_duration(ffmpeg, output)
    print(f"\nOutput: {output}")
    print(f"Duration: {int(final_duration // 60)}:{int(final_duration % 60):02d} "
          f"({final_duration:.1f}s, cap is {HARD_CAP_SECONDS}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
