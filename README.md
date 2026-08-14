# Sift

**Reclaims disk space and knows what not to touch.**

---

## Run it

```bash
uvx --from git+https://github.com/JacopKane/sift sift
```

That's it. It starts, opens your browser, and begins surveying. No config screen, no empty state.

Want the model to judge what the rules can't name? Add a key:

```bash
cp .env.example .env      # then paste one key: Gemini, OpenAI, or Claude
```

Survey a different folder: `sift ~/Projects` · Whole disk: `sift /`

---

## What it does

- **Finds what's big.** Walks a folder or the whole disk, streaming results as it counts.
- **Says what's safe.** Every item gets a verdict: rebuilds itself, needs a decision, or can't be replaced.
- **Tells you how to get it back.** `npm install`. `cargo build`. Or plainly: cannot be restored.
- **Takes plain requests.** *"Delete the app installers I already installed"* → the two `.dmg` files, nothing else.
- **Never deletes.** Reclaiming moves things to quarantine. `undo` puts them back.

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
| ✕ | **can't be replaced** | no command reproduces this |

Colour is never the only signal — each verdict has its own glyph and its own words.

---

## Safety

- **Nothing is deleted.** Reclaiming *moves* to quarantine with a manifest. Emptying it is your separate, deliberate act.
- **Protected by kind, not by location.** `~/.ssh`, `~/.gnupg`, `~/Library/Keychains`, and any `src/` beside a manifest. Your Desktop is where you work, not a vault — it needs a decision, not a lock.
- **Warnings, not locks.** You can override any of it — it's your disk. The override is recorded on the receipt.
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

Worth knowing: two frontier models disagreed about whether it's safe to delete a `src/` directory. That's why source is protected by a rule and never put to a model.

---

## Developing

```bash
uv sync && uv run sift
```

```bash
.venv/bin/pytest -m "not slow"   # 70 scenarios, ~4s, no network
.venv/bin/pytest -m slow         # calls the real model
```

Test-first in Gherkin, nothing mocked — not the filesystem, not the model. See [CLAUDE.md](CLAUDE.md).

Rebuild the frontend after changing it: `cd web && npm run build`

---

## Not built yet

- Reading file contents — it asks you instead
- Windows and Linux catalogs
- A native app shell

---

## License

MIT. Use it, change it, ship it — just keep the copyright line so credit travels with the code.
