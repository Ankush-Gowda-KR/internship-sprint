#!/usr/bin/env python3
"""Local server for the Internship Sprint tracker.

Serves index.html and keeps every entry in data/sprint.json on this computer.
Listens on 127.0.0.1 only, so no other device on the network can reach it.
Standard library only: runs on the system python3, no venv needed.

On the first run it creates data/sprint.json from starter.json, with the sprint starting today
(or on SPRINT_START=YYYY-MM-DD if that's set).
"""
import json
import os
import shutil
import tempfile
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
STARTER = HERE / "starter.json"
DATA_DIR = HERE / "data"
DATA_FILE = DATA_DIR / "sprint.json"
BACKUP_DIR = DATA_DIR / "backups"
ACTIVITY_LOG = DATA_DIR / "activity.jsonl"
COUNTERS = ("dsa", "sql", "cs", "outreach")
TICKS = ("focus", "oa")
HOST = "127.0.0.1"
PORT = int(os.environ.get("SPRINT_PORT", "47821"))
ALLOWED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
ALLOWED_ORIGINS = {f"http://{h}" for h in ALLOWED_HOSTS}
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/icon.svg": ("icon.svg", "image/svg+xml"),
}
MAX_BODY = 4 * 1024 * 1024


def new_state():
    """A fresh tracker from starter.json. Its dates are day numbers counted from the start (0 = the first day)."""
    starter = json.loads(STARTER.read_text(encoding="utf-8"))
    start = date.fromisoformat(os.environ["SPRINT_START"]) if os.environ.get("SPRINT_START") else date.today()

    def on(n):
        return (start + timedelta(days=int(n))).isoformat()

    plan = starter["plan"]
    plan["start"] = on(0)
    plan["end"] = on(int(plan.pop("days", 61)) - 1)
    for w in plan.get("weeks") or []:
        w["from"] = on(w.get("from", 0))
    milestones = starter.get("milestones") or []
    for m in milestones:
        if m.get("due") is not None:
            m["due"] = on(m["due"])
        m.setdefault("done", False)
        m.setdefault("doneAt", None)
    return {"rev": 0, "plan": plan, "days": {}, "apps": [], "milestones": milestones,
            "rewards": starter.get("rewards") or [], "spends": [], "timer": None}


def load_state():
    if not DATA_FILE.exists():
        return {"rev": 0}
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    """Write atomically; the first save of each day copies the previous file to backups/."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / f"sprint-{date.today().isoformat()}.json"
    if DATA_FILE.exists() and not backup.exists():
        shutil.copy2(DATA_FILE, backup)
    fd, tmp = tempfile.mkstemp(dir=DATA_DIR, prefix=".sprint-", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    os.replace(tmp, DATA_FILE)


def by_id(items):
    return {x.get("id"): x for x in items or [] if isinstance(x, dict)}


def changes(old, new):
    """What one save changed: counters, ticks, applications, spends, milestones."""
    out = []
    old_days, new_days = old.get("days") or {}, new.get("days") or {}
    for day in sorted(set(old_days) | set(new_days)):
        a, b = old_days.get(day) or {}, new_days.get(day) or {}
        for k in COUNTERS:
            x, y = int(a.get(k) or 0), int(b.get(k) or 0)
            if x != y:
                out.append({"day": day, "what": k, "from": x, "to": y})
        for k in TICKS:
            if bool(a.get(k)) != bool(b.get(k)):
                out.append({"day": day, "what": k, "to": bool(b.get(k))})
    old_apps, new_apps = by_id(old.get("apps")), by_id(new.get("apps"))
    for i, x in new_apps.items():
        if i not in old_apps:
            out.append({"day": x.get("date"), "what": "app", "company": x.get("company"), "channel": x.get("channel")})
        elif old_apps[i].get("status") != x.get("status"):
            out.append({"day": x.get("date"), "what": "app status", "company": x.get("company"),
                        "from": old_apps[i].get("status"), "to": x.get("status")})
    for i, x in old_apps.items():
        if i not in new_apps:
            out.append({"day": x.get("date"), "what": "app deleted", "company": x.get("company")})
    old_spends, new_spends = by_id(old.get("spends")), by_id(new.get("spends"))
    for i, x in new_spends.items():
        if i not in old_spends:
            out.append({"day": x.get("date"), "what": "spend", "name": x.get("name"), "cost": x.get("cost")})
        elif old_spends[i].get("usedOn") != x.get("usedOn"):
            out.append({"day": x.get("usedOn"), "what": "freeze used"})
    for i, x in old_spends.items():
        if i not in new_spends:
            out.append({"day": x.get("date"), "what": "spend undone", "name": x.get("name"), "cost": x.get("cost")})
    old_ms = by_id(old.get("milestones"))
    for i, x in by_id(new.get("milestones")).items():
        if i in old_ms and bool(old_ms[i].get("done")) != bool(x.get("done")):
            out.append({"what": "milestone", "title": x.get("title"), "to": bool(x.get("done"))})
    return out


def log_activity(entries):
    """Appends a timestamped line per change to data/activity.jsonl: a plain history of what you did and when."""
    if not entries:
        return
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    with open(ACTIVITY_LOG, "a", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps({"ts": ts, **e}, ensure_ascii=False) + "\n")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep server.log quiet

    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def host_ok(self):
        # Blocks DNS rebinding: a hostile site that points its own domain at 127.0.0.1
        # still sends its own domain in the Host header.
        return self.headers.get("Host", "") in ALLOWED_HOSTS

    def do_GET(self):
        if not self.host_ok():
            return self.send(403, '{"error":"bad host"}')
        path = self.path.split("?", 1)[0]
        if path == "/api/ping":
            return self.send(200, '"sprint"')
        if path == "/api/state":
            try:
                return self.send(200, json.dumps(load_state(), ensure_ascii=False))
            except ValueError:
                return self.send(500, '{"error":"data/sprint.json is unreadable; restore one from data/backups/"}')
        if path in STATIC:
            name, ctype = STATIC[path]
            return self.send(200, (HERE / name).read_bytes(), ctype)
        self.send(404, '{"error":"not found"}')

    def do_PUT(self):
        origin = self.headers.get("Origin")
        if not self.host_ok() or (origin is not None and origin not in ALLOWED_ORIGINS):
            return self.send(403, '{"error":"forbidden"}')
        if self.path != "/api/state":
            return self.send(404, '{"error":"not found"}')
        # Requiring JSON on a PUT forces a CORS preflight, which this server never approves,
        # so scripts on other websites can't write here.
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            return self.send(415, '{"error":"expected JSON"}')
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= MAX_BODY:
            return self.send(413, '{"error":"bad size"}')
        try:
            incoming = json.loads(self.rfile.read(length))
        except ValueError:
            return self.send(400, '{"error":"invalid JSON"}')
        if not isinstance(incoming, dict) or not isinstance(incoming.get("rev"), int):
            return self.send(400, '{"error":"expected an object with an integer rev"}')
        try:
            current = load_state()
        except ValueError:
            return self.send(500, '{"error":"data/sprint.json is unreadable; restore one from data/backups/"}')
        # A tab holding an older copy can't overwrite newer data: it gets the latest back instead.
        if incoming["rev"] != current.get("rev", 0):
            return self.send(409, json.dumps(current, ensure_ascii=False))
        incoming["rev"] += 1
        save_state(incoming)
        try:
            log_activity(changes(current, incoming))
        except Exception as e:  # a logging problem must never block a save
            print(f"activity log failed: {e!r}", flush=True)
        self.send(200, json.dumps({"rev": incoming["rev"]}))


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        state = new_state()
        save_state(state)
        print(f"New sprint from starter.json: {state['plan']['start']} to {state['plan']['end']}", flush=True)
    print(f"Internship Sprint on http://{HOST}:{PORT}/  (data: {DATA_FILE})", flush=True)
    HTTPServer((HOST, PORT), Handler).serve_forever()
