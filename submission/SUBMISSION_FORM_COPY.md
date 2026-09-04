# Paste-ready lablab submission fields

## Submission Title - 46/50 characters

CrossSignal: Auditable Cross-Market Options AI

## Short Description — 174/255 characters

CrossSignal turns conflicts across rates, credit, equities and volatility into defined-risk Alpaca options decisions—and proves why each trade entered, exited or was refused.

## Long Description — 1,860/2,000 characters; 258 words

Markets often disagree before they reprice. Most trading agents choose one signal and act. CrossSignal verifies whether the disagreement is real, executable and worth expressing through options—then manages the position through exit.

The agent synchronizes six lenses: equity volatility, Treasury yields, credit, realized volatility, rate expectations and options positioning. Deterministic code ranks the disagreements. Claude proposes a structured thesis; a separate adversarial pass identifies counterarguments, missing evidence, invalidation and a confidence penalty.

Approved signals map to defined-risk SPY, HYG and TLT vertical spreads. Before an Alpaca order, code verifies live data, confidence, maximum loss, buying power, diversification, Greeks, stress, liquidity, bid-ask quality and drawdown. Claude cannot contact the broker or override a failed gate.

Every eligible spread stores four exit rules: take 50% of maximum profit, stop at 50% of defined maximum loss, exit after five trading days, or close two days before expiry. The monitor reconciles broker legs, rejects stale quotes and closes both legs atomically. A deterministic client order ID and persisted EXIT_PENDING state prevent duplicate exits.

Each decision is sealed with its evidence, prediction, invalidation and risk result in a SHA-256 Decision Contract. Forecasts are later compared with inverse and cash counterfactuals.

Alpaca's official MCP server supplies market data, option snapshots, Greeks, account state, paper orders and reconciliation. The public app and GitHub Evidence Watch are read-only.

The fresh $100,000 competition account had zero orders or positions at the submission cutoff, so CrossSignal makes no P&L claim. It abstained when confidence or executable-liquidity evidence failed fixed thresholds instead of weakening controls to manufacture a trade.

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
