#!/usr/bin/env bash
# One-command Mac setup for the $0 daily event-lead scanner.
#
#   scripts/setup-mac-event-scanner.sh
#   scripts/setup-mac-event-scanner.sh --skip-sessions   # deps + launchd only
#   scripts/setup-mac-event-scanner.sh --skip-launchd    # deps + optional sessions
#
# Installs Python deps and Playwright Chromium, copies secrets/event-scanner.env,
# optionally saves Facebook / Instagram / TikTok sessions, and schedules a full
# local scan at 6:30 AM America/Chicago via launchd. GitHub Actions stays public-only.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

skip_sessions=0
skip_launchd=0
for arg in "$@"; do
  case "$arg" in
    --skip-sessions) skip_sessions=1 ;;
    --skip-launchd) skip_launchd=1 ;;
    -h | --help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *)
      echo "unknown argument: $arg (see --help)" >&2
      exit 2
      ;;
  esac
done

py=python3
if ! command -v "$py" >/dev/null; then
  echo "python3 is required (install from python.org or Homebrew)" >&2
  exit 1
fi
"$py" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit(f"Python 3.11+ required, found {sys.version.split()[0]}")
print(f"python {sys.version.split()[0]}")
PY

echo "==> Python packages (duckdb, playwright)"
if command -v uv >/dev/null; then
  uv pip install --python "$py" -e ".[social]" || uv pip install --python "$py" duckdb playwright
else
  "$py" -m pip install --user -e ".[social]" 2>/dev/null || "$py" -m pip install --user duckdb playwright
fi
"$py" -m playwright install chromium

mkdir -p secrets data
if [[ ! -f secrets/event-scanner.env ]]; then
  cp event-scanner.env.example secrets/event-scanner.env
  echo "wrote secrets/event-scanner.env from the example (gitignored)"
fi

if [[ "$skip_sessions" -eq 0 ]]; then
  if [[ ! -t 0 ]]; then
    echo "no TTY; skip headed session save (re-run without --skip-sessions on a Mac)"
  else
    echo
    echo "Save Facebook / Instagram / TikTok sessions? A headed browser will open."
    echo "Log in as the team's real account, then press Enter in this terminal."
    read -r -p "Save sessions now? [y/N] " answer
    if [[ "$answer" =~ ^[Yy] ]]; then
      for platform in facebook instagram tiktok; do
        "$py" -m engine.collect.social.save_session "$platform" || true
      done
    fi
  fi
fi

if [[ "$skip_launchd" -eq 1 ]]; then
  echo "skip launchd (--skip-launchd)"
  exit 0
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "not macOS; launchd plist not installed. On a Mac, re-run this script."
  echo "Set System Settings → General → Date & Time to America/Chicago so 6:30 local is Chicago."
  exit 0
fi

plist_src="$ROOT/scripts/macos/org.brickline.event-scan.plist.in"
plist_dest="$HOME/Library/LaunchAgents/org.brickline.event-scan.plist"
mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/data"
sed "s|@REPO@|$ROOT|g" "$plist_src" > "$plist_dest"
chmod +x "$ROOT/scripts/daily-event-scan.sh" "$ROOT/scripts/launchd-event-scan.sh"
launchctl bootout "gui/$(id -u)/org.brickline.event-scan" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$plist_dest"
echo
echo "Scheduled org.brickline.event-scan at 6:30 AM (this Mac's timezone)."
echo "Set the timezone to America/Chicago (System Settings → General → Date & Time)."
echo "The wrapper also no-ops unless America/Chicago hour is 06."
echo "Logs: $ROOT/data/event-scan.launchd.log"
echo "Full scan (local): $ROOT/scripts/daily-event-scan.sh"
echo "Public-only (CI):  $ROOT/scripts/daily-event-scan.sh --public-only --no-llm"
