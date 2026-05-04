# AVEVA + Snowflake — Industrial AI Demo Suite

**AVEVA World 2026 | 5 Live Demo Apps**

Real-time AVEVA Connect IoT data + Snowflake Marketplace weather + Cortex AI agents — from the operations center to the field operator's phone.

## Quick Start

### Prerequisites

1. **Snowflake account** with Cortex AI enabled
2. **AVEVA Connect CLD** configured (Iceberg REST Catalog)
3. **Snow CLI** installed ([docs](https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation/installation))
4. **Docker** (for the mobile app only)

### Step 1: Connect AVEVA Data (2 SQL statements)

```sql
-- Register AVEVA's Iceberg REST catalog
CREATE CATALOG INTEGRATION AVEVA_CLD_CATALOG
  CATALOG_SOURCE     = ICEBERG_REST
  TABLE_FORMAT       = ICEBERG
  CATALOG_URI        = 'https://<your-aveva-connect-endpoint>/iceberg'
  CATALOG_WAREHOUSE  = '<your-warehouse-name>'
  ACCESS_DELEGATION_MODE = VENDED_CREDENTIALS
  ENABLED = TRUE;

-- Create catalog-linked database (tables auto-sync)
CREATE DATABASE AVEVA_CLD_DATA
  FROM CATALOG INTEGRATION AVEVA_CLD_CATALOG
  AUTO_REFRESH = TRUE;
```

> Your AVEVA Connect team provides the catalog URI and warehouse name. Vended credentials mean AVEVA handles authentication — no keys to manage.

### Step 2: Get Marketplace Data (optional but recommended)

Install these free/sample listings from the Snowflake Marketplace:

- **WeatherSource** — `GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI` (weather history + forecasts)
- **Yes Energy** — `YES_ENERGY__SAMPLE_DATA` (energy market prices)

> If Marketplace data isn't available, the apps auto-detect and fall back to built-in sample data.

### Step 3: Run Setup SQL

Each app has a `setup.sql` that creates the tables, views, semantic views, agents, and search services it needs. Run them in order:

```bash
# 1. Complete Picture — creates SAP tables, knowledge base, Cortex Search service
snow sql -f complete_picture/setup.sql --connection <your_connection>

# 2. Fleet Ops — creates truck pivot view, semantic view, Cortex Agent
snow sql -f build2_fleet_ops/setup.sql --connection <your_connection>

# 3. Field Operator — creates pump pivot view, pump semantic view, 3-tool Cortex Agent
snow sql -f field_operator/setup.sql --connection <your_connection>

# 4. Total Cost Ops — creates Salesforce, delivery, contract, energy tables
snow sql -f total_cost_ops/setup.sql --connection <your_connection>
```

> The consolidated demo doesn't need its own setup — it uses objects created by the above.

### Step 4: Configure Your Connection

Add your connection to `~/.snowflake/connections.toml`:

```toml
[my_connection]
account = "<your-account>"
user = "<your-user>"
authenticator = "externalbrowser"  # or "snowflake" for password auth
warehouse = "COMPUTE_WH"
role = "ACCOUNTADMIN"
```

### Step 5: Update snowflake.yml (if your database names differ)

Each app has a `snowflake.yml` pointing to specific databases. If your CLD database is named differently, update the `database` and `schema` values.

### Step 6: Deploy All Apps

```bash
# Deploy all 4 Streamlit apps to your account
./deploy_all.sh <your_connection>
```

Or deploy individually:

```bash
cd consolidated_demo && snow streamlit deploy --replace --connection <your_connection>
cd complete_picture  && snow streamlit deploy --replace --connection <your_connection>
cd build2_fleet_ops  && snow streamlit deploy --replace --connection <your_connection>
cd total_cost_ops    && snow streamlit deploy --replace --connection <your_connection>
```

### Step 7: Start the Mobile App (optional)

```bash
cd field_operator
docker compose up -d
# Open http://localhost:5001
```

> Update `docker-compose.yml` with your Snowflake account details. The mobile app needs `~/.snowflake` mounted for authentication.

---

## The Apps

### 1. Consolidated Demo (`consolidated_demo/`)

**The main demo app.** Three tabs with an AI agent on every screen:

| Tab | What It Does | AI Pattern |
|-----|-------------|------------|
| **Asset Health** | 25 pumps, 3-step agentic AI diagnosis (auto-runs on load) | Cortex Search RAG + Cortex COMPLETE |
| **Fleet Operations** | 10 trucks, weather correlations, AI deployment plan | Cortex Agent (text-to-SQL via Semantic View) |
| **What-If Planner** | Interactive savings calculator | Cortex COMPLETE with business context |

**Data sources:** AVEVA CLD (trucks + pumps), WeatherSource, Yes Energy, SAP, Salesforce, 28-doc knowledge base

### 2. Complete Picture (`complete_picture/`)

**Deep-dive into pump asset health.** Four pages:

1. **Fleet Overview** — 25 pumps across 4 DMAs, color-coded risk grid, efficiency ranking
2. **Predicted vs Actual** — AVEVA's 76-channel predictive model, deviation analysis
3. **Weather Context** — Temperature-vibration correlation (r=0.31), weather event detection
4. **AI Agent** — 3-step agentic workflow: analyze → search knowledge base → synthesize recommendation

**Data sources:** AVEVA CLD (pumps), WeatherSource, SAP (work orders + spare parts), 28 industrial docs via Cortex Search

### 3. Fleet Ops (`build2_fleet_ops/`)

**Weather-aware mining truck fleet management.** Includes:

- AI fleet health score (0-100, live)
- Truck-by-truck KPI grid with delta indicators
- Weather-fuel correlation analysis (wind→fuel r=0.51)
- AI shift deployment plan (DEPLOY / LIGHT DUTY / HOLD per truck)
- Rolling z-score anomaly detection with AI narrative
- 7-day weather impact prediction
- **Talk to Your Data** — Cortex Agent chat backed by a Semantic View

**Data sources:** AVEVA CLD (trucks), WeatherSource

### 4. Total Cost of Operations (`total_cost_ops/`)

**Cross-industry cost intelligence.** 9 tabs:

| Tab | Focus |
|-----|-------|
| Truck Fuel | Daily fuel cost, per-truck breakdown |
| Pump Energy | Energy consumption (kWh), pump efficiency |
| Total Cost | Fuel + energy + SLA penalties unified |
| Energy Market | Yes Energy day-ahead vs. real-time spreads |
| Customer Revenue | Salesforce contracts, SLA penalties (87% weather-driven) |
| Weather Multipliers | Validated correlations with scatter plots |
| Digital Twin | GPS map with time scrubber, health scores, failure prediction |
| AI Optimization | 7-day operations schedule via Cortex AI |
| Savings Calculator | Interactive what-if with 3 sliders |

**Data sources:** AVEVA CLD (trucks + pumps), WeatherSource, Yes Energy, Salesforce CRM

### 5. Field Operator Mobile (`field_operator/`)

**Mobile AI assistant** — same Cortex Agent, phone interface. Three personas:

| Persona | Scenario |
|---------|----------|
| Plant Manager | Sees live alerts, taps for AI diagnosis |
| Truck Operator | Gets push notification, asks "is it safe to keep driving?" |
| Maintenance Planner | Agent queries pump data AND knowledge base in one turn |

**Architecture:** Docker (Flask + HTML) → Cortex Agent REST API (SSE streaming) → 3 tools (truck SQL, pump SQL, knowledge search)

**Extras:** English/Italian toggle via Cortex Translate, live API log panel, per-persona chat persistence

---

## Snowflake Cortex AI Capabilities Used

| Capability | Where |
|------------|-------|
| **Cortex COMPLETE** | AI analysis, health scores, deployment plans, predictions |
| **Cortex Search** | RAG over 28 industrial documents (OEM bulletins, SOPs) |
| **Cortex Agent** | Natural language → SQL via Semantic Views |
| **Cortex Analyst** | Text-to-SQL fallback |
| **Semantic Views** | FLEET_SEMANTIC_VIEW (trucks), PUMP_SEMANTIC_VIEW (pumps) |
| **Cortex Translate** | English/Italian in mobile app |

## Data Summary

| Dataset | Rows | Source |
|---------|------|--------|
| Mining trucks (live) | 3.8M+ | AVEVA CLD (Iceberg) |
| Mining trucks (Q1 batch) | 1.7M | AVEVA CLD (Iceberg) |
| Water pumps (live) | 7.6M+ | AVEVA CLD (Iceberg) |
| Weather history | 3,690 | WeatherSource (Marketplace) |
| Energy prices | 17,617 | Yes Energy (Marketplace) |
| Industrial docs | 28 | Cortex Search |
| SAP work orders | 40 | Setup SQL |
| SAP spare parts | 29 | Setup SQL |
| Salesforce contracts | 15 | Setup SQL |
| Salesforce deliveries | 1,350 | Setup SQL |

---

## Repository Structure

```
aveva-snowflake-demos/
├── README.md
├── deploy_all.sh                    # Deploy all 4 SiS apps to any account
├── AVEVA_SNOWFLAKE_USE_CASES.md     # Detailed use case documentation
│
├── consolidated_demo/               # Main 3-tab demo app
│   ├── streamlit_app.py
│   ├── environment.yml
│   ├── snowflake.yml
│   └── setup_cld.sql               # CLD integration reference SQL
│
├── complete_picture/                # Pump asset health (4 pages)
│   ├── streamlit_app.py
│   ├── environment.yml
│   ├── snowflake.yml
│   └── setup.sql                   # SAP tables, knowledge base, Cortex Search
│
├── build2_fleet_ops/                # Weather-aware fleet ops
│   ├── streamlit_app.py
│   ├── environment.yml
│   ├── snowflake.yml
│   ├── setup.sql                   # Pivot view, Semantic View, Cortex Agent
│   └── .streamlit/config.toml
│
├── total_cost_ops/                  # 9-tab cost intelligence
│   ├── streamlit_app.py
│   ├── environment.yml
│   ├── snowflake.yml
│   └── setup.sql                   # Salesforce, deliveries, energy tables
│
└── field_operator/                  # Mobile AI assistant
    ├── streamlit_app.py             # SiS phone mockup version
    ├── environment.yml
    ├── snowflake.yml
    ├── setup.sql                    # Pump semantic view, 3-tool Agent
    ├── docker-compose.yml
    └── app/
        ├── server.py                # Flask backend (SSE streaming)
        ├── Dockerfile
        ├── requirements.txt
        └── templates/
            └── index.html           # Photorealistic iPhone mockup UI
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Database 'AVEVA_CLD_DATA' does not exist` | Your CLD database may be named `CONNECT_AWC26`. Apps auto-detect both — ensure one exists. |
| `Object does not exist: FLEET_SEMANTIC_VIEW` | Run `build2_fleet_ops/setup.sql` first. |
| `INDUSTRIAL_DOCS_SEARCH` not found | Run `complete_picture/setup.sql` first — it creates the knowledge base and Cortex Search service. |
| WeatherSource/Yes Energy errors | Apps fall back to sample data automatically. No action needed. |
| Agent timeout | Warehouse may be suspended. Run any query to warm it up first. |
| Mobile app connection error | Check `docker-compose.yml` has correct account. Ensure `~/.snowflake` is mounted. |

## License

This demo code is provided for evaluation and demonstration purposes. AVEVA Connect data requires a valid AVEVA Connect subscription. Snowflake Marketplace data is subject to provider terms.
