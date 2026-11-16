#!/usr/bin/env bash
# Weekly data refresh: re-download public records, rebuild the warehouse, regenerate the app snapshot.
#   scripts/refresh-data.sh            # refresh everything
#   scripts/refresh-data.sh --backtest # also re-run the historical backtests
# Then commit web/data/snapshot.json, pest.json, prospects.json and contacts.json and republish the app.
set -euo pipefail
cd "$(dirname "$0")/.."

# Raw pages are cached for resumable downloads; clear them so this run fetches fresh data.
rm -rf data/raw/permits data/raw/violations data/raw/sales data/raw/food_licenses data/raw/parcel_addresses \
  data/raw/sr311 data/raw/benchmarking data/raw/res_chars data/raw/food_inspections \
  data/raw/biz_licenses data/raw/biz_owners data/raw/biz_license_history data/raw/adu_preapprovals \
  data/raw/zoning_districts

uv run python -m engine.warehouse sync
uv run python -m engine.warehouse build
# Weekly snapshots of sources that publish only their current state (FMCSA, HFSRB, Cook County buying plan,
# ADU preapprovals, IDPH directories). A failure here must not abort the refresh. Commit
# research/archive/manifest.json afterwards; the data files live in data/archive and the agent store.
uv run python -m engine.collect.archive || echo "WARNING: source archive failed (exit $?); continuing the refresh" >&2
uv run python -m engine.leads.snapshot
uv run python -m engine.leads.pest
uv run python -m engine.leads.prospects --trades porch masonry roofing
# Free contact suggestions (Overture, Chicago business licenses, company websites). Safe to rerun: website
# results are cached in data/raw/web_contacts for 30 days, so only new or stale sites are fetched (~1.5 min cold).
uv run python -m engine.enrich.contacts

if [[ "${1:-}" == "--backtest" ]]; then
  uv run python research/signal_lab/lab.py
  uv run python research/backtests/run_backtests.py
fi

git status --short web/data research/findings research/archive
