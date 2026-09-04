#!/usr/bin/env python3
"""Capture screenshots and extracted text across every tab of the public
judge replay, for building a fuller narrated submission video."""

from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "recording-output" / "full-tour"
SHOTS = OUT_DIR / "screenshots"
BASE_URL = os.getenv("CROSSSIGNAL_CAPTURE_URL", "http://localhost:8501")


def snap(page, name: str):
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=False)


def text_of(page, selector: str) -> str:
    try:
        return page.locator(selector).first.inner_text(timeout=3000).strip()
    except Exception:
        return ""


def main_text(page) -> str:
    for selector in ('[data-testid="stMain"]', '[data-testid="stAppViewContainer"]', "main", "body"):
        try:
            return page.locator(selector).first.inner_text(timeout=3000)[:4000]
        except Exception:
            continue
    return ""


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    extracted: dict[str, object] = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        page = context.new_page()
        page.goto(BASE_URL, wait_until="networkidle", timeout=60_000)
        # Works in both the public judge replay and controlled local mode.
        page.get_by_text("A complete decision, not another signal", exact=False).wait_for(timeout=30_000)
        page.wait_for_timeout(800)
        snap(page, "00-landing")
        tablist = page.locator('[role="tablist"]').first
        first_tab = page.locator('[role="tab"]').first
        extracted["tablist_html"] = tablist.evaluate("element => element.outerHTML")
        extracted["tablist_style"] = tablist.evaluate(
            "element => ({background:getComputedStyle(element).backgroundColor, padding:getComputedStyle(element).padding, position:getComputedStyle(element).position})"
        )
        extracted["first_tab_style"] = first_tab.evaluate(
            "element => ({background:getComputedStyle(element).backgroundColor, color:getComputedStyle(element).color, padding:getComputedStyle(element).padding})"
        )

        # --- Decision case tab ---
        page.get_by_role("tab", name="Decision case").click()
        page.wait_for_timeout(1200)
        extracted["component_frames"] = [
            {
                "url": frame.url,
                "text": frame.locator("body").inner_text()[:1000],
                "html": frame.locator("body").inner_html()[:2500],
            }
            for frame in page.frames[1:]
        ]
        select = page.locator('[data-testid="stSelectbox"]').first
        options_text = select.inner_text()
        extracted["decision_case_selector_text"] = options_text
        page.get_by_text("Decision intelligence scorecard").scroll_into_view_if_needed()
        page.wait_for_timeout(800)
        snap(page, "01-decision-scorecard")
        extracted["decision_case_metrics"] = [
            text_of(page, f'[data-testid="stMetric"]:nth-of-type({i})') for i in range(1, 5)
        ]
        extracted["decision_case_metric_values"] = page.locator('[data-testid="stMetricValue"]').all_inner_texts()
        extracted["decision_case_metric_labels"] = page.locator('[data-testid="stMetricLabel"]').all_inner_texts()

        page.get_by_text("Decision Replay courtroom").scroll_into_view_if_needed()
        page.wait_for_timeout(800)
        snap(page, "02-decision-replay")

        # Try to switch to an ABSTAIN case if one exists in the selector
        try:
            select_el = page.get_by_role("combobox").first
            select_el.click()
            page.wait_for_timeout(400)
            abstain_option = page.get_by_text("ABSTAIN", exact=False).first
            if abstain_option.is_visible(timeout=1500):
                abstain_option.click()
                page.wait_for_timeout(1200)
                page.get_by_text("Decision intelligence scorecard").scroll_into_view_if_needed()
                page.wait_for_timeout(800)
                snap(page, "03-decision-abstain-case")
                extracted["abstain_case_metric_values"] = page.locator('[data-testid="stMetricValue"]').all_inner_texts()
        except Exception as exc:
            extracted["abstain_case_error"] = str(exc)

        # Proof-of-abstention live toggle
        try:
            page.get_by_text("Prove the agent can refuse").scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            page.get_by_text("Simulate stale or fallback evidence").click()
            page.wait_for_timeout(1200)
            snap(page, "04-proof-of-abstention")
            extracted["abstention_banner"] = text_of(page, "text=ABSTAIN")
        except Exception as exc:
            extracted["proof_of_abstention_error"] = str(exc)

        # --- Run agent tab ---
        page.get_by_role("tab", name="Run agent").click()
        page.wait_for_timeout(1000)
        snap(page, "05-run-agent")
        try:
            page.get_by_role("button", name="Replay sanitized judge case").click()
            page.get_by_text("Sanitized case replayed", exact=False).wait_for(timeout=15_000)
            page.wait_for_timeout(800)
            snap(page, "06-run-agent-replayed")
        except Exception as exc:
            extracted["run_agent_replay_error"] = str(exc)

        # --- Executive overview tab ---
        page.get_by_role("tab", name="Executive overview").click()
        page.wait_for_timeout(1200)
        snap(page, "07-executive-overview")
        extracted["executive_overview_text"] = main_text(page)

        # --- Track record tab ---
        page.get_by_role("tab", name="Track record").click()
        page.wait_for_timeout(1200)
        snap(page, "08-track-record")
        extracted["track_record_text"] = main_text(page)

        # --- Readiness tab ---
        page.get_by_role("tab", name="Readiness").click()
        page.wait_for_timeout(1200)
        snap(page, "09-readiness")
        extracted["readiness_text"] = main_text(page)

        # --- Security tab ---
        page.get_by_role("tab", name="Security").click()
        page.wait_for_timeout(1200)
        snap(page, "10-security")
        extracted["security_text"] = main_text(page)

        # --- Methodology tab ---
        page.get_by_role("tab", name="Methodology").click()
        page.wait_for_timeout(1200)
        snap(page, "11-methodology")
        extracted["methodology_text"] = main_text(page)

        context.close()

        mobile_context = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=1,
            is_mobile=True,
        )
        mobile_page = mobile_context.new_page()
        mobile_page.goto(BASE_URL, wait_until="networkidle", timeout=60_000)
        mobile_page.get_by_text("A complete decision, not another signal", exact=False).wait_for(timeout=30_000)
        mobile_page.wait_for_timeout(800)
        mobile_page.screenshot(path=str(SHOTS / "12-mobile-landing.png"), full_page=False)
        mobile_page.get_by_role("tab", name="Decision case").click()
        mobile_page.wait_for_timeout(1200)
        mobile_page.get_by_text("One decision. Every claim inspectable.").scroll_into_view_if_needed()
        mobile_page.wait_for_timeout(500)
        mobile_page.screenshot(path=str(SHOTS / "13-mobile-decision.png"), full_page=False)
        mobile_page.get_by_text("Inspect a market disagreement", exact=True).scroll_into_view_if_needed()
        mobile_page.wait_for_timeout(500)
        mobile_page.screenshot(path=str(SHOTS / "14-mobile-controls.png"), full_page=False)
        mobile_context.close()
        browser.close()

    (OUT_DIR / "extracted.json").write_text(json.dumps(extracted, indent=2))
    print(f"Wrote screenshots to {SHOTS}")
    print(f"Wrote extracted text to {OUT_DIR / 'extracted.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
