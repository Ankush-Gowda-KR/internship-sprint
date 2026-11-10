# Internship Sprint

A local tracker for an internship hunt. You set a daily floor of applications and practice problems, keep a
streak going, earn points, and spend them on rewards you pick yourself. Milestones keep the bigger tasks moving.
Everything runs on your own computer, and your data never leaves it.

## AI disclosure

This project was vibecoded with Claude Code, Anthropic's AI coding agent, and Claude Code wrote the code. I
directed it: what to build, how the rules work, and what to change after using it.

## Run it

You need Python 3.8 or newer. It uses only the standard library, so there's nothing to install.

```bash
git clone https://github.com/Ankush-Gowda-KR/internship-sprint.git
cd internship-sprint
python3 sprint_server.py
```

Then open <http://127.0.0.1:47821/>. On Linux or macOS, `./launch.sh` does both: it starts the server if it
isn't running, then opens the page. On Windows, run `python sprint_server.py` and open the link.

The first start creates `data/sprint.json` from `starter.json`: a 61-day sprint that starts today. To start on
another day, run the first start as `SPRINT_START=2026-11-16 python3 sprint_server.py`.

## How it works

- **Today:** log applications (company, role, where you applied), DSA problems, SQL problems, fundamentals
  topics, outreach messages, a focus block, or an OA/interview day. Each row shows what it's worth. The ‹ arrow
  goes back to log a day you forgot.
- **Floor:** each week's daily targets come from `plan.weeks` and ramp up over the sprint. Meeting all of them
  is the floor and pays a bonus. 5 floor days out of 7 is a good week.
- **🔥 Streak:** 1 DSA problem, 1 SQL problem and 1 application in a day keep it alive, and an OA or interview
  day counts on its own. Freezes cost points and you can hold 2. If you miss a day, you can use one on it up to
  3 days later.
- **👑 Legendary streak:** the whole floor, with every DSA and SQL problem done on the in-page timer in one
  sitting (45 and 20 minutes by default). Going over still counts, but it adds one problem of that kind to
  tomorrow's legendary floor. Its freezes are automatic: you start with 2 and earn one back every 5 legendary
  days.
- **Points:**

  | What | Points |
  |---|---|
  | Application | 2 |
  | DSA problem | 3 |
  | SQL problem | 3 |
  | Fundamentals topic | 2 |
  | Outreach message | 2 |
  | Focus block | 5 |
  | OA or interview | 10 |
  | Full floor | +5 bonus |
  | Milestones | as listed |

  Unspent points fade: half of what's left over disappears on the morning each sprint week starts, so spend
  them.
- **Rewards:** add your own on the Rewards page, put them in the cart, and check out. Nothing is spent until
  you check out, and a claim can be undone until midnight.
- **Milestones:** the counted ones (applications, DSA, SQL) fill themselves from what you log. You tick the
  rest when they're done.

## Make it yours

Edit `starter.json` before the first start. After that, edit `data/sprint.json`, but stop the server first (or
add 1 to `rev`), or an open tab will overwrite your edit. In `starter.json`, `from` and `due` are day numbers
counted from the start (0 is the first day); `data/sprint.json` holds real dates.

- `plan.days`, `plan.goal`, `plan.weekTarget`: the sprint's length, the big prize, and the good-week count.
- `plan.points`: what each thing is worth, plus `freeze`, the price of a streak freeze.
- `plan.weeks`: the daily targets per week (`apps`, `dsa`, `sql`, `cs` for fundamentals, `outreach`). A target
  of 0 makes that row optional for the week.
- `plan.legendary`: `dsaMin` and `sqlMin` for the timer. Set `outreachAfter` to a milestone id (such as your
  LinkedIn one) to leave outreach out of the legendary floor until that milestone is ticked.
- `plan.decay`: `{"weeklyRate": 0.5}` is the weekly half. Use `{"rate": 0.25, "weeklyFrom": null}` to fade a
  quarter every morning instead, or `{"weeklyRate": 0}` to switch fading off.
- `milestones`: `title`, `due`, `pts`, and optionally `note`, `prize`, or `auto: {"kind": "apps" | "dsa" | "sql",
  "target": N}` for one that counts itself.
- `rewards`: also editable on the Rewards page.

The streak rule is written in two places: `streakNeeds()` in `index.html` and `needs()` in `remind.py`. If you
change it, change both.

## Reminders (optional, Linux)

`./install-reminders.sh` sets up a systemd user timer that runs `remind.py` at 16:00, 21:00 and 23:00. If
today's streak isn't done, or a milestone is due within a day, you get a desktop notification with an "Open
tracker" button. From the second week, the 16:00 one also fires if nothing is logged yet. From the third week,
the 21:00 one stays on screen.

- Test it now: `python3 remind.py --test`
- Turn it off: `systemctl --user disable --now sprint-remind.timer`

## Your data

- `data/sprint.json` holds everything. The first save each day copies the old file to `data/backups/`, and
  `data/activity.jsonl` keeps a timestamped history of what changed. `data/` is in `.gitignore`.
- The server listens on 127.0.0.1 only and checks the Host header, so a website can't reach it through DNS
  rebinding. Saves must be JSON from the page's own origin, and a stale tab can't overwrite newer data (it gets
  the latest copy back instead).

## License

MIT.
