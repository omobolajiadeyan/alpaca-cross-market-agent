![CrossSignal](../assets/crosssignal-logo-lockup-light.png)

# CrossSignal submission evidence record

## Selected video

- File: `CrossSignal-Submission-Video.mp4`
- Duration: 3:46.714
- Resolution: 1920×1080
- SHA-256: `762BF3996343548691BE287538CB3596C3D221F4C2113318D40EDCFE5D114BD7`
- Evidence date represented in video: through September 3, 2026
- Status: final live-demo-first position-lifecycle cut

The video combines cursor-driven recordings of the public judge deployment with
real code and genuine test output. Sanitized and simulated examples are labelled
as such; it does not claim an authorized case was filled on the dedicated
competition account.

## Latest local connected cycle

- Time: September 3, 2026, 6:14–6:15 PM CDT
- Contract: `CS-20260903-FE01A097`
- Decision hash:
  `fe01a097876fa3f9fce20e449f9d9ef523a911375db384ffe91091ecf6c4e94e`
- Signal quality: 82.4/100
- Stability: 90% (9/10)
- Confidence: 68% before challenge; 53% after challenge
- Base checks: 5/6
- Authorization: `ABSTAIN`
- Broker orders: 0

Reason: the falsification pass found that a short local IV history did not
support a robust “cheap volatility” claim, IV was 1.26× realized volatility,
and the ATM put/call ratio was narrower than a market-wide positioning measure.
Confidence fell below the fixed 55% minimum. Because the cycle ran after the
regular session, no after-hours option order should have been queued anyway.

## Latest unattended evidence

- GitHub run:
  <https://github.com/omobolajiadeyan/alpaca-cross-market-agent/actions/runs/33805502192>
- Contract: `CS-20260903-5C194F65`
- Mode: read-only live evidence; broker mutations disabled
- Scorecard: signal 82, stability 90, execution 87, outcome pending
- Full risk checks: 13/15
- Failed liquidity: 0 displayed contracts versus 10 required
- Failed bid-ask quality: 93.33% maximum relative spread versus 25% allowed
- Greeks coverage: 6/6
- Defined maximum loss: $464
- Exposure after decision: none

## Dedicated-account verification

Read-only Alpaca MCP audit on September 3:

- Cash: $100,000
- Portfolio value: $100,000
- Buying power: $400,000
- Open positions: 0
- Orders: 0

This proves the account is fresh and unused. It also means the project has no
competition-account P&L to claim. Historical August 25 fills belonged to a prior
account and are excluded from performance evidence.

## Privacy and integrity checklist

- No `.env`, API key, secret, raw order ID, or GitHub secret is packaged.
- Public artifacts contain only the paper account ID explicitly required by the
  competition.
- Local `trading_audit.db` is not part of the upload package.
- `Latest-Run-Evidence.json` is a curated, secret-free summary, not a raw database
  export.
