# Paste-ready lablab submission fields

## Submission Title - 46/50 characters

CrossSignal: Auditable Cross-Market Options AI

## Short Description - 159/255 characters

CrossSignal detects cross-market mispricing, governs Alpaca options entries, and manages each paper spread with auditable profit, loss, time, and expiry exits.

## Long Description - 1,917/2,000 characters; 265 words

Most trading agents optimize for producing a signal. CrossSignal produces a defensible decision and manages it through exit.

The agent synchronizes six lenses: equity volatility, Treasury yields, credit, realized volatility, rate expectations, and options positioning. Code ranks cross-market disagreements. Claude creates a structured thesis; an adversarial pass identifies counterarguments, missing evidence, invalidation, and a confidence penalty.

Approved signals become defined-risk SPY, HYG, and TLT vertical spreads. Before an Alpaca order, controls verify confidence, live data, maximum loss, buying power, diversification, Greeks, stress, liquidity, bid-ask quality, and drawdown. Claude cannot contact the broker or override a failed gate.

Each spread stores four exit rules: take 50% of maximum profit, stop at 50% of defined maximum loss, exit after five trading days, or close two days before expiry. Before an atomic multi-leg close, the monitor reconciles broker legs and rejects stale quotes. An atomic claim, deterministic client order ID, and persisted state prevent duplicate exits. A kill switch can pause entries without disabling management of open positions.

Each cycle seals its evidence, prediction, invalidation, risk result, and portfolio in a SHA-256 Decision Contract before the outcome. Forecasts are later scored against inverse and cash counterfactuals.

Alpaca's official MCP server provides market data, option snapshots, Greeks, account state, paper orders, valuation, and reconciliation. Mutations require the paper endpoint and explicit local switches; the public app and GitHub automation are read-only.

The fresh $100,000 competition account currently has no orders or positions, so CrossSignal makes no P&L claim. Recent cycles honestly abstained when confidence, liquidity, or bid-ask evidence failed fixed thresholds instead of weakening controls to manufacture a trade.

## Categories

Select the closest available categories in this order:

1. Finance / FinTech
2. AI Agents
3. Developer Tools, if a third category is allowed

## Event Track

Options Alpha Agents

## Technologies Used

Select these available technology tags:

- Alpaca
- Anthropic Claude
- Python
- Streamlit
- GitHub Actions
- MCP / Model Context Protocol, if available

Do not select Alpaca CLI because this project uses Alpaca MCP, not the CLI.

## Social Media Post Links

Leave these fields blank unless you already published genuine X or LinkedIn posts during the hackathon that tag both lablab.ai and Alpaca. Do not create placeholder links.

## Required links for later steps

- Application: <https://crosssignal-ai-agent.streamlit.app>
- Repository: <https://github.com/omobolajiadeyan/alpaca-cross-market-agent>
- Alpaca paper account ID: `PA3PDTUDIXDU`
- Latest Evidence Watch: <https://github.com/omobolajiadeyan/alpaca-cross-market-agent/actions/runs/33805502192>
