"""Run one read-only CrossSignal evidence cycle and export judge-safe artifacts."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


REQUIRED_SECRETS = ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY", "ANTHROPIC_API_KEY")


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")


def write_summary(path, summary):
    lines = [
        "# CrossSignal Evidence Watch",
        "",
        f"- Status: **{summary['status']}**",
        f"- Mode: `{summary['mode']}`",
        f"- Timestamp: `{summary['timestamp']}`",
        "- Broker mutations: **disabled**",
    ]
    if summary.get("contract_id"):
        lines.extend([
            f"- Contract: `{summary['contract_id']}`",
            f"- Authorization: **{summary['authorization']}**",
            f"- Signal quality: **{summary['scorecard']['signal_quality']}/100**",
            f"- Decision stability: **{summary['scorecard']['decision_stability']}/100**",
            f"- Execution quality: **{summary['scorecard']['execution_quality']}/100**",
        ])
    if summary.get("missing_secrets"):
        lines.extend(["", "Live evidence was not fabricated. Configure the listed repository secrets to enable the connected read-only cycle."])
    path.write_text("\n".join(lines) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="evidence-watch-output")
    parser.add_argument("--allow-unconfigured", action="store_true")
    args = parser.parse_args(argv)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    missing = [name for name in REQUIRED_SECRETS if not os.getenv(name)]
    if missing:
        summary = {"status": "CONFIGURATION_REQUIRED", "mode": "read-only-live-evidence",
                   "timestamp": timestamp, "missing_secrets": missing,
                   "broker_mutations": False}
        write_json(output / "summary.json", summary)
        write_summary(output / "summary.md", summary)
        print("Evidence Watch configuration required: " + ", ".join(missing))
        return 0 if args.allow_unconfigured else 2

    if os.getenv("ALLOW_PAPER_EXECUTION", "false").lower() in ("1", "true", "yes"):
        raise SystemExit("Evidence Watch refuses ALLOW_PAPER_EXECUTION=true")
    if os.getenv("PUBLIC_DEMO_MODE", "false").lower() in ("1", "true", "yes"):
        raise SystemExit("Evidence Watch requires connected preview mode, not the public fixture")

    from agent.evidence_protocol import EvidenceReceiptBuilder, decision_scorecard
    from live.cross_market_agent import CrossMarketAgent

    agent = CrossMarketAgent()
    try:
        result = agent.run(execute=False)
    finally:
        agent.close()
    if not result or not result.get("decision_contract"):
        raise SystemExit("Evidence Watch completed without a sealed Decision Contract")

    contract = result["decision_contract"]
    portfolio = result.get("portfolio") or {}
    scorecard = decision_scorecard(contract)
    receipt = EvidenceReceiptBuilder().build(contract, "preview", portfolio=portfolio)
    summary = {
        "status": "EVIDENCE_SEALED", "mode": "read-only-live-evidence",
        "timestamp": timestamp, "contract_id": contract["contract_id"],
        "decision_hash": contract["decision_hash"],
        "authorization": contract["authorization"], "scorecard": scorecard,
        "broker_mutations": False,
        "note": "Workflow evidence is an analysis artifact, not a submitted order.",
    }
    write_json(output / "evidence-receipt.json", receipt)
    write_json(output / "summary.json", summary)
    write_summary(output / "summary.md", summary)
    print(f"Evidence Watch sealed {contract['contract_id']}: {contract['authorization']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
