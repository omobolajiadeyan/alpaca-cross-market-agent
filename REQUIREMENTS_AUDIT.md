# Requirements audit

Audited September 1, 2026 by and for **Omobolaji E Adeyan**. Updated from the
official event page/PDF (`lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon`),
which supersedes the earlier August 31 audit's guesses at generic judging
criteria.

## Alpaca event page — explicit lines

| Published line | Status | Evidence |
|---|---|---|
| Event is online, Aug 28–Sep 4 2026 | Met | Enrolled, team `CrossSignal`, dashboard shows Approved |
| Autonomous AI trading agent on Alpaca's Trading API | Met | `live/cross_market_agent.py` |
| Uses Alpaca MCP server or CLI | Met | `alpaca-mcp-server`, persistent stdio session |
| All strategies incorporate options trading | Met | SPY/HYG/TLT vertical spreads only |
| **Brand-new paper account dedicated to this hackathon** | Met | `PA3PDTUDIXDU`, created 2026-09-01 |
| **$100,000 starting balance on that account** | Met | Verified via live `GET /v2/account` call |
| **Alpaca paper account ID in the final submission** | Ready | `PA3PDTUDIXDU` — must be entered on the lablab form |
| **One-page write-up** (AI logic, risk gates, Alpaca infra) | Met | `submission/ONE_PAGE_WRITEUP.md` |

## Real judging criteria (from the official page, not a generic rubric)

| Dimension | Current evidence | Gap |
|---|---|---|
| **P&L Performance** | Zero fills on the dedicated account as of this audit; five live cycles on 2026-09-01 all correctly abstained | This is the largest open risk — the account ID ties directly to this criterion and there is currently nothing for judges to evaluate |
| Technology Implementation | Real Alpaca MCP integration, real Claude synthesis + adversarial falsification (verified genuine, not the earlier silently-fallback version), deterministic risk gates | None known |
| Creativity & Originality | Six-lens disagreement engine, SHA-256 pre-registration, 10-perturbation stability testing, forward-scored walk-forward ledger, self-auditing Readiness tab | The "governed refusal" framing is shared by several other teams in this event's own public gallery; differentiation should lean on mechanism depth, not the headline concept |
| Presentation & Execution | Narrated screen-recorded video produced | Deck still references a stale test count/contract ID (see below) |
| Social engagement (bonus) | Not started | Up to 5 X/LinkedIn posts tagging @lablabai and @AlpacaHQ |

## lablab platform-wide submission checklist

| Requirement | Status | Evidence / next action |
|---|---|---|
| Project title, short/long description, tech tags | Ready | Content exists; paste into the form |
| 16:9 cover image | Met | `assets/crosssignal-hackathon-cover.png` |
| Video presentation (≤5 min, <300MB) | Met | Narrated walkthrough produced |
| Slide deck | Partial | `submission/CrossSignal-Hackathon-Pitch-Final.pdf` still cites 39 tests and contract `CS-20260831-66AAE940`; needs a refresh pass before submitting |
| Public GitHub repository | Met | github.com/omobolajiadeyan/alpaca-cross-market-agent, commits through 2026-09-01 |
| Demo application platform + URL | Met | crosssignal-ai-agent.streamlit.app, confirmed publicly reachable |
| Alpaca paper account ID | Ready | `PA3PDTUDIXDU` — add to form |
| Submit through lablab before deadline | Missing | Sep 4, 10:00 AM CDT |

## Verified product evidence (2026-09-01)

- 43 automated tests pass (up from 39 — added while fixing a real
  trade-direction bug, a partly-dead stability test, a misleading recovery
  state, and a silently-truncated falsification call).
- Stability testing is now genuinely 10-for-10 real perturbations (two of
  the original ten mutated a field the scoring engine never read).
- Falsification is confirmed running real Claude critiques per cycle
  (`source: claude-falsification-review`), not a canned fallback — this had
  been silently broken until fixed today.
- Five live cycles against the dedicated account on 2026-09-01 all correctly
  abstained, for legitimate reasons (confidence just under threshold after
  genuine adversarial review, or a live-data gap in options positioning) —
  not forced, not gamed.
- Three earlier paper spreads filled on 2026-08-25 are **historical evidence
  only** — that was a prior account and predates the dedicated-account
  requirement; it does not count toward P&L judging on `PA3PDTUDIXDU`.
- Credentials and local audit databases remain excluded from Git.

## Current-rule caveat

This audit reflects the official event PDF as read on 2026-09-01. Re-check
the authenticated dashboard and event Discord for any organizer update
issued after this date.
