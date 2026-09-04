# CrossSignal — final upload package

## Upload these files

1. `CrossSignal-Cover.png` — 16:9 cover image
2. `CrossSignal-Submission-Video.mp4` — replace with the new position-lifecycle recording before upload
3. `CrossSignal-Hackathon-Pitch-Final.pdf` — eight-slide presentation
4. `CrossSignal-One-Page-Writeup.pdf` — required one-page technical write-up

## Paste into the submission form

Use `SUBMISSION_FORM_COPY.md` for the project title, descriptions, tags, URLs,
account ID, and disclosure.

Required paper account ID: `PA3PDTUDIXDU`

## Supplemental judge evidence

- `JUDGE_NO_TRADE_MEMO.md`
- `CrossSignal-Competitive-Research-and-Enhancement-Report.pdf`
- `Latest-Run-Evidence.json`
- `CHECKSUMS.sha256`
- `CrossSignal-Hackathon-Pitch-Final.pptx` if an editable deck is useful

## App public-access check

An earlier automated check flagged the Streamlit demo as requiring a login.
Re-verified 2026-09-03 via three independent methods (curl with a real cookie
jar and browser user-agent, and 10+ real headless-Chromium page loads during
video rendering, all of which reached "PUBLIC JUDGE MODE" content directly):
the app is genuinely public. The earlier flag was almost certainly a naive
fetcher tripping Streamlit's bot-detection interstitial, not a real access
problem. Still worth a manual private-window check before submitting, but this
is not a blocker.

## Evidence boundary

The code, dashboard, deck, write-up, and submission copy now include governed
take-profit, stop-loss, maximum-hold, and pre-expiry exits. The existing video
predates that feature and must be replaced using `FINAL_VIDEO_SCRIPT.md`; do not
upload the old video as the final representation of the project. The dedicated
account has zero orders and zero positions, so the submission makes no P&L
claim. The dashboard lifecycle example is illustrative policy evidence, not a
competition-account fill.

The final monitor also reconciles registered legs with Alpaca, rejects stale
quote timestamps, identifies each atomic exit attempt with a deterministic
client order ID, exposes realized lifecycle metrics, and provides an independent
new-entry kill switch. These are reliability controls; they do not change the
cross-market signal objective.
