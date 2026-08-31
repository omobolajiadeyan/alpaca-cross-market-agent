# Security and AI risk case

**Owner:** Omobolaji E Adeyan

**Scope:** CrossSignal hackathon prototype; Alpaca paper trading only
**Last reviewed:** August 31, 2026

CrossSignal applies selected outcomes from the voluntary NIST AI Risk
Management Framework (AI RMF 1.0), NIST SP 800-218 Secure Software Development
Framework (SSDF), NIST SP 800-53 Rev. 5 control families, and the adversarial
machine-learning taxonomy in NIST AI 100-2e2025. This is a tailored engineering
profile, not a claim of NIST certification, compliance attestation, or
independent assessment.

## System boundary and security objective

The system may read market, account, news, option and order data from Alpaca;
read public Treasury data; send structured market evidence to Claude; produce a
trade proposal; and, only in controlled local paper mode, submit or recover
paper orders. The primary objective is to prevent untrusted content or an LLM
output from becoming an unauthorized financial action.

The trust boundary is deliberate:

```text
untrusted market/news data → sanitize + provenance → LLM proposal
                                               ↓
                         deterministic risk + policy engine
                                               ↓
                sealed contract → explicit approval → paper MCP
                                               ↓
                         audit, reconcile, verify, score
```

## NIST AI RMF profile

| Function | CrossSignal decision | Why this route was chosen | Evidence |
|---|---|---|---|
| GOVERN | Named owner, paper-only purpose, risk limits, documented limitations | Financial actions require clear accountability and risk tolerance | `SECURITY.md`, `config.py`, Readiness/Security tabs |
| MAP | Threat model covers users, LLM, third-party news, broker, secrets and audit data | Narrow context makes risks measurable; public and local deployments have different privileges | Threat register below |
| MEASURE | Tests, provenance, confidence, perturbation stability, Greeks, liquidity, drawdown and receipt verification | Qualitative “be safe” instructions are not measurable controls | Test suite, Decision Contract, stress and risk tables |
| MANAGE | Fail closed, abstain, disable public execution, require approval and recover explicitly | High-impact failures should stop action, not silently degrade | Broker mutation guard, recovery state machine, audit ledger |

## Threat and control register

| ID | Threat | Route/decision | Reason | Residual risk |
|---|---|---|---|---|
| T1 | Public visitor submits an order | `PUBLIC_DEMO_MODE=true` disables execution controls in the UI and broker layer | UI-only disabling is insufficient; the broker wrapper independently requires authorization | Host administrator can change deployment secrets |
| T2 | Accidental live-money routing | Mutation guard accepts only `https://paper-api.alpaca.markets` | A separate key or checkbox cannot compensate for the wrong endpoint | DNS/TLS and Alpaca remain external dependencies |
| T3 | Prompt injection in news | Headlines are length-bounded, HTML-escaped and instruction-like strings are removed; news never authorizes | External prose is untrusted data, not executable instruction | Novel obfuscation may evade lexical detection; deterministic gates still isolate broker access |
| T4 | LLM hallucination places a trade | Claude cannot call Alpaca; permitted symbols and structures are deterministic | Least agency limits blast radius | A plausible but incorrect thesis can pass; falsification and scoring expose rather than eliminate this risk |
| T5 | Stale or fallback data | Data provenance is sealed and fallback evidence forces abstention | Unknown data quality must not be treated as certainty | Upstream data can be wrong while appearing live |
| T6 | Excessive or illiquid exposure | Loss, buying power, delta, vega, theta, margin, volume, spread and drawdown gates | Independent measurable limits are auditable | Greeks and scenario estimates depend on broker snapshots |
| T7 | Partial execution leaves exposure | Recovery state blocks new submissions; cancellation/closure is paper-only and requires approval | Automatic recovery can compound a broker incident | Cross-underlying atomicity is unavailable; intervention may still face market movement |
| T8 | Evidence rewritten after outcome | Canonical Decision Contract is SHA-256 sealed before submission and independently verifiable | Precommitment separates prediction from hindsight | Local database is not an external timestamp authority |
| T9 | Secret leakage | `.env`, databases and deployment secrets are excluded; persistence/export uses recursive redaction | Defense in depth reduces accidental publication | Secrets can still leak through screenshots or operator error |
| T10 | Vulnerable dependency | Versions are declared, tests run before release, and dependency scanning is a release requirement | NIST SSDF treats third-party components as part of product risk | No dependency scanner guarantees absence of vulnerabilities |
| T11 | Scheduled automation gains trading authority | Evidence Watch is read-only, fixes execution false, refuses mutation-enabled configuration, and exports only redacted evidence | Continuous evidence collection does not require continuous order authority | Repository administrators can alter workflow code or secrets; protected review remains an operator responsibility |

## SP 800-218 SSDF practices used

- **PO — Prepare the Organization:** security owner, scope, risk tolerance,
  deployment modes and incident decisions are documented.
- **PS — Protect the Software:** credentials and local evidence are excluded
  from source control; public deployments are read-only.
- **PW — Produce Well-Secured Software:** mutation checks exist at the broker
  boundary; untrusted text is sanitized; errors fail closed; security behavior
  has isolated tests.
- **RV — Respond to Vulnerabilities:** recovery and incident steps are defined;
  dependency findings must be triaged before release.

## SP 800-53 family mapping

This lightweight mapping communicates intent; it is not a full 800-53 control
assessment or baseline.

| Family | Implementation |
|---|---|
| AC — Access Control | Explicit mutation authorization, public read-only mode, least-agency LLM |
| AU — Audit and Accountability | Decision, risk, order, recovery and evaluation ledger |
| CM — Configuration Management | Environment-driven modes and reviewed risk thresholds |
| IA — Identification and Authentication | Alpaca/Anthropic credentials held outside source; no browser disclosure |
| IR — Incident Response | Partial-fill recovery states, cancel/close plan, no silent retry |
| RA — Risk Assessment | Threat register, disagreement/stability and execution risk measurements |
| SA — System and Services Acquisition | Official Alpaca MCP and declared third-party dependencies |
| SI — System and Information Integrity | Input sanitization, provenance, hashing, receipt verification, fail-closed behavior |

## Deployment rules

Public deployment:

```env
PUBLIC_DEMO_MODE=true
ALLOW_PAPER_EXECUTION=false
REQUIRE_LIVE_DATA=true
```

Public mode uses a bundled, sanitized evidence replay. It does not require
Alpaca or Anthropic credentials, does not contact the broker, and labels all
replayed values as historical demonstration evidence rather than live data.

Scheduled cloud observation:

```env
PUBLIC_DEMO_MODE=false
ALLOW_PAPER_EXECUTION=false
REQUIRE_LIVE_DATA=true
```

Evidence Watch reads encrypted GitHub Actions secrets, executes only
`run(execute=False)`, and retains a secret-free artifact for 14 days. Missing
credentials produce an explicit `CONFIGURATION_REQUIRED` artifact; they never
cause fallback data to be presented as live evidence. The workflow has
read-only repository permissions and no broker-mutation mandate.

Controlled local paper execution:

```env
PUBLIC_DEMO_MODE=false
ALLOW_PAPER_EXECUTION=true
APCA_API_BASE_URL=https://paper-api.alpaca.markets
```

Live Alpaca endpoints are intentionally rejected by the mutation boundary.

## Release evidence

Before every public release:

1. Run `python -m pytest -q`.
2. Run Python compilation and Streamlit AppTest.
3. Search tracked files for `.env`, databases, tokens and secret patterns.
4. Review dependency vulnerabilities and licenses.
5. Verify the public deployment cannot enable execution.
6. Download and verify a Decision Contract receipt.
7. Record known failures and residual risk instead of deleting them.

## Incident response

If a credential is exposed: disable the deployment, rotate Alpaca and model
keys, review Git history and logs, issue new deployment secrets, and document
the event. If unexpected broker exposure occurs: engage the recovery lock,
cancel active paper orders, inspect actual positions, obtain explicit approval
before closure, reconcile final state, preserve evidence, and add a regression
test before re-enabling mutation.

## Authoritative references

- NIST AI RMF 1.0: <https://doi.org/10.6028/NIST.AI.100-1>
- NIST AI RMF Playbook: <https://airc.nist.gov/airmf-resources/playbook/>
- NIST SP 800-218 SSDF 1.1: <https://doi.org/10.6028/NIST.SP.800-218>
- NIST SP 800-53 Rev. 5: <https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final>
- NIST AI 100-2e2025: <https://doi.org/10.6028/NIST.AI.100-2e2025>
