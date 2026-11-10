#!/usr/bin/env python3
"""Streak reminder for Internship Sprint (Linux desktop notifications, optional).

Run by the sprint-remind.timer systemd user timer at 16:00, 21:00 and 23:00 (install-reminders.sh sets it up).
In the evening, if today's streak isn't done or a milestone is overdue or due within a day, it shows a desktop
notification saying what's left, with an "Open tracker" button. From the sprint's second week, the 16:00 run
also fires if nothing at all is logged yet. Days that are done get nothing. The rules match index.html: 1 DSA
problem, 1 SQL problem and 1 application, or an OA/interview day; a used freeze carries a missed day.

    python3 remind.py --test    # send it now, whatever the time
"""
import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_FILE = HERE / "data" / "sprint.json"
WAIT_FOR_CLICK = 50 * 60  # seconds; ends before the 23:00 run so that one isn't skipped
# The reminders get stricter as the sprint goes on, counted in days from plan.start:
MIDDAY_AFTER = 7   # from day 8: a 16:00 nudge if nothing is logged yet
STRICT_AFTER = 14  # from day 15: the 21:00 reminder stays on screen too


def needs(state, day):
    """What the streak still needs on `day` (a YYYY-MM-DD string); empty means it counts.
    Keep this in step with streakNeeds() in index.html."""
    d = (state.get("days") or {}).get(day) or {}
    if d.get("oa"):
        return []
    apps = sum(1 for a in state.get("apps") or [] if isinstance(a, dict) and a.get("date") == day)
    left = []
    if int(d.get("dsa") or 0) < 1:
        left.append("1 DSA problem")
    if int(d.get("sql") or 0) < 1:
        left.append("1 SQL problem")
    if apps < 1:
        left.append("1 application")
    return left


def streak_before(state, today):
    """The streak through yesterday, counted the way the tracker counts it."""
    start = (state.get("plan") or {}).get("start")
    if not start:
        return 0
    used = {s.get("usedOn") for s in state.get("spends") or []
            if isinstance(s, dict) and s.get("rewardId") == "freeze"}
    cur, day = 0, date.fromisoformat(start)
    while day < today:
        k = day.isoformat()
        if not needs(state, k):
            cur += 1
        elif k not in used:
            cur = 0
        day += timedelta(days=1)
    return cur


def and_list(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def logged_anything(state, day):
    d = (state.get("days") or {}).get(day) or {}
    if any(int(d.get(k) or 0) > 0 for k in ("dsa", "sql", "cs", "outreach")) or d.get("focus") or d.get("oa"):
        return True
    return any(isinstance(a, dict) and a.get("date") == day for a in state.get("apps") or [])


def milestone_done(state, m):
    """Same rule as the tracker: auto milestones count from the log, the rest are ticked by hand."""
    kind = (m.get("auto") or {}).get("kind")
    if not kind:
        return bool(m.get("done"))
    if kind == "apps":
        have = len(state.get("apps") or [])
    else:
        have = sum(int((d or {}).get(kind) or 0) for d in (state.get("days") or {}).values())
    return have >= int((m.get("auto") or {}).get("target") or 0)


def due_soon(state, today):
    """Unfinished milestones that are overdue or due today or tomorrow."""
    out = []
    for m in state.get("milestones") or []:
        due = m.get("due")
        if not due or milestone_done(state, m):
            continue
        d = date.fromisoformat(due)
        if d <= today + timedelta(days=1):
            out.append(f"{m.get('title', '')} ({'overdue' if d < today else 'today' if d == today else 'tomorrow'})")
    return out


def main():
    test = "--test" in sys.argv
    now = datetime.now()
    today, key = now.date(), now.date().isoformat()
    if not test and not 16 <= now.hour <= 23:
        return  # a run caught up after the computer was off; that day's window is over
    if not DATA_FILE.exists():
        return  # the tracker hasn't been started yet
    state = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    start = (state.get("plan") or {}).get("start")
    day_no = (today - date.fromisoformat(start)).days if start else 0  # 0 on the sprint's first day
    due = due_soon(state, today)
    if now.hour < 20 and not test:
        # The 16:00 run: from the second week, and only if nothing at all is logged yet today.
        if day_no < MIDDAY_AFTER or logged_anything(state, key):
            return
        title, body, urgent = "Nothing logged yet today", "Start small: a SQLBolt lesson takes 10 minutes and counts.", False
    else:
        left = needs(state, key)
        if not left and (not due or now.hour >= 23):
            return  # deadline-only reminders come at 21:00; 23:00 is the streak's last call
        last_call = now.hour >= 23
        if left:
            streak = streak_before(state, today)
            title = ("Last call: " if last_call else "") + (
                f"your {streak}-day streak ends at midnight" if streak else "today's streak isn't done yet")
            body = f"Still to do: {and_list(left)}. Had an OA or interview today? Tick it in the tracker instead."
        else:
            title, body = "Streak's done, but a deadline isn't", ""
        # A streak at risk at 23:00 stays on screen; from the third week, so does the 21:00 one.
        urgent = bool(left) and (last_call or day_no >= STRICT_AFTER)
    if due:
        body = (body + " " if body else "") + "Deadlines: " + "; ".join(due) + "."
    cmd = ["notify-send", "--app-name=Internship Sprint", f"--icon={HERE / 'icon.svg'}",
           f"--urgency={'critical' if urgent else 'normal'}", "--action=open=Open tracker",
           "🔥 " + title[0].upper() + title[1:], body]
    try:
        clicked = subprocess.run(cmd, capture_output=True, text=True,
                                 timeout=60 if test else WAIT_FOR_CLICK).stdout.strip()
    except subprocess.TimeoutExpired:
        return  # nobody clicked; the notification stays in the tray
    if clicked == "open":
        subprocess.Popen([str(HERE / "launch.sh")], start_new_session=True)


if __name__ == "__main__":
    main()
