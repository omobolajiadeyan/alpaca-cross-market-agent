"""Judge-visible evidence, stress and recovery primitives for CrossSignal."""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone

from config import RISK_GATES, MAX_MARGIN_UTILIZATION
from security.controls import redact, sanitize_external_text


GREEKS = ("delta", "gamma", "theta", "vega")


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class PortfolioStressEngine:
    """Aggregate Alpaca option Greeks and produce transparent local shocks."""

    SPOT_SHOCKS = (-0.05, -0.03, -0.01, 0.01, 0.03, 0.05)
    IV_SHOCKS = (-0.05, 0.05)

    def analyze(self, preflights):
        totals = {name: 0.0 for name in GREEKS}
        covered = total = 0
        max_loss = 0.0
        symbols = set()
        exposures = []
        for role, spread in preflights.items():
            max_loss += _float(spread.get("max_loss"))
            symbols.update(spread.get("underlyings", []))
            spot = _float(spread.get("underlying_price"))
            quantity = _float(spread.get("qty"), 1.0) * 100
            directions = {leg.get("symbol"): 1 if leg.get("side") == "buy" else -1
                          for leg in spread.get("order_legs", [])}
            for symbol, snapshot in spread.get("snapshots", {}).items():
                total += 1
                greeks = (snapshot or {}).get("greeks") or {}
                if greeks:
                    covered += 1
                sign = directions.get(symbol, 0)
                for name in GREEKS:
                    totals[name] += sign * quantity * _float(greeks.get(name))
                exposures.append({"role": role, "symbol": symbol, "spot": spot,
                                  "sign": sign, "quantity": quantity, "greeks": greeks})

        scenarios = []
        for shock in self.SPOT_SHOCKS:
            pnl = 0.0
            for item in exposures:
                move = item["spot"] * shock
                greeks = item["greeks"]
                pnl += item["sign"] * item["quantity"] * (
                    _float(greeks.get("delta")) * move
                    + .5 * _float(greeks.get("gamma")) * move ** 2
                )
            scenarios.append({"scenario": f"Spot {shock:+.0%}", "estimated_pnl": round(pnl, 2)})
        for shock in self.IV_SHOCKS:
            # Alpaca vega is interpreted per one volatility point; ±5% means five points.
            scenarios.append({"scenario": f"IV {shock:+.0%}",
                              "estimated_pnl": round(totals["vega"] * shock * 100, 2)})
        scenarios.append({"scenario": "One trading day decay",
                          "estimated_pnl": round(totals["theta"], 2)})

        worst = min((row["estimated_pnl"] for row in scenarios), default=0.0)
        return {
            "method": "alpaca-greeks-delta-gamma-vega-v1",
            "greeks": {name: round(value, 4) for name, value in totals.items()},
            "snapshot_coverage": {"covered": covered, "total": total,
                                  "complete": total > 0 and covered == total},
            "scenarios": scenarios,
            "worst_scenario_pnl": worst,
            "defined_max_loss": round(max_loss, 2),
            "symbols": sorted(symbols),
            "passed": total > 0 and covered == total and abs(worst) <= max_loss,
            "note": "Local first-order stress estimate; defined spread maximum loss remains authoritative.",
        }


class ExecutionRiskGate:
    """Enforce every configured exposure, liquidity, margin and drawdown policy."""

    def assess(self, stress, preflights, account, portfolio_history=None):
        checks = []

        def add(name, passed, actual, limit, detail):
            checks.append({"name": name, "passed": bool(passed), "actual": actual,
                           "limit": limit, "detail": detail})

        greeks = stress.get("greeks", {})
        delta = abs(_float(greeks.get("delta")))
        vega = abs(_float(greeks.get("vega")))
        theta = _float(greeks.get("theta"))
        add("Net delta", delta <= RISK_GATES["max_delta"], delta, RISK_GATES["max_delta"],
            "Absolute portfolio delta must stay below the configured cap")
        add("Net vega", vega <= RISK_GATES["max_vega"], vega, RISK_GATES["max_vega"],
            "Absolute portfolio vega must stay below the configured cap")
        add("Net theta", theta >= RISK_GATES["min_theta"], theta, RISK_GATES["min_theta"],
            "Portfolio theta must stay above the configured floor")

        portfolio_value = _float(account.get("portfolio_value"))
        margin_ratio = stress.get("defined_max_loss", 0) / portfolio_value if portfolio_value else 1.0
        margin_cap = min(MAX_MARGIN_UTILIZATION, RISK_GATES["margin_utilization_cap"])
        add("Margin utilization", margin_ratio <= margin_cap, round(margin_ratio, 4), margin_cap,
            "Defined loss divided by current portfolio value")

        volumes, spreads = [], []
        for spread in preflights.values():
            for symbol, snapshot in spread.get("snapshots", {}).items():
                volume = _float((snapshot.get("dailyBar") or {}).get("v"))
                volumes.append(volume)
                quote = spread.get("quotes", {}).get(symbol, {})
                bid, ask = _float(quote.get("bid")), _float(quote.get("ask"))
                midpoint = (bid + ask) / 2
                spreads.append((ask - bid) / midpoint if midpoint > 0 else 1.0)
        min_volume = min(volumes, default=0)
        max_spread = max(spreads, default=1.0)
        add("Option liquidity", min_volume >= RISK_GATES["min_volume"], min_volume,
            RISK_GATES["min_volume"], "Minimum daily volume across proposed option legs")
        add("Bid-ask quality", max_spread <= RISK_GATES["bid_ask_spread_limit"],
            round(max_spread, 4), RISK_GATES["bid_ask_spread_limit"],
            "Maximum relative bid-ask spread across proposed option legs")

        equity = [_float(item) for item in (portfolio_history or []) if _float(item) > 0]
        peak = max(equity, default=portfolio_value)
        current = equity[-1] if equity else portfolio_value
        drawdown = current - peak
        add("Daily drawdown", drawdown >= RISK_GATES["daily_drawdown_limit"], drawdown,
            RISK_GATES["daily_drawdown_limit"], "Current equity minus observed portfolio peak")
        add("Maximum drawdown", drawdown >= RISK_GATES["max_drawdown_limit"], drawdown,
            RISK_GATES["max_drawdown_limit"], "Current equity minus observed portfolio peak")
        add("Greek coverage", stress.get("snapshot_coverage", {}).get("complete", False),
            stress.get("snapshot_coverage", {}), "all legs", "Every option leg must have Alpaca Greeks")
        return {"passed": all(item["passed"] for item in checks), "checks": checks,
                "method": "execution-risk-gates-v1"}


class CatalystClassifier:
    """Classify whether fresh Alpaca news explains the selected disagreement."""

    def classify(self, articles, symbols=("SPY", "HYG", "TLT")):
        articles = articles or []
        symbol_set = set(symbols)
        relevant = []
        for article in articles:
            article_symbols = set(article.get("symbols") or [])
            if article_symbols & symbol_set:
                relevant.append({
                    "headline": sanitize_external_text(
                        article.get("headline") or article.get("title") or "Untitled catalyst"),
                    "symbols": sorted(article_symbols & symbol_set),
                    "created_at": article.get("created_at") or article.get("updated_at"),
                    "source": article.get("source", "Alpaca News"),
                })
        return {
            "classification": "SUPPORTED_CATALYST" if relevant else "UNEXPLAINED_DISAGREEMENT",
            "relevant_count": len(relevant),
            "articles": relevant[:5],
            "note": "Headlines provide context only and never bypass deterministic risk gates.",
        }


class ExecutionRecoveryPlanner:
    """Turn broker lifecycle states into an explicit, non-silent recovery plan."""

    TERMINAL_SUCCESS = {"filled"}
    ACTIVE = {"new", "accepted", "pending_new", "partially_filled", "submitted"}

    def assess(self, executions):
        statuses = {role: (item or {}).get("status", "not_submitted")
                    for role, item in executions.items()}
        filled = [role for role, status in statuses.items() if status in self.TERMINAL_SUCCESS]
        active = [role for role, status in statuses.items() if status in self.ACTIVE]
        failed = [role for role, status in statuses.items()
                  if status in {"rejected", "canceled", "expired", "unknown", "not_submitted"}]
        if len(filled) == len(statuses) and statuses:
            state, actions = "RECONCILED", ["Record final fills and release the recovery lock."]
        elif filled and (active or failed):
            state = "RECOVERY_REQUIRED"
            actions = ["Block new portfolio submissions.", "Cancel remaining open orders.",
                       "Recalculate risk from actual positions.",
                       "Require explicit paper-only approval before closing or hedging exposure."]
        elif active:
            state, actions = "MONITORING", ["Poll broker lifecycle until terminal state."]
        elif failed:
            state, actions = "STOPPED", ["Do not retry automatically; inspect broker rejection evidence."]
        else:
            state, actions = "PREFLIGHTED", ["No broker exposure exists."]
        return {"state": state, "statuses": statuses, "filled_roles": filled,
                "actions": actions, "automatic_orders": False}


class PaperRecoveryExecutor:
    """Perform approved cancellation/closure actions only in a paper environment."""

    def execute(self, plan, executions, broker, *, approved=False, paper_mode=True,
                positions_to_close=None):
        if not approved:
            return {"executed": False, "state": "AWAITING_APPROVAL", "actions": []}
        if not paper_mode:
            return {"executed": False, "state": "BLOCKED_LIVE_ACCOUNT", "actions": []}
        if plan.get("state") != "RECOVERY_REQUIRED":
            return {"executed": False, "state": "NO_RECOVERY_REQUIRED", "actions": []}
        actions, errors = [], []
        for role, execution in executions.items():
            if execution.get("status") in ExecutionRecoveryPlanner.ACTIVE and execution.get("order_id"):
                try:
                    broker.cancel_order(execution["order_id"])
                    actions.append({"action": "cancel_order", "role": role,
                                    "order_id": execution["order_id"]})
                except Exception as exc:
                    errors.append({"action": "cancel_order", "role": role, "error": str(exc)})
        for position in positions_to_close or []:
            try:
                broker.close_position(position["symbol"], position.get("qty"))
                actions.append({"action": "close_position", "symbol": position["symbol"],
                                "qty": position.get("qty")})
            except Exception as exc:
                errors.append({"action": "close_position", "symbol": position.get("symbol"),
                               "error": str(exc)})
        return {"executed": bool(actions), "state": "RECOVERY_SUBMITTED" if actions else "RECOVERY_FAILED",
                "actions": actions, "errors": errors, "paper_mode": True}


class EvidenceReceiptBuilder:
    """Build a portable, human-readable record without secrets."""

    def build(self, contract, execution_status, evaluation=None, portfolio=None):
        return {
            "schema": "crosssignal-evidence-receipt-1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "creator": contract.get("creator", "Omobolaji E Adeyan"),
            "contract_id": contract.get("contract_id"),
            "decision_hash": contract.get("decision_hash"),
            "sealed_contract": redact(contract),
            "market_timestamp": contract.get("market_timestamp"),
            "prediction": contract.get("prediction"),
            "authorization": contract.get("authorization"),
            "authorization_reasons": contract.get("authorization_reasons", []),
            "data_quality": redact(contract.get("data_quality", {})),
            "risk_assessment": contract.get("risk_assessment", {}),
            "portfolio_stress": (portfolio or {}).get("portfolio_stress"),
            "execution_recovery": (portfolio or {}).get("execution_recovery"),
            "execution_status": execution_status,
            "evaluation": evaluation,
            "verification": "Recompute SHA-256 from the canonical sealed contract payload.",
        }

    def dumps(self, *args, **kwargs):
        return json.dumps(self.build(*args, **kwargs), indent=2, sort_keys=True, default=str)

    def verify(self, receipt):
        """Verify a receipt's embedded sealed contract when the payload is included."""
        if isinstance(receipt, str):
            try:
                receipt = json.loads(receipt)
            except json.JSONDecodeError as exc:
                return {"valid": False, "reason": f"invalid JSON: {exc}"}
        contract = receipt.get("sealed_contract")
        expected = receipt.get("decision_hash")
        if not contract:
            return {"valid": False, "reason": "receipt does not include the sealed contract payload"}
        payload = dict(contract)
        payload.pop("decision_hash", None)
        payload.pop("contract_id", None)
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        actual = hashlib.sha256(canonical.encode()).hexdigest()
        return {"valid": actual == expected, "expected": expected, "actual": actual,
                "reason": "hash matches sealed payload" if actual == expected else "hash mismatch"}
