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
  2. Nothing is overwritten. Sessions get a name nothing else can hold and are
     created exclusively; the handoff is prepended to, never edited. If the
     record were editable it would drift toward the story you prefer, which is
     the failure this whole design exists to prevent.

Rule 2 was documented here before it was true. See `_unique_session_path`.

Usage:
    python save.py "what happened this session"
    python save.py --law "short-name" "the rule" --why "what it cost to learn it"
"""
import datetime
import os
import pathlib
import re
import string
import sys

ROOT = pathlib.Path(__file__).resolve().parent
LAWS = ROOT / "identity" / "laws"
MEMORY = ROOT / "memory"
HANDOFF = MEMORY / "handoff.md"
SESSIONS = MEMORY / "sessions"


def _console():
    """Make stdout able to carry the characters this tool prints.

    Python picks the encoding from the OS, and on a default Windows console that
    is still cp1252, which cannot encode a single emoji. The result is not a
    mangled character — it is UnicodeEncodeError, a traceback, and a first run
    that fails on the most common desktop OS while the README promises sixty
    seconds. Reported by an outside reviewer on D152; it had been true since the
    first commit, because it was only ever run on a UTF-8 terminal.

    The lesson is narrower than "support Windows": output encoding is part of
    the interface, and the machine you happen to develop on does not test it.
    """
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):     # pre-3.7, or an odd stream
            pass


def _die(msg):
    print(msg)
    return 2


def _day():
    try:
        text = (ROOT / "identity" / "identity.md").read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    m = re.search(r"^day_zero:\s*(\d{4}-\d{2}-\d{2})", text, re.M)
    if not m:
        return None
    return (datetime.date.today() - datetime.date.fromisoformat(m.group(1))).days


def _write_atomic(path, text):
    """Write via a temp file in the same directory, then replace.

    A plain write truncates the file first and fills it second. Crash in between
    and the old content is already gone — and here the file at risk is the
    handoff, which is the one thing carrying continuity forward. `os.replace` is
    atomic on both POSIX and Windows, so a reader sees either the old file or
    the new one, never a half-written one.
    """
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def save_law(name, rule, why):
    LAWS.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        return _die("🔴 that name has no letters or digits in it — give it a name "
                    "you could grep for in six months.")
    day = _day()
    path = LAWS / f"{datetime.date.today():%Y%m%d}-{slug}.md"
    if path.exists():
        print(f"🔴 {path.name} already exists — laws are not overwritten.")
        print("   Rename it, or edit that file deliberately.")
        return 1
    # Refuse, rather than rename. A law is something you meant; two of them with
    # the same name on the same day is a mistake worth stopping for. A session is
    # something that happened, and losing one to a name clash is data loss — so
    # the two cases get opposite treatment on purpose.
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


def _unique_session_path(now):
    """A path no existing session holds, created exclusively.

    The first version of this named sessions to the minute and then called
    write_text unconditionally — so two saves in the same minute silently
    destroyed the first record, while the handoff kept both summaries. The file
    claiming to be the raw evidence was the one being overwritten.

    Seconds make a clash unlikely; they do not make it impossible, and "unlikely"
    is not what append-only means. So the name is taken with O_EXCL — the
    filesystem decides who got there first, not a check-then-write that can lose
    a race.

    The suffix is a letter, not `-2`, so the names still sort chronologically:
    '-' sorts before '.', which would put a collision file ahead of the original
    and quietly make the wrong session look like the newest one.
    """
    SESSIONS.mkdir(parents=True, exist_ok=True)
    base = f"{now:%Y%m%d-%H%M%S}"
    for suffix in ("",) + tuple(string.ascii_lowercase):
        path = SESSIONS / f"{base}{suffix}.md"
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue
        os.close(fd)
        return path
    raise RuntimeError(f"27 sessions saved in the same second as {base}; "
                       "something is calling save.py in a loop.")


def save_session(summary):
    MEMORY.mkdir(parents=True, exist_ok=True)
    day = _day()
    now = datetime.datetime.now()
    tag = f"{now:%Y-%m-%d}" + (f" · day {day}" if day is not None else "")

    path = _unique_session_path(now)
    path.write_text(f"# {tag}\n\n{summary}\n", encoding="utf-8")

    old = HANDOFF.read_text(encoding="utf-8") if HANDOFF.exists() else ""
    _write_atomic(HANDOFF, f"## {tag}\n\n{summary}\n\n---\n\n{old}".rstrip() + "\n")

    print(f"  ✅ session → {path.relative_to(ROOT)}")
    print("  ✅ handoff updated (newest block on top)")
    print("\n  Next session: python boot.py")
    return 0


def main():
    _console()
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 2
    if a[0] == "--law":
        if "--why" not in a:
            return _die("🔴 A law without a reason is a rule nobody can re-evaluate "
                        "later.\n   Add --why \"what it cost you to learn this\".")
        i = a.index("--why")
        head = a[1:i]
        if len(head) < 2:
            return _die("🔴 usage: --law \"name\" \"the rule\" --why \"reason\"")
        if not " ".join(a[i + 1:]).strip():
            return _die("🔴 --why is empty. The reason is the part that makes the "
                        "law re-evaluable — it is not paperwork.")
        return save_law(head[0], " ".join(head[1:]), " ".join(a[i + 1:]))
    return save_session(" ".join(a))


if __name__ == "__main__":
    sys.exit(main())
