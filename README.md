# CrossSignal

![CrossSignal — markets disagree, we verify the trade](assets/crosssignal-hackathon-cover.png)

> Markets disagree. We verify the trade.

**Created by Omobolaji E Adeyan**

**Live judge demo:** <https://crosssignal-ai-agent.streamlit.app>

**Final submission evidence:** [video record](submission/EVIDENCE_RECORDING.md) ·
[pitch deck](submission/CrossSignal-Hackathon-Pitch-Final.pdf) ·
[one-page write-up](submission/CrossSignal-One-Page-Writeup.pdf) ·
[submission checklist](submission/SUBMISSION-CHECKLIST.md)

CrossSignal converts disagreement across equities, credit, rates and volatility
into defined-risk Alpaca options decisions. It proves why each trade entered,
exited or was refused.

Built for the **Alpaca AI Trading Agents Hackathon**, it synchronizes six market
lenses, asks Claude to identify incomplete repricing, constructs a defined-risk
SPY/HYG/TLT options portfolio, preflights every leg through Alpaca's official
MCP server, and manages every submitted spread through a persisted exit policy.

The differentiator is accountability: every thesis stores the market snapshot that produced it and is later scored against subsequent market data. The dashboard distinguishes live, proxy, and fallback values instead of presenting synthetic certainty.

The final narrated MP4 was uploaded through the competition submission portal.
GitHub tracks its script, review record, duration, and SHA-256 receipt rather
than duplicating the compiled video binary in source control.

## SIGNAL accountability protocol

Every decision must pass a scientific proof chain:

1. **Source integrity** — verify provenance, freshness, and fallback status.
2. **Inconsistency quantified** — rank deterministic cross-market disagreement scores.
3. **Gauntlet** — run a Claude falsification review and bounded stability perturbations.
4. **Notarized contract** — seal the prediction, invalidation, risk, and evidence with SHA-256.
5. **Alpaca execution** — submit capped-risk limit orders and reconcile broker lifecycle state.
6. **Position management** — value the complete spread and enforce take-profit, stop-loss, maximum-hold, and pre-expiry exits.
7. **Learning ledger** — issue a predetermined verdict and compare agent, inverse, and cash directional proxies.

## Judge evidence lab

- **Decision Replay courtroom** reconstructs only the evidence available at decision time.
- **Alpaca Greeks defense** captures option snapshots at preflight and runs delta/gamma/vega shocks.
- **Catalyst context** labels relevant Alpaca News without allowing headlines to bypass risk gates.
- **Recovery state machine** detects partial exposure, blocks silent retries, and proposes paper-safe actions.
- **Position lifecycle ledger** seals exit thresholds at entry, prevents duplicate closes, and records every recommendation, deferral, submission, and fill.
- **Proof of abstention** lets judges weaken evidence and watch authorization fail closed.
- **Evidence receipts** export a secret-free JSON chain from sealed prediction to later verdict.
- **Walk-forward verdicts** compare the agent direction with inverse and cash counterfactuals.
- **Four-part scorecard** separates signal quality, decision stability, execution quality, and outcome evidence instead of collapsing intelligence into one confidence number.
- **Contrasting cases** let judges compare a fully authorized workflow with a deliberate abstention under weaker execution evidence.

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

### Public judge deployment

The default configuration is a credential-free, read-only judge experience. It
loads a clearly labeled sanitized replay derived from a verified Alpaca paper
workflow, never contacts a broker, and cannot submit orders. Deploy `app.py` to
Streamlit Community Cloud with:

```toml
PUBLIC_DEMO_MODE = "true"
ALLOW_PAPER_EXECUTION = "false"
ENABLE_AUTOMATED_PAPER_EXITS = "false"
REQUIRE_LIVE_DATA = "true"
EVALUATION_HORIZON_DAYS = "5"
```

Use controlled local mode for the presenter-led connected demonstration by
setting `PUBLIC_DEMO_MODE=false` and supplying private Alpaca and Anthropic
credentials. `ALLOW_PAPER_EXECUTION` should remain false unless an intentional
paper-order demonstration is being supervised. Automated exits additionally
require `ENABLE_AUTOMATED_PAPER_EXITS=true`; neither switch can authorize a live
Alpaca endpoint.

### Autonomous Evidence Watch

`.github/workflows/evidence-watch.yml` runs a read-only observation cycle every
six hours on weekdays and can also be started manually. It generates a
secret-free evidence receipt, summary, and four-part scorecard as a GitHub
Actions artifact. The cloud job is intentionally unable to place or recover
orders: `ALLOW_PAPER_EXECUTION` is fixed to `false`, and the script refuses to
run if mutation is enabled.

Configure these encrypted GitHub repository secrets to enable connected
evidence collection:

- `APCA_API_KEY_ID`
- `APCA_API_SECRET_KEY`
- `ANTHROPIC_API_KEY`

Without them, the workflow records `CONFIGURATION_REQUIRED` and exits safely;
it never substitutes fabricated market evidence. A green workflow therefore
means the automation and safety boundary worked—inspect the artifact status to
confirm whether a connected observation was produced.

For the terminal version:

```bash
python live/cross_market_agent.py
python scripts/manage_positions.py           # observe and audit only
python scripts/manage_positions.py --execute # paper exits, only when both switches allow it
python performance_report.py
```

Before an exit can be submitted, the monitor reconciles registered option-leg
quantities against Alpaca, rejects missing or stale quote timestamps, checks the
Alpaca market clock, claims the exit atomically, and supplies a deterministic
`client_order_id`. `PAUSE_NEW_ENTRIES=true` is an independent kill switch: it
halts new positions while allowing already-authorized lifecycle exits to run.

## Product flow

1. **Observe** — read SPY price/options, HYG/LQD/IEF returns, Treasury yields, realized volatility, and positioning.
2. **Prove provenance** — label every feed live, computed proxy, or fallback.
3. **Reason** — Claude returns a structured thesis, repricing signals, confidence, and rationale.
4. **Construct** — translate signals into three defined-risk vertical spreads.
5. **Govern** — check structure, maximum loss, confidence, buying power, diversification, and data integrity.
6. **Preflight** — price all three legs before allowing the first paper order.
7. **Manage** — monitor spread liquidation value; close on 50% of maximum profit, 50% of maximum loss, five trading days, or two calendar days before expiry.
8. **Audit and learn** — persist entry/exit events and later score forecast direction.

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
- Exit policy persisted with the order: configurable profit, loss, time, and expiry triggers.
- Atomic multi-leg limit closes, market-clock checks, and idempotent `EXIT_PENDING` state.
- Separate authorization for automated paper exits; public mode cannot mutate the broker.
- Full thesis, risk, and execution audit trail.

The agent captures Alpaca option Greeks and enforces delta, vega, theta, margin,
liquidity, bid-ask, drawdown, and snapshot-completeness gates before sealing an
authorization. Scenario P&L is a transparent delta-gamma-vega approximation,
not a full volatility-surface repricer. Emergency recovery remains human-approved.
Normal management is a separate deterministic paper-only state machine and can
be automated only through its independent deployment switch. The walk-forward
ledger is not presented as investment-grade backtesting.

## Tests

```bash
pytest
```

Tests cover metric-aware thesis scoring, fallback-data fail-closed behavior,
maximum-loss and buying-power gates, spread preflight, Greek/liquidity/margin/
drawdown enforcement, recovery authorization, take-profit/stop-loss/time/expiry
decisions, atomic close construction, idempotency, receipt verification, and
audit status classification. The current suite contains **53 passing tests**.

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
agent/position_manager.py      Deterministic spread valuation and exit lifecycle
tools/alpaca_tools.py          Persistent Alpaca MCP integration
compliance/audit_logger.py     SQLite decision and execution ledger
scripts/evidence_watch.py      Read-only scheduled evidence exporter
scripts/manage_positions.py    Observe-only or explicitly authorized paper exit job
.github/workflows/             Tests and cloud Evidence Watch automation
tests/                         Fast isolated safety tests
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for system boundaries, [REQUIREMENTS_AUDIT.md](REQUIREMENTS_AUDIT.md) for the compliance audit, [SMOKE_TEST.md](SMOKE_TEST.md) for verification evidence, [PROJECT_PROVENANCE.md](PROJECT_PROVENANCE.md) for project provenance, and [SUBMISSION.md](SUBMISSION.md) for the pitch checklist.

See [SECURITY.md](SECURITY.md) for the NIST AI RMF/SSDF-aligned threat model,
control rationale, residual risks, deployment modes and incident procedure.

## Status

Hackathon prototype · Alpaca paper trading only · Educational use · Not investment advice.
