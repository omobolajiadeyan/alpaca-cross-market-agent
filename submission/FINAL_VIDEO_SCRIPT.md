# CrossSignal final video — live-demo cut

**Target runtime:** ~4:30 (produced cut: 3:46)
**Format:** 1920×1080, H.264 video, AAC audio, Microsoft Edge neural TTS narration
(edge-tts, `en-US-AndrewMultilingualNeural`) — there was no time before the
deadline to record a human voice-over, so this narration is read by the
same AI voice used in earlier drafts.
**Status:** Recorded. `scripts/build_lifecycle_video.py` renders this script
over real, cursor-driven recordings of the actual public deployment itself
(not a local copy or a mock-up) — the "Run agent" replay's six live-lens
cards and three-leg spread construction, the "Decision case" tab's ABSTAIN
verdict, and the "Track record" tab's real closed position — interleaved
with real code (`agent/position_manager.py`'s exit-rule evaluator and
broker-reconciliation function), a state-machine diagram of the four real
`PositionState` values, and real `59 passed` / `11 passed` test output. A
persistent presenter watermark and a step-progress bar run throughout.
Output: `recording-output/CrossSignal-Position-Lifecycle-Narrated.mp4`.

Structure follows a live-demo-first outline: state the real market problem,
explain the cross-market solution, then move to on-camera live evidence —
today's evaluation, why it abstained, how a spread would be constructed,
the complete position lifecycle, broker reconciliation, and the genuine
test suite — before an honest no-trade close.

## Narration and scene order

### Opening — the real market problem

> Markets rarely agree with themselves. Equities, credit, rates, and volatility
> often send conflicting signals about the same underlying risk, and most
> trading agents pick one confident number and act on it anyway. That's the
> real problem: a single strong signal is not proof of a real opportunity.
> I'm Omobolaji Adeyan, and this is CrossSignal.

### Solution — the cross-market architecture

> CrossSignal's answer is a cross-market solution. It synchronizes six live
> market lenses into one macro state, has Claude propose a structured thesis,
> then puts that thesis through independent deterministic checks —
> disagreement, stability, and execution risk — before anything is ever
> authorized. Claude never contacts the broker directly.

### Live evaluation — the six lenses, on camera

> Let's run today's evaluation live, on the actual public judge replay — the
> same page a judge would open. Six independent lenses source real market
> data: equity volatility, credit, rates, realized volatility, rate
> expectations, and positioning. Each is labeled and status-checked before
> anything downstream is allowed to trust it.

*Live: "Run agent" tab → "Replay sanitized judge case" → the six live-lens
data-provenance cards.*

### Why ABSTAIN — the courtroom, on camera

> Here is exactly why today's cycle landed on ABSTAIN. The Decision case tab
> reconstructs the allegation, the cross-examination, and the judgment in
> order. In this run, a real deterministic check failed the fixed bar — and
> CrossSignal refused to trade rather than force it through.

*Live: "Decision case" tab → scorecard → Decision Replay courtroom table.*

### Spread construction — a safe replay, on camera

> Even when a signal is strong, execution has its own gate. Watch the
> construction, live: a bearish credit spread, a defensive equity hedge, and
> a rates hedge — three legs, each preflighted against Greeks coverage,
> margin utilization, and option liquidity before anything could be
> submitted. Here, liquidity fell short on one leg, so nothing was.

*Live: "Run agent" tab, replayed → risk-decision checks → the three-leg
construction table (primary / secondary / hedge).*

### Position lifecycle — live, then the code and the state machine

> Now the complete position lifecycle, live. On the Track record tab, every
> submitted spread carries a persisted exit contract: take-profit,
> stop-loss, a five-day holding limit, and a pre-expiry close, valued
> against executable bids and asks every cycle. Underneath, deterministic
> code evaluates those four sealed thresholds with no broker side effects.
> And every position moves through one real state at a time: pending entry,
> open, exit pending, closed.

*Live: "Track record" tab → real closed position row → cuts to
`agent/position_manager.py`'s exit-rule evaluator → cuts to the
PENDING_ENTRY → OPEN → EXIT_PENDING → CLOSED state-machine diagram.*

### Broker reconciliation and the evidence record

> Before any exit reconciles, CrossSignal compares every registered leg
> against Alpaca's real broker inventory — a mismatch, and the cycle logs a
> reconciliation failure instead of trusting stale state. Every entry
> filled, exit submitted, and fill event is written to an append-only audit
> record, timestamped and independently inspectable.

*Real code: `agent/position_manager.py`'s `_broker_mismatches`.*

### The genuine test suite

> None of this is theoretical. Here is the genuine test suite running:
> fifty-nine automated tests covering authorization, pricing, profit and
> loss triggers, time and expiry exits, market-closed deferral, atomic leg
> reversal, audit persistence, and duplicate-order prevention.

*Real `59 passed` / `11 passed` pytest output.*

### Close — honest no-trade explanation and value proposition

> Honestly: against a fresh, dedicated hundred-thousand-dollar paper
> account, CrossSignal repeatedly found real disagreements but refused
> execution when the evidence didn't clear its own bar — so there is no
> competition P-and-L to show. That's not a demo failure; it's the
> discipline working as designed. CrossSignal proves when a trade deserves
> entry, manages it under rules fixed in advance, and proves why it exits.
> I'm Omobolaji Adeyan. Thank you.

*Real sealed-contract evidence card (no P&L), then the closing brand card.*

## Recording checklist

- All live segments are cursor-driven recordings of the actual public
  deployment (`crosssignal-ai-agent.streamlit.app`), not a local instance.
- Show the six live-lens data-provenance cards, the ABSTAIN courtroom, the
  three-leg spread construction, and the real closed position row — all on
  camera, not described only in narration.
- Show `agent/position_manager.py`'s exit-rule evaluator and broker
  reconciliation function, and the PENDING_ENTRY → OPEN → EXIT_PENDING →
  CLOSED state-machine diagram.
- Show `59 passed` in the terminal.
- State clearly that lifecycle and replay values are illustrative and the
  competition account has no fill or P&L evidence.
- Keep the rendered video at or below five minutes and recompute its
  SHA-256 afterward.
