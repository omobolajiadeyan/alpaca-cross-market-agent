"""Build the judge-facing CrossSignal upload bundle with verified checksums."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "submission"
PACKAGE = SUBMISSION / "CrossSignal-Final-Submission-Package"
LEGACY_PACKAGE = SUBMISSION / "final-package"
DEFAULT_VIDEO = ROOT / "recording-output" / "CrossSignal-Position-Lifecycle-Narrated.mp4"

PACKAGE_FILES = {
    ROOT / "assets" / "crosssignal-hackathon-cover.png": "CrossSignal-Cover.png",
    ROOT / "assets" / "crosssignal-logo-mark.png": "CrossSignal-Logo-Mark.png",
    ROOT / "assets" / "crosssignal-logo-lockup-light.png": "CrossSignal-Logo-Light.png",
    ROOT / "assets" / "crosssignal-logo.svg": "CrossSignal-Logo.svg",
    SUBMISSION / "CrossSignal-Hackathon-Pitch-Final.pdf": "CrossSignal-Hackathon-Pitch-Final.pdf",
    SUBMISSION / "CrossSignal-Hackathon-Pitch-Final.pptx": "CrossSignal-Hackathon-Pitch-Final.pptx",
    SUBMISSION / "CrossSignal-One-Page-Writeup.pdf": "CrossSignal-One-Page-Writeup.pdf",
    SUBMISSION / "FINAL-PACKAGE-README.md": "FINAL-PACKAGE-README.md",
    SUBMISSION / "FINAL_VIDEO_SCRIPT.md": "FINAL_VIDEO_SCRIPT.md",
    SUBMISSION / "JUDGE_NO_TRADE_MEMO.md": "JUDGE_NO_TRADE_MEMO.md",
    SUBMISSION / "Latest-Run-Evidence.json": "Latest-Run-Evidence.json",
    SUBMISSION / "SUBMISSION_FORM_COPY.md": "SUBMISSION_FORM_COPY.md",
    SUBMISSION / "SUBMISSION-CHECKLIST.md": "SUBMISSION-CHECKLIST.md",
    ROOT / "REQUIREMENTS_AUDIT.md": "REQUIREMENTS-AUDIT.md",
    SUBMISSION / "research" / "CrossSignal-Competitive-Research-and-Enhancement-Report.pdf":
        "CrossSignal-Competitive-Research-and-Enhancement-Report.pdf",
    SUBMISSION / "research" / "report-source.md": "RESEARCH-REPORT-SOURCE.md",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--video", type=Path, default=DEFAULT_VIDEO,
        help=f"Final MP4 (default: {DEFAULT_VIDEO.relative_to(ROOT)})",
    )
    args = parser.parse_args()

    PACKAGE.mkdir(parents=True, exist_ok=True)
    missing = [str(source) for source in PACKAGE_FILES if not source.exists()]
    if missing:
        raise FileNotFoundError("Missing package assets:\n" + "\n".join(missing))
    for source, destination in PACKAGE_FILES.items():
        shutil.copy2(source, PACKAGE / destination)

    packaged_video = PACKAGE / "CrossSignal-Submission-Video.mp4"
    source_video = args.video.resolve(strict=True)
    shutil.copy2(source_video, packaged_video)

    checksum_path = PACKAGE / "CHECKSUMS.sha256"
    package_members = sorted(
        path for path in PACKAGE.iterdir()
        if path.is_file() and path.name != checksum_path.name
    )
    checksum_path.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in package_members),
        encoding="utf-8",
    )
    package_members.append(checksum_path)

    zip_path = SUBMISSION / "CrossSignal-Final-Submission-Package.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as archive:
        for path in sorted(package_members):
            archive.write(path, path.name)

    # Keep the historical path synchronized for existing editor tabs while the
    # descriptive directory above remains the authoritative source.
    LEGACY_PACKAGE.mkdir(parents=True, exist_ok=True)
    for path in package_members:
        shutil.copy2(path, LEGACY_PACKAGE / path.name)

    print(f"Package directory: {PACKAGE}")
    print(f"ZIP: {zip_path}")
    print(f"Files: {len(package_members)}")
    print("Video included:", packaged_video)


if __name__ == "__main__":
    main()
