![CrossSignal](https://raw.githubusercontent.com/omobolajiadeyan/alpaca-cross-market-agent/main/assets/crosssignal-logo-lockup-light.png)

# CrossSignal — final submission package

CrossSignal is an auditable cross-market options agent. It converts disagreement
across equities, credit, rates and volatility into defined-risk Alpaca paper
decisions, then manages every eligible spread under exit rules sealed at entry.

## Primary judge assets

1. `CrossSignal-Cover.png` — final 16:9 branded cover.
2. `CrossSignal-Submission-Video.mp4` — final 3:46 live-demo-first walkthrough.
3. `CrossSignal-Hackathon-Pitch-Final.pdf` — eight-slide presentation.
4. `CrossSignal-One-Page-Writeup.pdf` — required one-page technical write-up.

The video is the current position-lifecycle cut. It shows the public judge
replay, six market lenses, the binding ABSTAIN gate, three-spread construction,
the illustrative lifecycle demonstration, real source code and the verified
59-test suite. It does not predate position management and does not need to be
replaced.

## Links and account

- Judge demo: <https://crosssignal-ai-agent.streamlit.app>
- Source: <https://github.com/omobolajiadeyan/alpaca-cross-market-agent>
- Alpaca paper account: `PA3PDTUDIXDU`
- Evidence Watch: <https://github.com/omobolajiadeyan/alpaca-cross-market-agent/actions/runs/33805502192>

## Evidence boundary

The dedicated $100,000 competition account had zero orders, zero positions and
therefore no P&L to claim at the submission cutoff. Connected cycles abstained
because adversarial confidence or executable-liquidity evidence failed fixed
thresholds. CrossSignal did not weaken those controls to manufacture a trade.

The public dashboard contains a sanitized decision replay and a clearly marked
simulated lifecycle scenario. Those values demonstrate policy and state
transitions; they are not broker fills or competition-account performance.

## Supplemental evidence

- `Latest-Run-Evidence.json` — secret-free evidence and exact video metadata.
- `JUDGE_NO_TRADE_MEMO.md` — concise explanation of zero orders.
- `REQUIREMENTS-AUDIT.md` — requirement-by-requirement review.
- `FINAL_VIDEO_SCRIPT.md` — narration and scene evidence map.
- `CHECKSUMS.sha256` — integrity hashes for every packaged file.
- `CrossSignal-Competitive-Research-and-Enhancement-Report.pdf` — design research.

## Safety

No credential, `.env`, local database, raw broker response or private order ID
is included. The public application and cloud Evidence Watch are read-only.
Broker mutation requires the Alpaca paper endpoint and explicit local switches.
