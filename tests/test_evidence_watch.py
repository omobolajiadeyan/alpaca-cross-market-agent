import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.evidence_watch import main


def test_evidence_watch_fails_honestly_when_cloud_secrets_are_missing(tmp_path, monkeypatch):
    for name in ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    assert main(["--allow-unconfigured", "--output-dir", str(tmp_path)]) == 0
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["status"] == "CONFIGURATION_REQUIRED"
    assert summary["broker_mutations"] is False
    assert not (tmp_path / "evidence-receipt.json").exists()


def test_evidence_watch_refuses_execution_authority(tmp_path, monkeypatch):
    for name in ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.setenv(name, "configured-for-boundary-test")
    monkeypatch.setenv("ALLOW_PAPER_EXECUTION", "true")
    with pytest.raises(SystemExit, match="refuses ALLOW_PAPER_EXECUTION=true"):
        main(["--output-dir", str(tmp_path)])


def test_evidence_watch_script_resolves_project_packages(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "evidence_watch.py"
    result = subprocess.run(
        [sys.executable, "-c",
         f"import runpy; runpy.run_path({str(script)!r}, run_name='evidence_watch_probe'); import agent"],
        cwd=tmp_path, capture_output=True, text=True, env={}, check=False,
    )
    assert result.returncode == 0
