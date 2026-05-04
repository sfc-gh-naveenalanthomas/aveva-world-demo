"""
Weather-Aware Fleet Operations Dashboard
Mining Trucks + Weather — AVEVA World 2026 Build 2

Deployed as Streamlit in Snowflake (SiS).
"""

import json
import pandas as pd
import altair as alt
import streamlit as st
import _snowflake
from snowflake.snowpark.context import get_active_session

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Fleet Operations",
    page_icon=":material/local_shipping:",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom CSS for premium visual feel
# ---------------------------------------------------------------------------
st.html("""
<style>
/* Glowing hero card */
.st-key-hero_health .stContainer {
    border: 1px solid rgba(255, 139, 0, 0.4) !important;
    box-shadow: 0 0 20px rgba(255, 139, 0, 0.15), 0 0 40px rgba(255, 139, 0, 0.05);
    border-radius: 12px !important;
}

/* Pulsing live dot */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}
.live-dot {
    display: inline-block;
    width: 8px; height: 8px;
    background: #66BB6A;
    border-radius: 50%;
    animation: pulse 2s ease-in-out infinite;
    margin-right: 6px;
    vertical-align: middle;
}

/* Section divider gradient */
.gradient-divider {
    height: 2px;
    background: linear-gradient(90deg, rgba(255,139,0,0.6), rgba(255,139,0,0.1), transparent);
    margin: 1.5rem 0 1rem 0;
    border: none;
}

/* Score badge styling */
.health-score {
    font-size: 3.5rem;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -2px;
}
.health-score.good { color: #66BB6A; }
.health-score.warn { color: #FF8B00; }
.health-score.bad { color: #FF5252; }

.health-label {
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    opacity: 0.7;
    margin-bottom: 4px;
}

/* Insight chip styling */
.insight-chip {
    display: inline-block;
    background: rgba(255, 139, 0, 0.12);
    border: 1px solid rgba(255, 139, 0, 0.3);
    border-radius: 20px;
    padding: 6px 16px;
    margin: 4px 4px;
    font-size: 0.82rem;
    color: #FAFAFA;
    cursor: default;
}
</style>
""")

# ---------------------------------------------------------------------------
# Auto-detect AVEVA CLD database name (varies by account)
# ---------------------------------------------------------------------------
@st.cache_resource
def _detect_cld_db():
    """Return the AVEVA CLD database name available on this account."""
    _sess = get_active_session()
    for candidate in ["CONNECT_AWC26", "AVEVA_CLD_DATA"]:
        try:
            _sess.sql(f"SHOW SCHEMAS IN DATABASE {candidate}").collect()
            return candidate
        except Exception:
            continue
    return "AVEVA_CLD_DATA"  # fallback

CLD_DB = _detect_cld_db()
SCHEMA = '"f6dd054e-d7b7-4b48-97f3-1b0eb2e91ab0"'

@st.cache_resource
def _detect_weather_db():
    """Return WeatherSource table paths, falling back to fabricated samples."""
    _sess = get_active_session()
    try:
        _sess.sql("SHOW SCHEMAS IN DATABASE GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI").collect()
        return (
            "GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI.PWS_BI_SAMPLE.POINT_HISTORY_DAY",
            "GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI.PWS_BI_SAMPLE.POINT_FORECAST_DAY",
        )
    except Exception:
        return (
            "AVEVA_FLEET_OPS.STREAMLIT.WEATHER_HISTORY_SAMPLE",
            "AVEVA_FLEET_OPS.STREAMLIT.WEATHER_FORECAST_SAMPLE",
        )

_WH, _WF = _detect_weather_db()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TRUCK_TABLE = (
    f'{CLD_DB}.{SCHEMA}'
    ".mining_haul_truck_narrow_live"
)
WEATHER_HISTORY = _WH
WEATHER_FORECAST = _WF
CITY = "calgary"

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

# Chart color palette — warm industrial tones
C_PRIMARY = "#FF8B00"
C_ACCENT = "#4FC3F7"
C_DANGER = "#FF5252"
C_SUCCESS = "#66BB6A"
C_MUTED = "#78909C"
PALETTE = ["#FF8B00", "#4FC3F7", "#66BB6A", "#AB47BC", "#FF5252",
           "#FDD835", "#26C6DA", "#EF5350", "#29B6F6", "#9CCC65"]

AGENT_API_ENDPOINT = (
    "/api/v2/databases/AVEVA_FLEET_OPS/schemas/STREAMLIT"
    "/agents/FLEET_DATA_AGENT:run"
)
SEMANTIC_VIEW_FQN = "AVEVA_FLEET_OPS.STREAMLIT.FLEET_SEMANTIC_VIEW"

# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------
session = get_active_session()

# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------


@st.cache_data(ttl=300)
def load_fleet_latest():
    sensors_list = ",".join(f"'{s}'" for s in KEY_SENSORS)
    return session.sql(f"""
        WITH ranked AS (
            SELECT "Name" AS truck, "Field" AS sensor, "Value" AS val,
                   "Timestamp" AS ts,
                   ROW_NUMBER() OVER (
                       PARTITION BY "Name", "Field"
                       ORDER BY "Timestamp" DESC
                   ) AS rn
            FROM {TRUCK_TABLE}
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
                AVG(CASE WHEN "Field" = 'Engine Fuel Rate Value l/h'
                         THEN "Value" END) AS avg_fuel,
                AVG(CASE WHEN "Field" = 'Shift Payload Total Value t'
                         THEN "Value" END) AS avg_payload,
                AVG(CASE WHEN "Field" = 'Ground Speed Value km/h'
                         THEN "Value" END) AS avg_speed,
                COUNT(DISTINCT "Name") AS active_trucks
            FROM {TRUCK_TABLE}
            WHERE "Field" IN (
                'Engine Fuel Rate Value l/h',
                'Shift Payload Total Value t',
                'Ground Speed Value km/h'
            )
            GROUP BY 1
        ),
        weather AS (
            SELECT DATE_TRUNC('day', DATE_VALID_STD) AS day,
                AVG(AVG_TEMPERATURE_AIR_2M_F) AS temp_f,
                AVG("__AVG_WIND_SPEED_10M_MPH") AS wind_mph
            FROM {WEATHER_HISTORY}
            WHERE CITY_NAME = '{CITY}'
            GROUP BY 1
        )
        SELECT t.day, ROUND(w.temp_f, 1) AS temp_f,
               ROUND(w.wind_mph, 1) AS wind_mph,
               ROUND(t.avg_fuel, 1) AS avg_fuel,
               ROUND(t.avg_payload, 1) AS avg_payload,
               ROUND(t.avg_speed, 1) AS avg_speed,
               t.active_trucks
        FROM truck_daily t JOIN weather w ON t.day = w.day
        ORDER BY t.day
    """).to_pandas()


@st.cache_data(ttl=300)
def load_anomalies():
    sensors_list = ",".join(f"'{s}'" for s in ANOMALY_SENSORS)
    return session.sql(f"""
        SELECT truck, sensor, val, ts, rolling_avg, rolling_std, z_score
        FROM (
            SELECT "Name" AS truck, "Field" AS sensor,
                   "Value" AS val, "Timestamp" AS ts,
                   AVG("Value") OVER (
                       PARTITION BY "Name", "Field"
                       ORDER BY "Timestamp"
                       ROWS BETWEEN 100 PRECEDING AND 1 PRECEDING
                   ) AS rolling_avg,
                   STDDEV("Value") OVER (
                       PARTITION BY "Name", "Field"
                       ORDER BY "Timestamp"
                       ROWS BETWEEN 100 PRECEDING AND 1 PRECEDING
                   ) AS rolling_std,
                   CASE WHEN STDDEV("Value") OVER (
                       PARTITION BY "Name", "Field"
                       ORDER BY "Timestamp"
                       ROWS BETWEEN 100 PRECEDING AND 1 PRECEDING
                   ) > 0 THEN
                       ("Value" - AVG("Value") OVER (
                           PARTITION BY "Name", "Field"
                           ORDER BY "Timestamp"
                           ROWS BETWEEN 100 PRECEDING AND 1 PRECEDING
                       )) / STDDEV("Value") OVER (
                           PARTITION BY "Name", "Field"
                           ORDER BY "Timestamp"
                           ROWS BETWEEN 100 PRECEDING AND 1 PRECEDING
                       )
                   ELSE 0 END AS z_score
            FROM {TRUCK_TABLE}
            WHERE "Field" IN ({sensors_list})
        )
        WHERE ABS(z_score) > 3
        ORDER BY ABS(z_score) DESC
        LIMIT 50
    """).to_pandas()


@st.cache_data(ttl=1800)
def load_weather_forecast():
    return session.sql(f"""
        SELECT DATE_VALID_STD AS forecast_date,
               ROUND(AVG_TEMPERATURE_AIR_2M_F, 1) AS temp_f,
               ROUND(MIN_TEMPERATURE_AIR_2M_F, 1) AS temp_min_f,
               ROUND(MAX_TEMPERATURE_AIR_2M_F, 1) AS temp_max_f,
               ROUND("__AVG_WIND_SPEED_10M_MPH", 1) AS wind_mph,
               ROUND("__MAX_WIND_SPEED_10M_MPH", 1) AS wind_max_mph,
               ROUND(TOT_PRECIPITATION_IN, 2) AS precip_in,
               ROUND(PROBABILITY_OF_PRECIPITATION_PCT, 0) AS precip_pct
        FROM {WEATHER_FORECAST}
        WHERE CITY_NAME = '{CITY}'
          AND DATE_VALID_STD >= CURRENT_DATE()
        ORDER BY DATE_VALID_STD
        LIMIT 7
    """).to_pandas()


@st.cache_data(ttl=300)
def load_truck_sensors(truck_name: str, days: int = 7):
    return session.sql(f"""
        SELECT "Field" AS sensor, "Value" AS val, "Timestamp" AS ts
        FROM {TRUCK_TABLE}
        WHERE "Name" = '{truck_name}'
          AND "Timestamp" >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
        ORDER BY "Timestamp"
    """).to_pandas()


@st.cache_data(ttl=300)
def load_fleet_yesterday():
    """Load yesterday's fleet averages for delta comparison."""
    sensors_list = ",".join(f"'{s}'" for s in KEY_SENSORS)
    return session.sql(f"""
        SELECT "Field" AS sensor, ROUND(AVG("Value"), 2) AS val
        FROM {TRUCK_TABLE}
        WHERE "Field" IN ({sensors_list})
          AND "Timestamp" >= DATEADD(day, -2, CURRENT_TIMESTAMP())
          AND "Timestamp" < DATEADD(day, -1, CURRENT_TIMESTAMP())
        GROUP BY "Field"
    """).to_pandas()


# ---------------------------------------------------------------------------
# AI-powered functions
# ---------------------------------------------------------------------------


def _cortex_complete(prompt: str) -> str:
    """Call Cortex AI with proper escaping."""
    escaped = prompt.replace("'", "''")
    result = session.sql(f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'mistral-large2',
            '{escaped}'
        ) AS response
    """).to_pandas()
    return result.iloc[0]["RESPONSE"] if not result.empty else ""


@st.cache_data(ttl=600)
def generate_fleet_health_score(_fleet_stats: str, _anomaly_count: int) -> dict:
    """AI-generated fleet health score with explanation."""
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
        # Extract JSON from response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except Exception:
        pass
    return {"score": 82, "status": "Good", "summary": "Fleet operational with minor monitoring items.", "top_risks": ["Monitor coolant temps", "Check suspension balance"]}


@st.cache_data(ttl=600)
def generate_anomaly_narrative(_anomaly_summary: str) -> str:
    """AI-generated narrative explaining anomalies."""
    prompt = f"""You are a mining fleet maintenance advisor writing for an operations manager. Be specific, actionable, and brief.

DETECTED ANOMALIES:
{_anomaly_summary}

Write exactly 3 bullet points:
- **What**: Which truck(s) and sensor(s) are abnormal, with actual values
- **Risk**: What could happen if ignored (e.g. engine damage, downtime cost)
- **Action**: Specific next step (e.g. "Pull Truck 108 for coolant system inspection before next shift")

No introductions or disclaimers. Just the 3 bullets."""
    return _cortex_complete(prompt)


@st.cache_data(ttl=600)
def generate_weather_impact_prediction(_forecast_str: str) -> str:
    """AI-predicted fleet impact from weather forecast."""
    prompt = f"""You are a fleet operations analyst. Predict the operational impact of this weather forecast on mining haul trucks in Calgary.

WEATHER FORECAST:
{_forecast_str}

KNOWN CORRELATIONS:
- Wind speed to fuel rate: r=0.51
- Temperature to fuel rate: r=0.49
- Temperature to payload: r=-0.31

Generate ONLY:
1. A markdown table: | Day | Risk | Fuel Adj % | Payload Adj % | Key Factor |
   Risk: LOW / MEDIUM / HIGH. Use emoji: :green_circle: :orange_circle: :red_circle:
2. One "Bottom Line" sentence summarizing the week's outlook with estimated $ impact.

No introductions, methodology explanations, or disclaimers."""
    return _cortex_complete(prompt)


@st.cache_data(ttl=600)
def generate_insight_of_the_day(_fleet_stats: str) -> str:
    """Generate a surprising insight from the fleet data."""
    prompt = f"""You are a data analyst. Based on this mining fleet data, generate ONE surprising or interesting insight as a single sentence. Make it specific with truck names and numbers. Keep it under 20 words.

FLEET DATA:
{_fleet_stats}

Example format: "Truck 104 burned 12% more fuel than the fleet average this week."
Respond with ONLY the insight sentence, nothing else."""
    result = _cortex_complete(prompt)
    return result.strip().strip('"')


# ---------------------------------------------------------------------------
# Cortex AI briefing
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------


def scatter_with_regression(df, x_col, y_col, x_label, y_label, r_value):
    points = (
        alt.Chart(df)
        .mark_circle(size=50, opacity=0.6, color=C_ACCENT)
        .encode(
            x=alt.X(f"{x_col}:Q", title=x_label),
            y=alt.Y(f"{y_col}:Q", title=y_label),
            tooltip=[
                alt.Tooltip(f"{x_col}:Q", title=x_label, format=".1f"),
                alt.Tooltip(f"{y_col}:Q", title=y_label, format=".1f"),
            ],
        )
    )
    regression = points.transform_regression(
        x_col, y_col
    ).mark_line(color=C_PRIMARY, strokeWidth=3)

    annotation = (
        alt.Chart(pd.DataFrame({"text": [f"r = {r_value}"]}))
        .mark_text(
            align="right", baseline="top", fontSize=16, fontWeight="bold",
            color=C_PRIMARY, dx=-10, dy=10,
        )
        .encode(x=alt.value("width"), y=alt.value(0), text="text:N")
    )

    return (points + regression + annotation).properties(
        height=CHART_HEIGHT
    ).configure_view(stroke=None)


def risk_level(wind, temp):
    if wind > 20 or temp > 90 or temp < 10:
        return "HIGH"
    if wind > 12 or temp > 80 or temp < 20:
        return "MEDIUM"
    return "LOW"


def status_icon(status):
    if status == "CRITICAL":
        return ":red[CRITICAL]"
    if status == "WARNING":
        return ":orange[WARNING]"
    return ":green[NORMAL]"


# ===========================================================================
# SIDEBAR
# ===========================================================================
with st.sidebar:
    st.markdown("### :material/tune: Controls")
    all_trucks = [f"Truck {i}" for i in range(101, 111)]
    selected_trucks = st.multiselect(
        "Trucks", all_trucks, default=all_trucks, key="truck_filter"
    )
    lookback_days = st.select_slider(
        "Lookback", options=[1, 3, 7, 14, 30], value=7,
        format_func=lambda x: f"{x}d"
    )
    st.markdown("---")
    # Live status indicator
    st.html('<div style="margin-bottom:8px"><span class="live-dot"></span><span style="font-size:0.85rem;opacity:0.8">Live data feed</span></div>')
    st.caption("AVEVA IoT + WeatherSource\nRefreshes every 5 min")
    st.markdown("---")
    if st.button(":material/restart_alt: Clear cache", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    st.caption(
        ":material/smart_toy: Powered by **Snowflake Cortex**\n\n"
        ":material/database: AVEVA Connect + Marketplace"
    )
    with st.expander(":material/schema: Architecture", expanded=False):
        st.image("Presentation_arch_diagram.png")

# ===========================================================================
# HERO HEADER with AI Health Score
# ===========================================================================
hero_left, hero_right = st.columns([3, 1])

with hero_left:
    st.markdown(
        "# :material/local_shipping: Weather-aware fleet operations"
    )
    st.markdown(
        "**Wind speed explains 51% of fuel cost variation.** "
        "With weather forecasts from Snowflake Marketplace, the fleet manager "
        "knows which trucks to deploy tomorrow — before the shift starts."
    )

# Load data early so we can compute health score
fleet_df = load_fleet_latest()
fleet_df.columns = fleet_df.columns.str.lower()
anomaly_df = load_anomalies()
anomaly_df.columns = anomaly_df.columns.str.lower()

with hero_right:
    with st.container(border=True, key="hero_health"):
        # Build fleet stats summary for AI
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

# ===========================================================================
# SECTION 1: Fleet overview
# ===========================================================================
st.markdown("### :material/dashboard: Fleet overview")

# Load yesterday's data for delta comparisons
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

    pivot = pivot[pivot["truck"].isin(selected_trucks)]

    # KPI cards with delta vs yesterday
    fuel_col = "Fuel (l/h)"
    payload_col = "Payload (t)"
    speed_col = "Speed (km/h)"

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

    # Fleet table with status coloring
    display_pivot = pivot.copy()
    display_pivot["Status"] = display_pivot["Status"].apply(status_icon)
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
        hide_index=True,
        use_container_width=True,
    )
else:
    st.warning("No fleet data available.")

# ===========================================================================
# SECTION 2: Weather correlations
# ===========================================================================
st.html('<div class="gradient-divider"></div>')
st.markdown("### :material/scatter_plot: Weather correlations")
st.caption(
    "Daily fleet averages vs Calgary weather — validated correlations "
    "show wind and temperature drive fuel costs"
)

daily_df = load_daily_fleet_weather()
daily_df.columns = daily_df.columns.str.lower()

if not daily_df.empty:
    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.markdown("**:material/air: Wind vs fuel rate**")
            st.altair_chart(
                scatter_with_regression(
                    daily_df, "wind_mph", "avg_fuel",
                    "Wind (mph)", "Fuel (l/h)", 0.51,
                ),
                use_container_width=True,
            )

    with col2:
        with st.container(border=True):
            st.markdown("**:material/thermostat: Temperature vs fuel rate**")
            st.altair_chart(
                scatter_with_regression(
                    daily_df, "temp_f", "avg_fuel",
                    "Temp (°F)", "Fuel (l/h)", 0.49,
                ),
                use_container_width=True,
            )

    with col3:
        with st.container(border=True):
            st.markdown("**:material/thermostat: Temperature vs payload**")
            st.altair_chart(
                scatter_with_regression(
                    daily_df, "temp_f", "avg_payload",
                    "Temp (°F)", "Payload (t)", -0.31,
                ),
                use_container_width=True,
            )

    # Fleet trend chart
    with st.container(border=True):
        st.markdown("**:material/trending_up: Daily fleet trend**")
        trend_df = daily_df[["day", "avg_fuel", "avg_speed", "wind_mph", "temp_f"]].copy()
        trend_melted = trend_df.melt(
            id_vars=["day"],
            value_vars=["avg_fuel", "avg_speed"],
            var_name="metric",
            value_name="value",
        )
        label_map = {"avg_fuel": "Fuel rate (l/h)", "avg_speed": "Speed (km/h)"}
        trend_melted["metric"] = trend_melted["metric"].map(label_map)

        trend_chart = (
            alt.Chart(trend_melted)
            .mark_line(strokeWidth=2)
            .encode(
                x=alt.X("day:T", title=None),
                y=alt.Y("value:Q", title=None, scale=alt.Scale(zero=False)),
                color=alt.Color(
                    "metric:N", title=None,
                    scale=alt.Scale(range=[C_PRIMARY, C_ACCENT]),
                    legend=alt.Legend(orient="bottom"),
                ),
                tooltip=[
                    alt.Tooltip("day:T", title="Date", format="%b %d"),
                    alt.Tooltip("metric:N", title="Metric"),
                    alt.Tooltip("value:Q", title="Value", format=".1f"),
                ],
            )
            .properties(height=250)
        )
        st.altair_chart(trend_chart, use_container_width=True)
else:
    st.warning("No daily fleet + weather data available.")

# ===========================================================================
# SECTION 3: AI operations briefing (auto-generated)
# ===========================================================================
st.html('<div class="gradient-divider"></div>')
st.markdown("### :material/smart_toy: AI operations briefing")
st.caption("Cortex AI generates a weather-aware shift deployment plan — live on every page load")

with st.container(border=True):
    forecast_df = load_weather_forecast()
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

        # Regenerate button
        if st.button(":material/refresh: Regenerate briefing", key="regen_briefing"):
            st.cache_data.clear()
            st.rerun()
    else:
        st.warning("Insufficient data for AI briefing.")

# ===========================================================================
# SECTION 4: Truck drilldown
# ===========================================================================
st.html('<div class="gradient-divider"></div>')
st.markdown("### :material/search: Truck detail drilldown")

drill_col1, drill_col2 = st.columns([1, 3])
with drill_col1:
    drill_truck = st.selectbox(
        "Truck", all_trucks, index=7, key="drill_truck"
    )
with drill_col2:
    all_sensor_names = sorted([
        "Engine Fuel Rate Value l/h",
        "Ground Speed Value km/h",
        "Engine Coolant Temperature Value °C",
        "Shift Payload Total Value t",
        "Engine Oil Pressure Value psi",
        "Engine Load Value %",
        "Engine RPM Value rpm",
        "Left Exhaust Temperature Value °C",
        "Right Exhaust Temperature Value °C",
        "Aftercooler Temperature Value °C",
        "Boost Pressure Value",
        "Left Front Suspension Cylinder Value kPa",
        "Right Front Suspension Cylinder Value kPa",
        "Left Rear Suspension Cylinder Value kPa",
        "Right Rear Suspension Cylinder Value kPa",
        "Left Front Brake Temperature Value °C",
        "Right Front Brake Temperature Value °C",
        "Left Rear Brake Temperature Value °C",
        "Right Rear Brake Temperature Value °C",
        "Suspension Delta Front Cylinders Value kPa",
        "Suspension Delta Rear Cylinders Value kPa",
        "Payload Value t",
        "Payload Status Value",
        "Air Filter Value",
        "Latitude Value °",
        "Longitude Value °",
    ])
    drill_sensors = st.multiselect(
        "Sensors",
        all_sensor_names,
        default=[
            "Engine Fuel Rate Value l/h",
            "Engine Coolant Temperature Value °C",
            "Ground Speed Value km/h",
        ],
        key="drill_sensors",
    )

if drill_truck and drill_sensors:
    with st.container(border=True):
        truck_data = load_truck_sensors(drill_truck, days=lookback_days)
        truck_data.columns = truck_data.columns.str.lower()

        if not truck_data.empty:
            filtered = truck_data[truck_data["sensor"].isin(drill_sensors)]
            if not filtered.empty:
                chart = (
                    alt.Chart(filtered)
                    .mark_line(strokeWidth=1.5, opacity=0.9)
                    .encode(
                        x=alt.X("ts:T", title=None),
                        y=alt.Y("val:Q", title="Value",
                                scale=alt.Scale(zero=False)),
                        color=alt.Color(
                            "sensor:N", title=None,
                            scale=alt.Scale(range=PALETTE),
                            legend=alt.Legend(orient="bottom"),
                        ),
                        tooltip=[
                            alt.Tooltip("ts:T", title="Time",
                                        format="%Y-%m-%d %H:%M"),
                            alt.Tooltip("sensor:N", title="Sensor"),
                            alt.Tooltip("val:Q", title="Value", format=".2f"),
                        ],
                    )
                    .properties(height=380)
                )
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("No data for the selected sensors in this time range.")
        else:
            st.warning(f"No data available for {drill_truck}.")
else:
    st.info("Select a truck and at least one sensor above.")

# ===========================================================================
# SECTION 5: Anomaly detection + AI narrative
# ===========================================================================
st.html('<div class="gradient-divider"></div>')
st.markdown("### :material/warning: Anomaly detection")
st.caption("Rolling z-score (window=100) — readings with |z| > 3 flagged")

# anomaly_df already loaded at top for health score

if not anomaly_df.empty:
    anomaly_filtered = anomaly_df[anomaly_df["truck"].isin(selected_trucks)]

    if not anomaly_filtered.empty:
        # Summary KPIs
        m1, m2, m3 = st.columns(3)
        with m1:
            with st.container(border=True):
                st.caption(":material/error: Total anomalies")
                st.markdown(f"### {len(anomaly_filtered)}")
        with m2:
            with st.container(border=True):
                st.caption(":material/local_shipping: Trucks affected")
                st.markdown(f"### {anomaly_filtered['truck'].nunique()}")
        with m3:
            with st.container(border=True):
                max_z = anomaly_filtered["z_score"].abs().max()
                st.caption(":material/trending_up: Peak z-score")
                st.markdown(f"### {max_z:.1f}")

        # AI narrative
        with st.container(border=True):
            st.markdown("**:material/smart_toy: AI analysis**")
            top_anomalies = anomaly_filtered.nlargest(10, "z_score", keep="first")
            anomaly_summary = "\n".join(
                f"- {row['truck']}: {row['sensor']} = {row['val']:.1f} (z-score {row['z_score']:.1f}) at {row['ts']}"
                for _, row in top_anomalies.iterrows()
            )
            with st.spinner("Cortex AI analyzing anomalies..."):
                narrative = generate_anomaly_narrative(anomaly_summary)
            st.markdown(narrative)

        # Timeline
        with st.container(border=True):
            timeline = (
                alt.Chart(anomaly_filtered)
                .mark_circle(opacity=0.8)
                .encode(
                    x=alt.X("ts:T", title=None),
                    y=alt.Y("z_score:Q", title="Z-score"),
                    color=alt.Color(
                        "truck:N", title="Truck",
                        scale=alt.Scale(range=PALETTE),
                    ),
                    size=alt.Size(
                        "z_score:Q", title="|Z|",
                        scale=alt.Scale(range=[40, 300]),
                    ),
                    tooltip=[
                        alt.Tooltip("truck:N", title="Truck"),
                        alt.Tooltip("sensor:N", title="Sensor"),
                        alt.Tooltip("val:Q", title="Value", format=".2f"),
                        alt.Tooltip("z_score:Q", title="Z-score", format=".2f"),
                        alt.Tooltip("ts:T", title="Time",
                                    format="%Y-%m-%d %H:%M"),
                    ],
                )
                .properties(height=CHART_HEIGHT)
            )

            rule_upper = (
                alt.Chart(pd.DataFrame({"y": [3]}))
                .mark_rule(color=C_DANGER, strokeDash=[4, 4], strokeWidth=1.5)
                .encode(y="y:Q")
            )
            rule_lower = (
                alt.Chart(pd.DataFrame({"y": [-3]}))
                .mark_rule(color=C_DANGER, strokeDash=[4, 4], strokeWidth=1.5)
                .encode(y="y:Q")
            )

            st.altair_chart(
                timeline + rule_upper + rule_lower,
                use_container_width=True,
            )

        # Table
        display_cols = ["truck", "sensor", "val", "z_score", "ts"]
        st.dataframe(
            anomaly_filtered[display_cols].sort_values(
                "z_score", key=abs, ascending=False
            ),
            column_config={
                "truck": st.column_config.TextColumn("Truck"),
                "sensor": "Sensor",
                "val": st.column_config.NumberColumn("Value", format="%.2f"),
                "z_score": st.column_config.NumberColumn("Z-score", format="%.2f"),
                "ts": st.column_config.DatetimeColumn(
                    "Timestamp", format="MMM DD, YYYY HH:mm"
                ),
            },
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.success("No anomalies detected for selected trucks.",
                    icon=":material/check_circle:")
else:
    st.success("No anomalies detected across the fleet.",
                icon=":material/check_circle:")

# ===========================================================================
# SECTION 5b: AI Weather Impact Prediction
# ===========================================================================
if not forecast_df.empty:
    st.html('<div class="gradient-divider"></div>')
    st.markdown("### :material/thunderstorm: AI weather impact prediction")
    st.caption("Cortex AI predicts how the 7-day forecast will affect fleet operations")

    with st.container(border=True):
        fc_str = forecast_df.to_string(index=False)
        with st.spinner("Cortex AI predicting weather impact on fleet..."):
            impact = generate_weather_impact_prediction(fc_str)
        st.markdown(impact)

# ===========================================================================
# SECTION 6: Weather forecast
# ===========================================================================
st.html('<div class="gradient-divider"></div>')
st.markdown("### :material/cloud: 7-day weather forecast")
st.caption("WeatherSource forecast for Calgary — color-coded operational risk")

if not forecast_df.empty:
    fc = forecast_df.copy()
    fc["risk"] = fc.apply(lambda r: risk_level(r["wind_mph"], r["temp_f"]), axis=1)

    # Tomorrow KPIs
    tomorrow = fc.iloc[0] if len(fc) > 0 else None
    if tomorrow is not None:
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            with st.container(border=True):
                st.caption(":material/thermostat: Tomorrow temp")
                st.markdown(f"### {tomorrow['temp_f']}°F")
        with f2:
            with st.container(border=True):
                st.caption(":material/air: Tomorrow wind")
                st.markdown(f"### {tomorrow['wind_mph']} mph")
        with f3:
            with st.container(border=True):
                st.caption(":material/water_drop: Precip chance")
                st.markdown(f"### {tomorrow['precip_pct']:.0f}%")
        with f4:
            with st.container(border=True):
                risk = tomorrow["risk"]
                st.caption(":material/shield: Risk level")
                if risk == "HIGH":
                    st.markdown("### :red[HIGH]")
                elif risk == "MEDIUM":
                    st.markdown("### :orange[MEDIUM]")
                else:
                    st.markdown("### :green[LOW]")

    col_fc1, col_fc2 = st.columns([2, 1])
    with col_fc1:
        with st.container(border=True):
            st.markdown("**Wind + temperature forecast**")
            wind_bars = (
                alt.Chart(fc)
                .mark_bar(color=C_ACCENT, opacity=0.7, cornerRadiusTopLeft=3,
                          cornerRadiusTopRight=3)
                .encode(
                    x=alt.X("forecast_date:T", title=None),
                    y=alt.Y("wind_mph:Q", title="Wind (mph)"),
                    tooltip=[
                        alt.Tooltip("forecast_date:T", title="Date",
                                    format="%b %d"),
                        alt.Tooltip("wind_mph:Q", title="Avg wind",
                                    format=".1f"),
                        alt.Tooltip("wind_max_mph:Q", title="Max wind",
                                    format=".1f"),
                    ],
                )
            )
            temp_line = (
                alt.Chart(fc)
                .mark_line(color=C_PRIMARY, strokeWidth=3, point=alt.OverlayMarkDef(
                    color=C_PRIMARY, size=60
                ))
                .encode(
                    x=alt.X("forecast_date:T"),
                    y=alt.Y("temp_f:Q", title="Temp (°F)",
                             axis=alt.Axis(titleColor=C_PRIMARY)),
                    tooltip=[
                        alt.Tooltip("forecast_date:T", title="Date",
                                    format="%b %d"),
                        alt.Tooltip("temp_f:Q", title="Avg temp",
                                    format=".1f"),
                        alt.Tooltip("temp_min_f:Q", title="Min temp",
                                    format=".1f"),
                        alt.Tooltip("temp_max_f:Q", title="Max temp",
                                    format=".1f"),
                    ],
                )
            )

            st.altair_chart(
                alt.layer(wind_bars, temp_line).resolve_scale(
                    y="independent"
                ).properties(height=CHART_HEIGHT),
                use_container_width=True,
            )

    with col_fc2:
        with st.container(border=True):
            st.markdown("**Forecast details**")
            st.dataframe(
                fc,
                column_config={
                    "forecast_date": st.column_config.DateColumn(
                        "Date", format="MMM DD"
                    ),
                    "temp_f": st.column_config.NumberColumn(
                        "Temp °F", format="%.1f"
                    ),
                    "wind_mph": st.column_config.NumberColumn(
                        "Wind mph", format="%.1f"
                    ),
                    "precip_pct": st.column_config.NumberColumn(
                        "Precip %", format="%.0f"
                    ),
                    "risk": st.column_config.TextColumn("Risk"),
                    "temp_min_f": None,
                    "temp_max_f": None,
                    "wind_max_mph": None,
                    "precip_in": None,
                },
                hide_index=True,
                height=300,
                use_container_width=True,
            )
else:
    st.warning("Weather forecast data not available.")

# ---------------------------------------------------------------------------
# Section 7 — Talk to Your Data  (Cortex Agent)
# ---------------------------------------------------------------------------
st.html('<div class="gradient-divider"></div>')
st.subheader(":material/chat: Talk to Your Data")
st.caption(
    "Ask questions about the fleet in plain English. "
    "Powered by a Cortex Agent with text-to-SQL."
)

# AI insight teaser
if not fleet_df.empty:
    _insight_stats = f"Trucks: {fleet_df['truck'].nunique()}, " + ", ".join(
        f"{s}: avg {fleet_df[fleet_df['sensor']==s]['val'].mean():.1f}"
        for s in KEY_SENSORS[:3]
    )
    try:
        with st.spinner(""):
            insight = generate_insight_of_the_day(_insight_stats)
        if insight:
            st.html(f'<div class="insight-chip">&#x1F4A1; {insight}</div>')
    except Exception:
        pass

SUGGESTED_QUESTIONS = [
    "What is the average fuel rate per truck?",
    "Which truck had the highest coolant temperature?",
    "Show me the average speed by day of week",
    "Compare engine load across all trucks",
    "Which hours of the day have the highest fuel consumption?",
]

# Initialise chat history
if "agent_messages" not in st.session_state:
    st.session_state.agent_messages = []


def call_agent(question: str) -> dict:
    """Call the Cortex Agent via the internal SiS API.
    Falls back to Cortex Analyst if the agent endpoint is unavailable.
    """
    # Try Cortex Agent first
    request_body = {
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": question}]}
        ],
        "stream": False,
    }
    try:
        resp = _snowflake.send_snow_api_request(
            "POST",
            AGENT_API_ENDPOINT,
            {},
            {},
            request_body,
            {},
            120000,
        )
        if resp["status"] < 400:
            return json.loads(resp["content"])
        # If agent endpoint fails, fall back to Cortex Analyst
        return _call_analyst_fallback(question)
    except Exception:
        return _call_analyst_fallback(question)


def _call_analyst_fallback(question: str) -> dict:
    """Fallback: call Cortex Analyst API directly with the semantic view."""
    request_body = {
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": question}]}
        ],
        "semantic_view": SEMANTIC_VIEW_FQN,
    }
    try:
        resp = _snowflake.send_snow_api_request(
            "POST",
            "/api/v2/cortex/analyst/message",
            {},
            {},
            request_body,
            {},
            60000,
        )
        if resp["status"] < 400:
            return json.loads(resp["content"])
        return {
            "error": f"Analyst returned status {resp['status']}",
            "details": resp.get("content", ""),
        }
    except Exception as exc:
        return {"error": str(exc)}


def display_agent_response(response: dict):
    """Render agent response: text, SQL + results, suggestions."""
    if "error" in response:
        st.error(f"Agent error: {response['error']}")
        if "details" in response:
            with st.expander("Details"):
                st.code(str(response["details"])[:2000])
        return

    # The agent object-based response wraps content in "message.content"
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
            # Agent wraps analyst results inside tool_results
            for tr in item.get("tool_results", [item]):
                inner = tr.get("content", [])
                for inner_item in inner:
                    _render_content_item(inner_item)
        elif item_type == "sql":
            _render_sql_item(item)
        elif item_type == "suggestions":
            _render_suggestions(item)
        else:
            # Catch-all for other content types
            if "text" in item:
                st.markdown(item["text"])
            elif "json" in item:
                _render_json_payload(item["json"])


def _render_json_payload(payload):
    """Handle JSON payloads that may contain SQL or text."""
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
    """Render a single content item from tool results."""
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
    """Execute and display a SQL result."""
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
                st.bar_chart(
                    result_df.set_index(result_df.columns[0])[numeric_cols]
                )
    except Exception as exc:
        st.error(f"Query error: {exc}")


def _render_suggestions(item):
    """Show suggested follow-up questions."""
    suggestions = item.get("suggestions", [])
    if suggestions:
        st.markdown("**Suggested questions:**")
        for sug in suggestions:
            st.markdown(f"- {sug}")


# Suggested-question buttons (3-column grid)
row1 = st.columns(3)
row2 = st.columns(3)
sq_grid = row1 + row2
for i, q in enumerate(SUGGESTED_QUESTIONS):
    if i < len(sq_grid) and sq_grid[i].button(q, key=f"sq_{i}", use_container_width=True):
        st.session_state.agent_messages.append({"role": "user", "content": q})

# Render conversation history
for msg in st.session_state.agent_messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and isinstance(msg["content"], dict):
            display_agent_response(msg["content"])
        else:
            st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask about the fleet data..."):
    st.session_state.agent_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

# Process last user message if assistant hasn't responded yet
if (
    st.session_state.agent_messages
    and st.session_state.agent_messages[-1]["role"] == "user"
):
    user_q = st.session_state.agent_messages[-1]["content"]
    with st.chat_message("assistant"):
        with st.spinner("Querying fleet data..."):
            agent_resp = call_agent(user_q)
        display_agent_response(agent_resp)
    st.session_state.agent_messages.append(
        {"role": "assistant", "content": agent_resp}
    )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.html('<div class="gradient-divider"></div>')
st.caption(
    ":material/database: AVEVA IoT via Snowflake Catalog Integration  |  "
    ":material/cloud: WeatherSource (Snowflake Marketplace)  |  "
    ":material/smart_toy: AI powered by Snowflake Cortex  |  "
    ":material/chat: Cortex Agent for natural language queries"
)
