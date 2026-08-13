# Sift

**A disk analyzer that knows what's safe to delete.**

Every disk tool shows you where your space went. Sift tells you what to do about it.

> **Status:** in development. The interface below is the v1 target — see [Roadmap](#roadmap).

---

## The problem

You're out of space. Your disk visualizer draws a beautiful map:

```
41.2 GB   ~/Library/Containers/com.docker.docker/.../Docker.raw
12.4 GB   ~/Sites/client-app/node_modules
12.1 GB   ~/Pictures/2019-portugal
```

Now what?

- **It answers the wrong question.** You learn *where* your space went, never *which of these is safe to delete*.
- **Size and disposability are unrelated.** The last two are the same size — one is `npm install` away from full restoration, the other is irreplaceable.
- **So you google paths one at a time.** Forty minutes later you've reclaimed 3 GB and still don't know about that Docker file.

**Sift sorts your disk by what you can get back.**

---

## What a size-based tool structurally can't do

- **Know what something is.** It sees bytes and a path string, so it can't tell a rebuildable cache from the only copy of a client project. That judgement is semantic — which is the reason there's a model in here at all.
- **Show patterns instead of paths.** Your 47 `node_modules` folders total 31 GB, but a tree view scatters them into 47 slivers you'll never connect. Sift shows one line.
- **Take a goal.** There's no way to say *"free 80 GB, but I'm mid-sprint on the Rust project."* Sift starts there and works backwards.

---

## Design decisions

**Regenerability is the unit, not size.**
Every proposal carries what you actually need in order to decide:

```
47 node_modules directories      31.2 GB  🟢   npm install         ~4 min
Xcode DerivedData                18.7 GB  🟢   rebuilds on open    ~90 sec
~/Archive/clients-2021            8.1 GB  🔴   cannot be restored
```

Red items are never proposed for deletion — they're shown so you can see Sift understood your disk too.

**The visualization *is* the AI output.**
The sunburst is coloured by verdict instead of by position, so one glance tells you which fraction of your disk is disposable. It isn't decoration sitting beside the intelligence; it's the intelligence, rendered.

```
     🟢 regenerable   🟡 worth a look   🔴 irreplaceable

  ┌────────────────────────────┬─────────────────────────┐
  │         ╭───────╮          │  ⌕ free 80 GB, but I'm  │
  │      ╭──┤ 🟢🟢🟡├──╮       │    mid-sprint on the    │
  │      │  ╰───────╯  │       │    Rust project         │
  │      │   🔴   🟢   │       │  ┌───────────────────┐  │
  │      ╰─────────────╯       │  │ ◉ 47 node_modules │  │
  │                            │  │   31.2 GB      🟢 │  │
  │   ‹ Home / Library         │  │   ↩ npm i   ~4min │  │
  │                            │  │   [ Reclaim ]     │  │
  ├────────────────────────────┴─────────────────────────┤
  │  reclaimable 84.3 GB  ·  scanned 412 GB              │
  └──────────────────────────────────────────────────────┘
```

**Results stream in.**
Arcs grow as the scanner walks and plan items appear as they're classified. A scan is slow enough that a spinner would be a lie about what's happening.

**Approve before act — and nothing is ever deleted.**
Sift proposes, you approve item by item. Reclaiming *moves* paths into quarantine with a manifest, and `sift undo` puts them back. No code path in this repo deletes a file.

**Permission failures are a designed state.**
Default scan roots need no macOS permission at all, so Sift is useful seconds after launch. Blocked folders show up as cards with a grant button, never as stack traces. Full Disk Access is an upgrade, not a prerequisite.

---

## Where the AI is — and where it deliberately isn't

Most of Sift is not AI, on purpose. A model in the wrong layer is slower, costlier, and less accurate than the boring alternative.

| Layer | How | Why |
|---|---|---|
| Walk the tree, sizes, timestamps | `os.scandir` | A model is strictly worse at traversal and arithmetic |
| ~40 known paths — caches, build artifacts, Docker, Trash | Static `catalog.yaml` | Deterministic, instant, free, and covers most reclaimable bytes |
| **Classify what the catalog can't name** | **One batched LLM call** | Genuinely semantic: build artifact, cache, or the only copy of something? |
| **Parse goal and constraints** | **LLM** | *"nothing related to the Rust project"* has no regex |
| Aggregate, order, total | Plain Python | Arithmetic |

The model never sees your file tree — just a few dozen unnamed directories described by their signals. One call, a few kilobytes, no file contents.

---

## MVP scope

**In**

- Filesystem scan, streamed to the UI as it walks
- Static catalog of known paths and verdicts
- LLM classification of unknown directories, batched into one call
- Goal and constraint parsing
- Verdict-coloured sunburst
- Plan aggregated by pattern rather than path
- Per-item approval, reclaim to quarantine, `undo`
- Two entry points: local scan, and drag-a-folder in the browser

**Out, and why**

| Deferred | Reasoning |
|---|---|
| Content-hash duplicate detection | Real work, and an orthogonal thesis — regenerability first |
| Background / scheduled scans | Turns a tool you open into a daemon you maintain |
| Windows and Linux | The catalog is the moat and it's platform-specific |
| Multi-volume, network drives | Long tail of edge cases, small share of the problem |
| Cloud storage | Different permissions, different failures, different product |
| Native app shell | Correct eventually — but it's packaging, not product |
| Accounts, sync, teams | A local disk tool needs no server-side identity |

v1 does one thing completely — tell you what's safe to delete and let you act on it — rather than six things partially.

---

## Architecture

```
                        ┌──────────────────────────────┐
  local scan  ─────────▶│  scanner/   os.scandir       │
  (real paths)          │            reports as it goes│
                        └──────────────┬───────────────┘
                                       │  ScanNode
  dragged folder ──────────────────────┤
  (names + sizes only)                 ▼
                        ┌──────────────────────────────┐
                        │  catalog/   catalog.yaml     │  most resolved, 0 cost
                        └──────────────┬───────────────┘
                                       │  unknowns only
                                       ▼
                        ┌──────────────────────────────┐
                        │  classify/  one batched call │
                        └──────────────┬───────────────┘
                                       │  Verdict
                                       ▼
                        ┌──────────────────────────────┐
                        │  plan/      aggregate, order │
                        └──────────────┬───────────────┘
                                       │  SSE
                                       ▼
                        ┌──────────────────────────────┐
                        │  web/       sunburst + plan  │
                        └──────────────┬───────────────┘
                                       │  approve
                                       ▼
                        ┌──────────────────────────────┐
                        │  quarantine/ move + manifest │
                        └──────────────────────────────┘
```

- Both entry points converge on the same classification pipeline.
- `scanner/` is a pure library with no web or AI imports, so it stays portable to a CLI or native shell.

---

## Running it

**Analyze a folder — nothing to install.**
Open the hosted build and drag a directory onto the page. The browser walks the tree locally and sends only a manifest of names and sizes; no file contents leave your machine.

**Analyze your whole machine.**

```bash
uvx --from git+https://github.com/<user>/sift sift
```

One command starts the server, opens your browser, and begins scanning the safe roots immediately — no config, no empty state.

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
- Every push runs the full suite including filesystem scenarios and end-to-end tests.
- No test makes a network call — the model layer has a deterministic fake and recorded fixtures.

---

## Roadmap

- **Native shell.** A Tauri wrapper gets real drag-and-drop with absolute paths, an app icon, and small signed binaries.
- **Learned catalog.** Your corrections — *"this is safe"*, *"never touch this"* — feed back in, so it improves with use.
- **Duplicate and version detection** by content hash, as a second lens on the same scan.
- **Linux and Windows catalogs.**

---

## License

All rights reserved. This repository is public for reading; it is not open source and no license to use, modify, or distribute is granted.
