#!/usr/bin/env python3
"""identitatis — save.

Ends a session: writes a session record and prepends it to the handoff. That is
the half people skip, and skipping it is why most "AI memory" is a folder that
only grows and never gets read.

Two rules are enforced here rather than documented, because a rule that lives in
a README is a rule that will be broken quietly:

  1. A law needs a WHY. `--law` refuses to write one without a reason. A rule
     with no reason cannot be re-evaluated later — you will not know whether it
     still applies, so you will either follow it forever or drop it blindly.
  2. Nothing is overwritten. Sessions are append-only files; the handoff is
     prepended to. If it were editable, the record would drift toward the story
     you prefer, which is the failure this whole design exists to prevent.

Usage:
    python save.py "what happened this session"
    python save.py --law "short-name" "the rule" --why "what it cost to learn it"
"""
import datetime
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
LAWS = ROOT / "identity" / "laws"
MEMORY = ROOT / "memory"
HANDOFF = MEMORY / "handoff.md"
SESSIONS = MEMORY / "sessions"


def _day():
    text = (ROOT / "identity" / "identity.md").read_text(encoding="utf-8")
    m = re.search(r"^day_zero:\s*(\d{4}-\d{2}-\d{2})", text, re.M)
    if not m:
        return None
    return (datetime.date.today() - datetime.date.fromisoformat(m.group(1))).days


def save_law(name, rule, why):
    LAWS.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    day = _day()
    path = LAWS / f"{datetime.date.today():%Y%m%d}-{slug}.md"
    if path.exists():
        print(f"🔴 {path.name} already exists — laws are not overwritten.")
        return 1
    path.write_text(
        f"# {name}\n\n"
        f"**{rule}**\n\n"
        f"**Why:** {why}\n\n"
        f"*Written {datetime.date.today()}"
        f"{f' · day {day}' if day is not None else ''}.*\n",
        encoding="utf-8")
    print(f"  ✅ law written → {path.relative_to(ROOT)}")
    print("     it will be in every boot from now on.")
    return 0


def save_session(summary):
    SESSIONS.mkdir(parents=True, exist_ok=True)
    MEMORY.mkdir(parents=True, exist_ok=True)
    day = _day()
    now = datetime.datetime.now()
    tag = f"{now:%Y-%m-%d}" + (f" · day {day}" if day is not None else "")
    path = SESSIONS / f"{now:%Y%m%d-%H%M}.md"
    path.write_text(f"# {tag}\n\n{summary}\n", encoding="utf-8")

    old = HANDOFF.read_text(encoding="utf-8") if HANDOFF.exists() else ""
    HANDOFF.write_text(f"## {tag}\n\n{summary}\n\n---\n\n{old}".rstrip() + "\n",
                       encoding="utf-8")
    print(f"  ✅ session → {path.relative_to(ROOT)}")
    print(f"  ✅ handoff updated (newest block on top)")
    print("\n  Next session: python boot.py")
    return 0


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 2
    if a[0] == "--law":
        if "--why" not in a:
            print("🔴 A law without a reason is a rule nobody can re-evaluate later.\n"
                  "   Add --why \"what it cost you to learn this\".")
            return 2
        i = a.index("--why")
        head = a[1:i]
        if len(head) < 2:
            print("🔴 usage: --law \"name\" \"the rule\" --why \"reason\"")
            return 2
        return save_law(head[0], " ".join(head[1:]), " ".join(a[i + 1:]))
    return save_session(" ".join(a))


if __name__ == "__main__":
    sys.exit(main())
