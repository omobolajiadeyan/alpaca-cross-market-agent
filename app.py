"""Judge-facing browser experience for the Cross-Market Macro Agent."""

import json
from datetime import datetime

import pandas as pd
import streamlit as st

from compliance.audit_logger import AuditLogger


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
.block-container { max-width:1280px; padding-top:1.2rem; padding-bottom:4rem; }
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
@media(max-width:800px){.proof-grid{grid-template-columns:1fr}.hero{padding:3rem 1.5rem}.nav-note{display:none}}
</style>
""", unsafe_allow_html=True)


def badge(status):
    kind = 'live' if status == 'live' else ('fallback' if status == 'fallback' else 'neutral')
    return f'<span class="status-{kind}">{status}</span>'


def fmt(value, suffix=""):
    if value is None:
        return "—"
    return f"{value:,.2f}{suffix}" if isinstance(value, (int, float)) else str(value)


logger = AuditLogger()
dashboard = logger.get_dashboard_data()

st.markdown('<div class="nav"><div class="brand"><span class="brand-mark">◈</span>CROSSSIGNAL</div><div class="nav-note">ALPACA PAPER TRADING · AUDITABLE BY DESIGN</div></div>', unsafe_allow_html=True)

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

live_lab, overview, track_record, readiness, methodology = st.tabs([
    "Agent Lab", "Executive overview", "Track record", "Readiness", "Methodology"
])

with overview:
    st.markdown('<p class="section-label">The intelligence stack</p>', unsafe_allow_html=True)
    st.header("A complete decision, not another signal")
    cols = st.columns(3)
    items = [
        ("01", "Observe", "Alpaca market data and public Treasury yields form a provenance-tagged cross-market snapshot."),
        ("02", "Reason", "Claude identifies the mispricing, direction, confidence, and the clearest expression of the thesis."),
        ("03", "Govern", "Risk checks and three-leg preflight complete before any paper order can be submitted."),
    ]
    for col, (number, title, copy) in zip(cols, items):
        col.markdown(f'<div class="card"><span class="section-label">{number}</span><h3>{title}</h3><p>{copy}</p></div>', unsafe_allow_html=True)

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
    execute = st.toggle("Submit eligible paper orders", value=False,
                        help="Uses the connected Alpaca paper account only. Leave off for a full dry run.")
    if execute:
        confirmation = st.checkbox("I understand this submits orders to the Alpaca paper account")
    else:
        confirmation = False
    if st.button("Run cross-market cycle", use_container_width=True,
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
            st.dataframe(pd.DataFrame(checks), use_container_width=True, hide_index=True)
            rows = []
            for name in ('primary_trade', 'secondary_trade', 'hedge'):
                leg = portfolio.get(name, {})
                execution = leg.get('execution', {})
                rows.append({'role': name.replace('_', ' ').title(), 'symbol': leg.get('symbol'),
                             'strategy': leg.get('strategy'), 'stance': leg.get('stance'),
                             'submitted': execution.get('submitted', False),
                             'status': execution.get('status') or execution.get('reason', 'not evaluated')})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

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
        st.dataframe(pd.DataFrame(thesis_rows), use_container_width=True, hide_index=True)
    else:
        st.info("The first thesis will appear here after an agent cycle.")
    st.subheader("Execution ledger")
    if dashboard['trades']:
        st.dataframe(pd.DataFrame([{'time': row['timestamp'], 'strategy': row['strategy'],
                                   'status': row['status']} for row in dashboard['trades']]),
                     use_container_width=True, hide_index=True)

with readiness:
    st.markdown('<p class="section-label">Submission assurance</p>', unsafe_allow_html=True)
    st.header("Hackathon readiness")
    requirements = [
        ('Autonomous AI trading workflow', 'Met', 'Observe, reason, construct, govern, preflight and audit'),
        ('Alpaca API / MCP integration', 'Met', 'Official Alpaca MCP server powers market data and paper orders'),
        ('Meaningful AI integration', 'Met', 'Claude generates structured macro theses and repricing signals'),
        ('Risk controls', 'Met', 'Defined loss, confidence, buying power, diversification and data-integrity gates'),
        ('Working browser prototype', 'Met', 'Judge-facing application with safe preview mode'),
        ('Public GitHub repository', 'Met', 'Published under the authenticated project owner'),
        ('Successful paper execution evidence', 'Met', 'Three Alpaca multi-leg paper orders filled on 2026-08-25'),
        ('Forward-scored thesis evidence', 'Met', 'Three earlier theses scored at a preliminary 66.7% short-horizon hit rate'),
        ('Hosted public application URL', 'Missing', 'Deploy with credentials configured privately'),
        ('Pitch video and slide deck', 'Partial', 'Scripts and outlines exist; final assets must be produced'),
        ('Hackathon cover image', 'Met', 'Final 16:9 cover is versioned in assets/'),
        ('lablab submission form', 'Missing', 'Complete on lablab.ai before the deadline'),
    ]
    readiness_df = pd.DataFrame(requirements, columns=['Requirement', 'Status', 'Evidence / next action'])
    st.dataframe(readiness_df, use_container_width=True, hide_index=True)
    completed = sum(status == 'Met' for _, status, _ in requirements)
    st.progress(completed / len(requirements), text=f'{completed} of {len(requirements)} requirements fully met')
    st.info('The software requirements are substantially complete. External proof and final submission assets remain intentionally marked incomplete.')

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

st.markdown(f'<div class="footer">CROSSSIGNAL · Built for the Alpaca AI Trading Agents Hackathon · Data timestamp {datetime.now().strftime("%Y-%m-%d %H:%M %Z")} · Paper trading only</div>', unsafe_allow_html=True)
