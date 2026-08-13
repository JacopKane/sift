# Sift

**Disk cleanup that asks instead of guessing.**

You tell it what you need. It works out what it can, asks about what it can't, and shows you the whole picture before anything moves.

> **Status:** in development. The interface below is the v1 target — see [Roadmap](#roadmap).

---

## The problem

You're out of space. Your disk visualizer draws a beautiful map:

```
41.2 GB   ~/Library/Containers/com.docker.docker/.../Docker.raw
12.4 GB   ~/Sites/client-app/node_modules
12.1 GB   ~/Archive/clients-2021
```

Now what?

- **It answers the wrong question.** You learn *where* your space went, never *which of these is safe to delete*.
- **Size and disposability are unrelated.** The last two are nearly the same size — one is `npm install` away from full restoration, the other might be the only copy.
- **And the deciding fact isn't on the disk.** Whether `clients-2021` still matters was never written anywhere. No scanner recovers it, however thorough.

That last point is the whole design. **The missing information is in your head, so the tool has to ask.**

---

## How it works

1. **You say what you want.** *"Free 80 GB, but I'm mid-sprint on the Rust project."*
2. **It surveys while you type.** The walk takes seconds, so by the time you've finished the sentence it already knows your disk.
3. **It resolves what it can.** Known caches and build artifacts are settled instantly, with no model involved.
4. **It asks about what it can't.** Only where it's genuinely uncertain and the stakes are real — never about things a filename already answers.
5. **You review the map.** Everything it proposes, coloured by what you can get back, visible at once.
6. **You approve.** Items move to quarantine. `sift undo` puts them back.

---

## Design decisions

**The conversation is the product — and every question has to be earned.**
An agent that asks what it could have worked out is ceremony, and worse than silence. Questions are gated on three conditions at once: genuinely uncertain, large enough to matter, and not obviously regenerable. A 200 MB mystery folder gets marked amber; a 40 GB one gets asked about.

**The map is the final review, not the exploration surface.**
Other tools open with the chart and leave you to interpret it. Sift earns the chart: by the time you see it, every arc has a verdict and a reason. It's the last look before you commit, not a puzzle to solve.

**Regenerability is the unit, not size.**
Every proposal carries what you need in order to decide:

```
47 node_modules directories      31.2 GB  🟢 ↺  npm install         ~4 min
Xcode DerivedData                18.7 GB  🟢 ↺  rebuilds on open    ~90 sec
~/Archive/clients-2021            8.1 GB  🔴 ✕  cannot be restored
```

Verdict is never carried by colour alone — each level has its own glyph, so the distinction survives colour blindness and greyscale.

**It reasons from metadata, never from your files.**
Extensions, locations, sibling markers, access times, naming patterns. A `Cargo.toml` beside `target/` settles it; 95% `.o` files settles it; two years untouched is a real signal. **No file contents are ever read or sent anywhere** — when metadata runs out, it asks you rather than opening the file.

**Nothing is ever deleted.**
Reclaiming *moves* paths into quarantine alongside a manifest of where each came from. There is no code path in this repo that deletes a file. Emptying quarantine is a separate act you perform.

**Permission failures are a designed state.**
Default scan roots need no macOS permission at all, so Sift is useful seconds after launch. Blocked folders appear as cards with a grant button, never as stack traces. Full Disk Access is an upgrade, not a prerequisite.

---

## The review screen

```
     🟢 ↺ regenerable    🟡 ? worth a look    🔴 ✕ irreplaceable

  ┌────────────────────────────┬─────────────────────────┐
  │         ╭───────╮          │  Plan · 84.3 GB         │
  │      ╭──┤ 🟢🟢🟡├──╮       │  ┌───────────────────┐  │
  │      │  ╰───────╯  │       │  │ ◉ 47 node_modules │  │
  │      │   🔴   🟢   │       │  │   31.2 GB    🟢 ↺ │  │
  │      ╰─────────────╯       │  │   ↩ npm i   ~4min │  │
  │                            │  └───────────────────┘  │
  │   ‹ Home / Library         │  ┌───────────────────┐  │
  │     tab to walk arcs       │  │ ○ DerivedData     │  │
  ├────────────────────────────┴─────────────────────────┤
  │  reclaimable 84.3 GB · scanned 412 GB · 3 skipped 🔒 │
  └──────────────────────────────────────────────────────┘
```

The chart is not the only way to read this. Every arc is reachable by keyboard, and the same data is available as a plain table for screen readers — the visualization is an enhancement, never the sole channel.

---

## Where the AI is — and where it deliberately isn't

Each level only ever sees what the level above couldn't resolve.

| Level | What | Cost |
|---|---|---|
| Walk the tree, sizes, timestamps | `os.scandir` | free |
| **Catalog** — ~40 known paths: caches, build artifacts, Docker, Trash | static `catalog.yaml` | free, instant |
| **Classify** — unresolved directories, from metadata alone | one batched call | small |
| **Ask** — genuine uncertainty, high stakes only | a few turns | rare by design |
| Aggregate, order, total | plain Python | free |

Two optimizations do most of the work: **directories are classified, not files** — you ask about the ~50 that didn't resolve, not the 47,000 beneath them — and the catalog settles the majority of reclaimable bytes before a model is ever invoked.

---

## Architecture

```
   you ──▶ chat
            │
            ▼
     ┌──────────────┐
     │    survey    │   walk + catalog — starts while you type
     └──────┬───────┘
            ▼
     ┌──────────────┐
     │   classify   │   metadata only, one batched call
     └──────┬───────┘
            ▼
       ⏸  ask you      only when uncertain and it matters
            │
            ▼
     ┌──────────────┐
     │     plan     │   aggregate by rule, order by risk
     └──────┬───────┘
            ▼
       ⏸  review      the map, coloured, whole plan at once
            │
            ▼
     ┌──────────────┐
     │  quarantine  │   move + manifest + undo
     └──────────────┘
```

- Two pauses, both genuine: one for questions, one for approval. State survives both.
- `scanner/` is a pure library with no web or AI imports, so it stays portable to a CLI or native shell.
- The model provider is set by environment variable — Gemini, Claude, or GPT, same graph.

---

## MVP scope

**In**

- Filesystem survey, reported as it walks
- Static catalog of known paths and verdicts
- Metadata classification of unresolved directories, batched into one call
- Conversational clarification when — and only when — uncertainty is real
- Free-form prompts against the survey (*"get rid of the large videos"*)
- Review map, verdict-coloured, keyboard navigable, with a table equivalent
- Per-item approval, reclaim to quarantine, `undo`
- Two entry points: local survey, and drag-a-folder in the browser

**Out, and why**

| Deferred | Reasoning |
|---|---|
| Reading file contents | Asking you is cheaper, faster, and keeps the privacy promise absolute |
| Content-hash duplicate detection | Real work, and an orthogonal thesis — regenerability first |
| Background / scheduled scans | Turns a tool you open into a daemon you maintain |
| Windows and Linux | The catalog is the moat and it's platform-specific |
| Multi-volume, network drives | Long tail of edge cases, small share of the problem |
| Native app shell | Correct eventually — but it's packaging, not product |
| Accounts, sync, teams | A local disk tool needs no server-side identity |

v1 does one thing completely — understand what your files mean to *you*, and act on it — rather than six things partially.

---

## Running it

**Analyze a folder — nothing to install.**
Open the hosted build and drag a directory onto the page. The browser walks the tree locally and sends only a manifest of names and sizes.

**Analyze your whole machine.**

```bash
uvx --from git+https://github.com/<user>/sift sift
```

One command starts the server, opens your browser, and begins surveying immediately.

**Choosing a model.** Set two environment variables; nothing else changes.

```bash
SIFT_PROVIDER=google_genai   # or anthropic, openai
SIFT_MODEL=gemini-2.0-flash
```

---

## Development

Test-first, without exception. Behaviour is specified in Gherkin before it is implemented — see [CLAUDE.md](CLAUDE.md) for the full rules.

```bash
uv sync
pre-commit install && pre-commit install --hook-type pre-push

pytest                 # full suite
pytest -m "not slow"   # fast suite, matches the pre-commit hook
```

- Every commit runs formatting, linting, type checks, and the fast suite.
- Every push runs the full suite, which calls the real model — nothing is mocked, so a passing
  suite means the thing actually works.
- Model assertions are about properties, never exact strings, because real responses vary.

---

## Roadmap

- **Native shell.** A Tauri wrapper gets real drag-and-drop with absolute paths, an app icon, and small signed binaries.
- **Learned catalog.** Your answers — *"this is safe"*, *"never touch this"* — feed back in, so it asks you the same question only once.
- **Duplicate and version detection** by content hash, as a second lens on the same survey.
- **Linux and Windows catalogs.**

---

## License

All rights reserved. This repository is public for reading; it is not open source and no license to use, modify, or distribute is granted.
