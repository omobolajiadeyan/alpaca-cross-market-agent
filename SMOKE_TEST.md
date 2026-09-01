# Smoke-test record

Last executed: September 1, 2026 by Omobolaji E Adeyan.

## Automated verification

- `python -m pytest` — 43 tests passed (39 original + 4 added while fixing a
  trade-direction bug, a partly-dead stability test, a misleading recovery
  state, and a silently-truncated falsification call -- see repository
  commit history for 2026-09-01).
- Python compilation — application, agent, compliance, live and Alpaca modules compiled successfully.
- Streamlit `AppTest` — zero render exceptions; seven judge-facing tabs detected, including Security.
- Public judge replay — renders without credentials, exposes authorized and abstention cases plus the four-part scorecard, and makes no external or broker call.
- Evidence Watch configuration test — missing secrets produce `CONFIGURATION_REQUIRED`; broker mutation remains false and no synthetic receipt is emitted.
- Public deployment — <https://crosssignal-ai-agent.streamlit.app> opened successfully in a signed-out private browser session.
- HTTP health — local server returned `200 OK` and `_stcore/health` returned `ok`.

## Live-safe integration verification

A complete preview cycle used the connected Alpaca paper account, live market data and Claude without submitting a new order.

Latest expanded-risk preview:

- Leading case: Rate expectations vs credit pricing
- Disagreement score: 80/100
- Stability: 100% across 10 bounded perturbations
- Catalyst context: 10 relevant Alpaca headlines
- Greek coverage: 6/6 proposed option legs
- Decision Contract: `CS-20260825-97D864E6`
- Authorization: `ABSTAIN`
- Reason: option volume and relative bid-ask quality failed the new execution gates
- Execution mode: preview; no paper order submitted

Earlier baseline preview:

- Leading case: Equity fear vs credit complacency
- Disagreement score: 81/100
- Stability: 100% across 10 bounded perturbations
- Confidence: 68% before challenge, 60% after challenge
- Decision Contract: `CS-20260825-D5D5FE92`
- Authorization: `AUTHORIZED`
- SHA-256: `d5d5fe92d533319251124e13d25b781590701721f5a5ddb911d6b945d7d002cf`
- Execution mode: preview; no additional paper order submitted

An earlier governed market-hours cycle filled three Alpaca multi-leg paper spreads
on a prior account, before the hackathon's dedicated-account requirement was
confirmed. That evidence does not carry over to the new account below.

## Dedicated-account verification (2026-09-01)

A brand-new Alpaca paper account was created for this hackathon:
account `PA3PDTUDIXDU`, $100,000 starting balance, created 2026-09-01 (verified
via a direct, unauthenticated-bypassing call to `GET /v2/account`).

Five live cycles were run against it on 2026-09-01, each reading real market
data and calling Claude for synthesis and adversarial falsification:

- All five correctly abstained -- either on post-falsification confidence
  landing just under the 55% threshold, or on a live-data gap in options-volume
  positioning (the code refuses to fabricate a put/call ratio from unreliable
  volume rather than guess).
- Falsification is genuinely running Claude per cycle (verified via the
  `source` field on each result), not the deterministic fallback -- confirmed
  after fixing a `max_tokens` truncation bug that had silently been forcing
  every earlier cycle onto a canned response.
- No trade has been filled on this account as of this record. Live cycles
  continue through the submission window; the audit database (`trading_audit.db`,
  excluded from Git) has the full record.

## Repeat locally

```bash
source venv/bin/activate
pytest
streamlit run app.py
```

Use the browser’s **Run agent** view in preview mode first. Paper execution requires a separate toggle and confirmation.
