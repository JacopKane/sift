# Sift

**A disk analyzer that knows what's safe to delete.**

Every disk tool shows you where your space went. Sift tells you what to do about it.

> **Status:** in active development. The interface described below is the target for v1;
> see [Roadmap](#roadmap) for what's built.

---

## The problem

You're out of space. You open a disk visualizer and it draws you a beautiful map — a 41 GB
blob at `~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw`, a 12 GB folder
called `node_modules`, a 12 GB folder called `2019-portugal`.

Now what?

The map answered *where did my space go*. It has no opinion on the only question you actually
came with: **which of these can I delete without regretting it?** So you start googling paths
one at a time. Forty minutes later you've reclaimed 3 GB, lost an afternoon, and you're still
not sure whether that Docker file was important.

The gap is that **size and disposability are unrelated**, and every existing tool measures
only size. `node_modules` and the Portugal photos are the same 12 GB arc on the chart. One is
`npm install` away from complete restoration. The other is irreplaceable.

**Sift sorts your disk by what you can get back.**

---

## Three things a size-based tool structurally cannot do

**It can't tell you what something is.** A visualizer sees bytes and a path string. It cannot
know that `~/Library/Developer/Xcode/DerivedData` rebuilds itself, that `Docker.raw` will be
re-pulled on next run, or that the unlabeled 8 GB directory in your home folder is the only
copy of a client project. That judgement is semantic, and it's the reason there's a language
model in here at all.

**It can't show you patterns, only paths.** You have 47 `node_modules` directories scattered
across `~/Sites`, `~/Projects`, and `~/dev`, totalling 31 GB. A tree-shaped visualization
renders them as 47 unrelated slivers in 47 different places, and you will never notice.
Sift's output is *pattern-shaped*: one line, 31.2 GB, restore with `npm install`.

**It can't take a goal.** There's no way to say *"free 80 GB, but I'm mid-sprint on the Rust
project — don't touch anything related to it."* You just wander the rings and hope. Sift
starts from the goal and works backwards.

---

## Design decisions

These are the choices that define the product. Each one is a deliberate trade.

### Regenerability is the unit, not size

Every item Sift proposes carries the thing you actually need in order to decide:

```
47 node_modules directories              31.2 GB   🟢
  restore:  npm install                  ~4 min
  found in: ~/Sites, ~/Projects, ~/dev

Xcode DerivedData                        18.7 GB   🟢
  restore:  rebuild on next open         ~90 sec

~/Archive/clients-2021                    8.1 GB   🔴
  restore:  cannot be restored
```

Not "this is big." **"This is big, here is exactly how you get it back, and here is what it
costs you."** A decision you can make in two seconds instead of two minutes of searching.

Red items are never proposed for reclamation. They appear so you understand your disk, and
so you can see that Sift understood it too.

### The visualization *is* the AI output

Sift draws the familiar sunburst, but colours it by verdict rather than by position:

```
        🟢 regenerable — one command, safe
        🟡 probably safe — worth a look
        🔴 irreplaceable — never touched

  ┌────────────────────────────┬─────────────────────────┐
  │                            │  ⌕ free 80 GB, but I'm  │
  │         ╭───────╮          │    mid-sprint on the    │
  │      ╭──┤ 🟢🟢🟡├──╮       │    Rust project         │
  │      │  ╰───────╯  │       │  ┌───────────────────┐  │
  │      │   🔴   🟢   │       │  │ ◉ 47 node_modules │  │
  │      ╰─────────────╯       │  │   31.2 GB      🟢 │  │
  │                            │  │   ↩ npm i   ~4min │  │
  │   ‹ Home / Library         │  │   [ Reclaim ]     │  │
  │                            │  └───────────────────┘  │
  │                            │  ┌───────────────────┐  │
  │                            │  │ ○ DerivedData     │  │
  ├────────────────────────────┴─────────────────────────┤
  │  reclaimable 84.3 GB  ·  scanned 412 GB              │
  └──────────────────────────────────────────────────────┘
```

One glance tells you which fraction of your disk is disposable. The chart isn't decoration
sitting next to the intelligence — the chart is the intelligence, rendered. This is the single
view no existing tool can show you.

### Results stream; nothing blocks

Arcs grow into the sunburst as the scanner walks, and plan items appear as they're classified.
A disk scan is slow enough that a spinner would be a lie about what's happening, and progressive
results mean you can start reading your disk two seconds in rather than ninety seconds in.

### Approve before act, and nothing is ever deleted

Sift proposes. You approve, item by item. There is **no code path that deletes a file.**

Reclaiming moves paths into a quarantine directory alongside a manifest recording where each
one came from. `sift undo` puts everything back. Emptying quarantine is a separate, explicit
act that you perform.

The product handles irreversible operations on data people cannot afford to lose. An
undo that always works is worth more than any feature on the roadmap, and it's why the
architecture is built around moves rather than deletes.

### Permission failures are a designed state, not an error

macOS gates `~/Desktop`, `~/Documents`, and `~/Downloads` behind consent prompts. Sift defaults
to scan roots that need no permission at all — caches, build artifacts, package managers, which
is where the reclaimable space overwhelmingly lives — so it is useful within seconds of launch
and prompts you for nothing.

When a directory *is* blocked, it appears in the plan as a first-class card, not a stack trace:

```
🔒  Downloads — not scanned
    macOS is blocking access to this folder.
    [ Grant access ]
```

Full Disk Access is an optional upgrade. It is never a prerequisite.

---

## Where the AI is — and where it deliberately isn't

Most of Sift is not AI, on purpose. A language model in the wrong layer is slower, costlier,
and less accurate than the boring alternative.

| Layer | Implementation | Why |
|---|---|---|
| Walking the tree, sizes, timestamps | `os.scandir`, threaded | A model would be strictly worse at arithmetic and traversal |
| ~40 known paths (DerivedData, npm/pip/cargo/brew caches, Docker, iOS backups, Trash) | Static catalog, `catalog.yaml` | Deterministic, instant, free, and covers the large majority of reclaimable bytes |
| **Classifying what the catalog can't name** | **One batched LLM call** | Genuinely semantic: given a path, size, extension histogram, and sample filenames — is this a build artifact, a cache, or the only copy of something? |
| **Parsing goal and constraints** | **LLM** | *"don't touch anything related to the Rust project"* has no regex |
| Aggregation, ordering, totals | Plain Python | Arithmetic |

The model never sees your file tree. It sees a few dozen unnamed directories, described by
their signals, and returns verdicts. One call, a few kilobytes, no file contents.

---

## MVP scope

The v1 boundary, and the reasoning behind it.

**In**

- Threaded filesystem scan, streamed to the UI
- Static catalog of known paths and their verdicts
- LLM classification of unknown directories, batched into a single call
- Goal and constraint parsing
- Verdict-coloured sunburst
- Aggregated plan grouped by pattern rather than path
- Per-item approval, reclaim to quarantine, `undo`
- Two entry points: local scan, and drag-a-folder in the browser

**Out, and why**

| Deferred | Reasoning |
|---|---|
| Content-hash duplicate detection | Substantial work, and it's an orthogonal product. Regenerability is the thesis; duplicates are a different one |
| Background / scheduled scans | Turns a tool you open into a daemon you maintain. Needs a real trust record first |
| Windows and Linux | The catalog is the moat and it's platform-specific. One platform, done properly |
| Multi-volume and network drives | Long tail of edge cases, small share of the actual problem |
| Cloud storage analysis | Different permission model, different failure modes, different product |
| Native app shell | Correct eventually (see Roadmap) — but it's packaging, not product |
| Accounts, sync, teams | A local disk tool needs no server-side identity |

The through-line: v1 does one thing — *tell you what's safe to delete and let you act on it* —
and does it completely, rather than doing six things partially.

---

## Architecture

```
                        ┌──────────────────────────────┐
  local scan  ─────────▶│  scanner/   os.scandir       │
  (real paths)          │             threaded, streams│
                        └──────────────┬───────────────┘
                                       │  ScanNode
  dragged folder ──────────────────────┤
  (browser manifest,                   ▼
   names + sizes only)  ┌──────────────────────────────┐
                        │  catalog/   catalog.yaml     │  ~80% resolved, 0 cost
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
                        │  quarantine/  move + manifest│
                        └──────────────────────────────┘
```

Both entry points converge on the same classification pipeline. The scanner is a pure library
with no dependency on the web or AI layers, so it stays portable to a CLI or a native shell.

---

## Running it

**Analyze a folder — nothing to install.** Open the hosted build and drag a directory onto the
page. The browser walks the tree locally and sends only a manifest of names and sizes; no file
contents leave your machine. You get the full analysis, read-only.

**Analyze your whole machine.**

```bash
uvx --from git+https://github.com/<user>/sift sift
```

One command. It starts the local server, opens your browser, and begins scanning the default
safe roots immediately — no configuration, no empty state.

---

## Development

This project is **test-first, without exception.** Behaviour is specified in Gherkin before it
is implemented. See [CLAUDE.md](CLAUDE.md) for the full working rules.

```bash
uv sync
pre-commit install && pre-commit install --hook-type pre-push

pytest                      # full suite
pytest -m "not slow"        # fast suite, matches the pre-commit hook
```

Every commit runs formatting, linting, type checks, and the fast suite automatically. Every
push runs the full suite including filesystem scenarios and end-to-end tests. No test makes a
network call — the model layer has a deterministic fake and recorded fixtures.

---

## Roadmap

- **Native shell.** A Tauri wrapper gets real drag-and-drop with absolute paths (the browser
  gives contents, not locations), a proper app icon, and small signed binaries.
- **Learned catalog.** Corrections you make — "this is actually safe", "never touch this" —
  feed back into your own catalog, so it improves with use.
- **Duplicate and version detection** by content hash, as a second lens on the same scan.
- **Linux and Windows catalogs.**

---

## License

All rights reserved. This repository is public for reading; it is not open source and no
license to use, modify, or distribute is granted.
