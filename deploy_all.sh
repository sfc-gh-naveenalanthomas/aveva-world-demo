#!/usr/bin/env bash
# =============================================================================
# AVEVA World 2026 — Deploy All Streamlit Apps
# =============================================================================
# Deploys all 4 SiS apps (+ optional extras) to a Snowflake account.
#
# Usage:
#   ./deploy_all.sh <connection_name>
#
# Examples:
#   ./deploy_all.sh my_polaris_connection    # Deploy to Polaris (AWS)
#   ./deploy_all.sh aveva_account            # Deploy to AVEVA (Azure)
#
# Prerequisites:
#   1. Snow CLI installed (snow --version)
#   2. Connection configured in ~/.snowflake/connections.toml
#   3. setup.sql for each app already run on the target account
#   4. AVEVA CLD catalog integration configured (CONNECT_AWC26 or AVEVA_CLD_DATA)
#
# What gets deployed:
#   1. Consolidated Demo   → AVEVA_CONNECT.PUBLIC.AVEVA_DEMO_CONSOLIDATED
#   2. Complete Picture     → AVEVA_CONNECT.PUBLIC.COMPLETE_PICTURE_DEMO
#   3. Fleet Ops            → AVEVA_FLEET_OPS.STREAMLIT.WEATHER_AWARE_FLEET_OPS
#   4. Total Cost Ops       → AVEVA_WORLD_DEMOS.STREAMLIT_APPS.TOTAL_COST_OPS
#
# Optional (uncomment below):
#   5. Field Operator (SiS) → AVEVA_CONNECT.PUBLIC.FIELD_OPERATOR_DEMO
#   6. Ennatuurlijk         → AVEVA_CONNECT.PUBLIC.ENNATUURLIJK_DEMO
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
if [ $# -lt 1 ]; then
    echo "Usage: $0 <snowflake_connection_name>"
    echo ""
    echo "Available connections:"
    snow connection list 2>/dev/null | grep "Name" || echo "  (run 'snow connection list' to see)"
    echo ""
    echo "Examples:"
    echo "  $0 my_polaris_connection"
    echo "  $0 aveva_account"
    exit 1
fi

CONNECTION="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ---------------------------------------------------------------------------
# Color output
# ---------------------------------------------------------------------------
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

ok()   { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; }
info() { echo -e "${CYAN}→${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }

# ---------------------------------------------------------------------------
# Verify connection
# ---------------------------------------------------------------------------
echo ""
echo "============================================="
echo " AVEVA World 2026 — Deploy All Apps"
echo " Connection: $CONNECTION"
echo "============================================="
echo ""

info "Testing connection..."
if snow sql -q "SELECT CURRENT_ACCOUNT(), CURRENT_REGION()" --connection "$CONNECTION" > /dev/null 2>&1; then
    ACCOUNT_INFO=$(snow sql -q "SELECT CURRENT_ACCOUNT() || ' (' || CURRENT_REGION() || ')'" --connection "$CONNECTION" 2>/dev/null | grep -oE '[A-Z0-9_]+.*\)' | head -1)
    ok "Connected to $ACCOUNT_INFO"
else
    fail "Cannot connect with connection '$CONNECTION'"
    echo "  Check ~/.snowflake/connections.toml"
    exit 1
fi

# ---------------------------------------------------------------------------
# Deploy function
# ---------------------------------------------------------------------------
TOTAL=0
PASSED=0
FAILED=0

deploy_app() {
    local app_dir="$1"
    local app_name="$2"
    local full_path="$SCRIPT_DIR/$app_dir"

    TOTAL=$((TOTAL + 1))

    if [ ! -d "$full_path" ]; then
        fail "$app_name — directory not found: $app_dir"
        FAILED=$((FAILED + 1))
        return
    fi

    if [ ! -f "$full_path/snowflake.yml" ]; then
        fail "$app_name — no snowflake.yml found"
        FAILED=$((FAILED + 1))
        return
    fi

    info "Deploying $app_name..."
    if cd "$full_path" && snow streamlit deploy --replace --connection "$CONNECTION" > /tmp/deploy_$app_dir.log 2>&1; then
        # Extract the URL from the output
        URL=$(grep -o 'https://[^ ]*' /tmp/deploy_$app_dir.log | head -1)
        ok "$app_name deployed"
        if [ -n "$URL" ]; then
            echo "    $URL"
        fi
        PASSED=$((PASSED + 1))
    else
        fail "$app_name — deployment failed"
        echo "    See /tmp/deploy_$app_dir.log for details"
        tail -5 /tmp/deploy_$app_dir.log 2>/dev/null | sed 's/^/    /'
        FAILED=$((FAILED + 1))
    fi
}

# ---------------------------------------------------------------------------
# Deploy the 4 core apps
# ---------------------------------------------------------------------------
echo ""
echo "--- Core Apps (4) ---"
echo ""

deploy_app "consolidated_demo"  "Consolidated Demo (AVEVA_CONNECT.PUBLIC)"
deploy_app "complete_picture"   "Complete Picture (AVEVA_CONNECT.PUBLIC)"
deploy_app "build2_fleet_ops"   "Fleet Ops (AVEVA_FLEET_OPS.STREAMLIT)"
deploy_app "total_cost_ops"     "Total Cost Ops (AVEVA_WORLD_DEMOS.STREAMLIT_APPS)"

# ---------------------------------------------------------------------------
# Optional: Deploy additional apps (uncomment to include)
# ---------------------------------------------------------------------------
# echo ""
# echo "--- Optional Apps ---"
# echo ""
# deploy_app "field_operator"     "Field Operator SiS (AVEVA_CONNECT.PUBLIC)"
# deploy_app "ennatuurlijk_demo"  "Ennatuurlijk (AVEVA_CONNECT.PUBLIC)"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "============================================="
echo " Deployment Summary"
echo "============================================="
echo ""
echo "  Connection:  $CONNECTION"
echo "  Total:       $TOTAL apps"
echo -e "  ${GREEN}Passed:      $PASSED${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "  ${RED}Failed:      $FAILED${NC}"
fi
echo ""

if [ $FAILED -eq 0 ]; then
    ok "All $PASSED apps deployed successfully"
else
    warn "$FAILED app(s) failed — check logs above"
    exit 1
fi

# ---------------------------------------------------------------------------
# Post-deployment checklist
# ---------------------------------------------------------------------------
echo ""
echo "--- Post-Deployment Checklist ---"
echo ""
echo "  1. Verify CLD data is accessible:"
echo "     snow sql -q \"SELECT COUNT(*) FROM AVEVA_CLD_DATA.\\\"f6dd054e-d7b7-4b48-97f3-1b0eb2e91ab0\\\".mining_haul_truck_narrow_live\" --connection $CONNECTION"
echo ""
echo "  2. Verify Cortex Search is active:"
echo "     snow sql -q \"SHOW CORTEX SEARCH SERVICES IN DATABASE AVEVA_CONNECT\" --connection $CONNECTION"
echo ""
echo "  3. Verify Cortex Agent exists:"
echo "     snow sql -q \"SHOW AGENTS IN DATABASE AVEVA_FLEET_OPS\" --connection $CONNECTION"
echo ""
echo "  4. Test Cortex AI:"
echo "     snow sql -q \"SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', 'Say OK')\" --connection $CONNECTION"
echo ""
echo "  5. Open each app in browser and verify data loads"
echo ""
