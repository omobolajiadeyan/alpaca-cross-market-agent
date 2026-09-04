# Architecture

```text
Alpaca MCP ─┬─ spot, bars, options ─┐
            └─ account, orders ─────┤
U.S. Treasury ── yield curve ───────┤
                                    ▼
                         Cross-market snapshot
                         + source provenance
                                    │
                                    ▼
                    Deterministic disagreement score
                                    │
                         Claude macro synthesis
                         + falsification review
                                    │
                                    ▼
                    SPY / HYG / TLT trade constructor
                                    │
                                    ▼
                Stability + risk → sealed Decision Contract
                                    │
                          all-leg limit preflight
                                    │
                          preview ──┴── paper submit
                                    │
                                    ▼
                      persisted exit contract
                      + spread lifecycle monitor
                      + atomic paper close
                                    │
                                    ▼
                         SQLite audit + scoring
                                    │
                                    ▼
                         Streamlit evidence layer
                         + replay / receipt export

GitHub Actions scheduler ── read-only `run(execute=False)`
                         └─ redacted receipt + scorecard artifact
```

## Trust boundaries

- Alpaca credentials remain in `.env`, which is excluded from version control.
- Claude proposes structured signals; it does not call the broker directly.
- Deterministic code maps signals into permitted instruments and risk limits.
- Fallback market data is visible and blocks submission by default.
- UI order submission requires a separate explicit confirmation.
- Every authorized decision is SHA-256 sealed before broker submission.
- Abstention is a successful policy outcome when evidence is insufficient.
- Alpaca option Greeks are captured at preflight and missing coverage fails the stress gate.
- Delta, vega, theta, margin, option volume, bid-ask quality, drawdown, and Greek completeness are enforced before authorization.
- Partial exposure enters an explicit recovery state; cancellation or position closure requires paper mode and explicit approval.
- Healthy filled spreads enter a separate lifecycle state machine: `PENDING_ENTRY → OPEN → EXIT_PENDING → CLOSED`.
- Each lifecycle row seals dollar take-profit and stop-loss thresholds, maximum holding days, and a pre-expiry deadline at entry time.
- Closing orders reverse both option legs in one Alpaca multi-leg limit order; a persisted `EXIT_PENDING` state prevents duplicate submissions.
- Exit execution requires the paper endpoint, `ALLOW_PAPER_EXECUTION=true`, `ENABLE_AUTOMATED_PAPER_EXITS=true`, and an open Alpaca market clock.
- Alpaca News is contextual evidence only and cannot override deterministic controls.
- Scheduled Evidence Watch has observation authority only; it cannot submit, cancel, or close paper orders.
- The judge replay contains both an authorized contract and a fail-closed abstention so the policy boundary is directly comparable.

## Known limitations

- The three portfolio spreads cannot be submitted as one cross-underlying atomic order. Preflight prevents known-invalid partial portfolios, but a later broker rejection can still produce fill-time partial exposure.
- “Hedge” denotes the rates diversifier; cross-asset beta is not yet calculated.
- Credit and positioning inputs are clearly labeled proxies.
- Scenario P&L uses local delta-gamma-vega approximation rather than full option repricing.
- Exit valuation uses executable bid/ask quotes for the registered vertical spread, not a full volatility-surface repricer; illiquid or invalid quotes fail closed.
- The lifecycle manager governs only spreads registered by CrossSignal after this feature; it does not silently adopt unrelated account positions.
- The track record is forward-scored and is not a substitute for an investment-grade historical backtest.
