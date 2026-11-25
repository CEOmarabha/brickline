#!/usr/bin/env bash
# launchd wrapper: full local scan at 6:30 AM America/Chicago.
# No-op unless the Chicago clock is 06:xx so a Mac set to UTC cannot fire early.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p data
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"

if [[ -f secrets/event-scanner.env ]]; then
  set -a
  # shellcheck disable=SC1091
  source secrets/event-scanner.env
  set +a
fi

python=python3
if command -v uv >/dev/null; then
  python="uv run python"
fi

chicago_hour="$($python -c 'from datetime import datetime; from zoneinfo import ZoneInfo; print(datetime.now(ZoneInfo("America/Chicago")).hour)')"
if [[ "$chicago_hour" != "6" ]]; then
  echo "skip: America/Chicago hour is ${chicago_hour}, launchd scan runs at 06:30"
  exit 0
fi

exec "$ROOT/scripts/daily-event-scan.sh"
