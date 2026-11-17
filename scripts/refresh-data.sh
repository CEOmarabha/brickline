#!/usr/bin/env bash
# Weekly data refresh: re-download public records, rebuild the warehouse, regenerate the app data.
#   scripts/refresh-data.sh            # refresh everything
#   scripts/refresh-data.sh --backtest # also re-run the signal lab, the backtests and the zoning parse check
# Then commit web/data/*.json, research/findings and research/archive/manifest.json, and republish the app.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v uv >/dev/null || export PATH="$HOME/.local/bin:$PATH"

backtest=0
for arg in "$@"; do
  case "$arg" in
    --backtest) backtest=1 ;;
    -h | --help)
      sed -n '2,5p' "$0"
      exit 0
      ;;
    *)
      echo "unknown argument: $arg (see --help)" >&2
      exit 2
      ;;
  esac
done

# Raw pages are cached for resumable downloads; clear every dataset that changes so this run fetches fresh data.
# Not listed on purpose: community_areas, tracts_2010 and tracts_2020 (fixed boundaries); noaa, swdi and overture
# (the collectors refetch the current and previous year, the unfinished month, and a newer release themselves);
# hmda (yearly files, kept once published); clerk (list pages are refetched on every sync); web_contacts (30-day
# cache by design); hfsrb (written only by the optional engine.collect.hfsrb run).
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
# snapshot and prospects must run before contacts, which reads web/data/snapshot.json and web/data/prospects.json.
uv run python -m engine.leads.snapshot
uv run python -m engine.leads.pest
uv run python -m engine.leads.prospects --trades porch masonry roofing
# Free contact suggestions (Overture, Chicago business licenses, company websites). Safe to rerun: website
# results are cached in data/raw/web_contacts for 30 days, so only new or stale sites are fetched (~1.5 min cold).
uv run python -m engine.enrich.contacts

if [[ $backtest -eq 1 ]]; then
  uv run python research/signal_lab/lab.py
  uv run python research/backtests/run_backtests.py
  uv run python research/probes/clerk_parse_check.py
fi

git status --short web/data research/findings research/archive
