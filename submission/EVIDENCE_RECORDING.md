# CrossSignal evidence recording package

This package produces credential-free 1080p source footage and seven evidence
screenshots from the bundled public judge replay. The short automation capture
is not the finished narrated submission video. It forces
`PUBLIC_DEMO_MODE=true` and `ALLOW_PAPER_EXECUTION=false`, never reads `.env`,
removes known credential variables from the child process, and never submits or
recovers orders.

## Record the evidence

From the repository root:

```bash
source venv/bin/activate
pip install -r requirements-recording.txt
playwright install chromium
python scripts/record_submission_evidence.py
```

Outputs are written to `recording-output/video/*.webm` and
`recording-output/screenshots/*.png`. To watch the automation as it records,
add `--headed`. To capture an already-running public-demo instance, use
`--no-launch --base-url URL` only after confirming that instance visibly says
`PUBLIC JUDGE MODE`.

Do not show the terminal, `.env`, GitHub Secrets, broker account identifiers, or
raw CI logs in the final submission. The green GitHub Actions run may be shown
as a browser page, but the strongest evidence is its downloaded secret-free
`summary.md` or `summary.json` artifact.

## Build the narrated 4:35 draft

After capturing the screenshots, run:

```bash
python scripts/build_narrated_submission.py
```

This uses a macOS system voice and the locally bundled Playwright `ffmpeg`
binary to create `recording-output/CrossSignal-Submission-Narrated.mp4`. The
builder verifies that the final duration is exactly 4:35. Review the entire
file before uploading, and replace the synthetic narration with your own voice
if the event requires the presenter to speak personally.

## Shot list and narration (4:35 target)

| Time | Picture | Narration |
|---|---|---|
| 0:00–0:25 | Deck title, then `01-landing.png` | “Markets reprice at different speeds. CrossSignal finds the disagreement, challenges it, and allows action only when the evidence and execution controls agree.” |
| 0:25–0:55 | Landing hero and six-lens message | “Six synchronized lenses cover equity volatility, rates, credit, realized volatility, rate expectations, and positioning. Every value carries provenance instead of hiding fallback data.” |
| 0:55–1:35 | `02-scorecard.png` | “Each decision separates signal quality, stability, execution quality, and outcome evidence. A strong thesis is not enough: deterministic execution checks still control authorization.” |
| 1:35–2:10 | `03-decision-replay.png` | “The replay freezes what was known, records the allegation and counterargument, seals the judgment, joins the broker lifecycle, and reveals the verdict only at the predetermined horizon.” |
| 2:10–2:45 | Proof-chain expanders and receipt control | “The contract preserves source integrity, quantified inconsistency, adversarial challenge, bounded perturbations, a SHA-256 seal, Greeks stress, catalyst context, and recovery state. The downloadable receipt is secret-free and independently verifiable.” |
| 2:45–3:15 | `04-proof-of-abstention.png` | “Here I weaken data integrity. CrossSignal fails closed. The latest connected Evidence Watch also abstained because fourteen of fifteen checks passed and option liquidity failed. Abstention is a correct governed outcome, not an error.” |
| 3:15–3:40 | `05-read-only-replay.png` | “The public demo replays a sanitized case without credentials or broker access. The execution toggle is disabled by deployment policy, so judges can inspect the workflow safely.” |
| 3:40–4:00 | Authorized case in Decision case, then execution ledger | “A separate verified paper case records three filled spreads from August 25. It demonstrates the order lifecycle without placing a new trade during this recording.” |
| 4:00–4:20 | `06-track-record.png` | “No decision disappears. The learning ledger keeps scored and pending theses and compares the sealed direction with inverse and cash counterfactuals.” |
| 4:20–4:35 | `07-security-boundary.png`, then closing slide | “The architecture keeps the language model away from broker calls, treats news as untrusted context, disables public mutations, and requires human approval for recovery. CrossSignal makes trading intelligence inspectable.” |

## Final evidence checklist

- Use the reviewed PDF/PPTX as the opening and closing frame; do not claim the
  public replay is live market data.
- Show both the verified filled case and the newer `ABSTAIN` case, keeping their
  labels visible.
- If showing Evidence Watch, state: `EVIDENCE_SEALED`, read-only, broker
  mutations disabled, and 14/15 deterministic checks passed.
- Keep the final edit under five minutes and export 1920×1080 H.264 MP4. The
  generated WebM is source footage; convert it in the editor or with:

```bash
ffmpeg -i recording-output/video/RECORDING.webm -c:v libx264 -pix_fmt yuv420p -an crosssignal-evidence.mp4
```

- Watch the entire export once, confirm text is legible, and confirm no secret,
  account number, order ID, notification, or unrelated browser tab appears.
- Uploading and submitting remain manual actions by the presenter.
