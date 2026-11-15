#!/usr/bin/env bash
# Weekly data refresh: re-download public records, rebuild the warehouse, regenerate the app snapshot.
#   scripts/refresh-data.sh            # refresh everything
#   scripts/refresh-data.sh --backtest # also re-run the historical backtests
# Then commit web/data/snapshot.json and republish the app.
set -euo pipefail
cd "$(dirname "$0")/.."

# Raw pages are cached for resumable downloads; clear them so this run fetches fresh data.
rm -rf data/raw/permits data/raw/violations data/raw/sales data/raw/food_licenses data/raw/parcel_addresses \
  data/raw/sr311 data/raw/benchmarking data/raw/res_chars

uv run python -m engine.warehouse sync
uv run python -m engine.warehouse build
uv run python -m engine.leads.snapshot
uv run python -m engine.leads.prospects --trades porch masonry roofing

if [[ "${1:-}" == "--backtest" ]]; then
  uv run python research/signal_lab/lab.py
  uv run python research/backtests/run_backtests.py
fi

git status --short web/data research/findings
