#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# setup/setup_bigquery.sh
#
# Creates the mcp_bakery BigQuery dataset and loads all four CSV tables
# from the local data/ directory.
#
# Usage (from the bakery_agent/ project root):
#   chmod +x setup/setup_bigquery.sh
#   ./setup/setup_bigquery.sh
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - GOOGLE_CLOUD_PROJECT env var set, OR project configured in gcloud
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Resolve project ID ────────────────────────────────────────────────────────
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "project_not_set" ]]; then
  echo "❌  ERROR: GOOGLE_CLOUD_PROJECT is not set."
  echo "   Run: export GOOGLE_CLOUD_PROJECT=your-project-id"
  exit 1
fi

DATASET="mcp_bakery"
LOCATION="US"
DATA_DIR="$(cd "$(dirname "$0")/data" && pwd)"

echo "──────────────────────────────────────────────────────"
echo " Bakery Agent — BigQuery Setup"
echo " Project  : ${PROJECT_ID}"
echo " Dataset  : ${DATASET}"
echo " Location : ${LOCATION}"
echo " Data dir : ${DATA_DIR}"
echo "──────────────────────────────────────────────────────"

# ── Enable BigQuery API ───────────────────────────────────────────────────────
echo ""
echo "▶  Enabling BigQuery API..."
gcloud services enable bigquery.googleapis.com --project="${PROJECT_ID}" --quiet
echo "✅ BigQuery API enabled."

# ── Enable BigQuery MCP API (preview) ────────────────────────────────────────
echo ""
echo "▶  Enabling BigQuery MCP server (preview)..."
gcloud beta services mcp enable bigquery.googleapis.com \
  --project="${PROJECT_ID}" --quiet 2>/dev/null || \
  echo "⚠  MCP enable failed — the beta command may not be available in your environment."
echo "   (If above failed, enable manually in Cloud Console → APIs & Services)"

# ── Create dataset ────────────────────────────────────────────────────────────
echo ""
echo "▶  Creating dataset '${DATASET}' in region ${LOCATION}..."
bq --project_id="${PROJECT_ID}" mk \
  --force \
  --dataset \
  --location="${LOCATION}" \
  --description="Bakery location intelligence data for ADK MCP agent" \
  "${PROJECT_ID}:${DATASET}" && echo "✅ Dataset ready."

# ── Helper: load a CSV into a BigQuery table ──────────────────────────────────
load_table() {
  local TABLE_NAME="$1"
  local CSV_FILE="${DATA_DIR}/${TABLE_NAME}.csv"
  local FULL_TABLE="${PROJECT_ID}:${DATASET}.${TABLE_NAME}"

  if [[ ! -f "${CSV_FILE}" ]]; then
    echo "❌  CSV not found: ${CSV_FILE}"
    return 1
  fi

  echo ""
  echo "▶  Loading ${TABLE_NAME}..."
  bq --project_id="${PROJECT_ID}" load \
    --replace \
    --source_format=CSV \
    --skip_leading_rows=1 \
    --autodetect \
    "${FULL_TABLE}" \
    "${CSV_FILE}" && echo "✅ ${TABLE_NAME} loaded."
}

# ── Load all four tables ──────────────────────────────────────────────────────
load_table "bakery_prices"
load_table "demographics"
load_table "foot_traffic"
load_table "sales_history_weekly"

# ── Verify ────────────────────────────────────────────────────────────────────
echo ""
echo "▶  Verifying tables..."
bq --project_id="${PROJECT_ID}" ls "${PROJECT_ID}:${DATASET}"

echo ""
echo "──────────────────────────────────────────────────────"
echo " ✅  Setup complete!"
echo ""
echo " Next steps:"
echo "   1. Copy mcp_bakery_app/.env.example → mcp_bakery_app/.env"
echo "   2. Fill in GOOGLE_API_KEY and MAPS_API_KEY"
echo "   3. From bakery_agent/: run  adk web ."
echo "──────────────────────────────────────────────────────"
