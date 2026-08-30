"""Judge-facing browser experience for the Cross-Market Macro Agent."""

import json
from datetime import datetime

import pandas as pd
import streamlit as st

from compliance.audit_logger import AuditLogger
from agent.evidence_protocol import EvidenceReceiptBuilder, PaperRecoveryExecutor
from config import (ALLOW_PAPER_EXECUTION, PUBLIC_DEMO_MODE, REQUIRE_LIVE_DATA,
                    ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL)
from security.controls import security_posture


st.set_page_config(
    page_title="CrossSignal — AI Macro Trading Agent",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');
:root { --ink:#071d49; --muted:#53657d; --canvas:#fff; --ice:#f2f7fb; --cyan:#19b5d8; --blue:#003b70; --navy:#071d49; --line:#d5e0e9; }
.stApp { background:var(--canvas); color:var(--ink); font-family:'DM Sans',sans-serif; }
[data-testid="stHeader"] { background:transparent; }
.block-container { max-width:1280px; padding-top:1.2rem; padding-bottom:4rem; overflow-x:hidden; }
h1,h2,h3 { font-family:'Manrope',sans-serif !important; letter-spacing:-.04em !important; }
.nav { display:flex; justify-content:space-between; align-items:center; padding:.75rem 0 1.2rem; border-bottom:1px solid var(--line); }
.brand { font:800 1.1rem Manrope; letter-spacing:-.04em; }.brand-mark { color:var(--cyan); margin-right:.45rem; }
.nav-note { color:var(--muted); font-size:.82rem; }
.hero { margin:1.5rem 0 0; padding:4.5rem 4rem; background:var(--navy); color:#fff; position:relative; overflow:hidden; }
.hero:after { content:''; position:absolute; width:380px; height:380px; border:70px solid var(--cyan); border-radius:50%; right:-180px; top:-155px; opacity:.9; }
.eyebrow { display:inline-block; border-left:3px solid var(--cyan); padding:.1rem 0 .1rem .75rem; font-size:.72rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:#b9dced; }
.hero h1 { font-size:clamp(3rem,6vw,6rem); line-height:.95; max-width:900px; margin:1.4rem 0 1.5rem; position:relative; z-index:1; }
.hero h1 em { color:#72d4e8; font-style:normal; }
.hero-copy { max-width:680px; color:#d7e7f0; font-size:1.12rem; line-height:1.65; position:relative; z-index:1; }
.proof-grid { display:grid; grid-template-columns:repeat(3,1fr); background:var(--ice); border-bottom:1px solid var(--line); margin:0 0 3.5rem; }
.proof { padding:1.65rem 2rem; border-right:1px solid var(--line); }.proof:last-child{border-right:0}.proof b { display:block; font:700 1.2rem Manrope; margin-bottom:.35rem; }.proof span { color:var(--muted); font-size:.88rem; }
.section-label { color:#007fa8; font-size:.72rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; }
.card { background:#fff; border:1px solid var(--line); border-radius:2px; padding:1.4rem; height:100%; box-shadow:0 6px 18px rgba(7,29,73,.04); }
.status-live,.status-fallback,.status-neutral { display:inline-block; padding:.27rem .55rem; border-radius:99px; font-size:.68rem; font-weight:700; text-transform:uppercase; }
.status-live { background:#dff8e8;color:#17653b }.status-fallback {background:#fff0cc;color:#8a5600}.status-neutral{background:#e8f2f8;color:#315b75}
.thesis { background:var(--blue); color:#fff; padding:2rem; border-left:5px solid var(--cyan); margin:1rem 0; }
.thesis p { color:#d7e7f0; line-height:1.65; }.thesis .confidence { color:#72d4e8; font:700 .8rem Manrope; }
div.stButton > button { border-radius:2px; border:0; background:var(--blue); color:white; font-weight:700; min-height:3rem; }
div.stButton > button:hover { background:var(--navy); color:#fff; }
[data-testid="stMetric"] { background:#fff; border:1px solid var(--line); border-top:3px solid var(--cyan); border-radius:2px; padding:1rem; }
.footer { border-top:1px solid var(--line); margin-top:4rem; padding-top:1.5rem; color:var(--muted); font-size:.78rem; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap:.25rem; overflow-x:auto; scrollbar-width:none; }
[data-testid="stTabs"] [data-baseweb="tab"] { white-space:nowrap; min-width:max-content; }
[data-testid="stDataFrame"] { border:1px solid var(--line); }
button:focus-visible,[role="tab"]:focus-visible { outline:3px solid rgba(25,181,216,.45)!important; outline-offset:2px; }
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important;animation:none!important}}
@media(max-width:900px){
  .block-container{padding:1rem 1.25rem 3rem}.proof-grid{grid-template-columns:1fr}.proof{border-right:0;border-bottom:1px solid var(--line)}
  .hero{padding:3.25rem 2rem}.hero:after{width:250px;height:250px;right:-160px;top:-120px}.hero h1{font-size:clamp(2.6rem,11vw,4.4rem)}
  .nav-note{display:none}.card{margin-bottom:.5rem}
}
@media(max-width:520px){
  .block-container{padding:.7rem .85rem 2rem}.hero{margin-top:1rem;padding:2.5rem 1.25rem}.hero-copy{font-size:1rem}
  .proof{padding:1.25rem}.nav{padding:.5rem 0 1rem}[data-testid="stMetric"]{padding:.75rem}
  h1{font-size:2.25rem!important}h2{font-size:1.65rem!important}.footer{line-height:1.6}
}
</style>
""", unsafe_allow_html=True)


def badge(status):
    kind = 'live' if status == 'live' else ('fallback' if status == 'fallback' else 'neutral')
    return f'<span class="status-{kind}">{status}</span>'


def fmt(value, suffix=""):
    if value is None:
        return "—"
    return f"{value:,.2f}{suffix}" if isinstance(value, (int, float)) else str(value)


def render_disagreement_map(disagreement):
    """Responsive, dependency-free JavaScript evidence explorer."""
    payload = json.dumps(disagreement['candidates']).replace('</', '<\\/')
    st.html(f"""
    <div id="signal-map">
      <div class="map-title">SELECT A MARKET DISAGREEMENT</div>
      <div id="nodes"></div>
      <div id="detail" aria-live="polite"></div>
    </div>
    <style>
      #signal-map,#signal-map *{{box-sizing:border-box}} #signal-map{{font-family:Arial,sans-serif;color:#071d49}}
      #signal-map{{border:1px solid #d5e0e9;background:#f2f7fb;padding:20px;min-height:245px}}
      .map-title{{font-size:11px;font-weight:700;letter-spacing:.12em;color:#007fa8;margin-bottom:14px}}
      #nodes{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}}
      #signal-map button{{width:100%;text-align:left;border:1px solid #bfd0dd;background:#fff;color:#071d49;padding:14px;cursor:pointer;transition:.18s ease;min-height:78px}}
      #signal-map button:hover,#signal-map button.active{{background:#003b70;color:#fff;border-color:#003b70;transform:translateY(-2px)}}
      #signal-map button strong{{display:block;font-size:15px;margin-bottom:8px}}#signal-map button span{{font-size:12px;opacity:.8}}
      #detail{{margin-top:12px;background:#071d49;color:#fff;padding:16px;border-left:5px solid #19b5d8;min-height:90px}}
      .detail-grid{{display:grid;grid-template-columns:100px 1fr 1fr;gap:14px;align-items:start}}
      .score{{font-size:30px;font-weight:800;color:#72d4e8}}.label{{font-size:10px;letter-spacing:.1em;color:#b9dced}}
      #signal-map p{{font-size:13px;line-height:1.5;margin:4px 0 0}}
      @media(max-width:650px){{#signal-map{{padding:12px}}#nodes{{grid-template-columns:1fr}}button{{min-height:auto}}.detail-grid{{grid-template-columns:1fr}}}}
    </style>
    <script>
      const cases={payload};
      const nodes=document.getElementById('nodes');
      const detail=document.getElementById('detail');
      function selectCase(item,index){{
        document.querySelectorAll('#nodes button').forEach((b,i)=>b.classList.toggle('active',i===index));
        detail.innerHTML=`<div class="detail-grid"><div><div class="label">SCORE</div><div class="score">${{Math.round(item.score)}}</div></div><div><div class="label">EXPECTED REPRICING</div><p><strong>${{item.repricing_market}}</strong><br>${{item.direction}}</p></div><div><div class="label">WHY IT MATTERS</div><p>${{item.explanation}}</p></div></div>`;
      }}
      cases.forEach((item,index)=>{{
        const button=document.createElement('button');
        button.innerHTML=`<strong>${{item.title}}</strong><span>${{item.repricing_market}} · score ${{Math.round(item.score)}}</span>`;
        button.setAttribute('aria-label',`Inspect ${{item.title}}`);
        button.onclick=()=>selectCase(item,index);
        button.onkeydown=(event)=>{{if(event.key==='Enter'||event.key===' '){{event.preventDefault();selectCase(item,index)}}}};
        nodes.appendChild(button);
      }});
      if(cases.length) selectCase(cases[0],0);
    </script>
    """, unsafe_allow_javascript=True)


def render_protocol_journey(contract, execution_status):
    """Interactive JavaScript walkthrough of the sealed decision lifecycle."""
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
    payload = json.dumps(stages).replace('</', '<\\/')
    decision_hash = contract['decision_hash']
    st.html(f"""
    <section id="journey" aria-label="SIGNAL protocol journey">
      <div class="journey-head"><div><span>SIGNAL PROTOCOL</span><h3>Follow the decision from evidence to execution</h3></div><div class="progress-label" id="progress-label"></div></div>
      <div class="progress-track"><div id="progress-fill"></div></div>
      <div id="stage-list" role="tablist"></div>
      <div id="stage-detail" role="tabpanel" aria-live="polite"></div>
      <div class="receipt"><div><span>SEALED PROOF</span><code>{decision_hash[:16]}…</code></div><button id="copy-proof" type="button">Copy full SHA-256</button></div>
    </section>
    <style>
      #journey,#journey *{{box-sizing:border-box}}#journey{{font-family:Arial,sans-serif;border:1px solid #d5e0e9;background:#fff;padding:22px;margin:18px 0;color:#071d49}}
      .journey-head{{display:flex;justify-content:space-between;gap:20px;align-items:flex-end}}.journey-head span,.receipt span{{font-size:10px;font-weight:700;letter-spacing:.12em;color:#007fa8}}
      .journey-head h3{{font-size:20px;margin:5px 0 0}}.progress-label{{font-size:12px;font-weight:700;color:#53657d}}
      .progress-track{{height:5px;background:#e5eef4;margin:18px 0}}#progress-fill{{height:100%;background:#19b5d8;width:0;transition:width .5s ease}}
      #stage-list{{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:7px}}
      #stage-list button{{position:relative;border:1px solid #c8d7e2;background:#f7fafc;color:#071d49;padding:12px 8px;cursor:pointer;font-weight:700;min-height:52px}}
      #stage-list button:before{{content:'';display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px;background:#a9b7c2}}
      #stage-list button.pass:before{{background:#19b5d8}}#stage-list button.active{{background:#071d49;color:#fff;border-color:#071d49;transform:translateY(-2px)}}
      #stage-detail{{background:#f2f7fb;border-left:4px solid #19b5d8;padding:14px 16px;margin-top:10px;font-size:14px;line-height:1.5;min-height:50px}}
      .receipt{{display:flex;justify-content:space-between;align-items:center;gap:16px;border-top:1px solid #d5e0e9;margin-top:16px;padding-top:14px}}.receipt code{{display:block;margin-top:5px;color:#003b70}}
      .receipt button{{border:1px solid #003b70;background:#fff;color:#003b70;padding:10px 13px;cursor:pointer;font-weight:700}}.receipt button:hover{{background:#003b70;color:#fff}}
      @media(max-width:760px){{#journey{{padding:15px}}.journey-head{{display:block}}.progress-label{{margin-top:8px}}#stage-list{{grid-template-columns:repeat(2,1fr)}}.receipt{{align-items:flex-start;flex-direction:column}}.receipt button{{width:100%}}}}
    </style>
    <script>
      const stages={payload}; const list=document.getElementById('stage-list'); const detail=document.getElementById('stage-detail');
      const passed=stages.filter(stage=>stage.ok).length; document.getElementById('progress-fill').style.width=`${{passed/stages.length*100}}%`;
      document.getElementById('progress-label').textContent=`${{passed}} of ${{stages.length}} controls complete`;
      function activate(index){{document.querySelectorAll('#stage-list button').forEach((button,i)=>{{button.classList.toggle('active',i===index);button.setAttribute('aria-selected',i===index)}});detail.innerHTML=`<strong>${{stages[index].name}}</strong><br>${{stages[index].copy}}`;}}
      stages.forEach((stage,index)=>{{const button=document.createElement('button');button.type='button';button.role='tab';button.textContent=stage.name;button.classList.toggle('pass',stage.ok);button.onclick=()=>activate(index);button.onkeydown=event=>{{if(event.key==='ArrowRight'){{activate((index+1)%stages.length);list.children[(index+1)%stages.length].focus()}}if(event.key==='ArrowLeft'){{activate((index-1+stages.length)%stages.length);list.children[(index-1+stages.length)%stages.length].focus()}}}};list.appendChild(button)}});activate(0);
      const copyButton=document.getElementById('copy-proof');copyButton.onclick=async()=>{{try{{await navigator.clipboard.writeText('{decision_hash}');copyButton.textContent='Copied'}}catch(error){{copyButton.textContent='Copy unavailable'}}setTimeout(()=>copyButton.textContent='Copy full SHA-256',1600)}};
    </script>
    """, unsafe_allow_javascript=True)


logger = AuditLogger()
dashboard = logger.get_dashboard_data()
broker_mutations_enabled = ALLOW_PAPER_EXECUTION and not PUBLIC_DEMO_MODE

st.markdown('<div class="nav"><div class="brand"><span class="brand-mark">◈</span>CROSSSIGNAL</div><div class="nav-note">BUILT BY OMOBOLAJI E ADEYAN · ALPACA PAPER TRADING</div></div>', unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <span class="eyebrow">Decision intelligence for cross-market trading</span>
  <h1>See the repricing.<br><em>Act with precision.</em></h1>
  <p class="hero-copy">CrossSignal turns fragmented market information into an evidence-backed macro decision—with transparent sources, governed risk and an auditable Alpaca paper-trading workflow.</p>
</div>
<div class="proof-grid">
  <div class="proof"><b>6 live lenses</b><span>One synchronized macro state instead of a single-market signal.</span></div>
  <div class="proof"><b>Defined risk</b><span>Every options structure is capped and preflighted before submission.</span></div>
  <div class="proof"><b>Self-scoring</b><span>Past forecasts are checked against subsequent market outcomes.</span></div>
</div>
""", unsafe_allow_html=True)

case_file, live_lab, overview, track_record, readiness, security_tab, methodology = st.tabs([
    "Decision case", "Run agent", "Executive overview", "Track record", "Readiness", "Security", "Methodology"
])

with case_file:
    st.markdown('<p class="section-label">SIGNAL protocol · evidence to verdict</p>', unsafe_allow_html=True)
    st.header("One decision. Every claim inspectable.")
    contracts = dashboard.get('contracts', [])
    if not contracts:
        st.info("Run an agent cycle to create the first sealed Decision Contract.")
    else:
        contract_ids = [item['contract_id'] for item in contracts]
        selected_id = st.selectbox("Replay decision", contract_ids,
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

        st.markdown(f'<div class="thesis"><span class="confidence">SEALED PREDICTION · {prediction["horizon_trading_days"]} TRADING DAYS</span><h2>{prediction["market"]} → {prediction["direction"]}</h2><p>{contract["thesis"]}</p></div>', unsafe_allow_html=True)
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
            verdict_cols[0].metric("Direction correct",
                                   "Yes" if evaluation.get('direction_correct') else "No")
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
    d.metric("Forecast hit rate", f"{hit:.0%}" if hit is not None else "Pending")

with live_lab:
    st.markdown('<p class="section-label">Controlled paper environment</p>', unsafe_allow_html=True)
    st.header("Run the agent")
    st.caption("Preview is the safe default. Paper execution remains disabled whenever a risk or live-data check fails.")
    execution_available = broker_mutations_enabled
    execute = st.toggle("Submit eligible paper orders", value=False, disabled=not execution_available,
                        help="Uses the connected Alpaca paper account only. Leave off for a full dry run.")
    if not execution_available:
        st.info("Broker mutations are disabled by deployment policy. Set ALLOW_PAPER_EXECUTION=true and PUBLIC_DEMO_MODE=false only on a controlled local machine.")
    if execute:
        confirmation = st.checkbox("I understand this submits orders to the Alpaca paper account")
    else:
        confirmation = False
    if st.button("Run cross-market cycle", width='stretch',
                 disabled=execute and not confirmation):
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
            st.markdown(f'<div class="thesis"><span class="confidence">CONFIDENCE {thesis.get("confidence_overall", 0):.0%}</span><h2>{thesis.get("thesis", "")}</h2><p>{thesis.get("rationale", "")}</p></div>', unsafe_allow_html=True)
        portfolio = result.get('portfolio')
        if portfolio:
            st.subheader("Risk decision")
            checks = portfolio.get('risk_assessment', {}).get('checks', [])
            st.dataframe(pd.DataFrame(checks), width='stretch', hide_index=True)
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

with readiness:
    st.markdown('<p class="section-label">Submission assurance</p>', unsafe_allow_html=True)
    st.header("Hackathon readiness")
    requirements = [
        ('Autonomous AI trading workflow', 'Met', 'Observe, reason, construct, govern, preflight and audit'),
        ('Alpaca API / MCP integration', 'Met', 'Official Alpaca MCP server powers market data and paper orders'),
        ('Meaningful AI integration', 'Met', 'Claude generates structured macro theses and repricing signals'),
        ('Risk controls', 'Met', 'Defined loss, confidence, buying power, diversification and data-integrity gates'),
        ('Working browser prototype', 'Met', 'Judge-facing application with safe preview mode'),
        ('Public GitHub repository', 'Deferred', 'Intentionally local until the eligible event window'),
        ('Successful paper execution evidence', 'Met', 'Three Alpaca multi-leg paper orders filled on 2026-08-25'),
        ('Forward-scored thesis evidence', 'Met', 'Three earlier theses scored at a preliminary 66.7% short-horizon hit rate'),
        ('Hosted public application URL', 'Missing', 'Deploy with credentials configured privately'),
        ('Pitch video and slide deck', 'Partial', 'Scripts and outlines exist; final assets must be produced'),
        ('Hackathon cover image', 'Met', 'Final 16:9 cover is versioned in assets/'),
        ('Participant enrollment and team', 'Unverified', 'Omobolaji E Adeyan must enroll and join/create a team on lablab.ai'),
        ('lablab submission form', 'Missing', 'Complete on lablab.ai before the deadline'),
    ]
    readiness_df = pd.DataFrame(requirements, columns=['Requirement', 'Status', 'Evidence / next action'])
    st.dataframe(readiness_df, width='stretch', hide_index=True)
    completed = sum(status == 'Met' for _, status, _ in requirements)
    st.progress(completed / len(requirements), text=f'{completed} of {len(requirements)} requirements fully met')
    st.info('The software requirements are substantially complete. External proof and final submission assets remain intentionally marked incomplete.')

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
7. **Audit:** persist the thesis, market snapshot, risk decision, order response, and future forecast score.
    """)
    st.warning("Educational prototype. Paper trading only. This application does not provide investment advice.")

st.markdown(f'<div class="footer">CROSSSIGNAL · Omobolaji E Adeyan · Built for the Alpaca AI Trading Agents Hackathon · Data timestamp {datetime.now().strftime("%Y-%m-%d %H:%M %Z")} · Paper trading only</div>', unsafe_allow_html=True)
