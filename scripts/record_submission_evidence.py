#!/usr/bin/env python3
"""Record a judge-safe CrossSignal evidence tour.

The recorder forces Streamlit into the bundled public replay and disables broker
mutations. It never reads .env, downloads receipts, or contacts Alpaca.
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
SECRET_ENV_NAMES = (
    "APCA_API_KEY_ID", "APCA_API_SECRET_KEY", "ANTHROPIC_API_KEY",
    "ALPACA_API_KEY", "ALPACA_API_KEY_ID", "ALPACA_SECRET_KEY",
    "ALPACA_API_SECRET_KEY",
)


def wait_for_app(url: str, timeout: int = 45) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return
        except (URLError, TimeoutError):
            time.sleep(0.5)
    raise RuntimeError(f"Streamlit did not become ready at {url}")


def recording_environment(source: dict[str, str] | None = None) -> dict[str, str]:
    """Return a public-replay-only child environment with credentials removed."""
    env = dict(os.environ if source is None else source)
    for name in SECRET_ENV_NAMES:
        env.pop(name, None)
    env.update({"PUBLIC_DEMO_MODE": "true", "ALLOW_PAPER_EXECUTION": "false"})
    return env


def available_local_port() -> int:
    """Return an unused loopback port for an isolated local capture."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="recording-output")
    parser.add_argument("--base-url", default="http://127.0.0.1:8501")
    parser.add_argument("--no-launch", action="store_true",
                        help="Capture an already-running public-demo instance")
    parser.add_argument("--headed", action="store_true",
                        help="Show the browser while recording")
    args = parser.parse_args()

    output = (ROOT / args.output_dir).resolve()
    screenshots = output / "screenshots"
    videos = output / "video"
    screenshots.mkdir(parents=True, exist_ok=True)
    videos.mkdir(parents=True, exist_ok=True)

    server = None
    capture_url = args.base_url
    if not args.no_launch:
        # The public fixture needs no secrets. Remove current and legacy names
        # rather than merely relying on public mode not to use their values.
        env = recording_environment()
        port = available_local_port()
        capture_url = f"http://127.0.0.1:{port}"
        server = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "app.py",
             "--server.headless=true", "--server.address=127.0.0.1",
             f"--server.port={port}", "--browser.gatherUsageStats=false"],
            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
        )

    try:
        wait_for_app(capture_url)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not args.headed)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1,
                record_video_dir=str(videos),
                record_video_size={"width": 1920, "height": 1080},
            )
            page = context.new_page()
            page.goto(capture_url, wait_until="networkidle", timeout=60_000)
            page.get_by_text("PUBLIC JUDGE MODE", exact=False).wait_for(timeout=30_000)
            page.screenshot(path=str(screenshots / "01-landing.png"), full_page=False)

            page.get_by_role("tab", name="Decision case").click()
            page.get_by_text("Decision intelligence scorecard").scroll_into_view_if_needed()
            page.wait_for_timeout(1_500)
            page.screenshot(path=str(screenshots / "02-scorecard.png"), full_page=False)

            page.get_by_text("Decision Replay courtroom").scroll_into_view_if_needed()
            page.wait_for_timeout(1_500)
            page.screenshot(path=str(screenshots / "03-decision-replay.png"), full_page=False)

            page.get_by_text("Prove the agent can refuse").scroll_into_view_if_needed()
            page.get_by_text("Simulate stale or fallback evidence").click()
            page.wait_for_timeout(1_500)
            page.screenshot(path=str(screenshots / "04-proof-of-abstention.png"), full_page=False)

            page.get_by_role("tab", name="Run agent").click()
            page.get_by_role("button", name="Replay sanitized judge case").click()
            page.get_by_text("Sanitized case replayed", exact=False).wait_for(timeout=15_000)
            page.screenshot(path=str(screenshots / "05-read-only-replay.png"), full_page=False)

            page.get_by_role("tab", name="Track record").click()
            page.wait_for_timeout(1_500)
            page.screenshot(path=str(screenshots / "06-track-record.png"), full_page=False)

            page.get_by_role("tab", name="Security").click()
            page.wait_for_timeout(1_500)
            page.screenshot(path=str(screenshots / "07-security-boundary.png"), full_page=False)

            page.wait_for_timeout(1_000)
            context.close()  # Finalizes Playwright's .webm recording.
            browser.close()

        print(f"Evidence recording written to {output}")
        print("Broker mutations remained disabled; only the sanitized fixture was used.")
        return 0
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
