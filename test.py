#!/usr/bin/env python3
"""identitatis — tests.

    python test.py

No dependencies, no test framework. Every case runs against a throwaway copy in
a temp directory, never against your real identity — a test suite that writes
into `identity/` would corrupt the thing the repo exists to protect, and it
would do it on the machine of whoever trusted it enough to run the tests.

What is covered is not "the happy path". It is the specific claims this repo
makes about itself, because those are the ones that cost something when false:

  * sessions are append-only          → two saves in the same second
  * laws are not overwritten          → same law name twice in a day
  * a law needs a reason              → --law without --why, and with an empty one
  * it runs on a normal console       → forced cp1252 stdout, the D152 blocker
  * a missing identity says so        → no traceback, a sentence

The first and the fourth were both broken in the first public commit and both
were found by an outside reviewer, not by us. That is what this file is for.
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

SRC = pathlib.Path(__file__).resolve().parent
PASS, FAIL = [], []


def run(tmp, *args, encoding=None):
    env = dict(os.environ, PYTHONIOENCODING=encoding or "utf-8")
    return subprocess.run([sys.executable, *args], cwd=tmp, env=env,
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=60)


def fresh(with_identity=True):
    """A minimal working copy: the two scripts and, optionally, an identity."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="identitatis-test-"))
    for f in ("boot.py", "save.py"):
        shutil.copy(SRC / f, tmp / f)
    (tmp / "identity" / "laws").mkdir(parents=True)
    if with_identity:
        (tmp / "identity" / "identity.md").write_text(
            "name: Testy\nday_zero: 2026-01-01\ncontext_budget: 8000\n\n"
            "# Testy\n\nA test identity. Deleted the moment this file finishes.\n",
            encoding="utf-8")
    return tmp


def check(name, condition, detail=""):
    (PASS if condition else FAIL).append(name)
    mark = "  ok  " if condition else "  FAIL"
    print(f"{mark}  {name}")
    if not condition and detail:
        for line in str(detail).strip().splitlines()[:6]:
            print(f"          {line}")


# --------------------------------------------------------------------------- 1
def test_same_second_saves_do_not_overwrite():
    """The D152 release blocker.

    Old behaviour: session files were named to the minute and written
    unconditionally, so the second save destroyed the first record while the
    handoff kept both summaries — the file claiming to be the raw evidence was
    the one being lost. Two saves back to back land in the same second, which is
    strictly harder than the same minute.
    """
    tmp = fresh()
    a = run(tmp, "save.py", "first session")
    b = run(tmp, "save.py", "second session")
    files = sorted((tmp / "memory" / "sessions").glob("*.md"))
    check("two saves in the same second keep two session files",
          len(files) == 2, f"got {len(files)}: {[f.name for f in files]}\n"
                           f"{a.stdout}{a.stderr}{b.stdout}{b.stderr}")
    bodies = [f.read_text(encoding="utf-8") for f in files]
    check("neither session record was replaced by the other",
          any("first session" in t for t in bodies)
          and any("second session" in t for t in bodies), bodies)
    check("session files still sort oldest-first",
          files == sorted(files, key=lambda p: p.stat().st_mtime_ns),
          [f.name for f in files])
    hand = (tmp / "memory" / "handoff.md").read_text(encoding="utf-8")
    check("handoff has the newest block on top",
          hand.index("second session") < hand.index("first session"))
    shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- 2
def test_laws_refuse_to_overwrite():
    tmp = fresh()
    run(tmp, "save.py", "--law", "no-guessing", "Do not guess.",
        "--why", "It cost a day.")
    second = run(tmp, "save.py", "--law", "no-guessing", "Something else.",
                 "--why", "Different reason.")
    laws = list((tmp / "identity" / "laws").glob("*.md"))
    check("a second law with the same name is refused, not merged",
          second.returncode == 1 and len(laws) == 1, second.stdout)
    check("the original law text survived",
          "Do not guess." in laws[0].read_text(encoding="utf-8"))
    shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- 3
def test_law_requires_a_reason():
    tmp = fresh()
    a = run(tmp, "save.py", "--law", "n", "A rule with no reason.")
    check("--law without --why is refused", a.returncode == 2, a.stdout)
    b = run(tmp, "save.py", "--law", "n", "A rule.", "--why", "   ")
    check("--law with an empty --why is refused", b.returncode == 2, b.stdout)
    check("neither wrote a law file",
          not list((tmp / "identity" / "laws").glob("*.md")))
    shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- 4
def test_runs_on_a_legacy_console():
    """The second D152 blocker: cp1252 stdout, the Windows console default.

    Forced here on every platform on purpose. This bug is invisible on the
    machine most people develop on, which is exactly why it shipped.
    """
    tmp = fresh()
    run(tmp, "save.py", "a session")
    for args in (["boot.py"], ["boot.py", "--check"],
                 ["save.py", "another session"],
                 ["save.py", "--law", "x", "A rule.", "--why", "A reason."]):
        r = run(tmp, *args, encoding="cp1252")
        name = "python " + " ".join(args)
        check(f"{name} survives a cp1252 console",
              r.returncode in (0, 1) and "UnicodeEncodeError" not in r.stderr,
              r.stderr)
    shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- 5
def test_missing_identity_is_a_sentence_not_a_traceback():
    tmp = fresh(with_identity=False)
    for args in (["boot.py"], ["boot.py", "--check"], ["save.py", "a session"]):
        r = run(tmp, *args)
        check("python " + " ".join(args) + " without an identity does not crash",
              "Traceback" not in r.stderr, r.stderr)
    r = run(tmp, "boot.py", "--check")
    check("--check names identity.example.md",
          "identity.example.md" in r.stdout, r.stdout)
    shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- 6
def test_boot_packet_contains_the_files():
    tmp = fresh()
    run(tmp, "save.py", "--law", "measure-first", "Measure before you claim.",
        "--why", "Twice in one hour a config predicted the wrong answer.")
    run(tmp, "save.py", "the session that happened")
    r = run(tmp, "boot.py")
    for needle in ("Testy", "Measure before you claim.",
                   "Twice in one hour", "the session that happened"):
        check(f"boot packet carries {needle[:34]!r}", needle in r.stdout)
    check("boot packet does not leak template HTML comments",
          "<!--" not in r.stdout.replace("<!-- 20", "").replace("<!-- _", ""))
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    print()
    for fn in (test_same_second_saves_do_not_overwrite,
               test_laws_refuse_to_overwrite,
               test_law_requires_a_reason,
               test_runs_on_a_legacy_console,
               test_missing_identity_is_a_sentence_not_a_traceback,
               test_boot_packet_contains_the_files):
        print(f"\n{fn.__name__}")
        fn()
    print(f"\n  {len(PASS)} passed · {len(FAIL)} failed\n")
    sys.exit(1 if FAIL else 0)
