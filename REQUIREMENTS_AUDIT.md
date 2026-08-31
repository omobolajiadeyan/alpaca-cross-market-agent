# Requirements audit

Audited August 31, 2026 by and for **Omobolaji E Adeyan**.

This document separates requirements explicitly visible on the Alpaca event page from lablab-wide submission requirements and judging guidance. The event page may be expanded at kickoff; recheck it before final submission.

## Alpaca event page — explicit lines

Source: <https://lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon>

| Published line | Status | Evidence |
|---|---|---|
| Event is online | Met | Public judge application: <https://crosssignal-ai-agent.streamlit.app> |
| Dates: August 28–September 4, 2026 | Acknowledged | Submission checklist records the event window |
| Prize pool: $6,000 | Informational | No implementation action required |
| Build AI trading agents on Alpaca | Met | CrossSignal autonomously observes, reasons, constructs, governs, executes and audits |
| Use Alpaca Trading API, MCP server or CLI | Met | Official `alpaca-mcp-server` is used for market data, account access and multi-leg paper orders |

## lablab platform-wide participation requirements

Sources: <https://lablab.ai/guide> and <https://lablab.ai/ai-articles/hackathon-guidelines>

| Requirement | Status | Evidence / next action |
|---|---|---|
| Each participant enrolls independently | Met | Authenticated event dashboard shows Omobolaji Adeyan as enrolled |
| Participant belongs to a team, including solo entrants | Met | Authenticated event dashboard shows the solo team `CrossSignal` |
| Working prototype usable online | Met | Credential-free public judge replay is deployed on Streamlit Community Cloud |
| Project title, maximum 50 characters | Ready | `CrossSignal` |
| Short description, maximum 255 characters | Ready | Supplied in `SUBMISSION.md` |
| Long description, minimum 100 words | Ready | README/product documentation provides source content; paste into submission form |
| Main track/categories | Pending event form | Select the Alpaca/autonomous-agent track shown by the authenticated form |
| Technology tags | Ready | Alpaca MCP, Alpaca Trading API, Claude, Python, Streamlit, SQLite |
| 16:9 cover image | Met | `assets/crosssignal-hackathon-cover.png` |
| Video presentation, five minutes or less and under 300 MB | Missing | Recording script is complete; final recording/upload requires presenter action |
| Pitch deck / slide presentation | Met | Editable eight-slide PowerPoint and final PDF are versioned in `submission/` |
| Public GitHub repository | Met | <https://github.com/omobolajiadeyan/alpaca-cross-market-agent> |
| Demo application platform | Ready | Streamlit Community Cloud selected |
| Direct application URL | Met | <https://crosssignal-ai-agent.streamlit.app> |
| Submit through lablab before deadline | Missing | Requires authenticated final form submission |

## Judging guidance

Lablab’s general rubric lists four dimensions. These are judging guidance, not additional Alpaca-specific technical requirements.

| Dimension | Current evidence | Remaining improvement |
|---|---|---|
| Application of technology | Claude produces structured signals; Alpaca MCP supplies real data and filled paper orders | Show the workflow in the video |
| Presentation | Executive browser UI, cover, pitch and video outlines | Finalize deck and video |
| Business value | Defined-risk decision intelligence for active options traders and small investment teams | Add sourced TAM and pricing hypothesis to deck |
| Originality | Cross-market disagreement plus forward self-scoring and data provenance | Emphasize the accountability loop in the opening minute |

## Verified product evidence

- Thirty-five automated tests pass, including public-fixture integrity, broker-boundary, endpoint, redaction, untrusted-text and read-only cloud automation controls.
- The public replay now presents one authorized and one abstention contract through the same four-part decision scorecard.
- GitHub Actions Evidence Watch can collect fresh, secret-free decision evidence on schedule without paper-order authority.
- Three Alpaca multi-leg paper spreads filled on August 25, 2026.
- Three earlier theses received preliminary forward scores with a 66.7% short-horizon average hit rate.
- A fresh connected preview captured six Alpaca Greek snapshots and ten relevant headlines, then correctly abstained because option liquidity and bid-ask quality failed.
- Credentials and local trading databases are excluded from Git.
- Public mode disables all broker mutations; controlled local execution requires explicit authorization and the exact Alpaca paper endpoint.

## Current-rule caveat

The public event page does not publish numeric judging weights or a performance leaderboard criterion. The authenticated event dashboard and event Discord remain controlling sources for any organizer announcement made after this audit.
