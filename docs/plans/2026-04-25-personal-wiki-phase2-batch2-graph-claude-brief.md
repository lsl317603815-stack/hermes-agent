# Personal Wiki Phase 2 Batch 2 — Graph Check Brief

> Execution target: local Claude Code, explicitly triggered with `/using-superpowers`.

## Objective

Implement **only** Phase 2 backlog item `P2-3` for the master personal wiki at `/Users/ryuka/personal-wiki`:

- extend `scripts/lint_wiki.py` with a `--graph` mode
- keep the scope narrow and verifiable
- update the minimum required docs so the new behavior is discoverable

Do **not** work on machine-readable schema sidecars, ingest tooling, taxonomy promotion, or any Hermes sub-library files.

## Constraints

1. Work only inside `/Users/ryuka/personal-wiki`.
2. Do **not** read from or write to `/Users/ryuka/Documents/GitHub/hermes-agent/docs/wiki` except the existence of its path already referenced by the master wiki.
3. Keep this batch small enough to avoid Claude Code turn-limit failures.
4. Preserve all current passing checks in normal mode and strict mode.
5. Use standard library only; no new dependencies.

## Current State

Already complete:
- `scripts/lint_wiki.py` exists and passes:
  - `python3 scripts/lint_wiki.py`
  - `python3 scripts/lint_wiki.py --strict`
- Current page set: 16 markdown pages
- Current docs already record Phase 2 Batch 1 in `log.md`

Known backlog target (`_meta/backlog.md`):
- `P2-3 | Wikilink graph check | lint_wiki.py --graph — flag dangling wikilink targets (for example a link to concepts/example-concept) and pages with zero inbound links.`

## Required Deliverables

### 1) Extend `scripts/lint_wiki.py`
Add a CLI flag:
- `--graph`

Expected behavior:
- Build a directed wikilink graph across all non-`raw/` markdown pages.
- Reuse the same target normalization as existing wikilink resolution logic.
- Report pages with **zero inbound links**.
- Preserve existing dangling-link detection behavior.
- Keep output human-readable and deterministic.

Recommended severity model:
- dangling wikilinks remain **errors** (same as today)
- zero-inbound pages are **warnings**, not errors
  - rationale: some root/meta pages may be intentionally hub-like or lightly linked during early phases

Implementation notes:
- Avoid duplicate edge counting from repeated identical wikilinks in the same page.
- Exclude `raw/` as current linter already does.
- Include root/meta pages in the graph unless there is a very strong reason not to; if you exclude any class of pages, document it explicitly.
- `--graph` should be additive, not a separate script.

### 2) Update docs minimally
Update only if needed:
- `/Users/ryuka/personal-wiki/SCHEMA.md`
- `/Users/ryuka/personal-wiki/log.md`

Minimum doc sync required:
- `log.md` gets a new Phase 2 Batch 2 entry describing the graph check.
- `SCHEMA.md` should mention that graph checking now exists if there is a natural status section for that.

Do **not** rewrite large portions of documentation.

## Verification Required
After implementation, run and confirm:

```bash
python3 scripts/lint_wiki.py
python3 scripts/lint_wiki.py --strict
python3 scripts/lint_wiki.py --graph
python3 scripts/lint_wiki.py --graph --strict
```

Desired result:
- all commands exit successfully unless there is a real error introduced
- output is clean or limited to intentional warning-level graph findings
- if zero-inbound warnings appear, either:
  - fix them by adding reasonable links, or
  - leave them only if clearly intentional and document briefly in `log.md`

## Non-Goals
Do not:
- add machine-readable YAML/JSON schema sidecars
- change taxonomy values
- touch `_meta/source-manifest.md`
- add ingest scripts
- modify Hermes repo-local wiki contents
- expand the page set beyond what is needed to satisfy graph validation

## Completion Standard
This batch is complete only if:
1. `scripts/lint_wiki.py --graph` exists and works
2. normal + strict + graph runs are verified
3. docs are minimally synced
4. no unrelated files are changed
