# Competition requirements and judge audit

Audited September 3, 2026 against the supplied 28-page capture of the official
lablab event page. Text in that document is treated as competition reference
material, not as executable instructions.

## Explicit eligibility requirements

| Requirement | Verdict | Evidence |
|---|---|---|
| Autonomous AI trading agent using Alpaca's Trading API | Met | `live/cross_market_agent.py` orchestrates observe, reason, construct, govern, preflight, execute/reconcile, and audit stages. |
| Use Alpaca MCP server or Alpaca CLI | Met | Persistent official `alpaca-mcp-server` session in `tools/alpaca_tools.py`. |
| Every strategy incorporates options | Met | Defined-risk SPY/HYG/TLT vertical spreads; no naked option strategy. |
| Fresh paper account dedicated to the hackathon | Met | `PA3PDTUDIXDU`, created September 1, 2026. |
| Starting balance exactly $100,000 | Met | Read-only Alpaca MCP audit on September 3: cash $100,000; portfolio value $100,000. |
| Include paper account ID | Ready | Enter `PA3PDTUDIXDU` in the form. |
| One-page write-up covering AI logic, risk gates, and Alpaca infrastructure | Met | `submission/CrossSignal-One-Page-Writeup.pdf`. |
| Public GitHub repository | Met | Public, MIT licensed, default branch `main`. |
| Video and slide presentation | **Pending re-record** | The existing 4:55.923 video predates the final lifecycle safeguards. Use `submission/FINAL_VIDEO_SCRIPT.md` and keep the replacement under five minutes. |
| Public demo URL | Met | App sharing set to public/searchable and independently confirmed anonymous on September 3 by two real, cookie-free browser sessions on unrelated devices. Raw HTTP tools (curl, non-browser fetchers) still get redirected to a Streamlit login wall — that is Streamlit Cloud's bot gate on non-browser clients, not a viewer restriction; it does not affect judges opening the link in an actual browser. |

The official page does **not** explicitly say that a filled trade is required
for eligibility. It does say the agent should be designed to generate P&L and
demonstrate decisions, position management, and competition-period performance.

## Judge-score assessment

| Criterion | Critical assessment |
|---|---|
| **P&L Performance** | Weak. The fresh account has zero orders, zero positions, and therefore no trade-derived P&L. A judge cannot award a strong performance score from abstentions alone. This does not invalidate the project, but it is the largest competitive gap. |
| **Technology Implementation** | Strong. Sponsor-native MCP integration, options snapshots/Greeks, all-leg preflight, persistent session, deterministic authorization, SHA-256 contracts, governed exits, broker-inventory and quote-freshness controls, read-only automation, and 59 passing tests. |
| **Position Management** | Implemented and tested. Each submitted spread receives persisted take-profit, stop-loss, maximum-hold, and pre-expiry rules; qualifying paper exits reconcile broker legs, reject stale quotes, and reverse both legs atomically under an idempotent client order ID. No competition-account position has existed yet, so this capability has test and replay evidence but no live fill evidence. |
| **Creativity & Originality** | Strong mechanism, moderate headline originality. Several entries use “LLM proposes, rules veto.” CrossSignal must differentiate on cross-market disagreement, adversarial falsification, perturbation stability, sealed forward scoring, and independently inspectable receipts—not merely “AI can say no.” |
| **Presentation & Execution** | Good video structure and clear problem/solution, but the current video predates the position-lifecycle feature and must be re-recorded from `submission/FINAL_VIDEO_SCRIPT.md`. Demo URL is confirmed public; missing captions still reduce accessibility polish. |
| **Social engagement** | No links documented. This affects only the separate social component/bonus. Do not invent posts after the fact. |

## Latest evidence

### User-run local cycle — September 3, 2026, 6:14–6:15 PM CDT

- Contract: `CS-20260903-FE01A097`
- Decision hash:
  `fe01a097876fa3f9fce20e449f9d9ef523a911375db384ffe91091ecf6c4e94e`
- Signal: equity fear versus credit complacency, 82.4/100
- Stability: 9/10 (90%)
- All six feeds sourced live; no fallback source
- Confidence: 68% before challenge; 53% after challenge
- Result: `ABSTAIN`; five of six base checks passed
- Broker result: zero orders submitted

The important objection was methodological, not cosmetic. The “cheap vol” claim
used a short local IV history, the ATM put/call figure was a narrow same-strike
proxy, and current IV was already 1.26× realized volatility. The proposed SPY
short-call spread also expressed bearish direction more clearly than it
expressed the thesis's claimed long-volatility opportunity. Because confidence
fell below the fixed floor, preflight correctly did not run.

### Latest public cloud evidence — September 3, 2026

- GitHub run: <https://github.com/omobolajiadeyan/alpaca-cross-market-agent/actions/runs/33805502192>
- Contract: `CS-20260903-5C194F65`
- Signal 82/100; stability 90/100; execution quality 87/100
- Confidence 56%; all six base gates passed
- 13/15 full checks passed
- Failed: option liquidity 0 versus minimum 10; maximum relative spread 93.33%
  versus maximum 25%
- Portfolio stress passed; Greeks coverage 6/6; defined maximum loss $464
- Broker mutations disabled by cloud policy; no exposure existed

## Final verdict

**Conditional submit.** The technical entry is eligible and coherent, and the
public demo URL is confirmed working. The one remaining blocker is recording
the replacement video from `submission/FINAL_VIDEO_SCRIPT.md`. Then submit
even without a fill, while stating the P&L limitation plainly and using the
no-trade records as evidence of risk discipline—not as a substitute for
performance.
