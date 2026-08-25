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
                         Claude macro synthesis
                                    │
                                    ▼
                    SPY / HYG / TLT trade constructor
                                    │
                                    ▼
                    Risk gates → all-leg preflight
                                    │
                          preview ──┴── paper submit
                                    │
                                    ▼
                         SQLite audit + scoring
                                    │
                                    ▼
                         Streamlit evidence layer
```

## Trust boundaries

- Alpaca credentials remain in `.env`, which is excluded from version control.
- Claude proposes structured signals; it does not call the broker directly.
- Deterministic code maps signals into permitted instruments and risk limits.
- Fallback market data is visible and blocks submission by default.
- UI order submission requires a separate explicit confirmation.

## Known limitations

- The three portfolio spreads cannot be submitted as one cross-underlying atomic order. Preflight prevents known-invalid partial portfolios, but a later broker rejection can still produce fill-time partial exposure.
- “Hedge” denotes the rates diversifier; portfolio beta and Greeks are not yet calculated.
- Credit and positioning inputs are clearly labeled proxies.
- The track record is forward-scored and begins empty; it is not a substitute for a historical backtest.
