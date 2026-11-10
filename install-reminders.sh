#!/usr/bin/env bash
# Sets up the optional streak reminder: a systemd user timer that runs remind.py at 16:00, 21:00 and 23:00.
# Linux with systemd and notify-send only.
# Turn it off: systemctl --user disable --now sprint-remind.timer
set -euo pipefail
DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
UNITS="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
PY="$(command -v python3)"
mkdir -p "$UNITS"

cat >"$UNITS/sprint-remind.service" <<EOF
[Unit]
Description=Internship Sprint streak reminder

[Service]
Type=oneshot
ExecStart=$PY "$DIR/remind.py"
EOF

cat >"$UNITS/sprint-remind.timer" <<'EOF'
[Unit]
Description=Internship Sprint reminders at 16:00, 21:00 and 23:00

[Timer]
OnCalendar=*-*-* 16:00:00
OnCalendar=*-*-* 21:00:00
OnCalendar=*-*-* 23:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now sprint-remind.timer
echo "Reminders are on. Send a test one now: python3 \"$DIR/remind.py\" --test"
