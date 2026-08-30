# CrossSignal

![CrossSignal hackathon cover](assets/crosssignal-hackathon-cover.png)

> Markets disagree. We trade the gap.

**Created by Omobolaji E Adeyan**

CrossSignal is an auditable cross-market macro agent built for the **Alpaca AI Trading Agents Hackathon**. It synchronizes six market lenses, asks Claude to identify incomplete repricing, constructs a defined-risk SPY/HYG/TLT options portfolio, and preflights every leg through Alpaca's official MCP server before paper submission.

The differentiator is accountability: every thesis stores the market snapshot that produced it and is later scored against subsequent market data. The dashboard distinguishes live, proxy, and fallback values instead of presenting synthetic certainty.

## SIGNAL accountability protocol

Every decision must pass a scientific proof chain:

1. **Source integrity** — verify provenance, freshness, and fallback status.
2. **Inconsistency quantified** — rank deterministic cross-market disagreement scores.
3. **Gauntlet** — run a Claude falsification review and bounded stability perturbations.
4. **Notarized contract** — seal the prediction, invalidation, risk, and evidence with SHA-256.
5. **Alpaca execution** — submit capped-risk limit orders and reconcile broker lifecycle state.
6. **Learning ledger** — issue a predetermined verdict and compare agent, inverse, and cash directional proxies.

## Judge evidence lab

- **Decision Replay courtroom** reconstructs only the evidence available at decision time.
- **Alpaca Greeks defense** captures option snapshots at preflight and runs delta/gamma/vega shocks.
- **Catalyst context** labels relevant Alpaca News without allowing headlines to bypass risk gates.
- **Recovery state machine** detects partial exposure, blocks silent retries, and proposes paper-safe actions.
- **Proof of abstention** lets judges weaken evidence and watch authorization fail closed.
- **Evidence receipts** export a secret-free JSON chain from sealed prediction to later verdict.
- **Walk-forward verdicts** compare the agent direction with inverse and cash counterfactuals.

If confidence, stability, data integrity, disagreement, or deterministic risk is inadequate, `ABSTAIN` is the correct protocol outcome.

## Judge demo

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Open `http://localhost:8501`. The **Agent Lab** starts in safe preview mode. Paper-order submission requires an explicit toggle and confirmation, and remains blocked if any implemented risk or data-integrity gate fails.

For the terminal version:

```bash
python live/cross_market_agent.py
python performance_report.py
```

## Product flow

1. **Observe** — read SPY price/options, HYG/LQD/IEF returns, Treasury yields, realized volatility, and positioning.
2. **Prove provenance** — label every feed live, computed proxy, or fallback.
3. **Reason** — Claude returns a structured thesis, repricing signals, confidence, and rationale.
4. **Construct** — translate signals into three defined-risk vertical spreads.
5. **Govern** — check structure, maximum loss, confidence, buying power, diversification, and data integrity.
6. **Preflight** — price all three legs before allowing the first paper order.
7. **Audit and learn** — persist decisions, order responses, and later score forecast direction.

## Data sources

| Lens | Source | Interpretation |
|---|---|---|
| Equity volatility | Alpaca SPY options snapshots | ATM call IV and locally accumulated IV percentile |
| Treasury curve | U.S. Treasury daily par yields | 2Y/5Y/10Y level and 10Y–2Y slope |
| Credit | Alpaca HYG/LQD/IEF bars | 20-session relative-return stress proxy, not official OAS |
| Rate expectations | Treasury 3M vs. 1Y | Directional policy-rate proxy |
| Realized volatility | Alpaca SPY bars | Annualized close-to-close volatility and ATR percentage |
| Positioning | Alpaca option volume | Same-strike ATM put/call volume proxy |

## Safety model

- Paper trading only by default.
- No submission when fallback feeds are present (`REQUIRE_LIVE_DATA=true`).
- Defined maximum loss per spread and portfolio.
- Buying-power, confidence, structure, and diversification checks.
- Complete portfolio preflight before any submission.
- Explicit UI confirmation for paper orders.
- Full thesis, risk, and execution audit trail.

The agent captures Alpaca option Greeks and enforces delta, vega, theta, margin,
liquidity, bid-ask, drawdown, and snapshot-completeness gates before sealing an
authorization. Scenario P&L is a transparent delta-gamma-vega approximation,
not a full volatility-surface repricer. Recovery can cancel approved paper
orders and close explicitly selected paper positions, but never acts without
human approval. The walk-forward ledger is not presented as investment-grade
backtesting.

## Tests

```bash
pytest
```

Tests cover metric-aware thesis scoring, fallback-data fail-closed behavior,
maximum-loss and buying-power gates, spread preflight, Greek/liquidity/margin/
drawdown enforcement, recovery authorization, receipt verification, and audit
status classification.

## Repository map

```text
app.py                         Judge-facing Streamlit experience
live/cross_market_agent.py     End-to-end agent orchestration
src/data_feed/                 Cross-market state and provenance
agent/synthesizer.py           Claude structured reasoning
agent/constructor.py           Signal mapping and risk assessment
agent/thesis_scorer.py         Outcome-based forecast scoring
agent/signal_protocol.py       Disagreement, stability, sealing and verdicts
agent/evidence_protocol.py     Greeks, stress, catalysts, recovery and receipts
tools/alpaca_tools.py          Persistent Alpaca MCP integration
compliance/audit_logger.py     SQLite decision and execution ledger
tests/                         Fast isolated safety tests
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for system boundaries, [REQUIREMENTS_AUDIT.md](REQUIREMENTS_AUDIT.md) for the compliance audit, [SMOKE_TEST.md](SMOKE_TEST.md) for verification evidence, [BUILD_LOG.md](BUILD_LOG.md) for transparent event-window provenance, and [SUBMISSION.md](SUBMISSION.md) for the pitch checklist.

See [SECURITY.md](SECURITY.md) for the NIST AI RMF/SSDF-aligned threat model,
control rationale, residual risks, deployment modes and incident procedure.

## Status

Hackathon prototype · Alpaca paper trading only · Educational use · Not investment advice.
