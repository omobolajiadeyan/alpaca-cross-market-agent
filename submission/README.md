![CrossSignal](../assets/crosssignal-logo-lockup-light.png)

# CrossSignal final submission assets

The local upload bundle is `CrossSignal-Final-Submission-Package.zip`, generated
from the versioned sources by `scripts/build_final_package.py`. The assembled
ZIP, unpacked duplicate directory, and compiled MP4 remain outside Git because
they are delivery artifacts; the submission portal received the final video.
`EVIDENCE_RECORDING.md` records its exact duration and SHA-256 checksum.

Primary files:

- `CrossSignal-Hackathon-Pitch-Final.pdf` — eight-slide upload deck
- `CrossSignal-Hackathon-Pitch-Final.pptx` — editable deck source
- `CrossSignal-One-Page-Writeup.pdf` — required one-page technical write-up
- `ONE_PAGE_WRITEUP.md` — accessible source text
- `FINAL_VIDEO_SCRIPT.md` — reviewed script and video audit
- `EVIDENCE_RECORDING.md` — current evidence and no-trade justification
- `SUBMISSION_FORM_COPY.md` — paste-ready lablab form content
- `JUDGE_NO_TRADE_MEMO.md` — concise, defensible explanation of zero fills
- `Latest-Run-Evidence.json` — secret-free current-cycle summary

The final package intentionally excludes `.env`, the local audit database,
credentials, caches, raw broker responses, and obsolete video drafts.
