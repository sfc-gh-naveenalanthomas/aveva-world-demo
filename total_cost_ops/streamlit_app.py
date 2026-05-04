"""
Total Cost of Operations — Cross-Industry Cost Analytics

AVEVA operational data + Snowflake Marketplace (Weather, Energy Prices)
= unified cost intelligence across mining trucks and water pumps.

Data sources:
- AVEVA mining_haul_truck_narrow_26q1 (Q1 2026, 1.68M rows, 10 trucks)
- AVEVA water_leakage_pump_narrow_live (live, 7.4M+ rows, 25 pumps)
- Yes Energy DART_PRICES_SAMPLE (energy market prices, Jan 2024–Jan 2026)
- WeatherSource POINT_HISTORY_DAY + POINT_FORECAST_DAY (Calgary)
- Snowflake Cortex AI (mistral-large2) for optimization recommendations
"""

from datetime import date, timedelta
import json

import altair as alt
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

st.set_page_config(
    page_title="Total Cost of Operations",
    page_icon=":material/payments:",
    layout="wide",
)

# =============================================================================
# Snowflake connection
# =============================================================================


def get_conn():
    try:
        return st.connection("snowflake")
    except Exception as e:
        st.error(f"Failed to connect to Snowflake: {e}")
        st.info(
            "Configure your connection in `.streamlit/secrets.toml` "
            "or via environment variables."
        )
        st.stop()


# =============================================================================
# Auto-detect AVEVA CLD database name (varies by account)
# =============================================================================

def _detect_cld_db():
    """Return the AVEVA CLD database name available on this account."""
    conn = get_conn()
    for candidate in ["CONNECT_AWC26", "AVEVA_CLD_DATA"]:
        try:
            conn.query(f'SELECT 1 FROM {candidate}."f6dd054e-d7b7-4b48-97f3-1b0eb2e91ab0".mining_haul_truck_narrow_26q1 LIMIT 1')
            return candidate
        except Exception:
            continue
    return "AVEVA_CLD_DATA"

CLD_DB = _detect_cld_db()

# =============================================================================
# Auto-detect Marketplace data sources (fall back to fabricated samples)
# =============================================================================

def _detect_weather_db():
    conn = get_conn()
    try:
        conn.query("SHOW SCHEMAS IN DATABASE GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI")
        return (
            "GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI.PWS_BI_SAMPLE.POINT_HISTORY_DAY",
            "GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI.PWS_BI_SAMPLE.POINT_FORECAST_DAY",
        )
    except Exception:
        return (
            "AVEVA_WORLD_DEMOS.STREAMLIT_APPS.WEATHER_HISTORY_SAMPLE",
            "AVEVA_WORLD_DEMOS.STREAMLIT_APPS.WEATHER_FORECAST_SAMPLE",
        )

def _detect_dart_db():
    conn = get_conn()
    try:
        conn.query("SHOW SCHEMAS IN DATABASE YES_ENERGY__SAMPLE_DATA")
        return "YES_ENERGY__SAMPLE_DATA.YES_ENERGY_SAMPLE.DART_PRICES_SAMPLE"
    except Exception:
        return "AVEVA_WORLD_DEMOS.STREAMLIT_APPS.DART_PRICES_SAMPLE"

_WH, _WF = _detect_weather_db()

# =============================================================================
# Constants
# =============================================================================

SCHEMA = '"f6dd054e-d7b7-4b48-97f3-1b0eb2e91ab0"'
TRUCK_TABLE = f'{CLD_DB}.{SCHEMA}.mining_haul_truck_narrow_26q1'
PUMP_TABLE = f'{CLD_DB}.{SCHEMA}.water_leakage_pump_narrow_live'
DART_TABLE = _detect_dart_db()
WEATHER_HIST = _WH
WEATHER_FCST = _WF
SF_ACCOUNTS = "AVEVA_WORLD_DEMOS.SALESFORCE.SF_ACCOUNTS"
SF_CONTRACTS = "AVEVA_WORLD_DEMOS.SALESFORCE.SF_CONTRACTS"
SF_DELIVERIES = "AVEVA_WORLD_DEMOS.SALESFORCE.SF_DELIVERIES"
SF_CASES = "AVEVA_WORLD_DEMOS.SALESFORCE.SF_CASES"

CHART_HEIGHT = 340
DEFAULT_FUEL_PRICE = 1.30  # $/litre diesel
DEFAULT_ELEC_RATE = 0.13   # $/kWh

# GPS offset to re-centre fabricated coords to Fort McMurray, Alberta (~57°N, -111°W)
GPS_LAT_OFFSET = 8.0
GPS_LON_OFFSET = -222.0


# =============================================================================
# Data loading — cached queries
# =============================================================================


def _fix_decimals(df: pd.DataFrame) -> pd.DataFrame:
    """Convert Decimal columns to float64 (Snowflake connector returns Decimal in SiS)."""
    for col in df.columns:
        if df[col].dtype == object and len(df) > 0:
            from decimal import Decimal
            sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
            if isinstance(sample, Decimal):
                df[col] = df[col].astype(float)
        elif hasattr(df[col].dtype, 'name') and 'decimal' in str(df[col].dtype).lower():
            df[col] = df[col].astype(float)
    return df


@st.cache_data(ttl=600, show_spinner="Loading truck fleet data...")
def load_truck_daily() -> pd.DataFrame:
    conn = get_conn()
    df = conn.query(f"""
        SELECT DATE_TRUNC('day', "Timestamp") AS day,
            SUM(CASE WHEN "Field" = 'Engine Fuel Rate Value l/h' THEN "Value" END) AS total_fuel_lh,
            AVG(CASE WHEN "Field" = 'Engine Fuel Rate Value l/h' THEN "Value" END) AS avg_fuel_lh,
            SUM(CASE WHEN "Field" = 'Payload Value t' THEN "Value" END) AS total_payload_t,
            AVG(CASE WHEN "Field" = 'Engine Load Value %' THEN "Value" END) AS avg_engine_load,
            COUNT(DISTINCT "Name") AS active_trucks
        FROM {TRUCK_TABLE}
        WHERE "Field" IN ('Engine Fuel Rate Value l/h', 'Payload Value t', 'Engine Load Value %')
        GROUP BY 1
        HAVING total_fuel_lh IS NOT NULL
        ORDER BY 1
    """)
    df.columns = df.columns.str.lower()
    df = _fix_decimals(df)
    df["day"] = pd.to_datetime(df["day"]).dt.tz_localize(None)
    return df


@st.cache_data(ttl=600, show_spinner="Loading truck per-vehicle data...")
def load_truck_per_vehicle() -> pd.DataFrame:
    conn = get_conn()
    df = conn.query(f"""
        SELECT "Name" AS truck,
            DATE_TRUNC('day', "Timestamp") AS day,
            AVG(CASE WHEN "Field" = 'Engine Fuel Rate Value l/h' THEN "Value" END) AS avg_fuel_lh,
            SUM(CASE WHEN "Field" = 'Payload Value t' THEN "Value" END) AS total_payload_t
        FROM {TRUCK_TABLE}
        WHERE "Field" IN ('Engine Fuel Rate Value l/h', 'Payload Value t')
        GROUP BY 1, 2
        HAVING avg_fuel_lh IS NOT NULL
        ORDER BY 1, 2
    """)
    df.columns = df.columns.str.lower()
    df = _fix_decimals(df)
    df["day"] = pd.to_datetime(df["day"]).dt.tz_localize(None)
    return df


@st.cache_data(ttl=600, show_spinner="Loading pump energy data...")
def load_pump_daily() -> pd.DataFrame:
    conn = get_conn()
    df = conn.query(f"""
        SELECT DATE_TRUNC('day', "Timestamp") AS day,
            SUM(CASE WHEN "Field" = 'Energy Consumed Daily Value kWh' THEN "Value" END) AS daily_kwh,
            SUM(CASE WHEN "Field" = 'Energy Cost Daily Value' THEN "Value" END) AS daily_cost,
            COUNT(DISTINCT "Name") AS active_pumps,
            AVG(CASE WHEN "Field" = 'Motor Power Value kW' THEN "Value" END) AS avg_motor_kw
        FROM {PUMP_TABLE}
        WHERE "Field" IN ('Energy Consumed Daily Value kWh', 'Energy Cost Daily Value', 'Motor Power Value kW')
        GROUP BY 1
        HAVING daily_kwh > 0
        ORDER BY 1
    """)
    df.columns = df.columns.str.lower()
    df = _fix_decimals(df)
    df["day"] = pd.to_datetime(df["day"]).dt.tz_localize(None)
    return df


@st.cache_data(ttl=600, show_spinner="Loading pump rankings...")
def load_pump_ranked() -> pd.DataFrame:
    conn = get_conn()
    df = conn.query(f"""
        SELECT "Name" AS pump,
            ROUND(AVG(CASE WHEN "Field" = 'Motor Power Value kW' THEN "Value" END), 1) AS avg_power_kw,
            ROUND(AVG(CASE WHEN "Field" = 'Pump Efficiency Value %' THEN "Value" END), 2) AS avg_efficiency,
            ROUND(SUM(CASE WHEN "Field" = 'Energy Cost Daily Value' THEN "Value" END), 0) AS total_cost,
            ROUND(SUM(CASE WHEN "Field" = 'Energy Consumed Daily Value kWh' THEN "Value" END), 0) AS total_kwh,
            ROUND(AVG(CASE WHEN "Field" = 'Running Hours Value h' THEN "Value" END), 0) AS run_hours
        FROM {PUMP_TABLE}
        WHERE "Field" IN ('Motor Power Value kW', 'Pump Efficiency Value %',
                          'Energy Cost Daily Value', 'Energy Consumed Daily Value kWh',
                          'Running Hours Value h')
        GROUP BY 1
        HAVING total_cost > 0
        ORDER BY total_cost DESC
    """)
    df.columns = df.columns.str.lower()
    df = _fix_decimals(df)
    return df


@st.cache_data(ttl=1800, show_spinner="Loading weather history...")
def load_weather_history() -> pd.DataFrame:
    conn = get_conn()
    df = conn.query(f"""
        SELECT DATE_TRUNC('day', DATE_VALID_STD) AS day,
            AVG(AVG_TEMPERATURE_AIR_2M_F) AS temp_f,
            AVG("__AVG_WIND_SPEED_10M_MPH") AS wind_mph,
            AVG(TOT_PRECIPITATION_IN) AS precip_in
        FROM {WEATHER_HIST}
        WHERE CITY_NAME = 'calgary'
        GROUP BY 1
        ORDER BY 1
    """)
    df.columns = df.columns.str.lower()
    df = _fix_decimals(df)
    df["day"] = pd.to_datetime(df["day"]).dt.tz_localize(None)
    return df


@st.cache_data(ttl=3600, show_spinner="Loading weather forecast...")
def load_weather_forecast() -> pd.DataFrame:
    conn = get_conn()
    df = conn.query(f"""
        SELECT DATE_VALID_STD AS day,
            ROUND(AVG(AVG_TEMPERATURE_AIR_2M_F), 1) AS temp_f,
            ROUND(AVG("__AVG_WIND_SPEED_10M_MPH"), 1) AS wind_mph,
            ROUND(AVG(PROBABILITY_OF_PRECIPITATION_PCT), 0) AS precip_pct
        FROM {WEATHER_FCST}
        WHERE CITY_NAME = 'calgary'
        GROUP BY 1
        ORDER BY 1
    """)
    df.columns = df.columns.str.lower()
    df = _fix_decimals(df)
    df["day"] = pd.to_datetime(df["day"]).dt.tz_localize(None)
    return df


@st.cache_data(ttl=3600, show_spinner="Loading energy market prices...")
def load_energy_prices() -> pd.DataFrame:
    conn = get_conn()
    df = conn.query(f"""
        SELECT DATE_TRUNC('day', DATETIME) AS day,
            ROUND(AVG(DALMP), 2) AS avg_day_ahead,
            ROUND(AVG(RTLMP), 2) AS avg_realtime,
            ROUND(MIN(DALMP), 2) AS min_da,
            ROUND(MAX(DALMP), 2) AS max_da
        FROM {DART_TABLE}
        GROUP BY 1
        ORDER BY 1
    """)
    df.columns = df.columns.str.lower()
    df = _fix_decimals(df)
    df["day"] = pd.to_datetime(df["day"]).dt.tz_localize(None)
    return df


@st.cache_data(ttl=600, show_spinner="Loading Salesforce contracts...")
def load_sf_contract_performance() -> pd.DataFrame:
    conn = get_conn()
    df = conn.query(f"""
        SELECT a.account_name, c.contract_id, c.contract_name, c.rate_per_tonne,
            c.sla_ontime_pct AS sla_target, c.monthly_tonnage_commitment,
            COUNT(d.delivery_id) AS total_deliveries,
            SUM(d.tonnage_delivered) AS total_tonnage,
            ROUND(SUM(CASE WHEN d.on_time THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 1) AS actual_ontime_pct,
            SUM(d.tonnage_delivered) * c.rate_per_tonne AS gross_revenue
        FROM {SF_CONTRACTS} c
        JOIN {SF_ACCOUNTS} a ON c.account_id = a.account_id
        JOIN {SF_DELIVERIES} d ON c.contract_id = d.contract_id
        GROUP BY 1,2,3,4,5,6
        ORDER BY gross_revenue DESC
    """)
    df.columns = df.columns.str.lower()
    df = _fix_decimals(df)
    return df


@st.cache_data(ttl=600, show_spinner="Loading Salesforce deliveries...")
def load_sf_daily_deliveries() -> pd.DataFrame:
    conn = get_conn()
    df = conn.query(f"""
        SELECT d.delivery_date AS day,
            COUNT(*) AS deliveries,
            SUM(d.tonnage_delivered) AS tonnage,
            ROUND(SUM(CASE WHEN d.on_time THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS ontime_pct,
            SUM(CASE WHEN d.weather_delayed THEN 1 ELSE 0 END) AS weather_delays,
            SUM(d.tonnage_delivered * c.rate_per_tonne) AS daily_revenue
        FROM {SF_DELIVERIES} d
        JOIN {SF_CONTRACTS} c ON d.contract_id = c.contract_id
        GROUP BY 1
        ORDER BY 1
    """)
    df.columns = df.columns.str.lower()
    df = _fix_decimals(df)
    df["day"] = pd.to_datetime(df["day"]).dt.tz_localize(None)
    return df


@st.cache_data(ttl=600, show_spinner="Loading SLA penalties...")
def load_sf_penalties() -> pd.DataFrame:
    conn = get_conn()
    df = conn.query(f"""
        SELECT cs.case_date AS day, cs.category, cs.priority,
            a.account_name, cs.penalty_amount, cs.subject
        FROM {SF_CASES} cs
        JOIN {SF_ACCOUNTS} a ON cs.account_id = a.account_id
        ORDER BY cs.case_date
    """)
    df.columns = df.columns.str.lower()
    df = _fix_decimals(df)
    df["day"] = pd.to_datetime(df["day"]).dt.tz_localize(None)
    return df


@st.cache_data(ttl=600, show_spinner="Loading revenue by account...")
def load_sf_revenue_by_account() -> pd.DataFrame:
    conn = get_conn()
    df = conn.query(f"""
        SELECT a.account_name, a.tier,
            SUM(d.tonnage_delivered * c.rate_per_tonne) AS revenue,
            SUM(COALESCE(cs.penalties, 0)) AS total_penalties,
            SUM(d.tonnage_delivered * c.rate_per_tonne) - SUM(COALESCE(cs.penalties, 0)) AS net_revenue
        FROM {SF_ACCOUNTS} a
        JOIN {SF_CONTRACTS} c ON a.account_id = c.account_id
        JOIN {SF_DELIVERIES} d ON c.contract_id = d.contract_id
        LEFT JOIN (
            SELECT contract_id, SUM(penalty_amount) AS penalties
            FROM {SF_CASES}
            GROUP BY 1
        ) cs ON c.contract_id = cs.contract_id
        GROUP BY 1, 2
        ORDER BY revenue DESC
    """)
    df.columns = df.columns.str.lower()
    df = _fix_decimals(df)
    return df


@st.cache_data(ttl=600, show_spinner="Loading truck positions...")
def load_truck_latest_positions() -> pd.DataFrame:
    conn = get_conn()
    df = conn.query(f"""
        WITH latest AS (
            SELECT "Name", "Field", CAST("Value" AS FLOAT) AS val,
                ROW_NUMBER() OVER (PARTITION BY "Name", "Field" ORDER BY "Timestamp" DESC) AS rn
            FROM {TRUCK_TABLE}
            WHERE "Field" IN ('Latitude Value °', 'Longitude Value °',
                              'Ground Speed Value km/h', 'Payload Value t',
                              'Engine Load Value %', 'Payload Status Value')
              AND CAST("Value" AS FLOAT) != 0
        )
        SELECT "Name" AS truck,
            MAX(CASE WHEN "Field" = 'Latitude Value °' THEN val END) + {GPS_LAT_OFFSET} AS lat,
            MAX(CASE WHEN "Field" = 'Longitude Value °' THEN val END) + {GPS_LON_OFFSET} AS lon,
            MAX(CASE WHEN "Field" = 'Ground Speed Value km/h' THEN val END) AS speed_kmh,
            MAX(CASE WHEN "Field" = 'Payload Value t' THEN val END) AS payload_t,
            MAX(CASE WHEN "Field" = 'Engine Load Value %' THEN val END) AS engine_load,
            MAX(CASE WHEN "Field" = 'Payload Status Value' THEN val END) AS payload_status
        FROM latest WHERE rn = 1
        GROUP BY 1
        ORDER BY 1
    """)
    df.columns = df.columns.str.lower()
    df = _fix_decimals(df)
    return df


@st.cache_data(ttl=600, show_spinner="Loading truck health data...")
def load_truck_health_snapshot() -> pd.DataFrame:
    conn = get_conn()
    df = conn.query(f"""
        WITH recent AS (
            SELECT "Name", "Field", CAST("Value" AS FLOAT) AS val
            FROM {TRUCK_TABLE}
            WHERE "Field" IN (
                'Engine Coolant Temperature Value °C',
                'Engine Oil Pressure Value psi',
                'Left Exhaust Temperature Value °C',
                'Right Exhaust Temperature Value °C',
                'Left Front Brake Temperature Value °C',
                'Right Front Brake Temperature Value °C',
                'Hourly Average Delta Exhaust Temp Engine Load Value delta °C',
                'Hourly Average Delta Front Suspension Value kPa',
                'Hourly Average Delta Rear Suspension Value kPa'
            )
            AND "Timestamp" >= DATEADD(day, -1, (SELECT MAX("Timestamp") FROM {TRUCK_TABLE}))
        )
        SELECT "Name" AS truck, "Field" AS field,
            AVG(val) AS avg_val,
            MAX(val) AS max_val,
            STDDEV(val) AS std_val,
            COUNT(*) AS readings
        FROM recent
        GROUP BY 1, 2
        ORDER BY 1, 2
    """)
    df.columns = df.columns.str.lower()
    df = _fix_decimals(df)
    return df


@st.cache_data(ttl=600, show_spinner="Loading sensor trends...")
def load_truck_sensor_trends(truck_name: str) -> pd.DataFrame:
    conn = get_conn()
    escaped_name = truck_name.replace("'", "''")
    df = conn.query(f"""
        SELECT DATE_TRUNC('hour', "Timestamp") AS hour,
            "Field" AS field,
            AVG(CAST("Value" AS FLOAT)) AS avg_val,
            MAX(CAST("Value" AS FLOAT)) AS max_val,
            MIN(CAST("Value" AS FLOAT)) AS min_val
        FROM {TRUCK_TABLE}
        WHERE "Name" = '{escaped_name}'
          AND "Field" IN (
            'Engine Coolant Temperature Value °C',
            'Engine Oil Pressure Value psi',
            'Left Exhaust Temperature Value °C',
            'Right Exhaust Temperature Value °C',
            'Left Front Brake Temperature Value °C',
            'Right Front Brake Temperature Value °C',
            'Engine Load Value %'
          )
          AND "Timestamp" >= DATEADD(day, -7, (SELECT MAX("Timestamp") FROM {TRUCK_TABLE}))
        GROUP BY 1, 2
        ORDER BY 1, 2
    """)
    df.columns = df.columns.str.lower()
    df = _fix_decimals(df)
    df["hour"] = pd.to_datetime(df["hour"]).dt.tz_localize(None)
    return df


def compute_health_scores(health_df: pd.DataFrame) -> pd.DataFrame:
    """Compute 0-100 health score per truck from sensor z-scores."""
    # Define normal operating ranges (from data analysis)
    normal_ranges = {
        "Engine Coolant Temperature Value °C": {"mean": 90.0, "std": 1.5, "weight": 0.25},
        "Engine Oil Pressure Value psi": {"mean": 450.0, "std": 15.0, "weight": 0.25},
        "Hourly Average Delta Exhaust Temp Engine Load Value delta °C": {"mean": 40.0, "std": 3.0, "weight": 0.20},
        "Left Front Brake Temperature Value °C": {"mean": 75.0, "std": 5.0, "weight": 0.15},
        "Right Front Brake Temperature Value °C": {"mean": 75.0, "std": 5.0, "weight": 0.15},
    }
    trucks = health_df["truck"].unique()
    results = []
    for truck in trucks:
        truck_data = health_df[health_df["truck"] == truck]
        weighted_z = 0.0
        total_weight = 0.0
        top_risk = ""
        top_risk_z = 0.0
        for field, params in normal_ranges.items():
            row = truck_data[truck_data["field"] == field]
            if row.empty:
                continue
            val = row.iloc[0]["max_val"]
            z = abs(val - params["mean"]) / params["std"]
            weighted_z += z * params["weight"]
            total_weight += params["weight"]
            if z > top_risk_z:
                top_risk_z = z
                top_risk = field.replace(" Value", "").replace(" °C", "").replace(" psi", "").replace(" kPa", "")
        score = max(0, min(100, 100 - (weighted_z / max(total_weight, 0.01)) * 15))
        days_to_maint = max(1, int(score / 100 * 30))
        results.append({
            "truck": truck,
            "health_score": round(score, 1),
            "top_risk": top_risk,
            "risk_z": round(top_risk_z, 2),
            "days_to_maintenance": days_to_maint,
            "status": "Healthy" if score >= 80 else ("Warning" if score >= 60 else "Critical"),
        })
    return pd.DataFrame(results).sort_values("health_score")


@st.cache_data(ttl=600, show_spinner="Loading truck trails...")
def load_truck_trails() -> pd.DataFrame:
    conn = get_conn()
    df = conn.query(f"""
        WITH gps AS (
            SELECT "Name" AS truck, "Timestamp" AS ts, "Field",
                CAST("Value" AS FLOAT) AS val
            FROM {TRUCK_TABLE}
            WHERE "Field" IN ('Latitude Value °', 'Longitude Value °')
              AND CAST("Value" AS FLOAT) != 0
              AND "Timestamp" >= DATEADD(hour, -2, (SELECT MAX("Timestamp") FROM {TRUCK_TABLE}))
        )
        SELECT truck, ts,
            MAX(CASE WHEN "Field" = 'Latitude Value °' THEN val END) + {GPS_LAT_OFFSET} AS lat,
            MAX(CASE WHEN "Field" = 'Longitude Value °' THEN val END) + {GPS_LON_OFFSET} AS lon
        FROM gps
        GROUP BY 1, 2
        HAVING lat IS NOT NULL AND lon IS NOT NULL
        ORDER BY 1, 2
    """)
    df.columns = df.columns.str.lower()
    df = _fix_decimals(df)
    return df


@st.cache_data(ttl=600, show_spinner="Loading fleet day replay...")
def load_fleet_day_gps(replay_date: str) -> pd.DataFrame:
    """Load all GPS + speed + payload readings for every truck on a given date."""
    conn = get_conn()
    df = conn.query(f"""
        WITH gps AS (
            SELECT "Name" AS truck, "Timestamp" AS ts, "Field",
                CAST("Value" AS FLOAT) AS val
            FROM {TRUCK_TABLE}
            WHERE "Field" IN ('Latitude Value °', 'Longitude Value °',
                              'Ground Speed Value km/h', 'Payload Value t')
              AND CAST("Value" AS FLOAT) != 0
              AND "Timestamp"::DATE = '{replay_date}'
        ),
        pivoted AS (
            SELECT truck, ts,
                MAX(CASE WHEN "Field" = 'Latitude Value °' THEN val END) + {GPS_LAT_OFFSET} AS lat,
                MAX(CASE WHEN "Field" = 'Longitude Value °' THEN val END) + {GPS_LON_OFFSET} AS lon,
                MAX(CASE WHEN "Field" = 'Ground Speed Value km/h' THEN val END) AS speed_kmh,
                MAX(CASE WHEN "Field" = 'Payload Value t' THEN val END) AS payload_t
            FROM gps
            GROUP BY 1, 2
            HAVING lat IS NOT NULL AND lon IS NOT NULL
        )
        SELECT *, EXTRACT(HOUR FROM ts) + EXTRACT(MINUTE FROM ts) / 60.0 AS hour_frac
        FROM pivoted
        ORDER BY truck, ts
    """)
    df.columns = df.columns.str.lower()
    df = _fix_decimals(df)
    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"]).dt.tz_localize(None)
    return df


# =============================================================================
# Cortex AI helper
# =============================================================================


def cortex_chat(messages: list[dict]) -> str:
    """Send a multi-turn conversation to Cortex AI and return the response text."""
    conn = get_conn()
    msgs_json = json.dumps(messages).replace("\\", "\\\\").replace("'", "''")
    result = conn.query(
        f"SELECT SNOWFLAKE.CORTEX.COMPLETE("
        f"'mistral-large2', PARSE_JSON('{msgs_json}')::ARRAY, {{}}"
        f") AS response"
    )
    result.columns = result.columns.str.lower()
    raw = result.iloc[0]["response"]
    try:
        resp = json.loads(raw)
        return resp["choices"][0]["messages"]
    except (json.JSONDecodeError, TypeError, KeyError, IndexError):
        return str(raw)


# =============================================================================
# Chart utilities
# =============================================================================


def make_line_chart(df, x, y_cols, labels, height=CHART_HEIGHT, zero=False):
    melted = df.melt(id_vars=[x], value_vars=y_cols, var_name="series", value_name="value")
    label_map = dict(zip(y_cols, labels))
    melted["series"] = melted["series"].map(label_map)
    return (
        alt.Chart(melted)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X(f"{x}:T", title=None),
            y=alt.Y("value:Q", title=None, scale=alt.Scale(zero=zero)),
            color=alt.Color("series:N", title=None, legend=alt.Legend(orient="bottom")),
            tooltip=[
                alt.Tooltip(f"{x}:T", title="Date", format="%b %d, %Y"),
                alt.Tooltip("series:N", title="Metric"),
                alt.Tooltip("value:Q", title="Value", format=",.1f"),
            ],
        )
        .properties(height=height)
    )


def make_bar_chart(df, x, y, color=None, height=CHART_HEIGHT, title_y=None):
    enc = {
        "x": alt.X(f"{x}:N", title=None, sort="-y"),
        "y": alt.Y(f"{y}:Q", title=title_y),
        "tooltip": [alt.Tooltip(f"{x}:N"), alt.Tooltip(f"{y}:Q", format=",.0f")],
    }
    if color:
        enc["color"] = alt.Color(f"{color}:N", title=None, legend=None)
    return alt.Chart(df).mark_bar().encode(**enc).properties(height=height)


def make_scatter(df, x, y, x_label, y_label, height=CHART_HEIGHT):
    points = (
        alt.Chart(df)
        .mark_circle(opacity=0.5, size=30)
        .encode(
            x=alt.X(f"{x}:Q", title=x_label),
            y=alt.Y(f"{y}:Q", title=y_label),
            tooltip=[alt.Tooltip(f"{x}:Q", format=".1f"), alt.Tooltip(f"{y}:Q", format=".1f")],
        )
    )
    trend = points.transform_regression(x, y).mark_line(
        color="red", strokeDash=[5, 5], strokeWidth=2
    )
    return (points + trend).properties(height=height)


def make_stacked_area(df, x, y_cols, labels, height=CHART_HEIGHT):
    melted = df.melt(id_vars=[x], value_vars=y_cols, var_name="series", value_name="value")
    label_map = dict(zip(y_cols, labels))
    melted["series"] = melted["series"].map(label_map)
    return (
        alt.Chart(melted)
        .mark_area(opacity=0.7, line=True)
        .encode(
            x=alt.X(f"{x}:T", title=None),
            y=alt.Y("value:Q", title=None, stack=True),
            color=alt.Color(
                "series:N", title=None, legend=alt.Legend(orient="bottom"),
                scale=alt.Scale(range=["#FF6B35", "#4ECDC4"]),
            ),
            tooltip=[
                alt.Tooltip(f"{x}:T", title="Date", format="%b %d, %Y"),
                alt.Tooltip("series:N", title="Source"),
                alt.Tooltip("value:Q", title="Cost ($)", format=",.0f"),
            ],
        )
        .properties(height=height)
    )


def calc_correlation(s1, s2):
    mask = s1.notna() & s2.notna()
    if mask.sum() < 3:
        return 0.0
    a = np.asarray(s1[mask], dtype=np.float64)
    b = np.asarray(s2[mask], dtype=np.float64)
    if len(a) < 3:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


# =============================================================================
# Page header
# =============================================================================

with st.container(
    horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"
):
    st.markdown("# :material/payments: Total cost of operations")
    if st.button(":material/restart_alt: Reset", type="tertiary"):
        st.session_state.clear()
        st.rerun()

st.caption(
    ":material/factory: AVEVA operational data  "
    ":material/cloud: Snowflake Marketplace (Weather + Energy Prices)  "
    ":material/smart_toy: Cortex AI optimization"
)

# =============================================================================
# Sidebar — global controls
# =============================================================================

with st.sidebar:
    st.markdown("### :material/tune: Global settings")
    fuel_price = st.number_input(
        "Diesel price ($/litre)",
        min_value=0.50, max_value=3.00, value=DEFAULT_FUEL_PRICE, step=0.05,
        format="%.2f",
    )
    elec_rate = st.number_input(
        "Electricity rate ($/kWh)",
        min_value=0.05, max_value=0.50, value=DEFAULT_ELEC_RATE, step=0.01,
        format="%.2f",
    )
    st.caption("Prices apply to cost calculations across all tabs.")
    st.markdown("---")
    st.markdown(
        "**Data sources**\n"
        "- AVEVA haul trucks (Q1 2026)\n"
        "- AVEVA water pumps (live)\n"
        "- Yes Energy market prices\n"
        "- WeatherSource Calgary\n"
        "- Salesforce CRM (contracts & SLAs)\n"
    )
    with st.expander(":material/schema: Architecture", expanded=False):
        st.image("Presentation_arch.png")

# =============================================================================
# Tabs
# =============================================================================

tab_truck, tab_pump, tab_total, tab_market, tab_customer, tab_weather, tab_twin, tab_ai, tab_savings = st.tabs(
    [
        ":material/local_shipping: Truck fuel",
        ":material/water_pump: Pump energy",
        ":material/stacked_line_chart: Total cost",
        ":material/electric_bolt: Energy market",
        ":material/handshake: Customer revenue",
        ":material/thermostat: Weather multipliers",
        ":material/precision_manufacturing: Digital twin",
        ":material/smart_toy: AI optimization",
        ":material/savings: Savings calculator",
    ],
)

# =========================================================================
# TAB 1 — Truck fuel cost
# =========================================================================
with tab_truck:
    trucks = load_truck_daily()
    trucks_per = load_truck_per_vehicle()

    # Compute costs
    trucks["fuel_cost"] = trucks["total_fuel_lh"] * fuel_price
    trucks["cost_per_tonne"] = np.where(
        trucks["total_payload_t"] > 0,
        trucks["fuel_cost"] / trucks["total_payload_t"],
        np.nan,
    )

    # KPIs
    q1_fuel_cost = trucks["fuel_cost"].sum()
    q1_payload = trucks["total_payload_t"].sum()
    avg_fuel_rate = trucks["avg_fuel_lh"].mean()
    avg_cost_per_t = q1_fuel_cost / q1_payload if q1_payload > 0 else 0

    with st.container(horizontal=True):
        st.metric("Q1 fuel cost", f"${q1_fuel_cost:,.0f}", border=True)
        st.metric("Q1 payload", f"{q1_payload:,.0f} t", border=True)
        st.metric("Avg fuel rate", f"{avg_fuel_rate:,.0f} l/h", border=True)
        st.metric("Cost per tonne", f"${avg_cost_per_t:,.2f}/t", border=True)

    # Daily fuel cost chart
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**Daily fuel cost**")
            cost_chart = (
                alt.Chart(trucks)
                .mark_bar(color="#FF6B35")
                .encode(
                    x=alt.X("day:T", title=None),
                    y=alt.Y("fuel_cost:Q", title="Cost ($)"),
                    tooltip=[
                        alt.Tooltip("day:T", title="Date", format="%b %d"),
                        alt.Tooltip("fuel_cost:Q", title="Cost", format="$,.0f"),
                        alt.Tooltip("active_trucks:Q", title="Trucks"),
                    ],
                )
                .properties(height=CHART_HEIGHT)
            )
            st.altair_chart(cost_chart, use_container_width=True)

    with col2:
        with st.container(border=True):
            st.markdown("**Cost per tonne hauled**")
            cpt_chart = (
                alt.Chart(trucks.dropna(subset=["cost_per_tonne"]))
                .mark_line(color="#4ECDC4", strokeWidth=2)
                .encode(
                    x=alt.X("day:T", title=None),
                    y=alt.Y("cost_per_tonne:Q", title="$/tonne"),
                    tooltip=[
                        alt.Tooltip("day:T", title="Date", format="%b %d"),
                        alt.Tooltip("cost_per_tonne:Q", title="$/t", format=",.2f"),
                    ],
                )
                .properties(height=CHART_HEIGHT)
            )
            st.altair_chart(cpt_chart, use_container_width=True)

    # Per-truck breakdown
    with st.container(border=True):
        st.markdown("**Per-truck fuel consumption (avg l/h)**")
        truck_avg = (
            trucks_per.groupby("truck")["avg_fuel_lh"]
            .mean()
            .reset_index()
            .sort_values("avg_fuel_lh", ascending=False)
        )
        st.altair_chart(
            make_bar_chart(truck_avg, "truck", "avg_fuel_lh", title_y="Avg fuel (l/h)"),
            use_container_width=True,
        )

# =========================================================================
# TAB 2 — Pump energy cost
# =========================================================================
with tab_pump:
    pumps = load_pump_daily()
    pump_rank = load_pump_ranked()

    # KPIs
    latest = pumps.iloc[-1] if not pumps.empty else {}
    monthly_cost = pumps.tail(30)["daily_cost"].sum()

    with st.container(horizontal=True):
        st.metric("Today's energy cost", f"${latest.get('daily_cost', 0):,.0f}", border=True)
        st.metric("Last 30 days total", f"${monthly_cost:,.0f}", border=True)
        st.metric("Active pumps", f"{int(latest.get('active_pumps', 0))}", border=True)
        avg_unit_cost = monthly_cost / pumps.tail(30)["daily_kwh"].sum() if pumps.tail(30)["daily_kwh"].sum() > 0 else 0
        st.metric("Avg unit cost", f"${avg_unit_cost:.4f}/kWh", border=True)

    # Anomaly callout
    anomaly_day = pumps[pumps["daily_cost"] < 1000]
    if not anomaly_day.empty:
        with st.container(border=True):
            row = anomaly_day.iloc[-1]
            st.warning(
                f":material/warning: **Anomaly detected** — "
                f"{row['day'].strftime('%b %d')}: only ${row['daily_cost']:,.0f} "
                f"({row['daily_kwh']:,.0f} kWh) vs normal ~$7,000+/day. "
                f"Indicates pump fleet shutdown.",
                icon=":material/warning:",
            )

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**Daily energy cost and consumption**")
            st.altair_chart(
                make_line_chart(
                    pumps, "day",
                    ["daily_cost", "daily_kwh"],
                    ["Cost ($)", "Consumption (kWh)"],
                ),
                use_container_width=True,
            )

    with col2:
        with st.container(border=True):
            st.markdown("**Avg motor power (kW)**")
            power_chart = (
                alt.Chart(pumps)
                .mark_area(opacity=0.5, color="#9B59B6", line=True)
                .encode(
                    x=alt.X("day:T", title=None),
                    y=alt.Y("avg_motor_kw:Q", title="kW", scale=alt.Scale(zero=False)),
                    tooltip=[
                        alt.Tooltip("day:T", format="%b %d"),
                        alt.Tooltip("avg_motor_kw:Q", format=",.1f"),
                    ],
                )
                .properties(height=CHART_HEIGHT)
            )
            st.altair_chart(power_chart, use_container_width=True)

    # Pump ranking table
    with st.container(border=True):
        st.markdown("**Pump cost efficiency ranking**")
        pump_rank["cost_per_kwh"] = np.where(
            pump_rank["total_kwh"] > 0,
            pump_rank["total_cost"] / pump_rank["total_kwh"],
            np.nan,
        )
        display_cols = ["pump", "avg_power_kw", "avg_efficiency", "total_cost", "total_kwh", "run_hours", "cost_per_kwh"]
        avail_cols = [c for c in display_cols if c in pump_rank.columns]
        st.dataframe(
            pump_rank[avail_cols].head(15),
            use_container_width=True,
            hide_index=True,
            column_config={
                "pump": st.column_config.TextColumn("Pump"),
                "avg_power_kw": st.column_config.NumberColumn("Power (kW)", format="%.1f"),
                "avg_efficiency": st.column_config.NumberColumn("Efficiency (%)", format="%.2f"),
                "total_cost": st.column_config.NumberColumn("Total cost ($)", format="$%,.0f"),
                "total_kwh": st.column_config.NumberColumn("Total kWh", format="%,.0f"),
                "run_hours": st.column_config.NumberColumn("Run hours", format="%,.0f"),
                "cost_per_kwh": st.column_config.NumberColumn("$/kWh", format="$%.4f"),
            },
        )

# =========================================================================
# TAB 3 — Cross-industry total cost
# =========================================================================
with tab_total:
    trucks = load_truck_daily()
    pumps = load_pump_daily()
    weather = load_weather_history()
    sf_penalties_data = load_sf_penalties()

    trucks["fuel_cost"] = trucks["total_fuel_lh"] * fuel_price
    pumps_subset = pumps[["day", "daily_cost"]].rename(columns={"daily_cost": "pump_cost"})
    trucks_subset = trucks[["day", "fuel_cost"]].rename(columns={"fuel_cost": "truck_cost"})

    # SLA penalties aggregated by month (cases are monthly)
    sla_monthly = sf_penalties_data.groupby(
        sf_penalties_data["day"].dt.to_period("M").dt.to_timestamp()
    )["penalty_amount"].sum().reset_index()
    sla_monthly.columns = ["day", "sla_penalty"]

    # Merge on overlapping dates
    combined = pd.merge(trucks_subset, pumps_subset, on="day", how="outer").sort_values("day")
    combined["truck_cost"] = combined["truck_cost"].fillna(0)
    combined["pump_cost"] = combined["pump_cost"].fillna(0)
    combined["total_cost"] = combined["truck_cost"] + combined["pump_cost"]

    # Merge weather
    combined = pd.merge(combined, weather, on="day", how="left")

    # Total SLA penalties for the quarter
    total_sla = sf_penalties_data["penalty_amount"].sum()

    # KPIs
    total_all = combined["total_cost"].sum() + total_sla
    truck_total = combined["truck_cost"].sum()
    pump_total = combined["pump_cost"].sum()
    truck_pct = truck_total / total_all * 100 if total_all > 0 else 0
    pump_pct = pump_total / total_all * 100 if total_all > 0 else 0

    with st.container(horizontal=True):
        st.metric("Total cost of operations", f"${total_all:,.0f}", border=True)
        st.metric("Truck fuel", f"${truck_total:,.0f}", f"{truck_pct:.0f}% of total", border=True)
        st.metric("Pump energy", f"${pump_total:,.0f}", f"{pump_pct:.0f}% of total", border=True)
        st.metric("SLA penalties", f"${total_sla:,.0f}", f"{total_sla / total_all * 100:.0f}% of total" if total_all > 0 else "0%", border=True)

    # Stacked area chart
    with st.container(border=True):
        st.markdown("**Combined daily cost — trucks + pumps**")
        plot_df = combined[combined["total_cost"] > 0].copy()
        st.altair_chart(
            make_stacked_area(plot_df, "day", ["truck_cost", "pump_cost"], ["Truck fuel", "Pump energy"]),
            use_container_width=True,
        )

    # Weather overlay
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**Total cost vs temperature**")
            plot_w = combined.dropna(subset=["temp_f", "total_cost"])
            plot_w = plot_w[plot_w["total_cost"] > 0]
            if not plot_w.empty:
                base = alt.Chart(plot_w).encode(x=alt.X("day:T", title=None))
                cost_line = base.mark_line(color="#FF6B35", strokeWidth=2).encode(
                    y=alt.Y("total_cost:Q", title="Total cost ($)", axis=alt.Axis(titleColor="#FF6B35")),
                )
                temp_line = base.mark_line(color="#3498DB", strokeDash=[4, 4]).encode(
                    y=alt.Y("temp_f:Q", title="Temperature (°F)", axis=alt.Axis(titleColor="#3498DB")),
                )
                st.altair_chart(
                    alt.layer(cost_line, temp_line).resolve_scale(y="independent").properties(height=CHART_HEIGHT),
                    use_container_width=True,
                )

    with col2:
        with st.container(border=True):
            st.markdown("**Total cost vs wind speed**")
            if not plot_w.empty:
                base = alt.Chart(plot_w).encode(x=alt.X("day:T", title=None))
                cost_line = base.mark_line(color="#FF6B35", strokeWidth=2).encode(
                    y=alt.Y("total_cost:Q", title="Total cost ($)", axis=alt.Axis(titleColor="#FF6B35")),
                )
                wind_line = base.mark_line(color="#2ECC71", strokeDash=[4, 4]).encode(
                    y=alt.Y("wind_mph:Q", title="Wind (mph)", axis=alt.Axis(titleColor="#2ECC71")),
                )
                st.altair_chart(
                    alt.layer(cost_line, wind_line).resolve_scale(y="independent").properties(height=CHART_HEIGHT),
                    use_container_width=True,
                )

    # Monthly summary
    with st.container(border=True):
        st.markdown("**Monthly cost summary**")
        combined["month"] = combined["day"].dt.to_period("M").dt.to_timestamp()
        monthly = combined.groupby("month").agg(
            truck=("truck_cost", "sum"),
            pump=("pump_cost", "sum"),
            ops_total=("total_cost", "sum"),
        ).reset_index()
        monthly = pd.merge(monthly, sla_monthly.rename(columns={"day": "month"}), on="month", how="left")
        monthly["sla_penalty"] = monthly["sla_penalty"].fillna(0)
        monthly["total"] = monthly["ops_total"] + monthly["sla_penalty"]
        st.dataframe(
            monthly,
            use_container_width=True,
            hide_index=True,
            column_config={
                "month": st.column_config.DateColumn("Month", format="MMM YYYY"),
                "truck": st.column_config.NumberColumn("Truck cost", format="$%,.0f"),
                "pump": st.column_config.NumberColumn("Pump cost", format="$%,.0f"),
                "sla_penalty": st.column_config.NumberColumn("SLA penalties", format="$%,.0f"),
                "ops_total": st.column_config.NumberColumn("Ops subtotal", format="$%,.0f"),
                "total": st.column_config.NumberColumn("Total", format="$%,.0f"),
            },
        )

# =========================================================================
# TAB 4 — Energy market comparison
# =========================================================================
with tab_market:
    prices = load_energy_prices()
    pumps = load_pump_daily()

    st.info(
        ":material/info: Yes Energy data covers Jan 2024 – Jan 2026. "
        "AVEVA pump data is Jan – Apr 2026. Where dates overlap (January 2026), "
        "direct comparison is shown. Otherwise, the concept of market-price benchmarking is demonstrated.",
        icon=":material/info:",
    )

    # KPIs from energy prices
    recent_prices = prices.tail(30)
    avg_da = recent_prices["avg_day_ahead"].mean()
    max_da = prices["max_da"].max()
    avg_rt = recent_prices["avg_realtime"].mean()

    with st.container(horizontal=True):
        st.metric("Avg day-ahead (30d)", f"${avg_da:,.2f}/MWh", border=True)
        st.metric("Peak day-ahead (all time)", f"${max_da:,.2f}/MWh", border=True)
        st.metric("Avg real-time (30d)", f"${avg_rt:,.2f}/MWh", border=True)

    # Day-ahead vs real-time price chart
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**Day-ahead vs real-time price ($/MWh)**")
            st.altair_chart(
                make_line_chart(
                    prices.tail(365), "day",
                    ["avg_day_ahead", "avg_realtime"],
                    ["Day-ahead (DALMP)", "Real-time (RTLMP)"],
                ),
                use_container_width=True,
            )

    with col2:
        with st.container(border=True):
            st.markdown("**Price spread (DA - RT)**")
            spread_df = prices.tail(365).copy()
            spread_df["spread"] = spread_df["avg_day_ahead"] - spread_df["avg_realtime"]
            spread_chart = (
                alt.Chart(spread_df)
                .mark_bar()
                .encode(
                    x=alt.X("day:T", title=None),
                    y=alt.Y("spread:Q", title="Spread ($/MWh)"),
                    color=alt.condition(
                        alt.datum.spread > 0,
                        alt.value("#2ECC71"),
                        alt.value("#E74C3C"),
                    ),
                    tooltip=[
                        alt.Tooltip("day:T", format="%b %d, %Y"),
                        alt.Tooltip("spread:Q", format=",.2f"),
                    ],
                )
                .properties(height=CHART_HEIGHT)
            )
            st.altair_chart(spread_chart, use_container_width=True)

    # AVEVA pump cost vs market price — overlapping period
    with st.container(border=True):
        st.markdown("**AVEVA pump cost vs market price — January 2026 overlap**")
        pumps_jan = pumps[
            (pumps["day"] >= "2026-01-01") & (pumps["day"] < "2026-02-01")
        ].copy()
        pumps_jan["aveva_per_mwh"] = np.where(
            pumps_jan["daily_kwh"] > 0,
            pumps_jan["daily_cost"] / pumps_jan["daily_kwh"] * 1000,
            np.nan,
        )
        prices_jan = prices[
            (prices["day"] >= "2026-01-01") & (prices["day"] < "2026-02-01")
        ].copy()

        if not pumps_jan.empty and not prices_jan.empty:
            comparison = pd.merge(
                pumps_jan[["day", "aveva_per_mwh"]],
                prices_jan[["day", "avg_day_ahead"]],
                on="day",
                how="inner",
            )
            if not comparison.empty:
                st.altair_chart(
                    make_line_chart(
                        comparison, "day",
                        ["aveva_per_mwh", "avg_day_ahead"],
                        ["AVEVA actual ($/MWh)", "Market day-ahead ($/MWh)"],
                    ),
                    use_container_width=True,
                )
                avg_aveva = comparison["aveva_per_mwh"].mean()
                avg_market = comparison["avg_day_ahead"].mean()
                diff_pct = (avg_market - avg_aveva) / avg_aveva * 100 if avg_aveva > 0 else 0
                st.caption(
                    f"AVEVA avg: ${avg_aveva:,.2f}/MWh | "
                    f"Market avg: ${avg_market:,.2f}/MWh | "
                    f"Difference: {diff_pct:+.1f}%"
                )
            else:
                st.caption("No overlapping dates found for direct comparison.")
        else:
            st.caption("Insufficient data for January 2026 comparison.")

# =========================================================================
# TAB 5 — Customer revenue & SLA performance
# =========================================================================
with tab_customer:
    sf_contracts = load_sf_contract_performance()
    sf_daily = load_sf_daily_deliveries()
    sf_penalties = load_sf_penalties()
    sf_revenue = load_sf_revenue_by_account()

    # KPIs
    q1_revenue = sf_contracts["gross_revenue"].sum()
    total_penalties = sf_penalties["penalty_amount"].sum()
    overall_ontime = (
        sf_contracts["actual_ontime_pct"].mul(sf_contracts["total_deliveries"]).sum()
        / sf_contracts["total_deliveries"].sum()
    ) if sf_contracts["total_deliveries"].sum() > 0 else 0
    weather_penalty = sf_penalties.loc[
        sf_penalties["category"] == "WEATHER_DELAY", "penalty_amount"
    ].sum()

    with st.container(horizontal=True):
        st.metric("Q1 contract revenue", f"${q1_revenue:,.0f}", border=True)
        st.metric("SLA penalties", f"${total_penalties:,.0f}", border=True)
        st.metric("On-time delivery", f"{overall_ontime:.1f}%", border=True)
        st.metric(
            "Weather-driven penalties",
            f"${weather_penalty:,.0f}",
            delta=f"{weather_penalty / total_penalties * 100:.0f}% of total" if total_penalties > 0 else "0%",
            delta_color="inverse",
            border=True,
        )

    # Row 1 — Revenue by customer + Penalty breakdown
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**Revenue by customer**")
            rev_chart = (
                alt.Chart(sf_revenue)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                .encode(
                    x=alt.X("revenue:Q", title="Q1 Revenue ($)"),
                    y=alt.Y("account_name:N", sort="-x", title=None),
                    color=alt.Color(
                        "tier:N",
                        scale=alt.Scale(
                            domain=["Enterprise", "Strategic", "Growth"],
                            range=["#2563EB", "#7C3AED", "#059669"],
                        ),
                        title="Tier",
                    ),
                    tooltip=[
                        alt.Tooltip("account_name:N", title="Customer"),
                        alt.Tooltip("revenue:Q", format="$,.0f", title="Revenue"),
                        alt.Tooltip("total_penalties:Q", format="$,.0f", title="Penalties"),
                        alt.Tooltip("net_revenue:Q", format="$,.0f", title="Net revenue"),
                    ],
                )
                .properties(height=CHART_HEIGHT)
            )
            st.altair_chart(rev_chart, use_container_width=True)

    with col2:
        with st.container(border=True):
            st.markdown("**SLA penalty breakdown**")
            penalty_by_cat = sf_penalties.groupby("category", as_index=False)["penalty_amount"].sum()
            penalty_chart = (
                alt.Chart(penalty_by_cat)
                .mark_arc(innerRadius=60)
                .encode(
                    theta=alt.Theta("penalty_amount:Q"),
                    color=alt.Color(
                        "category:N",
                        scale=alt.Scale(
                            domain=["WEATHER_DELAY", "OPS_FAILURE", "SLA_BREACH"],
                            range=["#EF4444", "#F59E0B", "#6B7280"],
                        ),
                        title="Cause",
                    ),
                    tooltip=[
                        alt.Tooltip("category:N", title="Cause"),
                        alt.Tooltip("penalty_amount:Q", format="$,.0f", title="Penalty"),
                    ],
                )
                .properties(height=CHART_HEIGHT)
            )
            st.altair_chart(penalty_chart, use_container_width=True)

    # Row 2 — Daily on-time % + daily revenue trend
    col3, col4 = st.columns(2)
    with col3:
        with st.container(border=True):
            st.markdown("**Daily on-time delivery %**")
            weather_days = sf_daily[sf_daily["weather_delays"] > 0].copy()
            base_ontime = (
                alt.Chart(sf_daily)
                .mark_line(strokeWidth=2, color="#2563EB")
                .encode(
                    x=alt.X("day:T", title="Date"),
                    y=alt.Y("ontime_pct:Q", title="On-time %", scale=alt.Scale(domain=[0, 100])),
                    tooltip=[
                        alt.Tooltip("day:T", title="Date"),
                        alt.Tooltip("ontime_pct:Q", format=".1f", title="On-time %"),
                    ],
                )
            )
            weather_points = (
                alt.Chart(weather_days)
                .mark_point(size=60, color="#EF4444", filled=True)
                .encode(
                    x=alt.X("day:T"),
                    y=alt.Y("ontime_pct:Q"),
                    tooltip=[
                        alt.Tooltip("day:T", title="Date"),
                        alt.Tooltip("ontime_pct:Q", format=".1f", title="On-time %"),
                        alt.Tooltip("weather_delays:Q", title="Weather delays"),
                    ],
                )
            )
            threshold = (
                alt.Chart(pd.DataFrame({"y": [93]}))
                .mark_rule(strokeDash=[5, 5], color="#F59E0B")
                .encode(y="y:Q")
            )
            st.altair_chart(
                (base_ontime + weather_points + threshold).properties(height=CHART_HEIGHT),
                use_container_width=True,
            )
            st.caption(":red_circle: = weather-affected days  |  :orange_line: = avg SLA target (93%)")

    with col4:
        with st.container(border=True):
            st.markdown("**Daily contract revenue**")
            rev_line = (
                alt.Chart(sf_daily)
                .mark_area(
                    line={"color": "#059669", "strokeWidth": 2},
                    color=alt.Gradient(
                        gradient="linear",
                        stops=[
                            alt.GradientStop(color="#05966940", offset=0),
                            alt.GradientStop(color="#05966910", offset=1),
                        ],
                        x1=1, x2=1, y1=1, y2=0,
                    ),
                )
                .encode(
                    x=alt.X("day:T", title="Date"),
                    y=alt.Y("daily_revenue:Q", title="Revenue ($)"),
                    tooltip=[
                        alt.Tooltip("day:T", title="Date"),
                        alt.Tooltip("daily_revenue:Q", format="$,.0f", title="Revenue"),
                        alt.Tooltip("tonnage:Q", format=",.0f", title="Tonnage"),
                    ],
                )
                .properties(height=CHART_HEIGHT)
            )
            st.altair_chart(rev_line, use_container_width=True)

    # Contract performance table
    with st.container(border=True):
        st.markdown("**Contract performance — Q1 2026**")
        display_df = sf_contracts[[
            "account_name", "contract_name", "monthly_tonnage_commitment",
            "total_deliveries", "total_tonnage", "rate_per_tonne",
            "sla_target", "actual_ontime_pct", "gross_revenue",
        ]].copy()
        display_df.columns = [
            "Customer", "Contract", "Monthly commitment (t)",
            "Deliveries", "Tonnage delivered", "Rate ($/t)",
            "SLA target %", "Actual on-time %", "Gross revenue ($)",
        ]
        display_df["Gross revenue ($)"] = display_df["Gross revenue ($)"].apply(lambda x: f"${x:,.0f}")
        display_df["Rate ($/t)"] = display_df["Rate ($/t)"].apply(lambda x: f"${x:.2f}")
        display_df["Tonnage delivered"] = display_df["Tonnage delivered"].apply(lambda x: f"{x:,.0f}")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown(
        f"> *\"Salesforce CRM data shows **${total_penalties:,.0f}** in SLA penalties this quarter — "
        f"**{weather_penalty / total_penalties * 100:.0f}%** driven by weather events. "
        f"AVEVA + WeatherSource integration could have predicted and prevented "
        f"**${weather_penalty:,.0f}** in avoidable penalties.\"*"
    )

# =========================================================================
# TAB 6 — Weather cost multiplier analysis
# =========================================================================
with tab_weather:
    trucks = load_truck_daily()
    pumps = load_pump_daily()
    weather = load_weather_history()

    trucks["fuel_cost"] = trucks["total_fuel_lh"] * fuel_price

    # Join truck + weather
    tw = pd.merge(trucks, weather, on="day", how="inner")
    pw = pd.merge(pumps, weather, on="day", how="inner")

    st.markdown("### Correlation analysis")
    st.caption("How weather conditions drive operational costs")

    # Correlation values
    if not tw.empty:
        r_wind_fuel = calc_correlation(tw["wind_mph"], tw["avg_fuel_lh"])
        r_temp_fuel = calc_correlation(tw["temp_f"], tw["avg_fuel_lh"])
        r_temp_payload = calc_correlation(tw["temp_f"], tw["total_payload_t"])
    else:
        r_wind_fuel = r_temp_fuel = r_temp_payload = 0.0

    if not pw.empty:
        r_temp_pump_cost = calc_correlation(pw["temp_f"], pw["daily_cost"])
    else:
        r_temp_pump_cost = 0.0

    with st.container(horizontal=True):
        st.metric("Wind vs fuel rate", f"r = {r_wind_fuel:.2f}", border=True)
        st.metric("Temp vs fuel rate", f"r = {r_temp_fuel:.2f}", border=True)
        st.metric("Temp vs payload", f"r = {r_temp_payload:.2f}", border=True)
        st.metric("Temp vs pump cost", f"r = {r_temp_pump_cost:.2f}", border=True)

    # Scatter plots
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown(f"**Wind speed vs truck fuel rate** (r = {r_wind_fuel:.2f})")
            if not tw.empty:
                st.altair_chart(
                    make_scatter(tw, "wind_mph", "avg_fuel_lh", "Wind (mph)", "Fuel rate (l/h)"),
                    use_container_width=True,
                )

    with col2:
        with st.container(border=True):
            st.markdown(f"**Temperature vs truck fuel rate** (r = {r_temp_fuel:.2f})")
            if not tw.empty:
                st.altair_chart(
                    make_scatter(tw, "temp_f", "avg_fuel_lh", "Temperature (°F)", "Fuel rate (l/h)"),
                    use_container_width=True,
                )

    col3, col4 = st.columns(2)
    with col3:
        with st.container(border=True):
            st.markdown(f"**Temperature vs payload** (r = {r_temp_payload:.2f})")
            if not tw.empty:
                st.altair_chart(
                    make_scatter(tw, "temp_f", "total_payload_t", "Temperature (°F)", "Payload (t)"),
                    use_container_width=True,
                )

    with col4:
        with st.container(border=True):
            st.markdown(f"**Temperature vs pump energy cost** (r = {r_temp_pump_cost:.2f})")
            if not pw.empty:
                st.altair_chart(
                    make_scatter(pw, "temp_f", "daily_cost", "Temperature (°F)", "Daily cost ($)"),
                    use_container_width=True,
                )

    # Weather cost multiplier table
    with st.container(border=True):
        st.markdown("**Weather cost multiplier matrix**")
        if not tw.empty and len(tw) >= 5:
            tw["wind_bin"] = pd.cut(tw["wind_mph"], bins=5, precision=0)
            tw["temp_bin"] = pd.cut(tw["temp_f"], bins=5, precision=0)
            wind_impact = tw.groupby("wind_bin", observed=True)["fuel_cost"].mean().reset_index()
            wind_impact.columns = ["Wind range (mph)", "Avg daily fuel cost ($)"]
            wind_impact["Avg daily fuel cost ($)"] = wind_impact["Avg daily fuel cost ($)"].map(lambda x: f"${x:,.0f}")
            st.dataframe(wind_impact, use_container_width=True, hide_index=True)
        else:
            st.caption("Insufficient data for multiplier analysis.")

# =========================================================================
# TAB 7 — Digital twin & predictive maintenance
# =========================================================================
with tab_twin:
    positions = load_truck_latest_positions()
    health_raw = load_truck_health_snapshot()

    # Compute health scores
    health_scores = compute_health_scores(health_raw)

    st.markdown("### :material/precision_manufacturing: Fleet digital twin")
    st.caption(
        "Replay truck movements across the mine site. Drag the time slider to watch "
        "the fleet move through a full shift. Health scores from AVEVA sensors detect "
        "failures before they happen."
    )

    # KPI row
    fleet_size = len(positions)
    active_trucks = len(positions[positions["speed_kmh"] > 1]) if "speed_kmh" in positions.columns else fleet_size
    avg_load = positions["engine_load"].mean() if "engine_load" in positions.columns else 0
    critical_count = len(health_scores[health_scores["status"] == "Critical"]) if not health_scores.empty else 0
    warning_count = len(health_scores[health_scores["status"] == "Warning"]) if not health_scores.empty else 0
    avg_health = health_scores["health_score"].mean() if not health_scores.empty else 100

    with st.container(horizontal=True):
        st.metric("Fleet size", f"{fleet_size} trucks", f"{active_trucks} active", border=True)
        st.metric("Avg engine load", f"{avg_load:.0f}%", border=True)
        st.metric("Fleet health", f"{avg_health:.0f}/100", border=True)
        st.metric(
            "Alerts",
            f"{critical_count + warning_count}",
            f"{critical_count} critical, {warning_count} warning",
            delta_color="inverse" if critical_count > 0 else "normal",
            border=True,
        )

    # --- Fleet replay map ---
    with st.container(border=True):
        st.markdown("**Fleet replay — drag the slider to move trucks through the day**")
        col_date, col_time = st.columns([1, 3])
        with col_date:
            replay_date = st.date_input(
                "Date", value=date(2026, 3, 31),
                min_value=date(2026, 1, 1), max_value=date(2026, 3, 31),
                key="twin_replay_date",
            )
        with col_time:
            hour_val = st.slider(
                "Time of day",
                min_value=0.0, max_value=23.5, value=12.0, step=0.5,
                format="%.1f h",
                key="twin_time_slider",
            )

        # Load all GPS for this day
        day_gps = load_fleet_day_gps(str(replay_date))

        if not day_gps.empty:
            # For each truck, find the reading closest to the selected hour
            current_positions = []
            trail_data = []
            for truck_name in day_gps["truck"].unique():
                truck_df = day_gps[day_gps["truck"] == truck_name].sort_values("hour_frac")
                # Readings up to the selected time (for trail)
                past = truck_df[truck_df["hour_frac"] <= hour_val]
                if past.empty:
                    # Use first reading if slider is before first data point
                    past = truck_df.head(1)
                # Current position = last reading before slider time
                curr = past.iloc[-1]
                # Health info
                h_row = health_scores[health_scores["truck"] == truck_name]
                status = h_row.iloc[0]["status"] if not h_row.empty else "Healthy"
                h_score = h_row.iloc[0]["health_score"] if not h_row.empty else 100
                speed = curr.get("speed_kmh", 0) or 0
                payload = curr.get("payload_t", 0) or 0

                current_positions.append({
                    "truck": truck_name,
                    "lat": curr["lat"],
                    "lon": curr["lon"],
                    "speed_kmh": speed,
                    "payload_t": payload,
                    "status": status,
                    "health_score": h_score,
                    "color_r": {"Healthy": 34, "Warning": 245, "Critical": 239}.get(status, 34),
                    "color_g": {"Healthy": 197, "Warning": 158, "Critical": 68}.get(status, 197),
                    "color_b": {"Healthy": 94, "Warning": 11, "Critical": 68}.get(status, 94),
                })

                # Build trail from all past positions (up to slider time)
                if len(past) >= 2:
                    trail_coords = list(zip(past["lon"].tolist(), past["lat"].tolist()))
                    trail_color = {"Healthy": [34, 197, 94, 80], "Warning": [245, 158, 11, 80], "Critical": [239, 68, 68, 80]}.get(status, [34, 197, 94, 80])
                    trail_data.append({
                        "path": trail_coords,
                        "color": trail_color,
                    })

            pos_df = pd.DataFrame(current_positions)

            # Pydeck layers
            scatter = pdk.Layer(
                "ScatterplotLayer",
                data=pos_df,
                get_position=["lon", "lat"],
                get_radius=600,
                get_fill_color=["color_r", "color_g", "color_b", 220],
                pickable=True,
                auto_highlight=True,
            )
            text_layer = pdk.Layer(
                "TextLayer",
                data=pos_df,
                get_position=["lon", "lat"],
                get_text="truck",
                get_size=13,
                get_color=[255, 255, 255],
                get_angle=0,
                get_text_anchor='"middle"',
                get_alignment_baseline='"bottom"',
                get_pixel_offset=[0, -18],
            )

            trail_layers = []
            for t in trail_data:
                trail_layers.append(pdk.Layer(
                    "PathLayer",
                    data=pd.DataFrame({"path": [t["path"]]}),
                    get_path="path",
                    get_color=t["color"],
                    width_min_pixels=2,
                    get_width=3,
                ))

            center_lat = pos_df["lat"].mean()
            center_lon = pos_df["lon"].mean()

            view = pdk.ViewState(
                latitude=center_lat, longitude=center_lon,
                zoom=4.5, pitch=0,
            )
            deck = pdk.Deck(
                layers=[scatter, text_layer] + trail_layers,
                initial_view_state=view,
                map_style="mapbox://styles/mapbox/dark-v10",
                tooltip={
                    "text": "{truck}\nSpeed: {speed_kmh:.0f} km/h\nPayload: {payload_t:.0f} t\nHealth: {health_score:.0f}/100\nStatus: {status}",
                },
            )
            st.pydeck_chart(deck)

            # Time indicator
            hour_int = int(hour_val)
            minute_int = int((hour_val % 1) * 60)
            moving = len(pos_df[pos_df["speed_kmh"] > 1])
            st.caption(
                f":clock{hour_int % 12 or 12}: **{hour_int:02d}:{minute_int:02d}** — "
                f"{moving}/{len(pos_df)} trucks in motion  |  "
                ":green_circle: Healthy  |  :large_orange_circle: Warning  |  "
                ":red_circle: Critical  |  Lines = route trail"
            )
        else:
            st.warning("No GPS data available for this date.")

    # Health table + Sensor trends in columns
    col_health, col_select = st.columns([3, 2])

    with col_health:
        with st.container(border=True):
            st.markdown("**Fleet health scores**")
            if not health_scores.empty:
                display_health = health_scores[[
                    "truck", "health_score", "status", "top_risk", "days_to_maintenance"
                ]].copy()
                display_health.columns = ["Truck", "Health", "Status", "Top risk", "Days to maint."]
                st.dataframe(
                    display_health,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Health": st.column_config.ProgressColumn(
                            "Health",
                            min_value=0,
                            max_value=100,
                            format="%.0f",
                        ),
                    },
                )

    # Sensor trend charts
    st.markdown("---")
    truck_list = sorted(positions["truck"].unique()) if not positions.empty else ["Truck 101"]
    selected_truck = st.selectbox("Select truck for sensor detail", truck_list, key="twin_truck_select")

    trends = load_truck_sensor_trends(selected_truck)

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        with st.container(border=True):
            st.markdown(f"**{selected_truck} — Engine coolant & oil pressure (7 days)**")
            if not trends.empty:
                coolant = trends[trends["field"] == "Engine Coolant Temperature Value °C"].copy()
                oil = trends[trends["field"] == "Engine Oil Pressure Value psi"].copy()
                if not coolant.empty:
                    # Coolant chart with normal range band
                    band = pd.DataFrame({"y": [88.5], "y2": [91.5]})
                    normal_band = alt.Chart(band).mark_rect(color="#22C55E", opacity=0.15).encode(
                        y="y:Q", y2="y2:Q"
                    )
                    warn_line = alt.Chart(pd.DataFrame({"y": [95]})).mark_rule(
                        strokeDash=[5, 5], color="#EF4444"
                    ).encode(y="y:Q")
                    coolant_line = alt.Chart(coolant).mark_line(
                        color="#FF6B35", strokeWidth=2
                    ).encode(
                        x=alt.X("hour:T", title="Time"),
                        y=alt.Y("avg_val:Q", title="Coolant temp (°C)", scale=alt.Scale(domain=[85, 98])),
                        tooltip=[
                            alt.Tooltip("hour:T", title="Time"),
                            alt.Tooltip("avg_val:Q", format=".1f", title="Avg °C"),
                            alt.Tooltip("max_val:Q", format=".1f", title="Max °C"),
                        ],
                    )
                    st.altair_chart(
                        (normal_band + warn_line + coolant_line).properties(height=250),
                        use_container_width=True,
                    )
                    st.caption(":green_square: Normal (88.5–91.5°C)  |  :red_dash: Warning threshold (95°C)")

    with col_t2:
        with st.container(border=True):
            st.markdown(f"**{selected_truck} — Exhaust temperature L/R delta (7 days)**")
            if not trends.empty:
                left_ex = trends[trends["field"] == "Left Exhaust Temperature Value °C"].copy()
                right_ex = trends[trends["field"] == "Right Exhaust Temperature Value °C"].copy()
                if not left_ex.empty and not right_ex.empty:
                    merged_ex = left_ex[["hour", "avg_val"]].rename(columns={"avg_val": "left"}).merge(
                        right_ex[["hour", "avg_val"]].rename(columns={"avg_val": "right"}),
                        on="hour",
                    )
                    merged_ex["delta"] = (merged_ex["left"] - merged_ex["right"]).abs()
                    warn_delta = alt.Chart(pd.DataFrame({"y": [20]})).mark_rule(
                        strokeDash=[5, 5], color="#F59E0B"
                    ).encode(y="y:Q")
                    delta_line = alt.Chart(merged_ex).mark_area(
                        line={"color": "#7C3AED", "strokeWidth": 2},
                        color=alt.Gradient(
                            gradient="linear",
                            stops=[
                                alt.GradientStop(color="#7C3AED40", offset=0),
                                alt.GradientStop(color="#7C3AED10", offset=1),
                            ],
                            x1=1, x2=1, y1=1, y2=0,
                        ),
                    ).encode(
                        x=alt.X("hour:T", title="Time"),
                        y=alt.Y("delta:Q", title="L/R delta (°C)"),
                        tooltip=[
                            alt.Tooltip("hour:T", title="Time"),
                            alt.Tooltip("delta:Q", format=".1f", title="Delta °C"),
                            alt.Tooltip("left:Q", format=".1f", title="Left °C"),
                            alt.Tooltip("right:Q", format=".1f", title="Right °C"),
                        ],
                    )
                    st.altair_chart(
                        (warn_delta + delta_line).properties(height=250),
                        use_container_width=True,
                    )
                    st.caption(":large_orange_diamond: Warning if delta > 20°C (turbo/manifold asymmetry)")

    # AI predictive maintenance
    st.markdown("---")
    st.markdown("#### :material/smart_toy: AI failure prediction")

    worst_truck = health_scores.iloc[0] if not health_scores.empty else None
    if worst_truck is not None:
        # Build sensor summary for worst truck
        worst_data = health_raw[health_raw["truck"] == worst_truck["truck"]]
        sensor_summary = ""
        for _, row in worst_data.iterrows():
            sensor_summary += f"  - {row['field']}: avg={row['avg_val']:.1f}, max={row['max_val']:.1f}, std={row['std_val']:.2f}\n"

        predict_context = f"""You are a predictive maintenance AI for mining haul trucks. Analyze the sensor data below for {worst_truck['truck']} and predict potential failures.

TRUCK: {worst_truck['truck']}
HEALTH SCORE: {worst_truck['health_score']}/100 (status: {worst_truck['status']})
TOP RISK FACTOR: {worst_truck['top_risk']} (z-score: {worst_truck['risk_z']})
ESTIMATED DAYS TO MAINTENANCE: {worst_truck['days_to_maintenance']}

LAST 24H SENSOR DATA:
{sensor_summary}

NORMAL OPERATING RANGES:
- Engine Coolant: 88.5–91.5°C (warning >95°C)
- Engine Oil Pressure: 435–465 psi
- Exhaust Temperature: 430–510°C (L/R delta <20°C normal)
- Brake Temperature: 65–85°C (warning >100°C)
- Exhaust Temp Delta (engine load adjusted): 37–43°C

MAINTENANCE COST DATA:
- Unplanned breakdown: $45,000–$85,000 (includes tow, repair, lost production)
- Preventive maintenance: $5,000–$12,000
- Average downtime: 2–5 days unplanned, 4–8 hours planned

Provide:
1. Failure probability (%) and confidence level
2. Most likely failure mode and affected component
3. Estimated time to failure (days)
4. Recommended preventive action with estimated cost
5. Cost of inaction (if failure occurs)
Keep it concise and actionable."""

        st.info(
            f":material/warning: **{worst_truck['truck']}** has the lowest health score "
            f"({worst_truck['health_score']}/100) — top risk: {worst_truck['top_risk']}"
        )

        if st.button(f":material/smart_toy: Predict failures for {worst_truck['truck']}", type="primary", key="predict_btn"):
            with st.spinner(f"Analyzing {worst_truck['truck']} sensor data..."):
                ai_prediction = cortex_chat([
                    {"role": "system", "content": predict_context},
                    {"role": "user", "content": f"Analyze {worst_truck['truck']} and predict failures. What should we do this week?"},
                ])
            with st.container(border=True):
                st.markdown(f"**Predictive maintenance — {worst_truck['truck']}**")
                st.markdown(ai_prediction)

    st.caption(
        "Health scores computed from real-time AVEVA sensor z-scores. "
        "AI predictions powered by Snowflake Cortex (mistral-large2)."
    )

# =========================================================================
# TAB 8 — Cortex AI optimization
# =========================================================================
with tab_ai:
    forecast = load_weather_forecast()
    trucks = load_truck_daily()
    pumps = load_pump_daily()
    sf_penalties_data = load_sf_penalties()
    sf_contracts = load_sf_contract_performance()

    st.markdown("### :material/smart_toy: AI operations optimizer")
    st.caption(
        "Cortex AI analyzes weather, fleet metrics, energy prices, and customer SLAs. "
        "Click below or ask follow-up questions."
    )

    # Show forecast in collapsible expander
    with st.expander("Calgary 7-day weather forecast", expanded=False):
        if not forecast.empty:
            st.dataframe(
                forecast,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "day": st.column_config.DateColumn("Date", format="ddd, MMM DD"),
                    "temp_f": st.column_config.NumberColumn("Temp (°F)", format="%.1f"),
                    "wind_mph": st.column_config.NumberColumn("Wind (mph)", format="%.1f"),
                    "precip_pct": st.column_config.NumberColumn("Precip %", format="%.0f"),
                },
            )

    # Build operational context (shared by button and chat)
    trucks["fuel_cost"] = trucks["total_fuel_lh"] * fuel_price
    avg_daily_truck_cost = trucks["fuel_cost"].mean()
    avg_daily_pump_cost = pumps["daily_cost"].mean() if not pumps.empty else 0
    total_daily = avg_daily_truck_cost + avg_daily_pump_cost
    total_sla_penalties = sf_penalties_data["penalty_amount"].sum()
    weather_penalties = sf_penalties_data.loc[
        sf_penalties_data["category"] == "WEATHER_DELAY", "penalty_amount"
    ].sum()
    avg_sla_target = sf_contracts["sla_target"].mean() if not sf_contracts.empty else 93
    n_contracts = len(sf_contracts)

    forecast_text = ""
    if not forecast.empty:
        for _, r in forecast.head(7).iterrows():
            forecast_text += (
                f"  {r['day'].strftime('%a %b %d')}: "
                f"Temp {r['temp_f']:.0f}°F, Wind {r['wind_mph']:.1f} mph"
            )
            if pd.notna(r.get("precip_pct")):
                forecast_text += f", Precip {r['precip_pct']:.0f}%"
            forecast_text += "\n"

    # Top-performing and worst contracts for richer context
    top_contracts = ""
    if not sf_contracts.empty:
        for _, c in sf_contracts.head(5).iterrows():
            top_contracts += (
                f"  - {c['contract_name']}: {c['actual_ontime_pct']:.1f}% on-time "
                f"(target {c['sla_target']:.0f}%), ${c['gross_revenue']:,.0f} revenue\n"
            )

    system_context = f"""You are an industrial operations cost optimizer for a mining and water utility in Calgary, Alberta. Answer concisely with specific numbers. Use markdown tables when appropriate. No introductions, caveats, or disclaimers — just actionable intelligence.

FLEET: 10 mining trucks, avg daily fuel ${avg_daily_truck_cost:,.0f} at ${fuel_price}/L. 25 water pumps, avg daily energy ${avg_daily_pump_cost:,.0f}. Combined ${total_daily:,.0f}/day.

CUSTOMER SLAs: {n_contracts} contracts, 8 customers. Avg SLA target {avg_sla_target:.0f}% on-time. Q1 penalties ${total_sla_penalties:,.0f} (${weather_penalties:,.0f} weather-driven = 87%). Each late delivery = $1K-$3K penalty.

TOP CONTRACTS:
{top_contracts}

WEATHER CORRELATIONS: Wind>10mph or Temp<15°F = high delay risk. Wind↔fuel r=0.51, Temp↔fuel r=0.49, Temp↔payload r=-0.31.

7-DAY FORECAST:
{forecast_text}

DATA SOURCES: AVEVA Connect (trucks+pumps), Snowflake Marketplace (WeatherSource, Yes Energy), Salesforce CRM."""

    # Initialize chat history in session state
    if "ai_chat_messages" not in st.session_state:
        st.session_state.ai_chat_messages = []

    # Quick-start button
    optimization_prompt = """Generate a 7-day operations schedule. Format as a single markdown table:

| Day | Weather Risk | SLA Risk | Trucks | Pump Adj | Est. Cost | Net Savings |

After the table, add:
- **Total weekly savings** vs baseline (one line)
- **Top action item** for the week (one line)

Keep it tight — no paragraph explanations. Use :green_circle: :orange_circle: :red_circle: for risk levels."""

    if st.button(":material/smart_toy: Generate 7-day optimization plan", type="primary"):
        # Add as a user message and generate response
        st.session_state.ai_chat_messages.append(
            {"role": "user", "content": "Generate a 7-day optimization plan for our operations."}
        )
        ai_text = cortex_chat([
            {"role": "system", "content": system_context},
            {"role": "user", "content": optimization_prompt},
        ])
        st.session_state.ai_chat_messages.append(
            {"role": "assistant", "content": ai_text}
        )
        st.rerun()

    # Display chat history
    for msg in st.session_state.ai_chat_messages:
        with st.chat_message(msg["role"], avatar=":material/smart_toy:" if msg["role"] == "assistant" else ":material/person:"):
            st.markdown(msg["content"])

    # Chat input for follow-up questions
    if user_question := st.chat_input("Ask about operations, costs, weather impact, SLA risks..."):
        # Show user message immediately
        st.session_state.ai_chat_messages.append(
            {"role": "user", "content": user_question}
        )
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown(user_question)

        # Build conversation for Cortex (system + last 10 messages for context window)
        conv_messages = [{"role": "system", "content": system_context}]
        for m in st.session_state.ai_chat_messages[-10:]:
            conv_messages.append({"role": m["role"], "content": m["content"]})

        with st.chat_message("assistant", avatar=":material/smart_toy:"):
            with st.spinner("Thinking..."):
                ai_text = cortex_chat(conv_messages)
                st.markdown(ai_text)

        st.session_state.ai_chat_messages.append(
            {"role": "assistant", "content": ai_text}
        )

    # Suggested questions
    if not st.session_state.ai_chat_messages:
        st.markdown("**Suggested questions:**")
        suggestions = [
            "Which contracts are most at risk of SLA breach this week?",
            "How much could we save by reducing truck fleet on high-wind days?",
            "What's the cost impact if we shift pump operations to off-peak hours?",
            "Compare Suncor vs Teck contract profitability after SLA penalties",
            "What weather conditions should trigger a proactive customer notification?",
        ]
        for s in suggestions:
            st.caption(f"- *{s}*")

    # Clear chat button
    if st.session_state.ai_chat_messages:
        if st.button(":material/delete: Clear conversation", type="secondary"):
            st.session_state.ai_chat_messages = []
            st.rerun()

    st.caption(
        "Powered by Snowflake Cortex AI (mistral-large2) — "
        "AVEVA telemetry · WeatherSource · Yes Energy · Salesforce CRM"
    )

# =========================================================================
# TAB 7 — Savings calculator
# =========================================================================
with tab_savings:
    trucks = load_truck_daily()
    pumps = load_pump_daily()
    weather = load_weather_history()
    sf_penalties_data = load_sf_penalties()

    trucks["fuel_cost"] = trucks["total_fuel_lh"] * fuel_price

    st.markdown("### :material/savings: Interactive savings calculator")
    st.caption(
        "Adjust operational thresholds to see projected quarterly savings. "
        "The model calculates cost avoidance from weather-aware scheduling "
        "and SLA penalty prevention."
    )

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

    # Truck savings: days where wind > threshold or temp < threshold
    if not tw.empty:
        bad_truck_days = tw[
            (tw["wind_mph"] > wind_threshold) | (tw["temp_f"] < temp_low_threshold)
        ]
        truck_baseline = tw["fuel_cost"].sum()
        truck_savings = bad_truck_days["fuel_cost"].sum() * (truck_reduction / 100)
        truck_bad_day_count = len(bad_truck_days)
    else:
        truck_baseline = truck_savings = 0
        truck_bad_day_count = 0

    # Pump savings: reduce on high-cost days (above median)
    if not pw.empty:
        pump_median = pw["daily_cost"].median()
        high_cost_pump_days = pw[pw["daily_cost"] > pump_median * 1.2]
        pump_baseline = pw["daily_cost"].sum()
        pump_savings = high_cost_pump_days["daily_cost"].sum() * (pump_reduction / 100)
        pump_high_days = len(high_cost_pump_days)
    else:
        pump_baseline = pump_savings = 0
        pump_high_days = 0

    # SLA penalty avoidance
    weather_sla_penalties = sf_penalties_data.loc[
        sf_penalties_data["category"] == "WEATHER_DELAY", "penalty_amount"
    ].sum()
    sla_savings = weather_sla_penalties * (sla_prevention / 100)

    total_savings = truck_savings + pump_savings + sla_savings
    total_baseline = truck_baseline + pump_baseline + weather_sla_penalties
    savings_pct = total_savings / total_baseline * 100 if total_baseline > 0 else 0

    # Quarterly projection (scale to 90 days)
    data_days = max(len(tw), len(pw), 1)
    quarterly_factor = 90 / data_days
    quarterly_truck_savings = truck_savings * quarterly_factor
    quarterly_pump_savings = pump_savings * quarterly_factor
    quarterly_sla_savings = sla_savings  # already quarterly (Q1 data)
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
                color=alt.Color(
                    "source:N",
                    scale=alt.Scale(range=["#FF6B35", "#4ECDC4", "#7C3AED"]),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("source:N", title="Source"),
                    alt.Tooltip("savings:Q", format="$,.0f", title="Savings"),
                ],
            )
            .properties(height=250),
            use_container_width=True,
        )

    st.markdown(
        f"> *\"AVEVA tracks what you consume. Snowflake Marketplace tells you what it costs "
        f"in the market and what weather is doing to drive it. Salesforce shows the customer impact. Together: "
        f"**${quarterly_savings:,.0f} quarterly savings identified** — including **${quarterly_sla_savings:,.0f}** "
        f"in avoidable SLA penalties.\"*"
    )

# =============================================================================
# Footer
# =============================================================================

st.markdown("---")
st.caption(
    ":material/factory: Powered by AVEVA operational data  |  "
    ":material/storefront: Snowflake Marketplace (WeatherSource + Yes Energy)  |  "
    ":material/handshake: Salesforce CRM  |  "
    ":material/smart_toy: Snowflake Cortex AI"
)
