# Sift — working rules

Short version: specify behaviour first, in Gherkin, then make it pass. Every commit is
checked automatically. Nothing is ever deleted.

## Non-negotiables

**TDD, without exception.** No implementation code is written before a failing test exists
for it. If you catch yourself writing a function with no red test behind it, stop and write
the test.

**BDD style.** Behaviour lives in Gherkin `.feature` files under `tests/features/`, written
in the user's language, not the code's. Step definitions bind them to the system. Unit tests
exist only for things a scenario can't reasonably reach (parsers, size arithmetic, edge cases).

**Never `unlink`.** Reclaiming moves paths into a quarantine directory with a manifest.
Deletion is the user emptying quarantine, never us. There is no code path in this repo that
calls `os.remove`, `shutil.rmtree`, or equivalent on user data.

**No secrets in the repo.** API keys live in `.env`, which is git-ignored from the first code
commit. `.env.example` carries placeholders only. Never log a key, never send one to the
frontend — all model calls go through the backend.

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
- The LLM classifier sits behind one interface with a deterministic fake used by every test.
  **No test may make a network call.** Model behaviour is pinned with recorded fixtures.
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
  features/            Gherkin scenarios
  steps/               Step definitions
  unit/                Narrow tests only
```

## Stack

Python 3.12, FastAPI, Pydantic v2, pytest + pytest-bdd, ruff, mypy.
SvelteKit, TypeScript, Tailwind, D3 (`d3-hierarchy`), Vitest, Playwright.

## Style

Match the surrounding code. Type hints everywhere. Prefer a boring function over a clever
abstraction. Comment *why*, never *what*.
