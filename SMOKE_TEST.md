# Smoke-test record

Last executed: August 25, 2026 by Omobolaji E Adeyan.

## Automated verification

- `python -m pytest` — 16 tests passed.
- Python compilation — application, agent, compliance, live and Alpaca modules compiled successfully.
- Streamlit `AppTest` — zero render exceptions; six judge-facing tabs detected.
- HTTP health — local server returned `200 OK` and `_stcore/health` returned `ok`.

## Live-safe integration verification

A complete preview cycle used the connected Alpaca paper account, live market data and Claude without submitting a new order.

- Leading case: Equity fear vs credit complacency
- Disagreement score: 81/100
- Stability: 100% across 10 bounded perturbations
- Confidence: 68% before challenge, 60% after challenge
- Decision Contract: `CS-20260825-D5D5FE92`
- Authorization: `AUTHORIZED`
- SHA-256: `d5d5fe92d533319251124e13d25b781590701721f5a5ddb911d6b945d7d002cf`
- Execution mode: preview; no additional paper order submitted

An earlier governed market-hours cycle filled three Alpaca multi-leg paper spreads. Local audit databases are intentionally excluded from Git.

## Repeat locally

```bash
source venv/bin/activate
pytest
streamlit run app.py
```

Use the browser’s **Run agent** view in preview mode first. Paper execution requires a separate toggle and confirmation.
