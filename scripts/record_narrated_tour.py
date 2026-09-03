#!/usr/bin/env python3
"""Record a real, cursor-driven screen capture of the CrossSignal public
judge replay (Playwright), timed to a narration track (Microsoft Edge
neural TTS), and mux them into the final submission video.

Fixes over the first pass:
  - A branded title card (with the presenter's name) covers Streamlit's
    cold-boot load time instead of showing a blank white page.
  - A warm-up navigation runs before the recorded pass to shrink that
    load time in the first place.
  - A visible animated cursor moves to and clicks each element, so tab
    switches and toggles read as an operator using the app, not as an
    instant unexplained cut.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
TAIL_PAD = 0.6      # seconds of dwell time after speech ends, before the next action
SETTLE = 0.3         # seconds given to the UI to render before the timer starts
CURSOR_MOVE_MS = 500  # cursor glide duration
TITLE_CARD_MIN = 3.5
TITLE_CARD_MAX = 12.0

CODE_SCENE_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
  * { box-sizing: border-box; margin:0; padding:0; }
  body {
    width:1920px; height:1080px; background:#0b1220;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    display:flex; flex-direction:column; color:#c9d6ef;
  }
  .titlebar { height:52px; background:#0f1a2e; display:flex; align-items:center;
    padding:0 24px; gap:10px; border-bottom:1px solid #1c2b47; }
  .dot { width:13px; height:13px; border-radius:50%; }
  .r{background:#ff5f57}.y{background:#febc2e}.g{background:#28c840}
  .filename { margin-left:20px; color:#7891b8; font-size:16px; }
  .body { display:flex; flex:1; }
  .gutter { width:80px; background:#0d1626; color:#3d5578; text-align:right;
    padding:28px 16px 0 0; font-size:22px; line-height:1.65; }
  .code { padding:28px 40px 0 24px; font-size:22px; line-height:1.65; white-space:pre; }
  .kw { color:#c586c0; } .fn { color:#4fc1e9; } .str { color:#ce9178; }
  .num { color:#b5cea8; } .plain { color:#c9d6ef; }
  .path { color:#7891b8; font-size:15px; padding: 6px 40px 0 24px; letter-spacing:.02em; }
</style></head>
<body>
  <div class="titlebar"><div class="dot r"></div><div class="dot y"></div><div class="dot g"></div>
    <span class="filename">agent/signal_protocol.py</span></div>
  <div class="path">CrossSignal &middot; the code that decides AUTHORIZED vs ABSTAIN</div>
  <div class="body">
    <div class="gutter">139
140
141
142
143
144
145
146
147
148
149
150
151
152
153
154
155</div>
    <div class="code"><span class="kw">def</span> <span class="fn">build</span>(<span class="plain">self, thesis, market_state, disagreement, stability, falsification, portfolio, risk</span>):
    <span class="plain">confidence_before = _number(thesis.get(</span><span class="str">'confidence_pre_falsification'</span><span class="plain">, ...))</span>
    <span class="plain">confidence_adjustment = _number(falsification.get(</span><span class="str">'confidence_adjustment'</span><span class="plain">))</span>
    <span class="plain">confidence_after = _clamp((confidence_before + confidence_adjustment) * </span><span class="num">100</span><span class="plain">, </span><span class="num">0</span><span class="plain">, </span><span class="num">100</span><span class="plain">) / </span><span class="num">100</span>
    <span class="plain">data_quality = market_state.get(</span><span class="str">'data_quality'</span><span class="plain">, {})</span>
    <span class="plain">reasons = []</span>
    <span class="kw">if not</span> <span class="plain">data_quality.get(</span><span class="str">'all_live'</span><span class="plain">, </span><span class="kw">False</span><span class="plain">):</span>
        <span class="plain">reasons.append(</span><span class="str">'required market data is not fully live'</span><span class="plain">)</span>
    <span class="kw">if</span> <span class="plain">disagreement.get(</span><span class="str">'score'</span><span class="plain">, </span><span class="num">0</span><span class="plain">) &lt; </span><span class="num">55</span><span class="plain">:</span>
        <span class="plain">reasons.append(</span><span class="str">'disagreement score below 55'</span><span class="plain">)</span>
    <span class="kw">if</span> <span class="plain">stability.get(</span><span class="str">'score'</span><span class="plain">, </span><span class="num">0</span><span class="plain">) &lt; .</span><span class="num">60</span><span class="plain">:</span>
        <span class="plain">reasons.append(</span><span class="str">'decision stability below 60%'</span><span class="plain">)</span>
    <span class="kw">if</span> <span class="plain">confidence_after &lt; MIN_SIGNAL_CONFIDENCE:</span>
        <span class="plain">reasons.append(</span><span class="fn">f</span><span class="str">'adjusted confidence below ...'</span><span class="plain">)</span>
    <span class="kw">if not</span> <span class="plain">risk.get(</span><span class="str">'passed'</span><span class="plain">):</span>
        <span class="plain">reasons.append(</span><span class="str">'deterministic risk assessment failed'</span><span class="plain">)</span></div>
  </div>
</body></html>
"""

PROBLEM_SCENE_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@700;800&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin:0; padding:0; }
  body { width:1920px; height:1080px; background:#071d49;
    font-family:'DM Sans',sans-serif; color:#fff;
    display:flex; flex-direction:column; justify-content:center;
    padding:0 140px; position:relative; overflow:hidden; }
  .ring { position:absolute; width:520px; height:520px; border:80px solid #19b5d8;
    border-radius:50%; opacity:.9; right:-220px; bottom:-220px; }
  .eyebrow { font-family:'Manrope',sans-serif; font-size:16px; letter-spacing:.16em;
    color:#72d4e8; font-weight:700; margin-bottom:20px; z-index:1; }
  h1 { font-family:'Manrope',sans-serif; font-weight:800; font-size:54px;
    letter-spacing:-.02em; line-height:1.25; max-width:1180px; margin-bottom:28px; z-index:1; }
  .sub { font-size:25px; color:#d7e7f0; max-width:1080px; line-height:1.65; z-index:1; }
  .sub b { color:#fff; }
</style></head>
<body>
  <div class="ring"></div>
  <div class="eyebrow">THE PROBLEM</div>
  <h1>A strong signal alone does not make a trade safe.</h1>
  <div class="sub">Most trading agents are built to find opportunities and execute quickly. But the market may be unstable, spreads may be too wide, liquidity may be insufficient, or different indicators may conflict &mdash; and a single model can overlook all of that and still place the trade. <b>That's a reliability problem: how does an autonomous agent prove a trade was justified before execution?</b></div>
</body></html>
"""

ARCHITECTURE_SCENE_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@700;800&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin:0; padding:0; }
  body { width:1920px; height:1080px; background:#071d49;
    font-family:'DM Sans',sans-serif; color:#fff;
    display:flex; flex-direction:column; justify-content:center;
    padding:0 140px; position:relative; overflow:hidden; }
  .ring { position:absolute; width:520px; height:520px; border:80px solid #19b5d8;
    border-radius:50%; opacity:.9; right:-220px; bottom:-220px; }
  .eyebrow { font-family:'Manrope',sans-serif; font-size:16px; letter-spacing:.16em;
    color:#72d4e8; font-weight:700; margin-bottom:20px; z-index:1; }
  h1 { font-family:'Manrope',sans-serif; font-weight:800; font-size:52px;
    letter-spacing:-.02em; line-height:1.25; max-width:1180px; margin-bottom:22px; z-index:1; }
  .sub { font-size:22px; color:#d7e7f0; max-width:1080px; line-height:1.6; margin-bottom:40px; z-index:1; }
  .flow { display:flex; gap:24px; z-index:1; }
  .step { flex:1; background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.15);
    border-radius:10px; padding:24px 26px; }
  .step .n { font-family:'Manrope',sans-serif; font-weight:800; font-size:14px;
    color:#19b5d8; letter-spacing:.1em; margin-bottom:10px; }
  .step .t { font-family:'Manrope',sans-serif; font-weight:700; font-size:20px; margin-bottom:8px; }
  .step .d { font-size:15px; color:#b9cfe0; line-height:1.5; }
</style></head>
<body>
  <div class="ring"></div>
  <div class="eyebrow">THE ARCHITECTURE</div>
  <h1>One proposal. Three independent, deterministic checks.</h1>
  <div class="sub">Claude proposes a structured cross-market thesis &mdash; but CrossSignal never trusts that proposal directly. It's verified by three separate deterministic components before a trade can ever be authorized.</div>
  <div class="flow">
    <div class="step"><div class="n">DISAGREEMENT ENGINE</div><div class="t">Is the opportunity strong enough?</div><div class="d">Synchronizes six market lenses &mdash; equity vol, credit, rates, realized vol, rate expectations, positioning &mdash; independent of Claude's framing.</div></div>
    <div class="step"><div class="n">STABILITY TESTER</div><div class="t">Do conditions support it?</div><div class="d">Perturbs the inputs ten times &mdash; a thesis that breaks under noise is marked unstable.</div></div>
    <div class="step"><div class="n">EXECUTION RISK GATE</div><div class="t">Can it execute safely?</div><div class="d">Checks liquidity, spread, margin, and loss caps against real Alpaca data.</div></div>
  </div>
</body></html>
"""

TERMINAL_SCENE_HTML = r"""<!doctype html>
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
  .term { padding:40px 48px; font-size:24px; line-height:1.85; }
  .prompt { color:#4fd2ef; } .cmd { color:#e8f0f8; } .out { color:#7f93b5; }
  .ok { color:#5fd68c; } .url { color:#4fc1e9; text-decoration:underline; }
  .cursorblink { display:inline-block; width:11px; height:24px; background:#4fd2ef;
    margin-left:2px; animation:blink 1s step-end infinite; vertical-align:middle; }
  @keyframes blink { 50% { opacity:0; } }
  .reveal { opacity:0; transition:opacity .3s ease; }
  .reveal.in { opacity:1; }
</style></head>
<body>
  <div class="titlebar"><div class="dot r"></div><div class="dot y"></div><div class="dot g"></div>
    <span class="filename">terminal &mdash; crosssignal</span></div>
  <div class="term">
<div><span class="prompt">$</span> <span class="cmd" id="cmd-text"></span></div>
<div>&nbsp;</div>
<div class="out reveal" id="line-1">  You can now view your Streamlit app in your browser.</div>
<div>&nbsp;</div>
<div class="out reveal" id="line-2">  Local URL: <span class="url">http://localhost:8501</span></div>
<div>&nbsp;</div>
<div class="ok reveal" id="line-3">&#10003; PUBLIC_DEMO_MODE=true &middot; ALLOW_PAPER_EXECUTION=false</div>
  </div>
  <script>
    function typeText(id, text, charDelay, onDone) {
      const el = document.getElementById(id);
      el.innerHTML = '<span class="cursorblink"></span>';
      const cursor = el.querySelector('.cursorblink');
      let i = 0;
      const iv = setInterval(() => {
        if (i >= text.length) { clearInterval(iv); cursor.remove(); if (onDone) onDone(); return; }
        cursor.insertAdjacentText('beforebegin', text[i]);
        i++;
      }, charDelay);
    }
    function show(id) { document.getElementById(id).classList.add('in'); }
    typeText('cmd-text', 'streamlit run app.py', 55, () => {
      setTimeout(() => show('line-1'), 300);
      setTimeout(() => show('line-2'), 600);
      setTimeout(() => show('line-3'), 950);
    });
  </script>
</body></html>
"""

EVIDENCE_SCENE_HTML = r"""<!doctype html>
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
  .wrap { padding:44px 56px; }
  .eyebrow { color:#4fd2ef; font-size:16px; letter-spacing:.12em; font-weight:700; margin-bottom:20px; }
  .row { display:flex; gap:40px; margin-bottom:28px; }
  .field { flex:1; }
  .label { color:#7891b8; font-size:14px; letter-spacing:.08em; margin-bottom:6px; }
  .value { color:#e8f0f8; font-size:26px; font-weight:600; }
  .value.mono { font-family: 'Cascadia Code', monospace; font-size:22px; color:#4fc1e9; }
  .hr { height:1px; background:#1c2b47; margin:8px 0 32px; }
  .scorecard { display:flex; gap:24px; margin-bottom:32px; }
  .metric { flex:1; background:#0f1a2e; border:1px solid #1c2b47; border-radius:6px; padding:20px; text-align:center; }
  .metric .num { font-size:44px; font-weight:800; color:#e8f0f8; }
  .metric .cap { font-size:13px; color:#7891b8; letter-spacing:.06em; margin-top:6px; }
  .metric.warn .num { color:#febc2e; }
  .verdict { display:flex; align-items:center; gap:16px; background:#2a1a0f; border:1px solid #5a3a1a; border-radius:6px; padding:18px 24px; }
  .verdict .tag { background:#febc2e; color:#1a1200; font-weight:800; font-size:20px; padding:6px 16px; border-radius:4px; letter-spacing:.05em; }
  .verdict .reasons { font-size:15px; color:#d8c9a8; line-height:1.5; }
  .hash { font-size:14px; color:#5d7099; margin-top:24px; word-break:break-all; }
  .reveal { opacity:0; transform:translateY(8px); transition:opacity .4s ease,transform .4s ease; }
  .reveal.in { opacity:1; transform:translateY(0); }
  .metric.pop { transition:transform .25s ease; }
  .metric.pop.bump { transform:scale(1.06); }
  .cursorblink { display:inline-block; width:10px; height:22px; background:#4fc1e9; margin-left:4px;
    animation:blink 1s step-end infinite; vertical-align:middle; }
  @keyframes blink { 50% { opacity:0; } }
</style></head>
<body>
  <div class="titlebar"><div class="dot r"></div><div class="dot y"></div><div class="dot g"></div>
    <span class="filename">trading_audit.db &mdash; sealed decision contract</span></div>
  <div class="wrap">
    <div class="eyebrow reveal" id="r-eyebrow">LIVE EVIDENCE &middot; DEDICATED HACKATHON ACCOUNT &middot; NOT A DEMO</div>
    <div class="row reveal" id="r-account">
      <div class="field"><div class="label">ALPACA ACCOUNT</div><div class="value mono">Dedicated hackathon account (ID withheld) &middot; $100,000 &middot; created 2026-09-01</div></div>
    </div>
    <div class="row reveal" id="r-contract">
      <div class="field"><div class="label">CONTRACT</div><div class="value mono">CS-20260901-4B6D4392</div></div>
      <div class="field"><div class="label">SEALED</div><div class="value mono">2026-09-01 15:42:53 UTC</div></div>
    </div>
    <div class="hr"></div>
    <div class="scorecard">
      <div class="metric pop" id="metric-signal"><div class="num" id="num-signal">0</div><div class="cap">SIGNAL QUALITY</div></div>
      <div class="metric pop" id="metric-stability"><div class="num" id="num-stability">0</div><div class="cap">DECISION STABILITY</div></div>
      <div class="metric pop warn" id="metric-execution"><div class="num" id="num-execution">0</div><div class="cap">EXECUTION QUALITY</div></div>
      <div class="metric pop reveal" id="metric-outcome"><div class="num">&mdash;</div><div class="cap">OUTCOME (PENDING)</div></div>
    </div>
    <div class="verdict reveal" id="r-verdict">
      <div class="tag">ABSTAIN</div>
      <div class="reasons" id="reasons-text"></div>
    </div>
    <div class="hash reveal" id="r-hash">SHA-256 4b6d43922b73cc9c0bf27da835cafc6811cdc10c6f5bfa5808c75e33df71a5b3</div>
  </div>
  <script>
    function show(id) { document.getElementById(id).classList.add('in'); }
    function countUp(numId, metricId, target, duration) {
      const el = document.getElementById(numId);
      const metric = document.getElementById(metricId);
      const start = performance.now();
      function frame(now) {
        const p = Math.min((now - start) / duration, 1);
        el.textContent = Math.round(p * target);
        if (p < 1) requestAnimationFrame(frame);
        else { metric.classList.add('bump'); setTimeout(() => metric.classList.remove('bump'), 250); }
      }
      requestAnimationFrame(frame);
    }
    function typeText(id, text, charDelay) {
      const el = document.getElementById(id);
      el.innerHTML = '<span class="cursorblink"></span>';
      let i = 0;
      const cursor = el.querySelector('.cursorblink');
      const iv = setInterval(() => {
        if (i >= text.length) { clearInterval(iv); cursor.remove(); return; }
        cursor.insertAdjacentText('beforebegin', text[i]);
        i++;
      }, charDelay);
    }
    show('r-eyebrow');
    setTimeout(() => show('r-account'), 250);
    setTimeout(() => show('r-contract'), 550);
    setTimeout(() => countUp('num-signal', 'metric-signal', 82, 650), 950);
    setTimeout(() => countUp('num-stability', 'metric-stability', 100, 650), 1500);
    setTimeout(() => countUp('num-execution', 'metric-execution', 67, 650), 2050);
    setTimeout(() => show('metric-outcome'), 2700);
    setTimeout(() => show('r-verdict'), 3000);
    setTimeout(() => typeText('reasons-text',
      'required market data not fully live · adjusted confidence below 55% · deterministic risk assessment failed',
      18), 3100);
    setTimeout(() => show('r-hash'), 5900);
  </script>
</body></html>
"""

CLOSING_SCENE_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@700;800&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin:0; padding:0; }
  body { width:1920px; height:1080px; background:#071d49;
    font-family:'DM Sans',sans-serif; color:#fff;
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    position:relative; overflow:hidden; }
  .ring { position:absolute; width:520px; height:520px; border:80px solid #19b5d8;
    border-radius:50%; opacity:.9; right:-220px; top:-180px; }
  .brand { font-family:'Manrope',sans-serif; font-weight:800; font-size:64px;
    letter-spacing:-.03em; margin-bottom:28px; z-index:1; }
  .brand .mark { color:#19b5d8; margin-right:14px; }
  .tagline { font-size:28px; color:#d7e7f0; max-width:900px; text-align:center;
    line-height:1.5; margin-bottom:56px; z-index:1; }
  .links { display:flex; gap:64px; z-index:1; margin-bottom:40px; }
  .link-block { text-align:center; }
  .link-label { font-size:13px; letter-spacing:.12em; color:#72d4e8; font-weight:700;
    text-transform:uppercase; margin-bottom:8px; }
  .link-value { font-size:20px; color:#fff; font-weight:600; }
  .presenter { font-size:16px; color:#b9dced; z-index:1; }
</style></head>
<body>
  <div class="ring"></div>
  <div class="brand"><span class="mark">&#9670;</span>CROSSSIGNAL</div>
  <div class="tagline">Markets disagree constantly. The hard part was never finding the<br>disagreement &mdash; it's knowing when not to act on it.</div>
  <div class="links">
    <div class="link-block"><div class="link-label">Live Application</div><div class="link-value">crosssignal-ai-agent.streamlit.app</div></div>
    <div class="link-block"><div class="link-label">Source Code</div><div class="link-value">github.com/omobolajiadeyan/alpaca-cross-market-agent</div></div>
  </div>
  <div class="presenter">Presented by Omobolaji Adeyan &middot; Alpaca AI Trading Agents Hackathon &middot; Paper trading only</div>
</body></html>
"""

SECRET_ENV_NAMES = (
    "APCA_API_KEY_ID", "APCA_API_SECRET_KEY", "ANTHROPIC_API_KEY",
    "ALPACA_API_KEY", "ALPACA_API_KEY_ID", "ALPACA_SECRET_KEY",
    "ALPACA_API_SECRET_KEY",
)

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

TITLE_BEAT = ("open_title", "What if the smartest thing an AI trading agent "
              "could do was say no? I'm Omobolaji Adeyan, and this is "
              "CrossSignal.")
PROBLEM_BEAT = ("problem_scene", "Most trading agents are designed to find "
                "opportunities and execute quickly. But a strong signal "
                "alone does not make a trade safe. The market may be "
                "unstable, spreads may be too wide, liquidity may be "
                "insufficient, or different indicators may conflict. A "
                "single model can overlook that and still place the "
                "trade. That's a reliability problem: how does an "
                "autonomous agent prove a trade was justified before it "
                "acts?")
ARCHITECTURE_BEAT = ("architecture_scene", "CrossSignal is a "
                      "decision-control system for Alpaca trading. "
                      "Instead of letting one signal trigger a trade, "
                      "Claude proposes a structured thesis from six "
                      "synchronized market lenses — equity volatility, "
                      "credit, rates, and more — and three independent, "
                      "deterministic checks verify it before anything "
                      "moves. A disagreement engine "
                      "scores whether the opportunity itself is real. A "
                      "stability tester checks whether that signal "
                      "survives realistic noise. An execution risk gate "
                      "checks whether the trade can actually be filled "
                      "safely. Each produces its own score and evidence — "
                      "not one blended confidence number.")
CODE_BEAT = ("code_scene", "CrossSignal then applies deterministic "
             "authorization rules to those three scores. A trade is "
             "authorized only when every required threshold is met. If "
             "one critical check fails — or the evidence is incomplete — "
             "the system abstains automatically. Uncertainty becomes an "
             "explicit, logged decision instead of an accidental trade. "
             "That logic lives right here, in code like this, not in a "
             "prompt.")
TERMINAL_BEAT = ("terminal_scene", "One command runs it locally, in public "
                  "demo mode, so you can verify every claim yourself.")
EVIDENCE_BEAT = ("evidence_scene", "CrossSignal runs on Alpaca's official "
                  "MCP server for market data, account state, and paper "
                  "execution. And this isn't a demo number — against a "
                  "fresh, dedicated hundred-thousand-dollar Alpaca "
                  "account, CrossSignal sealed this exact contract, "
                  "hashed with SHA-256 before the outcome was known. The "
                  "disagreement engine scored this real, the stability "
                  "test held across ten perturbations, but the execution "
                  "risk gate found the evidence incomplete. Verdict: "
                  "abstain.")

BEATS = [
    ("open_live", "Now the same governed process, live and "
     "credential-free — nothing here you have to take on faith."),
    ("scorecard", "This sanitized replay runs the exact same three "
     "checks — the disagreement engine, the stability tester, and the "
     "execution risk gate — scored independently on a different real "
     "case, not blended into one confidence number."),
    ("courtroom", "Every step is reconstructed and sealed before the "
     "outcome is known — the allegation, the cross-examination, the "
     "judgment — hashed with SHA-256 so it can't be edited after the "
     "fact."),
    ("abstention", "Here, the disagreement engine found a real signal, "
     "and it held up under the stability test. But the execution risk "
     "gate needed ten units of option liquidity, and only four existed. "
     "A conventional agent might still trade on the strength of the "
     "signal alone. Watch CrossSignal instead: no order sent, nothing to "
     "recover from. Refusing was correct, not a malfunction."),
    ("authorized_case", "Switch the case, and here's what full clearance "
     "looks like: the disagreement engine, the stability tester, and the "
     "execution risk gate all clear their thresholds. CrossSignal "
     "authorizes the trade and seals the scores, the rule results, and "
     "the evidence into a reproducible decision contract — a receipt "
     "any judge can verify independently, without trusting me at all."),
    ("cloud_evidence", "CrossSignal also runs unattended in GitHub "
     "Actions. This connected run sealed its own contract — same three "
     "checks, still correctly abstained, every step green, no laptop "
     "required."),
    ("repo_proof", "None of this is a mock-up. The public repository "
     "holds the complete implementation — forty-three automated tests, "
     "the same checks you've been watching, open for anyone to read."),
    ("close", "CrossSignal isn't another strategy for predicting whether "
     "prices rise or fall. It's a verification layer that sits between a "
     "proposal and execution — and Claude never touches the broker "
     "directly. Its only job: decide whether there's enough reliable "
     "evidence to act. I'm Omobolaji Adeyan. Thank you."),
]

GITHUB_EVIDENCE_PNG = ROOT / "recording-output" / "assets" / "github_evidence_watch.png"
GITHUB_REPO_PNG = ROOT / "recording-output" / "assets" / "github_repo_tree.png"

# Drop a real recording here named "<beat_id><ext>" (mp3/wav/m4a/mp4 all
# work) to replace that beat's synthesized narration -- e.g.
# recording-output/assets/voice_overrides/open_title.mp3 to record the
# opening in your own voice instead of edge-tts.
REAL_VOICE_DIR = ROOT / "recording-output" / "assets" / "voice_overrides"

# Natural speech runs well below edge-tts's -8% rate; a full set of real
# recordings comes in far longer than the synthesized draft they replace.
# Speed them up (pitch-preserved via ffmpeg's atempo) to fit the hackathon's
# 5:00 hard cap rather than silently blowing past it.
REAL_VOICE_SPEEDUP = 1.32


def find_real_voice_override(beat_id: str) -> Path | None:
    if not REAL_VOICE_DIR.is_dir():
        return None
    for ext in (".mp3", ".wav", ".m4a", ".mp4", ".aac", ".ogg"):
        candidate = REAL_VOICE_DIR / f"{beat_id}{ext}"
        if candidate.exists():
            return candidate
    return None

CAPTURE_URL = "http://127.0.0.1:8501"


def find_ffmpeg() -> str:
    direct = shutil.which("ffmpeg")
    if direct:
        return direct
    candidates = sorted((Path.home() / "AppData/Local/ms-playwright").glob("ffmpeg*/ffmpeg-*.exe"))
    if candidates:
        return str(candidates[-1])
    raise RuntimeError("ffmpeg is required")


def media_duration(ffmpeg: str, path: Path) -> float:
    probe = subprocess.run([ffmpeg, "-i", str(path)], capture_output=True, text=True)
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", probe.stderr)
    if not match:
        raise RuntimeError(f"Could not determine duration for {path.name}")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def synthesize(script: Path, audio: Path, voice: str, rate_pct: str, retries: int = 3) -> None:
    """edge-tts's free service occasionally drops a connection mid-stream
    (NoAudioReceived) with no code-level cause; a bare retry clears it."""
    edge_tts = shutil.which("edge-tts")
    cmd = [edge_tts] if edge_tts else [sys.executable, "-m", "edge_tts"]
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            subprocess.run([*cmd, "-f", str(script), "-v", voice, f"--rate={rate_pct}",
                            "--write-media", str(audio)], check=True,
                           capture_output=True, text=True)
            return
        except subprocess.CalledProcessError as exc:
            last_error = exc
            print(f"  [tts] attempt {attempt}/{retries} failed for {audio.name}, retrying...")
            time.sleep(2)
    raise RuntimeError(f"edge-tts failed {retries}x for {audio.name}: {last_error.stderr}") from last_error


def available_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def wait_for_app(url: str, timeout: int = 45) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return
        except (URLError, TimeoutError, OSError):
            time.sleep(0.5)
    raise RuntimeError(f"Streamlit did not become ready at {url}")


def recording_environment() -> dict[str, str]:
    env = dict(os.environ)
    for name in SECRET_ENV_NAMES:
        env.pop(name, None)
    env.update({"PUBLIC_DEMO_MODE": "true", "ALLOW_PAPER_EXECUTION": "false"})
    return env


def build_title_card(ffmpeg: str, out_path: Path, duration: float) -> None:
    with tempfile.TemporaryDirectory(prefix="crosssignal-fonts-") as fonts_dir:
        fonts_dir = Path(fonts_dir)
        bold = fonts_dir / "arialbd.ttf"
        regular = fonts_dir / "arial.ttf"
        shutil.copy(r"C:\Windows\Fonts\arialbd.ttf", bold)
        shutil.copy(r"C:\Windows\Fonts\arial.ttf", regular)
        fade_out_start = max(duration - 0.4, 0)
        vf = (
            f"drawtext=fontfile=arialbd.ttf:text='CROSSSIGNAL':fontcolor=white:"
            f"fontsize=130:x=(w-text_w)/2:y=360,"
            f"drawtext=fontfile=arial.ttf:text='Presented by Omobolaji Adeyan':"
            f"fontcolor=0x72d4e8:fontsize=50:x=(w-text_w)/2:y=540,"
            f"drawtext=fontfile=arial.ttf:text='Alpaca AI Trading Agents Hackathon':"
            f"fontcolor=0xb9dced:fontsize=30:x=(w-text_w)/2:y=615,"
            f"fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out_start}:d=0.4"
        )
        subprocess.run([
            ffmpeg, "-y", "-f", "lavfi", "-i", f"color=c=0x071d49:s=1920x1080:d={duration}",
            "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
            "-t", str(duration), str(out_path),
        ], check=True, cwd=fonts_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def render_scene_png(browser, html: str, out_png: Path) -> None:
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.set_content(html)
    page.screenshot(path=str(out_png))
    page.close()


def _srt_timestamp(t: float) -> str:
    h, rem = divmod(max(t, 0), 3600)
    m, s = divmod(rem, 60)
    ms = int(round((s - int(s)) * 1000))
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{ms:03d}"


def _split_into_caption_chunks(text: str, max_chars: int = 84) -> list[str]:
    """Break narration into caption-sized pieces on sentence boundaries, so
    a 25-second beat doesn't sit on screen as one giant paragraph."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    final: list[str] = []
    for chunk in chunks:
        while len(chunk) > max_chars:
            cut = chunk.rfind(" ", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            final.append(chunk[:cut].strip())
            chunk = chunk[cut:].strip()
        if chunk:
            final.append(chunk)
    return final or [text.strip()]


def build_captions_srt(segments: list[tuple[str, float]], out_srt: Path) -> None:
    """segments: [(narration_text, on_screen_duration), ...] in the exact
    same order the corresponding clips are concatenated in, so each beat's
    total caption time lines up with what's actually showing -- each beat's
    text is then split into sentence-sized chunks with proportional timing
    rather than shown as one static block for the whole beat."""
    lines = []
    cursor = 0.0
    idx = 1
    for text, duration in segments:
        beat_end = cursor + duration
        chunks = _split_into_caption_chunks(text)
        total_chars = sum(len(c) for c in chunks) or 1
        chunk_start = cursor
        for i, chunk in enumerate(chunks):
            share = len(chunk) / total_chars
            end = chunk_start + duration * share
            if i == len(chunks) - 1:
                end = beat_end  # last chunk always lands exactly on the beat boundary
            end = min(end, beat_end)  # never let a chunk bleed into the next beat's captions
            if end <= chunk_start:
                continue
            lines.append(str(idx))
            idx += 1
            lines.append(f"{_srt_timestamp(chunk_start)} --> {_srt_timestamp(end)}")
            lines.append(chunk)
            lines.append("")
            chunk_start = end
        cursor = beat_end
    out_srt.write_text("\n".join(lines), encoding="utf-8")


def build_static_clip(ffmpeg: str, image_path: Path, out_path: Path, duration: float) -> None:
    fade_out_start = max(duration - 0.4, 0)
    vf = f"fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out_start}:d=0.4"
    subprocess.run([
        ffmpeg, "-y", "-loop", "1", "-i", str(image_path), "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-t", str(duration), str(out_path),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def record_scene_video(browser, html: str, out_mp4: Path, duration: float, ffmpeg: str) -> None:
    """Capture a scene's own JS animation (count-up numbers, staggered
    reveals, a typing effect) as real recorded video, instead of a static
    screenshot held under a fade -- genuine motion, not a still image."""
    with tempfile.TemporaryDirectory(prefix="crosssignal-scene-") as vdir:
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080}, device_scale_factor=1,
            record_video_dir=vdir, record_video_size={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        page.set_content(html)
        dwell(page, duration)
        context.close()
        recorded = next(Path(vdir).glob("*.webm"))
        fade_out_start = max(duration - 0.4, 0)
        subprocess.run([
            ffmpeg, "-y", "-i", str(recorded),
            "-vf", f"fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out_start}:d=0.4",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "30",
            "-pix_fmt", "yuv420p", "-t", str(duration), str(out_mp4),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def dwell(page, seconds: float) -> None:
    page.wait_for_timeout(int(seconds * 1000))


def beat_finish(page, start: float, target_duration: float) -> None:
    """Wait only the time remaining to reach target_duration, measured from
    `start`. Clicks and scrolls take real wall-clock time that the narration
    track has no matching gap for; waiting a fixed extra amount on top of
    that (instead of accounting for it) accumulates drift beat over beat
    until picture and narration are visibly out of sync by the end."""
    elapsed = time.monotonic() - start
    remaining = max(target_duration - elapsed, 0.0)
    dwell(page, remaining)


def install_cursor(page) -> None:
    page.evaluate(CURSOR_INIT_JS)


def visible_click(page, locator) -> None:
    box = locator.bounding_box()
    if box:
        cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        page.evaluate("([x,y]) => window.__csMoveCursor && window.__csMoveCursor(x,y)", [cx, cy])
        page.mouse.move(cx, cy, steps=20)
        page.wait_for_timeout(CURSOR_MOVE_MS)
        page.evaluate("window.__csPulseCursor && window.__csPulseCursor()")
        page.wait_for_timeout(150)
    locator.click()


def switch_tab(page, name: str) -> None:
    """Reset scroll before AND after switching, so the tab bar sits in a
    known position for the cursor and the new tab's content actually lands
    on screen instead of wherever a previous deep-scroll left the viewport."""
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(200)
    visible_click(page, page.get_by_role("tab", name=name))
    page.wait_for_timeout(150)
    page.evaluate("window.scrollTo(0, 0)")


def run_beats(page, durations: dict[str, float]) -> None:
    install_cursor(page)

    t0 = time.monotonic()
    beat_finish(page, t0, durations["open_live"])

    t0 = time.monotonic()
    switch_tab(page, "Decision case")
    page.get_by_text("Decision intelligence scorecard").scroll_into_view_if_needed()
    beat_finish(page, t0, durations["scorecard"])

    t0 = time.monotonic()
    page.get_by_text("Decision Replay courtroom").scroll_into_view_if_needed()
    beat_finish(page, t0, durations["courtroom"])

    t0 = time.monotonic()
    try:
        page.get_by_text("Prove the agent can refuse").scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        toggle = page.get_by_text("Simulate stale or fallback evidence")
        for attempt in range(3):
            visible_click(page, toggle)
            try:
                page.get_by_text("ABSTAIN —", exact=False).wait_for(timeout=2_000)
                break
            except Exception:
                if attempt == 2:
                    raise
    except Exception:
        pass
    beat_finish(page, t0, durations["abstention"])

    t0 = time.monotonic()
    try:
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(150)
        replay_selector = page.get_by_role("combobox", name="Replay decision")
        visible_click(page, replay_selector)
        page.wait_for_timeout(300)
        page.keyboard.press("ArrowDown")
        page.wait_for_timeout(150)
        page.keyboard.press("Enter")
        page.get_by_text("AUTHORIZED", exact=False).first.wait_for(timeout=10_000)
        page.get_by_text("Decision Replay courtroom").scroll_into_view_if_needed()
    except Exception:
        pass
    beat_finish(page, t0, durations["authorized_case"])


def main() -> int:
    global CAPTURE_URL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="recording-output/CrossSignal-Submission-Narrated.mp4")
    parser.add_argument("--voice", default="en-US-AndrewMultilingualNeural")
    parser.add_argument("--edge-rate", default="-8%")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--captions", action="store_true",
                         help="Burn in captions (off by default -- covers "
                              "the app UI and reads as distracting).")
    args = parser.parse_args()

    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_ffmpeg()

    with tempfile.TemporaryDirectory(prefix="crosssignal-tour-") as name:
        temp = Path(name)

        # Pass 1: synthesize narration, measure real spoken durations. A
        # beat with a real-voice recording dropped in REAL_VOICE_DIR (see
        # find_real_voice_override) is re-encoded and used verbatim instead
        # of calling edge-tts -- title/closing duration is measured from
        # whichever audio actually plays, so real and synthetic clips mix
        # without any manual re-timing.
        durations: dict[str, float] = {}
        audio_paths: dict[str, Path] = {}
        for beat_id, narration in [TITLE_BEAT, PROBLEM_BEAT, ARCHITECTURE_BEAT, CODE_BEAT, TERMINAL_BEAT, EVIDENCE_BEAT, *BEATS]:
            audio = temp / f"{beat_id}.mp3"
            override = find_real_voice_override(beat_id)
            if override:
                subprocess.run([
                    ffmpeg, "-y", "-i", str(override),
                    "-filter:a", f"atempo={REAL_VOICE_SPEEDUP}",
                    "-ar", "48000", "-ac", "2",
                    "-c:a", "libmp3lame", "-q:a", "2", str(audio),
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"  [voice] using real recording for {beat_id} "
                      f"(sped up {REAL_VOICE_SPEEDUP}x): {override.name}")
            else:
                script = temp / f"{beat_id}.txt"
                script.write_text(narration.strip() + "\n", encoding="utf-8")
                synthesize(script, audio, args.voice, args.edge_rate)
            spoken = media_duration(ffmpeg, audio)
            durations[beat_id] = spoken + TAIL_PAD
            audio_paths[beat_id] = audio
        audio_clips = [audio_paths[beat_id] for beat_id, _ in BEATS]

        # Pass 2: launch app (public demo, minimal toolbar), warm it up, then record.
        port = available_local_port()
        CAPTURE_URL = f"http://127.0.0.1:{port}"
        env = recording_environment()
        videos_dir = temp / "video"
        videos_dir.mkdir()
        server = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "app.py",
             "--server.headless=true", "--server.address=127.0.0.1",
             f"--server.port={port}", "--browser.gatherUsageStats=false",
             "--client.toolbarMode=minimal"],
            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
        )
        try:
            wait_for_app(CAPTURE_URL)
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=not args.headed)

                # Warm-up pass (not recorded): forces Streamlit's script to
                # finish its first real run before we start the timed capture.
                warm_context = browser.new_context(viewport={"width": 1920, "height": 1080})
                warm_page = warm_context.new_page()
                warm_page.goto(CAPTURE_URL, wait_until="networkidle", timeout=60_000)
                warm_page.get_by_text("PUBLIC JUDGE MODE", exact=False).wait_for(timeout=30_000)
                warm_context.close()

                # Render the code/closing opening scenes while we have a browser handy.
                problem_png = temp / "problem_scene.png"
                architecture_png = temp / "architecture_scene.png"
                code_png = temp / "code_scene.png"
                closing_png = temp / "closing_scene.png"
                render_scene_png(browser, PROBLEM_SCENE_HTML, problem_png)
                render_scene_png(browser, ARCHITECTURE_SCENE_HTML, architecture_png)
                render_scene_png(browser, CODE_SCENE_HTML, code_png)
                render_scene_png(browser, CLOSING_SCENE_HTML, closing_png)

                # Terminal (typing effect) and evidence (count-up/reveal) have
                # their own JS animations -- record them as real video, not a
                # static screenshot held under a fade.
                terminal_clip = temp / "terminal.mp4"
                evidence_clip = temp / "evidence.mp4"
                record_scene_video(browser, TERMINAL_SCENE_HTML, terminal_clip,
                                    durations["terminal_scene"], ffmpeg)
                record_scene_video(browser, EVIDENCE_SCENE_HTML, evidence_clip,
                                    durations["evidence_scene"], ffmpeg)

                # Recorded pass: measure the residual load time for accurate sync.
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080}, device_scale_factor=1,
                    record_video_dir=str(videos_dir),
                    record_video_size={"width": 1920, "height": 1080},
                )
                page = context.new_page()
                load_start = time.monotonic()
                page.goto(CAPTURE_URL, wait_until="networkidle", timeout=60_000)
                page.get_by_text("PUBLIC JUDGE MODE", exact=False).wait_for(timeout=30_000)
                dwell(page, SETTLE)
                load_latency = time.monotonic() - load_start

                run_beats(page, durations)
                context.close()
                browser.close()
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()

        recorded = next(videos_dir.glob("*.webm"))

        # Title card holds the name-intro line and covers the measured load
        # window; if the load ran long, stretch the card and pad the audio
        # gap with silence so video and audio re-sync exactly at the cut.
        title_speech = durations["open_title"]
        title_duration = max(title_speech, load_latency + 0.3, TITLE_CARD_MIN)
        title_duration = min(title_duration, TITLE_CARD_MAX)
        audio_gap = max(title_duration - title_speech, 0.0)
        title_card = temp / "title.mp4"
        build_title_card(ffmpeg, title_card, title_duration)

        problem_clip = temp / "problem.mp4"
        architecture_clip = temp / "architecture.mp4"
        code_clip = temp / "code.mp4"
        closing_clip = temp / "closing.mp4"
        github_evidence_clip = temp / "github_evidence.mp4"
        repo_proof_clip = temp / "repo_proof.mp4"
        build_static_clip(ffmpeg, problem_png, problem_clip, durations["problem_scene"])
        build_static_clip(ffmpeg, architecture_png, architecture_clip, durations["architecture_scene"])
        build_static_clip(ffmpeg, code_png, code_clip, durations["code_scene"])
        build_static_clip(ffmpeg, closing_png, closing_clip, durations["close"])
        build_static_clip(ffmpeg, GITHUB_EVIDENCE_PNG, github_evidence_clip, durations["cloud_evidence"])
        build_static_clip(ffmpeg, GITHUB_REPO_PNG, repo_proof_clip, durations["repo_proof"])

        # Trim the recording's own blank lead-in (page load/render), not just
        # cover it with the title card — otherwise the concatenated result
        # still has dead white time after the title card cuts away.
        trim_point = max(load_latency + 0.2, 0.0)
        recorded_mp4 = temp / "recorded.mp4"
        # Every other clip in the manifest fades in/out through black; this
        # live screen recording was the one exception, so it cut in and out
        # abruptly against neighbors that fade -- match the same treatment
        # so the whole sequence reads as one consistent rhythm of cuts.
        recorded_duration = media_duration(ffmpeg, recorded) - trim_point
        recorded_fade_out_start = max(recorded_duration - 0.4, 0)
        subprocess.run([
            ffmpeg, "-y", "-i", str(recorded), "-ss", str(trim_point),
            "-vf", f"fade=t=in:st=0:d=0.4,fade=t=out:st={recorded_fade_out_start}:d=0.4",
            "-c:v", "libx264", "-preset", "medium",
            "-crf", "20", "-r", "30", "-pix_fmt", "yuv420p", "-an", str(recorded_mp4),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        video_manifest = temp / "video_manifest.txt"
        video_manifest.write_text(
            f"file '{title_card}'\nfile '{problem_clip}'\nfile '{architecture_clip}'\n"
            f"file '{code_clip}'\nfile '{terminal_clip}'\n"
            f"file '{evidence_clip}'\nfile '{recorded_mp4}'\n"
            f"file '{github_evidence_clip}'\nfile '{repo_proof_clip}'\n"
            f"file '{closing_clip}'\n"
        )
        combined_video = temp / "combined.mp4"
        subprocess.run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(video_manifest),
                        "-c", "copy", str(combined_video)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Narration starts at t=0, aligned with the title card's first line.
        # If the title card had to stretch beyond the spoken intro (slow
        # load), insert matching silence so the cut to live video still
        # lines up with the next narration beat.
        manifest_lines = [f"file '{audio_paths['open_title']}'\n"]
        if audio_gap > 0.05:
            silence = temp / "gap_silence.mp3"
            subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                            "-t", str(audio_gap), str(silence)], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            manifest_lines.append(f"file '{silence}'\n")
        manifest_lines += [
            f"file '{audio_paths['problem_scene']}'\n",
            f"file '{audio_paths['architecture_scene']}'\n",
            f"file '{audio_paths['code_scene']}'\n",
            f"file '{audio_paths['terminal_scene']}'\n",
            f"file '{audio_paths['evidence_scene']}'\n",
        ]
        manifest_lines += [f"file '{clip}'\n" for clip in audio_clips]
        manifest = temp / "audio_manifest.txt"
        manifest.write_text("".join(manifest_lines))
        narration_track = temp / "narration.mp3"
        subprocess.run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(manifest),
                        "-af", f"apad=pad_dur={TAIL_PAD}", str(narration_track)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Subtle ambient bed under the narration -- a low drone, not a melody,
        # so it can't clash with or distract from speech. Kept quiet enough
        # that it reads as "not dead silence" rather than as music per se.
        narration_duration = media_duration(ffmpeg, narration_track)
        fade_out_at = max(narration_duration - 3, 0)
        music_bed = temp / "music_bed.mp3"
        subprocess.run([
            ffmpeg, "-y",
            "-f", "lavfi", "-i", f"sine=frequency=65.41:duration={narration_duration}",
            "-f", "lavfi", "-i", f"sine=frequency=98.00:duration={narration_duration}",
            "-f", "lavfi", "-i", f"sine=frequency=261.63:duration={narration_duration}",
            "-filter_complex",
            "[0:a][1:a][2:a]amix=inputs=3:duration=longest:normalize=0,"
            "lowpass=f=900,"
            f"afade=t=in:st=0:d=3,afade=t=out:st={fade_out_at}:d=3,"
            "volume=0.045",
            str(music_bed),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        mixed_audio = temp / "mixed_audio.mp3"
        subprocess.run([
            ffmpeg, "-y", "-i", str(narration_track), "-i", str(music_bed),
            "-filter_complex",
            "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]",
            "-map", "[aout]", str(mixed_audio),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Two-pass loudness normalization to -16 LUFS (the mixed narration+bed
        # was measuring around -22 LUFS, noticeably quiet). Measure first,
        # then apply with the measured values for an accurate linear correction
        # rather than a blind single-pass guess.
        measure = subprocess.run([
            ffmpeg, "-i", str(mixed_audio),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
            "-f", "null", "-",
        ], capture_output=True, text=True)
        stats_match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", measure.stderr)
        final_audio = temp / "final_audio.mp3"
        if stats_match:
            stats = json.loads(stats_match.group())
            loudnorm_filter = (
                f"loudnorm=I=-16:TP=-1.5:LRA=11:"
                f"measured_I={stats['input_i']}:measured_TP={stats['input_tp']}:"
                f"measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}:"
                f"offset={stats['target_offset']}:linear=true"
            )
        else:
            loudnorm_filter = "loudnorm=I=-16:TP=-1.5:LRA=11"
        subprocess.run([
            ffmpeg, "-y", "-i", str(mixed_audio), "-af", loudnorm_filter, str(final_audio),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        mux_cmd = [
            ffmpeg, "-y", "-i", str(combined_video), "-i", str(final_audio),
            "-map", "0:v:0", "-map", "1:a:0",
        ]
        if args.captions:
            # Burned-in captions: walk the same clip sequence used to build
            # video_manifest, in the same order, so each caption's timing
            # lines up with what's actually on screen at that point.
            caption_segments = [(TITLE_BEAT[1], title_duration),
                                 (PROBLEM_BEAT[1], durations["problem_scene"]),
                                 (ARCHITECTURE_BEAT[1], durations["architecture_scene"]),
                                 (CODE_BEAT[1], durations["code_scene"]),
                                 (TERMINAL_BEAT[1], durations["terminal_scene"]),
                                 (EVIDENCE_BEAT[1], durations["evidence_scene"])]
            caption_segments += [(text, durations[beat_id]) for beat_id, text in BEATS]
            srt_path = temp / "captions.srt"
            build_captions_srt(caption_segments, srt_path)
            mux_cmd += [
                "-vf", f"subtitles={srt_path.name}:force_style="
                       "'FontName=Arial,FontSize=16,Bold=1,PrimaryColour=&HFFFFFF&,"
                       "OutlineColour=&H000000&,BorderStyle=1,Outline=2,Shadow=1,"
                       "MarginV=30,MarginL=30,MarginR=100'",
            ]
        mux_cmd += [
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "30",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
            "-shortest", "-movflags", "+faststart", str(output),
        ]
        subprocess.run(mux_cmd, check=True, cwd=temp,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    final_duration = media_duration(ffmpeg, output)
    if final_duration > 300:
        raise RuntimeError(f"Final video is {final_duration:.1f}s, over the 5:00 limit")
    print(f"Narrated screen recording: {output}")
    print(f"Duration: {int(final_duration // 60)}:{int(final_duration % 60):02d}")
    print(f"Title card duration: {title_duration:.1f}s (measured load latency: {load_latency:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
