###############################################################################
# AVEVA + Snowflake — Consolidated Demo  (AVEVA World 2026)
#
# Three hero screens in one app:
#   Tab 1  Asset Health   — 3-step agentic AI analysis (from Complete Picture)
#   Tab 2  Fleet Ops      — fleet overview + weather correlations + AI briefing
#   Tab 3  What-If Planner — interactive savings calculator with sliders
#
# Runs as Streamlit in Snowflake (SiS).
###############################################################################

import json
import time as _time

import _snowflake
import altair as alt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from snowflake.snowpark.context import get_active_session

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AVEVA + Snowflake — Consolidated Demo",
    page_icon=":material/hub:",
    layout="wide",
)

# ---------------------------------------------------------------------------
# CSS — merged styles from all three apps
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* ── Colour tokens ── */
:root {
    --teal: #00D4AA; --purple: #6366F1; --amber: #F59E0B;
    --red: #EF4444; --green: #22C55E; --orange: #FF8B00;
}

/* ── Hero banner ── */
.hero {
    background: linear-gradient(135deg, #0B1120 0%, #162033 40%, #1a1040 70%, #0B1120 100%);
    padding: 2rem 1.5rem; border-radius: 20px; margin-bottom: 1.5rem;
    border: 1px solid rgba(0,212,170,0.15); text-align: center;
    position: relative; overflow: hidden;
}
.hero::before {
    content:''; position:absolute; top:-50%; left:-50%; width:200%; height:200%;
    background: conic-gradient(from 0deg, transparent 0%, rgba(0,212,170,0.03) 25%, transparent 50%);
    animation: rotate 8s linear infinite;
}
@keyframes rotate { to { transform: rotate(360deg); } }
.hero h1 {
    background: linear-gradient(135deg, #00D4AA 0%, #6366F1 50%, #00D4AA 100%);
    background-size:200% auto; -webkit-background-clip:text;
    -webkit-text-fill-color:transparent; font-size:2.2rem; font-weight:800;
    margin:0; position:relative; z-index:1;
}
.hero .tagline { color:#94A3B8; font-size:0.95rem; margin-top:0.5rem; position:relative; z-index:1; }

/* ── Live dot ── */
@keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.4;} }
.live-dot { display:inline-block; width:8px; height:8px; background:#66BB6A;
    border-radius:50%; animation:pulse 2s ease-in-out infinite; margin-right:6px; vertical-align:middle; }

/* ── Gradient divider ── */
.gradient-divider { height:2px; background:linear-gradient(90deg,rgba(255,139,0,0.6),rgba(255,139,0,0.1),transparent); margin:1.5rem 0 1rem 0; border:none; }

/* ── Badges ── */
.badge { display:inline-block; padding:0.25rem 0.75rem; border-radius:999px; font-size:0.75rem; font-weight:700; letter-spacing:0.05em; }
.badge-aveva { background:rgba(99,102,241,0.15); color:#818CF8; border:1px solid rgba(99,102,241,0.3); }
.badge-sf { background:rgba(0,212,170,0.1); color:#00D4AA; border:1px solid rgba(0,212,170,0.3); }
.badge-cortex { background:rgba(245,158,11,0.1); color:#F59E0B; border:1px solid rgba(245,158,11,0.3); }
.badge-sap { background:rgba(56,182,255,0.1); color:#38B6FF; border:1px solid rgba(56,182,255,0.3); }
.badge-docs { background:rgba(16,185,129,0.1); color:#10B981; border:1px solid rgba(16,185,129,0.3); }

/* ── Glass metric cards ── */
.glass-card { background:rgba(30,41,59,0.7); backdrop-filter:blur(12px);
    border:1px solid rgba(0,212,170,0.12); border-radius:16px; padding:1.2rem 1.5rem; text-align:center; }
.glass-card .label { color:#94A3B8; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.3rem; }
.glass-card .value { font-size:2rem; font-weight:800; margin:0; }
.glass-card .value.teal { color:#00D4AA; }
.glass-card .value.purple { color:#6366F1; }
.glass-card .value.amber { color:#F59E0B; }
.glass-card .sub { color:#64748B; font-size:0.78rem; margin-top:0.2rem; }

/* ── Info cards ── */
.info-card { background:rgba(30,41,59,0.6); border:1px solid rgba(148,163,184,0.1);
    border-radius:12px; padding:1rem 1.2rem; margin:0.5rem 0; }
.info-card h4 { color:#E2E8F0; margin:0 0 0.4rem 0; font-size:0.9rem; }
.info-card p { color:#94A3B8; margin:0; font-size:0.85rem; line-height:1.5; }

/* ── Agent step cards ── */
.agent-step { background:rgba(30,41,59,0.6); border:1px solid rgba(148,163,184,0.1);
    border-radius:12px; padding:1rem 1.2rem; margin:0.6rem 0; transition:all 0.3s ease; }
.agent-step.running { border-color:rgba(0,212,170,0.4); animation:pulse-border 2s ease-in-out infinite; }
.agent-step.done { border-color:rgba(34,197,94,0.4); }
.agent-step .step-header { display:flex; align-items:center; gap:8px; margin-bottom:0.4rem; }
.agent-step .step-num { width:28px; height:28px; border-radius:50%; display:flex; align-items:center;
    justify-content:center; font-size:0.75rem; font-weight:800; color:#fff; }
.step-num.waiting { background:rgba(51,65,85,0.8); }
.step-num.running { background:linear-gradient(135deg,#00D4AA,#6366F1); animation:pulse-dot 1.5s ease-in-out infinite; }
.step-num.done { background:#22C55E; }
.agent-step .step-title { font-size:0.88rem; font-weight:600; color:#E2E8F0; }
.agent-step .step-detail { color:#94A3B8; font-size:0.82rem; line-height:1.5; margin-top:0.3rem; }
.agent-step .step-time { color:#64748B; font-size:0.72rem; margin-top:0.3rem; }

/* ── Document cards ── */
.doc-card { background:rgba(16,185,129,0.06); border:1px solid rgba(16,185,129,0.2);
    border-radius:8px; padding:0.6rem 0.8rem; margin:0.3rem 0; }
.doc-card .doc-title { color:#10B981; font-weight:600; font-size:0.82rem; }
.doc-card .doc-type { color:#64748B; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.05em; }
.doc-card .doc-snippet { color:#94A3B8; font-size:0.78rem; margin-top:0.2rem; line-height:1.4; }
.doc-score { display:inline-block; background:rgba(16,185,129,0.15); color:#10B981;
    font-size:0.65rem; font-weight:700; padding:0.1rem 0.4rem; border-radius:999px; margin-left:6px; }

/* ── Verdict cards ── */
.verdict { padding:1.5rem 2rem; border-radius:16px; text-align:center; margin:1rem 0; }
.verdict-continue { background:linear-gradient(135deg,rgba(34,197,94,0.1) 0%,rgba(34,197,94,0.05) 100%); border:2px solid #22C55E; }
.verdict-shutdown { background:linear-gradient(135deg,rgba(239,68,68,0.1) 0%,rgba(239,68,68,0.05) 100%); border:2px solid #EF4444; }
.verdict-inspect  { background:linear-gradient(135deg,rgba(245,158,11,0.1) 0%,rgba(245,158,11,0.05) 100%); border:2px solid #F59E0B; }
.verdict h2 { margin:0 0 0.5rem 0; font-size:1.8rem; letter-spacing:0.05em; }
.verdict-continue h2 { color:#22C55E; }
.verdict-shutdown h2 { color:#EF4444; }
.verdict-inspect h2  { color:#F59E0B; }
.verdict .conf { font-size:0.9rem; color:#94A3B8; }

/* ── Confidence gauge ── */
.gauge-track { background:rgba(51,65,85,0.5); border-radius:8px; height:10px; overflow:hidden; margin:0.5rem 0; }
.gauge-fill { height:100%; border-radius:8px; transition:width 1s ease; }
.gauge-green { background:linear-gradient(90deg,#22C55E,#4ADE80); }
.gauge-amber { background:linear-gradient(90deg,#F59E0B,#FBBF24); }
.gauge-red   { background:linear-gradient(90deg,#EF4444,#F87171); }

/* ── Savings counter ── */
.savings { background:linear-gradient(135deg,#0c4a3e 0%,#134e3f 100%);
    border:2px solid #00D4AA; border-radius:20px; padding:2rem; text-align:center; margin:1.5rem 0; }
.savings .amount { font-size:3rem; font-weight:900; color:#00D4AA; margin:0; }
.savings .desc { color:#A7F3D0; font-size:1rem; margin-top:0.5rem; }

/* ── Fleet Ops health score ── */
.health-label { font-size:0.85rem; text-transform:uppercase; letter-spacing:2px; opacity:0.7; margin-bottom:4px; }
.health-score { font-size:3.5rem; font-weight:800; line-height:1; letter-spacing:-2px; }
.health-score.good { color:#66BB6A; }
.health-score.warn { color:#FF8B00; }
.health-score.bad  { color:#FF5252; }

/* ── Glowing hero card ── */
.st-key-hero_health .stContainer {
    border:1px solid rgba(255,139,0,0.4) !important;
    box-shadow:0 0 20px rgba(255,139,0,0.15),0 0 40px rgba(255,139,0,0.05);
    border-radius:12px !important;
}

/* ── Parts table ── */
.parts-tbl { width:100%; border-collapse:separate; border-spacing:0 3px; font-size:0.78rem; }
.parts-tbl th { color:#94A3B8; font-size:0.68rem; text-transform:uppercase; letter-spacing:0.05em; padding:0.3rem 0.5rem; text-align:left; }
.parts-tbl td { padding:0.35rem 0.5rem; color:#CBD5E1; }
.stock-ok  { color:#22C55E; font-weight:700; }
.stock-low { color:#F59E0B; font-weight:700; }
.stock-out { color:#EF4444; font-weight:700; }

/* ── Animations ── */
@keyframes pulse-border { 0%,100%{border-color:rgba(0,212,170,0.15);} 50%{border-color:rgba(0,212,170,0.45);} }
@keyframes pulse-dot   { 0%,100%{opacity:1;transform:scale(1);} 50%{opacity:0.5;transform:scale(0.8);} }
@keyframes fade-in { from{opacity:0;transform:translateY(8px);} to{opacity:1;transform:translateY(0);} }
@keyframes glow-pulse { 0%,100%{box-shadow:0 0 0 rgba(0,212,170,0);} 50%{box-shadow:0 0 20px rgba(0,212,170,0.15);} }

.glass-card { transition:all 0.3s ease; animation:fade-in 0.6s ease-out; }
.glass-card:hover { transform:translateY(-2px); box-shadow:0 8px 25px rgba(0,212,170,0.08); border-color:rgba(0,212,170,0.3); }
.verdict { animation:fade-in 0.8s ease-out, glow-pulse 3s ease-in-out infinite; }
.savings { animation:fade-in 0.8s ease-out; }

/* ── Streamlit metric override ── */
[data-testid="stMetric"] {
    background:rgba(30,41,59,0.7); border:1px solid rgba(0,212,170,0.12);
    border-radius:16px; padding:1rem;
}
[data-testid="stMetricLabel"]  { color:#94A3B8 !important; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.06em; }
[data-testid="stMetricValue"]  { color:#00D4AA !important; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session & Helpers
# ---------------------------------------------------------------------------
session = get_active_session()


def run_query(sql):
    try:
        df = session.sql(sql).to_pandas()
        for col in df.columns:
            try:
                df[col] = df[col].apply(lambda x: float(x) if x is not None else None)
            except (ValueError, TypeError):
                pass
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


def _cortex_complete(prompt: str) -> str:
    escaped = prompt.replace("'", "''")
    result = session.sql(f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', '{escaped}') AS response
    """).to_pandas()
    return result.iloc[0]["RESPONSE"] if not result.empty else ""


def _fix_decimals(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if df[col].dtype == object and len(df) > 0:
            from decimal import Decimal
            sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
            if isinstance(sample, Decimal):
                df[col] = df[col].astype(float)
        elif hasattr(df[col].dtype, 'name') and 'decimal' in str(df[col].dtype).lower():
            df[col] = df[col].astype(float)
    return df


# ---------------------------------------------------------------------------
# Auto-detect AVEVA CLD database
# ---------------------------------------------------------------------------
@st.cache_resource
def _detect_cld_db():
    for candidate in ["CONNECT_AWC26", "AVEVA_CLD_DATA"]:
        try:
            session.sql(f"SHOW SCHEMAS IN DATABASE {candidate}").collect()
            return candidate
        except Exception:
            continue
    return "AVEVA_CLD_DATA"


@st.cache_resource
def _detect_weather_db():
    try:
        session.sql("SHOW SCHEMAS IN DATABASE GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI").collect()
        return (
            "GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI.PWS_BI_SAMPLE.POINT_HISTORY_DAY",
            "GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI.PWS_BI_SAMPLE.POINT_FORECAST_DAY",
        )
    except Exception:
        return (
            "AVEVA_FLEET_OPS.STREAMLIT.WEATHER_HISTORY_SAMPLE",
            "AVEVA_FLEET_OPS.STREAMLIT.WEATHER_FORECAST_SAMPLE",
        )


@st.cache_resource
def _detect_dart_db():
    try:
        session.sql("SHOW SCHEMAS IN DATABASE YES_ENERGY__SAMPLE_DATA").collect()
        return "YES_ENERGY__SAMPLE_DATA.YES_ENERGY_SAMPLE.DART_PRICES_SAMPLE"
    except Exception:
        return "AVEVA_WORLD_DEMOS.STREAMLIT_APPS.DART_PRICES_SAMPLE"


CLD_DB = _detect_cld_db()
SCHEMA = '"f6dd054e-d7b7-4b48-97f3-1b0eb2e91ab0"'
_WH, _WF = _detect_weather_db()

# Table references
TRUCK_TABLE_LIVE = f'{CLD_DB}.{SCHEMA}.mining_haul_truck_narrow_live'
TRUCK_TABLE_Q1   = f'{CLD_DB}.{SCHEMA}.mining_haul_truck_narrow_26q1'
PUMP_TABLE       = f'{CLD_DB}.{SCHEMA}.water_leakage_pump_narrow_live'
PUMP_TABLE_ENRICHED = 'AVEVA_CONNECT.PUBLIC.PUMP_DATA_ENRICHED'
WEATHER_HIST     = _WH
WEATHER_FCST     = _WF
DART_TABLE       = _detect_dart_db()

# Agent / Analyst endpoints
AGENT_API_ENDPOINT = (
    "/api/v2/databases/AVEVA_FLEET_OPS/schemas/STREAMLIT"
    "/agents/FLEET_DATA_AGENT:run"
)
SEMANTIC_VIEW_FQN = "AVEVA_FLEET_OPS.STREAMLIT.FLEET_SEMANTIC_VIEW"

# Complete Picture constants
FOCUS_PUMP = 'PMP-DMA04A-06'

@st.cache_resource
def _detect_cp_weather():
    try:
        session.sql("SHOW SCHEMAS IN DATABASE GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI").collect()
        return 'GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI.PWS_BI_SAMPLE.POINT_HISTORY_DAY'
    except Exception:
        return 'AVEVA_CONNECT.PUBLIC.WEATHER_HISTORY_SAMPLE'

CP_WEATHER_TABLE = _detect_cp_weather()

# Salesforce tables
SF_ACCOUNTS   = "AVEVA_WORLD_DEMOS.SALESFORCE.SF_ACCOUNTS"
SF_CONTRACTS  = "AVEVA_WORLD_DEMOS.SALESFORCE.SF_CONTRACTS"
SF_DELIVERIES = "AVEVA_WORLD_DEMOS.SALESFORCE.SF_DELIVERIES"
SF_CASES      = "AVEVA_WORLD_DEMOS.SALESFORCE.SF_CASES"

# Fleet Ops constants
KEY_SENSORS = [
    "Engine Fuel Rate Value l/h",
    "Shift Payload Total Value t",
    "Ground Speed Value km/h",
    "Engine Coolant Temperature Value °C",
    "Engine Oil Pressure Value psi",
    "Engine Load Value %",
]
ANOMALY_SENSORS = [
    "Engine Coolant Temperature Value °C",
    "Suspension Delta Front Cylinders Value kPa",
    "Suspension Delta Rear Cylinders Value kPa",
    "Left Exhaust Temperature Value °C",
    "Right Exhaust Temperature Value °C",
]
CHART_HEIGHT = 320
C_PRIMARY = "#FF8B00"
C_ACCENT  = "#4FC3F7"
DEFAULT_FUEL_PRICE = 1.30
DEFAULT_ELEC_RATE  = 0.13

# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADERS
# ═══════════════════════════════════════════════════════════════════════════════

# --- Tab 1: Asset Health ---

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
        FROM {CP_WEATHER_TABLE} WHERE CITY_NAME='calgary' AND DATE_VALID_STD>=DATEADD(day,-14,CURRENT_DATE())
    """)
    sap_wo = run_query(f"""
        SELECT WORK_ORDER_ID, ORDER_TYPE_DESC, PLANNED_DATE, ESTIMATED_COST_USD,
               STATUS, PRIORITY, DESCRIPTION, TECHNICIAN
        FROM AVEVA_CONNECT.PUBLIC.SAP_MAINTENANCE_ORDERS
        WHERE EQUIPMENT_ID='{FOCUS_PUMP}' AND STATUS IN ('SCHEDULED','IN_PROGRESS')
        ORDER BY PLANNED_DATE ASC LIMIT 1
    """)
    sap_parts = run_query("""
        SELECT MATERIAL_ID, DESCRIPTION, WAREHOUSE_LOCATION, QTY_ON_HAND,
               UNIT_COST_USD, LEAD_TIME_DAYS, REORDER_POINT
        FROM AVEVA_CONNECT.PUBLIC.SAP_SPARE_PARTS
        WHERE PART_CATEGORY = 'BEARINGS' AND WAREHOUSE_LOCATION = 'Calgary Main'
        ORDER BY MATERIAL_ID
    """)
    sap_hist = run_query(f"""
        SELECT COUNT(*) as TOTAL_WO,
               SUM(CASE WHEN STATUS='COMPLETED' THEN 1 ELSE 0 END) as COMPLETED,
               ROUND(SUM(ACTUAL_COST_USD),0) as TOTAL_SPENT,
               MAX(COMPLETION_DATE) as LAST_MAINT
        FROM AVEVA_CONNECT.PUBLIC.SAP_MAINTENANCE_ORDERS
        WHERE EQUIPMENT_ID='{FOCUS_PUMP}'
    """)
    return p, w, sap_wo, sap_parts, sap_hist


# --- Tab 2: Fleet Ops ---

@st.cache_data(ttl=300)
def load_fleet_latest():
    sensors_list = ",".join(f"'{s}'" for s in KEY_SENSORS)
    return session.sql(f"""
        WITH ranked AS (
            SELECT "Name" AS truck, "Field" AS sensor, "Value" AS val,
                   "Timestamp" AS ts,
                   ROW_NUMBER() OVER (PARTITION BY "Name","Field" ORDER BY "Timestamp" DESC) AS rn
            FROM {TRUCK_TABLE_LIVE}
            WHERE "Field" IN ({sensors_list})
        )
        SELECT truck, sensor, ROUND(val, 2) AS val, ts
        FROM ranked WHERE rn = 1
        ORDER BY truck, sensor
    """).to_pandas()


@st.cache_data(ttl=3600)
def load_daily_fleet_weather():
    return session.sql(f"""
        WITH truck_daily AS (
            SELECT DATE_TRUNC('day', "Timestamp") AS day,
                AVG(CASE WHEN "Field"='Engine Fuel Rate Value l/h' THEN "Value" END) AS avg_fuel,
                AVG(CASE WHEN "Field"='Shift Payload Total Value t' THEN "Value" END) AS avg_payload,
                AVG(CASE WHEN "Field"='Ground Speed Value km/h' THEN "Value" END) AS avg_speed,
                COUNT(DISTINCT "Name") AS active_trucks
            FROM {TRUCK_TABLE_LIVE}
            WHERE "Field" IN ('Engine Fuel Rate Value l/h','Shift Payload Total Value t','Ground Speed Value km/h')
            GROUP BY 1
        ),
        weather AS (
            SELECT DATE_TRUNC('day', DATE_VALID_STD) AS day,
                AVG(AVG_TEMPERATURE_AIR_2M_F) AS temp_f,
                AVG("__AVG_WIND_SPEED_10M_MPH") AS wind_mph
            FROM {WEATHER_HIST} WHERE CITY_NAME='calgary' GROUP BY 1
        )
        SELECT t.day, ROUND(w.temp_f,1) AS temp_f, ROUND(w.wind_mph,1) AS wind_mph,
               ROUND(t.avg_fuel,1) AS avg_fuel, ROUND(t.avg_payload,1) AS avg_payload,
               ROUND(t.avg_speed,1) AS avg_speed, t.active_trucks
        FROM truck_daily t JOIN weather w ON t.day=w.day ORDER BY t.day
    """).to_pandas()


@st.cache_data(ttl=300)
def load_anomalies():
    sensors_list = ",".join(f"'{s}'" for s in ANOMALY_SENSORS)
    return session.sql(f"""
        SELECT truck, sensor, val, ts, rolling_avg, rolling_std, z_score
        FROM (
            SELECT "Name" AS truck, "Field" AS sensor, "Value" AS val, "Timestamp" AS ts,
                   AVG("Value") OVER (PARTITION BY "Name","Field" ORDER BY "Timestamp"
                       ROWS BETWEEN 100 PRECEDING AND 1 PRECEDING) AS rolling_avg,
                   STDDEV("Value") OVER (PARTITION BY "Name","Field" ORDER BY "Timestamp"
                       ROWS BETWEEN 100 PRECEDING AND 1 PRECEDING) AS rolling_std,
                   CASE WHEN STDDEV("Value") OVER (PARTITION BY "Name","Field" ORDER BY "Timestamp"
                       ROWS BETWEEN 100 PRECEDING AND 1 PRECEDING) > 0 THEN
                       ("Value" - AVG("Value") OVER (PARTITION BY "Name","Field" ORDER BY "Timestamp"
                           ROWS BETWEEN 100 PRECEDING AND 1 PRECEDING))
                       / STDDEV("Value") OVER (PARTITION BY "Name","Field" ORDER BY "Timestamp"
                           ROWS BETWEEN 100 PRECEDING AND 1 PRECEDING)
                   ELSE 0 END AS z_score
            FROM {TRUCK_TABLE_LIVE} WHERE "Field" IN ({sensors_list})
        ) WHERE ABS(z_score)>3 ORDER BY ABS(z_score) DESC LIMIT 50
    """).to_pandas()


@st.cache_data(ttl=300)
def load_fleet_yesterday():
    sensors_list = ",".join(f"'{s}'" for s in KEY_SENSORS)
    return session.sql(f"""
        SELECT "Field" AS sensor, ROUND(AVG("Value"),2) AS val
        FROM {TRUCK_TABLE_LIVE}
        WHERE "Field" IN ({sensors_list})
          AND "Timestamp">=DATEADD(day,-2,CURRENT_TIMESTAMP())
          AND "Timestamp"<DATEADD(day,-1,CURRENT_TIMESTAMP())
        GROUP BY "Field"
    """).to_pandas()


@st.cache_data(ttl=1800)
def load_fleet_weather_forecast():
    return session.sql(f"""
        SELECT DATE_VALID_STD AS forecast_date,
               ROUND(AVG_TEMPERATURE_AIR_2M_F,1) AS temp_f,
               ROUND("__AVG_WIND_SPEED_10M_MPH",1) AS wind_mph,
               ROUND(PROBABILITY_OF_PRECIPITATION_PCT,0) AS precip_pct
        FROM {WEATHER_FCST} WHERE CITY_NAME='calgary' AND DATE_VALID_STD>=CURRENT_DATE()
        ORDER BY DATE_VALID_STD LIMIT 7
    """).to_pandas()


@st.cache_data(ttl=600)
def generate_fleet_health_score(_fleet_stats: str, _anomaly_count: int) -> dict:
    prompt = f"""You are a mining fleet health analyst. Based on the following fleet data, generate a fleet health assessment.

FLEET DATA:
{_fleet_stats}

ANOMALY COUNT: {_anomaly_count} sensor anomalies detected (z-score > 3)

SCORING RULES:
- 90-100: Excellent — all systems nominal
- 75-89: Good — minor issues, fleet operational
- 60-74: Fair — some trucks need attention
- Below 60: Poor — significant maintenance needed

Respond in EXACTLY this JSON format, nothing else:
{{"score": <number 0-100>, "status": "<Excellent|Good|Fair|Poor>", "summary": "<one sentence summary>", "top_risks": ["<risk1>", "<risk2>"]}}"""
    try:
        raw = _cortex_complete(prompt)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except Exception:
        pass
    return {"score": 82, "status": "Good", "summary": "Fleet operational with minor monitoring items.", "top_risks": ["Monitor coolant temps", "Check suspension balance"]}


@st.cache_data(ttl=600)
def generate_ai_briefing(_fleet_stats: str, _forecast_str: str) -> str:
    prompt = f"""You are a mining fleet operations manager writing a shift briefing for the operations room whiteboard. Be direct, specific, and concise.

FLEET STATUS (today):
{_fleet_stats}

WEATHER FORECAST (next 3 days):
{_forecast_str}

KNOWN CORRELATIONS:
- Wind speed to fuel rate: r=0.51 (higher wind = much more fuel)
- Temperature to fuel rate: r=0.49
- Temperature to payload: r=-0.31 (higher temp = lower payload)

KNOWN ANOMALIES:
- Truck 108: Coolant temperature spikes (z-score 4.04) — monitor closely
- Truck 106: Suspension pressure delta 326 kPa — inspect before heavy loads

Generate a concise shift briefing with:
1. A markdown TABLE: | Truck | Status | Fuel Adj % | Notes |
   Status: DEPLOY, LIGHT DUTY, or HOLD. Keep Notes under 8 words each.
2. One "Bottom Line" sentence with the $ impact.

Do NOT include introductions, caveats, disclaimers, or detailed methodology. Just the table and bottom line."""
    return _cortex_complete(prompt) or "AI briefing unavailable."


# --- Tab 3: What-If Planner ---

@st.cache_data(ttl=600, show_spinner="Loading truck fleet data...")
def load_truck_daily() -> pd.DataFrame:
    df = session.sql(f"""
        SELECT DATE_TRUNC('day', "Timestamp") AS day,
            SUM(CASE WHEN "Field"='Engine Fuel Rate Value l/h' THEN "Value" END) AS total_fuel_lh,
            AVG(CASE WHEN "Field"='Engine Fuel Rate Value l/h' THEN "Value" END) AS avg_fuel_lh,
            COUNT(DISTINCT "Name") AS active_trucks
        FROM {TRUCK_TABLE_Q1}
        WHERE "Field" IN ('Engine Fuel Rate Value l/h','Payload Value t','Engine Load Value %')
        GROUP BY 1 HAVING total_fuel_lh IS NOT NULL ORDER BY 1
    """).to_pandas()
    df.columns = df.columns.str.lower()
    df = _fix_decimals(df)
    df["day"] = pd.to_datetime(df["day"]).dt.tz_localize(None)
    return df


@st.cache_data(ttl=600, show_spinner="Loading pump energy data...")
def load_pump_daily() -> pd.DataFrame:
    df = session.sql(f"""
        SELECT DATE_TRUNC('day', "Timestamp") AS day,
            SUM(CASE WHEN "Field"='Energy Consumed Daily Value kWh' THEN "Value" END) AS daily_kwh,
            SUM(CASE WHEN "Field"='Energy Cost Daily Value' THEN "Value" END) AS daily_cost,
            COUNT(DISTINCT "Name") AS active_pumps
        FROM {PUMP_TABLE}
        WHERE "Field" IN ('Energy Consumed Daily Value kWh','Energy Cost Daily Value','Motor Power Value kW')
        GROUP BY 1 HAVING daily_kwh>0 ORDER BY 1
    """).to_pandas()
    df.columns = df.columns.str.lower()
    df = _fix_decimals(df)
    df["day"] = pd.to_datetime(df["day"]).dt.tz_localize(None)
    return df


@st.cache_data(ttl=1800, show_spinner="Loading weather history...")
def load_weather_history() -> pd.DataFrame:
    df = session.sql(f"""
        SELECT DATE_TRUNC('day', DATE_VALID_STD) AS day,
            AVG(AVG_TEMPERATURE_AIR_2M_F) AS temp_f,
            AVG("__AVG_WIND_SPEED_10M_MPH") AS wind_mph
        FROM {WEATHER_HIST} WHERE CITY_NAME='calgary' GROUP BY 1 ORDER BY 1
    """).to_pandas()
    df.columns = df.columns.str.lower()
    df = _fix_decimals(df)
    df["day"] = pd.to_datetime(df["day"]).dt.tz_localize(None)
    return df


@st.cache_data(ttl=600, show_spinner="Loading SLA penalties...")
def load_sf_penalties() -> pd.DataFrame:
    df = session.sql(f"""
        SELECT cs.case_date AS day, cs.category, cs.priority,
            a.account_name, cs.penalty_amount, cs.subject
        FROM {SF_CASES} cs
        JOIN {SF_ACCOUNTS} a ON cs.account_id=a.account_id
        ORDER BY cs.case_date
    """).to_pandas()
    df.columns = df.columns.str.lower()
    df = _fix_decimals(df)
    df["day"] = pd.to_datetime(df["day"]).dt.tz_localize(None)
    return df


# ═══════════════════════════════════════════════════════════════════════════════
# CHART HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def scatter_with_regression(df, x_col, y_col, x_label, y_label, r_value):
    points = (
        alt.Chart(df).mark_circle(size=50, opacity=0.6, color=C_ACCENT)
        .encode(
            x=alt.X(f"{x_col}:Q", title=x_label),
            y=alt.Y(f"{y_col}:Q", title=y_label),
            tooltip=[
                alt.Tooltip(f"{x_col}:Q", title=x_label, format=".1f"),
                alt.Tooltip(f"{y_col}:Q", title=y_label, format=".1f"),
            ],
        )
    )
    regression = points.transform_regression(x_col, y_col).mark_line(color=C_PRIMARY, strokeWidth=3)
    annotation = (
        alt.Chart(pd.DataFrame({"text": [f"r = {r_value}"]}))
        .mark_text(align="right", baseline="top", fontSize=16, fontWeight="bold",
                   color=C_PRIMARY, dx=-10, dy=10)
        .encode(x=alt.value("width"), y=alt.value(0), text="text:N")
    )
    return (points + regression + annotation).properties(height=CHART_HEIGHT).configure_view(stroke=None)


def status_icon(status):
    if status == "CRITICAL":
        return ":red[CRITICAL]"
    if status == "WARNING":
        return ":orange[WARNING]"
    return ":green[NORMAL]"


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT HELPERS — Cortex Agent / Analyst / Search
# ═══════════════════════════════════════════════════════════════════════════════

def call_fleet_agent(question: str) -> dict:
    """Call FLEET_DATA_AGENT via SiS API; fall back to Cortex Analyst."""
    request_body = {
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": question}]}
        ],
        "stream": False,
    }
    try:
        resp = _snowflake.send_snow_api_request(
            "POST", AGENT_API_ENDPOINT, {}, {}, request_body, {}, 120000,
        )
        if resp["status"] < 400:
            return json.loads(resp["content"])
        return _call_analyst_fallback(question)
    except Exception:
        return _call_analyst_fallback(question)


def _call_analyst_fallback(question: str) -> dict:
    request_body = {
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": question}]}
        ],
        "semantic_view": SEMANTIC_VIEW_FQN,
    }
    try:
        resp = _snowflake.send_snow_api_request(
            "POST", "/api/v2/cortex/analyst/message", {}, {}, request_body, {}, 60000,
        )
        if resp["status"] < 400:
            return json.loads(resp["content"])
        return {"error": f"Analyst returned status {resp['status']}"}
    except Exception as exc:
        return {"error": str(exc)}


def call_asset_agent(question: str) -> str:
    """RAG agent for asset health: Cortex Search + mistral-large2 synthesis."""
    sq_escaped = question.replace('"', '\\"').replace("'", "''")
    search_json = '{"query": "' + sq_escaped + '", "columns": ["TITLE","DOC_TYPE","SOURCE","CONTENT"], "limit": 4}'
    docs_text = ""
    try:
        search_result = run_query_scalar(
            f"SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW('AVEVA_CONNECT.PUBLIC.INDUSTRIAL_DOCS_SEARCH', '{search_json}')"
        )
        if search_result:
            parsed = json.loads(search_result)
            for i, doc in enumerate(parsed.get('results', []), 1):
                docs_text += f"\nDoc {i}: {doc.get('TITLE','')} ({doc.get('DOC_TYPE','')}, {doc.get('SOURCE','')})\n{doc.get('CONTENT','')[:800]}\n"
    except Exception:
        pass

    prompt = (
        f"You are an industrial operations AI assistant specializing in water pump maintenance and asset health. "
        f"Answer the user's question using the retrieved knowledge base documents below.\n\n"
        f"KNOWLEDGE BASE DOCUMENTS:\n{docs_text}\n\n"
        f"CURRENT CONTEXT: Pump PMP-DMA04A-06 is under monitoring. Thrust bearing temperature is being tracked "
        f"against AVEVA predictive model. 25 pumps across 4 DMAs in Calgary.\n\n"
        f"USER QUESTION: {question}\n\n"
        f"Provide a thorough answer with:\n"
        f"- Specific values, thresholds, and ranges from the documents\n"
        f"- Citations to document titles (e.g., 'per SKF Technical Bulletin...')\n"
        f"- Practical operational recommendations\n"
        f"- Any relevant warning signs or escalation criteria\n"
        f"Format with clear paragraphs. Use bullet points for lists."
    )
    return _cortex_complete(prompt) or "I couldn't generate an answer. Please try rephrasing."


def call_savings_agent(question: str) -> str:
    """Cost optimization agent: uses Cortex AI with Salesforce + weather + energy context."""
    context = (
        "DATA AVAILABLE:\n"
        "- Salesforce: SF_ACCOUNTS (8 mining customers), SF_CONTRACTS (15 contracts with SLAs), "
        "SF_DELIVERIES (1350 truck deliveries with tonnage, delays, fuel cost), SF_CASES (45 SLA cases/penalties)\n"
        "- WeatherSource: Daily Calgary weather (temperature, wind, precipitation)\n"
        "- Yes Energy: Hourly ERCOT electricity prices (DALMP, RTLMP)\n"
        "- AVEVA: Mining truck fleet (10 trucks, fuel rate, payload, speed) + Water pumps (25 pumps, energy consumption)\n\n"
        "KEY INSIGHTS:\n"
        "- Wind speed explains 51% of fuel cost variation\n"
        "- Temperature to fuel rate: r=0.49\n"
        "- High-wind days increase fuel costs 30-40%\n"
        "- Weather-driven SLA penalties account for ~$45K/quarter\n"
    )
    prompt = (
        f"You are a cost optimization analyst for mining and water utility operations. "
        f"Answer the user's question using the data context below.\n\n"
        f"{context}\n"
        f"USER QUESTION: {question}\n\n"
        f"Provide a concise, data-driven answer with specific numbers where possible."
    )
    return _cortex_complete(prompt) or "I couldn't generate an answer. Please try rephrasing."


def display_agent_response(response: dict):
    """Render Cortex Agent response: text, SQL + results, suggestions."""
    if "error" in response:
        st.error(f"Agent error: {response['error']}")
        return
    content_items = []
    if "message" in response:
        content_items = response["message"].get("content", [])
    elif "content" in response:
        content_items = response["content"]
    for item in content_items:
        item_type = item.get("type", "")
        if item_type == "text":
            st.markdown(item["text"])
        elif item_type == "tool_results":
            for tr in item.get("tool_results", [item]):
                inner = tr.get("content", [])
                for inner_item in inner:
                    _render_content_item(inner_item)
        elif item_type == "sql":
            _render_sql_item(item)
        elif item_type == "suggestions":
            _render_suggestions(item)
        else:
            if "text" in item:
                st.markdown(item["text"])
            elif "json" in item:
                _render_json_payload(item["json"])


def _render_json_payload(payload):
    if isinstance(payload, dict):
        if "sql" in payload:
            _render_sql_item(payload)
        elif "text" in payload:
            st.markdown(payload["text"])
        elif "statement" in payload:
            _render_sql_item({"statement": payload["statement"]})
    elif isinstance(payload, str):
        st.markdown(payload)


def _render_content_item(item):
    item_type = item.get("type", "")
    if item_type == "text":
        st.markdown(item["text"])
    elif item_type == "sql":
        _render_sql_item(item)
    elif item_type == "suggestions":
        _render_suggestions(item)
    elif item_type == "json":
        _render_json_payload(item.get("json", item))
    elif "text" in item:
        st.markdown(item["text"])


def _render_sql_item(item):
    sql_stmt = item.get("statement") or item.get("sql", "")
    if not sql_stmt:
        return
    with st.expander("Generated SQL", expanded=False):
        st.code(sql_stmt, language="sql")
    try:
        result_df = session.sql(sql_stmt).to_pandas()
        st.dataframe(result_df, use_container_width=True)
        if len(result_df) > 1:
            numeric_cols = result_df.select_dtypes(include=["number"]).columns
            if len(numeric_cols) >= 1 and len(result_df.columns) >= 2:
                st.bar_chart(result_df.set_index(result_df.columns[0])[numeric_cols])
    except Exception as exc:
        st.error(f"Query error: {exc}")


def _render_suggestions(item):
    suggestions = item.get("suggestions", [])
    if suggestions:
        st.markdown("**Suggested follow-ups:**")
        for sug in suggestions:
            st.markdown(f"- {sug}")


# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="hero">
    <h1>AVEVA + Snowflake — The Power of Together</h1>
    <p class="tagline">
        <span class="badge badge-aveva">AVEVA CLD</span> &nbsp;
        <span class="badge badge-sf">Snowflake</span> &nbsp;
        <span class="badge badge-sap">SAP ERP</span> &nbsp;
        <span class="badge badge-docs">Knowledge Base</span> &nbsp;
        <span class="badge badge-cortex">Cortex AI</span>
    </p>
    <div style="margin-top:0.6rem;">
        <span class="live-dot"></span>
        <span style="color:#22C55E; font-size:0.8rem; font-weight:600;">LIVE</span>
        <span style="color:#64748B; font-size:0.75rem;"> &nbsp; 13M+ sensor readings &nbsp;|&nbsp; 6 data sources &nbsp;|&nbsp; Agentic AI</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# DATA FOUNDATION — AVEVA CLD Integration
# ═══════════════════════════════════════════════════════════════════════════════

with st.expander(":material/database: **Data Foundation — AVEVA Connect CLD Integration**", expanded=False):
    st.markdown("""
    <div style="background:linear-gradient(135deg, rgba(255,139,0,0.06), rgba(99,102,241,0.06));
                border:1px solid rgba(255,139,0,0.15); border-radius:12px; padding:1.2rem 1.5rem; margin-bottom:1rem;">
        <div style="font-size:0.85rem; color:#94a3b8; margin-bottom:0.5rem;">HOW THE DATA GOT HERE</div>
        <div style="font-size:1.1rem; font-weight:700; color:#e2e8f0; margin-bottom:0.5rem;">
            Iceberg REST Catalog &nbsp;→&nbsp; Catalog-Linked Database &nbsp;→&nbsp; Zero Data Movement
        </div>
        <div style="font-size:0.82rem; color:#94a3b8;">
            AVEVA Connect publishes operational data as Iceberg tables. Snowflake reads them in-place via
            <strong style="color:#FF8B00;">vended credentials</strong> — no ETL, no copies, no pipelines to maintain.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # -- Two-statement setup SQL
    st.markdown("##### The Integration — 2 SQL Statements")
    st.code("""-- Statement 1: Register AVEVA's Iceberg REST catalog
CREATE CATALOG INTEGRATION AVEVA_CLD_CATALOG
  CATALOG_SOURCE = ICEBERG_REST
  TABLE_FORMAT   = ICEBERG
  CATALOG_URI    = 'https://<aveva-connect-endpoint>/iceberg'
  ACCESS_DELEGATION_MODE = VENDED_CREDENTIALS
  ENABLED = TRUE;

-- Statement 2: Create the catalog-linked database
CREATE DATABASE AVEVA_CLD_DATA
  FROM CATALOG INTEGRATION AVEVA_CLD_CATALOG
  AUTO_REFRESH = TRUE;

-- That's it. Tables appear automatically.""", language="sql")

    # -- Live stats from the CLD
    st.markdown("##### What's Synced — Live from AVEVA Connect")

    @st.cache_data(ttl=300)
    def _cld_stats():
        rows = session.sql(f"""
            SELECT 'Mining Trucks (Live)' AS dataset,
                   COUNT(*) AS row_count,
                   COUNT(DISTINCT "Name") AS assets,
                   COUNT(DISTINCT "Field") AS sensors,
                   MIN("Timestamp")::STRING AS earliest,
                   MAX("Timestamp")::STRING AS latest
              FROM {TRUCK_TABLE_LIVE}
            UNION ALL
            SELECT 'Mining Trucks (Q1 Batch)',
                   COUNT(*), COUNT(DISTINCT "Name"), COUNT(DISTINCT "Field"),
                   MIN("Timestamp")::STRING, MAX("Timestamp")::STRING
              FROM {TRUCK_TABLE_Q1}
            UNION ALL
            SELECT 'Water Pumps (Live)',
                   COUNT(*), COUNT(DISTINCT "Name"), COUNT(DISTINCT "Field"),
                   MIN("Timestamp")::STRING, MAX("Timestamp")::STRING
              FROM {PUMP_TABLE}
        """).collect()
        return rows
    try:
        cld_rows = _cld_stats()
        total_readings = sum(r['ROW_COUNT'] for r in cld_rows)
        cld_c1, cld_c2, cld_c3 = st.columns(3)
        for col, row in zip([cld_c1, cld_c2, cld_c3], cld_rows):
            with col:
                st.metric(row['DATASET'], f"{row['ROW_COUNT']:,.0f} readings")
                st.caption(f"{row['ASSETS']} assets  |  {row['SENSORS']} sensors")
        st.markdown(f"""
        <div style="background:#0f172a; border:1px solid rgba(148,163,184,0.1); border-radius:8px;
                    padding:0.8rem 1rem; margin-top:0.5rem;">
            <span style="font-size:0.9rem; font-weight:700; color:#22C55E;">{total_readings:,.0f}</span>
            <span style="font-size:0.82rem; color:#94a3b8;"> total readings synced via Iceberg REST Catalog — zero data movement</span>
        </div>
        """, unsafe_allow_html=True)
    except Exception:
        st.info("CLD stats unavailable — AVEVA CLD database not connected on this account.")

    # -- Data shape
    st.markdown("##### Data Shape — Narrow Format")
    st.markdown("""Every AVEVA CLD table follows the same 4-column schema.
    Narrow format means one row per sensor reading — flexible and JOIN-friendly.""")
    st.code("""  Timestamp              │ Name           │ Field                              │ Value
  ───────────────────────┼────────────────┼────────────────────────────────────┼──────
  2026-04-28 14:30:00    │ Truck 108      │ Engine Coolant Temperature °C      │ 92.4
  2026-04-28 14:30:00    │ PMP-DMA04A-06  │ Thrust Bearing Temperature DE °C   │ 68.7""")

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### :material/hub: AVEVA World 2026")
    st.markdown(
        '<span class="badge badge-aveva">AVEVA CLD</span> '
        '<span class="badge badge-sf">WeatherSource</span> '
        '<span class="badge badge-sap">SAP ERP</span><br/>'
        '<span class="badge badge-docs">28 Docs</span> '
        '<span class="badge badge-cortex">Cortex AI</span>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.html('<div style="margin-bottom:8px"><span class="live-dot"></span><span style="font-size:0.85rem;opacity:0.8">Live data feed</span></div>')
    st.caption(
        "10 mining trucks (live + Q1 2026)\n"
        "25 water pumps across 4 DMAs\n"
        "WeatherSource + Yes Energy\n"
        "Salesforce CRM (contracts & SLAs)\n"
        "28 industrial docs via Cortex Search"
    )
    st.markdown("---")
    fuel_price = st.number_input(
        "Diesel price ($/litre)", min_value=0.50, max_value=3.00,
        value=DEFAULT_FUEL_PRICE, step=0.05, format="%.2f",
    )
    st.markdown("---")
    if st.button(":material/restart_alt: Clear cache", use_container_width=True):
        st.cache_data.clear()
        for _k in ["ai_analysis_result", "fleet_health_cache", "fleet_briefing_cache"]:
            st.session_state.pop(_k, None)
        st.rerun()
    st.markdown("---")
    st.caption(":material/smart_toy: Powered by **Snowflake Cortex AI**")

# ═══════════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════════

tab_health, tab_fleet, tab_savings = st.tabs([
    ":material/health_and_safety: Asset Health",
    ":material/local_shipping: Fleet Operations",
    ":material/savings: What-If Planner",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ASSET HEALTH  (3-step agentic AI)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_health:
    st.markdown("### :material/health_and_safety: AI Agent — Pump Health Diagnosis")
    st.caption(
        "3-step agentic analysis: Structured Data (AVEVA + Weather + SAP) "
        "→ Knowledge Retrieval (Cortex Search) → Synthesis & Recommendation"
    )

    pump_df, weather_df, sap_wo_df, sap_parts_df, sap_hist_df = load_ai_ctx()
    p = pump_df.iloc[0] if not pump_df.empty else {}
    w = weather_df.iloc[0] if not weather_df.empty else {}
    sap_wo = sap_wo_df.iloc[0] if not sap_wo_df.empty else {}
    sap_hist = sap_hist_df.iloc[0] if not sap_hist_df.empty else {}

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

    # Context panels
    with st.expander("Data Context — AVEVA + WeatherSource + SAP", expanded=True):
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
                f'Temp-Vibration: <strong>r = 0.31</strong></p></div>',
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
                    stock_cls = 'stock-out' if qty == 0 else ('stock-low' if qty <= reorder else 'stock-ok')
                    desc_short = str(sp.get('DESCRIPTION', ''))[:28]
                    parts_html += (
                        f'<tr><td>{desc_short}</td>'
                        f'<td class="{stock_cls}">{qty}</td>'
                        f'<td>{int(sp.get("LEAD_TIME_DAYS",0))}d</td>'
                        f'<td>${float(sp.get("UNIT_COST_USD",0)):,.0f}</td></tr>'
                    )
                parts_html += '</tbody></table>'
                st.markdown(parts_html, unsafe_allow_html=True)

    # ── 3-STEP AGENTIC AI ANALYSIS (cached in session_state) ──────────────────
    if "ai_analysis_result" not in st.session_state:
        # ── STEP 1: Structured Data Analysis ──
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

        step1_ph.markdown(
            f'<div class="agent-step done">'
            f'<div class="step-header"><div class="step-num done">1</div>'
            f'<div class="step-title">Structured Data Analysis — Complete</div></div>'
            f'<div class="step-detail">{diagnosis} &nbsp; <strong>({conf_prelim:.0%} confidence)</strong></div>'
            f'<div class="step-time">{step1_elapsed:.1f}s — Cortex COMPLETE (mistral-large2)</div>'
            f'</div>', unsafe_allow_html=True,
        )

        # ── STEP 2: Knowledge Retrieval (Cortex Search) ──
        step2_start = _time.time()
        step2_ph = st.empty()
        step2_ph.markdown(
            '<div class="agent-step running">'
            '<div class="step-header"><div class="step-num running">2</div>'
            '<div class="step-title">Retrieving Knowledge — Cortex Search over 28 Industrial Documents</div></div>'
            '<div class="step-detail">Searching OEM bulletins, maintenance SOPs, incident reports, industry standards, and regulatory guidelines...</div>'
            '</div>', unsafe_allow_html=True,
        )

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

        seen_titles = set()
        unique_docs = []
        for d in sorted(all_docs, key=lambda x: x['relevance'], reverse=True):
            if d['title'] not in seen_titles:
                seen_titles.add(d['title'])
                unique_docs.append(d)
        top_docs = unique_docs[:4]
        step2_elapsed = _time.time() - step2_start

        # ── STEP 3: Synthesis & Recommendation ──
        step3_start = _time.time()
        step3_ph = st.empty()
        step3_ph.markdown(
            '<div class="agent-step running">'
            '<div class="step-header"><div class="step-num running">3</div>'
            '<div class="step-title">Synthesizing Final Recommendation — Grounding in Knowledge Base</div></div>'
            '<div class="step-detail">Combining structured analysis + retrieved documents + SAP context into a grounded, citable recommendation...</div>'
            '</div>', unsafe_allow_html=True,
        )

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
        total_elapsed = step1_elapsed + step2_elapsed + step3_elapsed

        rec = None
        if raw3:
            try:
                s3 = raw3.find('{')
                e3 = raw3.rfind('}') + 1
                if s3 >= 0 and e3 > s3:
                    rec = json.loads(raw3[s3:e3])
            except Exception:
                pass

        # Cache everything in session_state
        st.session_state.ai_analysis_result = {
            "diagnosis": diagnosis,
            "conf_prelim": conf_prelim,
            "step1_elapsed": step1_elapsed,
            "top_docs": top_docs,
            "step2_elapsed": step2_elapsed,
            "rec": rec,
            "raw3": raw3,
            "step3_elapsed": step3_elapsed,
            "total_elapsed": total_elapsed,
        }
    # ── END OF ANALYSIS — render from cache ─────────────────────────────────
    _cached = st.session_state.ai_analysis_result
    diagnosis = _cached["diagnosis"]
    conf_prelim = _cached["conf_prelim"]
    step1_elapsed = _cached["step1_elapsed"]
    top_docs = _cached["top_docs"]
    step2_elapsed = _cached["step2_elapsed"]
    rec = _cached["rec"]
    raw3 = _cached["raw3"]
    step3_elapsed = _cached["step3_elapsed"]
    total_elapsed = _cached["total_elapsed"]

    # Render Step 1
    st.markdown(
        f'<div class="agent-step done">'
        f'<div class="step-header"><div class="step-num done">1</div>'
        f'<div class="step-title">Structured Data Analysis — Complete</div></div>'
        f'<div class="step-detail">{diagnosis} &nbsp; <strong>({conf_prelim:.0%} confidence)</strong></div>'
        f'<div class="step-time">{step1_elapsed:.1f}s — Cortex COMPLETE (mistral-large2)</div>'
        f'</div>', unsafe_allow_html=True,
    )

    # Render Step 2
    st.markdown(
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
                f'</div>', unsafe_allow_html=True,
            )

    # Render Step 3 + Verdict
    if rec and 'verdict' in rec:
        verdict = rec.get('verdict', 'CONTINUE OPERATIONS').upper()
        confidence = float(rec.get('confidence', 0.85))
        root_cause = rec.get('root_cause', '')
        evidence = rec.get('evidence', [])
        action = rec.get('action', '')
        citations = rec.get('citations', [])

        st.markdown(
            f'<div class="agent-step done">'
            f'<div class="step-header"><div class="step-num done">3</div>'
            f'<div class="step-title">Synthesis Complete — Recommendation Ready</div></div>'
            f'<div class="step-detail"><strong>Verdict:</strong> {verdict} ({confidence:.0%} confidence)<br/>'
            f'<strong>Root Cause:</strong> {root_cause}</div>'
            f'<div class="step-time">{step3_elapsed:.1f}s — Cortex COMPLETE (mistral-large2) | Total: {total_elapsed:.1f}s</div>'
            f'</div>', unsafe_allow_html=True,
        )

        # Verdict card
        if 'CONTINUE' in verdict:
            v_cls, gauge_cls = 'verdict-continue', 'gauge-green'
        elif 'SHUTDOWN' in verdict:
            v_cls, gauge_cls = 'verdict-shutdown', 'gauge-red'
        else:
            v_cls, gauge_cls = 'verdict-inspect', 'gauge-amber'

        st.markdown(
            f'<div class="verdict {v_cls}">'
            f'<h2>{verdict}</h2>'
            f'<div class="conf">Confidence: {confidence:.0%} &nbsp;|&nbsp; 3-Step Agentic Analysis &nbsp;|&nbsp; {len(top_docs)} Documents Referenced</div>'
            f'<div class="gauge-track"><div class="gauge-fill {gauge_cls}" style="width:{confidence*100:.0f}%"></div></div>'
            f'</div>', unsafe_allow_html=True,
        )

        # Executive Summary
        sap_action = rec.get('sap_action', '')
        border_color = "#F59E0B" if "INSPECT" in verdict else ("#EF4444" if "SHUTDOWN" in verdict else "#22C55E")
        summary_html = (
            f'<div class="info-card" style="border-left:4px solid {border_color};">'
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

        with st.expander("View Evidence & Citations", expanded=False):
            for i, ev in enumerate(evidence, 1):
                st.markdown(f"**{i}.** {ev}")
            if citations:
                st.markdown("---")
                st.markdown("**Sources Cited:**")
                for c_title in citations:
                    st.markdown(f"- {c_title}")

        # Savings callout — dynamic based on verdict
        if 'SHUTDOWN' in verdict or 'INSPECT' in verdict:
            savings_amount = "$125,000+"
            savings_desc = (
                "Unplanned bearing failure prevented.<br/>"
                "AVEVA + Snowflake + SAP + Knowledge Base + Cortex AI Agent detected thrust bearing degradation,<br/>"
                "correlated rising vibration, temperature, and efficiency loss — grounded in OEM specs and incident history."
            )
        else:
            savings_amount = "$40,000+"
            savings_desc = (
                "Avoided unnecessary emergency shutdown.<br/>"
                "AVEVA + Snowflake + SAP + Knowledge Base + Cortex AI Agent confirmed sensor readings are within normal range,<br/>"
                "correlated with weather conditions — preventing costly false-alarm downtime and unnecessary parts replacement."
            )
        st.markdown(
            f'<div class="savings">'
            f'<div class="amount">{savings_amount}</div>'
            f'<div class="desc">{savings_desc}</div>'
            '</div>', unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="agent-step done">'
            f'<div class="step-header"><div class="step-num done">3</div>'
            f'<div class="step-title">Analysis Complete</div></div></div>',
            unsafe_allow_html=True,
        )
        if raw3:
            st.markdown(f'<div class="info-card"><h4>AI Recommendation</h4><p>{raw3}</p></div>', unsafe_allow_html=True)

    # ── Ask the Agent — Asset Health ──
    st.html('<div class="gradient-divider"></div>')
    st.markdown("#### :material/chat: Ask the Agent — Asset Health")
    st.caption("Ask follow-up questions about pump health, maintenance, or industrial knowledge base — powered by Cortex Search + Cortex AI")

    ASSET_SUGGESTED = [
        "What are the OEM-recommended bearing temperature limits?",
        "What maintenance SOPs apply to thrust bearing degradation?",
        "How does weather affect pump vibration and efficiency?",
    ]

    if "asset_agent_messages" not in st.session_state:
        st.session_state.asset_agent_messages = []

    sq_cols = st.columns(3)
    for i, q in enumerate(ASSET_SUGGESTED):
        if sq_cols[i].button(q, key=f"asset_sq_{i}", use_container_width=True):
            st.session_state.asset_agent_messages.append({"role": "user", "content": q})

    for msg in st.session_state.asset_agent_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt_asset := st.chat_input("Ask about pump health, bearings, maintenance...", key="asset_chat"):
        st.session_state.asset_agent_messages.append({"role": "user", "content": prompt_asset})
        with st.chat_message("user"):
            st.markdown(prompt_asset)

    if (
        st.session_state.asset_agent_messages
        and st.session_state.asset_agent_messages[-1]["role"] == "user"
    ):
        user_q = st.session_state.asset_agent_messages[-1]["content"]
        with st.chat_message("assistant"):
            with st.spinner("Searching knowledge base..."):
                answer = call_asset_agent(user_q)
            st.markdown(answer)
        st.session_state.asset_agent_messages.append({"role": "assistant", "content": answer})


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — FLEET OPERATIONS  (overview + weather correlations + AI briefing)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_fleet:
    # Hero header with AI health score
    hero_left, hero_right = st.columns([3, 1])
    with hero_left:
        st.markdown("### :material/local_shipping: Weather-aware fleet operations")
        st.markdown(
            "**Wind speed explains 51% of fuel cost variation.** "
            "With weather forecasts from Snowflake Marketplace, the fleet manager "
            "knows which trucks to deploy tomorrow — before the shift starts."
        )

    fleet_df = load_fleet_latest()
    fleet_df.columns = fleet_df.columns.str.lower()
    anomaly_df = load_anomalies()
    anomaly_df.columns = anomaly_df.columns.str.lower()

    with hero_right:
        with st.container(border=True, key="hero_health"):
            if not fleet_df.empty:
                _pivot_tmp = fleet_df.pivot(index="truck", columns="sensor", values="val").reset_index()
                _stats_summary = f"Trucks: {_pivot_tmp['truck'].nunique()}, " + ", ".join(
                    f"Avg {col}: {_pivot_tmp[col].mean():.1f}"
                    for col in _pivot_tmp.columns if col != "truck" and _pivot_tmp[col].dtype in ["float64", "int64"]
                )
            else:
                _stats_summary = "No data"

            _anom_count = len(anomaly_df)
            health = generate_fleet_health_score(_stats_summary, _anom_count)
            score = health.get("score", 82)
            status_word = health.get("status", "Good")
            score_class = "good" if score >= 80 else ("warn" if score >= 60 else "bad")

            st.html(f'<div class="health-label">Fleet health</div>')
            st.html(f'<div class="health-score {score_class}">{score}</div>')
            st.caption(f"**{status_word}** — {health.get('summary', '')}")

    st.html('<div class="gradient-divider"></div>')

    # Fleet overview
    st.markdown("#### :material/dashboard: Fleet overview")

    yesterday_df = load_fleet_yesterday()
    yesterday_df.columns = yesterday_df.columns.str.lower()
    yesterday_map = dict(zip(yesterday_df["sensor"], yesterday_df["val"])) if not yesterday_df.empty else {}

    if not fleet_df.empty:
        pivot = fleet_df.pivot(index="truck", columns="sensor", values="val").reset_index()
        pivot.columns.name = None

        col_map = {
            "Engine Fuel Rate Value l/h": "Fuel (l/h)",
            "Shift Payload Total Value t": "Payload (t)",
            "Ground Speed Value km/h": "Speed (km/h)",
            "Engine Coolant Temperature Value °C": "Coolant (°C)",
            "Engine Oil Pressure Value psi": "Oil Pres. (psi)",
            "Engine Load Value %": "Load (%)",
        }
        pivot = pivot.rename(columns=col_map)
        coolant_col = "Coolant (°C)"
        if coolant_col in pivot.columns:
            pivot["Status"] = pivot[coolant_col].apply(
                lambda x: "CRITICAL" if x > 95 else ("WARNING" if x > 92 else "NORMAL")
            )
        else:
            pivot["Status"] = "NORMAL"

        # KPI cards
        fuel_col, payload_col, speed_col = "Fuel (l/h)", "Payload (t)", "Speed (km/h)"
        today_fuel = pivot[fuel_col].mean() if fuel_col in pivot.columns else None
        today_payload = pivot[payload_col].mean() if payload_col in pivot.columns else None
        today_speed = pivot[speed_col].mean() if speed_col in pivot.columns else None
        yest_fuel = yesterday_map.get("Engine Fuel Rate Value l/h")
        yest_payload = yesterday_map.get("Shift Payload Total Value t")
        yest_speed = yesterday_map.get("Ground Speed Value km/h")

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            with st.container(border=True):
                st.caption(":material/directions_bus: Active trucks")
                st.markdown(f"### {len(pivot)}")
        with k2:
            with st.container(border=True):
                st.caption(":material/local_gas_station: Avg fuel rate")
                if today_fuel is not None:
                    delta_str = ""
                    if yest_fuel:
                        delta_pct = ((today_fuel - yest_fuel) / yest_fuel) * 100
                        delta_str = f"  `{'↑' if delta_pct > 0 else '↓'}{abs(delta_pct):.1f}% vs yesterday`"
                    st.markdown(f"### {today_fuel:.0f} l/h{delta_str}")
                else:
                    st.markdown("### N/A")
        with k3:
            with st.container(border=True):
                st.caption(":material/package_2: Avg payload")
                if today_payload is not None:
                    delta_str = ""
                    if yest_payload:
                        delta_pct = ((today_payload - yest_payload) / yest_payload) * 100
                        delta_str = f"  `{'↑' if delta_pct > 0 else '↓'}{abs(delta_pct):.1f}% vs yesterday`"
                    st.markdown(f"### {today_payload:.0f} t{delta_str}")
                else:
                    st.markdown("### N/A")
        with k4:
            with st.container(border=True):
                st.caption(":material/speed: Avg speed")
                if today_speed is not None:
                    delta_str = ""
                    if yest_speed:
                        delta_pct = ((today_speed - yest_speed) / yest_speed) * 100
                        delta_str = f"  `{'↑' if delta_pct > 0 else '↓'}{abs(delta_pct):.1f}% vs yesterday`"
                    st.markdown(f"### {today_speed:.1f} km/h{delta_str}")
                else:
                    st.markdown("### N/A")

        st.dataframe(
            pivot,
            column_config={
                "truck": st.column_config.TextColumn("Truck"),
                "Fuel (l/h)": st.column_config.NumberColumn("Fuel (l/h)", format="%.1f"),
                "Payload (t)": st.column_config.NumberColumn("Payload (t)", format="%.1f"),
                "Speed (km/h)": st.column_config.NumberColumn("Speed (km/h)", format="%.1f"),
                "Coolant (°C)": st.column_config.NumberColumn("Coolant (°C)", format="%.1f"),
                "Oil Pres. (psi)": st.column_config.NumberColumn("Oil (psi)", format="%.1f"),
                "Load (%)": st.column_config.NumberColumn("Load (%)", format="%.1f"),
                "Status": st.column_config.TextColumn("Status"),
            },
            use_container_width=True,
        )
    else:
        st.warning("No fleet data available.")

    # Weather correlations
    st.html('<div class="gradient-divider"></div>')
    st.markdown("#### :material/scatter_plot: Weather correlations")
    st.caption("Daily fleet averages vs Calgary weather — wind and temperature drive fuel costs")

    daily_df = load_daily_fleet_weather()
    daily_df.columns = daily_df.columns.str.lower()

    if not daily_df.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            with st.container(border=True):
                st.markdown("**:material/air: Wind vs fuel rate**")
                st.altair_chart(
                    scatter_with_regression(daily_df, "wind_mph", "avg_fuel", "Wind (mph)", "Fuel (l/h)", 0.51),
                    use_container_width=True,
                )
        with col2:
            with st.container(border=True):
                st.markdown("**:material/thermostat: Temp vs fuel rate**")
                st.altair_chart(
                    scatter_with_regression(daily_df, "temp_f", "avg_fuel", "Temp (°F)", "Fuel (l/h)", 0.49),
                    use_container_width=True,
                )
        with col3:
            with st.container(border=True):
                st.markdown("**:material/thermostat: Temp vs payload**")
                st.altair_chart(
                    scatter_with_regression(daily_df, "temp_f", "avg_payload", "Temp (°F)", "Payload (t)", -0.31),
                    use_container_width=True,
                )

        # Daily trend
        with st.container(border=True):
            st.markdown("**:material/trending_up: Daily fleet trend**")
            trend_melted = daily_df[["day", "avg_fuel", "avg_speed"]].melt(
                id_vars=["day"], value_vars=["avg_fuel", "avg_speed"],
                var_name="metric", value_name="value",
            )
            label_map = {"avg_fuel": "Fuel rate (l/h)", "avg_speed": "Speed (km/h)"}
            trend_melted["metric"] = trend_melted["metric"].map(label_map)

            trend_chart = (
                alt.Chart(trend_melted).mark_line(strokeWidth=2)
                .encode(
                    x=alt.X("day:T", title=None),
                    y=alt.Y("value:Q", title=None, scale=alt.Scale(zero=False)),
                    color=alt.Color("metric:N", title=None,
                                    scale=alt.Scale(range=[C_PRIMARY, C_ACCENT]),
                                    legend=alt.Legend(orient="bottom")),
                    tooltip=[
                        alt.Tooltip("day:T", title="Date", format="%b %d"),
                        alt.Tooltip("metric:N", title="Metric"),
                        alt.Tooltip("value:Q", title="Value", format=".1f"),
                    ],
                ).properties(height=250)
            )
            st.altair_chart(trend_chart, use_container_width=True)
    else:
        st.warning("No daily fleet + weather data available.")

    # AI operations briefing
    st.html('<div class="gradient-divider"></div>')
    st.markdown("#### :material/smart_toy: AI operations briefing")
    st.caption("Cortex AI generates a weather-aware shift deployment plan — live on every page load")

    with st.container(border=True):
        forecast_df = load_fleet_weather_forecast()
        forecast_df.columns = forecast_df.columns.str.lower()

        if not daily_df.empty and not forecast_df.empty:
            latest = daily_df.iloc[-1]
            fleet_stats = (
                f"Avg fuel: {latest.get('avg_fuel', 'N/A')} l/h | "
                f"Avg payload: {latest.get('avg_payload', 'N/A')} t | "
                f"Avg speed: {latest.get('avg_speed', 'N/A')} km/h | "
                f"Active trucks: {latest.get('active_trucks', 'N/A')}"
            )
            forecast_str = forecast_df.head(3).to_string(index=False)

            with st.spinner("Cortex AI is analyzing fleet + weather data..."):
                briefing = generate_ai_briefing(fleet_stats, forecast_str)
            st.markdown(briefing)
        else:
            st.warning("Insufficient data for AI briefing.")

    # ── Talk to Your Data — Fleet Operations ──
    st.html('<div class="gradient-divider"></div>')
    st.markdown("#### :material/chat: Talk to Your Data — Fleet Operations")
    st.caption("Ask questions about the fleet in plain English — powered by Cortex Agent with text-to-SQL")

    FLEET_SUGGESTED = [
        "What is the average fuel rate per truck?",
        "Which truck had the highest coolant temperature?",
        "Show me the average speed by day of week",
        "Compare engine load across all trucks",
        "Which hours of the day have the highest fuel consumption?",
    ]

    if "fleet_agent_messages" not in st.session_state:
        st.session_state.fleet_agent_messages = []

    fq_row1 = st.columns(3)
    fq_row2 = st.columns(3)
    fq_grid = fq_row1 + fq_row2
    for i, q in enumerate(FLEET_SUGGESTED):
        if i < len(fq_grid) and fq_grid[i].button(q, key=f"fleet_sq_{i}", use_container_width=True):
            st.session_state.fleet_agent_messages.append({"role": "user", "content": q})

    for msg in st.session_state.fleet_agent_messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant" and isinstance(msg["content"], dict):
                display_agent_response(msg["content"])
            else:
                st.markdown(msg["content"])

    if prompt_fleet := st.chat_input("Ask about the fleet data...", key="fleet_chat"):
        st.session_state.fleet_agent_messages.append({"role": "user", "content": prompt_fleet})
        with st.chat_message("user"):
            st.markdown(prompt_fleet)

    if (
        st.session_state.fleet_agent_messages
        and st.session_state.fleet_agent_messages[-1]["role"] == "user"
    ):
        user_q = st.session_state.fleet_agent_messages[-1]["content"]
        with st.chat_message("assistant"):
            with st.spinner("Querying fleet data..."):
                agent_resp = call_fleet_agent(user_q)
            display_agent_response(agent_resp)
        st.session_state.fleet_agent_messages.append(
            {"role": "assistant", "content": agent_resp}
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — WHAT-IF PLANNER  (savings calculator)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_savings:
    st.markdown("### :material/savings: Interactive savings calculator")
    st.caption(
        "Adjust operational thresholds to see projected quarterly savings. "
        "The model calculates cost avoidance from weather-aware scheduling "
        "and SLA penalty prevention."
    )

    trucks = load_truck_daily()
    pumps = load_pump_daily()
    weather = load_weather_history()
    sf_penalties_data = load_sf_penalties()

    trucks["fuel_cost"] = trucks["total_fuel_lh"] * fuel_price

    # Controls
    col_ctrl1, col_ctrl2 = st.columns(2)
    with col_ctrl1:
        wind_threshold = st.slider(
            "Max wind speed for full operations (mph)",
            min_value=3.0, max_value=20.0, value=10.0, step=0.5,
        )
        temp_low_threshold = st.slider(
            "Min temperature for full operations (°F)",
            min_value=0.0, max_value=50.0, value=20.0, step=1.0,
        )
    with col_ctrl2:
        truck_reduction = st.slider(
            "Truck fleet reduction on bad weather days (%)",
            min_value=0, max_value=80, value=40, step=5,
        )
        pump_reduction = st.slider(
            "Pump power reduction on high-cost days (%)",
            min_value=0, max_value=50, value=20, step=5,
        )
        sla_prevention = st.slider(
            "Weather-penalty prevention rate (%)",
            min_value=0, max_value=100, value=70, step=5,
            help="% of weather-driven SLA penalties avoided via proactive scheduling",
        )

    # Calculate savings
    tw = pd.merge(trucks, weather, on="day", how="inner")
    pw = pd.merge(pumps, weather, on="day", how="inner")

    if not tw.empty:
        bad_truck_days = tw[(tw["wind_mph"] > wind_threshold) | (tw["temp_f"] < temp_low_threshold)]
        truck_baseline = tw["fuel_cost"].sum()
        truck_savings = bad_truck_days["fuel_cost"].sum() * (truck_reduction / 100)
        truck_bad_day_count = len(bad_truck_days)
    else:
        truck_baseline = truck_savings = 0
        truck_bad_day_count = 0

    if not pw.empty:
        pump_median = pw["daily_cost"].median()
        high_cost_pump_days = pw[pw["daily_cost"] > pump_median * 1.2]
        pump_baseline = pw["daily_cost"].sum()
        pump_savings = high_cost_pump_days["daily_cost"].sum() * (pump_reduction / 100)
        pump_high_days = len(high_cost_pump_days)
    else:
        pump_baseline = pump_savings = 0
        pump_high_days = 0

    weather_sla_penalties = sf_penalties_data.loc[
        sf_penalties_data["category"] == "WEATHER_DELAY", "penalty_amount"
    ].sum()
    sla_savings = weather_sla_penalties * (sla_prevention / 100)

    total_savings = truck_savings + pump_savings + sla_savings
    total_baseline = truck_baseline + pump_baseline + weather_sla_penalties
    savings_pct = total_savings / total_baseline * 100 if total_baseline > 0 else 0

    data_days = max(len(tw), len(pw), 1)
    quarterly_factor = 90 / data_days
    quarterly_truck_savings = truck_savings * quarterly_factor
    quarterly_pump_savings = pump_savings * quarterly_factor
    quarterly_sla_savings = sla_savings  # already quarterly
    quarterly_savings = quarterly_truck_savings + quarterly_pump_savings + quarterly_sla_savings

    # Results
    st.markdown("---")
    with st.container(horizontal=True):
        st.metric(
            "Projected quarterly savings",
            f"${quarterly_savings:,.0f}",
            f"{savings_pct:.1f}% reduction",
            border=True,
        )
        st.metric(
            "Truck fuel savings",
            f"${quarterly_truck_savings:,.0f}",
            f"{truck_bad_day_count} high-weather days",
            border=True,
        )
        st.metric(
            "Pump energy savings",
            f"${quarterly_pump_savings:,.0f}",
            f"{pump_high_days} high-cost days",
            border=True,
        )
        st.metric(
            "SLA penalty avoidance",
            f"${quarterly_sla_savings:,.0f}",
            f"{sla_prevention}% prevention rate",
            border=True,
        )

    # Before/after comparison
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**Before: baseline operations**")
            baseline_total = truck_baseline * quarterly_factor + pump_baseline * quarterly_factor + weather_sla_penalties
            st.metric("Quarterly cost", f"${baseline_total:,.0f}")
            st.caption(
                f"Trucks: ${truck_baseline * quarterly_factor:,.0f} | "
                f"Pumps: ${pump_baseline * quarterly_factor:,.0f} | "
                f"SLA penalties: ${weather_sla_penalties:,.0f}"
            )
    with col2:
        with st.container(border=True):
            st.markdown("**After: weather-optimized**")
            optimized = baseline_total - quarterly_savings
            st.metric("Quarterly cost", f"${optimized:,.0f}")
            st.caption(
                f"Trucks: ${(truck_baseline - truck_savings) * quarterly_factor:,.0f} | "
                f"Pumps: ${(pump_baseline - pump_savings) * quarterly_factor:,.0f} | "
                f"SLA penalties: ${weather_sla_penalties - sla_savings:,.0f}"
            )

    # Savings breakdown chart
    with st.container(border=True):
        st.markdown("**Savings breakdown**")
        breakdown = pd.DataFrame({
            "source": [
                "Truck fuel (weather delays)",
                "Pump energy (load shifting)",
                "SLA penalty avoidance",
            ],
            "savings": [
                quarterly_truck_savings,
                quarterly_pump_savings,
                quarterly_sla_savings,
            ],
        })
        st.altair_chart(
            alt.Chart(breakdown)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("source:N", title=None),
                y=alt.Y("savings:Q", title="Quarterly savings ($)"),
                color=alt.Color("source:N",
                    scale=alt.Scale(range=["#FF6B35", "#4ECDC4", "#7C3AED"]),
                    legend=None),
                tooltip=[
                    alt.Tooltip("source:N", title="Source"),
                    alt.Tooltip("savings:Q", format="$,.0f", title="Savings"),
                ],
            ).properties(height=250),
            use_container_width=True,
        )

    st.markdown(
        f"> *\"AVEVA tracks what you consume. Snowflake Marketplace tells you what it costs "
        f"in the market and what weather is doing to drive it. Salesforce shows the customer impact. Together: "
        f"**${quarterly_savings:,.0f} quarterly savings identified** — including **${quarterly_sla_savings:,.0f}** "
        f"in avoidable SLA penalties.\"*"
    )

    # ── Ask the Agent — Cost Optimization ──
    st.html('<div class="gradient-divider"></div>')
    st.markdown("#### :material/chat: Ask the Agent — Cost Optimization")
    st.caption("Ask questions about cost savings, SLA penalties, weather impact, and energy pricing — powered by Cortex AI")

    SAVINGS_SUGGESTED = [
        "What are the main drivers of SLA penalties?",
        "How much could we save by avoiding high-wind day operations?",
        "What is the relationship between weather and delivery delays?",
    ]

    if "savings_agent_messages" not in st.session_state:
        st.session_state.savings_agent_messages = []

    sq_cols3 = st.columns(3)
    for i, q in enumerate(SAVINGS_SUGGESTED):
        if sq_cols3[i].button(q, key=f"savings_sq_{i}", use_container_width=True):
            st.session_state.savings_agent_messages.append({"role": "user", "content": q})

    for msg in st.session_state.savings_agent_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt_savings := st.chat_input("Ask about cost optimization, SLAs, weather impact...", key="savings_chat"):
        st.session_state.savings_agent_messages.append({"role": "user", "content": prompt_savings})
        with st.chat_message("user"):
            st.markdown(prompt_savings)

    if (
        st.session_state.savings_agent_messages
        and st.session_state.savings_agent_messages[-1]["role"] == "user"
    ):
        user_q = st.session_state.savings_agent_messages[-1]["content"]
        with st.chat_message("assistant"):
            with st.spinner("Analyzing cost data..."):
                answer = call_savings_agent(user_q)
            st.markdown(answer)
        st.session_state.savings_agent_messages.append({"role": "assistant", "content": answer})

# ═══════════════════════════════════════════════════════════════════════════════
# Footer
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.caption(
    ":material/factory: AVEVA Connect (Iceberg REST Catalog)  |  "
    ":material/cloud: Snowflake Marketplace (WeatherSource + Yes Energy)  |  "
    ":material/handshake: Salesforce CRM  |  "
    ":material/smart_toy: Snowflake Cortex AI"
)
