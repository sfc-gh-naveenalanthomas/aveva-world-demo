/*
 * Weather-Aware Fleet Operations Dashboard — Snowflake Setup
 * 
 * Prerequisites:
 *   1. AVEVA Connect Catalog Integration configured with mining truck data
 *      Database: CONNECT_AWC26  (or AVEVA_CLD_DATA on some accounts)
 *      Schema:   "f6dd054e-d7b7-4b48-97f3-1b0eb2e91ab0"
 *      Table:    mining_haul_truck_narrow_live  (3.7M+ rows, 10 trucks, 33 sensors)
 *      Setup:    Attach the AVEVA CLD via Snowflake Catalog Integration.
 *      NOTE:     If your CLD database is named differently, search-replace
 *               CONNECT_AWC26 with your database name in this script.
 *   2. WeatherSource "Global Weather & Climate Data for BI" from Snowflake Marketplace
 *      Database: GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI
 *      Schema:   PWS_BI_SAMPLE
 *      Tables:   POINT_HISTORY_DAY, POINT_FORECAST_DAY
 *   3. ACCOUNTADMIN or a role with CREATE DATABASE, CREATE WAREHOUSE privileges
 *   4. Cortex AI enabled on the account (mistral-large2 model)
 *
 * Usage:
 *   1. Update the AVEVA CLD schema ID below if yours differs
 *   2. Update the CITY variable if your mine site is not in Calgary
 *   3. Run this script in a Snowflake worksheet or via SnowSQL
 *   4. Deploy the Streamlit app with:
 *        snow streamlit deploy --replace --connection <your_connection>
 */

-- ============================================================================
-- 1. Create database, schema, and warehouse
-- ============================================================================
CREATE DATABASE IF NOT EXISTS AVEVA_FLEET_OPS;
CREATE SCHEMA IF NOT EXISTS AVEVA_FLEET_OPS.STREAMLIT;

CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH
  WITH WAREHOUSE_SIZE = 'MEDIUM'
  AUTO_SUSPEND = 300
  AUTO_RESUME = TRUE;

USE DATABASE AVEVA_FLEET_OPS;
USE SCHEMA STREAMLIT;
USE WAREHOUSE COMPUTE_WH;

-- ============================================================================
-- 2. Create pivoted view of narrow IoT data
--    
--    The AVEVA CLD data arrives in narrow/unpivoted format:
--      "Timestamp", "Name" (truck), "Field" (sensor), "Value" (reading)
--    
--    This view pivots it into one row per truck per hour with named columns.
--    
--    >>> UPDATE the FROM clause to match your AVEVA CLD schema ID <<<
-- ============================================================================
CREATE OR REPLACE VIEW AVEVA_FLEET_OPS.STREAMLIT.TRUCK_DATA_PIVOTED AS
WITH hourly AS (
    SELECT
        "Name" AS TRUCK,
        DATE_TRUNC('hour', "Timestamp") AS HOUR_TS,
        "Field",
        AVG("Value") AS AVG_VAL
    -- >>> CHANGE THIS TABLE REFERENCE to your AVEVA CLD table <<<
    FROM CONNECT_AWC26."f6dd054e-d7b7-4b48-97f3-1b0eb2e91ab0".mining_haul_truck_narrow_live
    GROUP BY "Name", DATE_TRUNC('hour', "Timestamp"), "Field"
)
SELECT
    TRUCK,
    HOUR_TS AS TIMESTAMP,
    DATE_TRUNC('day', HOUR_TS) AS DATE,
    DAYNAME(HOUR_TS) AS DAY_OF_WEEK,
    HOUR(HOUR_TS) AS HOUR_OF_DAY,
    ROUND(MAX(CASE WHEN "Field" = 'Engine Fuel Rate Value l/h' THEN AVG_VAL END), 2) AS FUEL_RATE_LPH,
    ROUND(MAX(CASE WHEN "Field" = 'Shift Payload Total Value t' THEN AVG_VAL END), 2) AS SHIFT_PAYLOAD_T,
    ROUND(MAX(CASE WHEN "Field" = 'Payload Value t' THEN AVG_VAL END), 2) AS PAYLOAD_T,
    ROUND(MAX(CASE WHEN "Field" = 'Ground Speed Value km/h' THEN AVG_VAL END), 2) AS GROUND_SPEED_KMH,
    ROUND(MAX(CASE WHEN "Field" = 'Engine Coolant Temperature Value °C' THEN AVG_VAL END), 2) AS COOLANT_TEMP_C,
    ROUND(MAX(CASE WHEN "Field" = 'Engine Oil Pressure Value psi' THEN AVG_VAL END), 2) AS OIL_PRESSURE_PSI,
    ROUND(MAX(CASE WHEN "Field" = 'Engine Load Value %' THEN AVG_VAL END), 2) AS ENGINE_LOAD_PCT,
    ROUND(MAX(CASE WHEN "Field" = 'Engine RPM Value rpm' THEN AVG_VAL END), 2) AS ENGINE_RPM,
    ROUND(MAX(CASE WHEN "Field" = 'Left Exhaust Temperature Value °C' THEN AVG_VAL END), 2) AS LEFT_EXHAUST_TEMP_C,
    ROUND(MAX(CASE WHEN "Field" = 'Right Exhaust Temperature Value °C' THEN AVG_VAL END), 2) AS RIGHT_EXHAUST_TEMP_C,
    ROUND(MAX(CASE WHEN "Field" = 'Aftercooler Temperature Value °C' THEN AVG_VAL END), 2) AS AFTERCOOLER_TEMP_C,
    ROUND(MAX(CASE WHEN "Field" = 'Boost Pressure Value' THEN AVG_VAL END), 2) AS BOOST_PRESSURE,
    ROUND(MAX(CASE WHEN "Field" = 'Left Front Suspension Cylinder Value kPa' THEN AVG_VAL END), 2) AS LEFT_FRONT_SUSPENSION_KPA,
    ROUND(MAX(CASE WHEN "Field" = 'Right Front Suspension Cylinder Value kPa' THEN AVG_VAL END), 2) AS RIGHT_FRONT_SUSPENSION_KPA,
    ROUND(MAX(CASE WHEN "Field" = 'Left Rear Suspension Cylinder Value kPa' THEN AVG_VAL END), 2) AS LEFT_REAR_SUSPENSION_KPA,
    ROUND(MAX(CASE WHEN "Field" = 'Right Rear Suspension Cylinder Value kPa' THEN AVG_VAL END), 2) AS RIGHT_REAR_SUSPENSION_KPA,
    ROUND(MAX(CASE WHEN "Field" = 'Suspension Delta Front Cylinders Value kPa' THEN AVG_VAL END), 2) AS SUSPENSION_DELTA_FRONT_KPA,
    ROUND(MAX(CASE WHEN "Field" = 'Suspension Delta Rear Cylinders Value kPa' THEN AVG_VAL END), 2) AS SUSPENSION_DELTA_REAR_KPA,
    ROUND(MAX(CASE WHEN "Field" = 'Left Front Brake Temperature Value °C' THEN AVG_VAL END), 2) AS LEFT_FRONT_BRAKE_TEMP_C,
    ROUND(MAX(CASE WHEN "Field" = 'Right Front Brake Temperature Value °C' THEN AVG_VAL END), 2) AS RIGHT_FRONT_BRAKE_TEMP_C,
    ROUND(MAX(CASE WHEN "Field" = 'Left Rear Brake Temperature Value °C' THEN AVG_VAL END), 2) AS LEFT_REAR_BRAKE_TEMP_C,
    ROUND(MAX(CASE WHEN "Field" = 'Right Rear Brake Temperature Value °C' THEN AVG_VAL END), 2) AS RIGHT_REAR_BRAKE_TEMP_C,
    ROUND(MAX(CASE WHEN "Field" = 'Latitude Value °' THEN AVG_VAL END), 6) AS LATITUDE,
    ROUND(MAX(CASE WHEN "Field" = 'Longitude Value °' THEN AVG_VAL END), 6) AS LONGITUDE
FROM hourly
GROUP BY TRUCK, HOUR_TS;

-- Verify the view
SELECT COUNT(*) AS row_count, COUNT(FUEL_RATE_LPH) AS fuel_rows FROM AVEVA_FLEET_OPS.STREAMLIT.TRUCK_DATA_PIVOTED;

-- ============================================================================
-- 3. Create Semantic View for Cortex Analyst / Agent
-- ============================================================================
CREATE OR REPLACE SEMANTIC VIEW AVEVA_FLEET_OPS.STREAMLIT.FLEET_SEMANTIC_VIEW
    TABLES (
        AVEVA_FLEET_OPS.STREAMLIT.TRUCK_DATA_PIVOTED
            COMMENT='Hourly aggregated sensor readings for 10 mining haul trucks (Truck 101 - Truck 110).'
    )
    FACTS (
        TRUCK_DATA_PIVOTED.FUEL_RATE_LPH AS FUEL_RATE_LPH COMMENT='Engine fuel consumption rate in liters per hour.',
        TRUCK_DATA_PIVOTED.SHIFT_PAYLOAD_T AS SHIFT_PAYLOAD_T COMMENT='Cumulative payload in metric tonnes.',
        TRUCK_DATA_PIVOTED.PAYLOAD_T AS PAYLOAD_T COMMENT='Current load weight in metric tonnes.',
        TRUCK_DATA_PIVOTED.GROUND_SPEED_KMH AS GROUND_SPEED_KMH COMMENT='Travel speed in km/h.',
        TRUCK_DATA_PIVOTED.COOLANT_TEMP_C AS COOLANT_TEMP_C COMMENT='Engine coolant temperature in Celsius. Normal 85-95.',
        TRUCK_DATA_PIVOTED.OIL_PRESSURE_PSI AS OIL_PRESSURE_PSI COMMENT='Engine oil pressure in psi.',
        TRUCK_DATA_PIVOTED.ENGINE_LOAD_PCT AS ENGINE_LOAD_PCT COMMENT='Engine load percentage (0-100).',
        TRUCK_DATA_PIVOTED.ENGINE_RPM AS ENGINE_RPM COMMENT='Engine RPM.',
        TRUCK_DATA_PIVOTED.LEFT_EXHAUST_TEMP_C AS LEFT_EXHAUST_TEMP_C COMMENT='Left exhaust temperature in Celsius.',
        TRUCK_DATA_PIVOTED.RIGHT_EXHAUST_TEMP_C AS RIGHT_EXHAUST_TEMP_C COMMENT='Right exhaust temperature in Celsius.',
        TRUCK_DATA_PIVOTED.AFTERCOOLER_TEMP_C AS AFTERCOOLER_TEMP_C COMMENT='Aftercooler temperature in Celsius.',
        TRUCK_DATA_PIVOTED.BOOST_PRESSURE AS BOOST_PRESSURE COMMENT='Turbocharger boost pressure.',
        TRUCK_DATA_PIVOTED.LEFT_FRONT_SUSPENSION_KPA AS LEFT_FRONT_SUSPENSION_KPA COMMENT='Left front suspension pressure in kPa.',
        TRUCK_DATA_PIVOTED.RIGHT_FRONT_SUSPENSION_KPA AS RIGHT_FRONT_SUSPENSION_KPA COMMENT='Right front suspension pressure in kPa.',
        TRUCK_DATA_PIVOTED.LEFT_REAR_SUSPENSION_KPA AS LEFT_REAR_SUSPENSION_KPA COMMENT='Left rear suspension pressure in kPa.',
        TRUCK_DATA_PIVOTED.RIGHT_REAR_SUSPENSION_KPA AS RIGHT_REAR_SUSPENSION_KPA COMMENT='Right rear suspension pressure in kPa.',
        TRUCK_DATA_PIVOTED.SUSPENSION_DELTA_FRONT_KPA AS SUSPENSION_DELTA_FRONT_KPA COMMENT='Front suspension left-right pressure difference in kPa.',
        TRUCK_DATA_PIVOTED.SUSPENSION_DELTA_REAR_KPA AS SUSPENSION_DELTA_REAR_KPA COMMENT='Rear suspension left-right pressure difference in kPa.',
        TRUCK_DATA_PIVOTED.LEFT_FRONT_BRAKE_TEMP_C AS LEFT_FRONT_BRAKE_TEMP_C COMMENT='Left front brake temperature in Celsius.',
        TRUCK_DATA_PIVOTED.RIGHT_FRONT_BRAKE_TEMP_C AS RIGHT_FRONT_BRAKE_TEMP_C COMMENT='Right front brake temperature in Celsius.',
        TRUCK_DATA_PIVOTED.LEFT_REAR_BRAKE_TEMP_C AS LEFT_REAR_BRAKE_TEMP_C COMMENT='Left rear brake temperature in Celsius.',
        TRUCK_DATA_PIVOTED.RIGHT_REAR_BRAKE_TEMP_C AS RIGHT_REAR_BRAKE_TEMP_C COMMENT='Right rear brake temperature in Celsius.',
        TRUCK_DATA_PIVOTED.LATITUDE AS LATITUDE COMMENT='GPS latitude.',
        TRUCK_DATA_PIVOTED.LONGITUDE AS LONGITUDE COMMENT='GPS longitude.'
    )
    DIMENSIONS (
        TRUCK_DATA_PIVOTED.TRUCK AS TRUCK COMMENT='Truck identifier: Truck 101 through Truck 110.',
        TRUCK_DATA_PIVOTED.TIMESTAMP AS TIMESTAMP COMMENT='Hourly timestamp of reading.',
        TRUCK_DATA_PIVOTED.DATE AS DATE COMMENT='Date of the reading.',
        TRUCK_DATA_PIVOTED.DAY_OF_WEEK AS DAY_OF_WEEK COMMENT='Day of week (Mon-Sun).',
        TRUCK_DATA_PIVOTED.HOUR_OF_DAY AS HOUR_OF_DAY COMMENT='Hour of day (0-23).'
    )
    COMMENT='Mining haul truck fleet sensor data. 10 trucks, 24 sensors, hourly granularity.';

-- Verify
DESCRIBE SEMANTIC VIEW AVEVA_FLEET_OPS.STREAMLIT.FLEET_SEMANTIC_VIEW;

-- ============================================================================
-- 4. Create Cortex Agent with text-to-SQL tool
-- ============================================================================
CREATE OR REPLACE AGENT AVEVA_FLEET_OPS.STREAMLIT.FLEET_DATA_AGENT
FROM SPECIFICATION $${"models":{"orchestration":"auto"},"orchestration":{"budget":{"seconds":300,"tokens":200000}},"instructions":{"orchestration":"You are a fleet operations analyst for a mining company. You help users query and analyze data from 10 mining haul trucks (Truck 101 through Truck 110). The data includes hourly sensor readings like fuel rate, speed, engine temperature, payload, suspension pressure, brake temperature, and more. Always use the query_fleet_data tool to answer questions about the trucks.","response":"Provide clear, concise answers about fleet operations. When presenting data, highlight key findings and any anomalies. Use units where applicable (L/h for fuel, km/h for speed, C for temperature, kPa for pressure, tonnes for payload)."},"tools":[{"tool_spec":{"type":"cortex_analyst_text_to_sql","name":"query_fleet_data","description":"Query mining haul truck fleet sensor data including fuel rate, speed, payload, engine temperature, oil pressure, RPM, exhaust temps, suspension pressure, brake temps, and GPS coordinates. Data is hourly aggregated for 10 trucks (Truck 101-110)."}}],"tool_resources":{"query_fleet_data":{"execution_environment":{"query_timeout":299,"type":"warehouse","warehouse":""},"semantic_view":"AVEVA_FLEET_OPS.STREAMLIT.FLEET_SEMANTIC_VIEW"}}}$$;

-- Verify
SHOW AGENTS IN SCHEMA AVEVA_FLEET_OPS.STREAMLIT;

-- ============================================================================
-- 5. Verify Cortex AI is working
-- ============================================================================
SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', 'Say hello in one word') AS test;

-- ============================================================================
-- 6. Verify data sources
-- ============================================================================

-- AVEVA truck data (update schema ID to match your account)
SELECT COUNT(*) AS truck_rows,
       COUNT(DISTINCT "Name") AS trucks,
       COUNT(DISTINCT "Field") AS sensors
FROM CONNECT_AWC26."f6dd054e-d7b7-4b48-97f3-1b0eb2e91ab0".mining_haul_truck_narrow_live;

-- WeatherSource historical data (commented out — Marketplace listing may not be installed)
-- SELECT COUNT(*) AS weather_rows
-- FROM GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI.PWS_BI_SAMPLE.POINT_HISTORY_DAY
-- WHERE CITY_NAME = 'calgary';

-- WeatherSource forecast data (commented out — Marketplace listing may not be installed)
-- SELECT COUNT(*) AS forecast_rows
-- FROM GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI.PWS_BI_SAMPLE.POINT_FORECAST_DAY
-- WHERE CITY_NAME = 'calgary'
--   AND DATE_VALID_STD >= CURRENT_DATE();

-- ============================================================================
-- 7. Fabricated WeatherSource Data
-- ============================================================================
--
-- These tables provide sample weather data that mirrors the Snowflake Marketplace
-- WeatherSource listing. The app auto-detects: if the real Marketplace database
-- exists, it uses that; otherwise it falls back to these tables.
-- ============================================================================

-- 7a. WeatherSource POINT_HISTORY_DAY sample (Calgary, ~365 days)
CREATE OR REPLACE TABLE AVEVA_FLEET_OPS.STREAMLIT.WEATHER_HISTORY_SAMPLE AS
WITH date_series AS (
    SELECT DATEADD('day', -SEQ4(), CURRENT_DATE()) AS dt
    FROM TABLE(GENERATOR(ROWCOUNT => 369))
),
monthly_params AS (
    SELECT column1 AS mo, column2 AS avg_f, column3 AS min_delta, column4 AS max_delta,
           column5 AS wind, column6 AS humid, column7 AS precip, column8 AS snow
    FROM VALUES
        (1,  27.4, -8.7, 8.9,  8.0, 61.5, 0.00, 0.00),
        (2,  26.9, -9.4, 8.9,  7.6, 58.8, 0.01, 0.27),
        (3,  30.3, -9.8, 10.7, 8.3, 67.0, 0.03, 0.35),
        (4,  39.9, -10.2, 9.3, 8.5, 62.6, 0.04, 0.39),
        (5,  55.8, -12.4, 11.3, 7.5, 52.4, 0.08, 0.00),
        (6,  60.8, -11.1, 10.2, 7.3, 52.8, 0.18, 0.00),
        (7,  62.7, -9.6, 8.8,  7.0, 68.6, 0.31, 0.00),
        (8,  65.2, -11.7, 11.3, 5.7, 62.5, 0.06, 0.00),
        (9,  62.0, -12.3, 12.4, 5.8, 55.5, 0.00, 0.00),
        (10, 44.7, -9.9, 10.4, 7.5, 52.1, 0.01, 0.01),
        (11, 32.7, -8.3, 8.7,  5.6, 69.3, 0.02, 0.20),
        (12, 18.2, -10.1, 12.0, 7.1, 72.5, 0.01, 0.21)
)
SELECT
    'calgary' AS CITY_NAME,
    'CA' AS COUNTRY_CODE,
    51.0447 AS LATITUDE_DEG,
    -114.0719 AS LONGITUDE_DEG,
    d.dt AS DATE_VALID_STD,
    DAYOFYEAR(d.dt) AS DOY_STD,
    ROUND(p.avg_f + p.min_delta + UNIFORM(-3.0, 3.0, RANDOM()), 1) AS MIN_TEMPERATURE_AIR_2M_F,
    ROUND(p.avg_f + UNIFORM(-4.0, 4.0, RANDOM()), 1) AS AVG_TEMPERATURE_AIR_2M_F,
    ROUND(p.avg_f + p.max_delta + UNIFORM(-3.0, 3.0, RANDOM()), 1) AS MAX_TEMPERATURE_AIR_2M_F,
    ROUND(p.wind + UNIFORM(-2.0, 3.0, RANDOM()), 1) AS "__AVG_WIND_SPEED_10M_MPH",
    ROUND(p.humid + UNIFORM(-10.0, 10.0, RANDOM()), 1) AS AVG_HUMIDITY_RELATIVE_2M_PCT,
    ROUND(GREATEST(0, p.precip + UNIFORM(-0.02, 0.15, RANDOM())), 2) AS TOT_PRECIPITATION_IN,
    ROUND(GREATEST(0, p.snow + UNIFORM(-0.1, 0.5, RANDOM())), 2) AS TOT_SNOWFALL_IN,
    ROUND(CASE WHEN MONTH(d.dt) IN (11,12,1,2,3) THEN UNIFORM(0.0, 8.0, RANDOM()) ELSE 0.0 END, 1) AS TOT_SNOWDEPTH_IN
FROM date_series d
JOIN monthly_params p ON p.mo = MONTH(d.dt)
ORDER BY d.dt;

-- 7b. WeatherSource POINT_FORECAST_DAY sample (Calgary, 15 days ahead)
CREATE OR REPLACE TABLE AVEVA_FLEET_OPS.STREAMLIT.WEATHER_FORECAST_SAMPLE AS
WITH forecast_days AS (
    SELECT DATEADD('day', SEQ4() + 1, CURRENT_DATE()) AS dt
    FROM TABLE(GENERATOR(ROWCOUNT => 15))
),
init_times AS (
    SELECT column1 AS init_offset_hrs FROM VALUES (0), (6), (12)
),
monthly_params AS (
    SELECT column1 AS mo, column2 AS avg_f, column3 AS min_delta, column4 AS max_delta,
           column5 AS wind, column6 AS humid
    FROM VALUES
        (1,  27.4, -8.7, 8.9,  8.0, 61.5),
        (2,  26.9, -9.4, 8.9,  7.6, 58.8),
        (3,  30.3, -9.8, 10.7, 8.3, 67.0),
        (4,  39.9, -10.2, 9.3, 8.5, 62.6),
        (5,  55.8, -12.4, 11.3, 7.5, 52.4),
        (6,  60.8, -11.1, 10.2, 7.3, 52.8),
        (7,  62.7, -9.6, 8.8,  7.0, 68.6),
        (8,  65.2, -11.7, 11.3, 5.7, 62.5),
        (9,  62.0, -12.3, 12.4, 5.8, 55.5),
        (10, 44.7, -9.9, 10.4, 7.5, 52.1),
        (11, 32.7, -8.3, 8.7,  5.6, 69.3),
        (12, 18.2, -10.1, 12.0, 7.1, 72.5)
)
SELECT
    'calgary' AS CITY_NAME,
    'CA' AS COUNTRY_CODE,
    51.0447 AS LATITUDE_DEG,
    -114.0719 AS LONGITUDE_DEG,
    DATEADD('hour', i.init_offset_hrs, d.dt::TIMESTAMP_NTZ) AS TIME_INIT_UTC,
    d.dt AS DATE_VALID_STD,
    DAYOFYEAR(d.dt) AS DOY_STD,
    ROUND(p.avg_f + p.min_delta + UNIFORM(-3.0, 3.0, RANDOM()), 1) AS MIN_TEMPERATURE_AIR_2M_F,
    ROUND(p.avg_f + UNIFORM(-4.0, 4.0, RANDOM()), 1) AS AVG_TEMPERATURE_AIR_2M_F,
    ROUND(p.avg_f + p.max_delta + UNIFORM(-3.0, 3.0, RANDOM()), 1) AS MAX_TEMPERATURE_AIR_2M_F,
    ROUND(p.wind + UNIFORM(-2.0, 3.0, RANDOM()), 1) AS "__AVG_WIND_SPEED_10M_MPH",
    ROUND(p.wind + UNIFORM(2.0, 8.0, RANDOM()), 1) AS "__MAX_WIND_SPEED_10M_MPH",
    ROUND(GREATEST(0, UNIFORM(-0.02, 0.15, RANDOM())), 2) AS TOT_PRECIPITATION_IN,
    ROUND(UNIFORM(5, 60, RANDOM()), 0) AS PROBABILITY_OF_PRECIPITATION_PCT,
    ROUND(CASE WHEN MONTH(d.dt) IN (11,12,1,2,3,4) THEN UNIFORM(0, 40, RANDOM()) ELSE 0 END, 0) AS PROBABILITY_OF_SNOW_PCT
FROM forecast_days d
CROSS JOIN init_times i
JOIN monthly_params p ON p.mo = MONTH(d.dt)
ORDER BY d.dt, i.init_offset_hrs;

-- Verify fabricated data
SELECT 'WEATHER_HISTORY_SAMPLE' AS table_name, COUNT(*) AS row_count FROM AVEVA_FLEET_OPS.STREAMLIT.WEATHER_HISTORY_SAMPLE
UNION ALL SELECT 'WEATHER_FORECAST_SAMPLE', COUNT(*) FROM AVEVA_FLEET_OPS.STREAMLIT.WEATHER_FORECAST_SAMPLE;

-- ============================================================================
-- 8. Deploy the Streamlit app
-- ============================================================================
--
-- From the build2_fleet_ops directory, run:
--   snow streamlit deploy --replace --connection <your_connection>
--
-- The app will be available at:
--   AVEVA_FLEET_OPS.STREAMLIT.WEATHER_AWARE_FLEET_OPS
--
-- ============================================================================
