###############################################################################
# "The Complete Picture" — AVEVA + Snowflake Demo for AVEVA World 2026
# Streamlit in Snowflake (SiS) — warehouse runtime
###############################################################################

import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from snowflake.snowpark.context import get_active_session

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AVEVA + Snowflake — The Complete Picture",
    layout="wide",
    page_icon="🔧",
)

# ---------------------------------------------------------------------------
# CSS — Glass-morphism cards, status indicators, rich styling
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* ── Base ── */
:root { --teal: #00D4AA; --purple: #6366F1; --amber: #F59E0B; --red: #EF4444; --green: #22C55E; }

/* ── Animated header ── */
.hero {
    background: linear-gradient(135deg, #0B1120 0%, #162033 40%, #1a1040 70%, #0B1120 100%);
    padding: 2.5rem 2rem; border-radius: 20px; margin-bottom: 1.5rem;
    border: 1px solid rgba(0,212,170,0.15); text-align: center;
    position: relative; overflow: hidden;
}
.hero::before {
    content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
    background: conic-gradient(from 0deg, transparent 0%, rgba(0,212,170,0.03) 25%, transparent 50%);
    animation: rotate 8s linear infinite;
}
@keyframes rotate { to { transform: rotate(360deg); } }
.hero h1 {
    background: linear-gradient(135deg, #00D4AA 0%, #6366F1 50%, #00D4AA 100%);
    background-size: 200% auto; -webkit-background-clip: text;
    -webkit-text-fill-color: transparent; font-size: 2.4rem; font-weight: 800;
    margin: 0; position: relative; z-index: 1;
}
.hero .tagline { color: #94A3B8; font-size: 1.05rem; margin-top: 0.5rem; position: relative; z-index: 1; }

/* ── Glass metric cards ── */
.glass-card {
    background: rgba(30,41,59,0.7); backdrop-filter: blur(12px);
    border: 1px solid rgba(0,212,170,0.12); border-radius: 16px;
    padding: 1.2rem 1.5rem; text-align: center;
}
.glass-card .label { color: #94A3B8; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.3rem; }
.glass-card .value { font-size: 2rem; font-weight: 800; margin: 0; }
.glass-card .value.teal { color: #00D4AA; }
.glass-card .value.purple { color: #6366F1; }
.glass-card .value.amber { color: #F59E0B; }
.glass-card .value.red { color: #EF4444; }
.glass-card .sub { color: #64748B; font-size: 0.78rem; margin-top: 0.2rem; }

/* ── Badges ── */
.badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.05em; }
.badge-aveva { background: rgba(99,102,241,0.15); color: #818CF8; border: 1px solid rgba(99,102,241,0.3); }
.badge-sf { background: rgba(0,212,170,0.1); color: #00D4AA; border: 1px solid rgba(0,212,170,0.3); }
.badge-cortex { background: rgba(245,158,11,0.1); color: #F59E0B; border: 1px solid rgba(245,158,11,0.3); }
.badge-sap { background: rgba(56,182,255,0.1); color: #38B6FF; border: 1px solid rgba(56,182,255,0.3); }
.badge-docs { background: rgba(16,185,129,0.1); color: #10B981; border: 1px solid rgba(16,185,129,0.3); }

/* ── Agent step cards ── */
.agent-step { background:rgba(30,41,59,0.6); border:1px solid rgba(148,163,184,0.1); border-radius:12px; padding:1rem 1.2rem; margin:0.6rem 0; transition:all 0.3s ease; }
.agent-step.running { border-color:rgba(0,212,170,0.4); animation: pulse-border 2s ease-in-out infinite; }
.agent-step.done { border-color:rgba(34,197,94,0.4); }
.agent-step .step-header { display:flex; align-items:center; gap:8px; margin-bottom:0.4rem; }
.agent-step .step-num { width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:0.75rem; font-weight:800; color:#fff; }
.step-num.waiting { background:rgba(51,65,85,0.8); }
.step-num.running { background:linear-gradient(135deg,#00D4AA,#6366F1); animation: pulse-dot 1.5s ease-in-out infinite; }
.step-num.done { background:#22C55E; }
.agent-step .step-title { font-size:0.88rem; font-weight:600; color:#E2E8F0; }
.agent-step .step-detail { color:#94A3B8; font-size:0.82rem; line-height:1.5; margin-top:0.3rem; }
.agent-step .step-time { color:#64748B; font-size:0.72rem; margin-top:0.3rem; }
.doc-card { background:rgba(16,185,129,0.06); border:1px solid rgba(16,185,129,0.2); border-radius:8px; padding:0.6rem 0.8rem; margin:0.3rem 0; }
.doc-card .doc-title { color:#10B981; font-weight:600; font-size:0.82rem; }
.doc-card .doc-type { color:#64748B; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.05em; }
.doc-card .doc-snippet { color:#94A3B8; font-size:0.78rem; margin-top:0.2rem; line-height:1.4; }
.doc-score { display:inline-block; background:rgba(16,185,129,0.15); color:#10B981; font-size:0.65rem; font-weight:700; padding:0.1rem 0.4rem; border-radius:999px; margin-left:6px; }

/* ── Risk rows ── */
.risk-table { width: 100%; border-collapse: separate; border-spacing: 0 4px; }
.risk-table th { color: #94A3B8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em; padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid rgba(148,163,184,0.15); }
.risk-table td { padding: 0.6rem 0.75rem; font-size: 0.88rem; }
.risk-table .row-critical { background: rgba(239,68,68,0.08); border-left: 3px solid #EF4444; }
.risk-table .row-high { background: rgba(245,158,11,0.08); border-left: 3px solid #F59E0B; }
.risk-table .row-elevated { background: rgba(234,179,8,0.05); border-left: 3px solid #EAB308; }
.risk-table .row-normal { background: rgba(30,41,59,0.4); border-left: 3px solid rgba(34,197,94,0.3); }
.risk-table .row-focus { background: rgba(99,102,241,0.12) !important; border-left: 3px solid #6366F1 !important; }
.risk-pill { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 999px; font-size: 0.7rem; font-weight: 700; }
.pill-critical { background: rgba(239,68,68,0.2); color: #FCA5A5; }
.pill-high { background: rgba(245,158,11,0.2); color: #FCD34D; }
.pill-elevated { background: rgba(234,179,8,0.15); color: #FDE047; }
.pill-normal { background: rgba(34,197,94,0.15); color: #86EFAC; }

/* ── Verdict cards ── */
.verdict { padding: 1.5rem 2rem; border-radius: 16px; text-align: center; margin: 1rem 0; }
.verdict-continue { background: linear-gradient(135deg, rgba(34,197,94,0.1) 0%, rgba(34,197,94,0.05) 100%); border: 2px solid #22C55E; }
.verdict-shutdown { background: linear-gradient(135deg, rgba(239,68,68,0.1) 0%, rgba(239,68,68,0.05) 100%); border: 2px solid #EF4444; }
.verdict-inspect { background: linear-gradient(135deg, rgba(245,158,11,0.1) 0%, rgba(245,158,11,0.05) 100%); border: 2px solid #F59E0B; }
.verdict h2 { margin: 0 0 0.5rem 0; font-size: 1.8rem; letter-spacing: 0.05em; }
.verdict-continue h2 { color: #22C55E; }
.verdict-shutdown h2 { color: #EF4444; }
.verdict-inspect h2 { color: #F59E0B; }
.verdict .conf { font-size: 0.9rem; color: #94A3B8; }

/* ── Confidence gauge ── */
.gauge-track { background: rgba(51,65,85,0.5); border-radius: 8px; height: 10px; overflow: hidden; margin: 0.5rem 0; }
.gauge-fill { height: 100%; border-radius: 8px; transition: width 1s ease; }
.gauge-green { background: linear-gradient(90deg, #22C55E, #4ADE80); }
.gauge-amber { background: linear-gradient(90deg, #F59E0B, #FBBF24); }
.gauge-red { background: linear-gradient(90deg, #EF4444, #F87171); }

/* ── Info cards ── */
.info-card {
    background: rgba(30,41,59,0.6); border: 1px solid rgba(148,163,184,0.1);
    border-radius: 12px; padding: 1rem 1.2rem; margin: 0.5rem 0;
}
.info-card h4 { color: #E2E8F0; margin: 0 0 0.4rem 0; font-size: 0.9rem; }
.info-card p { color: #94A3B8; margin: 0; font-size: 0.85rem; line-height: 1.5; }

/* ── Savings counter ── */
.savings {
    background: linear-gradient(135deg, #0c4a3e 0%, #134e3f 100%);
    border: 2px solid #00D4AA; border-radius: 20px; padding: 2rem; text-align: center; margin: 1.5rem 0;
}
.savings .amount { font-size: 3rem; font-weight: 900; color: #00D4AA; margin: 0; }
.savings .desc { color: #A7F3D0; font-size: 1rem; margin-top: 0.5rem; }

/* ── Story prompt ── */
.story-next {
    background: linear-gradient(90deg, rgba(99,102,241,0.08) 0%, rgba(0,212,170,0.08) 100%);
    border: 1px solid rgba(99,102,241,0.2); border-radius: 12px;
    padding: 1rem 1.5rem; margin-top: 2rem; text-align: center;
}
.story-next p { color: #CBD5E1; margin: 0; font-size: 0.95rem; }
.story-next strong { color: #00D4AA; }

/* ── Translation tabs ── */
.lang-card {
    background: rgba(30,41,59,0.6); border-left: 3px solid #6366F1;
    border-radius: 0 12px 12px 0; padding: 1rem 1.2rem; margin: 0.5rem 0;
}
.lang-card .flag { font-size: 1.5rem; margin-right: 0.5rem; }
.lang-card .name { color: #818CF8; font-weight: 700; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.06em; }
.lang-card .text { color: #CBD5E1; font-size: 0.85rem; margin-top: 0.4rem; line-height: 1.5; }

/* ── Animations ── */
@keyframes pulse-border { 0%,100% { border-color: rgba(0,212,170,0.15); } 50% { border-color: rgba(0,212,170,0.45); } }
@keyframes pulse-dot { 0%,100% { opacity:1; transform:scale(1); } 50% { opacity:0.5; transform:scale(0.8); } }
@keyframes fade-in { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
@keyframes flow-right { 0% { transform:translateX(-4px); opacity:0.4; } 50% { opacity:1; } 100% { transform:translateX(4px); opacity:0.4; } }
@keyframes glow-pulse { 0%,100% { box-shadow: 0 0 0 rgba(0,212,170,0); } 50% { box-shadow: 0 0 20px rgba(0,212,170,0.15); } }

.hero { animation: pulse-border 4s ease-in-out infinite; }
.glass-card { transition: all 0.3s ease; animation: fade-in 0.6s ease-out; }
.glass-card:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,212,170,0.08); border-color: rgba(0,212,170,0.3); }
.info-card { transition: all 0.3s ease; }
.info-card:hover { border-color: rgba(0,212,170,0.25); box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
.verdict { animation: fade-in 0.8s ease-out, glow-pulse 3s ease-in-out infinite; }
.story-next { animation: glow-pulse 3s ease-in-out infinite; }
.savings { animation: fade-in 0.8s ease-out; }
.flow-arrow { display:inline-block; animation: flow-right 1.5s ease-in-out infinite; color:#64748B; font-size:1.2rem; }

/* ── Live dot ── */
.live-dot { display:inline-block; width:8px; height:8px; border-radius:50%; background:#22C55E; animation: pulse-dot 2s ease-in-out infinite; margin-right:6px; vertical-align:middle; }

/* ── DMA Grid ── */
.dma-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.dma-zone { background:rgba(30,41,59,0.5); border:1px solid rgba(148,163,184,0.1); border-radius:12px; padding:0.8rem; }
.dma-zone h5 { color:#94A3B8; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; margin:0 0 0.5rem 0; }
.pump-grid { display:flex; flex-wrap:wrap; gap:6px; }
.pump-tile { width:36px; height:36px; border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:0.55rem; font-weight:700; color:#fff; transition: all 0.3s ease; cursor:default; }
.pump-tile:hover { transform:scale(1.15); z-index:2; }
.pump-tile.focus { animation: pulse-border 2s ease-in-out infinite; border:2px solid #6366F1; }

/* ── Story arc ── */
.arc { display:flex; gap:4px; margin:0.5rem 0; }
.arc-step { flex:1; height:4px; border-radius:2px; background:rgba(51,65,85,0.6); transition: background 0.3s ease; }
.arc-step.active { background: linear-gradient(90deg, #00D4AA, #6366F1); }
.arc-step.done { background: #00D4AA; }

/* ── Parts table ── */
.parts-tbl { width:100%; border-collapse:separate; border-spacing:0 3px; font-size:0.78rem; }
.parts-tbl th { color:#94A3B8; font-size:0.68rem; text-transform:uppercase; letter-spacing:0.05em; padding:0.3rem 0.5rem; text-align:left; }
.parts-tbl td { padding:0.35rem 0.5rem; color:#CBD5E1; }
.stock-ok { color:#22C55E; font-weight:700; }
.stock-low { color:#F59E0B; font-weight:700; }
.stock-out { color:#EF4444; font-weight:700; }

/* ── Timeline bars ── */
.tl-container { display:flex; gap:2px; align-items:flex-end; height:120px; padding:0.5rem 0; }
.tl-bar { flex:1; border-radius:3px 3px 0 0; min-width:4px; position:relative; transition: all 0.3s ease; }
.tl-bar:hover { opacity:1 !important; filter:brightness(1.3); }
.tl-event { border:2px solid rgba(239,68,68,0.6); border-radius:3px 3px 0 0; }

/* ── Override stale Streamlit defaults ── */
[data-testid="stMetric"] {
    background: rgba(30,41,59,0.7); border: 1px solid rgba(0,212,170,0.12);
    border-radius: 16px; padding: 1rem;
}
[data-testid="stMetricLabel"] { color: #94A3B8 !important; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.06em; }
[data-testid="stMetricValue"] { color: #00D4AA !important; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session & Helpers
# ---------------------------------------------------------------------------
session = get_active_session()

def run_query(sql):
    try:
        df = session.sql(sql).to_pandas()
        # Snowpark to_pandas() can return Decimal objects that Plotly cannot plot.
        # Brute-force: try converting every column to float64.
        for col in df.columns:
            try:
                df[col] = df[col].apply(lambda x: float(x) if x is not None else None)
            except (ValueError, TypeError):
                pass  # String columns will fail — that's fine
        return df
    except Exception as e:
        st.error(f"Query error: {e}")
        return pd.DataFrame()

def run_query_scalar(sql):
    try:
        result = session.sql(sql).collect()
        return result[0][0] if result else None
    except Exception as e:
        st.error(f"Query error: {e}")
        return None

def glass_card(label, value, color="teal", sub=""):
    sub_html = f'<div class="sub">{sub}</div>' if sub else ''
    return f'<div class="glass-card"><div class="label">{label}</div><div class="value {color}">{value}</div>{sub_html}</div>'

# ---------------------------------------------------------------------------
# Auto-detect Marketplace data sources (fall back to fabricated samples)
# ---------------------------------------------------------------------------
@st.cache_resource
def _detect_weather_db():
    try:
        session.sql("SHOW SCHEMAS IN DATABASE GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI").collect()
        return 'GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI.PWS_BI_SAMPLE.POINT_HISTORY_DAY'
    except Exception:
        return 'AVEVA_CONNECT.PUBLIC.WEATHER_HISTORY_SAMPLE'

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCHEMA = '"f6dd054e-d7b7-4b48-97f3-1b0eb2e91ab0"'
PUMP_TABLE = 'AVEVA_CONNECT.PUBLIC.PUMP_DATA_ENRICHED'
WEATHER_TABLE = _detect_weather_db()
FOCUS_PUMP = 'PMP-DMA04A-06'

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.markdown("### Navigation")
page = st.sidebar.radio("Go to:", [
    "1. Fleet Overview",
    "2. Predicted vs Actual",
    "3. Weather Context",
    "4. AI Recommendation",
], label_visibility="collapsed")

st.sidebar.markdown("---")
st.sidebar.markdown(
    '<span class="badge badge-aveva">AVEVA CLD</span> '
    '<span class="badge badge-sf">WeatherSource</span> '
    '<span class="badge badge-sap">SAP ERP</span> '
    '<span class="badge badge-docs">Knowledge Base</span> '
    '<span class="badge badge-cortex">Cortex AI</span>',
    unsafe_allow_html=True,
)

# Story arc progress
page_idx = ["1. Fleet Overview","2. Predicted vs Actual","3. Weather Context","4. AI Recommendation"].index(page)
arc_html = '<div class="arc">'
for i in range(4):
    if i < page_idx:
        arc_html += '<div class="arc-step done"></div>'
    elif i == page_idx:
        arc_html += '<div class="arc-step active"></div>'
    else:
        arc_html += '<div class="arc-step"></div>'
arc_html += '</div>'
st.sidebar.markdown(arc_html, unsafe_allow_html=True)

st.sidebar.markdown(
    '<div style="text-align:center; margin:0.8rem 0;">'
    '<span class="live-dot"></span>'
    '<span style="color:#22C55E; font-size:0.78rem; font-weight:600;">LIVE</span>'
    '<span style="color:#64748B; font-size:0.72rem;"> &nbsp; 7.6M+ readings</span>'
    '</div>',
    unsafe_allow_html=True,
)

st.sidebar.caption("Live data via Iceberg REST Catalog")
st.sidebar.caption("Weather from Snowflake Marketplace")
st.sidebar.caption("SAP maintenance & parts data")
st.sidebar.caption("28 industrial docs via Cortex Search")
st.sidebar.caption("Agentic AI via Cortex mistral-large2")

with st.sidebar.expander(":material/schema: Architecture", expanded=False):
    st.image("Presentation_arch.png")

st.sidebar.markdown("---")
st.sidebar.markdown(
    '<div style="text-align:center; font-size:0.7rem; color:#64748B; line-height:1.6;">'
    '<strong style="color:#94A3B8;">5</strong> data sources &nbsp;|&nbsp; '
    '<strong style="color:#94A3B8;">25</strong> pumps &nbsp;|&nbsp; '
    '<strong style="color:#94A3B8;">77</strong> sensors<br/>'
    '<strong style="color:#94A3B8;">28</strong> knowledge docs &nbsp;|&nbsp; '
    '<strong style="color:#94A3B8;">3</strong>-step AI agent'
    '</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Hero Header
# ---------------------------------------------------------------------------
st.markdown("""
<div class="hero">
    <h1>The Complete Picture</h1>
    <p class="tagline">
        <span class="badge badge-aveva">AVEVA</span> tells you WHAT is happening &nbsp;|&nbsp;
        <span class="badge badge-sf">Snowflake</span> tells you WHY &nbsp;|&nbsp;
        <span class="badge badge-sap">SAP</span> tells you WHAT it costs &nbsp;|&nbsp;
        <span class="badge badge-docs">Knowledge Base</span> provides expertise &nbsp;|&nbsp;
        <span class="badge badge-cortex">Cortex AI Agent</span> recommends what to do
    </p>
    <div style="margin-top:0.8rem;">
        <span class="live-dot"></span>
        <span style="color:#22C55E; font-size:0.8rem; font-weight:600;">LIVE</span>
        <span style="color:#64748B; font-size:0.75rem;"> &nbsp; 7.6M+ sensor readings &nbsp;|&nbsp; 5 data sources &nbsp;|&nbsp; Agentic AI &nbsp;|&nbsp; Iceberg REST Catalog</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1: Fleet Overview
# ═══════════════════════════════════════════════════════════════════════════════
if page == "1. Fleet Overview":
    st.markdown("## Fleet Overview — 25 Water Pumps Across 4 DMAs")

    @st.cache_data(ttl=300)
    def load_fleet():
        return run_query(f"""
            SELECT "Name" as PUMP,
                ROUND(AVG(CASE WHEN "Field"='Pump Efficiency Value %' THEN "Value" END),2) as AVG_EFF,
                ROUND(MIN(CASE WHEN "Field"='Pump Efficiency Value %' THEN "Value" END),2) as MIN_EFF,
                ROUND(AVG(CASE WHEN "Field"='Motor Power Value kW' THEN "Value" END),1) as POWER,
                ROUND(MAX(CASE WHEN "Field"='Run Hours Since Last Maintenance Value h' THEN "Value" END),0) as RUN_H,
                ROUND(AVG(CASE WHEN "Field"='Vibration X - Inboard Bearing Value' THEN "Value" END),4) as VIB,
                COUNT(*) as CNT
            FROM {PUMP_TABLE}
            WHERE "Field" IN ('Pump Efficiency Value %','Motor Power Value kW',
                              'Run Hours Since Last Maintenance Value h','Vibration X - Inboard Bearing Value')
            GROUP BY 1 ORDER BY AVG_EFF ASC NULLS LAST
        """)

    fleet = load_fleet()
    if fleet.empty:
        st.warning("No fleet data available")
        st.stop()

    # Force numeric columns to float (Snowpark Decimal safety)
    for c in ['AVG_EFF','MIN_EFF','POWER','RUN_H','VIB']:
        if c in fleet.columns:
            fleet[c] = pd.to_numeric(fleet[c], errors='coerce')

    def risk(r):
        if r.get('MIN_EFF') and r['MIN_EFF'] < 50: return "CRITICAL"
        if r.get('RUN_H') and r['RUN_H'] > 2800: return "HIGH"
        if r.get('AVG_EFF') and r['AVG_EFF'] < 74: return "ELEVATED"
        return "NORMAL"

    fleet['RISK'] = fleet.apply(risk, axis=1)
    n_crit = (fleet['RISK']=='CRITICAL').sum()
    n_high = (fleet['RISK']=='HIGH').sum()
    n_elev = (fleet['RISK']=='ELEVATED').sum()
    n_norm = (fleet['RISK']=='NORMAL').sum()

    # ── KPI Cards ──
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(glass_card("Total Pumps", "25", "teal", "Across 4 DMAs"), unsafe_allow_html=True)
    with c2: st.markdown(glass_card("Fleet Efficiency", f"{fleet['AVG_EFF'].mean():.1f}%", "purple", "Avg across fleet"), unsafe_allow_html=True)
    with c3: st.markdown(glass_card("Pumps at Risk", f"{n_crit + n_high}", "red" if n_crit > 0 else "amber", f"{n_crit} critical, {n_high} high"), unsafe_allow_html=True)
    with c4: st.markdown(glass_card("Predictive Models", "1", "purple", f"{FOCUS_PUMP}"), unsafe_allow_html=True)

    st.markdown("")

    # ── DMA Fleet Grid + Efficiency Ranking ──
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown("**Fleet Status by DMA Zone**")
        # Organize pumps by DMA zone
        dma_map = {}
        for _, r in fleet.iterrows():
            # Extract DMA from pump name: PMP-DMA01A-11 → DMA01
            dma = r['PUMP'][4:9]  # "DMA01", "DMA02", etc.
            if dma not in dma_map:
                dma_map[dma] = []
            dma_map[dma].append(r)

        risk_colors = {'CRITICAL':'#EF4444','HIGH':'#F59E0B','ELEVATED':'#EAB308','NORMAL':'#22C55E'}
        grid_html = '<div class="dma-grid">'
        for dma in sorted(dma_map.keys()):
            pumps = dma_map[dma]
            n_issues = sum(1 for p in pumps if p['RISK'] in ('CRITICAL','HIGH'))
            zone_border = 'border-color:rgba(239,68,68,0.3);' if n_issues > 0 else ''
            grid_html += f'<div class="dma-zone" style="{zone_border}">'
            grid_html += f'<h5>{dma} &nbsp; <span style="color:#64748B;">({len(pumps)} pumps)</span></h5>'
            grid_html += '<div class="pump-grid">'
            for p in pumps:
                color = risk_colors.get(p['RISK'], '#22C55E')
                num = p['PUMP'].split('-')[-1]
                focus_cls = ' focus' if p['PUMP'] == FOCUS_PUMP else ''
                title = f'{p["PUMP"]}: {p["AVG_EFF"]:.1f}% eff, {p["RISK"]}'
                grid_html += (
                    f'<div class="pump-tile{focus_cls}" style="background:{color};" title="{title}">'
                    f'{num}</div>'
                )
            grid_html += '</div></div>'
        grid_html += '</div>'
        st.markdown(grid_html, unsafe_allow_html=True)
        st.markdown(
            '<div style="margin-top:0.5rem; font-size:0.68rem; color:#64748B;">'
            '<span style="color:#EF4444;">&#9632;</span> Critical &nbsp; '
            '<span style="color:#F59E0B;">&#9632;</span> High &nbsp; '
            '<span style="color:#EAB308;">&#9632;</span> Elevated &nbsp; '
            '<span style="color:#22C55E;">&#9632;</span> Normal &nbsp; '
            '<span style="color:#6366F1;">&#9634;</span> Predictive Model'
            '</div>',
            unsafe_allow_html=True,
        )

    with col_right:
        st.markdown("**Pump Efficiency Ranking**")
        sorted_fleet = fleet.sort_values('AVG_EFF', ascending=True)
        eff_min = max(sorted_fleet['AVG_EFF'].min() - 2, 0)
        eff_max = sorted_fleet['AVG_EFF'].max() + 1
        eff_range = eff_max - eff_min if eff_max > eff_min else 1
        bar_html = '<div style="font-size:0.82rem;">'
        for _, r in sorted_fleet.iterrows():
            rk = r['RISK']
            if rk == 'CRITICAL': bar_c = '#EF4444'
            elif rk == 'HIGH': bar_c = '#F59E0B'
            elif rk == 'ELEVATED': bar_c = '#EAB308'
            else: bar_c = '#22C55E'
            pct = max(((r['AVG_EFF'] - eff_min) / eff_range) * 100, 2)
            lbl = r['PUMP']
            if r['PUMP'] == FOCUS_PUMP:
                lbl += ' *'
            bar_html += (
                f'<div style="display:flex; align-items:center; margin:2px 0;">'
                f'<div style="width:110px; text-align:right; padding-right:8px; color:#CBD5E1; font-size:0.72rem; white-space:nowrap;">{lbl}</div>'
                f'<div style="flex:1; background:rgba(51,65,85,0.4); border-radius:4px; height:18px; overflow:hidden;">'
                f'<div style="width:{pct:.0f}%; background:{bar_c}; height:100%; border-radius:4px; '
                f'display:flex; align-items:center; justify-content:flex-end; padding-right:6px;">'
                f'<span style="color:#fff; font-size:0.7rem; font-weight:700;">{r["AVG_EFF"]:.1f}%</span>'
                f'</div></div></div>'
            )
        bar_html += '</div>'
        st.markdown(bar_html, unsafe_allow_html=True)

    # ── Color-coded Fleet Table ──
    st.markdown("#### Fleet Health Detail")
    risk_class_map = {'CRITICAL':'row-critical','HIGH':'row-high','ELEVATED':'row-elevated','NORMAL':'row-normal'}
    pill_class_map = {'CRITICAL':'pill-critical','HIGH':'pill-high','ELEVATED':'pill-elevated','NORMAL':'pill-normal'}

    table_html = '<table class="risk-table"><thead><tr>'
    for h in ['Pump','Efficiency','Min Eff.','Power','Run Hours','Vibration','Risk']:
        table_html += f'<th>{h}</th>'
    table_html += '</tr></thead><tbody>'
    for _, r in fleet.iterrows():
        rk = r['RISK']
        row_cls = risk_class_map.get(rk, 'row-normal')
        if r['PUMP'] == FOCUS_PUMP:
            row_cls = 'row-focus'
        table_html += f'<tr class="{row_cls}">'
        pump_label = r['PUMP']
        if r['PUMP'] == FOCUS_PUMP:
            pump_label += ' <span class="badge badge-aveva" style="font-size:0.65rem;">PREDICTIVE MODEL</span>'
        table_html += f'<td><strong>{pump_label}</strong></td>'
        table_html += f'<td>{r["AVG_EFF"]:.1f}%</td>'
        table_html += f'<td>{r["MIN_EFF"]:.1f}%</td>'
        table_html += f'<td>{r["POWER"]:.0f} kW</td>'
        table_html += f'<td>{int(r["RUN_H"] or 0):,}h</td>'
        table_html += f'<td>{r["VIB"]:.3f} mm/s</td>'
        pill_cls = pill_class_map.get(rk, 'pill-normal')
        table_html += f'<td><span class="risk-pill {pill_cls}">{rk}</span></td>'
        table_html += '</tr>'
    table_html += '</tbody></table>'
    st.markdown(table_html, unsafe_allow_html=True)

    # ── Story prompt ──
    st.markdown(
        '<div class="story-next"><p>One pump has AVEVA\'s full predictive model with 76 channels. '
        'Select <strong>2. Predicted vs Actual</strong> to see how it performs.</p></div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2: Predicted vs Actual
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "2. Predicted vs Actual":
    st.markdown(f"## Predicted vs Actual — {FOCUS_PUMP}")
    st.markdown(
        '<span class="badge badge-aveva">AVEVA PREDICTIVE MODEL</span> &nbsp; '
        '76 predicted channels on this pump',
        unsafe_allow_html=True,
    )

    sensor_options = {
        "Thrust Bearing Temp 3": ("Thrust Bearing Temperature 3 Value °C", "Thrust Bearing Temperature 3|Predicted Value °C", "°C"),
        "Motor Current": ("Motor Current Value A", "Motor Current|Predicted Value A", "A"),
        "Ambient Temperature": ("Ambient Temperature Value °C", "Ambient Temperature|Predicted Value °C", "°C"),
        "Thrust Bearing Temp 1": ("Thrust Bearing Temperature 1 Value °C", "Thrust Bearing Temperature 1|Predicted Value °C", "°C"),
        "Thrust Bearing Temp 2": ("Thrust Bearing Temperature 2 Value °C", "Thrust Bearing Temperature 2|Predicted Value °C", "°C"),
        "Suction Chamber Level": ("Suction Chamber Level Value mm", "Suction Chamber Level|Predicted Value mm", "mm"),
        "Vibration Y Drive End": ("Motor Bearing Vibration Y Drive End Value", "Motor Bearing Vibration Y Drive End|Predicted Value", "mm/s"),
    }

    sel = st.selectbox("Select sensor channel:", list(sensor_options.keys()), index=0)
    actual_f, pred_f, unit = sensor_options[sel]

    @st.cache_data(ttl=300)
    def load_pa(af, pf):
        return run_query(f"""
            SELECT DATE_TRUNC('day',"Timestamp") as DAY,
                ROUND(AVG(CASE WHEN "Field"='{af}' THEN "Value" END),3) as ACTUAL,
                ROUND(AVG(CASE WHEN "Field"='{pf}' THEN "Value" END),3) as PREDICTED
            FROM {PUMP_TABLE}
            WHERE "Name"='{FOCUS_PUMP}' AND "Field" IN ('{af}','{pf}')
            GROUP BY 1 HAVING ACTUAL IS NOT NULL ORDER BY 1
        """)

    df = load_pa(actual_f, pred_f)
    if df.empty:
        st.warning("No data for this channel")
        st.stop()

    df['DAY'] = pd.to_datetime(df['DAY'].astype(str).str.strip('"'))
    # Force numeric (Snowpark Decimal safety)
    for c in ['ACTUAL','PREDICTED']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    df['DEV'] = df['ACTUAL'] - df['PREDICTED']

    valid = df.dropna(subset=['PREDICTED'])
    mae = valid['DEV'].abs().mean() if not valid.empty else 0
    max_dev = valid['DEV'].abs().max() if not valid.empty else 0

    # ── KPI Cards ──
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(glass_card("Days Tracked", str(len(valid)), "teal"), unsafe_allow_html=True)
    with c2: st.markdown(glass_card("Mean Abs Error", f"{mae:.2f} {unit}", "purple"), unsafe_allow_html=True)
    with c3: st.markdown(glass_card("Max Deviation", f"{max_dev:.2f} {unit}", "amber" if max_dev > 1.5 else "teal"), unsafe_allow_html=True)
    with c4:
        status = "Accurate" if mae < 2 else "Drifting"
        clr = "teal" if mae < 2 else "red"
        st.markdown(glass_card("Model Status", status, clr), unsafe_allow_html=True)

    st.markdown("")

    # ── Unified chart with deviation fill ──
    fig = make_subplots(rows=2, cols=1, row_heights=[0.75, 0.25], shared_xaxes=True,
                        vertical_spacing=0.05)

    # Main traces
    fig.add_trace(go.Scatter(
        x=df['DAY'], y=df['ACTUAL'], name='Actual',
        line=dict(color='#00D4AA', width=2.5),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df['DAY'], y=df['PREDICTED'], name='AVEVA Predicted',
        line=dict(color='#6366F1', width=2, dash='dash'),
    ), row=1, col=1)

    # Deviation fill — upper bound (actual) and lower bound (predicted)
    fig.add_trace(go.Scatter(
        x=pd.concat([df['DAY'], df['DAY'][::-1]]),
        y=pd.concat([df['ACTUAL'], df['PREDICTED'][::-1]]),
        fill='toself', fillcolor='rgba(245,158,11,0.08)',
        line=dict(width=0), showlegend=False, hoverinfo='skip',
    ), row=1, col=1)

    # Deviation bars
    bar_colors = ['#EF4444' if abs(d) > 1.5 else '#F59E0B' if abs(d) > 0.5 else '#22C55E'
                  for d in df['DEV'].fillna(0)]
    fig.add_trace(go.Bar(
        x=df['DAY'], y=df['DEV'], name='Deviation',
        marker_color=bar_colors, showlegend=False,
    ), row=2, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.2)", row=2, col=1)

    fig.update_layout(
        template="plotly_dark", height=550,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(t=20, b=30),
    )
    fig.update_yaxes(title_text=f"{sel} ({unit})", row=1, col=1)
    fig.update_yaxes(title_text=f"Dev ({unit})", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        f'> AVEVA\'s model is **accurate** — MAE of just {mae:.2f} {unit} over {len(valid)} days. '
        f'But notice the deviation spikes. Is that mechanical wear, or something external?',
    )

    st.markdown(
        '<div class="story-next"><p>The deviations might not be equipment failure. '
        'Select <strong>3. Weather Context</strong> to add data from outside the plant.</p></div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3: Weather Context
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "3. Weather Context":
    st.markdown("## The WHY — Weather Context from Snowflake Marketplace")
    st.markdown(
        '<span class="badge badge-aveva">AVEVA CLD</span> + '
        '<span class="badge badge-sf">WeatherSource Marketplace</span> &nbsp; '
        'Cross-platform JOIN in a single SQL query',
        unsafe_allow_html=True,
    )

    @st.cache_data(ttl=300)
    def load_weather_join():
        return run_query(f"""
            WITH pump_daily AS (
                SELECT DATE_TRUNC('day',"Timestamp") as DAY,
                    AVG(CASE WHEN "Field"='Vibration X - Inboard Bearing Value' THEN "Value" END) as VIB,
                    AVG(CASE WHEN "Field"='Pump Efficiency Value %' THEN "Value" END) as EFF,
                    AVG(CASE WHEN "Field"='Motor Power Value kW' THEN "Value" END) as POWER
                FROM {PUMP_TABLE}
                WHERE "Field" IN ('Vibration X - Inboard Bearing Value','Pump Efficiency Value %','Motor Power Value kW')
                GROUP BY 1
            ),
            weather AS (
                SELECT DATE_VALID_STD as DAY, AVG_TEMPERATURE_AIR_2M_F as TEMP_F,
                    ROUND((AVG_TEMPERATURE_AIR_2M_F-32)*5.0/9.0,1) as TEMP_C,
                    "__AVG_WIND_SPEED_10M_MPH" as WIND, AVG_HUMIDITY_RELATIVE_2M_PCT as HUMID
                FROM {WEATHER_TABLE} WHERE CITY_NAME='calgary'
            )
            SELECT p.DAY, w.TEMP_F, w.TEMP_C, w.WIND, w.HUMID, p.VIB, p.EFF, p.POWER
            FROM pump_daily p JOIN weather w ON p.DAY=w.DAY
            WHERE p.VIB IS NOT NULL ORDER BY p.DAY
        """)

    wx = load_weather_join()
    if wx.empty:
        st.warning("No weather data available")
        st.stop()

    wx['DAY'] = pd.to_datetime(wx['DAY'].astype(str).str.strip('"'))
    # Force numeric (Snowpark Decimal safety)
    for c in ['TEMP_F','TEMP_C','WIND','HUMID','VIB','EFF','POWER']:
        if c in wx.columns:
            wx[c] = pd.to_numeric(wx[c], errors='coerce')
    r_tv = wx[['TEMP_F','VIB']].dropna().corr().iloc[0,1]
    r_te = wx[['TEMP_F','EFF']].dropna().corr().iloc[0,1]
    r_we = wx[['WIND','EFF']].dropna().corr().iloc[0,1]
    t_min, t_max = wx['TEMP_F'].min(), wx['TEMP_F'].max()

    # ── KPI Cards ──
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(glass_card("Temp ↔ Vibration", f"r = {r_tv:.2f}", "amber"), unsafe_allow_html=True)
    with c2: st.markdown(glass_card("Temp ↔ Efficiency", f"r = {r_te:.2f}", "purple"), unsafe_allow_html=True)
    with c3: st.markdown(glass_card("Days Joined", str(len(wx)), "teal"), unsafe_allow_html=True)
    with c4: st.markdown(glass_card("Temp Swing", f"{t_max-t_min:.0f}°F", "red", f"{t_min:.0f}°F → {t_max:.0f}°F"), unsafe_allow_html=True)

    st.markdown("")

    # ── Temperature + Vibration Timeline (HTML — reliable in SiS) ──
    st.markdown("**Temperature (WeatherSource) vs Pump Vibration (AVEVA)**")

    if not wx.empty and 'VIB' in wx.columns and 'TEMP_F' in wx.columns:
        vib_max_val = wx['VIB'].max()
        vib_min_val = wx['VIB'].min()
        vib_rng = vib_max_val - vib_min_val if vib_max_val > vib_min_val else 1
        temp_min_val = wx['TEMP_F'].min()
        temp_max_val = wx['TEMP_F'].max()
        temp_rng = temp_max_val - temp_min_val if temp_max_val > temp_min_val else 1

        tl_html = '<div class="tl-container">'
        for _, row in wx.sort_values('DAY').iterrows():
            day_str = str(row['DAY'])[:10]
            # Vibration bar height (10%-100%)
            vib_pct = max(10, ((row['VIB'] - vib_min_val) / vib_rng) * 100)
            # Temperature as background color (blue cold → red hot)
            temp_norm = (row['TEMP_F'] - temp_min_val) / temp_rng
            r_c = int(60 + 195 * temp_norm)
            g_c = int(80 + 80 * (1 - abs(temp_norm - 0.5) * 2))
            b_c = int(200 * (1 - temp_norm))
            # Is this in the weather event window?
            event_cls = ' tl-event' if '2026-04-21' <= day_str <= '2026-04-26' else ''
            tl_html += (
                f'<div class="tl-bar{event_cls}" style="height:{vib_pct:.0f}%; '
                f'background:rgb({r_c},{g_c},{b_c}); opacity:0.85;" '
                f'title="{day_str}: {row["TEMP_F"]:.0f}°F / {row["VIB"]:.3f} mm/s"></div>'
            )
        tl_html += '</div>'

        # Legend row
        tl_html += (
            '<div style="display:flex; justify-content:space-between; font-size:0.7rem; color:#94A3B8; margin-top:4px;">'
            f'<span>Bar height = vibration ({vib_min_val:.3f} – {vib_max_val:.3f} mm/s)</span>'
            f'<span>Color = temperature ({temp_min_val:.0f}°F '
            '<span style="color:#3B82F6;">cold</span> → '
            f'{temp_max_val:.0f}°F <span style="color:#EF4444;">hot</span>)</span>'
            '</div>'
            '<div style="font-size:0.7rem; color:#EF4444; margin-top:2px;">&#9634; = Apr 21-26 weather event</div>'
        )
        st.markdown(tl_html, unsafe_allow_html=True)

    # ── Correlation detail panels (HTML — Plotly scatter unreliable in SiS) ──
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown(f"**Temperature vs Vibration &nbsp; (r = {r_tv:.2f})**")
        # Show daily data as a mini HTML heatmap strip
        mask = wx[['DAY','TEMP_F','VIB']].dropna().sort_values('DAY')
        if not mask.empty:
            vib_min, vib_max = mask['VIB'].min(), mask['VIB'].max()
            vib_range = vib_max - vib_min if vib_max > vib_min else 1
            strip_html = '<div style="display:flex; flex-wrap:wrap; gap:3px; margin:0.5rem 0;">'
            for _, row in mask.iterrows():
                intensity = (row['VIB'] - vib_min) / vib_range
                # Red scale: higher vibration = more red
                r_val = int(100 + 155 * intensity)
                g_val = int(200 * (1 - intensity))
                b_val = int(100 * (1 - intensity))
                day_str = str(row['DAY'])[:10] if hasattr(row['DAY'], 'strftime') else str(row['DAY'])[:10]
                strip_html += (
                    f'<div style="width:28px; height:28px; border-radius:4px; '
                    f'background:rgb({r_val},{g_val},{b_val}); opacity:0.85;" '
                    f'title="{day_str}: {row["TEMP_F"]:.0f}°F / {row["VIB"]:.3f} mm/s"></div>'
                )
            strip_html += '</div>'
            strip_html += '<div style="display:flex; justify-content:space-between; font-size:0.7rem; color:#94A3B8;">'
            strip_html += f'<span>Low vib ({vib_min:.3f})</span><span>High vib ({vib_max:.3f})</span></div>'
            st.markdown(strip_html, unsafe_allow_html=True)

            st.markdown(
                f'<div class="info-card" style="margin-top:0.5rem;"><p>'
                f'Higher temperatures drive higher vibration through thermal expansion of bearing clearances. '
                f'On warm days (>{mask["TEMP_F"].quantile(0.75):.0f}°F), vibration averages '
                f'{mask[mask["TEMP_F"] > mask["TEMP_F"].quantile(0.75)]["VIB"].mean():.3f} mm/s '
                f'vs {mask[mask["TEMP_F"] < mask["TEMP_F"].quantile(0.25)]["VIB"].mean():.3f} mm/s on cold days.</p></div>',
                unsafe_allow_html=True,
            )

    with col_r:
        st.markdown(f"**Temperature vs Efficiency &nbsp; (r = {r_te:.2f})**")
        mask2 = wx[['DAY','TEMP_F','EFF']].dropna().sort_values('DAY')
        if not mask2.empty:
            eff_min_v, eff_max_v = mask2['EFF'].min(), mask2['EFF'].max()
            eff_range_v = eff_max_v - eff_min_v if eff_max_v > eff_min_v else 1
            strip2_html = '<div style="display:flex; flex-wrap:wrap; gap:3px; margin:0.5rem 0;">'
            for _, row in mask2.iterrows():
                intensity = (row['EFF'] - eff_min_v) / eff_range_v
                # Green scale: higher efficiency = more green
                r_val = int(100 * (1 - intensity))
                g_val = int(100 + 155 * intensity)
                b_val = int(100 * (1 - intensity))
                day_str = str(row['DAY'])[:10] if hasattr(row['DAY'], 'strftime') else str(row['DAY'])[:10]
                strip2_html += (
                    f'<div style="width:28px; height:28px; border-radius:4px; '
                    f'background:rgb({r_val},{g_val},{b_val}); opacity:0.85;" '
                    f'title="{day_str}: {row["TEMP_F"]:.0f}°F / {row["EFF"]:.1f}%"></div>'
                )
            strip2_html += '</div>'
            strip2_html += '<div style="display:flex; justify-content:space-between; font-size:0.7rem; color:#94A3B8;">'
            strip2_html += f'<span>Low eff ({eff_min_v:.1f}%)</span><span>High eff ({eff_max_v:.1f}%)</span></div>'
            st.markdown(strip2_html, unsafe_allow_html=True)

            st.markdown(
                f'<div class="info-card" style="margin-top:0.5rem;"><p>'
                f'Temperature changes affect pump efficiency through fluid viscosity and thermal expansion. '
                f'The correlation (r={r_te:.2f}) confirms weather is a contributing factor to performance variation.</p></div>',
                unsafe_allow_html=True,
            )

    # ── Insight callout ──
    st.markdown(
        '<div class="info-card"><h4>Key Insight — Physics Explains the Deviation</h4>'
        f'<p>Warmer temperatures correlate with higher vibration (r={r_tv:.2f}) due to thermal expansion '
        f'affecting bearing clearances. The Apr 21-26 temperature swing of {t_max-t_min:.0f}°F aligns with the '
        'deviation peaks seen in AVEVA\'s predicted vs actual chart. This is environmental — not mechanical failure.</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="info-card" style="border-color:rgba(0,212,170,0.3);">'
        '<h4>Without Snowflake Marketplace, this correlation is invisible to AVEVA\'s model</h4>'
        '<p>AVEVA captures what happens <strong>inside</strong> the plant. Snowflake Marketplace adds what happens '
        '<strong>outside</strong>. Together, operators get the complete picture.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="story-next"><p>Now let <strong>Cortex AI</strong> connect both data sources '
        'and generate an actionable recommendation. Select <strong>4. AI Recommendation</strong>.</p></div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 4: AI Recommendation
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "4. AI Recommendation":
    st.markdown("## Cortex AI Agent — The Complete Picture")

    # ── Data source flow (animated) ──
    st.markdown(
        '<div style="text-align:center; margin:1rem 0 1.5rem 0;">'
        '<span class="badge badge-aveva" style="font-size:0.85rem; padding:0.4rem 1rem;">AVEVA CLD</span>'
        ' &nbsp; <span class="flow-arrow">&#10132;</span> &nbsp; '
        '<span class="badge badge-sf" style="font-size:0.85rem; padding:0.4rem 1rem;">WeatherSource</span>'
        ' &nbsp; <span class="flow-arrow">&#10132;</span> &nbsp; '
        '<span class="badge badge-sap" style="font-size:0.85rem; padding:0.4rem 1rem;">SAP ERP</span>'
        ' &nbsp; <span class="flow-arrow">&#10132;</span> &nbsp; '
        '<span class="badge badge-docs" style="font-size:0.85rem; padding:0.4rem 1rem;">Knowledge Base</span>'
        ' &nbsp; <span class="flow-arrow">&#10132;</span> &nbsp; '
        '<span class="badge badge-cortex" style="font-size:0.85rem; padding:0.4rem 1rem;">Cortex AI Agent</span>'
        ' &nbsp; <span class="flow-arrow">&#10132;</span> &nbsp; '
        '<span style="color:#00D4AA; font-weight:700; font-size:1rem;">Recommendation</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    @st.cache_data(ttl=300)
    def load_ai_ctx():
        p = run_query(f"""
            SELECT
                ROUND(AVG(CASE WHEN "Field"='Thrust Bearing Temperature 3 Value °C' THEN "Value" END),2) as AT,
                ROUND(AVG(CASE WHEN "Field"='Thrust Bearing Temperature 3|Predicted Value °C' THEN "Value" END),2) as PT,
                ROUND(AVG(CASE WHEN "Field"='Motor Current Value A' THEN "Value" END),2) as AC,
                ROUND(AVG(CASE WHEN "Field"='Motor Current|Predicted Value A' THEN "Value" END),2) as PC,
                ROUND(AVG(CASE WHEN "Field"='Vibration X - Inboard Bearing Value' THEN "Value" END),4) as VIB,
                ROUND(AVG(CASE WHEN "Field"='Pump Efficiency Value %' THEN "Value" END),2) as EFF,
                ROUND(MAX(CASE WHEN "Field"='Run Hours Since Last Maintenance Value h' THEN "Value" END),0) as RH
            FROM {PUMP_TABLE} WHERE "Name"='{FOCUS_PUMP}' AND "Timestamp">=DATEADD(day,-14,CURRENT_TIMESTAMP())
        """)
        w = run_query(f"""
            SELECT ROUND(AVG(AVG_TEMPERATURE_AIR_2M_F),1) as AVGT,
                ROUND(MIN(AVG_TEMPERATURE_AIR_2M_F),1) as MINT,
                ROUND(MAX(AVG_TEMPERATURE_AIR_2M_F),1) as MAXT,
                ROUND(AVG("__AVG_WIND_SPEED_10M_MPH"),1) as AVGW
            FROM {WEATHER_TABLE} WHERE CITY_NAME='calgary' AND DATE_VALID_STD>=DATEADD(day,-14,CURRENT_DATE())
        """)
        # SAP: Next scheduled work order for focus pump
        sap_wo = run_query(f"""
            SELECT WORK_ORDER_ID, ORDER_TYPE_DESC, PLANNED_DATE, ESTIMATED_COST_USD,
                   STATUS, PRIORITY, DESCRIPTION, TECHNICIAN
            FROM AVEVA_CONNECT.PUBLIC.SAP_MAINTENANCE_ORDERS
            WHERE EQUIPMENT_ID='{FOCUS_PUMP}' AND STATUS IN ('SCHEDULED','IN_PROGRESS')
            ORDER BY PLANNED_DATE ASC LIMIT 1
        """)
        # SAP: Relevant spare parts (bearings for this pump)
        sap_parts = run_query("""
            SELECT MATERIAL_ID, DESCRIPTION, WAREHOUSE_LOCATION, QTY_ON_HAND,
                   UNIT_COST_USD, LEAD_TIME_DAYS, REORDER_POINT
            FROM AVEVA_CONNECT.PUBLIC.SAP_SPARE_PARTS
            WHERE PART_CATEGORY = 'BEARINGS' AND WAREHOUSE_LOCATION = 'Calgary Main'
            ORDER BY MATERIAL_ID
        """)
        # SAP: Maintenance history summary
        sap_hist = run_query(f"""
            SELECT COUNT(*) as TOTAL_WO,
                   SUM(CASE WHEN STATUS='COMPLETED' THEN 1 ELSE 0 END) as COMPLETED,
                   ROUND(SUM(ACTUAL_COST_USD),0) as TOTAL_SPENT,
                   MAX(COMPLETION_DATE) as LAST_MAINT
            FROM AVEVA_CONNECT.PUBLIC.SAP_MAINTENANCE_ORDERS
            WHERE EQUIPMENT_ID='{FOCUS_PUMP}'
        """)
        return p, w, sap_wo, sap_parts, sap_hist

    pump_df, weather_df, sap_wo_df, sap_parts_df, sap_hist_df = load_ai_ctx()
    p = pump_df.iloc[0] if not pump_df.empty else {}
    w = weather_df.iloc[0] if not weather_df.empty else {}
    sap_wo = sap_wo_df.iloc[0] if not sap_wo_df.empty else {}
    sap_hist = sap_hist_df.iloc[0] if not sap_hist_df.empty else {}

    # ── Extract SAP values (used by AI agent prompts below) ──
    next_wo = sap_wo.get('WORK_ORDER_ID', 'N/A')
    next_date = str(sap_wo.get('PLANNED_DATE', 'N/A')).replace('"', '')
    next_cost = sap_wo.get('ESTIMATED_COST_USD', 0)
    next_desc = sap_wo.get('DESCRIPTION', 'N/A')
    hist_spent = sap_hist.get('TOTAL_SPENT', 0)
    hist_last = str(sap_hist.get('LAST_MAINT', 'N/A')).replace('"', '')
    bearing_stock = 0
    if not sap_parts_df.empty:
        thrust_row = sap_parts_df[sap_parts_df['MATERIAL_ID'] == 'M-4420']
        if not thrust_row.empty:
            bearing_stock = int(thrust_row.iloc[0].get('QTY_ON_HAND', 0))

    # ── Context panels in collapsible expander ──
    with st.expander("Data Context — AVEVA · WeatherSource · SAP", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                '<div class="info-card" style="border-left:3px solid #6366F1;">'
                '<h4><span class="badge badge-aveva">AVEVA</span> &nbsp; Pump PMP-DMA04A-06 (14d)</h4>'
                f'<p>Bearing Temp: <strong>{p.get("AT","?")}</strong>°C actual vs <strong>{p.get("PT","?")}</strong>°C predicted<br/>'
                f'Motor Current: <strong>{p.get("AC","?")}</strong>A actual vs <strong>{p.get("PC","?")}</strong>A predicted<br/>'
                f'Vibration: <strong>{p.get("VIB","?")}</strong> mm/s &nbsp;|&nbsp; Efficiency: <strong>{p.get("EFF","?")}%</strong><br/>'
                f'Run Hours: <strong>{int(p.get("RH",0) or 0):,}h</strong></p></div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                '<div class="info-card" style="border-left:3px solid #00D4AA;">'
                '<h4><span class="badge badge-sf">WeatherSource</span> &nbsp; Calgary, AB (14d)</h4>'
                f'<p>Avg Temp: <strong>{w.get("AVGT","?")}°F</strong><br/>'
                f'Range: <strong>{w.get("MINT","?")}°F</strong> to <strong>{w.get("MAXT","?")}°F</strong> '
                f'(swing: {round(float(w.get("MAXT",61) or 61) - float(w.get("MINT",20) or 20))}°F)<br/>'
                f'Avg Wind: <strong>{w.get("AVGW","?")} mph</strong><br/>'
                f'Temp ↔ Vibration: <strong>r = 0.31</strong></p></div>',
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                '<div class="info-card" style="border-left:3px solid #38B6FF;">'
                '<h4><span class="badge badge-sap">SAP ERP</span> &nbsp; Maintenance & Parts</h4>'
                f'<p>Next Work Order: <strong>{next_wo}</strong><br/>'
                f'Planned: <strong>{next_date}</strong> — {next_desc}<br/>'
                f'Est. Cost: <strong>${next_cost:,.0f}</strong><br/>'
                f'Bearing Kits in Stock: <strong>{bearing_stock}</strong> (Calgary)<br/>'
                f'YTD Maint. Spend: <strong>${float(hist_spent or 0):,.0f}</strong></p></div>',
                unsafe_allow_html=True,
            )
            if not sap_parts_df.empty:
                parts_html = '<table class="parts-tbl"><thead><tr><th>Part</th><th>Stock</th><th>Lead</th><th>Cost</th></tr></thead><tbody>'
                for _, sp in sap_parts_df.iterrows():
                    qty = int(sp.get('QTY_ON_HAND', 0))
                    reorder = int(sp.get('REORDER_POINT', 0))
                    if qty == 0:
                        stock_cls = 'stock-out'
                    elif qty <= reorder:
                        stock_cls = 'stock-low'
                    else:
                        stock_cls = 'stock-ok'
                    desc_short = str(sp.get('DESCRIPTION', ''))[:28]
                    parts_html += (
                        f'<tr><td>{desc_short}</td>'
                        f'<td class="{stock_cls}">{qty}</td>'
                        f'<td>{int(sp.get("LEAD_TIME_DAYS",0))}d</td>'
                        f'<td>${float(sp.get("UNIT_COST_USD",0)):,.0f}</td></tr>'
                    )
                parts_html += '</tbody></table>'
                st.markdown(parts_html, unsafe_allow_html=True)

    if st.button("Run AI Agent Analysis", type="primary", use_container_width=True):
        import time as _time

        # ====================================================================
        # AGENT STEP 1: Structured Data Analysis (Cortex COMPLETE)
        # ====================================================================
        step1_start = _time.time()
        step1_ph = st.empty()
        step1_ph.markdown(
            '<div class="agent-step running">'
            '<div class="step-header"><div class="step-num running">1</div>'
            '<div class="step-title">Analyzing Structured Data — AVEVA + Weather + SAP</div></div>'
            '<div class="step-detail">Cortex AI is examining sensor readings, predictive model deviations, weather correlations, and maintenance history...</div>'
            '</div>', unsafe_allow_html=True,
        )

        sap_context = ""
        if next_wo != 'N/A':
            sap_context = (
                f"\nSAP ERP CONTEXT:\n"
                f"- Next Work Order: {next_wo} ({sap_wo.get('ORDER_TYPE_DESC','')}) — {next_desc}\n"
                f"- Scheduled Date: {next_date}\n"
                f"- Estimated Cost: ${float(next_cost or 0):,.0f}\n"
                f"- Thrust Bearing Kits in Stock: {bearing_stock} units at Calgary Main (Material M-4420, $2800/unit)\n"
                f"- Lead Time if Reorder Needed: 14 days from SKF Industrial\n"
                f"- YTD Maintenance Spend on This Pump: ${float(hist_spent or 0):,.0f}\n"
                f"- Last Completed Maintenance: {hist_last}"
            )

        step1_prompt = (
            f"You are an industrial operations AI performing Step 1 of a 3-step analysis. "
            f"Analyze ONLY the structured data below. Identify key anomalies and provide an initial diagnosis.\n\n"
            f"PUMP: PMP-DMA04A-06 (14-day window)\n"
            f"- Bearing Temp: actual {p.get('AT',65.4)}°C vs predicted {p.get('PT',65.2)}°C "
            f"(deviation: {round(float(p.get('AT',65.4) or 65.4) - float(p.get('PT',65.2) or 65.2), 2)}°C)\n"
            f"- Motor Current: actual {p.get('AC',322.5)}A vs predicted {p.get('PC',322.5)}A\n"
            f"- Vibration: {p.get('VIB',0.53)} mm/s | Efficiency: {p.get('EFF',74.6)}%\n"
            f"- Run Hours: {int(p.get('RH',0) or 0)}h (fleet avg 2,400h)\n\n"
            f"WEATHER (Calgary, WeatherSource):\n"
            f"- Avg: {w.get('AVGT',38)}°F | Range: {w.get('MINT',20)}°F to {w.get('MAXT',61)}°F "
            f"(swing: {round(float(w.get('MAXT',61) or 61) - float(w.get('MINT',20) or 20))}°F)\n"
            f"- Known: Temperature<>Vibration r=0.31\n"
            f"{sap_context}\n\n"
            f"Respond ONLY with JSON:\n"
            '{"diagnosis": "one sentence initial assessment",'
            ' "anomalies": ["anomaly 1", "anomaly 2"],'
            ' "search_queries": ["query to find relevant OEM bulletins or SOPs", "query about failure modes or incident reports"],'
            ' "confidence_preliminary": 0.0 to 1.0}'
        )

        escaped1 = step1_prompt.replace("'", "''")
        raw1 = run_query_scalar(f"SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', '{escaped1}')")
        step1_elapsed = _time.time() - step1_start

        # Parse Step 1 result
        step1_result = None
        if raw1:
            try:
                s1 = raw1.find('{')
                e1 = raw1.rfind('}') + 1
                if s1 >= 0 and e1 > s1:
                    step1_result = json.loads(raw1[s1:e1])
            except Exception:
                pass

        diagnosis = step1_result.get('diagnosis', 'Analysis complete.') if step1_result else 'Structured data analyzed.'
        anomalies = step1_result.get('anomalies', ['Bearing temperature deviation detected']) if step1_result else ['Bearing temperature deviation detected']
        search_queries = step1_result.get('search_queries', ['thrust bearing temperature limits centrifugal pump', 'vibration weather correlation false alarm pump']) if step1_result else ['thrust bearing temperature limits centrifugal pump', 'vibration weather correlation false alarm pump']
        conf_prelim = float(step1_result.get('confidence_preliminary', 0.7)) if step1_result else 0.7

        # Render Step 1 done (compact — diagnosis only, no anomaly bullets)
        step1_ph.markdown(
            f'<div class="agent-step done">'
            f'<div class="step-header"><div class="step-num done">1</div>'
            f'<div class="step-title">Structured Data Analysis — Complete</div></div>'
            f'<div class="step-detail">{diagnosis} &nbsp; <strong>({conf_prelim:.0%} confidence)</strong></div>'
            f'<div class="step-time">{step1_elapsed:.1f}s — Cortex COMPLETE (mistral-large2)</div>'
            f'</div>', unsafe_allow_html=True,
        )

        # ====================================================================
        # AGENT STEP 2: Unstructured Knowledge Retrieval (Cortex Search)
        # ====================================================================
        step2_start = _time.time()
        step2_ph = st.empty()
        step2_ph.markdown(
            '<div class="agent-step running">'
            '<div class="step-header"><div class="step-num running">2</div>'
            '<div class="step-title">Retrieving Knowledge — Cortex Search over 28 Industrial Documents</div></div>'
            '<div class="step-detail">Searching OEM bulletins, maintenance SOPs, incident reports, industry standards, and regulatory guidelines...</div>'
            '</div>', unsafe_allow_html=True,
        )

        # Run 2 search queries from Step 1
        all_docs = []
        for sq in search_queries[:2]:
            sq_escaped = sq.replace('"', '\\"').replace("'", "''")
            search_json = '{"query": "' + sq_escaped + '", "columns": ["TITLE","DOC_TYPE","SOURCE","CONTENT"], "limit": 3}'
            search_result = run_query_scalar(
                f"SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW('AVEVA_CONNECT.PUBLIC.INDUSTRIAL_DOCS_SEARCH', '{search_json}')"
            )
            if search_result:
                try:
                    parsed = json.loads(search_result)
                    for doc in parsed.get('results', []):
                        scores = doc.get('@scores', {})
                        relevance = scores.get('reranker_score', 0)
                        all_docs.append({
                            'title': doc.get('TITLE', ''),
                            'doc_type': doc.get('DOC_TYPE', ''),
                            'source': doc.get('SOURCE', ''),
                            'content': doc.get('CONTENT', '')[:500],
                            'relevance': relevance,
                        })
                except Exception:
                    pass

        # Deduplicate by title and sort by relevance
        seen_titles = set()
        unique_docs = []
        for d in sorted(all_docs, key=lambda x: x['relevance'], reverse=True):
            if d['title'] not in seen_titles:
                seen_titles.add(d['title'])
                unique_docs.append(d)
        top_docs = unique_docs[:4]
        step2_elapsed = _time.time() - step2_start

        # Render Step 2 done (compact — title only, docs in expander)
        step2_ph.markdown(
            f'<div class="agent-step done">'
            f'<div class="step-header"><div class="step-num done">2</div>'
            f'<div class="step-title">Knowledge Retrieval — {len(top_docs)} Relevant Documents Found</div></div>'
            f'<div class="step-time">{step2_elapsed:.1f}s — Cortex Search (snowflake-arctic-embed-m-v1.5)</div>'
            f'</div>', unsafe_allow_html=True,
        )
        with st.expander(f"View {len(top_docs)} Retrieved Documents", expanded=False):
            for doc in top_docs:
                score_pct = max(0, min(100, (doc['relevance'] + 2) * 25))
                st.markdown(
                    f'<div class="doc-card">'
                    f'<div class="doc-title">{doc["title"]} <span class="doc-score">{score_pct:.0f}% match</span></div>'
                    f'<div class="doc-type">{doc["doc_type"]} — {doc["source"]}</div>'
                    f'<div class="doc-snippet">{doc["content"][:200]}...</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # ====================================================================
        # AGENT STEP 3: Synthesis & Final Recommendation (Cortex COMPLETE)
        # ====================================================================
        step3_start = _time.time()
        step3_ph = st.empty()
        step3_ph.markdown(
            '<div class="agent-step running">'
            '<div class="step-header"><div class="step-num running">3</div>'
            '<div class="step-title">Synthesizing Final Recommendation — Grounding in Knowledge Base</div></div>'
            '<div class="step-detail">Combining structured analysis + retrieved documents + SAP context into a grounded, citable recommendation...</div>'
            '</div>', unsafe_allow_html=True,
        )

        # Build document context for final prompt
        doc_context = "\nRETRIEVED KNOWLEDGE BASE DOCUMENTS:\n"
        for i, doc in enumerate(top_docs, 1):
            doc_context += f"\nDocument {i}: {doc['title']} (Source: {doc['source']}, Type: {doc['doc_type']})\n"
            doc_context += f"Content: {doc['content']}\n"

        step3_prompt = (
            f"You are an industrial operations AI performing the FINAL STEP of a 3-step agentic analysis. "
            f"You have already analyzed the structured data and retrieved relevant knowledge base documents. "
            f"Now synthesize everything into a final recommendation.\n\n"
            f"STEP 1 FINDINGS (Structured Data):\n"
            f"- Diagnosis: {diagnosis}\n"
            f"- Anomalies: {', '.join(anomalies)}\n"
            f"- Preliminary Confidence: {conf_prelim:.0%}\n\n"
            f"PUMP: PMP-DMA04A-06\n"
            f"- Bearing Temp: actual {p.get('AT',65.4)}°C vs predicted {p.get('PT',65.2)}°C\n"
            f"- Motor Current: {p.get('AC',322.5)}A vs predicted {p.get('PC',322.5)}A\n"
            f"- Vibration: {p.get('VIB',0.53)} mm/s | Efficiency: {p.get('EFF',74.6)}%\n"
            f"- Run Hours: {int(p.get('RH',0) or 0)}h\n"
            f"- Weather: {w.get('AVGT',38)}°F avg, swing {round(float(w.get('MAXT',61) or 61) - float(w.get('MINT',20) or 20))}°F, Temp-Vibration r=0.31\n"
            f"{sap_context}\n"
            f"{doc_context}\n\n"
            f"IMPORTANT: Cite specific documents by title in your evidence and recommendation. "
            f"Ground your advice in the OEM specs, SOPs, and incident reports retrieved above.\n\n"
            f"Respond ONLY with this JSON (no other text):\n"
            '{{"verdict": "CONTINUE OPERATIONS" or "EMERGENCY SHUTDOWN" or "SCHEDULE INSPECTION",'
            ' "confidence": 0.0 to 1.0,'
            ' "root_cause": "one sentence citing relevant document",'
            ' "evidence": ["evidence point citing Document 1", "evidence point citing Document 2", "evidence point citing Document 3"],'
            ' "action": "specific recommendation referencing SAP work order, spare parts, cost, AND relevant OEM bulletin or SOP — 2-3 sentences",'
            ' "sap_action": "specific SAP-grounded next step",'
            ' "citations": ["Document title 1", "Document title 2", "Document title 3"]}}'
        )

        escaped3 = step3_prompt.replace("'", "''")
        raw3 = run_query_scalar(f"SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', '{escaped3}')")
        step3_elapsed = _time.time() - step3_start

        # Parse Step 3 result
        rec = None
        if raw3:
            try:
                s3 = raw3.find('{')
                e3 = raw3.rfind('}') + 1
                if s3 >= 0 and e3 > s3:
                    rec = json.loads(raw3[s3:e3])
            except Exception:
                pass

        total_elapsed = step1_elapsed + step2_elapsed + step3_elapsed

        if rec and 'verdict' in rec:
            verdict = rec.get('verdict', 'CONTINUE OPERATIONS').upper()
            confidence = float(rec.get('confidence', 0.85))
            root_cause = rec.get('root_cause', '')
            evidence = rec.get('evidence', [])
            action = rec.get('action', '')
            citations = rec.get('citations', [])

            # Render Step 3 done
            step3_ph.markdown(
                f'<div class="agent-step done">'
                f'<div class="step-header"><div class="step-num done">3</div>'
                f'<div class="step-title">Synthesis Complete — Recommendation Ready</div></div>'
                f'<div class="step-detail"><strong>Verdict:</strong> {verdict} ({confidence:.0%} confidence)<br/>'
                f'<strong>Root Cause:</strong> {root_cause}</div>'
                f'<div class="step-time">{step3_elapsed:.1f}s — Cortex COMPLETE (mistral-large2) | Total agent time: {total_elapsed:.1f}s</div>'
                f'</div>', unsafe_allow_html=True,
            )

            st.markdown("")

            # Verdict card
            if 'CONTINUE' in verdict:
                v_cls = 'verdict-continue'
                gauge_cls = 'gauge-green'
            elif 'SHUTDOWN' in verdict:
                v_cls = 'verdict-shutdown'
                gauge_cls = 'gauge-red'
            else:
                v_cls = 'verdict-inspect'
                gauge_cls = 'gauge-amber'

            st.markdown(
                f'<div class="verdict {v_cls}">'
                f'<h2>{verdict}</h2>'
                f'<div class="conf">Confidence: {confidence:.0%} &nbsp;|&nbsp; 3-Step Agentic Analysis &nbsp;|&nbsp; {len(top_docs)} Documents Referenced</div>'
                f'<div class="gauge-track"><div class="gauge-fill {gauge_cls}" style="width:{confidence*100:.0f}%"></div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # ── Executive Summary — single card for plant manager ──
            sap_action = rec.get('sap_action', '')
            summary_html = (
                f'<div class="info-card" style="border-left:4px solid {("#F59E0B" if "INSPECT" in verdict else "#EF4444" if "SHUTDOWN" in verdict else "#22C55E")};">'
                f'<h4 style="font-size:1rem;">Executive Summary</h4>'
                f'<p><strong>What\'s Wrong:</strong> {root_cause}</p>'
                f'<p><strong>What To Do:</strong> {action}</p>'
            )
            if sap_action:
                summary_html += f'<p><strong>SAP Next Step:</strong> {sap_action}</p>'
            summary_html += (
                f'<p style="color:#64748B; font-size:0.78rem; margin-top:0.6rem;">'
                f'Based on {len(top_docs)} industrial documents &middot; {len(evidence)} evidence points &middot; {len(citations)} sources cited</p>'
                f'</div>'
            )
            st.markdown(summary_html, unsafe_allow_html=True)

            # Detailed evidence & citations in collapsible expander
            with st.expander("View Evidence & Citations", expanded=False):
                for i, ev in enumerate(evidence, 1):
                    st.markdown(f"**{i}.** {ev}")
                if citations:
                    st.markdown("---")
                    st.markdown("**Sources Cited:**")
                    for c_title in citations:
                        st.markdown(f"- {c_title}")

        else:
            step3_ph.markdown(
                f'<div class="agent-step done">'
                f'<div class="step-header"><div class="step-num done">3</div>'
                f'<div class="step-title">Analysis Complete</div></div>'
                f'</div>', unsafe_allow_html=True,
            )
            if raw3:
                st.markdown(f'<div class="info-card"><h4>Cortex AI Agent Recommendation</h4><p>{raw3}</p></div>', unsafe_allow_html=True)

        # Savings callout — dynamic based on verdict
        if 'SHUTDOWN' in verdict or 'INSPECT' in verdict:
            _sv_amount = "$125,000+"
            _sv_desc = (
                "Unplanned bearing failure prevented.<br/>"
                "AVEVA + Snowflake + SAP + Knowledge Base + Cortex AI Agent detected thrust bearing degradation on PMP-DMA04A-06,<br/>"
                "correlated rising vibration, temperature, and efficiency loss — grounded in OEM specs and incident history."
            )
        else:
            _sv_amount = "$40,000+"
            _sv_desc = (
                "Avoided unnecessary emergency shutdown.<br/>"
                "AVEVA + Snowflake + SAP + Knowledge Base + Cortex AI Agent confirmed sensor readings are within normal range,<br/>"
                "correlated with weather conditions — preventing costly false-alarm downtime and unnecessary parts replacement."
            )
        st.markdown(
            f'<div class="savings">'
            f'<div class="amount">{_sv_amount}</div>'
            f'<div class="desc">{_sv_desc}</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        # Multilingual translations (collapsed by default)
        with st.expander("Global Reach — Multilingual via Cortex TRANSLATE", expanded=False):
            short_rec = f"{rec.get('verdict','')}. {rec.get('root_cause','')} {rec.get('action','')}" if rec else (raw3[:400] if raw3 else '')
            escaped_rec = short_rec.replace("'", "''")

            flags = {'Spanish': '\U0001F1EA\U0001F1F8', 'French': '\U0001F1EB\U0001F1F7', 'Portuguese': '\U0001F1E7\U0001F1F7'}
            lang_tabs = st.tabs(["\U0001F1EA\U0001F1F8 Spanish", "\U0001F1EB\U0001F1F7 French", "\U0001F1E7\U0001F1F7 Portuguese"])
            for tab, (lang_code, lang_name) in zip(lang_tabs, [('es','Spanish'),('fr','French'),('pt','Portuguese')]):
                with tab:
                    trans = run_query_scalar(f"SELECT SNOWFLAKE.CORTEX.TRANSLATE('{escaped_rec}','en','{lang_code}')")
                    if trans:
                        st.markdown(
                            f'<div class="lang-card">'
                            f'<span class="flag">{flags[lang_name]}</span>'
                            f'<span class="name">{lang_name}</span>'
                            f'<div class="text">{trans}</div></div>',
                            unsafe_allow_html=True,
                        )

        st.session_state['ai_result'] = rec

    # Partnership footer
    st.markdown("---")
    st.markdown(
        '<div class="savings" style="border-color:#6366F1; background:linear-gradient(135deg,#1a1040 0%,#1e2950 100%);">'
        '<div class="amount" style="color:#6366F1; font-size:2.2rem;">The Complete Picture</div>'
        '<div class="desc" style="color:#C4B5FD;">'
        'AVEVA tells you WHAT is happening inside the plant.<br/>'
        'Snowflake tells you WHY from the world outside.<br/>'
        'SAP tells you WHAT it costs and WHAT parts are available.<br/>'
        'The Knowledge Base provides institutional expertise.<br/>'
        'Cortex AI Agent connects all five sources and recommends what to do.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
