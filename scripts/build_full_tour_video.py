#!/usr/bin/env python3
"""Build a comprehensive narrated CrossSignal submission video covering every
judge-facing tab, using real screenshots and extracted figures captured by
capture_full_tour.py. Uses Microsoft Edge neural TTS (free, no API key) and
per-clip fades instead of fixed-duration silence padding and hard cuts."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "recording-output" / "full-tour" / "screenshots"

FADE = 0.25       # seconds, video/audio fade in and out at each clip boundary
TAIL_PAD = 0.35   # seconds of breathing room after speech ends, before the cut

SCENES = [
    ("00-landing.png",
     "Hello, I'm Omobolaji E Adeyan, and this is CrossSignal. Markets rarely "
     "reprice at the same speed — equity options may show fear while credit "
     "stays calm. CrossSignal synchronizes six live market lenses into one "
     "macro state. Its goal isn't the most trades. It's proving when a trade "
     "actually deserves authorization."),
    ("11-methodology.png",
     "The SIGNAL protocol runs seven deterministic steps. Read six market "
     "lenses. Label every value as live, computed, proxied, or fallback. "
     "Synthesize a structured thesis with Claude. Construct SPY, HYG, and TLT "
     "defined-risk spreads. Govern with structure, loss, and buying-power "
     "checks. Preflight every leg's price. And audit the full decision trail. "
     "This is an educational prototype for paper trading only, not investment "
     "advice."),
    ("01-decision-scorecard.png",
     "This is Decision Replay for contract CS-DEMO-781AEDF2. Instead of one "
     "confidence number, CrossSignal scores four things: signal quality, 80 "
     "out of 100; decision stability, 100 out of 100; execution quality, 80 "
     "out of 100; and outcome evidence. The sealed prediction: credit spread "
     "moves wider. The verdict: ABSTAIN."),
    ("02-decision-replay.png",
     "The courtroom reconstructs only what was known at decision time — the "
     "allegation, the cross-examination, and the judgment. Every case is "
     "sealed with a SHA-256 hash, starting with 781aedf2dafea7a0, so the "
     "reasoning is independently verifiable, not just asserted."),
    ("04-proof-of-abstention.png",
     "Why abstain? Option liquidity required ten; only four were available. "
     "Recovery state is STOPPED, with an explicit instruction not to retry "
     "automatically. A strong signal is not automatic permission to trade. "
     "This is a correct, governed refusal, not a system failure."),
    ("06-run-agent-replayed.png",
     "The public judge application is credential-free. One click replays a "
     "sanitized case — no external service or broker account is contacted, "
     "and the paper-order toggle stays disabled by deployment policy."),
    ("07-executive-overview.png",
     "Executive overview breaks the workflow into three stages: Observe, "
     "where Alpaca data and Treasury yields form a provenance-tagged "
     "snapshot; Reason, where Claude proposes the thesis; and Govern, where "
     "risk checks run before any order. So far: two theses generated, two "
     "trade cycles, one submitted, and a 100 percent forecast hit rate."),
    ("08-track-record.png",
     "No thesis disappears when it's inconvenient. The track record keeps "
     "one scored thesis at a 100 percent hit rate, and one still pending "
     "— nothing gets rewritten after the fact."),
    ("09-readiness.png",
     "CrossSignal is transparent about its own gaps too. The Readiness tab "
     "tracks submission requirements live: eleven of fourteen fully met, "
     "with the rest honestly marked incomplete."),
    ("10-security.png",
     "Safety is architectural, not a prompt. Claude cannot call Alpaca "
     "directly. The paper endpoint is enforced, public execution is "
     "disabled, live data is required, and missing credentials fail setup "
     "explicitly. These controls are aligned to NIST AI risk-management "
     "practices — a documented boundary, not a certification claim."),
    ("00-landing.png",
     "CrossSignal doesn't just recommend a trade — it proves whether the "
     "trade deserves authorization. Thirty-nine automated tests back every "
     "gate you just saw. I'm Omobolaji E Adeyan. Thank you."),
]


def find_ffmpeg() -> str:
    direct = shutil.which("ffmpeg")
    if direct:
        return direct
    candidates = sorted((Path.home() / "AppData/Local/ms-playwright").glob("ffmpeg*/ffmpeg-*.exe"))
    if candidates:
        return str(candidates[-1])
    raise RuntimeError("ffmpeg is required; install it or Playwright Chromium")


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
    subprocess.run([*cmd, "-f", str(script), "-v", voice, "--rate", rate_pct,
                    "--write-media", str(audio)], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="recording-output/CrossSignal-Submission-Narrated.mp4")
    parser.add_argument("--voice", default="en-US-AndrewNeural")
    parser.add_argument("--edge-rate", default="+0%")
    args = parser.parse_args()

    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_ffmpeg()

    with tempfile.TemporaryDirectory(prefix="crosssignal-fulltour-") as name:
        temp, clips = Path(name), []
        for index, (image_name, narration) in enumerate(SCENES, 1):
            image = SHOTS / image_name
            if not image.exists():
                raise FileNotFoundError(f"Missing evidence frame: {image}")
            script = temp / f"scene-{index:02d}.txt"
            audio = temp / f"scene-{index:02d}.mp3"
            clip = temp / f"scene-{index:02d}.mp4"
            script.write_text(narration.strip() + "\n", encoding="utf-8")
            synthesize(script, audio, args.voice, args.edge_rate)
            spoken = media_duration(ffmpeg, audio)
            duration = spoken + TAIL_PAD
            fade_out_start = max(duration - FADE, 0)
            audio_fade_out_start = max(duration - FADE * 1.5, 0)
            subprocess.run([
                ffmpeg, "-y", "-loop", "1", "-i", str(image), "-i", str(audio),
                "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
                       "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=white,format=yuv420p,"
                       f"fade=t=in:st=0:d={FADE}:color=white,"
                       f"fade=t=out:st={fade_out_start}:d={FADE}:color=white",
                "-af", f"apad,afade=t=in:st=0:d={FADE*0.6},afade=t=out:st={audio_fade_out_start}:d={FADE*1.5}",
                "-t", str(duration), "-r", "30", "-c:v", "libx264",
                "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
                "-ar", "48000", str(clip),
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            clips.append(clip)
        manifest = temp / "clips.txt"
        manifest.write_text("".join(f"file '{clip}'\n" for clip in clips))
        subprocess.run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(manifest),
                        "-c", "copy", "-movflags", "+faststart", str(output)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    final_duration = media_duration(ffmpeg, output)
    if final_duration > 300:
        raise RuntimeError(f"Final video is {final_duration:.1f}s, over the 5:00 limit")
    print(f"Narrated submission draft: {output}")
    print(f"Duration: {int(final_duration // 60)}:{int(final_duration % 60):02d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
