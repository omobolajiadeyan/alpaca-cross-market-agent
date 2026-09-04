# Why CrossSignal submitted no trade

CrossSignal did not fail to place a trade. It declined to authorize one because
the evidence failed two different layers of its published policy.

## Hypothesis quality failed in the latest local cycle

Contract `CS-20260903-FE01A097` began with a plausible 68%-confidence thesis:
equity options appeared fearful while credit remained complacent. The
deterministic disagreement score was 82.4/100 and the leading case survived 9 of
10 perturbations.

The independent falsification pass then found three weaknesses:

1. “Low IV rank” meant low relative to the agent's short local history—not a
   standard 252-day or multi-year history.
2. ATM IV was already 1.26× realized volatility, which does not cleanly support
   calling volatility cheap.
3. The 2.15 put/call value was a narrow same-strike ATM volume proxy, not a
   market-wide positioning measure.

Confidence fell to 53%. The rule requires at least 55%. The system did not round,
reinterpret, or override the result; it sealed `ABSTAIN` before option preflight.

## Execution quality failed in the latest unattended preflight

Contract `CS-20260903-5C194F65` cleared confidence at 56% and passed all six base
gates. All six option legs had Greeks and portfolio stress passed. Preflight then
found minimum displayed option volume of 0 against a requirement of 10 and a
maximum relative bid-ask spread of 93.33% against a 25% cap. Only 13 of 15 full
checks passed. The run occurred after the regular options session, when those
quotes were not credible execution evidence.

## Why this is the correct autonomous behavior

Submitting anyway would have required at least one of the following: weakening a
precommitted confidence floor, treating a short-history proxy as stronger than it
was, accepting an extreme spread, ignoring zero displayed volume, or queueing an
after-hours options order for the sake of a competition metric. CrossSignal did
none of those things.

The fresh paper account remains at $100,000 cash with zero positions and zero
orders. Consequently there is no P&L to claim, and the P&L judging dimension is a
real weakness. The submission does not present abstention as investment
performance. It presents it as verifiable evidence that the agent's safety and
epistemic controls are binding even when placing a trade would make the demo look
better.
