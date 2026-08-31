import json

from agent.evidence_protocol import EvidenceReceiptBuilder, decision_scorecard
from demo.judge_fixture import judge_dashboard


def test_public_judge_fixture_is_complete_and_verifiable():
    dashboard = judge_dashboard()
    assert dashboard["fixture"] is True
    assert dashboard["contracts"] and dashboard["trades"] and dashboard["theses"]
    row = dashboard["contracts"][0]
    receipt = EvidenceReceiptBuilder().dumps(
        row["contract"], row["execution_status"], row["evaluation"],
        dashboard["trades"][0]["portfolio"],
    )
    assert EvidenceReceiptBuilder().verify(receipt)["valid"] is True
    assert {item["authorization"] for item in dashboard["contracts"]} == {
        "AUTHORIZED", "ABSTAIN",
    }
    for item in dashboard["contracts"]:
        receipt = EvidenceReceiptBuilder().dumps(item["contract"], item["execution_status"])
        assert EvidenceReceiptBuilder().verify(receipt)["valid"] is True


def test_public_judge_fixture_contains_no_credentials_or_broker_identifiers():
    encoded = json.dumps(judge_dashboard()).lower()
    forbidden = ("api_key", "secret_key", "account_id", "order_id", "@")
    assert not any(item in encoded for item in forbidden)


def test_decision_scorecard_separates_signal_from_execution_and_outcome():
    dashboard = judge_dashboard()
    abstained = next(item for item in dashboard["contracts"]
                     if item["authorization"] == "ABSTAIN")
    score = decision_scorecard(abstained["contract"], abstained["evaluation"])
    assert score["signal_quality"] == 80
    assert score["decision_stability"] == 100
    assert score["execution_quality"] < 100
    assert score["outcome_evidence"] == 100

    authorized = next(item for item in dashboard["contracts"]
                      if item["authorization"] == "AUTHORIZED")
    score = decision_scorecard(authorized["contract"])
    assert score["execution_quality"] == 100
    assert score["outcome_evidence"] is None
