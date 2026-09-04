"""Bundled public replay derived from a verified Alpaca paper workflow.

The fixture contains no account identifiers, credentials, order identifiers, or
broker-access capability. It is deliberately labeled as a replay in the UI.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy


def _reseal(payload, prefix="CS-DEMO"):
    payload.pop("decision_hash", None)
    payload.pop("contract_id", None)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    payload["decision_hash"] = hashlib.sha256(canonical.encode()).hexdigest()
    payload["contract_id"] = f"{prefix}-{payload['decision_hash'][:8].upper()}"
    return payload


def _sealed_contract():
    candidates = [
        {"title": "Rate expectations vs credit pricing", "score": 80.0,
         "repricing_market": "credit_spread", "direction": "WIDER",
         "explanation": "Hawkish front-end rates conflict with unusually resilient credit pricing."},
        {"title": "Equity fear vs credit complacency", "score": 68.0,
         "repricing_market": "credit_spread", "direction": "WIDER",
         "explanation": "Equity-option concern is not fully reflected in the credit proxy."},
        {"title": "Realized vs implied volatility", "score": 57.0,
         "repricing_market": "equity_volatility", "direction": "LOWER",
         "explanation": "Implied volatility remains above the recent realized-volatility regime."},
    ]
    checks = [
        {"name": "Net delta", "passed": True, "actual": 42.0, "limit": 5000,
         "detail": "Absolute portfolio delta stays below the configured cap"},
        {"name": "Net vega", "passed": True, "actual": 31.5, "limit": 2000,
         "detail": "Absolute portfolio vega stays below the configured cap"},
        {"name": "Margin utilization", "passed": True, "actual": .012, "limit": .30,
         "detail": "Defined loss divided by paper portfolio value"},
        {"name": "Option liquidity", "passed": False, "actual": 4, "limit": 10,
         "detail": "One proposed option leg had insufficient daily volume"},
        {"name": "Greek coverage", "passed": True,
         "actual": {"covered": 6, "total": 6, "complete": True}, "limit": "all legs",
         "detail": "Every proposed option leg had an Alpaca Greeks snapshot"},
    ]
    stress = {
        "method": "alpaca-greeks-delta-gamma-vega-v1",
        "greeks": {"delta": 42.0, "gamma": 3.1, "theta": -18.4, "vega": 31.5},
        "snapshot_coverage": {"covered": 6, "total": 6, "complete": True},
        "scenarios": [
            {"scenario": "Spot -5%", "estimated_pnl": -410.0},
            {"scenario": "Spot -3%", "estimated_pnl": -268.0},
            {"scenario": "Spot -1%", "estimated_pnl": -91.0},
            {"scenario": "Spot +1%", "estimated_pnl": 96.0},
            {"scenario": "Spot +3%", "estimated_pnl": 302.0},
            {"scenario": "Spot +5%", "estimated_pnl": 524.0},
            {"scenario": "IV -5%", "estimated_pnl": -157.5},
            {"scenario": "IV +5%", "estimated_pnl": 157.5},
            {"scenario": "One trading day decay", "estimated_pnl": -18.4},
        ],
        "worst_scenario_pnl": -410.0, "defined_max_loss": 1200.0,
        "symbols": ["HYG", "SPY", "TLT"], "passed": True,
        "note": "Sanitized Alpaca-Greeks replay. Defined spread maximum loss remains authoritative.",
    }
    payload = {
        "protocol_version": "SIGNAL-1.0", "created_at": "2026-08-30T14:35:00+00:00",
        "creator": "Omobolaji E Adeyan",
        "prediction": {"market": "credit_spread", "direction": "WIDER",
                       "minimum_move": "measurable directional move from sealed baseline",
                       "horizon_trading_days": 5,
                       "invalidation": "Credit strengthens while rate expectations remain hawkish."},
        "thesis": "Credit pricing has not fully absorbed tighter rate expectations; wait for executable liquidity before expressing the repricing.",
        "confidence_before_challenge": .72, "confidence_after_challenge": .64,
        "disagreement": {"score": 80.0, "primary": candidates[0], "candidates": candidates,
                          "method": "deterministic-cross-market-v1"},
        "stability": {"score": 1.0, "stable_cases": 10, "total_cases": 10,
                      "outcomes": [{"perturbation": f"bounded-{i + 1}", "leading_case": candidates[0]["title"],
                                    "stable": True} for i in range(10)],
                      "method": "bounded-perturbation-v1"},
        "falsification": {
            "strongest_counterargument": "Credit resilience may reflect sound balance sheets rather than delayed repricing.",
            "alternative_explanation": "The rate signal may already be absorbed through sector rotation.",
            "invalidation_condition": "Credit strengthens while rate expectations remain hawkish.",
            "confidence_adjustment": -.08,
        },
        "risk_assessment": {"passed": False, "checks": checks},
        "portfolio_stress": stress,
        "catalyst_context": {"classification": "SUPPORTED_CATALYST", "relevant_count": 2,
                             "articles": [{"headline": "Sanitized macro-policy catalyst",
                                           "symbols": ["SPY", "TLT"], "source": "Alpaca News"}],
                             "note": "Headlines provide context only and never bypass risk gates."},
        "portfolio": {}, "market_timestamp": "2026-08-30T14:30:00+00:00",
        "sealed_baseline_value": -1.25,
        "data_quality": {"all_live": True, "sources": {
            "equity_volatility": {"status": "live", "note": "Alpaca SPY option snapshot"},
            "treasury_curve": {"status": "live", "note": "U.S. Treasury par yields"},
            "credit": {"status": "live", "note": "Alpaca HYG/LQD/IEF bars"},
            "realized_volatility": {"status": "live", "note": "Computed from Alpaca SPY bars"},
            "rate_expectations": {"status": "live", "note": "Treasury 3M versus 1Y proxy"},
            "positioning": {"status": "live", "note": "Alpaca ATM option-volume proxy"},
        }},
        "authorization": "ABSTAIN",
        "authorization_reasons": ["deterministic execution-risk assessment failed: option liquidity"],
    }
    return _reseal(payload), stress, checks


def judge_dashboard():
    """Return the complete presentation model used only in public demo mode."""
    contract, stress, checks = _sealed_contract()
    recovery = {"state": "PREFLIGHTED",
                "statuses": {"primary_trade": "not_submitted", "secondary_trade": "not_submitted",
                             "hedge": "not_submitted"},
                "filled_roles": [], "actions": ["No broker exposure exists."],
                "automatic_orders": False}
    portfolio = {
        "primary_trade": {"symbol": "HYG", "strategy": "call_debit_spread", "stance": "bearish credit",
                          "execution": {"submitted": False, "status": "not_submitted"}},
        "secondary_trade": {"symbol": "SPY", "strategy": "put_debit_spread", "stance": "defensive",
                            "execution": {"submitted": False, "status": "not_submitted"}},
        "hedge": {"symbol": "TLT", "strategy": "put_debit_spread", "stance": "rates hedge",
                  "execution": {"submitted": False, "status": "not_submitted"}},
        "portfolio_stress": stress, "execution_risk": {"passed": False, "checks": checks},
        "execution_recovery": recovery, "catalyst_context": contract["catalyst_context"],
        "risk_assessment": {"passed": False, "checks": checks},
    }
    evaluation = {"contract_id": contract["contract_id"], "evaluated_at": "2026-08-30T14:40:00+00:00",
                  "before": -1.25, "after": -1.42, "direction_correct": True,
                  "normalized_market_move": -.136,
                  "counterfactuals": {"agent_direction_proxy": .136,
                                      "inverse_direction_proxy": -.136, "cash_proxy": 0.0},
                  "note": "Illustrative sanitized outcome demonstrates the predetermined scoring method."}
    thesis = {"id": 1, "timestamp": contract["created_at"], "thesis": contract["thesis"],
              "rationale": "Cross-market evidence supported the thesis, while execution evidence required abstention.",
              "confidence": .64, "repricing_signals": [contract["prediction"]], "market_state": {},
              "evaluated": 1, "hit_rate": 1.0, "evaluated_at": evaluation["evaluated_at"],
              "evaluation_detail": evaluation}
    trade = {"id": 1, "timestamp": contract["created_at"], "thesis_id": 1,
             "strategy": "governed three-leg options portfolio", "portfolio": portfolio, "status": "rejected"}
    row = {"contract_id": contract["contract_id"], "decision_hash": contract["decision_hash"],
           "created_at": contract["created_at"], "authorization": "ABSTAIN", "contract": contract,
           "execution_status": "abstained", "trade_id": 1, "evaluated": 1,
           "evaluation_json": json.dumps(evaluation), "evaluation": evaluation}

    authorized_contract = deepcopy(contract)
    authorized_contract.update({
        "created_at": "2026-08-25T15:40:00+00:00",
        "market_timestamp": "2026-08-25T15:35:00+00:00",
        "thesis": "Equity-option fear was not fully reflected in credit; executable liquidity supported a defined-risk paper expression.",
        "authorization": "AUTHORIZED", "authorization_reasons": [],
    })
    authorized_checks = deepcopy(checks)
    for item in authorized_checks:
        item["passed"] = True
        if item["name"] == "Option liquidity":
            item["actual"] = 120
    authorized_contract["risk_assessment"] = {"passed": True, "checks": authorized_checks}
    authorized_contract = _reseal(authorized_contract, "CS-VERIFIED")
    filled_portfolio = deepcopy(portfolio)
    for role in ("primary_trade", "secondary_trade", "hedge"):
        filled_portfolio[role]["execution"] = {"submitted": True, "status": "filled"}
    filled_portfolio["execution_risk"] = {"passed": True, "checks": authorized_checks}
    filled_portfolio["risk_assessment"] = {"passed": True, "checks": authorized_checks}
    filled_portfolio["execution_recovery"] = {
        "state": "RECONCILED", "statuses": {role: "filled" for role in
        ("primary_trade", "secondary_trade", "hedge")}, "filled_roles":
        ["primary_trade", "secondary_trade", "hedge"],
        "actions": ["Record final fills and release the recovery lock."],
        "automatic_orders": False,
    }
    authorized_thesis = {**thesis, "id": 2, "timestamp": authorized_contract["created_at"],
                         "thesis": authorized_contract["thesis"], "evaluated": 0,
                         "hit_rate": None, "evaluated_at": None, "evaluation_detail": None}
    filled_trade = {"id": 2, "timestamp": authorized_contract["created_at"], "thesis_id": 2,
                    "strategy": "governed three-leg options portfolio",
                    "portfolio": filled_portfolio, "status": "submitted"}
    authorized_row = {"contract_id": authorized_contract["contract_id"],
                      "decision_hash": authorized_contract["decision_hash"],
                      "created_at": authorized_contract["created_at"], "authorization": "AUTHORIZED",
                      "contract": authorized_contract, "execution_status": "filled", "trade_id": 2,
                      "evaluated": 0, "evaluation_json": None}
    latest_cycle = {"market_state": {"data_quality": contract["data_quality"]},
                    "thesis": {"thesis": contract["thesis"], "rationale": thesis["rationale"],
                               "confidence_overall": .64},
                    "portfolio": portfolio, "decision_contract": contract}
    positions = [{
        "id": 1, "trade_id": 2, "contract_id": authorized_contract["contract_id"],
        "role": "primary_trade", "underlying_symbol": "HYG",
        "strategy": "call_debit_spread", "spread_type": "debit", "qty": 1,
        "multiplier": 100, "opening_legs": [
            {"symbol": "HYG_OPTION_NEAR_REDACTED", "side": "buy"},
            {"symbol": "HYG_OPTION_FAR_REDACTED", "side": "sell"},
        ],
        "entry_price": .80,
        "max_profit": 420.0, "max_loss": 80.0,
        "take_profit_target": 210.0, "stop_loss_limit": 40.0,
        "max_holding_days": 5, "exit_before_expiry_days": 2,
        "expiration_date": "2026-09-25", "opened_at": "2026-08-25T15:41:00+00:00",
        "status": "CLOSED", "exit_reason": "TAKE_PROFIT",
        "closed_at": "2026-08-27T15:05:00+00:00", "last_mark": 2.90,
        "last_pnl": 210.0, "last_checked_at": "2026-08-27T15:05:00+00:00",
        "realized_pnl": 210.0, "evidence_label": "illustrative policy demonstration; not broker fill evidence",
    }]
    position_events = [
        {"id": 3, "position_id": 1, "timestamp": "2026-08-27T15:05:00+00:00",
         "event_type": "EXIT_FILLED", "state_before": "EXIT_PENDING", "state_after": "CLOSED",
         "reason": "TAKE_PROFIT", "detail": {"evidence_label": "illustrative policy demonstration; not broker fill evidence"}},
        {"id": 2, "position_id": 1, "timestamp": "2026-08-27T15:04:00+00:00",
         "event_type": "EXIT_SUBMITTED", "state_before": "OPEN", "state_after": "EXIT_PENDING",
         "reason": "TAKE_PROFIT", "detail": {"atomic_multileg": True}},
        {"id": 1, "position_id": 1, "timestamp": "2026-08-25T15:41:00+00:00",
         "event_type": "POSITION_REGISTERED", "state_before": None, "state_after": "OPEN",
         "reason": "Exit policy sealed when the entry was logged.", "detail": {}},
    ]
    return {"theses": [thesis, authorized_thesis], "trades": [trade, filled_trade],
            "contracts": [row, authorized_row],
            "positions": positions, "position_events": position_events,
            "position_performance": {
                "by_status": {"CLOSED": 1}, "closed_positions": 1,
                "wins": 1, "losses": 0, "win_rate": 1.0,
                "realized_pnl": 210.0, "average_pnl": 210.0,
                "exit_reasons": {"TAKE_PROFIT": 1},
                "evidence_label": "illustrative policy demonstration; not broker fill evidence",
            },
            "track_record": {"theses_scored": 1, "theses_pending": 1, "average_hit_rate": 1.0},
            "latest_cycle": latest_cycle, "fixture": True}
