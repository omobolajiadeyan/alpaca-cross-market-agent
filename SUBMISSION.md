# CrossSignal hackathon submission kit

**Creator:** Omobolaji E Adeyan  
**Challenge:** Alpaca AI Trading Agents Hackathon — Options Alpha Agents  
**Deadline:** September 4, 2026 at 10:00 AM CDT

## Submission position

CrossSignal is eligible on the documented technical requirements: it is an
autonomous options agent, uses Alpaca's official MCP server and Trading API,
runs only against a fresh $100,000 paper account, and includes a one-page
description of its AI logic, risk gates, and Alpaca infrastructure.

The material competitive weakness is **P&L Performance**. The dedicated account
currently has $100,000 cash, $100,000 portfolio value, no open positions, and no
orders. This is not an eligibility failure, but it gives judges no realized P&L
to score. Do not disguise that limitation.

## Judge-ready pitch

Most agents optimize for producing a trade. CrossSignal optimizes for producing
a defensible decision. It synchronizes six market lenses, quantifies the
strongest cross-market disagreement, asks Claude to propose and then attack a
thesis, tests stability under bounded perturbations, constructs defined-risk
options spreads, and gives deterministic code final authority. Every decision
is sealed before the outcome and later scored.

## Why the latest cycles did not trade

Two September 3 records show different layers of the same policy working:

- **Local connected cycle — `CS-20260903-FE01A097`:** signal quality 82.4 and
  stability 90%, with all feeds sourced live. Claude's adversarial review found
  that the “cheap volatility” claim relied on a short, non-standard local IV
  history while IV was already 1.26× realized volatility. It cut confidence
  from 68% to 53%. The hard minimum is 55%, so the cycle stopped before option
  preflight and sent no order.
- **Unattended Evidence Watch — `CS-20260903-5C194F65`:** confidence cleared at
  56%, all six base gates passed, and all six proposed option legs had Greeks.
  Preflight then found zero displayed daily volume on the weakest leg and a
  maximum relative bid-ask spread of 93.33%, against limits of 10 contracts and
  25%. Only 13 of 15 checks passed. This was after the regular options session,
  so refusing non-executable quotes was the correct decision.

This is stronger than saying “the score was low.” The agent found evidence that
the hypothesis or the executable market was not reliable enough. It did not
round confidence upward, loosen risk limits, queue an after-hours options order,
or fabricate P&L for the competition.

## Final assets

- Judge demo: <https://crosssignal-ai-agent.streamlit.app>
- Repository: <https://github.com/omobolajiadeyan/alpaca-cross-market-agent>
- Dedicated Alpaca paper account ID: `PA3PDTUDIXDU`
- Selected video: `CrossSignal-Submission-Video.mp4` (4:49, 1920×1080, all ten cycles including today's)
- Slide deck: `CrossSignal-Hackathon-Pitch-Final.pdf`
- One-page write-up: `CrossSignal-One-Page-Writeup.pdf`
- Latest secret-free evidence: `Latest-Run-Evidence.json`

## Stop-ship checklist

- [x] **Streamlit app public access re-verified 2026-09-03.** An earlier
  automated check flagged a login redirect; re-checked via curl with a real
  cookie jar/browser user-agent and 10+ real headless-Chromium loads during
  video rendering, all reaching "PUBLIC JUDGE MODE" directly. Not a blocker —
  still worth a manual private-window glance before submitting.
- [ ] Enter account ID `PA3PDTUDIXDU` in the lablab submission form.
- [ ] Upload the selected 4:49 video, cover, PDF deck, and one-page PDF.
- [ ] Add the public GitHub URL and demo URL.
- [ ] Paste the prepared short and long descriptions from
  `submission/SUBMISSION_FORM_COPY.md`.
- [ ] Submit before September 4, 2026 at 10:00 AM CDT.

Do not wait for or force a trade. If the form supports later edits, a normal
market-hours cycle may be run after 8:30 AM CDT, but only a gate-approved order
belongs in the record.
