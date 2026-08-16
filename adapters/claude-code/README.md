# Claude Code adapter

Runs `boot.py` automatically when a session starts, so the identity is in
context before the first answer instead of after you remember to load it.

This uses Claude Code's own documented hooks. There is nothing clever here and
nothing specific to my setup — it is ten lines of configuration.

## Wire it

Copy `settings.example.json` into your project as `.claude/settings.json`
(or merge the `hooks` block into the one you already have), and fix the path:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python /absolute/path/to/identitatis/boot.py"
          }
        ]
      }
    ]
  }
}
```

Whatever `boot.py` prints is injected into the session. That is the whole
adapter.

## Ending a session

There is no automatic hook for this on purpose.

You could fire `save.py` on session end and have it write something generic. It
would run every time, it would always succeed, and the handoff would slowly fill
with sentences nobody wrote and nobody reads — which is worse than an empty
file, because an empty file is honest about being empty.

So: run it yourself, in your own words.

```bash
python save.py "what actually happened, and what you would want to know tomorrow"
```

If you want a prompt rather than automation, add this to your project
instructions:

> At the end of a session, before we finish, remind me to run `save.py` and
> offer a two-sentence summary I can edit.

## Check it worked

Start a session and ask it who it is. If it answers from `identity.md` without
being told, the hook fired.

If it does not:

```bash
python boot.py --check          # is there an identity to load at all?
python boot.py | head -5        # does it print?
```

Then check the path in `settings.json` is absolute. Relative paths resolve
against the working directory, which is not always what you expect.
