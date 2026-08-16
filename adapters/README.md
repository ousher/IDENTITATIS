# Adapters

An adapter wires `boot.py` and `save.py` into whatever you actually work in, so
you stop doing it by hand.

**The rule that keeps this honest:** delete this entire folder and the core still
works. If an adapter ever becomes required, the claim on the front page — that
identity lives in files, not in a runtime — stops being true, and the first
person to notice will be right.

So adapters are examples, never dependencies. There is exactly one here on
purpose: enough to show the shape, not enough to look like this is a tool for
one vendor.

## The manual path is a real path

```bash
python boot.py            # prints
# paste into your model
python save.py "..."      # at the end
```

That is not a fallback for people without an adapter. It is the reference
behaviour, and every adapter is just automation on top of it. If an adapter does
something the manual path cannot, that adapter is doing too much.

## Writing your own

Two hooks, both optional:

| when | run | why |
|---|---|---|
| session starts | `python boot.py` | the identity has to arrive before the first answer, not after |
| session ends | `python save.py "..."` | the half everyone skips, which is why most agent memory only grows and never gets read |

If your tool has no session-start hook, run `boot.py --copy` and paste. If it
has no session-end hook, that is the one to build first — writing down is worth
more than loading, because you cannot load what nobody wrote.

## Available

- [`claude-code/`](claude-code/) — session-start hook via `settings.json`
