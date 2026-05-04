-- =============================================================================
-- Field Operator AI Demo — Setup Script
-- AVEVA World 2026 — "The Edge" Demo
-- =============================================================================
-- Run this ONCE against AVEVA_CONNECT.PUBLIC on Polaris1 (my_polaris_connection)
-- Prerequisites:
--   - INDUSTRIAL_DOCS_SEARCH Cortex Search service must exist
--   - AVEVA_CLD_DATA with mining truck + water pump live data
--   - AVEVA_FLEET_OPS.STREAMLIT.FLEET_SEMANTIC_VIEW must exist (from build2_fleet_ops)
-- =============================================================================

USE DATABASE AVEVA_CONNECT;
USE SCHEMA PUBLIC;
USE WAREHOUSE COMPUTE_WH;

-- =============================================================================
-- 1. Create Pivoted Pump View (for semantic model)
-- =============================================================================
-- CLD pump data arrives in narrow format: Timestamp, Name, Field, Value
-- This pivots it into one row per pump per hour with named columns.
-- =============================================================================

CREATE OR REPLACE VIEW AVEVA_CONNECT.PUBLIC.PUMP_DATA_PIVOTED AS
WITH hourly AS (
    SELECT
        "Name" AS PUMP,
        DATE_TRUNC('hour', "Timestamp") AS HOUR_TS,
        "Field",
        AVG("Value") AS AVG_VAL
    FROM AVEVA_CLD_DATA."f6dd054e-d7b7-4b48-97f3-1b0eb2e91ab0".water_leakage_pump_narrow_live
    GROUP BY "Name", DATE_TRUNC('hour', "Timestamp"), "Field"
)
SELECT
    PUMP,
    HOUR_TS AS TIMESTAMP,
    DATE_TRUNC('day', HOUR_TS) AS DATE,
    DAYNAME(HOUR_TS) AS DAY_OF_WEEK,
    HOUR(HOUR_TS) AS HOUR_OF_DAY,
    ROUND(MAX(CASE WHEN "Field" = 'Temperature - Inboard Bearing Value °C' THEN AVG_VAL END), 2) AS INBOARD_BEARING_TEMP_C,
    ROUND(MAX(CASE WHEN "Field" = 'Temperature - Outboard Bearing Value °C' THEN AVG_VAL END), 2) AS OUTBOARD_BEARING_TEMP_C,
    ROUND(MAX(CASE WHEN "Field" = 'Thrust Bearing Temperature 1 Value °C' THEN AVG_VAL END), 2) AS THRUST_BEARING_TEMP1_C,
    ROUND(MAX(CASE WHEN "Field" = 'Thrust Bearing Temperature 2 Value °C' THEN AVG_VAL END), 2) AS THRUST_BEARING_TEMP2_C,
    ROUND(MAX(CASE WHEN "Field" = 'Thrust Bearing Temperature 3 Value °C' THEN AVG_VAL END), 2) AS THRUST_BEARING_TEMP3_C,
    ROUND(MAX(CASE WHEN "Field" = 'Thrust Bearing Temperature 1|Predicted Value °C' THEN AVG_VAL END), 2) AS THRUST_BEARING_TEMP1_PREDICTED_C,
    ROUND(MAX(CASE WHEN "Field" = 'Thrust Bearing Temperature 2|Predicted Value °C' THEN AVG_VAL END), 2) AS THRUST_BEARING_TEMP2_PREDICTED_C,
    ROUND(MAX(CASE WHEN "Field" = 'Thrust Bearing Temperature 3|Predicted Value °C' THEN AVG_VAL END), 2) AS THRUST_BEARING_TEMP3_PREDICTED_C,
    ROUND(MAX(CASE WHEN "Field" = 'Vibration X - Inboard Bearing Value' THEN AVG_VAL END), 4) AS VIBRATION_X_INBOARD,
    ROUND(MAX(CASE WHEN "Field" = 'Vibration Y - Inboard Bearing Value' THEN AVG_VAL END), 4) AS VIBRATION_Y_INBOARD,
    ROUND(MAX(CASE WHEN "Field" = 'Vibration X - Outboard Bearing Value' THEN AVG_VAL END), 4) AS VIBRATION_X_OUTBOARD,
    ROUND(MAX(CASE WHEN "Field" = 'Vibration Y - Outboard Bearing Value' THEN AVG_VAL END), 4) AS VIBRATION_Y_OUTBOARD,
    ROUND(MAX(CASE WHEN "Field" = 'Pump Efficiency Value %' THEN AVG_VAL END), 2) AS PUMP_EFFICIENCY_PCT,
    ROUND(MAX(CASE WHEN "Field" = 'Motor Current Value A' THEN AVG_VAL END), 2) AS MOTOR_CURRENT_A,
    ROUND(MAX(CASE WHEN "Field" = 'Motor Power Value kW' THEN AVG_VAL END), 2) AS MOTOR_POWER_KW,
    ROUND(MAX(CASE WHEN "Field" = 'Speed - Pump Value rpm' THEN AVG_VAL END), 2) AS PUMP_SPEED_RPM,
    ROUND(MAX(CASE WHEN "Field" = 'Discharge Pressure Value psi' THEN AVG_VAL END), 2) AS DISCHARGE_PRESSURE_PSI,
    ROUND(MAX(CASE WHEN "Field" = 'Discharge Flow Rate Value' THEN AVG_VAL END), 2) AS DISCHARGE_FLOW_RATE,
    ROUND(MAX(CASE WHEN "Field" = 'Ambient Temperature Value °C' THEN AVG_VAL END), 2) AS AMBIENT_TEMP_C,
    ROUND(MAX(CASE WHEN "Field" = 'Ambient Temperature|Predicted Value °C' THEN AVG_VAL END), 2) AS AMBIENT_TEMP_PREDICTED_C,
    ROUND(MAX(CASE WHEN "Field" = 'Run Hours Since Last Maintenance Value h' THEN AVG_VAL END), 0) AS RUN_HOURS_SINCE_MAINTENANCE,
    ROUND(MAX(CASE WHEN "Field" = 'Run Hours since installed Value h' THEN AVG_VAL END), 0) AS RUN_HOURS_TOTAL,
    ROUND(MAX(CASE WHEN "Field" = 'Amps - Motor Value A' THEN AVG_VAL END), 2) AS MOTOR_AMPS
FROM hourly
GROUP BY PUMP, HOUR_TS;

-- =============================================================================
-- 2. Create Pump Semantic View (for Agent text-to-SQL)
-- =============================================================================

CREATE OR REPLACE SEMANTIC VIEW AVEVA_CONNECT.PUBLIC.PUMP_SEMANTIC_VIEW
    TABLES (
        AVEVA_CONNECT.PUBLIC.PUMP_DATA_PIVOTED
            COMMENT='Hourly aggregated sensor readings for 25 water distribution pumps across 4 DMA zones (DMA01-DMA04). Includes AVEVA predicted values for anomaly detection.'
    )
    FACTS (
        PUMP_DATA_PIVOTED.INBOARD_BEARING_TEMP_C AS INBOARD_BEARING_TEMP_C COMMENT='Inboard bearing temperature in Celsius. Normal: 45-60C. Alert >70C.',
        PUMP_DATA_PIVOTED.OUTBOARD_BEARING_TEMP_C AS OUTBOARD_BEARING_TEMP_C COMMENT='Outboard bearing temperature in Celsius.',
        PUMP_DATA_PIVOTED.THRUST_BEARING_TEMP1_C AS THRUST_BEARING_TEMP1_C COMMENT='Thrust bearing temp sensor 1 (actual) in Celsius. Normal: 55-70C. Critical >85C.',
        PUMP_DATA_PIVOTED.THRUST_BEARING_TEMP2_C AS THRUST_BEARING_TEMP2_C COMMENT='Thrust bearing temp sensor 2 (actual) in Celsius.',
        PUMP_DATA_PIVOTED.THRUST_BEARING_TEMP3_C AS THRUST_BEARING_TEMP3_C COMMENT='Thrust bearing temp sensor 3 (actual) in Celsius.',
        PUMP_DATA_PIVOTED.THRUST_BEARING_TEMP1_PREDICTED_C AS THRUST_BEARING_TEMP1_PREDICTED_C COMMENT='AVEVA predicted thrust bearing temp sensor 1.',
        PUMP_DATA_PIVOTED.THRUST_BEARING_TEMP2_PREDICTED_C AS THRUST_BEARING_TEMP2_PREDICTED_C COMMENT='AVEVA predicted thrust bearing temp sensor 2.',
        PUMP_DATA_PIVOTED.THRUST_BEARING_TEMP3_PREDICTED_C AS THRUST_BEARING_TEMP3_PREDICTED_C COMMENT='AVEVA predicted thrust bearing temp sensor 3.',
        PUMP_DATA_PIVOTED.VIBRATION_X_INBOARD AS VIBRATION_X_INBOARD COMMENT='Inboard bearing X-axis vibration mm/s RMS. Normal 0.2-0.8. Alert >1.2.',
        PUMP_DATA_PIVOTED.VIBRATION_Y_INBOARD AS VIBRATION_Y_INBOARD COMMENT='Inboard bearing Y-axis vibration mm/s RMS.',
        PUMP_DATA_PIVOTED.VIBRATION_X_OUTBOARD AS VIBRATION_X_OUTBOARD COMMENT='Outboard bearing X-axis vibration mm/s RMS.',
        PUMP_DATA_PIVOTED.VIBRATION_Y_OUTBOARD AS VIBRATION_Y_OUTBOARD COMMENT='Outboard bearing Y-axis vibration mm/s RMS.',
        PUMP_DATA_PIVOTED.PUMP_EFFICIENCY_PCT AS PUMP_EFFICIENCY_PCT COMMENT='Pump efficiency %. Normal 70-85. Concern <65. Impeller issue <50.',
        PUMP_DATA_PIVOTED.MOTOR_CURRENT_A AS MOTOR_CURRENT_A COMMENT='Motor current draw in Amps.',
        PUMP_DATA_PIVOTED.MOTOR_POWER_KW AS MOTOR_POWER_KW COMMENT='Motor power consumption in kW.',
        PUMP_DATA_PIVOTED.PUMP_SPEED_RPM AS PUMP_SPEED_RPM COMMENT='Pump speed in RPM.',
        PUMP_DATA_PIVOTED.DISCHARGE_PRESSURE_PSI AS DISCHARGE_PRESSURE_PSI COMMENT='Discharge pressure in PSI.',
        PUMP_DATA_PIVOTED.DISCHARGE_FLOW_RATE AS DISCHARGE_FLOW_RATE COMMENT='Discharge flow rate.',
        PUMP_DATA_PIVOTED.AMBIENT_TEMP_C AS AMBIENT_TEMP_C COMMENT='Ambient temperature Celsius. Affects bearing temps.',
        PUMP_DATA_PIVOTED.AMBIENT_TEMP_PREDICTED_C AS AMBIENT_TEMP_PREDICTED_C COMMENT='AVEVA predicted ambient temperature.',
        PUMP_DATA_PIVOTED.RUN_HOURS_SINCE_MAINTENANCE AS RUN_HOURS_SINCE_MAINTENANCE COMMENT='Run hours since last maintenance. Fleet avg 2400h. Overdue >2800h.',
        PUMP_DATA_PIVOTED.RUN_HOURS_TOTAL AS RUN_HOURS_TOTAL COMMENT='Total run hours since installation.',
        PUMP_DATA_PIVOTED.MOTOR_AMPS AS MOTOR_AMPS COMMENT='Motor amperage reading.'
    )
    DIMENSIONS (
        PUMP_DATA_PIVOTED.PUMP AS PUMP COMMENT='Pump ID: PMP-DMAxxY-ZZ. DMA01-04 are district metered areas.',
        PUMP_DATA_PIVOTED.TIMESTAMP AS TIMESTAMP COMMENT='Hourly timestamp.',
        PUMP_DATA_PIVOTED.DATE AS DATE COMMENT='Date of reading.',
        PUMP_DATA_PIVOTED.DAY_OF_WEEK AS DAY_OF_WEEK COMMENT='Day of week (Mon-Sun).',
        PUMP_DATA_PIVOTED.HOUR_OF_DAY AS HOUR_OF_DAY COMMENT='Hour of day (0-23).'
    )
    COMMENT='Water pump sensor data. 25 pumps, 4 DMA zones. Includes AVEVA predictions.';

-- =============================================================================
-- 3. Create the Cortex Agent Object (3 tools)
-- =============================================================================
-- Tools:
--   1. query_truck_data: text-to-SQL via FLEET_SEMANTIC_VIEW (10 trucks, 24 sensors)
--   2. query_pump_data:  text-to-SQL via PUMP_SEMANTIC_VIEW (25 pumps, 23 sensors)
--   3. knowledge_search: cortex_search on 28 OEM docs, SOPs, incident reports
-- =============================================================================

CREATE OR REPLACE AGENT AVEVA_CONNECT.PUBLIC.FIELD_OPERATOR_AGENT
FROM SPECIFICATION $$
instructions:
  system: |
    You are AVEVA Field AI — an intelligent assistant for industrial operations
    at a mining and water utility site near Calgary, Alberta.

    You have access to three data tools:
    1. query_truck_data: Query live sensor data from 10 mining haul trucks (Truck 101-110).
       Data includes coolant temp, brake temps, fuel rate, speed, payload, suspension, GPS, engine load.
    2. query_pump_data: Query live sensor data from 25 water distribution pumps across 4 DMA zones.
       Data includes bearing temps (actual vs AVEVA predicted), vibration, efficiency, motor current, run hours.
    3. knowledge_search: Search 28 industrial documents — OEM bulletins (SKF, Sulzer, WEG),
       maintenance SOPs, incident reports, safety procedures, and industry standards.

    USE THE DATA TOOLS. When asked about equipment status, temperatures, trends, or comparisons,
    always query the actual data rather than guessing. Use knowledge_search for procedures and thresholds.

    Key context:
    - Pump names: PMP-DMAxxY-ZZ (e.g., PMP-DMA04A-06). DMA01-04 are district metered areas.
    - Trucks: Truck 101 through Truck 110. Mining haul trucks with hourly sensor data.
    - Bearing temp normal: 55-70C. Alert >75C. Critical >85C.
    - Vibration normal: 0.2-0.8 mm/s. Alert >1.2. Trip >2.0.
    - Pump efficiency normal: 70-85%. Concern <65%. Impeller issue <50%.
    - Coolant temp normal: 85-95C. Alert >96C.
    - SAP spare parts and maintenance orders are documented in the knowledge base.

    IMPORTANT RULES:
    - Be concise — users are on mobile devices
    - Always include a clear YES/NO/MONITOR recommendation
    - Cite specific data values and documents when relevant
    - Include safety warnings when readings are critical
    - Format for mobile: short paragraphs, bullet points, bold key numbers
  response: |
    Keep responses under 250 words. Use bullet points and bold for key values.
    Always end with a clear action item. When citing documents, mention their title.
    If safety is involved, lead with the safety recommendation.
orchestration:
  budget:
    seconds: 120
    tokens: 50000
tools:
  - tool_spec:
      type: cortex_analyst_text_to_sql
      name: query_truck_data
      description: >
        Query live mining haul truck sensor data for Truck 101-110.
        Includes coolant temp, brake temps, fuel rate, speed, payload, suspension,
        GPS, engine load, exhaust temps, oil pressure. Hourly aggregated.
  - tool_spec:
      type: cortex_analyst_text_to_sql
      name: query_pump_data
      description: >
        Query live water pump sensor data for 25 pumps across 4 DMA zones.
        Includes bearing temps (actual and AVEVA predicted), vibration, efficiency,
        motor current, run hours, ambient temp. Hourly aggregated.
  - tool_spec:
      type: cortex_search
      name: knowledge_search
      description: >
        Search industrial knowledge base with 28 documents: OEM bulletins (SKF bearings,
        Sulzer pumps, WEG motors), maintenance SOPs, incident reports, safety procedures,
        and industry standards. Use for thresholds, procedures, and part numbers.
tool_resources:
  query_truck_data:
    semantic_view: AVEVA_FLEET_OPS.STREAMLIT.FLEET_SEMANTIC_VIEW
    execution_environment:
      warehouse: COMPUTE_WH
  query_pump_data:
    semantic_view: AVEVA_CONNECT.PUBLIC.PUMP_SEMANTIC_VIEW
    execution_environment:
      warehouse: COMPUTE_WH
  knowledge_search:
    search_service: AVEVA_CONNECT.PUBLIC.INDUSTRIAL_DOCS_SEARCH
    title_column: TITLE
    id_column: TITLE
$$;

-- =============================================================================
-- 4. Create the SiS stage (if not exists)
-- =============================================================================

CREATE STAGE IF NOT EXISTS AVEVA_CONNECT.PUBLIC.FIELD_OPERATOR_STAGE
  DIRECTORY = (ENABLE = TRUE);

-- =============================================================================
-- 5. Verify
-- =============================================================================

-- DESCRIBE AGENT AVEVA_CONNECT.PUBLIC.FIELD_OPERATOR_AGENT;
-- Test via REST: POST /api/v2/databases/AVEVA_CONNECT/schemas/PUBLIC/agents/FIELD_OPERATOR_AGENT:run

SELECT 'Setup complete. Agent FIELD_OPERATOR_AGENT created with 3 tools (truck SQL, pump SQL, knowledge search).' AS status;
