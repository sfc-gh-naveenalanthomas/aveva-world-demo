# AVEVA + Snowflake — Detailed Use Case Portfolio

**AVEVA World 2026 | Live Demo Suite**

All use cases run on **real AVEVA Connect data** flowing into Snowflake via Iceberg REST Catalog — 13M+ sensor readings across mining trucks and water pumps, streaming live. Every visualization, correlation, and AI output is grounded in production-grade data and runs entirely inside Snowflake.

---

## Data Foundation — AVEVA Connected Lifecycle Data (CLD)

Every use case begins with the same two-statement integration:

```sql
CREATE CATALOG INTEGRATION AVEVA_CLD_CATALOG
  CATALOG_SOURCE = ICEBERG_REST
  TABLE_FORMAT   = ICEBERG
  CATALOG_URI    = 'https://<aveva-connect-endpoint>/iceberg'
  ACCESS_DELEGATION_MODE = VENDED_CREDENTIALS
  ENABLED = TRUE;

CREATE DATABASE AVEVA_CLD_DATA
  FROM CATALOG INTEGRATION AVEVA_CLD_CATALOG
  AUTO_REFRESH = TRUE;
```

**What syncs automatically:**

| Table | Rows | Assets | Sensors | Format |
|-------|------|--------|---------|--------|
| `mining_haul_truck_narrow_live` | 3.8M+ | 10 trucks (101–110) | 33 per truck | Narrow: Timestamp, Name, Field, Value |
| `mining_haul_truck_narrow_26q1` | 1.7M | 10 trucks | 33 per truck | Same (Q1 2026 static batch) |
| `water_leakage_pump_narrow_live` | 7.6M+ | 25 pumps across 4 DMAs | 77 per pump (76 on focus pump) | Same |
| **Total** | **13M+** | **35 assets** | **110 unique sensors** | |

All CLD tables are read-only Iceberg tables. Snowflake reads them in place — zero data movement, zero ETL.

---

# Use Case 1: The Complete Picture — AI-Powered Asset Health Diagnosis

**App:** `AVEVA_CONNECT.PUBLIC.COMPLETE_PICTURE_DEMO` (Streamlit in Snowflake)
**Focus:** Water pump asset health with 3-step agentic AI diagnosis
**Runtime:** ~10 minutes full walkthrough

## Data Sources (5)

| Source | Snowflake Object | What It Provides |
|--------|-----------------|------------------|
| **AVEVA CLD** | `water_leakage_pump_narrow_live` (7.6M+ rows) | Live sensor data: bearing temps, motor current, vibration, efficiency, run hours, power, flow rate, ambient temperature — all in narrow format |
| **AVEVA Predictive Model** | Same CLD table — fields with `|Predicted` suffix | AVEVA's predicted values for thrust bearing temps, motor current, ambient temp — enables actual-vs-predicted deviation analysis |
| **WeatherSource** | `GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI.PWS_BI_SAMPLE.POINT_HISTORY_DAY` | Calgary daily weather: min/avg/max temperature, wind speed, humidity, precipitation. Falls back to `LOCAL_WEATHER_FALLBACK` (369 synthetic rows) |
| **SAP ERP** | `SAP_MAINTENANCE_ORDERS` (40 rows) + `SAP_SPARE_PARTS` (29 rows) | Work orders with priority/status/cost, spare parts with stock levels/lead times/vendors. Key item: Thrust Bearing Kit M-4420, 3 units at Calgary Main, $2,800/unit, 14-day lead from SKF Industrial |
| **Industrial Knowledge Base** | `INDUSTRIAL_KNOWLEDGE_BASE` (28 docs) via `INDUSTRIAL_DOCS_SEARCH` Cortex Search service | OEM bulletins (SKF, Sulzer, WEG), maintenance SOPs, incident reports, API standards, emergency protocols, regulatory guidelines |

## What's Built — Page by Page

### Page 1: Fleet Overview
- **25 pumps across 4 District Metered Areas (DMA01–DMA04)**, queried from CLD with 14-day lookback
- **Risk classification engine** (Python): CRITICAL (efficiency <60% OR vibration >1.5 OR run hours >3000), HIGH, ELEVATED, NORMAL
- **DMA Fleet Grid**: Color-coded tiles per pump — red/amber/green. Purple border highlights PMP-DMA04A-06 (focus pump with 76 sensor channels + predictive model)
- **Efficiency ranking**: Horizontal bar chart per pump, color-coded by threshold (<65% red, <70% orange, <75% amber, ≥75% green)
- **Fleet Health Detail table**: Custom HTML — pump name, efficiency %, min efficiency, power kW, run hours, vibration mm/s, risk pill badge

### Page 2: Predicted vs Actual
- **Focus pump: PMP-DMA04A-06** — the only pump with AVEVA's full predictive model
- **Sensor dropdown**: Thrust Bearing Temp 1/2/3, Motor Current, Ambient Temperature, Suction Chamber Level
- **Dual-line chart**: Actual (teal) vs. Predicted (purple dashed) with amber deviation fill zone
- **Deviation bars**: Green (tight), amber (noteworthy), red (significant)
- **Mean Absolute Error** computed from the time series

### Page 3: Weather Context
- **Cross-source JOIN**: CLD pump data joined with WeatherSource in a single SQL query
- **Correlation cards**: Temperature vs. Vibration r=0.31 (statistically significant)
- **Timeline visualization**: Bar height = vibration, bar color = temperature (blue=cold, red=hot). Red-bordered bars mark the April 21–26 weather event
- **Heatmap strips**: Warmer days → higher vibration, lower efficiency
- **Key insight**: Deviation peaks in AVEVA's model align with temperature swings — environmental, not mechanical

### Page 4: AI Agent Recommendation — THE SHOWSTOPPER

**3-step agentic AI workflow, triggered by button click:**

**Step 1 — Structured Data Analysis** (`SNOWFLAKE.CORTEX.COMPLETE` with `mistral-large2`):
- Input: PMP-DMA04A-06 sensor readings (bearing temp actual 82.6°C vs predicted 65.2°C, motor current, vibration, efficiency, run hours), Calgary weather (avg/min/max temp, swing), SAP context (next WO-2026-0847 on May 15 at $12,400, bearing kits in stock, YTD spend)
- Output: JSON with diagnosis, anomalies list, **self-generated search queries** for the knowledge base, preliminary confidence score
- The AI decides what documents it needs — not hardcoded queries

**Step 2 — Knowledge Retrieval** (`SNOWFLAKE.CORTEX.SEARCH_PREVIEW` on `INDUSTRIAL_DOCS_SEARCH`):
- Runs the 2 search queries generated by Step 1
- Each query returns top 3 documents with `reranker_score`
- Deduplicates by title, keeps top 4 by relevance
- Retrieved columns: TITLE, DOC_TYPE, SOURCE, CONTENT (500-char excerpts)
- Embedding model: `snowflake-arctic-embed-m-v1.5`

**Step 3 — Synthesis & Recommendation** (`SNOWFLAKE.CORTEX.COMPLETE` with `mistral-large2`):
- Input: Step 1 findings + all sensor data + weather data + SAP context + retrieved document content
- Instruction: Must cite specific document titles, ground advice in OEM specs/SOPs/incident reports
- Output JSON: `{verdict, confidence, root_cause, evidence[], action, sap_action, citations[]}`
- Verdict options: `CONTINUE OPERATIONS` | `EMERGENCY SHUTDOWN` | `SCHEDULE INSPECTION`

**Rendered UI:**
- Verdict card (color-coded green/red/amber) with confidence gauge bar
- Executive Summary: "What's Wrong" (citing OEM doc), "What To Do" (citing SOP), "SAP Next Step" (WO number, parts, cost)
- Evidence & Citations expander with numbered evidence points and source document list
- **Dynamic savings callout**: $125K+ (if failure caught) or $40K+ (if false alarm avoided)
- **Multilingual output** via `SNOWFLAKE.CORTEX.TRANSLATE`: Spanish, French, Portuguese tabs

## Cortex AI Functions Used
| Function | Purpose |
|----------|---------|
| `CORTEX.COMPLETE('mistral-large2')` | Step 1 analysis + Step 3 synthesis |
| `CORTEX.SEARCH_PREVIEW('INDUSTRIAL_DOCS_SEARCH')` | Step 2 knowledge retrieval (28 docs, arctic-embed-m-v1.5) |
| `CORTEX.TRANSLATE(text, 'en', lang)` | Multilingual output (es/fr/pt) |

---

# Use Case 2: Weather-Aware Fleet Operations

**App:** `AVEVA_FLEET_OPS.STREAMLIT.WEATHER_AWARE_FLEET_OPS` (Streamlit in Snowflake)
**Focus:** Mining truck fleet optimization with weather intelligence and Cortex Agent
**Runtime:** ~8 minutes full walkthrough

## Data Sources (2 + AI)

| Source | Snowflake Object | What It Provides |
|--------|-----------------|------------------|
| **AVEVA CLD** | `mining_haul_truck_narrow_live` (3.8M+ rows) | 10 trucks, 33 sensors each: fuel rate, coolant temp, engine RPM, oil pressure, payload, ground speed, brake temps (4 positions), suspension pressure (4 positions), exhaust temps (L/R), engine load %, GPS lat/lon |
| **WeatherSource** | `GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI.PWS_BI_SAMPLE.POINT_HISTORY_DAY` + `POINT_FORECAST_DAY` | Calgary weather history (90 days) + 7-day forecast. Falls back to `AVEVA_FLEET_OPS.STREAMLIT.WEATHER_HISTORY_SAMPLE` (369 rows) + `WEATHER_FORECAST_SAMPLE` (45 rows) |
| **Cortex AI** | `mistral-large2` via CORTEX.COMPLETE + FLEET_DATA_AGENT via Cortex Agent API | 6 AI calls per page load + conversational agent |

## Snowflake Objects Created (setup.sql)

| Object | Purpose |
|--------|---------|
| `TRUCK_DATA_PIVOTED` (view) | Pivots narrow CLD data into one row per truck per hour with 24 named sensor columns |
| `FLEET_SEMANTIC_VIEW` | Semantic View over TRUCK_DATA_PIVOTED — 24 facts + 5 dimensions with business-friendly names and threshold descriptions |
| `FLEET_DATA_AGENT` | Cortex Agent with 1 tool: `cortex_analyst_text_to_sql` backed by FLEET_SEMANTIC_VIEW |

## What's Built — Section by Section

### Section 1: AI Fleet Health Score
- **`CORTEX.COMPLETE('mistral-large2')`** generates a 0–100 health score from fleet-wide sensor stats + anomaly count
- Output JSON: `{score, status (Excellent/Good/Fair/Poor), summary, top_risks[]}`
- Rendered as a glowing hero card with score, status, and risk factors
- Cached with `@st.cache_data(ttl=600)`

### Section 2: Fleet Overview with Deltas
- **10 truck KPI cards** showing today's sensor readings with **delta indicators vs. yesterday** (↑/↓ %)
- 6 key sensors displayed per truck: Fuel Rate (l/h), Payload (t), Ground Speed (km/h), Coolant Temp (°C), Oil Pressure (psi), Engine Load (%)
- Data from a single query pivoting CLD narrow data to wide format, grouped by truck

### Section 3: Weather Correlations
- **Cross-source JOIN**: Daily truck metrics (avg fuel rate, avg payload) joined with WeatherSource on date
- **Scatter plots with regression lines** (Altair): Fuel Rate vs. Wind Speed, Fuel Rate vs. Temperature, Payload vs. Temperature
- **Computed correlations**: Wind→fuel r=0.51, Temp→fuel r=0.49, Temp→payload r=-0.31
- These are real statistical correlations from production sensor data matched against real weather

### Section 4: AI Shift Deployment Plan
- **`CORTEX.COMPLETE('mistral-large2')`** generates a truck-by-truck deployment table
- Input: Fleet sensor stats, tomorrow's weather forecast, known correlations, anomaly summary
- Output: Markdown table — one row per truck with recommendation (DEPLOY / LIGHT DUTY / HOLD), reason, and dollar impact summary
- Rendered as styled HTML table with color-coded recommendation pills
- Cached with `@st.cache_data(ttl=600)`

### Section 5: Truck Drilldown
- **Dropdown selectors**: Pick any truck (101–110) + any combination of sensors
- **Time series line chart** (Altair): Multi-sensor overlay for the selected truck over the full date range
- Used for investigating anomalies flagged by the AI

### Section 6: Anomaly Detection with AI Narrative
- **Rolling z-score** detection: 100-reading sliding window, threshold >3.0 standard deviations
- Computed per truck per sensor in Python (pandas)
- 5 anomaly sensors monitored: Coolant Temp, Suspension Delta Front/Rear, Left/Right Exhaust Temp
- **`CORTEX.COMPLETE('mistral-large2')`** translates anomalies into 3 bullet points: what's abnormal, what's at risk, what to do
- Anomaly bars rendered as Altair charts per truck, red fill for flagged readings

### Section 7: 7-Day Weather Impact Prediction
- **`CORTEX.COMPLETE('mistral-large2')`** takes the 7-day forecast and generates a day-by-day operational impact table
- Output: Risk level, fuel adjustment %, payload adjustment %, key driving factor, estimated dollar impact per day
- Total weekly cost estimate at the bottom
- Cached with `@st.cache_data(ttl=600)`

### Section 8: Weather Forecast Display
- Raw WeatherSource 7-day forecast data
- Color-coded by operational risk level: HIGH (red) if wind >25mph or temp <10°F, MODERATE (amber) if wind >15mph, LOW (green) otherwise

### Section 9: Talk to Your Data — Cortex Agent Chat
- **Cortex Agent** at `/api/v2/databases/AVEVA_FLEET_OPS/schemas/STREAMLIT/agents/FLEET_DATA_AGENT:run`
- Called via `_snowflake.send_snow_api_request()` (SiS internal API)
- **Falls back** to Cortex Analyst at `/api/v2/cortex/analyst/message` if Agent endpoint fails
- 5 suggested questions: "What is the average fuel rate per truck?", "Which truck had the highest coolant temperature?", "Show me average speed by day of week", "Compare engine load across all trucks", "Which hours of the day have highest fuel consumption?"
- Responses rendered with: text blocks, SQL code blocks, auto-executed result tables, bar charts from SQL results, follow-up suggestion pills
- Persistent chat history in `st.session_state`

## Cortex AI Functions Used
| Function | Purpose | Calls per Page |
|----------|---------|----------------|
| `CORTEX.COMPLETE('mistral-large2')` | Health score, deployment plan, anomaly narrative, weather impact, insight teaser | 5 |
| Cortex Agent API (`FLEET_DATA_AGENT`) | Natural language → SQL → results via Semantic View | On-demand (chat) |
| Cortex Analyst API (fallback) | Same as above, direct Analyst call | On-demand (fallback) |

---

# Use Case 3: Total Cost of Operations

**App:** `AVEVA_WORLD_DEMOS.STREAMLIT_APPS.TOTAL_COST_OPS` (Streamlit in Snowflake)
**Focus:** Cross-industry cost unification — truck fuel + pump energy + SLA penalties + energy markets
**Runtime:** ~12–15 minutes full walkthrough

## Data Sources (5)

| Source | Snowflake Object | What It Provides |
|--------|-----------------|------------------|
| **AVEVA CLD — Trucks** | `mining_haul_truck_narrow_26q1` (1.7M rows) | Q1 2026 truck data: fuel rate, payload, GPS, engine load, 30+ sensor channels |
| **AVEVA CLD — Pumps** | `water_leakage_pump_narrow_live` (7.6M+ rows) | Live pump data: energy consumption (kWh), energy cost, motor power, efficiency |
| **WeatherSource** | Marketplace or `WEATHER_HISTORY_SAMPLE` (369 rows) | Calgary daily weather for correlation analysis |
| **Yes Energy** | Marketplace or `DART_PRICES_SAMPLE` (17,617 rows) | Hourly Alberta ERCOT day-ahead (DALMP) and real-time (RTLMP) electricity prices |
| **Salesforce CRM** | `SF_ACCOUNTS` + `SF_CONTRACTS` + `SF_DELIVERIES` + `SF_CASES` | 8 mining customers (Suncor, Teck, Imperial Oil, CNRL...), 15 active contracts with SLA terms, 1,350 truck deliveries with tonnage/delays/fuel cost, 45 SLA penalty cases |

## Snowflake Objects Created (setup.sql)

10 tables in `AVEVA_WORLD_DEMOS.STREAMLIT_APPS`:
- `SENSOR_READINGS` — 12 AVEVA PI sensors, pivoted format
- `PRODUCTION_METRICS` — Daily production output
- `MAINTENANCE_LOGS` — Equipment maintenance records with costs
- `FLEET_VEHICLES` — 10 trucks with Belgium GPS coordinates for digital twin
- `DELIVERY_ROUTES` — Truck delivery routes with timing, delays, fuel
- `CONTRACTS` — 15 SLA contracts simulating Salesforce CRM
- `DELIVERIES` — 1,350 deliveries with SLA penalty calculations
- `WEATHER_HISTORY_SAMPLE` — Fabricated Calgary weather matching WeatherSource schema
- `WEATHER_FORECAST_SAMPLE` — 7-day forecast sample
- `DART_PRICES_SAMPLE` — 17,617 rows of hourly Alberta electricity prices matching Yes Energy schema

## What's Built — Tab by Tab (9 Tabs)

### Tab 1: Truck Fuel
- **Daily fuel cost chart** (Altair area chart): Total Q1 fuel cost from AVEVA truck data
- **Per-truck breakdown table**: Fuel rate, payload, cost per tonne hauled, total fuel cost
- **KPI row**: Q1 total fuel cost, total payload moved, average fuel rate, cost per tonne
- Data: CLD Q1 batch table, pivoted with `CASE WHEN "Field" = 'Engine Fuel Rate Value l/h'`

### Tab 2: Pump Energy
- **Daily energy consumption chart**: kWh per day from AVEVA pump data
- **Pump-by-pump efficiency table**: Energy consumption, efficiency %, motor power
- **KPI row**: Total energy cost, avg daily consumption, avg efficiency
- Data: CLD live pump table, filtered for energy-related fields

### Tab 3: Total Cost
- **Unified cost view**: Truck fuel + pump energy + SLA penalties in one stacked chart
- **Monthly summary table**: 3 cost columns + total, showing the relative weight of each
- **KPI row**: Total cost, truck %, pump %, SLA penalty %
- **Key insight**: SLA penalties are nearly half a million dollars per quarter — only visible when connecting ops data to CRM

### Tab 4: Energy Market
- **Yes Energy DART prices**: Day-ahead vs. real-time price time series
- **Price volatility chart**: Spread between DALMP and RTLMP — load-shifting opportunities
- **Pump energy overlaid on price**: When energy cost spikes, is it consumption or price?
- Data: `DART_PRICES_SAMPLE` joined with pump energy data on date/hour

### Tab 5: Customer Revenue
- **Salesforce contract view**: 8 customers, 15 contracts, Q1 revenue, SLA penalties
- **On-time delivery %** chart with red dots marking weather-caused delays
- **SLA penalty breakdown** (donut chart): **87% of penalties are weather-driven**
- **Contract-level detail table**: Per-contract performance, penalty amount, at-risk status
- **Key insight**: These aren't operations failures — they're forecasting failures. Proactive rescheduling prevents penalties.

### Tab 6: Weather Multipliers
- **Validated correlations** from AVEVA truck data × WeatherSource:
  - Wind speed → truck fuel rate: **r = 0.51**
  - Temperature → payload capacity: **r = -0.31**
- **Scatter plots** with regression lines (Altair)
- Confirms that weather-aware scheduling is data-justified, not theoretical

### Tab 7: Digital Twin
- **PyDeck GPS map**: 10 trucks plotted on a map using actual GPS coordinates from AVEVA
- **Time scrubber slider** (0h–24h): Drag to see trucks move along haul routes, trails build up showing paths
- **Color-coded health**: Green (healthy), yellow (warning), red (critical)
- **Health scores table**: Per-truck 0–100 score from coolant temp, oil pressure, exhaust temp asymmetry, brake temps
- **Sensor drilldown**: Select worst truck, see time series with green (normal) band and red (warning) threshold
- **"Predict failures" button**: Sends 24h of sensor data to `CORTEX.COMPLETE('mistral-large2')` — returns failure predictions with timing and cost impact
- **Key message**: $8,000 preventive visit vs. $65,000 unplanned breakdown

### Tab 8: AI Optimization
- **`CORTEX.COMPLETE('mistral-large2')`** generates a 7-day operations schedule
- Input: Fleet status, weather forecast, SLA commitments, cost correlations
- Output: Day-by-day table — weather risk, SLA risk, trucks to deploy, pump adjustments, estimated cost, net savings
- Color-coded risk levels (green/orange/red)
- **Conversational follow-ups**: "Which contracts are most at risk this week?", "What if we reduce fleet by 30% on Thursday?"

### Tab 9: Savings Calculator
- **3 interactive sliders**:
  - Max wind speed for full operations (mph)
  - Fleet reduction % on bad weather days
  - SLA penalty prevention rate (% of weather-impacted deliveries proactively rescheduled)
- **Real-time quarterly projections**: Truck fuel savings + pump energy savings + SLA penalty avoidance
- **Before/after comparison**: Baseline cost vs. weather-optimized cost
- Projected savings: **hundreds of thousands per quarter**

## Cortex AI Functions Used
| Function | Purpose |
|----------|---------|
| `CORTEX.COMPLETE('mistral-large2')` | Failure prediction (Tab 7), 7-day optimization (Tab 8), conversational AI (Tab 8) |

**Note:** This app uses direct `CORTEX.COMPLETE` — no Cortex Agent, no Cortex Search, no Semantic Views. All queries are inline SQL. The Salesforce CRM data is simulated by the CONTRACTS/DELIVERIES tables.

---

# Use Case 4: AVEVA Snowline — Mobile AI for Field Operators (The Edge)

**App:** Docker container (Flask + HTML/CSS/JS) calling `AVEVA_CONNECT.PUBLIC.FIELD_OPERATOR_AGENT`
**Also available as:** `AVEVA_CONNECT.PUBLIC.FIELD_OPERATOR_DEMO` (SiS phone mockup version)
**Focus:** Same AI intelligence from the operations center, delivered to a phone for 3 field personas
**Runtime:** ~5 minutes (3 personas × 90 seconds)

## Data Sources (3, accessed via Cortex Agent tools)

| Agent Tool | Snowflake Object | What It Queries |
|------------|-----------------|-----------------|
| `query_truck_data` | `AVEVA_FLEET_OPS.STREAMLIT.FLEET_SEMANTIC_VIEW` (over `TRUCK_DATA_PIVOTED`) | 10 trucks, 24 sensor metrics: coolant temp, brake temps (4 positions), fuel rate, ground speed, payload, suspension (4 positions), exhaust temps (L/R), engine load, oil pressure, GPS |
| `query_pump_data` | `AVEVA_CONNECT.PUBLIC.PUMP_SEMANTIC_VIEW` (over `PUMP_DATA_PIVOTED`) | 25 pumps, 23 sensor metrics: bearing temps (actual + predicted for 3 positions), vibration (X/Y for inboard/outboard), efficiency, motor current/power/amps, pump speed, discharge pressure/flow, ambient temp (actual + predicted), run hours (since maintenance + total) |
| `knowledge_search` | `AVEVA_CONNECT.PUBLIC.INDUSTRIAL_DOCS_SEARCH` | 28 documents: SKF bearing bulletins, Sulzer pump guides, WEG motor specs, maintenance SOPs, incident reports, safety procedures, API/AWWA standards |

## Snowflake Objects Created (setup.sql)

| Object | Details |
|--------|---------|
| `PUMP_DATA_PIVOTED` (view) | Pivots narrow CLD pump data into hourly aggregated rows with 23 named columns. Source: `AVEVA_CLD_DATA."f6dd054e-...".water_leakage_pump_narrow_live` |
| `PUMP_SEMANTIC_VIEW` | 23 facts (all bearing temps actual + predicted, vibration X/Y, efficiency, current, power, speed, pressure, flow, ambient, run hours) + 5 dimensions (pump, timestamp, date, day_of_week, hour_of_day). Each fact has operational thresholds in comments. |
| `FIELD_OPERATOR_AGENT` | Cortex Agent with 3 tools, system prompt optimized for mobile: "Be concise — users are on mobile devices", "Always include clear YES/NO/MONITOR recommendation", "Format for mobile: short paragraphs, bullet points, bold key numbers". Budget: 120 seconds, 50,000 tokens. |

## Architecture

```
Photorealistic iPhone Mockup (HTML/CSS/JS)
    │
    ├── 3 Persona Tabs: Plant Manager | Truck Operator | Maint. Planner
    ├── Per-persona alerts (CRITICAL/WARNING) with tap-to-ask
    ├── Quick-action chips (4 per persona)
    ├── Chat interface with SSE streaming
    ├── English/Italian language toggle
    │
    └── Flask Backend (server.py)
            │
            ├── POST /api/chat (non-streaming, JSON response)
            ├── POST /api/chat/stream (SSE streaming)
            │       │
            │       └── Cortex Agent REST API
            │           POST /api/v2/databases/AVEVA_CONNECT/schemas/PUBLIC/agents/FIELD_OPERATOR_AGENT:run
            │           │
            │           ├── Tool 1: query_truck_data (text-to-SQL → FLEET_SEMANTIC_VIEW)
            │           ├── Tool 2: query_pump_data (text-to-SQL → PUMP_SEMANTIC_VIEW)
            │           └── Tool 3: knowledge_search (Cortex Search → INDUSTRIAL_DOCS_SEARCH)
            │
            └── POST-response: SNOWFLAKE.CORTEX.TRANSLATE(response, 'en', 'it')
                (if Italian language selected)
```

## Three Personas — What Each Sees and Does

### Plant Manager
**Alerts:**
- CRITICAL: "Truck 108 — Coolant Running Hot" (Engine coolant trending near 96°C)
- WARNING: "Pump DMA04 — Bearing Deviation" (PMP-DMA04A-06 bearing temps above prediction)

**Quick Actions:** Fleet overview | Pump health | Worst performers | Run hours check

**When they tap the coolant alert, the agent:**
1. Receives: "Pull the latest coolant temperature readings for Truck 108 from the last 24 hours. Is it running above normal? What's the max value and should I authorize pulling it from the haul road?"
2. Calls `query_truck_data` tool → SQL against FLEET_SEMANTIC_VIEW
3. Returns specific temperature value, compares to 85–95°C normal range, gives YES/NO recommendation

### Truck Operator
**Alerts:**
- URGENT: "Your Truck — Coolant Alert" (Truck 108 coolant may be spiking)
- CAUTION: "Brake Temperature Warning" (Check brake temps before hauling)

**Push Notification:** Animated slide-in notification when switching to this tab: "COOLANT ALERT — Truck 108. Engine coolant temperature spiking."

**Quick Actions:** Coolant check | Brake temps | Fuel usage | End-of-shift

**When they tap the push notification, the agent:**
1. Receives: "I'm driving Truck 108 and my dashboard is showing high coolant temperature. Pull the latest coolant readings. What's the current value? Is it safe to keep driving or should I pull over?"
2. Calls `query_truck_data` tool
3. Returns concise mobile-formatted answer with clear action item

### Maintenance Planner
**Alerts:**
- OVERDUE: "PMP-DMA02D-21 — High Run Hours" (Run hours may exceed 2400h maintenance interval)
- PLAN: "Truck 108 — Coolant Follow-Up" (Plan inspection after high coolant readings)

**Quick Actions:** Parts needed | Priority ranking | Cost comparison | Pump efficiency

**When they tap the pump alert, the agent:**
1. Receives: "What are the current run hours for PMP-DMA02D-21? How does it compare to the fleet average? Check what the SOP says about maintenance intervals and what spare parts we need for a bearing replacement."
2. Calls **two tools in one turn**: `query_pump_data` (actual run hours) + `knowledge_search` (maintenance SOP + parts list)
3. Returns: actual run hours from live data, recommended interval from OEM docs, specific parts to order — three data sources combined

## UI Implementation Details

- **Photorealistic iPhone mockup**: Dynamic Island, status bar with signal/battery, 410px wide, 780px screen
- **Per-persona chat persistence**: Chat history cached per persona — switching tabs preserves conversations
- **SSE streaming**: Word-by-word response rendering via Server-Sent Events, with live character count and elapsed time in the API log panel
- **API log panel**: Shows the actual REST call being made — method, endpoint, headers (token masked), request body, response stream, HTTP status, elapsed time
- **Data source cards** (left panel): AVEVA Trucks (3.8M+ rows), AVEVA Pumps (7.6M+ rows), Industrial Knowledge Base (28 docs)
- **English/Italian toggle**: Agent always reasons in English. If Italian selected, response is translated via `SNOWFLAKE.CORTEX.TRANSLATE(text, 'en', 'it')` and a `translated` SSE event replaces the English bubble. Cortex Translate sometimes converts `\n` to `<BR>` tags — the server normalizes these back.
- **i18n**: All UI strings (alerts, chip labels, status text, placeholders) have Italian translations

## Cortex AI Functions Used
| Function | Purpose |
|----------|---------|
| Cortex Agent REST API (`FIELD_OPERATOR_AGENT`) | Multi-tool orchestration: text-to-SQL (trucks), text-to-SQL (pumps), knowledge search |
| `cortex_analyst_text_to_sql` (via Agent) | Natural language → SQL over Semantic Views |
| `cortex_search` (via Agent) | Semantic search over 28 industrial documents |
| `SNOWFLAKE.CORTEX.TRANSLATE` | English → Italian translation |

---

# Use Case 5: Consolidated Operations Center

**App:** `AVEVA_CONNECT.PUBLIC.AVEVA_DEMO_CONSOLIDATED` (Streamlit in Snowflake)
**Focus:** Combines asset health, fleet ops, and cost optimization into one 3-tab app with an AI agent on every screen
**Runtime:** ~9 minutes (3 tabs) or ~13 minutes with mobile demo (Part 2)

## Data Sources (6)

| Source | What It Provides |
|--------|------------------|
| **AVEVA CLD — Trucks** | 3.8M+ live truck readings (10 trucks, 33 sensors) + 1.7M Q1 batch |
| **AVEVA CLD — Pumps** | 7.6M+ live pump readings (25 pumps, 77 sensors, 76 on focus pump with predictions) |
| **WeatherSource** | Calgary weather history + forecast (Marketplace or fallback samples) |
| **Yes Energy** | Alberta electricity prices — DART day-ahead + real-time (Marketplace or fallback) |
| **SAP ERP** | Maintenance orders (40) + spare parts (29) |
| **Salesforce CRM** | Accounts (8) + contracts (15) + deliveries (1,350) + SLA cases (45) |

## What's Built — Tab by Tab

### Tab 1: Asset Health — 3-Step Agentic AI (Auto-Running, Cached)
**Everything from Use Case 1, plus:**
- **Auto-runs on first page load** — no button click required. Results cached in `st.session_state` so subsequent page interactions don't re-trigger the AI
- **Data Foundation expander** at the top: shows the 2-statement CLD SQL, live row counts queried at runtime (3 metric cards), narrow-format schema explanation
- **Agent chat** below the analysis: `call_asset_agent()` does Cortex Search RAG (4 docs, 800 chars each) + `CORTEX.COMPLETE` synthesis. Prompt includes pump monitoring context, asks for specific thresholds, citations, recommendations, escalation criteria
- 3 suggested questions: OEM bearing temp limits, maintenance SOPs, weather impact on vibration

### Tab 2: Fleet Operations — Weather Intelligence + Cortex Agent
**Everything from Use Case 2, plus:**
- Fleet health score + truck grid with deltas
- Weather correlation scatter plots
- AI shift deployment briefing
- **Talk to Your Data** chat using `FLEET_DATA_AGENT` via `_snowflake.send_snow_api_request()`, falls back to Cortex Analyst
- 5 suggested questions, structured response rendering (text + SQL + tables + charts + suggestions)

### Tab 3: What-If Planner — Cost Optimization
- **Interactive savings calculator** with 4 sliders: wind threshold, fleet reduction %, pump power reduction %, SLA prevention rate
- **Real-time quarterly projections**: 3 savings buckets (truck fuel, pump energy, SLA penalties)
- **Before/after comparison**: Baseline vs. weather-optimized cost
- **Agent chat**: `call_savings_agent()` uses `CORTEX.COMPLETE` with pre-loaded context about all 6 data sources (Salesforce contracts, weather correlations, energy pricing, fleet stats, pump data)
- 3 suggested questions: SLA penalty drivers, high-wind savings, weather-delay relationship

## 3 Different AI Patterns on 3 Tabs

| Tab | AI Pattern | Implementation |
|-----|-----------|----------------|
| Asset Health | **Cortex Search RAG** | Search 28 docs → CORTEX.COMPLETE synthesis |
| Fleet Ops | **Cortex Agent** | FLEET_DATA_AGENT with text-to-SQL via Semantic View |
| What-If | **Cortex COMPLETE** | Direct LLM call with pre-loaded business context |

## Sidebar Features
- Data source badges (AVEVA CLD, Snowflake, SAP, Knowledge Base, Cortex AI)
- Live data feed indicator
- Asset summary (10 trucks, 25 pumps, WeatherSource, Yes Energy, Salesforce, 28 docs)
- Diesel price input ($0.50–$3.00/litre)
- **Clear cache button**: Clears `st.cache_data` + session state (`ai_analysis_result`, `fleet_health_cache`, `fleet_briefing_cache`) + triggers `st.rerun()`

---

# Cortex AI Capabilities — Full Matrix

| Capability | Use Case 1 (Complete Picture) | Use Case 2 (Fleet Ops) | Use Case 3 (Total Cost) | Use Case 4 (Mobile) | Use Case 5 (Consolidated) |
|------------|:---:|:---:|:---:|:---:|:---:|
| **Cortex COMPLETE** | Step 1 + Step 3 analysis | Health score, deployment plan, anomaly narrative, weather impact | Failure prediction, 7-day optimization, conversational AI | — (via Agent) | Step 1 + Step 3, fleet score, briefing, savings agent |
| **Cortex Search** | Step 2 knowledge retrieval (28 docs) | — | — | Via Agent (knowledge_search tool) | Asset health agent chat (RAG) |
| **Cortex Agent** | — | Talk to Your Data (FLEET_DATA_AGENT) | — | FIELD_OPERATOR_AGENT (3 tools) | Tab 2 Talk to Data (FLEET_DATA_AGENT) |
| **Cortex Analyst** | — | Fallback from Agent | — | Via Agent (text-to-SQL) | Tab 2 fallback |
| **Semantic Views** | — | FLEET_SEMANTIC_VIEW (24 facts) | — | FLEET + PUMP Semantic Views | FLEET_SEMANTIC_VIEW |
| **Cortex Translate** | es/fr/pt output | — | — | English/Italian toggle | — |

---

# Technical Architecture Summary

| Component | Detail |
|-----------|--------|
| **Data Integration** | Iceberg REST Catalog (CLD) — 2 SQL statements, zero data movement, vended credentials |
| **Data Volume** | 13M+ sensor readings live (3.8M trucks + 1.7M Q1 batch + 7.6M pumps) |
| **Marketplace** | WeatherSource (weather), Yes Energy (energy prices) — zero ETL, auto-detected with fallback |
| **Enterprise** | SAP (40 work orders, 29 spare parts), Salesforce (8 accounts, 15 contracts, 1,350 deliveries, 45 cases) |
| **Knowledge Base** | 28 industrial documents — OEM bulletins, SOPs, incident reports, standards — via Cortex Search |
| **AI Model** | mistral-large2 via Cortex COMPLETE |
| **Search Embedding** | snowflake-arctic-embed-m-v1.5 via Cortex Search |
| **Agents** | FLEET_DATA_AGENT (1 tool: truck text-to-SQL), FIELD_OPERATOR_AGENT (3 tools: truck SQL + pump SQL + knowledge search) |
| **Semantic Views** | FLEET_SEMANTIC_VIEW (24 facts, 5 dims), PUMP_SEMANTIC_VIEW (23 facts, 5 dims) |
| **Apps** | 4 Streamlit-in-Snowflake apps + 1 Docker mobile app + 1 SiS phone mockup |
| **Deployment** | Polaris (AWS, SFSENORTHAMERICA-POLARIS1) + AVEVA (Azure, AVEVA-AWCMILAN2026) |
| **CLD Auto-Detection** | Apps try `CONNECT_AWC26` first (AVEVA account), fall back to `AVEVA_CLD_DATA` (Polaris) |
| **Marketplace Fallback** | Apps auto-detect real Marketplace DBs, fall back to fabricated sample tables on accounts without listings |
