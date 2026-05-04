-- =============================================================================
-- AVEVA CLD Integration — Catalog-Linked Database Setup
-- =============================================================================
-- This script connects Snowflake to AVEVA Connect via Iceberg REST Catalog.
-- Two statements. Zero data movement. 13M+ sensor readings become queryable.
--
-- Prerequisites:
--   1. AVEVA Connect tenant with CLD (Connected Lifecycle Data) enabled
--   2. AVEVA provides the Iceberg REST catalog URI and warehouse name
--   3. Vended credentials (AVEVA issues short-lived tokens automatically)
-- =============================================================================

-- ─── Step 1: Create Catalog Integration ──────────────────────────────────────
-- This registers AVEVA's Iceberg REST catalog endpoint with Snowflake.
-- VENDED_CREDENTIALS means AVEVA handles authentication — no keys to manage.

CREATE OR REPLACE CATALOG INTEGRATION AVEVA_CLD_CATALOG
  CATALOG_SOURCE     = ICEBERG_REST
  TABLE_FORMAT       = ICEBERG
  CATALOG_URI        = 'https://westus3.azuredatabricks.net/api/2.0/delta-sharing/metastores/<metastore-id>/iceberg'
  CATALOG_API_TYPE   = PUBLIC
  CATALOG_WAREHOUSE  = 'AWC26_Snowflake_<warehouse-token>'
  ACCESS_DELEGATION_MODE = VENDED_CREDENTIALS
  ENABLED            = TRUE;

-- ─── Step 2: Create Catalog-Linked Database ──────────────────────────────────
-- This creates a database that auto-syncs with the AVEVA catalog.
-- Tables appear automatically as AVEVA publishes them — no DDL needed.

CREATE OR REPLACE DATABASE AVEVA_CLD_DATA
  FROM CATALOG INTEGRATION AVEVA_CLD_CATALOG
  AUTO_REFRESH = TRUE
  COMMENT = 'AVEVA Connect CLD data via Iceberg REST catalog - vended credentials';

-- =============================================================================
-- That's it. Two statements. The database now contains every table AVEVA
-- has published to this catalog. Let's verify.
-- =============================================================================

-- ─── Verify: What schemas and tables appeared? ───────────────────────────────

SHOW SCHEMAS IN DATABASE AVEVA_CLD_DATA;
-- Returns: f6dd054e-d7b7-4b48-97f3-1b0eb2e91ab0  (AVEVA's catalog namespace)

SHOW TABLES IN DATABASE AVEVA_CLD_DATA;
-- Returns:
--   mining_haul_truck_narrow_26q1   │ 1.7M rows  │ Iceberg │ 10 trucks, Q1 2026 static batch
--   mining_haul_truck_narrow_live   │ 3.8M rows  │ Iceberg │ 10 trucks, live stream
--   water_leakage_pump_narrow_live  │ 7.6M rows  │ Iceberg │ 25 pumps, live stream

-- ─── Verify: Row counts ──────────────────────────────────────────────────────

SELECT 'mining_haul_truck_narrow_26q1'  AS table_name, COUNT(*) AS rows
  FROM AVEVA_CLD_DATA."f6dd054e-d7b7-4b48-97f3-1b0eb2e91ab0".mining_haul_truck_narrow_26q1
UNION ALL
SELECT 'mining_haul_truck_narrow_live',  COUNT(*)
  FROM AVEVA_CLD_DATA."f6dd054e-d7b7-4b48-97f3-1b0eb2e91ab0".mining_haul_truck_narrow_live
UNION ALL
SELECT 'water_leakage_pump_narrow_live', COUNT(*)
  FROM AVEVA_CLD_DATA."f6dd054e-d7b7-4b48-97f3-1b0eb2e91ab0".water_leakage_pump_narrow_live;

-- ─── Verify: Data shape (narrow format) ──────────────────────────────────────
-- Every AVEVA CLD table follows the same schema:
--   Timestamp  │  Name           │  Field                              │  Value
--   2026-01-15 │  Truck 108      │  Engine Coolant Temperature °C      │  92.4
--   2026-01-15 │  PMP-DMA04A-06  │  Thrust Bearing Temperature DE °C   │  68.7

SELECT "Timestamp", "Name", "Field", "Value"
  FROM AVEVA_CLD_DATA."f6dd054e-d7b7-4b48-97f3-1b0eb2e91ab0".mining_haul_truck_narrow_live
  LIMIT 5;

-- ─── Verify: What assets and sensors are available? ──────────────────────────

-- Trucks: 10 assets, 33 sensor types
SELECT COUNT(DISTINCT "Name") AS trucks, COUNT(DISTINCT "Field") AS sensors
  FROM AVEVA_CLD_DATA."f6dd054e-d7b7-4b48-97f3-1b0eb2e91ab0".mining_haul_truck_narrow_live;

-- Pumps: 25 assets, 77 sensor types
SELECT COUNT(DISTINCT "Name") AS pumps, COUNT(DISTINCT "Field") AS sensors
  FROM AVEVA_CLD_DATA."f6dd054e-d7b7-4b48-97f3-1b0eb2e91ab0".water_leakage_pump_narrow_live;

-- ─── Example: Cross-source JOIN (AVEVA + WeatherSource) ─────────────────────
-- This is the key demo moment: operational data + marketplace data, one query.

SELECT
    t."Name"                        AS truck,
    DATE(t."Timestamp")             AS day,
    AVG(t."Value")                  AS avg_fuel_rate,
    AVG(w.AVG_WIND_SPEED_10M_MPH)  AS avg_wind_mph
FROM AVEVA_CLD_DATA."f6dd054e-d7b7-4b48-97f3-1b0eb2e91ab0".mining_haul_truck_narrow_live t
JOIN GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI.PWS_BI_SAMPLE.POINT_HISTORY_DAY w
  ON DATE(t."Timestamp") = w.DATE_VALID_STD
WHERE t."Field" = 'Engine Fuel Rate Value l/h'
  AND w.POSTAL_CODE = 'T2P'
  AND t."Timestamp" >= '2026-04-01'
GROUP BY 1, 2
ORDER BY 2
LIMIT 10;
