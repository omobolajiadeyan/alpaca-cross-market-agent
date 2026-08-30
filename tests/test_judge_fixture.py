import json

from agent.evidence_protocol import EvidenceReceiptBuilder
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


def test_public_judge_fixture_contains_no_credentials_or_broker_identifiers():
    encoded = json.dumps(judge_dashboard()).lower()
    forbidden = ("api_key", "secret_key", "account_id", "order_id", "@")
    assert not any(item in encoded for item in forbidden)
