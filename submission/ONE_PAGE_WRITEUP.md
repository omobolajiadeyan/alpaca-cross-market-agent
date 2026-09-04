# CrossSignal — One-Page Technical Write-Up

**Creator:** Omobolaji E Adeyan  
**Alpaca paper account:** `PA3PDTUDIXDU` — fresh account, $100,000 starting balance  
**Repository:** <https://github.com/omobolajiadeyan/alpaca-cross-market-agent>  
**Demo:** <https://crosssignal-ai-agent.streamlit.app>

## Strategy and AI logic

CrossSignal is an autonomous, cross-market options agent built to answer a
question most trading systems skip: **does a promising signal deserve execution?**
It synchronizes six lenses—equity implied volatility, Treasury curve, credit,
realized volatility, rate expectations, and options positioning. A deterministic
engine ranks three cross-market disagreements and selects the strongest case.
Claude then produces a structured thesis, proposed repricing direction, rationale,
and confidence. A separate adversarial Claude review must identify the strongest
counterargument, missing evidence, alternative explanation, invalidation condition,
and a confidence adjustment. Claude proposes and critiques; it never receives
broker authority.

The SIGNAL protocol then applies ten bounded input perturbations to test whether
the selected disagreement survives plausible measurement noise. Before any order,
the complete market snapshot, thesis, challenge, stability result, portfolio,
prediction horizon, and invalidation rule are sealed into a SHA-256 Decision
Contract. Later evaluation compares the precommitted direction with inverse and
cash counterfactuals instead of rewriting the story after the result.

## Risk gates and options construction

Signals map only to defined-risk two-leg vertical spreads in SPY, HYG, and TLT.
No naked options are permitted. Deterministic base gates require complete
structure, total proposed maximum loss no greater than $1,500, post-challenge
confidence of at least 55%, sufficient buying power, cross-market diversification,
and zero fallback feeds when live data is required. All proposed legs are then
preflighted before the first order. The execution gate checks portfolio delta,
vega, theta, margin utilization, minimum option volume, maximum relative bid-ask
spread, daily and maximum drawdown, and Greeks coverage. One failed required gate
produces an explicit `ABSTAIN`; thresholds cannot be relaxed by the language model.

## Alpaca infrastructure and safety boundary

Alpaca's official MCP server is held in one persistent stdio session for market
data, account state, options snapshots and Greeks, orders, positions, and
reconciliation. Mutations are rejected unless the endpoint is exactly Alpaca's
paper URL and local execution authorization is enabled. The public Streamlit demo
is credential-free and read-only. GitHub Evidence Watch runs unattended with
broker mutations hard-disabled and exports only secret-free evidence artifacts.

## Submission evidence and honest limitation

On September 3, local contract `CS-20260903-FE01A097` found an 82.4/100
equity-fear-versus-credit disagreement with 90% perturbation stability. The
adversarial review challenged the “cheap vol” framing: the IV percentile came
from a short local history, the put/call value was a narrow ATM proxy, and IV was
already 1.26× realized volatility. Confidence fell from 68% to 53%, below the
fixed 55% floor, so no preflight or order occurred.

The latest unattended contract, `CS-20260903-5C194F65`, cleared confidence at
56% and all six base gates, but option preflight passed only 13 of 15 checks:
minimum displayed volume was 0 versus 10 required, and the widest relative
bid-ask spread was 93.33% versus a 25% maximum. Greeks coverage was 6/6 and
defined maximum loss was $464, but execution quality was unacceptable—especially
after the regular options session—so it abstained.

The dedicated account currently has $100,000 cash, no positions, and no orders.
Therefore CrossSignal has no competition-account P&L to claim; that is a judging
weakness, not an eligibility failure. The evidence shows that the agent did not
force a paper trade, queue an after-hours options order, or weaken controls to
manufacture performance.
