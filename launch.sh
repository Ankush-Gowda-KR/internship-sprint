#!/usr/bin/env bash
# Opens the Internship Sprint tracker, starting its local server first if it isn't running.
set -u
DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
PORT="${SPRINT_PORT:-47821}"
URL="http://127.0.0.1:${PORT}/"

running() { [ "$(curl -fsS --max-time 1 "${URL}api/ping" 2>/dev/null)" = '"sprint"' ]; }

if ! running; then
  mkdir -p "$DIR/data"
  setsid python3 "$DIR/sprint_server.py" >>"$DIR/data/server.log" 2>&1 </dev/null &
  for _ in $(seq 1 50); do running && break; sleep 0.1; done
fi

if running; then
  # Your default browser, or a specific Chrome profile if SPRINT_CHROME_PROFILE is set (e.g. "Profile 1").
  if [ -n "${SPRINT_CHROME_PROFILE:-}" ] && command -v google-chrome >/dev/null 2>&1; then
    google-chrome --profile-directory="$SPRINT_CHROME_PROFILE" "$URL" >/dev/null 2>&1 &
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 &
  elif command -v open >/dev/null 2>&1; then
    open "$URL" >/dev/null 2>&1 &
  else
    echo "Tracker running: open $URL"
  fi
else
  msg="The tracker didn't start. Details: $DIR/data/server.log"
  notify-send "Internship Sprint" "$msg" 2>/dev/null || echo "$msg" >&2
fi
