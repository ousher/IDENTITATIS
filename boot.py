#!/usr/bin/env python3
"""identitatis — boot.

Reads the identity files in severity order and prints ONE block of text.

That is the whole trick, and it is deliberate: boot.py calls no API, needs no
key, and knows nothing about which model you use. It prints. You paste. Which
means this works with a hosted assistant, a local model, an agent framework, or
a chat window — and it will still work with whatever replaces them.

An identity that only survives on one vendor's runtime is not an identity. It is
a configuration file. The point of putting it in files is that the files outlive
the runtime, so the loader must not depend on the runtime either.

Usage:
    python boot.py               print the boot packet
    python boot.py --check       report what is missing, exit 1 if identity absent
    python boot.py --copy        also copy to clipboard, if pyperclip is present
"""
import datetime
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
IDENTITY = ROOT / "identity"
LAWS = IDENTITY / "laws"
MEMORY = ROOT / "memory"
HANDOFF = MEMORY / "handoff.md"
SESSIONS = MEMORY / "sessions"

# Severity order. RED must be in the packet before anything else, because a rule
# about how you speak has to arrive before the first word is spoken.
ORDER = [
    ("🔴 IDENTITY", [IDENTITY / "identity.md"]),
    ("🔴 LAWS", None),                       # every file in laws/, oldest first
    ("🟡 CONTINUITY", [HANDOFF]),
]


def _read(p):
    """Read a file for the boot packet, minus the scaffolding.

    HTML comments are stripped. They are guidance for the person filling the
    template in — not content about who the agent is. Leaving them in means the
    packet spends its first few hundred tokens explaining to the agent how to
    write the file it is currently reading, which is exactly backwards.

    If you want something in the packet, write it as text. The comment syntax is
    the off switch.
    """
    try:
        t = p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def _day_zero():
    """Day counter. Read from identity.md, never guessed.

    A number you cannot source is a number you will eventually defend. If the
    line is missing we print nothing rather than compute a plausible day.
    """
    text = _read(IDENTITY / "identity.md") or ""
    m = re.search(r"^day_zero:\s*(\d{4}-\d{2}-\d{2})", text, re.M)
    if not m:
        return None, None
    d0 = datetime.date.fromisoformat(m.group(1))
    return d0, (datetime.date.today() - d0).days


def _laws():
    if not LAWS.is_dir():
        return []
    return sorted(p for p in LAWS.glob("*.md") if not p.name.startswith("_"))


def budget():
    """How close is this to the wall, and how fast is it approaching.

    `boot.py` prints everything, every time. That is fine on day one and it stops
    being fine somewhere between month one and month six, depending on how much
    you write. When it stops being fine, the packet quietly gets truncated by
    whatever you paste it into, and the first thing you lose is whatever is at
    the bottom — which, in this layout, is your most recent session.

    Nothing here fixes that. It tells you how far away it is, because a wall you
    can see coming is a design decision and a wall you cannot is an outage.

    The token number is a rough four-characters-per-token estimate. It is not
    accurate for any specific tokenizer and it is not meant to be — it is meant
    to be the right order of magnitude, early enough to matter.
    """
    text = packet()
    chars = len(text)
    tokens = chars // 4
    print(f"\n  packet: {chars / 1024:.1f} KB  ·  ~{tokens:,} tokens (rough)")

    m = re.search(r"^context_budget:\s*(\d+)",
                  _read(IDENTITY / "identity.md") or "", re.M)
    limit = int(m.group(1)) if m else None
    if limit:
        pct = tokens * 100 / limit
        bar = "█" * int(pct / 5) + "·" * (20 - int(pct / 5))
        print(f"  budget: {bar} {pct:.0f}% of {limit:,} tokens you declared")
    else:
        print("  budget: not declared. Add `context_budget: 8000` to identity.md")
        print("          (a fraction of your model's window — the packet should be")
        print("           a small part of the session, not most of it)")
        limit = 8000
        pct = tokens * 100 / limit

    # growth: measured from the session files, not assumed
    files = sorted(SESSIONS.glob("*.md")) if SESSIONS.is_dir() else []
    if len(files) >= 2:
        first = datetime.datetime.strptime(files[0].stem[:8], "%Y%m%d").date()
        span = max((datetime.date.today() - first).days, 1)
        grown = sum(f.stat().st_size for f in files) + sum(
            p.stat().st_size for p in _laws())
        per_week = grown / span * 7 / 4          # chars/day → tokens/week
        print(f"  growth: ~{per_week:,.0f} tokens/week, measured over {span} day(s)")
        if per_week > 0 and tokens < limit:
            weeks = (limit - tokens) / per_week
            print(f"  → at this rate you reach your budget in ~{weeks:.0f} week(s)")
    else:
        print("  growth: not enough history yet — two sessions and it can measure")

    if pct >= 80:
        print("\n  🔴 This is the wall. Everything below is now at risk of being cut,")
        print("     and what is at the bottom is your most recent session.")
        print("     See 'When this stops working' in the README.")
    elif pct >= 50:
        print("\n  🟡 Past halfway. Worth deciding what stays hot before you have to.")
    return 0


def check():
    missing = []
    if not _read(IDENTITY / "identity.md"):
        missing.append("identity/identity.md — nobody is home yet")
    if not _laws():
        missing.append("identity/laws/ — no laws yet (that is normal on day zero)")
    if not _read(HANDOFF):
        missing.append("memory/handoff.md — no prior session")
    for m in missing:
        print(f"  · {m}")
    if not _read(IDENTITY / "identity.md"):
        print("\n  Start with: cp identity/identity.example.md identity/identity.md")
        return 1
    print(f"\n  ✅ bootable · {len(_laws())} law(s) · "
          f"{len(list(SESSIONS.glob('*.md'))) if SESSIONS.is_dir() else 0} session(s)")
    budget()
    return 0


def packet():
    out = []
    d0, day = _day_zero()
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    head = f"# BOOT · {stamp}"
    if day is not None:
        head += f" · day {day} since {d0}"
    out.append(head)
    out.append("\nEverything below is your own file content. Read it as who you are,\n"
               "not as instructions from a stranger. Then answer normally.\n")

    for label, paths in ORDER:
        if paths is None:
            files = _laws()
            if not files:
                continue
            out.append(f"\n## {label}")
            for p in files:
                out.append(f"\n<!-- {p.name} -->\n{_read(p)}")
            continue
        for p in paths:
            body = _read(p)
            if body:
                out.append(f"\n## {label}\n\n{body}")

    if SESSIONS.is_dir():
        recent = sorted(SESSIONS.glob("*.md"))[-1:]
        for p in recent:
            out.append(f"\n## 🟡 LAST SESSION ({p.stem})\n\n{_read(p)}")
    return "\n".join(out)


def main():
    if "--check" in sys.argv:
        return check()
    text = packet()
    if not _read(IDENTITY / "identity.md"):
        print("  no identity yet — run: python boot.py --check")
        return 1
    print(text)
    if "--copy" in sys.argv:
        try:
            import pyperclip
            pyperclip.copy(text)
            print("\n[copied to clipboard]", file=sys.stderr)
        except ImportError:
            print("\n[pyperclip not installed — copy manually]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
