# Sift — working rules

Short version: specify behaviour first, in Gherkin, then make it pass. Every commit is
checked automatically. Nothing is ever deleted.

## Non-negotiables

**TDD, without exception.** No implementation code is written before a failing test exists
for it. If you catch yourself writing a function with no red test behind it, stop and write
the test.

**BDD style.** Behaviour lives in Gherkin `.feature` files under `tests/features/`, written
in the user's language, not the code's. Step definitions bind them to the system.

**Fat integration tests, not unit tests.** Every test exercises real code paths end to end —
real filesystem, real graph, real HTTP, real model — against a fixture that resembles a real
machine. **Nothing is mocked, including the model.** Never mock the filesystem, never stub a
layer of our own code, never assert on a constant. A fake only ever proves the fake works.
Prefer one scenario that proves something true about the whole system over five that each
poke at a part of it.

**Real model calls are nondeterministic, so assert on properties, not strings.** `node_modules
is never irreplaceable` is a real assertion; `restore == "npm install"` is a flake waiting to
happen. Anything that hits the network is marked `slow`, so it runs on push rather than on
every commit — the model is real either way, only the cadence differs.

**One realistic fixture.** `tests/machine.py` builds a temp tree with active projects, build
output, package caches, a locked directory and a symlink all present at once. Bugs live in the
interaction between those, and a two-file fixture never exercises the interaction.

**Never `unlink`.** Reclaiming moves paths into a quarantine directory with a manifest.
Deletion is the user emptying quarantine, never us. There is no code path in this repo that
calls `os.remove`, `shutil.rmtree`, or equivalent on user data.

**No secrets in the repo.** API keys live in `.env`, which is git-ignored from the first code
commit. `.env.example` carries placeholders only. Never log a key, never send one to the
frontend — all model calls go through the backend.

## Decisions are made together

**No architectural, product, dependency, or data-modelling decision is made unilaterally.**
When a choice has more than one defensible answer, stop and present it:

- the options, one line each
- the tradeoff that actually separates them — not a feature list
- a recommendation, with the reason it wins

Then wait for an answer. Every decision here has to be defended out loud later, which means
its author needs a reason they actually hold, not one handed to them after the fact.

Record the outcome in the **commit body**: what was chosen, what was rejected, and why.
`git log` is the decision record. There is exactly one human-facing document in this repo —
`README.md` — and no side files accumulate beside it.

Cheap and reversible choices — variable names, test file layout, formatting — don't need a
round trip. The test is: **would someone reasonably ask "why did you do it that way?"** If
yes, ask first.

## The loop

1. Write or extend a scenario in `tests/features/*.feature`.
2. Write the step definitions. Run them. **Watch them fail** — a test that has never failed
   proves nothing.
3. Write the minimum implementation to go green.
4. Refactor with the tests still green.
5. Commit. Hooks run automatically.

## Automated checks

Managed by `pre-commit`, installed with `pre-commit install && pre-commit install --hook-type pre-push`.

**On every commit:** `ruff format --check`, `ruff check`, `mypy`, and the fast test suite
(`pytest -m "not slow"`), plus `eslint` / `svelte-check` on staged frontend files.

**On push:** the full suite including slow filesystem scenarios and Playwright end-to-end runs.

Hooks are not optional and are not bypassed. If a hook is wrong, fix the hook.

## Boundaries that matter

- `sift/scanner/` imports **nothing** from FastAPI, OpenAI, or the web layer. It is a pure
  `path -> ScanNode` library and must stay portable to a CLI or a native shell later.
- The path catalog is **data** (`sift/catalog/catalog.yaml`), never Python. It is the part
  that accretes value; keep it editable without a code change.
- The LLM sits behind one interface so the provider can be swapped by env var, **not** so it
  can be faked. Tests call the real thing.
- Pydantic models in `sift/models.py` are the contract between scanner, classifier, and UI.
  Change them there first; everything else follows.

## Layout

```
sift/
  models.py            Pydantic contracts — the source of truth
  scanner/             Pure filesystem walk. No AI, no web.
  catalog/             catalog.yaml + loader. Known paths, known verdicts.
  classify/            LLM layer. Only ever sees what the catalog couldn't name.
  plan/                Aggregation, goal parsing, ordering
  quarantine/          Move, manifest, undo
  api/                 FastAPI, SSE
web/                   SvelteKit frontend
tests/
  machine.py           The realistic fixture everything runs against
  features/            Gherkin scenarios
  steps/               Step definitions
```

## Stack

Python 3.12, FastAPI, Pydantic v2, pytest + pytest-bdd, ruff, mypy.
SvelteKit, TypeScript, Tailwind, D3 (`d3-hierarchy`), Vitest, Playwright.

## Style

Match the surrounding code. Type hints everywhere. Prefer a boring function over a clever
abstraction. Comment *why*, never *what*.
