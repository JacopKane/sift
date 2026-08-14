# Sift

**Reclaims disk space and knows what not to touch.**

---

## Run it

```bash
uvx --refresh --from git+https://github.com/JacopKane/sift sift
```

A window opens asking which folder — drop one in, or pick Downloads, Desktop or the whole disk. No config screen.

`--refresh` skips `uvx`'s build cache. Without it a second run can silently start
an older copy, which looks exactly like the new one until it behaves differently.

**A key is optional, and worth having.** The rules settle most of a disk without
one. The model names what's left — the folders no rule recognises, which is where
the interesting decisions are. Without a key those go unjudged and the app says so.

```bash
export OPENAI_API_KEY=sk-...     # or GOOGLE_API_KEY, or ANTHROPIC_API_KEY
export SIFT_PROVIDER=openai      # google_genai · openai · anthropic
```

Or put the same lines in a `.env` file **in the directory you run from** — that's
where it looks. Cloned the repo? `cp .env.example .env`.

Gemini's free tier is enough — set `SIFT_REQUESTS_PER_MINUTE=12` with one.

Sift prints which of the two it's running with on the line after the URL, before
you touch anything.

Skip the question by naming a folder: `sift ~/Projects` · Whole disk: `sift /`

---

## What it does

- **Takes plain requests.** *"Delete the screenshots on my desktop"* → those files, nothing else. This is the main way in.
- **Finds what's big.** Walks a folder or the whole disk, streaming results as it counts.
- **Says what's safe.** Every item gets a verdict: rebuilds itself, needs a decision, or can't be replaced.
- **Tells you how long it's been.** Every row says when it was last opened. A 4 GB folder untouched for three years is a different decision from the same folder opened this morning.
- **Tells you how to get it back.** `npm install`. `cargo build`. Or plainly: cannot be restored.
- **Finds duplicates.** Same bytes, different names — one of them is free to take.
- **Never deletes.** Reclaiming moves things to your Trash. `undo` puts them back.

---

## Why it's different

Disk tools show you *where* your space went. None of them tell you *what's safe to delete*.

A 12 GB `node_modules` and 12 GB of holiday photos look identical on a size chart. One is `npm install` away from coming back. The other is gone forever. **Sift sorts by what you can get back.**

---

## The verdicts

| | | |
|---|---|---|
| ↺ | **rebuilds itself** | a command brings it back — deleting costs only time |
| ? | **needs a decision** | mixed, or genuinely unclear — look before you act |
| ✕ | **can't be replaced** | no command reproduces this — never proposed, always yours to take |

Colour is never the only signal — each verdict has its own glyph and its own words.

---

## Safety

- **Nothing is locked.** There is no protected list and nothing you can be refused. It's your disk.
- **Nothing is deleted either.** Reclaiming *moves* to the Trash your desktop already has, behind a countdown you can cancel. Emptying it is yours, in the app you already trust for it.
- **You always know what you picked.** The verdict travels with a file — into the basket, onto the receipt, into the manifest. The basket says how many of its contents can't be replaced before you empty it.
- **Undo is ours, not the Finder's.** A manifest beside the Trash puts a whole basket back at once. Empty the Trash first and undo says which ones it couldn't reach rather than claiming success.
- **It proposes, you choose.** Sift never *proposes* deleting something irreplaceable; it puts it under "can't be replaced" and leaves it there. Taking it is one click, same as anything else.
- **Your files stay put.** Names, sizes and extensions go to the model. File contents never leave your machine.

---

## Cost

- The rules settle most of a disk for **zero tokens**.
- A model is asked only about what the rules can't name — one batched call.
- One free-form question costs 3–6 calls. On a free Gemini key set `SIFT_REQUESTS_PER_MINUTE=12`.

---

## Switching models

Two lines in `.env`. Gemini, OpenAI and Claude are the same code path.

```bash
SIFT_PROVIDER=openai        # or google_genai, anthropic
SIFT_MODEL=gpt-5.4-mini
```

Worth knowing: two frontier models disagreed about whether it's safe to delete a `src/` directory. That's why source is settled by a rule and never put to a model — the verdict has to be stable even when the model isn't.

---

## Developing

```bash
uv sync && uv run sift
```

```bash
.venv/bin/pytest -m "not slow"   # 70 scenarios, ~4s, no key needed
.venv/bin/pytest -m slow         # 22 more, real model, needs the key from .env
```

Test-first in Gherkin, nothing mocked — not the filesystem, not the model. See [CLAUDE.md](CLAUDE.md).

Rebuild the frontend after changing it: `cd web && npm run build`

---

## If something goes wrong

- **Port in use.** Sift moves to the next free port and prints where it went. Pass `--port` and it will refuse to move instead — you asked for that one.
- **It behaves like an older version.** That's the `uvx` cache. Add `--refresh`.
- **"The model could not be reached."** The survey is still there and still usable; only the unnamed folders went unjudged. Check the key in `.env`, then survey again.
- **macOS blocks a folder.** Only a real permission error says so, and it names the setting: System Settings > Privacy & Security > Full Disk Access, for the terminal you launched from.
- **Nothing seems to delete.** It moves to your Trash, and the list updates to match. If a row is still there, it did not move — the status line will say what refused.

---

## Not built yet

- Reading file contents — it judges by name, size, extension, age and what's inside a folder, never by opening a file
- Recognising that an archive is a backup of something you still have
- Windows and Linux catalogs — the scanner is portable, only the path rules are macOS
- A native app shell

---

## License

MIT. Use it, change it, ship it — just keep the copyright line so credit travels with the code.
