# Hackathon submission kit

## Short description

CrossSignal is an auditable AI macro trading agent that detects disagreements across volatility, rates, credit, and positioning, then constructs and preflights a defined-risk Alpaca paper portfolio. Unlike agents that only explain a trade, CrossSignal records every prediction and scores it against what the market does next.

## The 30-second pitch

Most trading agents stare at one chart and forget yesterday's prediction. CrossSignal treats markets as a connected system. It reads six live lenses, uses Claude to identify which market has not finished repricing, maps that view into capped-risk Alpaca options spreads, and exposes every source, risk gate, order response, and later forecast score in one dashboard.

## Five-minute video outline

- **0:00–0:25 — Problem:** markets transmit information at different speeds; single-market agents miss the disagreement.
- **0:25–0:55 — Product:** show the landing screen and the observe → reason → govern loop.
- **0:55–2:40 — Live demo:** run preview mode, inspect provenance, thesis, portfolio, and risk checks.
- **2:40–3:25 — Alpaca:** show MCP-backed market reads and a successful paper order/order lifecycle recorded in the ledger.
- **3:25–4:05 — Accountability:** show the stored market snapshot and self-scored thesis history.
- **4:05–4:35 — Business:** research and risk copilot for active options traders and small investment teams; SaaS plus broker/infrastructure partnerships.
- **4:35–5:00 — Roadmap:** Greeks, replay/backtest, fill reconciliation, and configurable strategy policies.

## Slide deck

1. Markets disagree. We trade the gap.
2. Problem: fragmented signals and unaccountable AI decisions.
3. Solution: six lenses, one thesis, one governed workflow.
4. Live product screenshots.
5. Architecture and Alpaca integration.
6. Safety and auditability.
7. Target user and business model.
8. Evidence, limitations, and roadmap.

## Before submitting

- [ ] Register/enroll on lablab.ai and verify event-specific rules.
- [ ] Push a public GitHub repository with no secrets or database files.
- [x] Capture at least one successful market-hours paper fill (three spreads filled on 2026-08-25).
- [x] Verify order status and position in Alpaca; capture the filled workflow in the demo.
- [ ] Let at least one thesis mature and show its scored outcome.
- [ ] Deploy the Streamlit application with secrets configured privately.
- [x] Add the final 16:9 cover image (`assets/crosssignal-hackathon-cover.png`).
- [ ] Add application URL, repository URL, video, and PDF deck to lablab.ai.
- [ ] Test the public URL in a private browser window.
- [ ] Submit before the deadline and reserve time for judge Q&A.
