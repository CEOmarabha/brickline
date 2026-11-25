#!/usr/bin/env bash
# Daily event-lead scan.
#   scripts/daily-event-scan.sh                 # full run (public + social if secrets exist)
#   scripts/daily-event-scan.sh --public-only   # calendars + listings; no FB/IG/TikTok sessions
#   scripts/daily-event-scan.sh --chicago-hour  # no-op unless local Chicago hour is 7
# Local Mac: scripts/setup-mac-event-scanner.sh schedules this at 6:30 AM America/Chicago via launchd.
# GitHub Actions stays --public-only --no-llm.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v uv >/dev/null || export PATH="$HOME/.local/bin:$PATH"
python=python3
if command -v uv >/dev/null; then
  python="uv run python"
fi

public_only=0
chicago_hour=0
no_llm=0
for arg in "$@"; do
  case "$arg" in
    --public-only) public_only=1 ;;
    --chicago-hour | --require-chicago-hour) chicago_hour=1 ;;
    --no-llm) no_llm=1 ;;
    -h | --help)
      sed -n '2,6p' "$0"
      exit 0
      ;;
    *)
      echo "unknown argument: $arg (see --help)" >&2
      exit 2
      ;;
  esac
done

args=()
if [[ "$public_only" -eq 1 ]]; then args+=(--public-only); fi
if [[ "$chicago_hour" -eq 1 ]]; then args+=(--require-chicago-hour); fi
if [[ "$no_llm" -eq 1 ]]; then args+=(--no-llm); fi

$python -m engine.leads.event_scan "${args[@]}"
if [[ -n "${DATABASE_URL:-}" && -f web/scripts/upsert-event-leads.mjs ]]; then
  (cd web && node scripts/upsert-event-leads.mjs) || true
fi
