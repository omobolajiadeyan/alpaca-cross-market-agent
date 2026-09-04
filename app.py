"""Judge-facing browser experience for the Cross-Market Macro Agent."""

import html
import json
import sys
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    # Live agent code paths (AlpacaTools, etc.) print checkmark characters
    # outside the default Windows console codepage; force UTF-8 so a local
    # "Run agent" click can't crash on that.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import pandas as pd
import streamlit as st

from compliance.audit_logger import AuditLogger
from agent.evidence_protocol import (
    EvidenceReceiptBuilder, PaperRecoveryExecutor, decision_scorecard,
)
from demo.judge_fixture import judge_dashboard
from config import (ALLOW_PAPER_EXECUTION, PUBLIC_DEMO_MODE, REQUIRE_LIVE_DATA,
                    ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL,
                    ENABLE_AUTOMATED_PAPER_EXITS)
from security.controls import security_posture


ASSET_DIR = Path(__file__).resolve().parent / "assets"

st.set_page_config(
    page_title="CrossSignal — AI Macro Trading Agent",
    page_icon=str(ASSET_DIR / "crosssignal-logo-mark.png"),
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');
:root { --ink:#071d49; --body:#263f58; --muted:#465d73; --canvas:#f3f6fa; --surface:#fff; --ice:#eaf1f6; --cyan:#079fc4; --light-cyan:#72d4e8; --blue:#003b70; --navy:#031126; --line:#c9d7e2; --amber:#f6b84a; }
.stApp { background:var(--canvas); color:var(--ink); font-family:'DM Sans',sans-serif; }
[data-testid="stHeader"] { background:transparent; }
.block-container { max-width:1380px; padding-top:.75rem; padding-bottom:4rem; overflow-x:hidden; }
h1,h2,h3 { font-family:'Manrope',sans-serif !important; letter-spacing:-.04em !important; }
.stMarkdown p,.stMarkdown li { color:var(--body); line-height:1.65; }
.nav { display:flex; justify-content:space-between; align-items:center; padding:.5rem 0 .8rem; border-bottom:1px solid var(--line); }
.brand-lockup{display:flex;align-items:center;gap:.65rem}.brand-lockup svg{width:42px;height:42px}.brand-name{font:800 1.05rem Manrope;letter-spacing:-.035em}.brand-sub{display:block;color:var(--muted);font-size:.6rem;letter-spacing:.1em;margin-top:.08rem}
.nav-note { color:var(--muted); font-size:.78rem; font-weight:600; }
.hero { margin:1rem 0 0; padding:2rem 2.25rem; background:radial-gradient(circle at 88% 18%,#0b4262 0,transparent 30%),linear-gradient(125deg,#031126,#071d49); color:#fff; position:relative; overflow:hidden; display:grid;grid-template-columns:minmax(0,1.65fr) minmax(270px,.72fr);gap:2rem;align-items:center;border-radius:16px 16px 0 0; }
.hero:after { content:''; position:absolute; width:360px; height:360px; border:1px solid rgba(114,212,232,.25); border-radius:50%; right:-185px; top:-150px; box-shadow:0 0 0 42px rgba(25,181,216,.035),0 0 0 90px rgba(25,181,216,.025); }
.eyebrow { display:inline-block; border-left:3px solid var(--cyan); padding:.1rem 0 .1rem .75rem; font-size:.72rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:#b9dced; }
.hero h1 { font-size:clamp(2.35rem,4vw,3.9rem); line-height:1; max-width:820px; margin:.8rem 0 .9rem; position:relative; z-index:1; }
.hero h1 em { color:#72d4e8; font-style:normal; }
.hero .hero-copy { max-width:720px; color:#e7f1f6!important; font-size:1rem; line-height:1.55; position:relative; z-index:1; margin:0; }
.hero-status{position:relative;z-index:2;background:rgba(1,12,29,.78);border:1px solid rgba(114,212,232,.34);border-radius:12px;padding:1rem 1.1rem;backdrop-filter:blur(8px)}
.hero-status-label{color:#9bcbd9;font-size:.65rem;letter-spacing:.13em;text-transform:uppercase;font-weight:700}.hero-verdict{font:800 2rem Manrope;color:var(--amber);margin:.4rem 0 1rem}.hero-row{display:flex;justify-content:space-between;gap:1rem;border-top:1px solid rgba(255,255,255,.1);padding:.72rem 0;color:#d7e7f0;font-size:.78rem}.hero-row strong{color:#fff;text-align:right}
.proof-grid { display:grid; grid-template-columns:repeat(4,1fr); background:var(--surface); border:1px solid var(--line);border-top:0; margin:0 0 1rem;border-radius:0 0 16px 16px;overflow:hidden;box-shadow:0 12px 32px rgba(7,29,73,.07); }
.proof { padding:1rem 1.35rem; border-right:1px solid var(--line); }.proof:last-child{border-right:0}.proof b { display:block; font:700 1rem Manrope; margin-bottom:.18rem; color:var(--ink); }.proof span { color:var(--muted); font-size:.78rem; }
.judge-route{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:1rem 0 2rem}.route-step{background:#fff;border:1px solid var(--line);border-radius:12px;padding:1rem 1.15rem;box-shadow:0 5px 16px rgba(7,29,73,.04)}.route-step i{font-style:normal;display:inline-grid;place-items:center;width:26px;height:26px;border-radius:50%;background:var(--navy);color:#fff;font-weight:700;font-size:.75rem;margin-right:.55rem}.route-step b{font:700 .92rem Manrope;color:var(--ink)}.route-step span{display:block;color:var(--muted);font-size:.82rem;margin:.55rem 0 0 2.1rem;line-height:1.5}
.section-label { color:#006f91; font-size:.74rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }
.card { background:#fff; border:1px solid var(--line); border-radius:12px; padding:1.4rem; height:100%; box-shadow:0 8px 24px rgba(7,29,73,.05); }
.card h3{color:var(--ink);margin-top:0}.card p{color:var(--body)!important;font-size:.94rem;line-height:1.6;margin-bottom:0}
.evidence-detail{display:grid;grid-template-columns:150px minmax(190px,.7fr) minmax(280px,1.5fr);gap:1px;background:#28425a;border:1px solid #28425a;border-left:5px solid var(--cyan);border-radius:10px;overflow:hidden;margin:.65rem 0 1.5rem}.evidence-detail>div{background:var(--navy);padding:1rem 1.1rem;min-height:105px}.evidence-detail span,.protocol-detail span{display:block;color:#83d7e8;font-size:.67rem;font-weight:800;letter-spacing:.1em;margin-bottom:.5rem}.evidence-detail strong{display:block;color:#fff;font:800 2rem Manrope}.evidence-detail strong small{font-size:.8rem;color:#b9dced}.evidence-detail b{color:#fff;font:700 1rem Manrope}.evidence-detail p{color:#dcebf2!important;font-size:.85rem;line-height:1.5;margin:.25rem 0 0}.protocol-detail{background:#fff;border:1px solid var(--line);border-left:5px solid var(--cyan);border-radius:9px;padding:1rem 1.15rem;margin:.65rem 0 1rem}.protocol-detail span{color:#007c9f}.protocol-detail b{display:block;color:var(--ink);font:800 1rem Manrope}.protocol-detail p{color:var(--body)!important;margin:.3rem 0 0}
[data-testid="stPills"],[data-testid="stSegmentedControl"]{margin:.2rem 0 .45rem}
.status-live,.status-fallback,.status-neutral { display:inline-block; padding:.27rem .55rem; border-radius:99px; font-size:.68rem; font-weight:700; text-transform:uppercase; }
.status-live { background:#dff8e8;color:#17653b }.status-fallback {background:#fff0cc;color:#8a5600}.status-neutral{background:#e8f2f8;color:#315b75}
.mode-banner{display:flex;align-items:center;gap:.75rem;background:#e5f1fa;border:1px solid #b9d2e4;border-left:4px solid var(--blue);border-radius:9px;padding:.7rem .9rem;margin:.75rem 0 1rem;color:#153a5a;font-size:.83rem;line-height:1.45}.mode-dot{width:9px;height:9px;border-radius:50%;background:#17875d;box-shadow:0 0 0 4px rgba(23,135,93,.12);flex:0 0 auto}.mode-banner strong{font:800 .72rem Manrope;letter-spacing:.06em;white-space:nowrap}.mode-banner span{color:#33566f}.mode-banner b{margin-left:auto;background:#fff;border:1px solid #afc8da;border-radius:99px;padding:.25rem .55rem;font-size:.67rem;letter-spacing:.05em;white-space:nowrap}
.thesis { background:var(--blue); color:#fff; padding:2rem; border-left:5px solid var(--cyan); margin:1rem 0; }
.thesis p { color:#d7e7f0; line-height:1.65; }.thesis .confidence { color:#72d4e8; font:700 .8rem Manrope; }
div.stButton > button { border-radius:9px; border:0; background:var(--blue); color:white; font-weight:700; min-height:3rem; }
div.stButton > button:hover { background:var(--navy); color:#fff; }
[data-testid="stMetric"] { background:#fff; border:1px solid var(--line); border-top:3px solid var(--cyan); border-radius:10px; padding:1rem; box-shadow:0 4px 14px rgba(7,29,73,.035); }
[data-testid="stMetricLabel"] p{color:#40576e!important;font-weight:700!important;font-size:.8rem!important}
[data-testid="stMetricValue"]{color:var(--ink)!important;font-family:'Manrope',sans-serif!important}
[data-testid="stCaptionContainer"] p{color:#435b72!important;font-size:.88rem!important;line-height:1.55!important}
[data-testid="stAlert"] p{color:inherit!important;font-weight:500}
[data-testid="stExpander"]{background:#fff;border-color:var(--line)!important;border-radius:10px!important}
[data-testid="stExpander"] summary p{color:var(--ink)!important;font-weight:700!important}
label p{color:#203a53!important;font-weight:650!important}
.footer { border-top:1px solid var(--line); margin-top:4rem; padding-top:1.5rem; color:var(--muted); font-size:.78rem; }
[data-testid="stTabs"] [role="tablist"] { gap:.3rem!important; overflow-x:auto!important; scrollbar-width:thin; background:#e5edf3!important; border:1px solid #c4d3df; border-radius:12px; padding:.38rem!important; position:sticky!important; top:.45rem; z-index:50; box-shadow:0 8px 22px rgba(7,29,73,.12); }
[data-testid="stTabs"] [data-testid="stTab"] { white-space:nowrap; min-width:max-content; min-height:2.75rem; padding:.55rem .95rem!important; border-radius:8px; color:#29465f!important; font-size:.86rem; font-weight:750; }
[data-testid="stTabs"] [data-testid="stTab"] p{color:inherit!important;font-weight:inherit!important}
[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"]{background:var(--navy)!important;color:#fff!important;box-shadow:0 4px 12px rgba(3,17,38,.22)}
[data-testid="stTabs"] .react-aria-SelectionIndicator{display:none!important}
[data-testid="stTabs"] [role="tabpanel"]{padding-top:1.15rem}
[data-testid="stDataFrame"] { border:1px solid var(--line); }
button:focus-visible,[role="tab"]:focus-visible { outline:3px solid rgba(25,181,216,.45)!important; outline-offset:2px; }
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important;animation:none!important}}
@media(max-width:900px){
  .block-container{padding:1rem 1.25rem 3rem}.proof-grid{grid-template-columns:repeat(2,1fr)}.proof:nth-child(2){border-right:0}.judge-route{grid-template-columns:1fr}
  .hero{padding:1.75rem 1.5rem;grid-template-columns:1fr}.hero:after{width:250px;height:250px;right:-160px;top:-120px}.hero h1{font-size:clamp(2.25rem,8vw,3.25rem)}
  .nav-note{display:none}.card{margin-bottom:.5rem}.evidence-detail{grid-template-columns:1fr 1fr}.evidence-detail>div:last-child{grid-column:1/-1}
}
@media(max-width:520px){
  .block-container{padding:.55rem .72rem 2rem}.hero{margin-top:.75rem;padding:1.5rem 1.1rem}.hero-copy{font-size:.94rem}.hero-status{padding:.9rem}.hero-verdict{font-size:1.6rem}
  .proof-grid{grid-template-columns:1fr}.proof{padding:1.25rem;border-right:0;border-bottom:1px solid var(--line)}.nav{padding:.5rem 0 1rem}[data-testid="stMetric"]{padding:.75rem}
  h1{font-size:2.05rem!important}h2{font-size:1.55rem!important}.footer{line-height:1.6}.mode-banner{align-items:flex-start;flex-wrap:wrap}.mode-banner b{margin-left:1.4rem}.evidence-detail{grid-template-columns:1fr}.evidence-detail>div:last-child{grid-column:auto}[data-testid="stTabs"] [data-testid="stTab"]{padding:.5rem .75rem!important;font-size:.8rem}
}
</style>
""", unsafe_allow_html=True)


def badge(status):
    kind = 'live' if status == 'live' else ('fallback' if status == 'fallback' else 'neutral')
    return f'<span class="status-{kind}">{status}</span>'


def brand_mark_svg() -> str:
    """Inline mark keeps the public header crisp without an external request."""
    return """<svg viewBox="0 0 72 72" aria-hidden="true"><g fill="none" stroke-linecap="round" stroke-width="3"><path d="M5 10 C22 10 23 31 34 35" stroke="#19b5d8" opacity=".55"/><path d="M5 20 C20 20 25 32 34 35" stroke="#19b5d8" opacity=".72"/><path d="M5 30 C20 30 26 34 34 35" stroke="#72d4e8"/><path d="M5 42 C20 42 26 38 34 37" stroke="#72d4e8"/><path d="M5 52 C20 52 25 40 34 37" stroke="#19b5d8" opacity=".72"/><path d="M5 62 C22 62 23 41 34 37" stroke="#19b5d8" opacity=".55"/><path d="M42 36 H67" stroke="#19b5d8" stroke-width="4"/></g><path d="M38 29 L45 36 L38 43 L31 36 Z" fill="#071d49" stroke="#72d4e8" stroke-width="2.5"/><circle cx="38" cy="36" r="2.6" fill="#f6b84a"/><circle cx="67" cy="36" r="2.7" fill="#72d4e8"/></svg>"""


def fmt(value, suffix=""):
    if value is None:
        return "—"
    return f"{value:,.2f}{suffix}" if isinstance(value, (int, float)) else str(value)


def render_disagreement_map(disagreement):
    """Render an accessible, native evidence explorer."""
    candidates = disagreement.get('candidates', [])
    if not candidates:
        st.info("No cross-market disagreements were recorded for this decision.")
        return

    labels = [item['title'] for item in candidates]
    selected_label = st.pills(
        "Inspect a market disagreement",
        labels,
        default=labels[0],
        selection_mode="single",
        key="market-disagreement-selector",
    ) or labels[0]
    selected = next(item for item in candidates if item['title'] == selected_label)
    st.markdown(
        f"""
        <div class="evidence-detail">
          <div><span>DISAGREEMENT SCORE</span><strong>{float(selected['score']):.0f}<small>/100</small></strong></div>
          <div><span>EXPECTED REPRICING</span><b>{html.escape(str(selected['repricing_market']))}</b><p>{html.escape(str(selected['direction']))}</p></div>
          <div><span>WHY IT MATTERS</span><p>{html.escape(str(selected['explanation']))}</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_protocol_journey(contract, execution_status):
    """Render a native, keyboard-accessible decision-lifecycle walkthrough."""
    quality_ok = contract.get('data_quality', {}).get('all_live', False)
    stability_ok = contract.get('stability', {}).get('score', 0) >= .60
    authorized = contract.get('authorization') == 'AUTHORIZED'
    execution_done = execution_status in ('filled', 'submitted', 'preview', 'abstained')
    stages = [
        {'name': 'Sources', 'ok': quality_ok, 'copy': 'Market inputs passed provenance and fallback checks.'},
        {'name': 'Signal', 'ok': contract['disagreement']['score'] >= 55, 'copy': f"The leading disagreement scored {contract['disagreement']['score']:.0f} out of 100."},
        {'name': 'Challenge', 'ok': True, 'copy': 'A falsification review challenged the thesis and adjusted confidence.'},
        {'name': 'Stability', 'ok': stability_ok, 'copy': f"The conclusion survived {contract['stability']['stable_cases']} of {contract['stability']['total_cases']} perturbations."},
        {'name': 'Contract', 'ok': authorized, 'copy': f"The decision was sealed as {contract['authorization']} before submission."},
        {'name': 'Execution', 'ok': execution_done, 'copy': f"Broker lifecycle state: {execution_status}."},
    ]
    decision_hash = contract['decision_hash']
    passed = sum(stage['ok'] for stage in stages)
    st.subheader("Follow the decision from evidence to execution")
    st.progress(passed / len(stages), text=f"{passed} of {len(stages)} controls complete")
    stage_names = [stage['name'] for stage in stages]
    selected_name = st.segmented_control(
        "SIGNAL protocol stage",
        stage_names,
        default=stage_names[0],
        selection_mode="single",
        key=f"protocol-stage-{decision_hash[:12]}",
        label_visibility="collapsed",
    ) or stage_names[0]
    selected = next(stage for stage in stages if stage['name'] == selected_name)
    state = "CONTROL PASSED" if selected['ok'] else "BINDING CONTROL"
    st.markdown(
        f'<div class="protocol-detail"><span>{state}</span><b>{html.escape(selected_name)}</b><p>{html.escape(selected["copy"])}</p></div>',
        unsafe_allow_html=True,
    )
    st.caption("SEALED PROOF · SHA-256 decision contract")
    st.code(decision_hash, language=None)


logger = AuditLogger()
dashboard = judge_dashboard() if PUBLIC_DEMO_MODE else logger.get_dashboard_data()
broker_mutations_enabled = ALLOW_PAPER_EXECUTION and not PUBLIC_DEMO_MODE

st.markdown(
    f'<div class="nav"><div class="brand-lockup">{brand_mark_svg()}<div><div class="brand-name">CROSSSIGNAL</div><span class="brand-sub">AUDITABLE OPTIONS INTELLIGENCE</span></div></div><div class="nav-note">BUILT BY OMOBOLAJI E ADEYAN · ALPACA PAPER TRADING</div></div>',
    unsafe_allow_html=True,
)

if PUBLIC_DEMO_MODE:
    st.markdown("""
    <div class="mode-banner" role="status">
      <i class="mode-dot" aria-hidden="true"></i>
      <strong>PUBLIC JUDGE MODE</strong>
      <span>Sanitized historical replay from a verified Alpaca paper workflow—not live quotes.</span>
      <b>READ ONLY · NO BROKER ACCESS</b>
    </div>
    """, unsafe_allow_html=True)

latest_contract_row = (dashboard.get('contracts') or [{}])[0]
latest_contract = latest_contract_row.get('contract', {})
latest_verdict = latest_contract.get('authorization', 'NO DECISION')
latest_id = latest_contract.get('contract_id', 'Pending')
latest_reasons = latest_contract.get('authorization_reasons') or ['No failed gate recorded.']
latest_reason = html.escape(str(latest_reasons[0]))
binding_control = str(latest_reasons[0]).split(':', 1)[-1].strip().title()
deployment_mode = 'READ-ONLY REPLAY' if PUBLIC_DEMO_MODE else 'CONTROLLED LOCAL MODE'

st.markdown(f"""
<div class="hero">
  <div><span class="eyebrow">Six markets · one governed decision</span>
  <h1>Markets disagree.<br><em>We verify the trade.</em></h1>
  <p class="hero-copy">CrossSignal converts conflicts across equities, credit, rates and volatility into defined-risk Alpaca options decisions—and proves why each trade entered, exited or was refused.</p></div>
  <aside class="hero-status"><div class="hero-status-label">Latest sealed decision</div><div class="hero-verdict">{html.escape(str(latest_verdict))}</div><div class="hero-row"><span>Contract</span><strong>{html.escape(str(latest_id))}</strong></div><div class="hero-row"><span>Binding control</span><strong title="{latest_reason}">{html.escape(binding_control)}</strong></div><div class="hero-row"><span>Deployment</span><strong>{deployment_mode}</strong></div></aside>
</div>
<div class="proof-grid">
  <div class="proof"><b>6 market lenses</b><span>One synchronized macro state.</span></div>
  <div class="proof"><b>15 execution checks</b><span>One failure blocks submission.</span></div>
  <div class="proof"><b>4 exit rules</b><span>Profit, loss, time and expiry.</span></div>
  <div class="proof"><b>59 tests</b><span>Verified safety and lifecycle behaviour.</span></div>
</div>
""", unsafe_allow_html=True)

overview, live_lab, case_file, track_record, readiness, security_tab, methodology = st.tabs([
    "Executive overview", "Run agent", "Decision case", "Track record", "Readiness", "Security", "Methodology"
])

with case_file:
    st.markdown('<p class="section-label">SIGNAL protocol · evidence to verdict</p>', unsafe_allow_html=True)
    st.header("One decision. Every claim inspectable.")
    contracts = dashboard.get('contracts', [])
    if not contracts:
        st.info("Run an agent cycle to create the first sealed Decision Contract.")
    else:
        contract_ids = [item['contract_id'] for item in contracts]
        labels = {item['contract_id']: f"{item['authorization']} · {item['contract_id']}"
                  for item in contracts}
        selected_id = st.selectbox("Replay decision", contract_ids,
                                   format_func=lambda value: labels[value],
                                   help="Reconstructs only evidence sealed at the original decision time.")
        row = next(item for item in contracts if item['contract_id'] == selected_id)
        contract = row['contract']
        trade = next((item for item in dashboard.get('trades', [])
                      if item.get('id') == row.get('trade_id')), None)
        recorded_portfolio = (trade or {}).get('portfolio', {})
        disagreement = contract['disagreement']
        stability = contract['stability']
        prediction = contract['prediction']
        a, b, c, d = st.columns(4)
        a.metric("Case", contract['contract_id'])
        b.metric("Disagreement", f"{disagreement['score']:.0f}/100")
        c.metric("Stability", f"{stability['score']:.0%}")
        d.metric("Verdict", contract['authorization'])

        scorecard = decision_scorecard(contract, row.get('evaluation'))
        st.subheader("Decision intelligence scorecard")
        score_cols = st.columns(4)
        score_cols[0].metric("Signal quality", f"{scorecard['signal_quality']}/100")
        score_cols[1].metric("Decision stability", f"{scorecard['decision_stability']}/100")
        score_cols[2].metric(
            "Execution quality", f"{scorecard['execution_quality']}/100",
            help=f"{scorecard['risk_checks_passed']} of {scorecard['risk_checks_total']} deterministic checks passed",
        )
        score_cols[3].metric(
            "Outcome evidence",
            "Pending" if scorecard['outcome_evidence'] is None else f"{scorecard['outcome_evidence']}/100",
            help="Revealed only after the sealed evaluation horizon.",
        )

        st.markdown(f'<div class="thesis"><span class="confidence">SEALED PREDICTION · {prediction["horizon_trading_days"]} TRADING DAYS</span><h2>{html.escape(str(prediction["market"]))} → {html.escape(str(prediction["direction"]))}</h2><p>{html.escape(str(contract["thesis"]))}</p></div>', unsafe_allow_html=True)
        render_protocol_journey(contract, row['execution_status'])
        render_disagreement_map(disagreement)

        st.subheader("Decision Replay courtroom")
        replay_steps = [
            ("Known", contract.get('market_timestamp') or contract.get('created_at'),
             "The market snapshot was frozen before broker access."),
            ("Allegation", disagreement['primary']['title'],
             f"Expected {prediction['market']} to move {prediction['direction']}."),
            ("Cross-examination", contract['falsification']['strongest_counterargument'],
             contract['falsification']['alternative_explanation']),
            ("Judgment", contract['authorization'],
             '; '.join(contract.get('authorization_reasons', [])) or 'All deterministic controls passed.'),
            ("Broker", row.get('execution_status', 'not_submitted'),
             "Order lifecycle is joined to the sealed contract, never rewritten into it."),
            ("Verdict", "Scored" if row.get('evaluation') else "Pending",
             "Outcome is revealed only after the predetermined horizon."),
        ]
        st.dataframe(pd.DataFrame(replay_steps, columns=['Stage', 'Evidence', 'Meaning']),
                     width='stretch', hide_index=True)
        if row.get('evaluation'):
            evaluation = row['evaluation']
            st.subheader("Predetermined verdict and counterfactuals")
            verdict_cols = st.columns(3)
            direction_correct = evaluation.get('direction_correct')
            verdict = "Unscoreable" if direction_correct is None else (
                "Yes" if direction_correct else "No"
            )
            verdict_cols[0].metric("Direction correct", verdict)
            verdict_cols[1].metric("Sealed baseline", fmt(evaluation.get('before')))
            verdict_cols[2].metric("Observed outcome", fmt(evaluation.get('after')))
            counterfactuals = evaluation.get('counterfactuals', {})
            st.dataframe(pd.DataFrame([
                {'Alternative': name.replace('_', ' ').title(), 'Normalized result': value}
                for name, value in counterfactuals.items()
            ]), width='stretch', hide_index=True)
        else:
            st.info("Verdict remains sealed until the configured horizon; no early outcome is revealed.")

        st.subheader("The proof chain")
        with st.expander("1 · Source integrity", expanded=True):
            quality = contract.get('data_quality', {})
            st.write("All required sources live" if quality.get('all_live') else "Fallback sources detected")
            source_rows = [{'source': name, **source} for name, source in quality.get('sources', {}).items()]
            if source_rows:
                st.dataframe(pd.DataFrame(source_rows), width='stretch', hide_index=True)
        with st.expander("2 · Quantified inconsistency", expanded=True):
            st.write(disagreement['primary']['explanation'])
            st.dataframe(pd.DataFrame([{
                'case': item['title'], 'score': item['score'],
                'repricing market': item['repricing_market'], 'direction': item['direction'],
            } for item in disagreement['candidates']]), width='stretch', hide_index=True)
        with st.expander("3 · Adversarial challenge", expanded=True):
            challenge = contract['falsification']
            st.error(challenge['strongest_counterargument'])
            st.write(f"**Alternative explanation:** {challenge['alternative_explanation']}")
            st.write(f"**Invalidation:** {challenge['invalidation_condition']}")
            st.write(f"**Confidence:** {contract['confidence_before_challenge']:.0%} → {contract['confidence_after_challenge']:.0%}")
        with st.expander("4 · Decision stability", expanded=True):
            st.write(f"The leading conclusion survived {stability['stable_cases']} of {stability['total_cases']} bounded perturbations.")
            st.dataframe(pd.DataFrame(stability['outcomes']), width='stretch', hide_index=True)
        with st.expander("5 · Sealed contract and execution", expanded=True):
            st.code(contract['decision_hash'], language=None)
            st.write(f"**Authorization:** {contract['authorization']}")
            st.write(f"**Execution lifecycle:** {row['execution_status']}")
            st.caption("The SHA-256 receipt was persisted before broker submission; changing any sealed claim produces a different hash.")

        stress = recorded_portfolio.get('portfolio_stress')
        with st.expander("6 · Greeks and scenario defense", expanded=True):
            if stress:
                greek_cols = st.columns(4)
                for col, name in zip(greek_cols, ('delta', 'gamma', 'theta', 'vega')):
                    col.metric(f"Net {name.title()}", fmt(stress.get('greeks', {}).get(name)))
                st.dataframe(pd.DataFrame(stress.get('scenarios', [])), width='stretch', hide_index=True)
                execution_risk = recorded_portfolio.get('execution_risk', {})
                if execution_risk.get('checks'):
                    risk_rows = [{**item, 'actual': json.dumps(item.get('actual'), default=str),
                                  'limit': json.dumps(item.get('limit'), default=str)}
                                 for item in execution_risk['checks']]
                    st.dataframe(pd.DataFrame(risk_rows), width='stretch', hide_index=True)
                st.caption(stress.get('note'))
            else:
                st.info("This historical contract predates Greek snapshot capture. The next cycle will preserve Alpaca Greeks at preflight.")

        with st.expander("7 · Execution recovery and catalyst context", expanded=True):
            recovery = recorded_portfolio.get('execution_recovery')
            catalyst = recorded_portfolio.get('catalyst_context')
            if recovery:
                st.write(f"**Recovery state:** {recovery['state']}")
                for action in recovery.get('actions', []):
                    st.write(f"• {action}")
                if recovery['state'] == 'RECOVERY_REQUIRED':
                    approve_recovery = st.checkbox(
                        "I approve canceling active orders in the Alpaca paper account",
                        key=f"recover-{contract['contract_id']}",
                        disabled=not broker_mutations_enabled,
                    )
                    if st.button("Execute paper recovery lock", disabled=not approve_recovery,
                                 key=f"recover-button-{contract['contract_id']}"):
                        from tools.alpaca_tools import AlpacaTools
                        broker = AlpacaTools(mutation_authorized=broker_mutations_enabled)
                        try:
                            executions = {
                                name: recorded_portfolio.get(name, {}).get('execution', {})
                                for name in ('primary_trade', 'secondary_trade', 'hedge')
                            }
                            recovery_result = PaperRecoveryExecutor().execute(
                                recovery, executions, broker, approved=True, paper_mode=True,
                            )
                            st.write(recovery_result)
                        finally:
                            broker.close()
            else:
                st.caption("Recovery state will be recorded on the next agent cycle.")
            if catalyst:
                st.write(f"**Catalyst classification:** {catalyst['classification']}")
                if catalyst.get('articles'):
                    st.dataframe(pd.DataFrame(catalyst['articles']), width='stretch', hide_index=True)

        receipt = EvidenceReceiptBuilder().dumps(
            contract, row.get('execution_status'), row.get('evaluation'), recorded_portfolio,
        )
        st.download_button("Download judge evidence receipt", receipt,
                           file_name=f"{contract['contract_id']}-receipt.json",
                           mime="application/json", width='stretch')
        uploaded_receipt = st.file_uploader("Verify an evidence receipt", type=['json'])
        if uploaded_receipt is not None:
            verification = EvidenceReceiptBuilder().verify(uploaded_receipt.getvalue().decode('utf-8'))
            (st.success if verification['valid'] else st.error)(verification['reason'])

        st.subheader("Prove the agent can refuse")
        weak_data = st.toggle("Simulate stale or fallback evidence", value=False)
        weak_signal = st.slider("Simulated disagreement strength", 0, 100,
                                int(disagreement['score']))
        simulated_reasons = []
        if weak_data:
            simulated_reasons.append("required market data is not fully live")
        if weak_signal < 55:
            simulated_reasons.append("disagreement score below 55")
        simulated_decision = "ABSTAIN" if simulated_reasons else "AUTHORIZED"
        (st.error if simulated_reasons else st.success)(
            f"{simulated_decision} — " + ('; '.join(simulated_reasons) if simulated_reasons else 'minimum evidence gates pass')
        )

with overview:
    st.markdown('<p class="section-label">The intelligence stack</p>', unsafe_allow_html=True)
    st.header("A complete decision, not another signal")
    st.markdown("""
    <div class="judge-route">
      <div class="route-step"><i>1</i><b>Run the replay</b><span>See six sources become one governed candidate.</span></div>
      <div class="route-step"><i>2</i><b>Inspect the refusal</b><span>Trace the exact gate that produced ABSTAIN.</span></div>
      <div class="route-step"><i>3</i><b>Verify the lifecycle</b><span>Follow a clearly labelled illustrative spread from entry policy to exit.</span></div>
    </div>
    """, unsafe_allow_html=True)
    cols = st.columns(3)
    items = [
        ("Observe", "Alpaca market data and public Treasury yields form a provenance-tagged cross-market snapshot."),
        ("Reason", "Claude identifies the mispricing, direction, confidence, and the clearest expression of the thesis."),
        ("Govern", "Risk checks and three-leg preflight complete before any paper order can be submitted."),
    ]
    for col, (title, copy) in zip(cols, items):
        col.markdown(f'<div class="card"><h3>{title}</h3><p>{copy}</p></div>', unsafe_allow_html=True)

    st.write("")
    st.markdown('<p class="section-label">Latest evidence</p>', unsafe_allow_html=True)
    a, b, c, d = st.columns(4)
    a.metric("Theses generated", len(dashboard['theses']))
    b.metric("Trade cycles", len(dashboard['trades']))
    b_statuses = [row['status'] for row in dashboard['trades']]
    c.metric("Submitted cycles", b_statuses.count('submitted'))
    hit = dashboard['track_record']['average_hit_rate']
    if dashboard.get('fixture'):
        d.metric("Evidence scope", "Illustrative replay", help="Not competition-account performance")
    else:
        d.metric("Forecast hit rate", f"{hit:.0%}" if hit is not None else "Pending")

with live_lab:
    st.markdown('<p class="section-label">Controlled paper environment</p>', unsafe_allow_html=True)
    st.header("Replay the agent" if PUBLIC_DEMO_MODE else "Run the agent")
    st.caption("This public replay makes the complete decision path available without credentials or broker access." if PUBLIC_DEMO_MODE else "Preview is the safe default. Paper execution remains disabled whenever a risk or live-data check fails.")
    execution_available = broker_mutations_enabled
    execute = st.toggle("Submit eligible paper orders", value=False, disabled=not execution_available,
                        help="Uses the connected Alpaca paper account only. Leave off for a full dry run.")
    if not execution_available:
        st.info("Broker mutations are disabled by deployment policy. Set ALLOW_PAPER_EXECUTION=true and PUBLIC_DEMO_MODE=false only on a controlled local machine.")
    if execute:
        confirmation = st.checkbox("I understand this submits orders to the Alpaca paper account")
    else:
        confirmation = False
    run_label = "Replay sanitized judge case" if PUBLIC_DEMO_MODE else "Run cross-market cycle"
    if st.button(run_label, width='stretch',
                 disabled=execute and not confirmation):
        if PUBLIC_DEMO_MODE:
            st.session_state['latest_cycle'] = dashboard['latest_cycle']
            st.success("Sanitized case replayed. No external service or broker account was contacted.")
        else:
            from live.cross_market_agent import CrossMarketAgent
            agent = None
            try:
                with st.status("Agent is reading the market…", expanded=True) as status:
                    agent = CrossMarketAgent()
                    result = agent.run(execute=execute)
                    status.update(label="Cycle complete", state="complete")
                st.session_state['latest_cycle'] = result
            except Exception as exc:
                st.error(f"Cycle failed safely: {exc}")
            finally:
                if agent:
                    agent.close()

    result = st.session_state.get('latest_cycle')
    if result:
        state = result.get('market_state') or {}
        quality = state.get('data_quality', {})
        st.subheader("Data provenance")
        cols = st.columns(3)
        for idx, (name, source) in enumerate(quality.get('sources', {}).items()):
            cols[idx % 3].markdown(
                f'<div class="card">{badge(source["status"])}<h3>{name.replace("_", " ").title()}</h3><p>{source["note"]}</p></div>',
                unsafe_allow_html=True,
            )
        thesis = result.get('thesis')
        if thesis:
            st.markdown(f'<div class="thesis"><span class="confidence">CONFIDENCE {thesis.get("confidence_overall", 0):.0%}</span><h2>{html.escape(str(thesis.get("thesis", "")))}</h2><p>{html.escape(str(thesis.get("rationale", "")))}</p></div>', unsafe_allow_html=True)
        portfolio = result.get('portfolio')
        if portfolio:
            st.subheader("Risk decision")
            checks = portfolio.get('risk_assessment', {}).get('checks', [])
            display_checks = [{**item,
                               'actual': json.dumps(item.get('actual'), default=str),
                               'limit': json.dumps(item.get('limit'), default=str)}
                              for item in checks]
            st.dataframe(pd.DataFrame(display_checks), width='stretch', hide_index=True)
            rows = []
            for name in ('primary_trade', 'secondary_trade', 'hedge'):
                leg = portfolio.get(name, {})
                execution = leg.get('execution', {})
                rows.append({'role': name.replace('_', ' ').title(), 'symbol': leg.get('symbol'),
                             'strategy': leg.get('strategy'), 'stance': leg.get('stance'),
                             'submitted': execution.get('submitted', False),
                             'status': execution.get('status') or execution.get('reason', 'not evaluated')})
            st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

with track_record:
    st.markdown('<p class="section-label">No cherry-picking</p>', unsafe_allow_html=True)
    st.header("Every thesis leaves a trail")
    track = dashboard['track_record']
    x, y, z = st.columns(3)
    x.metric("Scored theses", track['theses_scored'])
    y.metric("Pending evaluation", track['theses_pending'])
    if dashboard.get('fixture'):
        z.metric("Performance status", "Illustrative only", help="No competition-account P&L claim")
    else:
        z.metric("Average hit rate", f"{track['average_hit_rate']:.0%}" if track['average_hit_rate'] is not None else "—")
    thesis_rows = []
    for row in dashboard['theses']:
        thesis_rows.append({'time': row['timestamp'], 'thesis': row['thesis'],
                            'confidence': row['confidence'], 'evaluated': bool(row['evaluated']),
                            'hit_rate': row['hit_rate']})
    if thesis_rows:
        st.dataframe(pd.DataFrame(thesis_rows), width='stretch', hide_index=True)
    else:
        st.info("The first thesis will appear here after an agent cycle.")
    st.subheader("Execution ledger")
    if dashboard['trades']:
        st.dataframe(pd.DataFrame([{'time': row['timestamp'], 'strategy': row['strategy'],
                                   'status': row['status']} for row in dashboard['trades']]),
                     width='stretch', hide_index=True)

    st.subheader("Position lifecycle")
    st.caption(
        "Every submitted spread receives a persisted exit contract. The monitor values the whole spread, "
        "checks take-profit, stop-loss, holding-period and expiry rules, then closes both legs atomically."
        + (" This table is an illustrative policy demonstration, not broker fill evidence." if dashboard.get('fixture') else "")
    )
    lifecycle = dashboard.get('position_performance', {})
    life_a, life_b, life_c, life_d = st.columns(4)
    if dashboard.get('fixture'):
        life_a.metric("Evidence type", "Simulation")
        life_b.metric("Lifecycle cases", lifecycle.get('closed_positions', 0))
        life_c.metric("Triggered exit", "Take profit")
        life_d.metric("Sealed exit rules", "4")
    else:
        life_a.metric("Managed positions", sum(lifecycle.get('by_status', {}).values()))
        life_b.metric("Closed", lifecycle.get('closed_positions', 0))
        life_c.metric("Realized P&L", f"${lifecycle.get('realized_pnl', 0):,.2f}")
        win_rate = lifecycle.get('win_rate')
        life_d.metric("Lifecycle win rate", f"{win_rate:.0%}" if win_rate is not None else "Pending")
    if dashboard.get('fixture'):
        st.warning(
            "SIMULATED LIFECYCLE REPLAY — This demonstrates policy and state transitions. "
            "It is not broker P&L or competition-account performance."
        )
    position_rows = []
    for item in dashboard.get('positions', []):
        position_rows.append({
            'contract': item.get('contract_id'), 'role': item.get('role'),
            'underlying': item.get('underlying_symbol'), 'status': item.get('status'),
            'P&L': item.get('realized_pnl') if item.get('status') == 'CLOSED' else item.get('last_pnl'),
            'take profit': item.get('take_profit_target'),
            'stop loss': -float(item.get('stop_loss_limit') or 0),
            'max hold': f"{item.get('max_holding_days')} trading days",
            'exit before expiry': f"{item.get('exit_before_expiry_days')} days",
            'exit reason': item.get('exit_reason'),
        })
    if position_rows:
        st.dataframe(pd.DataFrame(position_rows), width='stretch', hide_index=True)
        event_rows = [{key: row.get(key) for key in
                       ('timestamp', 'position_id', 'event_type', 'state_before', 'state_after', 'reason')}
                      for row in dashboard.get('position_events', [])]
        with st.expander("Lifecycle event ledger"):
            st.dataframe(pd.DataFrame(event_rows), width='stretch', hide_index=True)
    else:
        st.info("No submitted spreads are currently registered for lifecycle management.")

with readiness:
    st.markdown('<p class="section-label">Submission assurance</p>', unsafe_allow_html=True)
    st.header("Hackathon readiness")
    requirements = [
        ('Autonomous AI trading workflow', 'Met', 'Observe, reason, construct, govern, preflight and audit'),
        ('Alpaca API / MCP integration', 'Met', 'Official Alpaca MCP server powers market data and paper orders'),
        ('Meaningful AI integration', 'Met', 'Claude generates structured macro theses and repricing signals'),
        ('Risk controls', 'Met', 'Defined loss, confidence, buying power, diversification, data integrity, and governed exits'),
        ('Position management', 'Met', 'Persisted take-profit, stop-loss, five-day holding and pre-expiry exits; atomic multi-leg paper closes'),
        ('Working browser prototype', 'Met', 'Judge-facing application with safe preview mode'),
        ('Public GitHub repository', 'Met', 'Published at github.com/omobolajiadeyan/alpaca-cross-market-agent'),
        ('Dedicated new Alpaca paper account', 'Met', 'PA3PDTUDIXDU, created 2026-09-01, $100,000 starting balance'),
        ('Filled trade on the dedicated account', 'Pending', 'Ten live cycles across 2026-09-01/02/03 correctly abstained (closest miss: 54% confidence vs a 55% floor, 5 of 6 gates passed); no fill yet -- required for P&L judging'),
        ('Forward-scored thesis evidence', 'Info', 'Earlier scored theses predate the dedicated account and are historical evidence only'),
        ('Hosted public application URL', 'Met', 'Public judge app is deployed at crosssignal-ai-agent.streamlit.app'),
        ('Scheduled cloud Evidence Watch', 'Ready', 'Read-only workflow is implemented; connected runs require encrypted repository secrets'),
        ('Pitch video', 'Met', 'Narrated screen-recorded walkthrough produced'),
        ('Slide deck', 'Met', 'Refreshed 2026-09-02 with the current test count and a real dedicated-account contract'),
        ('One-page write-up', 'Met', 'AI logic, risk gates and Alpaca infrastructure documented in submission/'),
        ('Hackathon cover image', 'Met', 'Final 16:9 cover is versioned in assets/'),
        ('Participant enrollment and team', 'Met', 'Authenticated event dashboard shows Omobolaji Adeyan and team CrossSignal'),
        ('lablab submission form', 'Submitted', 'User confirmed submission with the dedicated account ID'),
    ]
    readiness_df = pd.DataFrame(requirements, columns=['Requirement', 'Status', 'Evidence / next action'])
    st.dataframe(readiness_df, width='stretch', hide_index=True)
    completed = sum(status == 'Met' for _, status, _ in requirements)
    st.progress(completed / len(requirements), text=f'{completed} of {len(requirements)} requirements fully met')
    st.success('Submission completed. This page now serves as the public, read-only judge evidence experience.')

with security_tab:
    st.markdown('<p class="section-label">NIST-aligned risk management</p>', unsafe_allow_html=True)
    st.header("Every privilege has a reason and a boundary")
    posture = security_posture({
        'paper_endpoint': ALPACA_BASE_URL == 'https://paper-api.alpaca.markets',
        'public_execution': PUBLIC_DEMO_MODE and ALLOW_PAPER_EXECUTION,
        'require_live_data': REQUIRE_LIVE_DATA,
        'credentials_present': bool(ALPACA_API_KEY and ALPACA_SECRET_KEY),
    })
    st.dataframe(pd.DataFrame(posture['checks']), width='stretch', hide_index=True)
    st.caption(posture['residual_risk'])
    st.subheader("Why each route exists")
    st.dataframe(pd.DataFrame([
        {'Decision': 'Public UI is read-only', 'Threat': 'Unauthorized visitor submits an order',
         'Control': 'Deployment policy disables broker mutations', 'NIST route': 'AI RMF MANAGE 1; SP 800-53 AC'},
        {'Decision': 'LLM cannot call Alpaca', 'Threat': 'Prompt injection or hallucination reaches broker',
         'Control': 'Deterministic constructor and execution gate', 'NIST route': 'AI RMF MAP/MEASURE/MANAGE'},
        {'Decision': 'News is untrusted context', 'Threat': 'Instruction-like third-party content',
         'Control': 'Bound, sanitize and never authorize from headlines', 'NIST route': 'NIST AI 100-2e2025'},
        {'Decision': 'Contract sealed before execution', 'Threat': 'Post-outcome evidence rewriting',
         'Control': 'Canonical SHA-256 precommitment and verifier', 'NIST route': 'SP 800-53 AU/SI'},
        {'Decision': 'Fallback means abstain', 'Threat': 'Trade based on fabricated or stale evidence',
         'Control': 'Live-data integrity gate', 'NIST route': 'AI RMF MEASURE 1 / MANAGE 1'},
        {'Decision': 'Recovery requires approval', 'Threat': 'Automatic correction compounds exposure',
         'Control': 'Paper-only endpoint, explicit approval, logged actions', 'NIST route': 'SP 800-53 AC/AU/IR'},
        {'Decision': 'Exit automation is independently gated', 'Threat': 'Duplicate or unauthorized closing orders',
         'Control': f"Persisted lifecycle state, atomic close, Alpaca clock and separate switch ({ENABLE_AUTOMATED_PAPER_EXITS})", 'NIST route': 'SP 800-53 AC/AU/SI'},
        {'Decision': 'Secrets never enter receipts', 'Threat': 'Credential disclosure in logs or exports',
         'Control': 'Recursive redaction and Git exclusions', 'NIST route': 'SP 800-218 PW.4 / SP 800-53 IA'},
    ]), width='stretch', hide_index=True)
    st.warning("NIST guidance is voluntary and tailorable. CrossSignal is NIST-aligned, not NIST-certified or independently assessed.")

with methodology:
    st.markdown('<p class="section-label">Transparent by construction</p>', unsafe_allow_html=True)
    st.header("From disagreement to defined risk")
    st.markdown("""
1. **Read:** synchronize SPY volatility and positioning, Treasury yields, credit proxies, and realized volatility.
2. **Label:** expose whether each value is live, computed, proxied, or fallback.
3. **Synthesize:** ask Claude for a structured macro thesis and explicit repricing signals.
4. **Construct:** map the signals to SPY, HYG, and TLT defined-risk vertical spreads.
5. **Govern:** require portfolio structure, loss, confidence, buying power, diversification, and live-data checks.
6. **Preflight:** price every leg before allowing any paper order submission.
7. **Manage:** monitor the spread as a unit and enforce take-profit, stop-loss, holding-period and pre-expiry exits.
8. **Audit:** persist the thesis, market snapshot, risk decision, entry/exit lifecycle, and future forecast score.
    """)
    st.warning("Educational prototype. Paper trading only. This application does not provide investment advice.")

st.markdown(f'<div class="footer">CROSSSIGNAL · Omobolaji E Adeyan · Built for the Alpaca AI Trading Agents Hackathon · Data timestamp {datetime.now().strftime("%Y-%m-%d %H:%M %Z")} · Paper trading only</div>', unsafe_allow_html=True)
