# CrossSignal — One-Page Technical Write-Up

**Alpaca account:** PA3PDTUDIXDU (paper, $100,000 starting balance, created 2026-09-01)
**Repository:** github.com/omobolajiadeyan/alpaca-cross-market-agent

## AI logic

CrossSignal runs the **SIGNAL protocol**, a six-step pipeline that separates
pattern-recognition (Claude) from decision authority (deterministic code):

1. **Observe** — Alpaca's Trading API and MCP server supply SPY options
   snapshots, HYG/LQD/IEF bars, and Treasury par yields. Every value is
   labeled live, computed, proxied, or fallback; none are silently faked.
2. **Quantify disagreement** — a deterministic engine scores three candidate
   cross-market anomalies (equity fear vs. credit, implied vs. realized vol,
   rate expectations vs. credit) and picks the strongest as the case to
   reason about. Claude never picks the case; the math does.
3. **Synthesize** — Claude (`claude-sonnet-5`) proposes a structured thesis,
   direction, and confidence from the six-lens snapshot.
4. **Falsify** — a second Claude call acts as an adversarial reviewer,
   returning the strongest counterargument, missing evidence, and a
   confidence penalty. This is a genuine critique step, not decoration: in
   testing, it correctly flagged a duration-mismatch artifact in the credit
   proxy and a mislabeled rate-direction field, both real methodological
   weaknesses, and adjusted confidence accordingly.
5. **Stress-test stability** — ten bounded perturbations (±1–2% on implied
   vol, ±10% on put/call ratio, ±10bps on the credit proxy) nudge the input
   data and re-run the disagreement engine. A conclusion that doesn't
   survive realistic noise is marked unstable.
6. **Seal** — the market snapshot, thesis, falsification, stability result,
   and risk assessment are hashed with SHA-256 into a Decision Contract
   *before* any broker call, so the record can't be edited after the
   outcome is known.

## Risk gates

No trade reaches the broker without passing all of the following,
independent of Claude's confidence:

- **Structure** — thesis, trade legs, confidence, and loss fields present
- **Maximum defined loss** — proposed loss ≤ `$1,500` portfolio cap
- **Signal confidence** — post-falsification confidence ≥ 55%
- **Buying power** — sufficient margin for the proposed spreads
- **Cross-market diversification** — legs span distinct instruments
- **Live-data integrity** — zero fallback feeds when `REQUIRE_LIVE_DATA=true`
- **Execution risk gate** (pre-submission) — net delta/vega/theta limits,
  margin utilization, option liquidity, bid-ask quality, and daily/max
  drawdown, computed from real Alpaca option Greeks snapshots
- **Portfolio preflight** — every leg is priced against live quotes before
  the first order is allowed

Any single failure blocks submission and the cycle logs an explicit
`ABSTAIN`, not a silent skip.

## Alpaca infrastructure

- **MCP server**: all market data, account state, and order execution route
  through the official `alpaca-mcp-server`, held as one persistent stdio
  session rather than a new subprocess per call.
- **Paper endpoint enforcement**: broker mutations are rejected unless the
  base URL is exactly `https://paper-api.alpaca.markets` — a live endpoint
  cannot execute even by misconfiguration.
- **Instruments**: SPY, HYG, TLT — all three traded exclusively as
  defined-risk two-leg vertical spreads (debit or credit), never naked
  single-leg options.
- **Explicit authorization**: paper execution requires both
  `ALLOW_PAPER_EXECUTION=true` locally and passing every gate above; the
  public Streamlit demo runs in a separate credential-free mode that cannot
  reach the broker at all.

## Status at submission

As of Sep 1, live cycles against the dedicated account have correctly
identified real cross-market disagreement (score 82/100, stability
100%/10) but abstained each time — either on signal confidence just under
threshold after genuine adversarial review, or on a live-data gap in
options-volume positioning. We treat this as the system working as
designed: refusing marginal evidence is the point, not a shortfall. Live
cycles continue through the submission window.
