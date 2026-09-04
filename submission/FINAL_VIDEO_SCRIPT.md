# CrossSignal final video — position-lifecycle cut

**Target runtime:** 4:35–4:55  
**Format:** 1920×1080, H.264 video, AAC audio, human narration  
**Status:** Re-record required. The existing 4:55.923 video was produced before the position-lifecycle feature and does not demonstrate exits.

## Narration and scene order

### 0:00–0:15 — Opening

> What if the smartest thing an AI trading agent could do was say no—and, when
> it says yes, know exactly how to get out? I'm Omobolaji Adeyan, and this is
> CrossSignal.

### 0:15–0:48 — Problem

> Most trading agents focus on finding an opportunity and entering quickly. But
> a strong signal alone does not make a safe trade. Market data may conflict,
> liquidity may be poor, or the spread may be too wide. And entry is only half
> the problem. Without an explicit take-profit, stop-loss, time limit, and
> expiry rule, a valid entry can become unmanaged risk. An autonomous agent must
> justify both why it entered and why it stayed or exited.

### 0:48–1:20 — Solution and architecture

> CrossSignal is an auditable decision and position-management system for Alpaca
> paper trading. It synchronizes six market lenses. Claude proposes a structured
> thesis and attacks its own case. Independent deterministic code measures the
> disagreement, tests stability, checks risk and execution quality, and has final
> authority. Claude never contacts the broker.

### 1:20–1:58 — Entry governance

> Before any order, CrossSignal verifies live-data integrity, confidence,
> maximum loss, buying power, diversification, Greeks coverage, portfolio stress,
> liquidity, bid-ask quality, and drawdown. Every authorized decision is sealed
> into a SHA-256 Decision Contract before submission. If one critical control
> fails, the outcome is ABSTAIN—not a forced trade.

### 1:58–2:38 — Position lifecycle and exits

> Governance now continues after entry. Every submitted vertical spread stores
> its two option legs, fill price, maximum profit, maximum loss, expiry, and four
> exit rules. By default, it takes profit at fifty percent of maximum profit,
> cuts the position at fifty percent of defined maximum loss, exits after five
> trading days, or closes two calendar days before expiry. The monitor first
> reconciles every registered leg against Alpaca, then values the complete spread
> using executable bids and asks. Stale quotes cannot trigger an order. When a
> rule fires, it reverses both legs in one atomic Alpaca multi-leg limit order
> with a deterministic client order ID. An atomic claim and EXIT_PENDING state
> prevent duplicate closes, while every recommendation, deferral, submission,
> and fill remains auditable.

### 2:38–3:08 — Safety boundary

> Exit automation is independently gated. It requires the exact Alpaca paper
> endpoint, entry authorization, a second automated-exit switch, valid quotes,
> and an open Alpaca market clock. The public judge application and scheduled
> GitHub Evidence Watch are read-only. Emergency recovery for a broken entry
> remains separate and human-approved. A dedicated kill switch can pause new
> entries while continuing to manage positions already open.

### 3:08–3:42 — Dedicated-account evidence and no-trade decision

> Against a fresh one-hundred-thousand-dollar competition paper account,
> CrossSignal repeatedly found real disagreements but refused execution when
> adversarial confidence or after-hours liquidity failed fixed thresholds. The
> account therefore has no competition P-and-L to claim. That is a competitive
> limitation, but it is honest evidence that the controls were not weakened to
> manufacture a trade.

### 3:42–4:20 — Dashboard and proof

> The dashboard exposes the decision courtroom, risk scorecard, entry ledger,
> and the new position lifecycle. Judges can inspect each sealed policy and each
> state transition from pending entry, to open, to exit pending, to closed. The
> public example is explicitly labeled as an illustrative policy demonstration,
> not broker fill evidence.

### 4:20–4:42 — Repository and tests

> The public repository contains the complete implementation, not a mock-up.
> Fifty-nine automated tests cover authorization, pricing, profit and loss
> triggers, time and expiry exits, market-closed deferral, atomic leg reversal,
> audit persistence, privacy, and duplicate-order prevention.

### 4:42–4:55 — Close

> CrossSignal proves when a trade deserves entry, manages it under rules fixed in
> advance, and proves why it exited. I'm Omobolaji Adeyan. Thank you.

## Recording checklist

- Show `agent/position_manager.py`, `tools/alpaca_tools.py`, and the lifecycle table.
- Show the four dollar/time exit thresholds, broker reconciliation, quote freshness,
  deterministic client order ID, entry kill switch, and `EXIT_PENDING` control.
- State clearly that the lifecycle replay is illustrative and the competition account has no fill or P&L evidence.
- Show `59 passed` in the terminal.
- Keep the rendered video at or below five minutes and recompute its SHA-256 afterward.
