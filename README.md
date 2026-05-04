# AVEVA + Snowflake — Industrial AI Demo Suite

**4 Streamlit-in-Snowflake apps** showcasing AVEVA operational data + Snowflake Marketplace + Cortex AI — from asset health diagnosis to fleet optimization to cost intelligence.

Built for **AVEVA World 2026**.

---

## What's Included

| App | What It Does |
|-----|-------------|
| **Consolidated Demo** | 3-tab operations center with AI agents on every screen (asset health + fleet ops + cost savings) |
| **Complete Picture** | Deep-dive pump health diagnosis — 4 pages with 3-step agentic AI workflow |
| **Fleet Ops** | Weather-aware mining fleet management with Cortex Agent natural language chat |
| **Total Cost Ops** | 9-tab cost intelligence — digital twin, energy markets, SLA penalties, savings calculator |

---

## Prerequisites

- A **Snowflake account** (Enterprise edition or higher for Cortex AI)
- **AVEVA Connect CLD** configured on your account (Iceberg REST Catalog integration)
- **Snow CLI** installed on your machine

### Install Snow CLI

Follow the official guide: https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation/installation

```bash
# macOS (Homebrew)
brew install snowflake-cli

# pip
pip install snowflake-cli

# Verify
snow --version
```

### Configure a Snowflake Connection

Create or edit `~/.snowflake/connections.toml`:

```toml
[aveva_demo]
account = "<your-account-identifier>"
user = "<your-username>"
authenticator = "externalbrowser"
warehouse = "COMPUTE_WH"
role = "ACCOUNTADMIN"
```

> **Finding your account identifier:** https://docs.snowflake.com/en/user-guide/admin-account-identifier
>
> **Connection configuration reference:** https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/configure-connections

Test your connection:
```bash
snow sql -q "SELECT CURRENT_ACCOUNT(), CURRENT_ROLE()" --connection aveva_demo
```

---

## Deployment (3 Steps)

### Step 1: Connect AVEVA Data

Run these two statements in Snowflake to link your AVEVA Connect data:

```sql
-- 1. Register AVEVA's Iceberg REST catalog
CREATE CATALOG INTEGRATION AVEVA_CLD_CATALOG
  CATALOG_SOURCE     = ICEBERG_REST
  TABLE_FORMAT       = ICEBERG
  CATALOG_URI        = 'https://<aveva-connect-endpoint>/iceberg'
  CATALOG_WAREHOUSE  = '<warehouse-name-from-aveva>'
  ACCESS_DELEGATION_MODE = VENDED_CREDENTIALS
  ENABLED = TRUE;

-- 2. Create catalog-linked database (tables sync automatically)
CREATE DATABASE AVEVA_CLD_DATA
  FROM CATALOG INTEGRATION AVEVA_CLD_CATALOG
  AUTO_REFRESH = TRUE;
```

> Your AVEVA Connect team provides the catalog URI and warehouse name. See `consolidated_demo/setup_cld.sql` for a complete annotated example.

**Optional — Marketplace data (recommended):**

Install these free/sample listings from the [Snowflake Marketplace](https://app.snowflake.com/marketplace):
- **WeatherSource** → `GLOBAL_WEATHER__CLIMATE_DATA_FOR_BI`
- **Yes Energy** → `YES_ENERGY__SAMPLE_DATA`

> If not installed, the apps fall back to built-in sample data automatically.

### Step 2: Run Setup SQL

Each app has a `setup.sql` that creates the required tables, views, semantic views, agents, and search services:

```bash
# Creates: SAP tables, knowledge base (28 docs), Cortex Search service
snow sql -f complete_picture/setup.sql --connection aveva_demo

# Creates: Truck pivot view, FLEET_SEMANTIC_VIEW, FLEET_DATA_AGENT
snow sql -f build2_fleet_ops/setup.sql --connection aveva_demo

# Creates: Salesforce CRM, delivery routes, energy price tables
snow sql -f total_cost_ops/setup.sql --connection aveva_demo
```

> The consolidated demo doesn't need its own setup — it uses objects created by the above three scripts.

### Step 3: Deploy Apps

Deploy all 4 apps with one command:

```bash
./deploy_all.sh aveva_demo
```

Or deploy individually:

```bash
cd consolidated_demo && snow streamlit deploy --replace --connection aveva_demo
cd complete_picture  && snow streamlit deploy --replace --connection aveva_demo
cd build2_fleet_ops  && snow streamlit deploy --replace --connection aveva_demo
cd total_cost_ops    && snow streamlit deploy --replace --connection aveva_demo
```

That's it. Open each app from the Snowflake UI under **Streamlit**.

---

## The Apps in Detail

### 1. Consolidated Demo (`consolidated_demo/`)

The primary demo — a single app with three tabs, each showcasing a different Cortex AI pattern:

| Tab | Focus | AI Pattern |
|-----|-------|------------|
| Asset Health | 25 pumps, auto-running 3-step agentic AI diagnosis | Cortex Search RAG + Cortex COMPLETE |
| Fleet Operations | 10 trucks, weather correlations, AI deployment plan, "Talk to Your Data" chat | Cortex Agent (text-to-SQL via Semantic View) |
| What-If Planner | Interactive savings calculator with projections | Cortex COMPLETE with business context |

**Highlights:**
- AI analysis runs automatically on page load — no button click
- Data Foundation expander shows the CLD integration SQL and live row counts
- 6 data sources: AVEVA CLD, WeatherSource, Yes Energy, SAP, Salesforce, Knowledge Base

### 2. Complete Picture (`complete_picture/`)

Four-page deep-dive into pump asset health:

1. **Fleet Overview** — 25 pumps, color-coded risk grid, efficiency ranking
2. **Predicted vs Actual** — AVEVA's 76-channel predictive model with deviation analysis
3. **Weather Context** — Temperature-vibration correlation (r=0.31), weather event detection
4. **AI Agent** — 3-step workflow: analyze structured data → search 28 OEM documents → synthesize grounded recommendation

**Highlights:**
- AI generates its own search queries — decides what documents it needs
- Verdict cites specific OEM bulletins and incident reports by name
- Multilingual output (Spanish, French, Portuguese) via Cortex Translate

### 3. Fleet Ops (`build2_fleet_ops/`)

Weather-aware mining truck fleet dashboard:

- **AI health score** (0–100) computed live on every page load
- **Weather correlations**: Wind → fuel (r=0.51), Temperature → fuel (r=0.49)
- **AI shift deployment plan**: DEPLOY / LIGHT DUTY / HOLD per truck
- **Anomaly detection**: Rolling z-score with AI-generated narrative
- **7-day weather impact prediction** with dollar estimates
- **Talk to Your Data**: Cortex Agent chat with natural language → SQL

### 4. Total Cost Ops (`total_cost_ops/`)

9-tab cost intelligence platform:

| Tab | What It Shows |
|-----|---------------|
| Truck Fuel | Daily cost, per-truck breakdown, cost per tonne |
| Pump Energy | Energy consumption (kWh), pump-by-pump efficiency |
| Total Cost | Fuel + energy + SLA penalties unified |
| Energy Market | Yes Energy day-ahead vs. real-time price spreads |
| Customer Revenue | Salesforce contracts, SLA penalties (87% weather-driven) |
| Weather Multipliers | Validated correlations with scatter plots |
| Digital Twin | GPS map with time scrubber, health scores, failure prediction |
| AI Optimization | 7-day operations schedule generated by Cortex AI |
| Savings Calculator | Interactive what-if with 3 sliders — quarterly savings projections |

---

## Snowflake Cortex AI Capabilities Used

| Capability | What It Does | Where |
|------------|-------------|-------|
| **Cortex COMPLETE** | LLM reasoning and generation (mistral-large2) | All apps — analysis, scores, plans, predictions |
| **Cortex Search** | Semantic search over documents (arctic-embed-m-v1.5) | Complete Picture + Consolidated Demo (28 OEM docs) |
| **Cortex Agent** | Multi-tool orchestration with text-to-SQL | Fleet Ops "Talk to Your Data" chat |
| **Semantic Views** | Natural language → SQL mapping | FLEET_SEMANTIC_VIEW (24 truck metrics) |
| **Cortex Translate** | Multilingual output | Complete Picture (es/fr/pt) |

---

## Data Summary

| Dataset | Volume | Source |
|---------|--------|--------|
| Mining trucks (live stream) | 3.8M+ rows | AVEVA CLD (Iceberg) |
| Mining trucks (Q1 batch) | 1.7M rows | AVEVA CLD (Iceberg) |
| Water pumps (live stream) | 7.6M+ rows | AVEVA CLD (Iceberg) |
| Calgary weather | 3,690 days | WeatherSource (Marketplace) |
| Alberta energy prices | 17,617 hours | Yes Energy (Marketplace) |
| Industrial knowledge base | 28 documents | Cortex Search |
| SAP work orders | 40 records | Setup SQL |
| SAP spare parts | 29 records | Setup SQL |
| Salesforce contracts | 15 contracts | Setup SQL |

---

## Repository Structure

```
aveva-world-demo/
├── README.md
├── deploy_all.sh                    # One-command deploy for all 4 apps
├── AVEVA_SNOWFLAKE_USE_CASES.md     # Detailed use case documentation
│
├── consolidated_demo/               # Main 3-tab operations center
│   ├── streamlit_app.py
│   ├── environment.yml
│   ├── snowflake.yml
│   └── setup_cld.sql               # CLD integration reference
│
├── complete_picture/                # Pump asset health (4 pages)
│   ├── streamlit_app.py
│   ├── environment.yml
│   ├── snowflake.yml
│   └── setup.sql                   # SAP tables + knowledge base + Cortex Search
│
├── build2_fleet_ops/                # Weather-aware fleet operations
│   ├── streamlit_app.py
│   ├── environment.yml
│   ├── snowflake.yml
│   ├── setup.sql                   # Pivot view + Semantic View + Cortex Agent
│   └── .streamlit/config.toml
│
└── total_cost_ops/                  # 9-tab cost intelligence
    ├── streamlit_app.py
    ├── environment.yml
    ├── snowflake.yml
    └── setup.sql                   # Salesforce + deliveries + energy tables
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Database 'AVEVA_CLD_DATA' does not exist` | Your CLD database may be named `CONNECT_AWC26`. The apps auto-detect both names. |
| `FLEET_SEMANTIC_VIEW` not found | Run `build2_fleet_ops/setup.sql` first |
| `INDUSTRIAL_DOCS_SEARCH` not found | Run `complete_picture/setup.sql` first |
| WeatherSource / Yes Energy errors | Apps fall back to sample data automatically — no action needed |
| Agent timeout on first query | Warehouse may be suspended. Run any query to warm it up. |
| Snow CLI not found | Install: https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation/installation |
| Connection error | Check `~/.snowflake/connections.toml` — see https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/configure-connections |

---

## Useful Links

- [Snow CLI Installation](https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation/installation)
- [Configuring Snowflake Connections](https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/configure-connections)
- [Account Identifiers](https://docs.snowflake.com/en/user-guide/admin-account-identifier)
- [Streamlit in Snowflake](https://docs.snowflake.com/en/developer-guide/streamlit/about-streamlit)
- [Cortex AI Functions](https://docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions)
- [Cortex Search](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview)
- [Cortex Agent](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agent)
- [Semantic Views](https://docs.snowflake.com/en/user-guide/views-semantic)
- [Catalog Integrations (Iceberg)](https://docs.snowflake.com/en/sql-reference/sql/create-catalog-integration-rest-config)

---

## License

Demo code provided for evaluation purposes. AVEVA Connect data requires a valid AVEVA subscription. Snowflake Marketplace data subject to provider terms.
