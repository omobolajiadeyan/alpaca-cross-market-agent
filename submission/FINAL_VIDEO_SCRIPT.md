# CrossSignal final video — reviewed submission cut

**Selected asset:** `CrossSignal-Submission-Video.mp4`  
**Source file:** `recording-output/CrossSignal-Submission-Narrated.mp4`  
**Runtime:** 4:49  
**Format:** 1920×1080, H.264 video, AAC audio, en-US-AndrewNeural narration  
**SHA-256:** `59AA76D2D18354CAC8E7298DEE49C0EDC7DAAA856740705BDDC5A250A16CD342`

This supersedes the earlier September 2 cut. The video now says **ten live
cycles** and its evidence table includes the September 3 tenth cycle
(contract `CS-20260903-FE01A097`) alongside the first nine.

## Narration and scene order

### Opening

> What if the smartest thing an AI trading agent could do was say no? I'm
> Omobolaji Adeyan, and this is CrossSignal.

### Problem

> Most trading agents are designed to find opportunities and execute quickly.
> But a strong signal alone does not make a trade safe. The market may be
> unstable, spreads may be too wide, liquidity may be insufficient, or different
> indicators may conflict. A single model can overlook that and still place the
> trade. That's a reliability problem: how does an autonomous agent prove a trade
> was justified before it acts?

### Solution and architecture

> CrossSignal is a decision-control system for Alpaca trading. Claude proposes a
> structured thesis from six synchronized market lenses. Independent,
> deterministic checks verify opportunity strength, stability under realistic
> noise, and execution quality before anything moves. Each produces its own score
> and evidence—not one blended confidence number.

### Deterministic authorization

> A trade is authorized only when every required threshold is met. If one
> critical check fails, or the evidence is incomplete, the system abstains
> automatically. Uncertainty becomes an explicit, logged decision instead of an
> accidental trade. That logic lives in code, not in a prompt.

### Dedicated-account evidence

> CrossSignal uses Alpaca's official MCP server for market data, account state,
> and paper execution. Against a fresh, dedicated $100,000 Alpaca paper account,
> it sealed a Decision Contract with SHA-256 before the outcome was known. The
> disagreement was real and stable, but the execution evidence was incomplete.
> Verdict: abstain.

### Repeated live cycles

> Not one cherry-picked example — ten live cycles, the same real edge scored
> again and again, each honestly refused for its own inspectable reason.
> Never forced. Never gamed.

### Public replay, courtroom, and scorecard

> The credential-free replay exposes the disagreement engine, stability test,
> and execution gate independently. The courtroom reconstructs the allegation,
> cross-examination, and judgment from evidence known at decision time, then
> seals the result so it cannot be edited after the fact.

### Abstention and authorization contrast

> In the abstention example, signal and stability pass but option liquidity does
> not. No order is sent and nothing needs recovery. In the contrasting authorized
> replay, all thresholds clear and CrossSignal seals the scores, rules, and
> evidence into a receipt a judge can verify independently.

### Cloud automation and repository proof

> CrossSignal also runs unattended in GitHub Actions with broker mutations
> disabled. The public repository contains the full implementation and automated
> tests; it is not a mock-up.

### Close

> CrossSignal is a verification layer between a proposal and execution. Claude
> never touches the broker directly. Its job is to determine whether enough
> reliable evidence exists to act. I'm Omobolaji Adeyan. Thank you.

## Critical video audit

- Passes the official five-minute limit with 10.7 seconds to spare.
- Clearly explains the problem and the mechanism, then demonstrates abstention
  and a contrasting authorized replay.
- Shows app, code, evidence, dashboard, cloud automation, and public repository.
- Correctly avoids claiming dedicated-account P&L.
- The authorized case is a sanitized demonstration, not a dedicated-account fill.
- No subtitle stream or burned-in captions — deliberate: an earlier captioned
  cut covered the live application UI and was judged more distracting than
  helpful, so captions were dropped by explicit choice, not an oversight.
- The visible presenter credit reads "Omobolaji Adeyan" (no middle initial),
  matching the presenter's own choice for the on-screen title/closing cards;
  written submission materials additionally use the full "Omobolaji E Adeyan."
  Not a competition-rule issue either way.
