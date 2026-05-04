-- ============================================================================
-- AVEVA + Snowflake: The Complete Picture — Demo Setup Script
-- ============================================================================
--
-- This script creates all fabricated data objects needed to run the
-- 'Complete Picture' AVEVA demo on a new Snowflake account.
--
-- Run this script top-to-bottom in a Snowflake worksheet.
--
-- PREREQUISITES (external data — cannot be replicated by this script):
--
--   1. AVEVA Catalog-Linked Database
--      Database: CONNECT_AWC26  (or AVEVA_CLD_DATA on some accounts)
--      Schema:   "f6dd054e-d7b7-4b48-97f3-1b0eb2e91ab0"
--      Table:    water_leakage_pump_narrow_live
--      Setup:    Attach the AVEVA CLD via Snowflake's Catalog Integration.
--               This provides live AVEVA PI sensor data for pumps.
--      NOTE:     If your CLD database is named differently, search-replace
--               CONNECT_AWC26 with your database name in this script.
--
--   2. WeatherSource (Snowflake Marketplace)
--      Database: GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI
--      Schema:   PWS_BI_SAMPLE
--      Table:    POINT_HISTORY_DAY
--      Setup:    Install 'Global Weather & Climate Data for BI' from the
--               Snowflake Marketplace (provider: WeatherSource).
--
--   3. Streamlit App Files
--      You need streamlit_app.py and environment.yml uploaded to
--      the stage AVEVA_CONNECT.PUBLIC.COMPLETE_PICTURE_STAGE.
--      See Section 7 at the bottom of this script.
--
-- ============================================================================


-- ======================================================================
-- SECTION 0: DATABASE, SCHEMA, WAREHOUSE, AND STAGE SETUP
-- ======================================================================

USE ROLE ACCOUNTADMIN;

-- Create database and schema (if they don't already exist)
CREATE DATABASE IF NOT EXISTS AVEVA_CONNECT;
CREATE SCHEMA IF NOT EXISTS AVEVA_CONNECT.PUBLIC;

-- Create warehouse (adjust size as needed)
CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH
  WITH WAREHOUSE_SIZE = 'MEDIUM'
  AUTO_SUSPEND = 300
  AUTO_RESUME = TRUE;

USE DATABASE AVEVA_CONNECT;
USE SCHEMA PUBLIC;
USE WAREHOUSE COMPUTE_WH;

-- Create stage for Streamlit app files
CREATE STAGE IF NOT EXISTS AVEVA_CONNECT.PUBLIC.COMPLETE_PICTURE_STAGE;


-- ======================================================================
-- SECTION 1: SAP_MAINTENANCE_ORDERS (40 rows)
-- ======================================================================

CREATE OR REPLACE TABLE AVEVA_CONNECT.PUBLIC.SAP_MAINTENANCE_ORDERS (
    WORK_ORDER_ID      VARCHAR(20),
    EQUIPMENT_ID       VARCHAR(30),
    ORDER_TYPE         VARCHAR(10),
    ORDER_TYPE_DESC    VARCHAR(50),
    PLANNED_DATE       DATE,
    COMPLETION_DATE    DATE,
    COST_CENTER        VARCHAR(20),
    ESTIMATED_COST_USD NUMBER(10,2),
    ACTUAL_COST_USD    NUMBER(10,2),
    STATUS             VARCHAR(20),
    PRIORITY           VARCHAR(10),
    DESCRIPTION        VARCHAR(200),
    TECHNICIAN         VARCHAR(50),
    SAP_PLANT          VARCHAR(20),
    CREATED_DATE       DATE
);

INSERT INTO AVEVA_CONNECT.PUBLIC.SAP_MAINTENANCE_ORDERS
    (WORK_ORDER_ID, EQUIPMENT_ID, ORDER_TYPE, ORDER_TYPE_DESC, PLANNED_DATE,
     COMPLETION_DATE, COST_CENTER, ESTIMATED_COST_USD, ACTUAL_COST_USD, STATUS,
     PRIORITY, DESCRIPTION, TECHNICIAN, SAP_PLANT, CREATED_DATE)
VALUES
    ('WO-2026-0102', 'PMP-DMA01A-11', 'PM', 'Preventive Maintenance', '2026-01-20', '2026-01-21', 'CC-WTR-01', 6500.0, 6120.0, 'COMPLETED', 'LOW', 'Annual pump overhaul and seal replacement', 'M. Chen', 'PLT-CGY-01', '2025-12-15'),
    ('WO-2026-0120', 'PMP-DMA03A-01', 'PM', 'Preventive Maintenance', '2026-01-22', '2026-01-22', 'CC-WTR-03', 6800.0, 6500.0, 'COMPLETED', 'LOW', 'Annual overhaul — oldest pump in fleet', 'M. Chen', 'PLT-CGY-01', '2025-12-20'),
    ('WO-2026-0135', 'PMP-DMA03A-02', 'PM', 'Preventive Maintenance', '2026-01-25', '2026-01-25', 'CC-WTR-03', 5200.0, 5100.0, 'COMPLETED', 'LOW', 'Quarterly bearing inspection and lubrication', 'R. Okafor', 'PLT-CGY-01', '2026-01-05'),
    ('WO-2026-0155', 'PMP-DMA01C-13', 'PM', 'Preventive Maintenance', '2026-01-28', '2026-01-28', 'CC-WTR-01', 4100.0, 3950.0, 'COMPLETED', 'LOW', 'Bearing temperature sensor recalibration', 'R. Okafor', 'PLT-CGY-01', '2026-01-10'),
    ('WO-2026-0160', 'PMP-DMA04A-07', 'PM', 'Preventive Maintenance', '2026-01-30', '2026-01-30', 'CC-WTR-04', 5800.0, 5600.0, 'COMPLETED', 'LOW', 'Quarterly bearing inspection', 'T. Blackwood', 'PLT-CGY-01', '2026-01-10'),
    ('WO-2026-0180', 'PMP-DMA02A-16', 'PM', 'Preventive Maintenance', '2026-02-01', '2026-02-01', 'CC-WTR-02', 5400.0, 5200.0, 'COMPLETED', 'LOW', 'Quarterly maintenance — suction chamber inspection', 'A. Patel', 'PLT-CGY-01', '2026-01-15'),
    ('WO-2026-0200', 'PMP-DMA03B-03', 'CM', 'Corrective Maintenance', '2026-02-03', '2026-02-05', 'CC-WTR-03', 16400.0, 17800.0, 'COMPLETED', 'HIGH', 'Suction chamber level sensor failure — full replacement', 'T. Blackwood', 'PLT-CGY-01', '2026-02-03'),
    ('WO-2026-0210', 'PMP-DMA01B-12', 'CM', 'Corrective Maintenance', '2026-02-05', '2026-02-07', 'CC-WTR-01', 18500.0, 21340.0, 'COMPLETED', 'HIGH', 'Emergency seal replacement — discharge pressure drop', 'T. Blackwood', 'PLT-CGY-01', '2026-02-05'),
    ('WO-2026-0225', 'PMP-DMA02B-17', 'CM', 'Corrective Maintenance', '2026-02-14', '2026-02-16', 'CC-WTR-02', 22100.0, 24500.0, 'COMPLETED', 'CRITICAL', 'Thrust bearing failure — emergency replacement', 'T. Blackwood', 'PLT-CGY-01', '2026-02-14'),
    ('WO-2026-0240', 'PMP-DMA04B-08', 'CM', 'Corrective Maintenance', '2026-02-10', '2026-02-12', 'CC-WTR-04', 14200.0, 15600.0, 'COMPLETED', 'HIGH', 'Vibration spike — motor bearing drive end replacement', 'R. Okafor', 'PLT-CGY-01', '2026-02-10'),
    ('WO-2026-0260', 'PMP-DMA02F-24', 'PM', 'Preventive Maintenance', '2026-02-18', '2026-02-18', 'CC-WTR-02', 4900.0, 4750.0, 'COMPLETED', 'LOW', 'Motor bearing temperature sensor replacement', 'A. Patel', 'PLT-CGY-01', '2026-02-01'),
    ('WO-2026-0290', 'PMP-DMA02B-18', 'PM', 'Preventive Maintenance', '2026-02-25', '2026-02-25', 'CC-WTR-02', 4800.0, 4650.0, 'COMPLETED', 'LOW', 'Motor alignment and vibration check', 'R. Okafor', 'PLT-CGY-01', '2026-02-01'),
    ('WO-2026-0310', 'PMP-DMA03D-05', 'PM', 'Preventive Maintenance', '2026-03-05', '2026-03-05', 'CC-WTR-03', 7500.0, 7200.0, 'COMPLETED', 'LOW', 'Semi-annual full maintenance — discharge valve + bearings', 'J. Makenzie', 'PLT-CGY-01', '2026-02-10'),
    ('WO-2026-0330', 'PMP-DMA04D-10', 'PM', 'Preventive Maintenance', '2026-03-08', '2026-03-08', 'CC-WTR-04', 5200.0, 5050.0, 'COMPLETED', 'LOW', 'Discharge pressure transducer calibration', 'A. Patel', 'PLT-CGY-01', '2026-02-15'),
    ('WO-2026-0340', 'PMP-DMA01D-15', 'PM', 'Preventive Maintenance', '2026-03-10', '2026-03-11', 'CC-WTR-01', 7200.0, 6890.0, 'COMPLETED', 'LOW', 'Motor bearing replacement (scheduled lifecycle)', 'M. Chen', 'PLT-CGY-01', '2026-02-15'),
    ('WO-2026-0350', 'PMP-DMA02C-20', 'CM', 'Corrective Maintenance', '2026-03-12', '2026-03-14', 'CC-WTR-02', 15800.0, 16200.0, 'COMPLETED', 'HIGH', 'Motor current anomaly — winding inspection and repair', 'J. Makenzie', 'PLT-CGY-01', '2026-03-12'),
    ('WO-2026-0370', 'PMP-DMA03C-04', 'PM', 'Preventive Maintenance', '2026-03-15', '2026-03-15', 'CC-WTR-03', 4600.0, 4400.0, 'COMPLETED', 'LOW', 'Motor current calibration', 'A. Patel', 'PLT-CGY-01', '2026-02-20'),
    ('WO-2026-0380', 'PMP-DMA04C-09', 'PM', 'Preventive Maintenance', '2026-03-18', '2026-03-18', 'CC-WTR-04', 4800.0, 4650.0, 'COMPLETED', 'LOW', 'Standard quarterly maintenance', 'M. Chen', 'PLT-CGY-01', '2026-02-25'),
    ('WO-2026-0391', 'PMP-DMA04A-06', 'PM', 'Preventive Maintenance', '2026-02-10', '2026-02-11', 'CC-WTR-04', 8750.0, 8320.0, 'COMPLETED', 'LOW', 'Semi-annual vibration alignment and bearing lubrication', 'T. Blackwood', 'PLT-CGY-01', '2026-01-15'),
    ('WO-2026-0410', 'PMP-DMA02C-19', 'PM', 'Preventive Maintenance', '2026-03-20', '2026-03-21', 'CC-WTR-02', 5100.0, 5050.0, 'COMPLETED', 'LOW', 'Discharge pressure valve inspection', 'A. Patel', 'PLT-CGY-01', '2026-03-01'),
    ('WO-2026-0430', 'PMP-DMA02D-21', 'PM', 'Preventive Maintenance', '2026-03-22', '2026-03-22', 'CC-WTR-02', 4300.0, 4150.0, 'COMPLETED', 'LOW', 'Quarterly bearing lubrication', 'M. Chen', 'PLT-CGY-01', '2026-03-01'),
    ('WO-2026-0455', 'PMP-DMA01A-11', 'INSP', 'Scheduled Inspection', '2026-06-01', NULL, 'CC-WTR-01', 4200.0, NULL, 'SCHEDULED', 'LOW', 'Bi-annual vibration analysis', 'M. Chen', 'PLT-CGY-01', '2026-04-10'),
    ('WO-2026-0480', 'PMP-DMA02F-25', 'CM', 'Corrective Maintenance', '2026-04-01', '2026-04-03', 'CC-WTR-02', 19800.0, 21100.0, 'COMPLETED', 'HIGH', 'Efficiency drop to 73% — impeller wear, full replacement', 'J. Makenzie', 'PLT-CGY-01', '2026-04-01'),
    ('WO-2026-0500', 'PMP-DMA02E-22', 'PM', 'Preventive Maintenance', '2026-04-05', '2026-04-05', 'CC-WTR-02', 5600.0, 5400.0, 'COMPLETED', 'LOW', 'Semi-annual pump overhaul', 'R. Okafor', 'PLT-CGY-01', '2026-03-15'),
    ('WO-2026-0510', 'PMP-DMA02E-23', 'INSP', 'Scheduled Inspection', '2026-04-08', NULL, 'CC-WTR-02', 3200.0, NULL, 'IN_PROGRESS', 'MEDIUM', 'Vibration trending review — elevated readings observed', 'T. Blackwood', 'PLT-CGY-01', '2026-03-25'),
    ('WO-2026-0520', 'PMP-DMA01C-14', 'INSP', 'Scheduled Inspection', '2026-04-15', '2026-04-15', 'CC-WTR-01', 3800.0, 3800.0, 'COMPLETED', 'MEDIUM', 'Efficiency audit — flagged by ops team', 'J. Makenzie', 'PLT-CGY-01', '2026-03-20'),
    ('WO-2026-0550', 'PMP-DMA03A-02', 'PM', 'Preventive Maintenance', '2026-04-12', '2026-04-12', 'CC-WTR-03', 5200.0, 5000.0, 'COMPLETED', 'LOW', 'Quarterly bearing inspection and lubrication', 'R. Okafor', 'PLT-CGY-01', '2026-03-20'),
    ('WO-2026-0560', 'PMP-DMA04D-10', 'INSP', 'Scheduled Inspection', '2026-04-18', NULL, 'CC-WTR-04', 3600.0, NULL, 'IN_PROGRESS', 'MEDIUM', 'Annual efficiency and vibration audit', 'A. Patel', 'PLT-CGY-01', '2026-03-28'),
    ('WO-2026-0580', 'PMP-DMA04B-08', 'INSP', 'Scheduled Inspection', '2026-04-20', '2026-04-20', 'CC-WTR-04', 4100.0, 3900.0, 'COMPLETED', 'MEDIUM', 'Post-repair 60-day verification', 'R. Okafor', 'PLT-CGY-01', '2026-03-25'),
    ('WO-2026-0612', 'PMP-DMA04A-06', 'PM', 'Preventive Maintenance', '2026-03-28', '2026-03-28', 'CC-WTR-04', 3200.0, 2980.0, 'COMPLETED', 'LOW', 'Motor current calibration and efficiency check', 'R. Okafor', 'PLT-CGY-01', '2026-03-01'),
    ('WO-2026-0811', 'PMP-DMA01B-12', 'PM', 'Preventive Maintenance', '2026-05-20', NULL, 'CC-WTR-01', 5800.0, NULL, 'SCHEDULED', 'LOW', 'Quarterly lubrication and alignment', 'T. Blackwood', 'PLT-CGY-01', '2026-04-15'),
    ('WO-2026-0820', 'PMP-DMA03C-04', 'INSP', 'Scheduled Inspection', '2026-05-18', NULL, 'CC-WTR-03', 3800.0, NULL, 'SCHEDULED', 'MEDIUM', 'Post-calibration 60-day check', 'A. Patel', 'PLT-CGY-01', '2026-04-15'),
    ('WO-2026-0830', 'PMP-DMA02B-17', 'INSP', 'Scheduled Inspection', '2026-05-10', NULL, 'CC-WTR-02', 6800.0, NULL, 'SCHEDULED', 'HIGH', 'Post-failure 90-day follow-up inspection', 'T. Blackwood', 'PLT-CGY-01', '2026-04-12'),
    ('WO-2026-0840', 'PMP-DMA04A-07', 'PM', 'Preventive Maintenance', '2026-05-12', NULL, 'CC-WTR-04', 5800.0, NULL, 'SCHEDULED', 'LOW', 'Quarterly bearing inspection', 'T. Blackwood', 'PLT-CGY-01', '2026-04-10'),
    ('WO-2026-0847', 'PMP-DMA04A-06', 'INSP', 'Scheduled Inspection', '2026-05-15', NULL, 'CC-WTR-04', 12400.0, NULL, 'SCHEDULED', 'MEDIUM', 'Quarterly bearing inspection — thrust bearing + motor bearings', 'J. Makenzie', 'PLT-CGY-01', '2026-04-01'),
    ('WO-2026-0850', 'PMP-DMA03A-01', 'PM', 'Preventive Maintenance', '2026-05-22', NULL, 'CC-WTR-03', 6800.0, NULL, 'SCHEDULED', 'LOW', 'Semi-annual overhaul', 'M. Chen', 'PLT-CGY-01', '2026-04-15'),
    ('WO-2026-0860', 'PMP-DMA02C-19', 'INSP', 'Scheduled Inspection', '2026-06-10', NULL, 'CC-WTR-02', 3500.0, NULL, 'SCHEDULED', 'LOW', 'Annual efficiency audit', 'A. Patel', 'PLT-CGY-01', '2026-04-25'),
    ('WO-2026-0870', 'PMP-DMA02A-16', 'PM', 'Preventive Maintenance', '2026-05-25', NULL, 'CC-WTR-02', 5400.0, NULL, 'SCHEDULED', 'LOW', 'Quarterly maintenance — suction chamber inspection', 'A. Patel', 'PLT-CGY-01', '2026-04-20'),
    ('WO-2026-0880', 'PMP-DMA04C-09', 'PM', 'Preventive Maintenance', '2026-06-15', NULL, 'CC-WTR-04', 4800.0, NULL, 'SCHEDULED', 'LOW', 'Standard quarterly maintenance', 'M. Chen', 'PLT-CGY-01', '2026-04-25'),
    ('WO-2026-0890', 'PMP-DMA02F-25', 'INSP', 'Scheduled Inspection', '2026-05-30', NULL, 'CC-WTR-02', 4500.0, NULL, 'SCHEDULED', 'HIGH', 'Post-repair verification — impeller replacement follow-up', 'J. Makenzie', 'PLT-CGY-01', '2026-04-20');


-- ======================================================================
-- SECTION 2: SAP_SPARE_PARTS (29 rows)
-- ======================================================================

CREATE OR REPLACE TABLE AVEVA_CONNECT.PUBLIC.SAP_SPARE_PARTS (
    MATERIAL_ID        VARCHAR(20),
    DESCRIPTION        VARCHAR(100),
    EQUIPMENT_MATCH    VARCHAR(30),
    PART_CATEGORY      VARCHAR(30),
    WAREHOUSE_LOCATION VARCHAR(50),
    QTY_ON_HAND        NUMBER(5,0),
    REORDER_POINT      NUMBER(5,0),
    LEAD_TIME_DAYS     NUMBER(5,0),
    UNIT_COST_USD      NUMBER(10,2),
    PREFERRED_VENDOR   VARCHAR(50),
    LAST_RECEIPT_DATE  DATE,
    SAP_PLANT          VARCHAR(20)
);

INSERT INTO AVEVA_CONNECT.PUBLIC.SAP_SPARE_PARTS
    (MATERIAL_ID, DESCRIPTION, EQUIPMENT_MATCH, PART_CATEGORY, WAREHOUSE_LOCATION,
     QTY_ON_HAND, REORDER_POINT, LEAD_TIME_DAYS, UNIT_COST_USD, PREFERRED_VENDOR,
     LAST_RECEIPT_DATE, SAP_PLANT)
VALUES
    ('M-4420', 'Thrust Bearing Kit — DMA Series', 'PMP-DMA*', 'BEARINGS', 'Calgary Main', 3, 2, 14, 2800.0, 'SKF Industrial', '2026-03-15', 'PLT-CGY-01'),
    ('M-4420-E', 'Thrust Bearing Kit — DMA Series', 'PMP-DMA*', 'BEARINGS', 'Edmonton Depot', 2, 1, 3, 2800.0, 'SKF Industrial', '2026-01-15', 'PLT-CGY-01'),
    ('M-4421', 'Motor Bearing Kit — Drive End', 'PMP-DMA*', 'BEARINGS', 'Calgary Main', 5, 3, 14, 1950.0, 'SKF Industrial', '2026-04-01', 'PLT-CGY-01'),
    ('M-4422', 'Motor Bearing Kit — Non-Drive End', 'PMP-DMA*', 'BEARINGS', 'Calgary Main', 4, 3, 14, 1850.0, 'SKF Industrial', '2026-03-20', 'PLT-CGY-01'),
    ('M-4423', 'Inboard Bearing Assembly', 'PMP-DMA*', 'BEARINGS', 'Calgary Main', 2, 2, 21, 3400.0, 'Timken Corp', '2026-02-28', 'PLT-CGY-01'),
    ('M-4424', 'Outboard Bearing Assembly', 'PMP-DMA*', 'BEARINGS', 'Calgary Main', 2, 2, 21, 3200.0, 'Timken Corp', '2026-02-28', 'PLT-CGY-01'),
    ('M-5510', 'Mechanical Seal Kit — Standard', 'PMP-DMA*', 'SEALS', 'Calgary Main', 8, 4, 7, 1200.0, 'Flowserve', '2026-04-10', 'PLT-CGY-01'),
    ('M-5510-E', 'Mechanical Seal Kit — Standard', 'PMP-DMA*', 'SEALS', 'Edmonton Depot', 4, 2, 3, 1200.0, 'Flowserve', '2026-02-20', 'PLT-CGY-01'),
    ('M-5511', 'Discharge Valve Seal', 'PMP-DMA*', 'SEALS', 'Calgary Main', 12, 6, 7, 480.0, 'Flowserve', '2026-04-05', 'PLT-CGY-01'),
    ('M-5512', 'Suction Chamber Gasket Set', 'PMP-DMA*', 'SEALS', 'Calgary Main', 6, 4, 10, 650.0, 'Garlock', '2026-03-22', 'PLT-CGY-01'),
    ('M-5513', 'Shaft Seal — High Pressure', 'PMP-DMA02*', 'SEALS', 'Calgary Main', 3, 2, 14, 2100.0, 'John Crane', '2026-03-10', 'PLT-CGY-01'),
    ('M-6610', 'Impeller Assembly — Standard Flow', 'PMP-DMA*', 'HYDRAULICS', 'Calgary Main', 1, 1, 42, 8500.0, 'Sulzer Pumps', '2026-01-20', 'PLT-CGY-01'),
    ('M-6610-E', 'Impeller Assembly — Standard Flow', 'PMP-DMA*', 'HYDRAULICS', 'Edmonton Depot', 1, 1, 3, 8500.0, 'Sulzer Pumps', '2025-12-01', 'PLT-CGY-01'),
    ('M-6611', 'Impeller Assembly — High Flow', 'PMP-DMA02F*', 'HYDRAULICS', 'Calgary Main', 0, 1, 42, 9200.0, 'Sulzer Pumps', '2025-11-15', 'PLT-CGY-01'),
    ('M-6612', 'Wear Ring Set', 'PMP-DMA*', 'HYDRAULICS', 'Calgary Main', 4, 3, 21, 1800.0, 'Sulzer Pumps', '2026-03-28', 'PLT-CGY-01'),
    ('M-6613', 'Diffuser Vane Assembly', 'PMP-DMA*', 'HYDRAULICS', 'Calgary Main', 1, 1, 35, 6200.0, 'Sulzer Pumps', '2026-02-15', 'PLT-CGY-01'),
    ('M-7710', 'Motor Winding Kit — 200kW', 'PMP-DMA*', 'MOTOR', 'Calgary Main', 1, 1, 28, 4800.0, 'WEG Electric', '2026-02-20', 'PLT-CGY-01'),
    ('M-7711', 'Motor Cooling Fan Assembly', 'PMP-DMA*', 'MOTOR', 'Calgary Main', 3, 2, 14, 1100.0, 'WEG Electric', '2026-03-25', 'PLT-CGY-01'),
    ('M-7712', 'Motor Stator Assembly', 'PMP-DMA*', 'MOTOR', 'Edmonton Depot', 0, 1, 56, 12500.0, 'WEG Electric', '2025-10-01', 'PLT-CGY-01'),
    ('M-7713', 'Variable Frequency Drive Module', 'PMP-DMA*', 'MOTOR', 'Calgary Main', 2, 1, 35, 7800.0, 'ABB', '2026-01-30', 'PLT-CGY-01'),
    ('M-8810', 'Vibration Sensor — Inboard', 'PMP-DMA*', 'SENSORS', 'Calgary Main', 6, 4, 10, 890.0, 'Bently Nevada', '2026-04-12', 'PLT-CGY-01'),
    ('M-8811', 'Vibration Sensor — Outboard', 'PMP-DMA*', 'SENSORS', 'Calgary Main', 5, 4, 10, 890.0, 'Bently Nevada', '2026-04-12', 'PLT-CGY-01'),
    ('M-8812', 'Temperature Probe — Bearing', 'PMP-DMA*', 'SENSORS', 'Calgary Main', 10, 6, 7, 340.0, 'Emerson', '2026-04-15', 'PLT-CGY-01'),
    ('M-8813', 'Pressure Transducer — Discharge', 'PMP-DMA*', 'SENSORS', 'Calgary Main', 4, 3, 14, 1450.0, 'Emerson', '2026-03-18', 'PLT-CGY-01'),
    ('M-8814', 'Flow Meter — Electromagnetic', 'PMP-DMA*', 'SENSORS', 'Edmonton Depot', 1, 1, 28, 5600.0, 'Endress+Hauser', '2026-02-10', 'PLT-CGY-01'),
    ('M-8815', 'Suction Chamber Level Sensor', 'PMP-DMA*', 'SENSORS', 'Calgary Main', 3, 2, 14, 1250.0, 'Emerson', '2026-03-05', 'PLT-CGY-01'),
    ('M-9910', 'Bearing Lubricant — SKF LGMT3 (5kg)', 'PMP-DMA*', 'CONSUMABLES', 'Calgary Main', 15, 8, 5, 185.0, 'SKF Industrial', '2026-04-20', 'PLT-CGY-01'),
    ('M-9911', 'Motor Cooling Fluid (20L)', 'PMP-DMA*', 'CONSUMABLES', 'Calgary Main', 8, 4, 5, 120.0, 'Shell Industrial', '2026-04-18', 'PLT-CGY-01'),
    ('M-9912', 'Hydraulic Oil — ISO 46 (200L drum)', 'PMP-DMA*', 'CONSUMABLES', 'Calgary Main', 4, 2, 7, 420.0, 'Shell Industrial', '2026-04-10', 'PLT-CGY-01');


-- ======================================================================
-- SECTION 3: PUMP_ANOMALY_OVERLAY (145 rows)
-- ======================================================================

CREATE OR REPLACE TABLE AVEVA_CONNECT.PUBLIC.PUMP_ANOMALY_OVERLAY (
    "Timestamp" TIMESTAMP_LTZ(6),
    "Name"      VARCHAR,
    "Field"     VARCHAR,
    "Value"     FLOAT
);

INSERT INTO AVEVA_CONNECT.PUBLIC.PUMP_ANOMALY_OVERLAY ("Timestamp", "Name", "Field", "Value")
VALUES
    ('2026-04-14 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Amps - Motor Value A', 298.5),
    ('2026-04-14 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Amps - Motor Value A', 305.2),
    ('2026-04-14 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Amps - Motor Value A', 318.7),
    ('2026-04-15 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Amps - Motor Value A', 335.4),
    ('2026-04-15 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Amps - Motor Value A', 352.1),
    ('2026-04-15 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Amps - Motor Value A', 361.8),
    ('2026-04-16 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Amps - Motor Value A', 342.5),
    ('2026-04-16 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Amps - Motor Value A', 310.8),
    ('2026-04-16 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Amps - Motor Value A', 295.2),
    ('2026-04-14 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Motor Power Value kW', 168.4),
    ('2026-04-15 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Motor Power Value kW', 212.6),
    ('2026-04-16 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Motor Power Value kW', 178.3),
    ('2026-04-14 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Pump Efficiency Value %', 74.1),
    ('2026-04-14 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Pump Efficiency Value %', 71.3),
    ('2026-04-14 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Pump Efficiency Value %', 65.8),
    ('2026-04-15 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Pump Efficiency Value %', 58.2),
    ('2026-04-15 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Pump Efficiency Value %', 48.7),
    ('2026-04-15 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Pump Efficiency Value %', 39.5),
    ('2026-04-16 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Pump Efficiency Value %', 45.6),
    ('2026-04-16 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Pump Efficiency Value %', 58.3);

INSERT INTO AVEVA_CONNECT.PUBLIC.PUMP_ANOMALY_OVERLAY ("Timestamp", "Name", "Field", "Value")
VALUES
    ('2026-04-16 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Pump Efficiency Value %', 68.9),
    ('2026-04-15 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Run Hours Since Last Maintenance Value h', 2529),
    ('2026-04-15 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Vibration X - Inboard Bearing Value', 0.82),
    ('2026-04-15 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Vibration X - Inboard Bearing Value', 1.15),
    ('2026-04-15 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA01C-13', 'Vibration X - Inboard Bearing Value', 1.42),
    ('2026-04-22 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Motor Power Value kW', 172.5),
    ('2026-04-23 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Motor Power Value kW', 185.3),
    ('2026-04-24 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Motor Power Value kW', 198.7),
    ('2026-04-25 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Motor Power Value kW', 205.1),
    ('2026-04-21 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Pump Efficiency Value %', 73.4),
    ('2026-04-21 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Pump Efficiency Value %', 72.8),
    ('2026-04-21 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Pump Efficiency Value %', 72.1),
    ('2026-04-22 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Pump Efficiency Value %', 71.5),
    ('2026-04-22 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Pump Efficiency Value %', 70.2),
    ('2026-04-22 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Pump Efficiency Value %', 68.9),
    ('2026-04-23 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Pump Efficiency Value %', 66.3),
    ('2026-04-23 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Pump Efficiency Value %', 62.1),
    ('2026-04-23 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Pump Efficiency Value %', 58.5),
    ('2026-04-24 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Pump Efficiency Value %', 55.2),
    ('2026-04-24 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Pump Efficiency Value %', 51.8);

INSERT INTO AVEVA_CONNECT.PUBLIC.PUMP_ANOMALY_OVERLAY ("Timestamp", "Name", "Field", "Value")
VALUES
    ('2026-04-24 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Pump Efficiency Value %', 48.3),
    ('2026-04-25 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Pump Efficiency Value %', 45.1),
    ('2026-04-25 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Pump Efficiency Value %', 42.3),
    ('2026-04-25 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Pump Efficiency Value %', 52.6),
    ('2026-04-21 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Run Hours Since Last Maintenance Value h', 2241),
    ('2026-04-25 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Run Hours Since Last Maintenance Value h', 2337),
    ('2026-04-21 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Temperature - Inboard Bearing Value °C', 54.8),
    ('2026-04-21 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Temperature - Inboard Bearing Value °C', 56.2),
    ('2026-04-21 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Temperature - Inboard Bearing Value °C', 57.5),
    ('2026-04-22 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Temperature - Inboard Bearing Value °C', 59.3),
    ('2026-04-22 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Temperature - Inboard Bearing Value °C', 63.1),
    ('2026-04-22 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Temperature - Inboard Bearing Value °C', 66.7),
    ('2026-04-23 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Temperature - Inboard Bearing Value °C', 71.4),
    ('2026-04-23 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Temperature - Inboard Bearing Value °C', 76.8),
    ('2026-04-23 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Temperature - Inboard Bearing Value °C', 80.2),
    ('2026-04-24 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Temperature - Inboard Bearing Value °C', 83.6),
    ('2026-04-24 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Temperature - Inboard Bearing Value °C', 87.1),
    ('2026-04-24 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Temperature - Inboard Bearing Value °C', 89.5),
    ('2026-04-25 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Temperature - Inboard Bearing Value °C', 91.2),
    ('2026-04-25 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Temperature - Inboard Bearing Value °C', 92.8);

INSERT INTO AVEVA_CONNECT.PUBLIC.PUMP_ANOMALY_OVERLAY ("Timestamp", "Name", "Field", "Value")
VALUES
    ('2026-04-25 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Temperature - Inboard Bearing Value °C', 85.4),
    ('2026-04-21 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Vibration X - Inboard Bearing Value', 0.62),
    ('2026-04-21 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Vibration X - Inboard Bearing Value', 0.68),
    ('2026-04-21 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Vibration X - Inboard Bearing Value', 0.71),
    ('2026-04-22 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Vibration X - Inboard Bearing Value', 0.78),
    ('2026-04-22 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Vibration X - Inboard Bearing Value', 0.89),
    ('2026-04-22 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Vibration X - Inboard Bearing Value', 0.97),
    ('2026-04-23 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Vibration X - Inboard Bearing Value', 1.12),
    ('2026-04-23 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Vibration X - Inboard Bearing Value', 1.35),
    ('2026-04-23 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Vibration X - Inboard Bearing Value', 1.48),
    ('2026-04-24 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Vibration X - Inboard Bearing Value', 1.62),
    ('2026-04-24 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Vibration X - Inboard Bearing Value', 1.81),
    ('2026-04-24 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Vibration X - Inboard Bearing Value', 1.95),
    ('2026-04-25 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Vibration X - Inboard Bearing Value', 2.05),
    ('2026-04-25 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Vibration X - Inboard Bearing Value', 2.18),
    ('2026-04-25 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02B-17', 'Vibration X - Inboard Bearing Value', 1.72),
    ('2026-03-27 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Motor Power Value kW', 175.2),
    ('2026-03-27 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Motor Power Value kW', 182.8),
    ('2026-03-27 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Motor Power Value kW', 189.4),
    ('2026-03-28 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Motor Power Value kW', 195.6);

INSERT INTO AVEVA_CONNECT.PUBLIC.PUMP_ANOMALY_OVERLAY ("Timestamp", "Name", "Field", "Value")
VALUES
    ('2026-03-28 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Motor Power Value kW', 201.3),
    ('2026-03-29 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Motor Power Value kW', 204.8),
    ('2026-03-25 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Pump Efficiency Value %', 71.8),
    ('2026-03-25 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Pump Efficiency Value %', 70.3),
    ('2026-03-25 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Pump Efficiency Value %', 69.1),
    ('2026-03-26 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Pump Efficiency Value %', 67.5),
    ('2026-03-26 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Pump Efficiency Value %', 65.8),
    ('2026-03-26 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Pump Efficiency Value %', 64.2),
    ('2026-03-27 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Pump Efficiency Value %', 63.1),
    ('2026-03-27 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Pump Efficiency Value %', 61.5),
    ('2026-03-27 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Pump Efficiency Value %', 60.2),
    ('2026-03-28 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Pump Efficiency Value %', 59.8),
    ('2026-03-28 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Pump Efficiency Value %', 58.2),
    ('2026-03-28 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Pump Efficiency Value %', 57.5),
    ('2026-03-29 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Pump Efficiency Value %', 57.1),
    ('2026-03-29 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Pump Efficiency Value %', 56.8),
    ('2026-03-25 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Run Hours Since Last Maintenance Value h', 2480),
    ('2026-03-29 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Run Hours Since Last Maintenance Value h', 2576),
    ('2026-03-25 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Vibration X - Inboard Bearing Value', 0.72),
    ('2026-03-25 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Vibration X - Inboard Bearing Value', 0.81);

INSERT INTO AVEVA_CONNECT.PUBLIC.PUMP_ANOMALY_OVERLAY ("Timestamp", "Name", "Field", "Value")
VALUES
    ('2026-03-25 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Vibration X - Inboard Bearing Value', 0.88),
    ('2026-03-26 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Vibration X - Inboard Bearing Value', 0.95),
    ('2026-03-26 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Vibration X - Inboard Bearing Value', 1.08),
    ('2026-03-26 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Vibration X - Inboard Bearing Value', 1.15),
    ('2026-03-27 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Vibration X - Inboard Bearing Value', 1.22),
    ('2026-03-27 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Vibration X - Inboard Bearing Value', 1.31),
    ('2026-03-27 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA02F-25', 'Vibration X - Inboard Bearing Value', 1.38);

-- PMP-DMA04A-06: Thrust bearing degradation pattern (Apr 24-27)
-- Bearing temp escalating well above predicted (~65.5°C), vibration rising, efficiency dropping
INSERT INTO AVEVA_CONNECT.PUBLIC.PUMP_ANOMALY_OVERLAY ("Timestamp", "Name", "Field", "Value")
VALUES
    -- Thrust Bearing Temperature: escalating 66 → 72 → 78 → 82°C (predicted ~65.5°C)
    ('2026-04-24 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Thrust Bearing Temperature 3 Value °C', 66.8),
    ('2026-04-24 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Thrust Bearing Temperature 3 Value °C', 68.4),
    ('2026-04-24 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Thrust Bearing Temperature 3 Value °C', 70.2),
    ('2026-04-25 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Thrust Bearing Temperature 3 Value °C', 72.5),
    ('2026-04-25 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Thrust Bearing Temperature 3 Value °C', 74.8),
    ('2026-04-25 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Thrust Bearing Temperature 3 Value °C', 76.3),
    ('2026-04-26 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Thrust Bearing Temperature 3 Value °C', 78.1),
    ('2026-04-26 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Thrust Bearing Temperature 3 Value °C', 79.9),
    ('2026-04-26 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Thrust Bearing Temperature 3 Value °C', 81.2),
    ('2026-04-27 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Thrust Bearing Temperature 3 Value °C', 82.6),
    -- Vibration: escalating 0.55 → 1.6 mm/s (normal ~0.45)
    ('2026-04-24 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Vibration X - Inboard Bearing Value', 0.58),
    ('2026-04-24 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Vibration X - Inboard Bearing Value', 0.67),
    ('2026-04-24 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Vibration X - Inboard Bearing Value', 0.78),
    ('2026-04-25 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Vibration X - Inboard Bearing Value', 0.91),
    ('2026-04-25 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Vibration X - Inboard Bearing Value', 1.08),
    ('2026-04-25 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Vibration X - Inboard Bearing Value', 1.22),
    ('2026-04-26 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Vibration X - Inboard Bearing Value', 1.38),
    ('2026-04-26 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Vibration X - Inboard Bearing Value', 1.52),
    ('2026-04-26 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Vibration X - Inboard Bearing Value', 1.61),
    ('2026-04-27 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Vibration X - Inboard Bearing Value', 1.74);

INSERT INTO AVEVA_CONNECT.PUBLIC.PUMP_ANOMALY_OVERLAY ("Timestamp", "Name", "Field", "Value")
VALUES
    -- Efficiency: dropping 72% → 58% (normal ~74%)
    ('2026-04-24 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Pump Efficiency Value %', 72.1),
    ('2026-04-24 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Pump Efficiency Value %', 70.5),
    ('2026-04-24 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Pump Efficiency Value %', 68.8),
    ('2026-04-25 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Pump Efficiency Value %', 66.4),
    ('2026-04-25 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Pump Efficiency Value %', 64.1),
    ('2026-04-25 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Pump Efficiency Value %', 62.3),
    ('2026-04-26 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Pump Efficiency Value %', 60.8),
    ('2026-04-26 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Pump Efficiency Value %', 59.2),
    ('2026-04-26 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Pump Efficiency Value %', 58.5),
    ('2026-04-27 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Pump Efficiency Value %', 57.8),
    -- Motor Current: rising 325A → 358A (bearing friction increasing load)
    ('2026-04-24 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Motor Current Value A', 325.8),
    ('2026-04-24 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Motor Current Value A', 331.2),
    ('2026-04-25 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Motor Current Value A', 338.5),
    ('2026-04-26 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Motor Current Value A', 345.1),
    ('2026-04-26 18:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Motor Current Value A', 351.8),
    ('2026-04-27 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Motor Current Value A', 358.2),
    -- Run Hours (high)
    ('2026-04-25 12:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Run Hours Since Last Maintenance Value h', 2685),
    ('2026-04-27 06:00:00.000 -0700'::TIMESTAMP_LTZ, 'PMP-DMA04A-06', 'Run Hours Since Last Maintenance Value h', 2733);


-- ======================================================================
-- SECTION 4: INDUSTRIAL_KNOWLEDGE_BASE (28 rows)
-- ======================================================================

CREATE OR REPLACE TABLE AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE (
    DOC_ID         VARCHAR(20),
    TITLE          VARCHAR(300),
    CONTENT        VARCHAR(16000),
    DOC_TYPE       VARCHAR(50),
    SOURCE         VARCHAR(100),
    PUBLISHED_DATE DATE
);

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-BP-001',
    'Best Practice: Integrating Weather Data into Industrial Pump Monitoring',
    'Industry Best Practice Document — Weather-Integrated Pump Health Monitoring. Authors: Calgary Water Utility Operations Team. Background: Traditional pump monitoring systems rely exclusively on sensor data from the equipment itself. While effective for detecting mechanical degradation, these systems generate false positives when environmental factors (temperature, humidity, barometric pressure) cause sensor readings to deviate from normal ranges without any equipment issue. Problem Statement: Over a 12-month period, our 25-pump DMA network generated 47 vibration alerts and 23 bearing temperature alerts. Investigation revealed that 31 of the vibration alerts (66%) and 12 of the temperature alerts (52%) were environmentally driven — the equipment was healthy, but ambient conditions caused readings to cross static alarm thresholds. Each false alarm costs approximately $4,200-6,000 in unnecessary inspection and lost production time. Total cost of false alarms: $223,000/year. Solution: We integrated WeatherSource data from the Snowflake Marketplace into our monitoring workflow. For each alert, the system now automatically: 1) Queries WeatherSource for ambient conditions at the time of the alert. 2) Calculates the temperature-vibration and temperature-bearing-temp correlations over the preceding 7 days. 3) If correlation r > 0.25, classifies the alert as "environmentally influenced" and recommends continued monitoring rather than emergency inspection. 4) Routes the classification to the AVEVA predictive model dashboard for operator review. Results (6 months post-implementation): False positive rate reduced from 58% to 12%. Unnecessary inspections reduced by 78%. Annual savings: estimated $174,000 in avoided false alarm costs. Zero missed genuine mechanical events — all 8 actual equipment issues were correctly identified and addressed proactively.',
    'BEST_PRACTICE',
    'Calgary Water Utility',
    '2024-09-01';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-BP-002',
    'Best Practice: AI-Augmented Decision Making for Industrial Operations',
    'Best Practice Document — AI-Augmented Decision Making for Water Utility Operations. Published by: Canadian Water and Wastewater Association (CWWA). Introduction: Artificial intelligence is transforming how water utilities make operational decisions. Rather than replacing human operators, AI serves as a force multiplier — analyzing vast amounts of data across multiple sources and presenting synthesized recommendations for human review and approval. The Agentic Approach: Leading utilities are moving from single-prompt AI interactions to multi-step agentic workflows where the AI system: 1) Analyzes structured operational data (sensor readings, predictive model outputs, efficiency metrics). 2) Retrieves relevant unstructured knowledge (OEM bulletins, maintenance SOPs, incident reports, industry standards). 3) Cross-references with business systems (SAP work orders, spare parts inventory, cost data). 4) Synthesizes all sources into a grounded recommendation with citations and confidence levels. This approach mirrors how experienced engineers make decisions — they do not just look at a single metric, but consider the full context including their institutional knowledge and experience. Key Requirements: The AI system must be able to cite its sources — operators need to verify that recommendations are grounded in legitimate standards and data, not hallucinated. Retrieval-augmented generation (RAG) using services like Snowflake Cortex Search ensures that AI recommendations reference actual documents in the knowledge base. Transparency in the reasoning chain — showing each step of the analysis — builds operator trust and enables effective human oversight. Benefits: Utilities implementing agentic AI workflows report: 40% faster decision-making, 55% reduction in false positive responses, 30% reduction in maintenance costs through more targeted interventions, and 90%+ operator satisfaction with AI-assisted recommendations.',
    'BEST_PRACTICE',
    'Canadian Water and Wastewater Association',
    '2024-11-01';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-CS-001',
    'Technical Note: Interpreting AVEVA Predictive Model Deviations in Context',
    'Technical Note TN-2024-015. Subject: Framework for Interpreting AVEVA Predictive Model Deviations with Multi-Source Context. Author: Dr. Sarah Chen, Reliability Engineering Lead. Problem: AVEVA predictive models are highly accurate for detecting mechanical degradation patterns. However, they are trained primarily on equipment sensor data and do not inherently account for external factors. This leads to false positive alerts when environmental conditions cause sensor readings to deviate from model predictions. Framework for Deviation Analysis: When the AVEVA model shows a deviation between predicted and actual values: Step 1 — Quantify: Calculate the magnitude and trend of the deviation. Is it increasing, stable, or decreasing? Step 2 — Correlate: Check environmental factors. Query weather data for the same time period. Calculate Pearson correlation between the deviating parameter and ambient temperature, humidity, and wind speed. Step 3 — Contextualize: Cross-reference with maintenance history (SAP). When was the last maintenance? How many run hours since? Are there open work orders? Step 4 — Search Knowledge: Query the industrial knowledge base for relevant OEM bulletins, failure mode patterns, and historical incident reports that match the current signature. Step 5 — Synthesize: Combine all evidence to determine if the deviation is: (a) environmentally driven (high weather correlation, recent maintenance, no other anomalies), (b) mechanical degradation (low weather correlation, high run hours, multiple correlated anomalies), or (c) inconclusive (requires additional data or physical inspection). This multi-step analysis reduces false positives by 60-80% while maintaining 100% detection of genuine mechanical issues. It is the basis for the "agentic" AI workflow where Cortex AI performs each step autonomously, presenting the complete analysis to the operator.',
    'TECHNICAL_NOTE',
    'Reliability Engineering',
    '2024-08-20';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-ENR-001',
    'Energy Cost Analysis: Alberta Industrial Electricity Rates Impact on Pump Operations',
    'Alberta Utilities Commission — Energy Cost Analysis for Industrial Water Pumping (2024). Alberta Pool Price Trends: The Alberta electricity market operates on a deregulated pool price model. Average pool prices in 2024: $85-120/MWh during peak hours (7am-11pm), $45-70/MWh off-peak. For a fleet of 25 water distribution pumps averaging 180 kW each, annual electricity cost is approximately $2.8-3.6 million depending on demand profile. Pump Efficiency Impact on Energy Cost: At an average electricity cost of $0.095/kWh, each 1% improvement in pump efficiency across the fleet saves approximately $37,500/year. A typical degraded pump operating at 68% efficiency vs design 78% efficiency wastes approximately $15,600/year per pump. Early detection of efficiency degradation through AVEVA predictive models, combined with proactive maintenance, typically recovers 5-8% fleet-wide efficiency, representing annual savings of $187,500-300,000. Cost of Unplanned Shutdowns: Direct costs: emergency repair ($45,000-70,000), overtime labor ($8,000-18,000), expedited parts ($5,000-15,000). Indirect costs: regulatory penalties for service interruption ($10,000-50,000), customer compensation, reputation damage. Average total cost per unplanned shutdown event: $85,000-165,000. Predictive maintenance programs demonstrating weather-integrated analytics reduce unplanned shutdowns by 70-80%, representing annual avoided costs of $400,000-800,000 for a 25-pump fleet.',
    'ENERGY_ANALYSIS',
    'Alberta Utilities Commission',
    '2024-07-01';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-ENR-002',
    'McKinsey Global Institute: Predictive Maintenance ROI in Water Utilities',
    'McKinsey Global Institute Report — Predictive Maintenance in Water Utilities: ROI Analysis and Best Practices (2024 Update). Key Findings: Water utilities implementing advanced predictive maintenance (combining IoT sensors, AI/ML models, and external data integration) achieve: 25-35% reduction in maintenance costs, 60-75% reduction in unplanned downtime, 10-20% extension of equipment life, and 5-10% improvement in energy efficiency. The highest-performing utilities distinguish themselves by integrating multiple data sources beyond equipment sensors: weather data (reduces false positive maintenance triggers by 40%), maintenance history from ERP systems like SAP (enables cost-optimized scheduling), and unstructured knowledge (OEM bulletins, industry standards) for evidence-based decision-making. The concept of "The Complete Picture" — where operational technology data (what is happening), external context data (why it is happening), ERP data (what it costs), and AI (what to do about it) are unified on a single platform — represents the frontier of predictive maintenance maturity. Early adopters report ROI of 300-500% within 18 months. Technology Stack: Leading implementations use cloud data platforms (e.g., Snowflake) to unify structured sensor data, semi-structured IoT logs, and unstructured documents. This enables cross-source analytics that are impossible in siloed legacy systems.',
    'INDUSTRY_REPORT',
    'McKinsey Global Institute',
    '2024-04-15';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-FM-001',
    'Failure Mode Analysis: Common Failure Patterns in DMA Water Pump Bearings',
    'Failure Mode and Effects Analysis (FMEA) — Thrust Bearings in DMA Water Distribution Pumps. Based on 5-year failure data from 150+ pump installations across Western Canada. Failure Mode 1 — Lubricant Degradation (38% of failures): Cause: Extended re-greasing intervals, contamination ingress, or thermal breakdown of lubricant in high-temperature environments. Detection: Gradual bearing temperature increase of 1-2°C/week, AVEVA predicted vs actual deviation increasing linearly. Vibration may remain normal until late stage. Time to failure from first detectable sign: 4-8 weeks. Failure Mode 2 — Fatigue Spalling (26% of failures): Cause: Normal wear progression, accelerated by misalignment or overload. Detection: Characteristic vibration signature at bearing defect frequencies (BPFO, BPFI, BSF). AVEVA vibration trending shows step increase. Time to failure: 2-6 weeks from first crack initiation. Failure Mode 3 — Thermal Runaway (18% of failures): Cause: Combination of reduced lubrication, high ambient temperature, and high load. Rapid positive feedback loop: friction → heat → lubricant breakdown → more friction. Detection: Rapid temperature rise (>5°C/day), often preceded by period of gradual increase. Time to failure: 24-72 hours once thermal runaway begins. CRITICAL: This failure mode progresses faster than procurement lead times for replacement parts. Failure Mode 4 — Electrical Erosion (11% of failures): Cause: Stray currents through bearings due to VFD operation or grounding issues. Detection: Random high-frequency vibration, bearing noise, pit marks visible during inspection. Failure Mode 5 — Installation Error (7% of failures): Cause: Incorrect preload, contamination during assembly, shaft tolerance out of spec. Detection: Abnormal vibration or temperature immediately after maintenance. Typically detected within first 100 run hours.',
    'FAILURE_ANALYSIS',
    'Reliability Engineering Team',
    '2024-06-01';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-FM-002',
    'Case Study: How Snowflake + AVEVA Prevented a $165,000 Shutdown at Edmonton Water Utility',
    'Case Study — Proactive Maintenance Success at Edmonton Water Utility. Date: November 2024. Facility: Goldbar Water Treatment Plant, DMA Zone 3. Equipment: 315 kW centrifugal pump serving 45,000 connections. Situation: The AVEVA predictive model detected a bearing temperature deviation of +4.2°C from predicted baseline over 7 days. Traditional monitoring would have classified this as an early-stage mechanical issue and triggered an emergency inspection work order. New Approach: The integrated monitoring system (AVEVA + Snowflake + WeatherSource + SAP) performed the following automated analysis: Step 1) Queried WeatherSource data: Edmonton experienced an unusual warm spell with average temperature 8°C above seasonal norm. Step 2) Calculated temperature-vibration correlation: r = 0.34 over the preceding 14 days, indicating significant environmental influence. Step 3) Compared with historical incidents: Similar pattern to IR-2024-0234 (Calgary false alarm event). Step 4) Checked SAP maintenance history: Bearing was replaced 1,800h ago (within service life). Step 5) Generated recommendation: Continue monitoring, reclassify from ALARM to WATCH, schedule routine inspection at next planned outage. Outcome: The pump continued operating normally. Temperature deviation returned to normal within 5 days as weather normalized. The utility avoided an unnecessary emergency shutdown that would have cost an estimated $165,000 (emergency inspection: $6,000, production loss during shutdown: $89,000, restart and verification: $12,000, overtime labor: $8,000, regulatory reporting: $50,000). Annual Impact: This single incident avoidance paid for 2 years of the Snowflake Marketplace WeatherSource subscription and Cortex AI compute costs.',
    'CASE_STUDY',
    'Edmonton Water Utility',
    '2024-12-01';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-INC-001',
    'Incident Report IR-2023-0891: Thermal Runaway Event at DMA02 Pump Station',
    'Incident Report IR-2023-0891. Date: September 14, 2023. Location: DMA02 Pump Station, Calgary Water Distribution Network. Equipment: PMP-DMA02B-17, Sulzer MSD 80-250 centrifugal pump, 200 kW WEG W22 motor. Summary: Unplanned emergency shutdown due to thrust bearing failure and thermal runaway. The bearing temperature rose from a normal operating range of 58-63°C to 94°C over a 5-day period before the trip threshold was reached. Root Cause Analysis: The primary cause was determined to be lubricant degradation due to contamination with fine particulate matter entering through a deteriorated bearing housing seal. Contributing factors included: an unusually warm period (ambient temperatures 32-36°C, approximately 8°C above seasonal average) which reduced the thermal margin, and the bearing having accumulated 3,200 run hours since last re-greasing (recommended interval: 2,800h for high-temperature-variability installations per SKF TB-2024-0147). Timeline: Day 1 — Bearing temp 63°C (normal). Day 2 — 68°C (AVEVA model predicted 64°C, deviation +4°C). Day 3 — 74°C (deviation +8°C, alert threshold crossed). Day 4 — 82°C (deviation +16°C, alarm threshold crossed, maintenance work order created). Day 5 — 94°C (trip threshold, emergency shutdown). Damage: Bearing cage deformation, inner raceway spalling, shaft scoring requiring 0.05mm chrome plating repair. Total Cost: $67,400 (emergency parts: $12,800, overtime labor: $18,600, production loss: $28,000, shaft repair: $8,000). Lessons Learned: 1) Dynamic alarm thresholds incorporating ambient temperature would have triggered investigation 2 days earlier. 2) Integration of weather data into the monitoring system would have identified the contributing environmental factor. 3) SAP spare parts inventory showed 0 bearing kits at Calgary Main at the time — 14-day lead time for procurement caused extended downtime. Recommendation: Maintain minimum 2 bearing kits (M-4420) at Calgary Main warehouse at all times.',
    'INCIDENT_REPORT',
    'Operations Safety Team',
    '2023-10-01';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-INC-002',
    'Incident Report IR-2024-0234: False Alarm — Temperature-Induced Vibration Spike at DMA04',
    'Incident Report IR-2024-0234. Date: February 8, 2024. Location: DMA04 Pump Station, Calgary Water Distribution Network. Equipment: PMP-DMA04A-06, Sulzer MSD 80-250 centrifugal pump, 200 kW WEG W22 motor. Summary: A vibration spike triggered an alarm condition, leading to an unnecessary emergency inspection. Investigation revealed the vibration increase was entirely attributable to a rapid ambient temperature change (chinook wind event). False Alarm Details: On February 7, ambient temperature in Calgary rose from -18°C to +12°C within 8 hours (a chinook event). Inboard bearing vibration increased from 0.45 mm/s to 0.82 mm/s within the same period, crossing the alert threshold of 0.8 mm/s. An emergency inspection was ordered, requiring pump isolation and 6 hours of technician time. Findings: Bearing inspection revealed no mechanical issues. Vibration returned to 0.48 mm/s within 48 hours as temperatures stabilized. The vibration increase was caused by differential thermal expansion between the pump casing and shaft, temporarily altering bearing clearances. Cost of False Alarm: Technician labor: $1,800. Lost production during pump isolation: $4,200. Total unnecessary cost: $6,000. Root Cause: The AVEVA predictive model for this pump did not include ambient temperature as an input variable. The model predicted stable vibration of 0.46 mm/s while actual rose to 0.82 mm/s — a deviation that appeared anomalous but was environmentally driven. Corrective Action: 1) Integrated WeatherSource data from Snowflake Marketplace into the monitoring workflow. 2) Established a correlation baseline (r = 0.31 for temperature-vibration on this pump). 3) Implemented a rule: if vibration deviation from predicted value correlates with ambient temperature change (r > 0.25 over preceding 7 days), classify as environmental and continue monitoring rather than triggering emergency inspection. Result: This integration has prevented 4 additional false alarm inspections in the following 6 months, saving an estimated $24,000.',
    'INCIDENT_REPORT',
    'Operations Safety Team',
    '2024-03-15';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-INC-003',
    'Incident Report IR-2024-0567: Impeller Cavitation Damage at DMA02 Station',
    'Incident Report IR-2024-0567. Date: July 22, 2024. Location: DMA02 Pump Station. Equipment: PMP-DMA02F-25. Summary: Pump efficiency declined from 78.2% to 56.8% over a 5-day period in late March 2024. Motor power consumption simultaneously increased from 185 kW to 204 kW at constant flow rate, indicating significant internal losses. Root Cause: Advanced cavitation erosion on the impeller leading edge, combined with wear ring clearance that had increased to 0.62mm (maximum allowable: 0.50mm per SOP-MNT-6600). The cavitation was initiated by a temporary reduction in suction pressure due to a distribution network pressure transient. Damage Assessment: Impeller vane thickness reduced by 22% at leading edge (replacement threshold: 15%). Wear rings worn beyond serviceable limits. Pump was producing only 72% of rated flow at rated head. Repair: Impeller replacement (M-6611, $18,500) and wear ring replacement ($3,200). Total repair cost: $26,400 including labor. Downtime: 4 days (parts were available at Calgary Main warehouse). Predictive Indicators: The AVEVA predictive model showed a sustained efficiency deviation of -8% beginning 3 days before the acute decline. Motor current deviation was +4% over the same period. If the SAP work order had been created when the AVEVA deviation exceeded the 5% threshold (per SOP-MNT-6600), the impeller could have been inspected and potentially saved with wear ring replacement only ($3,200 vs $26,400). Key Learning: Early intervention based on AVEVA predictive model deviations, combined with SAP inventory verification, can reduce repair costs by up to 87%.',
    'INCIDENT_REPORT',
    'Operations Safety Team',
    '2024-08-10';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-OEM-001',
    'SKF Technical Bulletin: Thrust Bearing Temperature Limits for Centrifugal Pumps',
    'SKF Technical Bulletin TB-2024-0147. Subject: Operating Temperature Limits and Alarm Thresholds for Thrust Bearings in Horizontal Centrifugal Water Pumps. Applicable Models: SKF 29340E, 29344E, 29348E series thrust bearings commonly installed in municipal water distribution pumps rated 100-250 kW. Normal Operating Range: Thrust bearing temperatures should remain within 55-70°C under standard load conditions. A sustained temperature above 75°C indicates abnormal operation and warrants investigation. Critical Threshold: Temperatures exceeding 85°C require immediate operational review. At 90°C, bearing lubricant viscosity drops below minimum film thickness requirements, accelerating wear. Above 95°C, risk of thermal runaway increases significantly — bearing cage deformation and raceway spalling may occur within 48-72 hours of sustained operation. Environmental Factors: External ambient temperature significantly affects bearing operating temperature. For every 10°C increase in ambient temperature, thrust bearing temperature typically increases by 3-5°C due to reduced heat dissipation through the bearing housing. Installations in regions with high temperature variability (e.g., Canadian prairies with 30-40°C seasonal swings) should adjust alarm thresholds seasonally. Recommendation: For pumps operating in variable climate zones, implement dynamic alarm thresholds that account for ambient temperature. A deviation of more than 6°C from the AVEVA predictive model baseline should trigger an inspection work order, while a deviation exceeding 10°C warrants expedited bearing inspection. Lubrication: Use SKF LGWA 2 wide-temperature grease for installations subject to temperature swings exceeding 25°C. Re-greasing interval should be reduced from 4000h to 2800h in high-variability environments.',
    'OEM_BULLETIN',
    'SKF Industrial',
    '2024-03-15';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-OEM-002',
    'Sulzer Pump Technical Advisory: Vibration Monitoring Best Practices for DMA Water Networks',
    'Sulzer Technical Advisory TA-2024-089. Subject: Vibration Monitoring and Diagnostic Thresholds for Horizontal Split-Case Centrifugal Pumps in District Metered Area (DMA) Water Distribution Networks. Background: DMA water networks operate pumps under variable demand conditions, leading to flow rate fluctuations that directly impact vibration signatures. Unlike constant-speed industrial applications, DMA pumps experience frequent load changes that must be distinguished from mechanical degradation. Vibration Thresholds (per ISO 10816-7): Normal operation: 0.2-0.8 mm/s RMS at inboard bearing. Alert level: 0.8-1.2 mm/s RMS — schedule inspection within 30 days. Alarm level: 1.2-2.0 mm/s RMS — schedule inspection within 7 days. Trip level: >2.0 mm/s RMS — immediate shutdown recommended. Important: These thresholds assume stable operating conditions. Environmental factors such as ambient temperature, wind loading on exposed pump houses, and thermal cycling of the pump casing can cause vibration increases of 0.1-0.3 mm/s that do not indicate mechanical issues. Temperature-Vibration Correlation: Field studies across 14 DMA installations in Western Canada show a consistent correlation (Pearson r = 0.28-0.35) between ambient temperature and inboard bearing vibration. This is caused by differential thermal expansion between the bearing housing (cast iron, CTE 10.8 µm/m/°C) and the shaft (AISI 4140 steel, CTE 11.2 µm/m/°C), which alters bearing preload and clearances. During rapid temperature swings (>15°C in 48 hours), vibration can spike by 0.2-0.4 mm/s without any mechanical degradation. Recommendation: Correlate vibration trends with local weather data before scheduling unplanned maintenance. Predictive models should incorporate ambient temperature as an input variable.',
    'OEM_BULLETIN',
    'Sulzer Pumps',
    '2024-06-22';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-OEM-003',
    'WEG Motors Application Note: Motor Current Signatures in Variable-Load Pump Applications',
    'WEG Application Note AN-W7-2024-031. Subject: Interpreting Motor Current Signatures for Centrifugal Pump Health Monitoring. Applicable to: WEG W22 series motors, 150-315 kW, driving horizontal centrifugal pumps via direct coupling. Motor Current Baseline: For a 200 kW centrifugal pump motor operating at rated conditions, expect nameplate current draw of 310-330A at full load. Current draw below 290A suggests the pump is operating significantly below its best efficiency point (BEP), while sustained current above 345A indicates overload conditions that may result from impeller wear, increased system head, or mechanical binding. Current Deviation Analysis: A gradual increase in motor current of 3-5% over 30 days, without corresponding changes in system demand, typically indicates impeller wear or seal degradation increasing hydraulic losses. A sudden current spike of >10% followed by sustained elevated current suggests mechanical binding — inspect coupling alignment, bearing condition, and impeller clearances. Temperature Effects on Motor Current: Motor winding resistance increases with temperature (copper has a temperature coefficient of 0.00393/°C). For every 10°C increase in ambient temperature, motor current may decrease by 1-2% while power consumption remains constant due to increased I²R losses. This effect should be accounted for in current-based predictive models. Integration with Predictive Analytics: When combined with AVEVA predictive models, motor current deviations should be cross-referenced with bearing temperature and vibration data. A simultaneous increase in bearing temperature, vibration, and motor current strongly suggests mechanical degradation. An increase in bearing temperature with stable motor current more likely indicates an environmental or lubrication issue.',
    'OEM_BULLETIN',
    'WEG Motors',
    '2024-01-10';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-OEM-004',
    'Flowserve Technical Bulletin: Seal Maintenance and Leakage Prevention for Water Pumps',
    'Flowserve Technical Bulletin FTB-2024-073. Subject: Mechanical Seal Maintenance for Horizontal Centrifugal Pumps in Municipal Water Service. Seal Types: For clean water service in DMA networks, Type 1 single mechanical seals (carbon/silicon carbide) are standard. Seal life expectancy: 18,000-24,000 operating hours under normal conditions. Leakage Indicators: Minor weeping (<0.5 mL/min) is normal for running-in period. Visible drip rate (>2 mL/min) indicates seal face wear — schedule replacement within 30 days. Significant leakage (>10 mL/min) requires immediate intervention. Efficiency Impact: A degraded seal increases pump power consumption by 2-4% due to increased friction and internal recirculation. AVEVA efficiency monitoring will show this as a gradual decline in pump efficiency without corresponding changes in vibration or bearing temperature. Temperature Effects on Seals: Rapid temperature changes cause differential thermal expansion between seal faces, temporarily increasing leakage. During chinook events in Alberta (temperature swings of 20-30°C in 24 hours), seal leakage may temporarily increase without indicating seal failure. Allow 48 hours after temperature stabilization before assessing seal condition. SAP Material References: Standard seal kit: M-5510, $1,850, 7-day lead time. Emergency seal kit (includes all O-rings and secondary seal components): M-5515, $2,400, available at Calgary Main warehouse.',
    'OEM_BULLETIN',
    'Flowserve Corporation',
    '2024-05-10';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-OEM-005',
    'ABB Technical Guide: Variable Frequency Drive Impact on Pump Bearing Life',
    'ABB Technical Guide TG-2024-112. Subject: Impact of Variable Frequency Drive (VFD) Operation on Bearing Life in Centrifugal Pumps. VFD-Induced Bearing Currents: VFDs generate common-mode voltage that can cause bearing electrical erosion. For pumps operated via ABB ACS880 or similar drives, shaft voltage should be maintained below 0.3V peak. Above this threshold, electrical discharge machining (EDM) of bearing raceways occurs, leading to fluting damage visible as parallel grooves on the raceway surface. Detection: EDM damage manifests as: 1) Broadband high-frequency vibration increase (characteristically above 2 kHz). 2) Audible bearing noise (distinctive crackling). 3) Gradual bearing temperature increase of 3-8°C above baseline over weeks to months. AVEVA predictive models may detect the temperature increase but cannot distinguish electrical erosion from lubrication issues based on temperature alone. Cross-referencing with vibration frequency analysis is essential. Prevention: Install shaft grounding rings (AEGIS or equivalent) on all VFD-driven pump motors. For existing installations without grounding rings, inspect bearings at 4,000h intervals rather than the standard 6,000h. Ensure common-mode filter is installed between VFD and motor. Interaction with Environmental Factors: VFD bearing currents are not temperature-dependent. Therefore, if bearing temperature increases correlate strongly with ambient temperature (r > 0.25), electrical erosion can be ruled out as the cause. This distinction is critical for maintenance planning — electrical erosion requires motor bearing replacement ($4,200) plus grounding ring installation ($800), while temperature-related issues may only require lubrication adjustment.',
    'OEM_BULLETIN',
    'ABB Ltd',
    '2024-02-28';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-OP-001',
    'Operational Intelligence: DMA Zone Performance Benchmarking Report Q1 2026',
    'DMA Zone Performance Benchmarking — Q1 2026. Calgary Water Distribution Network. Summary: Fleet-wide analysis of 25 pumps across 4 DMA zones for January-March 2026. Fleet Performance Metrics: Average pump efficiency: 74.8% (target: 78%). Pumps below 70% efficiency: 3 (PMP-DMA02B-17 at 64.2%, PMP-DMA02F-25 at 67.1%, PMP-DMA01C-13 at 69.8%). Total unplanned shutdowns: 1 (PMP-DMA02B-17, bearing temperature alarm). False alarm rate: 14% (down from 58% pre-Snowflake integration). Average AVEVA model accuracy: 96.2% (MAE < 2.0 for all monitored parameters). Zone Analysis: DMA01 (7 pumps): Average efficiency 76.1%, 0 unplanned events. DMA02 (7 pumps): Average efficiency 71.3%, 1 unplanned event. Contains 2 of 3 lowest-performing pumps. DMA03 (5 pumps): Average efficiency 75.9%, 0 unplanned events. DMA04 (6 pumps): Average efficiency 76.2%, 0 unplanned events. PMP-DMA04A-06 operating within normal parameters — bearing temp deviation tracked to weather events per established correlation protocol. Weather Impact Summary: Q1 2026 featured 12 chinook events (above seasonal average of 8). Temperature swings ranged from 15-35°C. 67% of all vibration alerts during chinook events were classified as environmentally influenced and handled through continued monitoring rather than emergency inspection. Energy Cost: Total Q1 electricity cost for pump fleet: $842,000. Estimated savings from efficiency improvements: $47,000. Estimated avoided costs from prevented false alarms: $52,000.',
    'OPERATIONS_REPORT',
    'Calgary Water Operations',
    '2026-04-01';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-OP-002',
    'Weekly Operations Briefing: DMA Fleet Status — Week of April 21, 2026',
    'Weekly Operations Briefing — Calgary Water Distribution Network. Week: April 21-27, 2026. Prepared by: Operations Control Center. Weather Summary: Significant weather event this week. Temperature swung from 2°C on April 20 to 18°C on April 23, then dropped to -3°C on April 26 before recovering to 8°C on April 27. This 21°C swing over 6 days is consistent with a late-season chinook pattern. Wind speeds peaked at 45 km/h on April 23. Fleet Status: 22 of 25 pumps in NORMAL status. 3 pumps in WATCH status: PMP-DMA04A-06 — Bearing temperature showing +2.3°C deviation from AVEVA predicted value. Vibration increased from 0.48 to 0.61 mm/s. Both deviations correlate with ambient temperature (r=0.31 and r=0.29 respectively). Classification: ENVIRONMENTAL. Continue monitoring. Next scheduled maintenance: WO-2026-0847, May 15. PMP-DMA02B-17 — Recovering from anomaly event April 21-25. Bearing temperature peaked at 87°C before subsiding. Investigation ongoing. PMP-DMA01C-13 — Motor current elevated at 348A (baseline 325A). Not correlated with weather. Scheduling inspection. SAP Inventory Alert: Thrust Bearing Kits (M-4420) at Calgary Main: 3 units. Reorder point: 2 units. Stock adequate for current needs. Motor Stator Assemblies (M-7712): 0 units at Calgary Main. CRITICAL: Order placed, ETA 28 days. If PMP-DMA01C-13 requires motor work, expedited procurement will be needed. AI Recommendation: Cortex AI analysis incorporating AVEVA + WeatherSource + SAP data recommends: Maintain current operating status for PMP-DMA04A-06. The weather correlation analysis confirms environmental influence on sensor readings. No mechanical intervention needed until scheduled WO-2026-0847 on May 15.',
    'OPERATIONS_REPORT',
    'Operations Control Center',
    '2026-04-27';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-REG-001',
    'Alberta Energy Regulator: Water Infrastructure Reliability Standards Directive 2024',
    'Alberta Energy Regulator — Directive 2024-WI-003: Reliability Standards for Municipal Water Distribution Infrastructure. Effective Date: January 1, 2024. Scope: All municipal water distribution systems in Alberta serving populations over 10,000. Key Requirements: 1) Continuous Monitoring: All pumps in critical service (defined as pumps whose failure would result in supply interruption to >500 connections) must be equipped with continuous monitoring for bearing temperature, vibration, motor current, and flow rate. Monitoring data must be retained for minimum 3 years. 2) Predictive Maintenance: Operators of critical water infrastructure are required to implement predictive maintenance programs by December 2025. Acceptable approaches include: physics-based models, machine learning models, or hybrid approaches (such as AVEVA Predictive Analytics). Models must demonstrate >85% accuracy in predicting maintenance needs 14+ days in advance. 3) Environmental Integration: Maintenance decision-making must account for environmental factors. Operators must demonstrate that weather data is incorporated into their condition assessment process to reduce false positive maintenance triggers and avoid unnecessary shutdowns. 4) Spare Parts Management: Critical spare parts (bearings, seals, impellers) must be maintained at inventory levels sufficient to support a 14-day emergency response without procurement delays. Operators must maintain integration between their CMMS (e.g., SAP PM) and monitoring systems. 5) Reporting: Annual reliability reports must include: pump availability statistics, unplanned shutdown events, false alarm rates, and predictive model accuracy metrics. Penalties: Non-compliance may result in fines of up to $50,000 per violation per month.',
    'REGULATORY',
    'Alberta Energy Regulator',
    '2024-01-01';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-REG-002',
    'AWWA M44: Emergency Planning for Water Utility Operations',
    'American Water Works Association Manual M44 — Emergency Planning for Water Utility Operations (Summary). Chapter 7: Equipment Failure Response. Pump Failure Categories: Category 1 (Non-Critical): Single pump failure in a multi-pump station with N+1 redundancy. Response: Schedule repair within 72 hours. Category 2 (Significant): Pump failure reducing station capacity below 80% of peak demand. Response: Initiate repair within 24 hours, activate backup supply if available. Category 3 (Critical): Pump failure causing or threatening service interruption. Response: Immediate emergency response, activate mutual aid if needed. Predictive vs Reactive Maintenance: AWWA research (RF-4751) demonstrates that utilities implementing predictive maintenance programs experience 62% fewer Category 2+ events compared to reactive-only programs. The average cost of a Category 2 event is $45,000-85,000 including repair, overtime, and customer impact. Predictive programs that integrate multiple data sources (equipment sensors, weather, maintenance history) show the highest prevention rates. Integration Requirements: Modern water utility operations should integrate: 1) SCADA/IoT sensor data for real-time monitoring. 2) Predictive analytics (e.g., AVEVA) for equipment health trending. 3) Weather services for environmental context. 4) CMMS (e.g., SAP) for maintenance planning and parts management. 5) AI/ML for automated decision support. This multi-source integration — what leading utilities call "The Complete Picture" — enables proactive decision-making that prevents 70-80% of unplanned shutdowns.',
    'REGULATORY',
    'American Water Works Association',
    '2023-06-15';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-REG-003',
    'Government of Alberta: Climate Adaptation Guidelines for Water Infrastructure',
    'Government of Alberta — Climate Adaptation Guidelines for Water Infrastructure (2024). Publication: ENV-2024-0089. Context: Alberta is experiencing increasing climate variability, with more frequent chinook events, wider temperature swings, and shifting precipitation patterns. These changes directly impact water distribution infrastructure reliability. Impact on Pump Operations: Temperature Variability: Calgary experiences chinook events 25-35 times per year, with temperature swings of 20-30°C within 24 hours. These rapid changes cause thermal stress on pump components, particularly bearings and seals. Water utilities report a 40% increase in maintenance events during high-variability months (January-March, October-November). Vibration Correlation: Provincial monitoring data from 8 water utilities confirms a consistent correlation (r = 0.25-0.40) between ambient temperature and pump vibration across all installation types. This correlation is strongest for outdoor pump stations and weakest for climate-controlled facilities. Recommended Adaptations: 1) Weather-Integrated Monitoring: Incorporate Environment Canada or commercial weather data (e.g., WeatherSource via Snowflake Marketplace) into pump monitoring systems. 2) Dynamic Thresholds: Adjust alarm and trip thresholds seasonally and during known weather events. 3) Inventory Buffer: Increase critical spare parts inventory by 25% during high-variability months. 4) Predictive Model Enhancement: Ensure predictive models (AVEVA, OSIsoft, etc.) account for ambient temperature as an input variable. 5) Cross-Source Analytics: Use platforms like Snowflake to JOIN operational data with external environmental data for comprehensive decision-making.',
    'REGULATORY',
    'Government of Alberta',
    '2024-05-01';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-SOP-001',
    'SOP-MNT-4420: Thrust Bearing Inspection and Replacement Procedure',
    'Standard Operating Procedure SOP-MNT-4420. Department: Mechanical Maintenance. Revision: 3.2 (2024). Scope: This procedure covers the inspection, assessment, and replacement of thrust bearings in horizontal centrifugal water pumps across all DMA zones. Applies to SKF 29340E and equivalent thrust bearings installed in Sulzer MSD series pumps. Pre-Inspection Requirements: 1) Obtain current AVEVA predictive model output for the target pump — compare actual vs predicted bearing temperatures over the preceding 14 days. 2) Review SAP maintenance history (transaction IW39) for the equipment — check last bearing replacement date, total run hours since last maintenance, and any outstanding work orders. 3) Check SAP spare parts inventory (transaction MMBE) for Material M-4420 (Thrust Bearing Kit) at the nearest warehouse location. Lead time for emergency procurement from SKF Industrial is 14 calendar days. Inspection Criteria: Visual: Check for discoloration (bluing indicates overheating above 300°C), pitting, spalling, or cage damage. Measurement: Radial clearance should be 0.05-0.12mm. Clearance above 0.15mm requires replacement. Surface finish: Ra value should not exceed 0.4µm on raceways. Replacement Decision Matrix: If bearing temperature deviation from AVEVA predicted value exceeds 6°C AND vibration exceeds 1.0 mm/s AND run hours exceed 2400h — replace bearing. If only temperature deviation exceeds 6°C but vibration is normal — investigate environmental factors (ambient temperature, cooling system) before replacing. If vibration exceeds 1.5 mm/s regardless of temperature — replace bearing immediately. Cost Considerations: Planned bearing replacement: $8,400 (parts) + $4,000 (labor) = $12,400 total. Emergency bearing replacement (unplanned shutdown): $8,400 (parts) + $12,000 (overtime labor + expedited shipping) + $25,000-50,000 (production loss) = $45,400-70,400 total. Proactive replacement saves $33,000-58,000 per incident.',
    'MAINTENANCE_SOP',
    'Internal Operations',
    '2024-02-01';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-SOP-002',
    'SOP-MNT-6600: Impeller Inspection and Clearance Adjustment for Centrifugal Pumps',
    'Standard Operating Procedure SOP-MNT-6600. Department: Mechanical Maintenance. Revision: 2.1 (2024). Scope: Inspection and clearance adjustment of impellers in horizontal split-case centrifugal pumps. Indicators of Impeller Wear: Gradual decline in pump efficiency (>5% below design point over 60 days), increased motor power consumption at constant flow rate, and cavitation noise during operation. AVEVA predictive model deviation in efficiency >3% sustained over 14 days warrants inspection. Procedure: 1) Isolate pump per LOTO procedure SOP-SAF-001. 2) Remove upper casing. 3) Measure impeller-to-wear-ring clearance at 4 points (0°, 90°, 180°, 270°). Design clearance: 0.25-0.35mm. Maximum allowable: 0.50mm. 4) If clearance exceeds 0.50mm, replace wear rings. If impeller vane thickness is reduced by >15% from design, replace impeller. Cost: Wear ring replacement: $3,200. Impeller replacement: $18,500 (Material M-6611). Note: High-flow impellers (M-6611) have variable availability — check SAP inventory at both Calgary Main and Edmonton Depot warehouses.',
    'MAINTENANCE_SOP',
    'Internal Operations',
    '2024-04-15';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-SOP-003',
    'SOP-MNT-7700: Motor Electrical Health Assessment Protocol',
    'Standard Operating Procedure SOP-MNT-7700. Department: Electrical Maintenance. Revision: 1.4 (2024). Scope: Routine and condition-based electrical health assessment of pump drive motors (150-315 kW). Monitoring Parameters: Motor current (via AVEVA continuous monitoring), insulation resistance (quarterly megger test), winding temperature (via embedded RTDs), and power factor. Current Signature Analysis: Use AVEVA motor current data to establish a 30-day rolling baseline. Deviations exceeding ±5% from baseline without corresponding changes in pump load indicate potential issues: broken rotor bars (characteristic current modulation at slip frequency), stator winding degradation (increased harmonic content), or bearing electrical erosion (random high-frequency noise). Motor Stator Replacement Criteria: Insulation resistance below 5 MΩ at 40°C requires offline testing. Below 2 MΩ requires immediate motor removal for rewind or replacement. SAP Material M-7712 (Motor Stator Assembly) — note: this is a critical long-lead item with 28-day procurement time. Maintain minimum 1 unit in stock at Calgary Main warehouse. Current inventory status should be verified via SAP before scheduling any motor-related maintenance.',
    'MAINTENANCE_SOP',
    'Internal Operations',
    '2024-03-20';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-STD-001',
    'API 610 Summary: Vibration Acceptance Criteria for Centrifugal Pumps',
    'API Standard 610, 12th Edition — Summary of Vibration Acceptance Criteria. Scope: This standard establishes minimum requirements for centrifugal pumps used in petroleum, petrochemical, and natural gas industries. The vibration criteria are widely adopted across water infrastructure as well. Unfiltered Vibration Limits (Bearing Housing): For pumps operating at speeds up to 3600 RPM with rated power 75-500 kW: Acceptance test: 3.8 mm/s peak or 2.7 mm/s RMS. Allowable in service: 6.4 mm/s peak or 4.5 mm/s RMS. Alarm: 8.5 mm/s peak or 6.0 mm/s RMS. Trip: 11.0 mm/s peak or 7.8 mm/s RMS. Note: These are absolute limits. For condition-based monitoring, the rate of change is often more diagnostic than absolute values. A vibration increase of >25% over a 14-day period warrants investigation, even if absolute values remain below alarm levels. Frequency Analysis: First-order vibration (1x running speed) indicates imbalance or misalignment. Second-order (2x) indicates misalignment or looseness. Sub-synchronous vibration (0.4-0.48x) indicates oil whirl in sleeve bearings. Broadband high-frequency indicates bearing defects — correlate with bearing temperature trending. Relationship to Predictive Models: When AVEVA predictive models show increasing deviation between predicted and actual vibration, and the deviation correlates with ambient temperature changes (r > 0.25), the root cause is likely environmental rather than mechanical. In such cases, verify that predictive model inputs include ambient temperature before scheduling mechanical intervention.',
    'INDUSTRY_STANDARD',
    'American Petroleum Institute',
    '2023-09-01';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-STD-002',
    'ISO 10816-7: Vibration Assessment for Rotodynamic Pumps',
    'ISO 10816-7:2009 — Mechanical Vibration — Evaluation of machine vibration by measurements on non-rotating parts. Part 7: Rotodynamic pumps for industrial applications. Classification Zones: Zone A (newly commissioned or after overhaul): vibration velocity ≤ 3.5 mm/s RMS. Zone B (acceptable for unrestricted long-term operation): ≤ 7.1 mm/s RMS. Zone C (not suitable for long-term operation — remedial action needed): ≤ 11.0 mm/s RMS. Zone D (severe — damage potential): > 11.0 mm/s RMS. Important Caveats for Water Infrastructure: Municipal water pumps in DMA networks typically operate well within Zone A under normal conditions (0.3-0.8 mm/s RMS). Any transition from Zone A to Zone B should trigger investigation. However, environmental factors can temporarily push readings from Zone A into low Zone B without indicating mechanical issues. Temperature-induced vibration increases of 0.1-0.3 mm/s are well-documented in field studies across Western Canadian installations. Assessment Protocol: 1) Establish baseline vibration at known-good conditions. 2) Monitor trending via AVEVA or equivalent predictive system. 3) If vibration increases beyond baseline + 0.3 mm/s, check ambient conditions first. 4) If ambient conditions explain the increase (temperature correlation r > 0.25), continue monitoring. 5) If no environmental explanation, schedule inspection per maintenance SOP.',
    'INDUSTRY_STANDARD',
    'International Organization for Standardization',
    '2023-11-15';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-STD-003',
    'Hydraulic Institute Standard HI 9.6.4: Rotodynamic Pump Efficiency',
    'Hydraulic Institute Standard HI 9.6.4-2016 — Rotodynamic Pumps for Vibration Measurements and Allowable Values. Efficiency Monitoring: Pump efficiency is calculated as hydraulic power output divided by shaft power input. For municipal water distribution pumps in the 100-250 kW range, design efficiency typically ranges from 78-86% at best efficiency point (BEP). Acceptable Efficiency Degradation: New pump: within 2% of design efficiency. After 2 years operation: within 5% of design. After 5 years: within 8% of design. Efficiency drop exceeding 10% from design at any point warrants investigation. Efficiency drop exceeding 15% requires immediate intervention — likely impeller wear, increased internal clearances, or seal degradation. Factors Affecting Efficiency: Operating point (flow rate relative to BEP), internal clearances (wear ring condition), impeller condition, and system head. Environmental factors: fluid viscosity changes with temperature (water viscosity at 5°C is 1.519 cP vs 0.653 cP at 40°C — a 57% reduction). This means pump efficiency varies seasonally by 1-3% in climates with large temperature swings, purely due to fluid property changes. For Canadian DMA installations, expect efficiency to be 1-2% higher in summer than winter due to reduced viscosity. AVEVA predictive model calibration should account for this seasonal baseline shift. Cost of Inefficiency: Each 1% drop in pump efficiency for a 200 kW pump operating 8000h/year at $0.08/kWh costs approximately $1,600/year in excess energy. A fleet of 25 pumps with average 3% excess degradation represents $120,000/year in wasted energy.',
    'INDUSTRY_STANDARD',
    'Hydraulic Institute',
    '2024-01-20';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-TR-001',
    'Training Module: Understanding AVEVA Predictive Model Outputs for Pump Operations',
    'Training Module TM-OPS-2024-003. Subject: Interpreting AVEVA Predictive Analytics Dashboard for Centrifugal Pump Operations. Target Audience: Pump operators, maintenance technicians, reliability engineers. Module 1 — What AVEVA Predicts: The AVEVA predictive model uses machine learning trained on historical sensor data to predict expected values for key parameters: bearing temperatures, motor current, vibration, pump efficiency, and derived KPIs like Overall Machine Rating (OMR). The model learns normal operating patterns and flags deviations. Module 2 — Reading Deviations: A deviation is the difference between actual sensor reading and model prediction. Small deviations (within model MAE): Normal variation, no action needed. Moderate deviations (1.5-3x MAE sustained >3 days): Investigate. Check environmental factors first, then mechanical. Large deviations (>3x MAE): Likely mechanical issue. Create SAP work order. Module 3 — The Limitation: AVEVA models what happens INSIDE the plant — sensor data from the equipment. They do NOT model what happens OUTSIDE — weather, supply chain disruptions, energy prices, regulatory changes. This is why deviations sometimes have environmental root causes that the AVEVA model alone cannot explain. Module 4 — The Complete Picture: By combining AVEVA sensor analysis with Snowflake Marketplace weather data, SAP maintenance/cost data, and Cortex AI reasoning, operators get the full context needed for accurate decision-making. This integration turns data into actionable intelligence: AVEVA tells you WHAT is happening, Snowflake tells you WHY, SAP tells you WHAT it costs, and Cortex AI recommends what to do.',
    'TRAINING',
    'Operations Training Department',
    '2024-10-15';

INSERT INTO AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
    (DOC_ID, TITLE, CONTENT, DOC_TYPE, SOURCE, PUBLISHED_DATE)
SELECT
    'DOC-TR-002',
    'Emergency Response Protocol: Bearing Thermal Runaway in Critical Water Pumps',
    'Emergency Response Protocol ERP-2024-005. Subject: Response Procedure for Bearing Thermal Runaway in Critical Water Distribution Pumps. Classification: IMMEDIATE RESPONSE REQUIRED when bearing temperature exceeds 90°C or rate of temperature rise exceeds 5°C/hour. Step 1 — Verify (0-5 minutes): Confirm bearing temperature reading with secondary sensor or IR gun. Rule out sensor malfunction. Check AVEVA model — is the deviation sudden (sensor issue) or trending (mechanical issue)? Step 2 — Assess (5-15 minutes): Check ambient conditions via WeatherSource. If temperature deviation correlates with weather (r > 0.25), this may be environmentally amplified. However, if bearing temp exceeds 90°C regardless of cause, proceed to Step 3. Query SAP for pump maintenance history and available spare parts. Step 3 — Decide (15-20 minutes): If temp > 95°C or rising > 3°C/hour: EMERGENCY SHUTDOWN. Initiate controlled pump shutdown per SOP-EMS-001. If temp 85-95°C and stable: REDUCE LOAD. Lower flow set point by 20%, monitor for 30 minutes. If temperature stabilizes, maintain reduced operation until planned maintenance. If temp 75-85°C and weather-correlated: CONTINUE MONITORING. Increase monitoring frequency to 15-minute intervals. Prepare contingency work order in SAP. Step 4 — Communicate: Notify Operations Manager and Maintenance Lead. If shutdown required, notify Distribution Network Operations for demand management. Log all actions in SAP work order system. Critical Parts: Thrust Bearing Kit M-4420 must be available at Calgary Main for any emergency bearing replacement. Current stock status should be verified immediately upon entering this protocol. If stock is below reorder point (2 units), place emergency procurement order simultaneously.',
    'EMERGENCY_PROTOCOL',
    'Operations Safety Team',
    '2024-07-01';


-- ======================================================================
-- SECTION 5: PUMP_DATA_ENRICHED VIEW
-- ======================================================================

-- This view unions the live AVEVA CLD sensor data with fabricated anomaly data.
-- REQUIRES: CONNECT_AWC26 catalog-linked database to be attached.
-- NOTE: If your CLD database is named differently, change the reference below.

CREATE OR REPLACE VIEW AVEVA_CONNECT.PUBLIC.PUMP_DATA_ENRICHED AS
SELECT "Timestamp", "Name", "Field", "Value"
FROM CONNECT_AWC26."f6dd054e-d7b7-4b48-97f3-1b0eb2e91ab0".water_leakage_pump_narrow_live
UNION ALL
SELECT "Timestamp", "Name", "Field", "Value"
FROM AVEVA_CONNECT.PUBLIC.PUMP_ANOMALY_OVERLAY;


-- ======================================================================
-- SECTION 6: CORTEX SEARCH SERVICE
-- ======================================================================

-- Creates a Cortex Search Service over the industrial knowledge base
-- for RAG-powered document retrieval in the Streamlit app.

CREATE CORTEX SEARCH SERVICE AVEVA_CONNECT.PUBLIC.INDUSTRIAL_DOCS_SEARCH
  ON CONTENT
  ATTRIBUTES TITLE, DOC_TYPE, SOURCE
  WAREHOUSE = COMPUTE_WH
  TARGET_LAG = '1 hour'
AS (
  SELECT CONTENT, TITLE, DOC_TYPE, SOURCE
  FROM AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE
);


-- ======================================================================
-- SECTION 7: FABRICATED WEATHERSOURCE DATA
-- ======================================================================
--
-- This table provides sample weather data that mirrors the Snowflake Marketplace
-- WeatherSource listing. The app auto-detects: if the real Marketplace database
-- exists, it uses that; otherwise it falls back to this table.
-- ======================================================================

CREATE OR REPLACE TABLE AVEVA_CONNECT.PUBLIC.WEATHER_HISTORY_SAMPLE AS
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


-- ======================================================================
-- SECTION 8: STREAMLIT APP DEPLOYMENT
-- ======================================================================

-- Upload Streamlit app files to the stage, then create the Streamlit object.
-- IMPORTANT: Update the file paths below to match your local file locations.
--
-- Option A: Upload via PUT commands (from SnowSQL or a Snowflake worksheet)
--   Replace '/path/to/' with the actual directory containing the files.

-- PUT file:///path/to/streamlit_app.py @AVEVA_CONNECT.PUBLIC.COMPLETE_PICTURE_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
-- PUT file:///path/to/environment.yml @AVEVA_CONNECT.PUBLIC.COMPLETE_PICTURE_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

-- Option B: If files are already on the stage, just create the Streamlit object:
-- NOTE: Commented out — use `snow streamlit deploy --replace` instead,
--       which uploads files and creates the Streamlit object in one step.

-- CREATE OR REPLACE STREAMLIT AVEVA_CONNECT.PUBLIC.COMPLETE_PICTURE_DEMO
--   FROM '@AVEVA_CONNECT.PUBLIC.COMPLETE_PICTURE_STAGE'
--   MAIN_FILE = 'streamlit_app.py'
--   QUERY_WAREHOUSE = COMPUTE_WH
--   TITLE = 'AVEVA + Snowflake: The Complete Picture';

-- ALTER STREAMLIT AVEVA_CONNECT.PUBLIC.COMPLETE_PICTURE_DEMO ADD LIVE VERSION FROM LAST;


-- ============================================================================
-- SETUP COMPLETE
-- ============================================================================
--
-- Verification queries:
--
-- SELECT 'SAP_MAINTENANCE_ORDERS' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM AVEVA_CONNECT.PUBLIC.SAP_MAINTENANCE_ORDERS
-- UNION ALL
-- SELECT 'SAP_SPARE_PARTS', COUNT(*) FROM AVEVA_CONNECT.PUBLIC.SAP_SPARE_PARTS
-- UNION ALL
-- SELECT 'PUMP_ANOMALY_OVERLAY', COUNT(*) FROM AVEVA_CONNECT.PUBLIC.PUMP_ANOMALY_OVERLAY
-- UNION ALL
-- SELECT 'INDUSTRIAL_KNOWLEDGE_BASE', COUNT(*) FROM AVEVA_CONNECT.PUBLIC.INDUSTRIAL_KNOWLEDGE_BASE;
--
-- Expected counts:
--   SAP_MAINTENANCE_ORDERS:    40
--   SAP_SPARE_PARTS:           29
--   PUMP_ANOMALY_OVERLAY:     145
--   INDUSTRIAL_KNOWLEDGE_BASE: 28
--
-- ============================================================================