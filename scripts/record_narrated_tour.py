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
</style></head>
<body>
  <div class="titlebar"><div class="dot r"></div><div class="dot y"></div><div class="dot g"></div>
    <span class="filename">terminal &mdash; crosssignal</span></div>
  <div class="term">
<div><span class="prompt">$</span> <span class="cmd">streamlit run app.py</span></div>
<div>&nbsp;</div>
<div class="out">  You can now view your Streamlit app in your browser.</div>
<div>&nbsp;</div>
<div class="out">  Local URL: <span class="url">http://localhost:8501</span></div>
<div>&nbsp;</div>
<div class="ok">&#10003; PUBLIC_DEMO_MODE=true &middot; ALLOW_PAPER_EXECUTION=false</div>
  </div>
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
              "could do was say no? I'm Omobolaji E Adeyan, and this is "
              "CrossSignal.")
CODE_BEAT = ("code_scene", "Most autonomous agents will happily risk your "
             "capital on a hunch they can't defend later. CrossSignal "
             "can't. Every decision — authorized or refused — is sealed "
             "with cryptographic proof, traced straight back to code like "
             "this, before it ever touches a dollar.")
TERMINAL_BEAT = ("terminal_scene", "One command runs it locally, in public "
                  "demo mode, with paper execution disabled by default — so "
                  "you can verify all of this yourself, not just take my "
                  "word for it.")

BEATS = [
    ("open_live", "On August 30th, rate expectations and credit pricing "
     "disagreed by 80 points out of 100 — strong enough that most systems "
     "would have fired a trade immediately. Here's what CrossSignal did "
     "instead."),
    ("scorecard", "It ran the case through four independent scores: signal "
     "quality came in at eighty, decision stability held at a full "
     "hundred across ten bounded perturbations, and execution quality "
     "landed at eighty as well. Three real gates, and all of them were "
     "clearing so far."),
    ("courtroom", "Every step of that reasoning gets reconstructed and "
     "sealed, from the allegation to the cross-examination to the "
     "judgment, all hashed with SHA-256 starting with 781aedf2dafea7a0. "
     "Nothing here is simply asserted — it's proven."),
    ("abstention", "Then one gate failed: option liquidity required ten, "
     "and only four existed. And here's what most trading bots can't do — "
     "CrossSignal said no, with no order ever sent to the broker and "
     "nothing to recover from, because a strong signal is never automatic "
     "authorization to trade. Refusing was the correct call here, not a "
     "malfunction."),
    ("methodology", "That judgment wasn't improvised. It came from the "
     "same seven-step SIGNAL protocol every decision runs through: "
     "reading six market lenses, labeling each value's provenance, "
     "synthesizing a thesis with Claude, constructing SPY, HYG, and TLT "
     "defined-risk spreads, governing against risk limits, preflighting "
     "every leg's price, and auditing the full trail. This is an "
     "educational prototype for paper trading only, not investment "
     "advice."),
    ("run_agent", "This public application stays completely "
     "credential-free, and one click replays a sanitized version of this "
     "exact case, with no external service and no broker account "
     "involved. There's nothing here you have to trust blindly."),
    ("executive", "This isn't a one-off, either. The same loop of "
     "observing, reasoning, and governing has already run twice, "
     "producing two theses, two trade cycles, one submission, and a "
     "hundred percent forecast hit rate so far."),
    ("track_record", "Nothing here gets cherry-picked. The track record "
     "keeps every thesis visible, whether it's already scored or still "
     "pending, including the one still waiting on its evaluation "
     "horizon."),
    ("readiness", "CrossSignal is candid about itself, too. The Readiness "
     "tab tracks its own submission requirements live, showing eleven of "
     "fourteen fully met, with the rest marked incomplete right out in "
     "the open."),
    ("security", "None of this would hold if the model could act "
     "unsupervised, so it simply can't. Claude cannot call Alpaca "
     "directly. Public execution stays disabled, the paper endpoint is "
     "enforced, and missing credentials fail setup explicitly instead of "
     "manufacturing evidence. These are NIST-aligned controls, not a "
     "prompt asking the model to behave."),
    ("close", "Markets disagree constantly. The hard part was never "
     "finding the disagreement — it's knowing when not to act on it, and "
     "proving you were right to wait. This is CrossSignal."),
]

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


def synthesize(script: Path, audio: Path, voice: str, rate_pct: str) -> None:
    edge_tts = shutil.which("edge-tts")
    cmd = [edge_tts] if edge_tts else [sys.executable, "-m", "edge_tts"]
    subprocess.run([*cmd, "-f", str(script), "-v", voice, f"--rate={rate_pct}",
                    "--write-media", str(audio)], check=True)


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
            f"drawtext=fontfile=arial.ttf:text='Presented by Omobolaji E Adeyan':"
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


def build_static_clip(ffmpeg: str, image_path: Path, out_path: Path, duration: float) -> None:
    fade_out_start = max(duration - 0.4, 0)
    vf = f"fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out_start}:d=0.4"
    subprocess.run([
        ffmpeg, "-y", "-loop", "1", "-i", str(image_path), "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-t", str(duration), str(out_path),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def dwell(page, seconds: float) -> None:
    page.wait_for_timeout(int(seconds * 1000))


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

    dwell(page, durations["open_live"])

    switch_tab(page, "Decision case")
    dwell(page, SETTLE)
    page.get_by_text("Decision intelligence scorecard").scroll_into_view_if_needed()
    dwell(page, durations["scorecard"])

    page.get_by_text("Decision Replay courtroom").scroll_into_view_if_needed()
    dwell(page, durations["courtroom"])

    try:
        page.get_by_text("Prove the agent can refuse").scroll_into_view_if_needed()
        dwell(page, SETTLE)
        visible_click(page, page.get_by_text("Simulate stale or fallback evidence"))
        dwell(page, durations["abstention"])
    except Exception:
        dwell(page, durations["abstention"])

    switch_tab(page, "Methodology")
    dwell(page, SETTLE)
    dwell(page, durations["methodology"])

    switch_tab(page, "Run agent")
    dwell(page, SETTLE)
    try:
        visible_click(page, page.get_by_role("button", name="Replay sanitized judge case"))
        page.get_by_text("Sanitized case replayed", exact=False).wait_for(timeout=15_000)
    except Exception:
        pass
    dwell(page, durations["run_agent"])

    switch_tab(page, "Executive overview")
    dwell(page, SETTLE)
    dwell(page, durations["executive"])

    switch_tab(page, "Track record")
    dwell(page, SETTLE)
    dwell(page, durations["track_record"])

    switch_tab(page, "Readiness")
    dwell(page, SETTLE)
    dwell(page, durations["readiness"])

    switch_tab(page, "Security")
    dwell(page, SETTLE)
    dwell(page, durations["security"])

    page.evaluate("window.scrollTo(0, 0)")
    dwell(page, SETTLE)
    dwell(page, durations["close"])


def main() -> int:
    global CAPTURE_URL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="recording-output/CrossSignal-Submission-Narrated.mp4")
    parser.add_argument("--voice", default="en-US-AndrewMultilingualNeural")
    parser.add_argument("--edge-rate", default="-8%")
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_ffmpeg()

    with tempfile.TemporaryDirectory(prefix="crosssignal-tour-") as name:
        temp = Path(name)

        # Pass 1: synthesize narration, measure real spoken durations.
        durations: dict[str, float] = {}
        audio_paths: dict[str, Path] = {}
        for beat_id, narration in [TITLE_BEAT, CODE_BEAT, TERMINAL_BEAT, *BEATS]:
            script = temp / f"{beat_id}.txt"
            audio = temp / f"{beat_id}.mp3"
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

                # Render the code/terminal opening scenes while we have a browser handy.
                code_png = temp / "code_scene.png"
                terminal_png = temp / "terminal_scene.png"
                render_scene_png(browser, CODE_SCENE_HTML, code_png)
                render_scene_png(browser, TERMINAL_SCENE_HTML, terminal_png)

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

        code_clip = temp / "code.mp4"
        terminal_clip = temp / "terminal.mp4"
        build_static_clip(ffmpeg, code_png, code_clip, durations["code_scene"])
        build_static_clip(ffmpeg, terminal_png, terminal_clip, durations["terminal_scene"])

        # Trim the recording's own blank lead-in (page load/render), not just
        # cover it with the title card — otherwise the concatenated result
        # still has dead white time after the title card cuts away.
        trim_point = max(load_latency + 0.2, 0.0)
        recorded_mp4 = temp / "recorded.mp4"
        subprocess.run([
            ffmpeg, "-y", "-i", str(recorded), "-ss", str(trim_point),
            "-c:v", "libx264", "-preset", "medium",
            "-crf", "20", "-r", "30", "-pix_fmt", "yuv420p", "-an", str(recorded_mp4),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        video_manifest = temp / "video_manifest.txt"
        video_manifest.write_text(
            f"file '{title_card}'\nfile '{code_clip}'\nfile '{terminal_clip}'\n"
            f"file '{recorded_mp4}'\n"
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
            f"file '{audio_paths['code_scene']}'\n",
            f"file '{audio_paths['terminal_scene']}'\n",
        ]
        manifest_lines += [f"file '{clip}'\n" for clip in audio_clips]
        manifest = temp / "audio_manifest.txt"
        manifest.write_text("".join(manifest_lines))
        narration_track = temp / "narration.mp3"
        subprocess.run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(manifest),
                        "-af", f"apad=pad_dur={TAIL_PAD}", str(narration_track)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        subprocess.run([
            ffmpeg, "-y", "-i", str(combined_video), "-i", str(narration_track),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "30",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
            "-shortest", "-movflags", "+faststart", str(output),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    final_duration = media_duration(ffmpeg, output)
    if final_duration > 300:
        raise RuntimeError(f"Final video is {final_duration:.1f}s, over the 5:00 limit")
    print(f"Narrated screen recording: {output}")
    print(f"Duration: {int(final_duration // 60)}:{int(final_duration % 60):02d}")
    print(f"Title card duration: {title_duration:.1f}s (measured load latency: {load_latency:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
