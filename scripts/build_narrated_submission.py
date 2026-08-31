#!/usr/bin/env python3
"""Build an exact 4:35 narrated CrossSignal draft from safe screenshots."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_SECONDS = 275
SCENES = [
    ("01-landing.png", 28, """Markets reprice at different speeds. CrossSignal finds the disagreement between equities, credit, rates, volatility, and positioning before it becomes obvious in one market. It is an auditable AI trading agent built on Alpaca paper trading. Its purpose is not to produce the most trades. Its purpose is to prove when a trade deserves authorization."""),
    ("02-scorecard.png", 42, """Most systems compress intelligence into one confidence number. CrossSignal separates four questions. Is the cross-market signal strong? Is the decision stable when inputs are perturbed? Can the proposed structure pass every deterministic execution check? And, after the sealed horizon matures, was the prediction actually correct? This scorecard prevents a persuasive language model explanation from hiding weak liquidity, stale data, excessive risk, or an outcome that has not yet been observed."""),
    ("03-decision-replay.png", 45, """The Decision Replay courtroom reconstructs only what was known at decision time. The market snapshot states the allegation. Cross-market evidence provides the counterargument. The agent records its judgment, seals the prediction and invalidation conditions, and joins the later broker lifecycle without rewriting history. At the predetermined horizon, the verdict compares the agent direction with inverse and cash counterfactuals. Judges can inspect the reasoning path and independently verify the decision hash."""),
    ("04-proof-of-abstention.png", 42, """A strong signal is not automatic permission to trade. In this demonstration, evidence integrity is deliberately weakened and the policy fails closed. The latest connected GitHub Evidence Watch reached the same kind of governed result. Signal quality was eighty-five, stability was one hundred, but execution quality was ninety-three because only fourteen of fifteen checks passed. CrossSignal abstained. That is a correct autonomous decision, not a system failure."""),
    ("05-read-only-replay.png", 30, """The public judge application is deliberately credential free. It uses a clearly labeled sanitized replay, cannot contact a broker, and cannot enable order submission. The same repository contains a scheduled cloud evidence watcher. That automation observes, reasons, and seals a receipt, while execution remains forcibly disabled. Judges receive reproducible evidence without receiving financial authority."""),
    ("06-track-record.png", 34, """No thesis disappears when it becomes inconvenient. The learning ledger keeps both scored and pending decisions. Each record preserves confidence, the evaluation horizon, the observed result, and whether the forecast direction was correct. The sample is intentionally labeled preliminary. CrossSignal does not turn a small result into a performance promise; it turns every new decision into additional accountable evidence."""),
    ("07-security-boundary.png", 38, """Safety is architectural, not a sentence in a prompt. Claude proposes structured signals but has no direct broker tools. News is treated as untrusted context. Public execution is disabled in both the interface and broker boundary. Only the exact Alpaca paper endpoint is permitted. Recovery actions require explicit approval. Secret-free receipts, provenance, deterministic limits, and thirty-eight automated tests make each privilege visible and reviewable."""),
    ("01-landing.png", 16, """CrossSignal does not merely recommend a trade. It shows the evidence, challenges the reasoning, governs execution, seals the decision, and learns from the outcome. Markets disagree. CrossSignal proves whether the gap deserves action."""),
]


def find_ffmpeg() -> str:
    direct = shutil.which("ffmpeg")
    if direct:
        return direct
    candidates = sorted((Path.home() / "Library/Caches/ms-playwright").glob("ffmpeg*/ffmpeg-*"))
    if candidates:
        return str(candidates[-1])
    raise RuntimeError("ffmpeg is required; install Playwright Chromium or ffmpeg")


def media_duration(ffmpeg: str, path: Path) -> float:
    probe = subprocess.run([ffmpeg, "-i", str(path)], capture_output=True, text=True)
    match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", probe.stderr)
    if not match:
        raise RuntimeError(f"Could not determine duration for {path.name}")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", default="recording-output/screenshots")
    parser.add_argument("--output", default="recording-output/CrossSignal-Submission-Narrated.mp4")
    parser.add_argument("--voice", default="Samantha")
    parser.add_argument("--rate", type=int, default=175)
    args = parser.parse_args()
    screenshots = (ROOT / args.input_dir).resolve()
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg, say = find_ffmpeg(), shutil.which("say")
    if not say:
        raise RuntimeError("This builder currently requires the macOS 'say' command")

    with tempfile.TemporaryDirectory(prefix="crosssignal-narration-") as name:
        temp, clips = Path(name), []
        for index, (image_name, allotted, narration) in enumerate(SCENES, 1):
            image = screenshots / image_name
            if not image.exists():
                raise FileNotFoundError(f"Missing evidence frame: {image}")
            script, audio = temp / f"scene-{index:02d}.txt", temp / f"scene-{index:02d}.aiff"
            clip = temp / f"scene-{index:02d}.mp4"
            script.write_text(narration.strip() + "\n")
            subprocess.run([say, "-v", args.voice, "-r", str(args.rate),
                            "-f", str(script), "-o", str(audio)], check=True)
            spoken = media_duration(ffmpeg, audio)
            if spoken > allotted - 0.5:
                raise RuntimeError(f"Scene {index} speech is {spoken:.1f}s; increase --rate")
            subprocess.run([
                ffmpeg, "-y", "-loop", "1", "-i", str(image), "-i", str(audio),
                "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
                       "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=white,format=yuv420p",
                "-af", "apad", "-t", str(allotted), "-r", "30", "-c:v", "libx264",
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
    if abs(final_duration - TARGET_SECONDS) > 0.2:
        raise RuntimeError(f"Expected {TARGET_SECONDS}s, produced {final_duration:.2f}s")
    print(f"Narrated submission draft: {output}")
    print(f"Duration: {int(final_duration // 60)}:{int(final_duration % 60):02d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
