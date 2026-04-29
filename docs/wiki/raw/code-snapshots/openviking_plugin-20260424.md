---
kind: snapshot
source_path: plugins/memory/openviking/__init__.py
captured_at: 2026-04-24
sha256: d1d4a1a86063a8b114ee4eb82fe201095e3cd83cd8a50d6e4fe10f957afa536d
supersedes: —
---

# plugins/memory/openviking/__init__.py — structured code snapshot

File stats: 674 lines · top-level classes: `_VikingClient`, `OpenVikingMemoryProvider` · top-level functions: `_atexit_commit_sessions`, `_get_httpx`, `register` · module constants: `_DEFAULT_ENDPOINT`, `_TIMEOUT`, `_last_active_provider`, `SEARCH_SCHEMA`, `READ_SCHEMA`, `BROWSE_SCHEMA`, `REMEMBER_SCHEMA`, `ADD_RESOURCE_SCHEMA`.

## Public surface

- `register(ctx) -> None` (line 672) — plugin entry point. Calls `ctx.register_memory_provider(OpenVikingMemoryProvider())`; this is the only symbol the plugin loader needs.
- `OpenVikingMemoryProvider(MemoryProvider)` (line 255) — full bidirectional memory provider subclassing `agent.memory_provider.MemoryProvider`.
  - `name -> "openviking"` (property, line 270)
  - `is_available() -> bool` (line 273) — returns `bool(os.environ.get("OPENVIKING_ENDPOINT"))`; zero network calls.
  - `get_config_schema()` (line 277) — five fields (all with `env_var` set; only `api_key` is `secret`):
    - `endpoint` (required, default `http://127.0.0.1:1933`, env `OPENVIKING_ENDPOINT`)
    - `api_key` (secret, env `OPENVIKING_API_KEY`)
    - `account` (default `default`, env `OPENVIKING_ACCOUNT`)
    - `user` (default `default`, env `OPENVIKING_USER`)
    - `agent` (default `hermes`, env `OPENVIKING_AGENT`)
  - `initialize(session_id, **kwargs)` (line 312) — reads env vars, constructs `_VikingClient`, probes `/health`; on ImportError for httpx or failed health check, sets `self._client = None` (graceful disable). Registers `self` as `_last_active_provider` for atexit safety net.
  - `system_prompt_block()` (line 337) — GET `/api/v1/fs/ls?uri=viking://`; returns a short prompt block only if the root listing contains ≥1 child (line 347). Falls back to a generic block on exception.
  - `prefetch(query, session_id="")` (line 364) — joins any running `_prefetch_thread` with 3.0 s timeout, then returns the buffered `self._prefetch_result` (cleared under `_prefetch_lock`). Output is prefixed with `"## OpenViking Context\n"`.
  - `queue_prefetch(query, session_id="")` (line 375) — spawns a daemon thread (`name="openviking-prefetch"`) that POSTs `/api/v1/search/find` with `{"query": query, "top_k": 5}` and formats up to 3 items each from the `memories` and `resources` buckets into a score-prefixed list.
  - `sync_turn(user_content, assistant_content, session_id="")` (line 411) — joins any prior `_sync_thread` with 5.0 s timeout, then spawns a new daemon thread (`name="openviking-sync"`) that POSTs each of user/assistant messages to `/api/v1/sessions/{sid}/messages`. Content is trimmed to 4000 chars.
  - `on_session_end(messages)` (line 448) — first joins `_sync_thread` with 10.0 s timeout **before** checking `_turn_count`; only if `_turn_count > 0` does it POST `/api/v1/sessions/{sid}/commit` (triggers server-side memory extraction).
  - `on_memory_write(action, target, content)` (line 472) — only acts on `action == "add"` with non-empty content; spawns daemon (`name="openviking-memwrite"`) that posts a `parts`-shaped message tagged `"[Memory note — {target}] {content}"`.
  - `get_tool_schemas()` (line 497) — returns `[SEARCH_SCHEMA, READ_SCHEMA, BROWSE_SCHEMA, REMEMBER_SCHEMA, ADD_RESOURCE_SCHEMA]`.
  - `handle_tool_call(tool_name, args, **kwargs)` (line 500) — dispatches to `_tool_search`, `_tool_read`, `_tool_browse`, `_tool_remember`, `_tool_add_resource`. Unknown names and exceptions are wrapped via `tools.registry.tool_error`.
  - `shutdown()` (line 519) — joins both `_sync_thread` and `_prefetch_thread` with 5.0 s timeouts; clears the global `_last_active_provider` if still pointing at `self` to avoid double-commit.
- Tool schemas (all OpenAI-function-format, exported as module constants):
  - `SEARCH_SCHEMA` (line 137) → `viking_search(query, mode?, scope?, limit?)`; modes `auto` / `fast` / `deep`.
  - `READ_SCHEMA` (line 163) → `viking_read(uri, level?)`; levels `abstract` (~100 tok, L0) / `overview` (~2k tok, L1, default) / `full` (L2).
  - `BROWSE_SCHEMA` (line 185) → `viking_browse(action, path?)`; actions `tree` / `list` / `stat`.
  - `REMEMBER_SCHEMA` (line 209) → `viking_remember(content, category?)`; categories `preference` / `entity` / `event` / `case` / `pattern`.
  - `ADD_RESOURCE_SCHEMA` (line 230) → `viking_add_resource(url, reason?)`.
- Internal helpers:
  - `_VikingClient` (line 80) — thin httpx wrapper; constructor stores `endpoint` (stripped trailing `/`), `api_key`, tenant identifiers; raises `ImportError` if httpx is not installed. Methods: `_headers()` (injects `X-OpenViking-Account`/`-User`/`-Agent` and optional `X-API-Key`), `_url()`, `get()`, `post()` (both use `timeout=30.0`), and `health()` which GETs `/health` with a 3.0 s timeout and returns `True` only on HTTP 200.
  - `_get_httpx()` (line 71) — lazy httpx import; returns module or `None`.
  - `_atexit_commit_sessions()` (line 51) — registered at import via `atexit.register` (line 64); fires `provider.on_session_end([])` on the last active provider as a best-effort safety net for SIGKILL / crash-before-shutdown paths.

## Key wiring facts

- Plugin discovery: `register(ctx)` at line 672 is the sole entry point. The module is loaded by `hermes_cli.plugins.discover_plugins()` per the shared plugin contract; `ctx.register_memory_provider()` hands the instance to the `MemoryManager`.
- Activation gate: `is_available()` reads only `OPENVIKING_ENDPOINT` from the process environment (line 275). Per the `MemoryProvider` ABC contract, this is called during agent init with no network I/O.
- atexit safety net lives at module scope (lines 48–64): `_last_active_provider` is a module global assigned inside `initialize()` (line 333–334). `_atexit_commit_sessions` swallows every exception (`pass  # best-effort at shutdown time`, line 58) so shutdown cannot crash the interpreter.
- HTTP transport: `_VikingClient` uses httpx with `timeout=_TIMEOUT` (30 s) for all standard calls and a 3 s timeout on `/health`. Bearer auth is set as `X-API-Key` header, NOT `Authorization: Bearer` (line 103).
- Threading model:
  - `_sync_thread` (sync writes to session messages) — at most one alive at a time; `sync_turn` joins the previous with 5.0 s timeout before spawning a new one (lines 435–440).
  - `_prefetch_thread` (pre-loads context for next turn) — at most one alive at a time; `prefetch` joins with 3.0 s timeout on consumption (lines 365–366); `shutdown()` joins with 5.0 s.
  - Memory-write thread (`openviking-memwrite`) — fire-and-forget, not tracked.
  - All threads are daemon threads named for debuggability.
- Server-side memory extraction is triggered by `POST /api/v1/sessions/{sid}/commit` (line 465) on `on_session_end`. OpenViking extracts six categories according to the module docstring (lines 22–23): profile, preferences, entities, events, cases, patterns.
- `_tool_search` (line 531) orders results across `memories`, `resources`, and `skills` buckets by raw `score` (descending) after a tolerant sort-key for `None` scores (lines 556–558); it attaches up to 3 related URIs per entry.
- `_tool_read` (line 573) maps level → endpoint: `abstract` → `/api/v1/content/abstract`; `full` → `/api/v1/content/read`; everything else (default `overview`) → `/api/v1/content/overview` (lines 580–585). Truncates content at 8000 chars with an in-band notice (lines 591–593).
- `_tool_browse` (line 601) action → endpoint map: `tree` → `/api/v1/fs/tree`, `list` → `/api/v1/fs/ls`, `stat` → `/api/v1/fs/stat`; default on unknown action is `ls` (lines 607–608). Caps directory entries at 50 (line 613).
- `_tool_remember` (line 625) does NOT call a dedicated memory endpoint — it posts a session message tagged `[Remember]` (optionally `[Remember — category]`) so the subsequent `/commit` call extracts it as an explicit memory (lines 631–642).

## Invariants enforced in this module

- Module import is side-effect minimal but NOT pure: `atexit.register(_atexit_commit_sessions)` (line 64) runs at import time. Importing this module in a test without cleanup leaves an atexit callback registered for the test process lifetime.
- `is_available()` performs zero network I/O per the ABC contract — only an environment variable read (lines 274–275).
- All provider methods short-circuit on `self._client is None` (the disabled state after a failed health check or missing httpx): `system_prompt_block` (line 339), `prefetch` (via empty buffer), `queue_prefetch` (line 377), `sync_turn` (line 413), `on_session_end` (line 455), `on_memory_write` (line 474), `handle_tool_call` (line 502) — so a partially-configured OpenViking instance fails open and never crashes the agent loop.
- `on_session_end` joins the in-flight sync thread BEFORE the `_turn_count > 0` guard (lines 457–462) so that late message writes are flushed even when `_turn_count` hasn't been incremented yet.
- `shutdown()` clears the module global `_last_active_provider` only if it still references `self` (lines 528–530) — preserving correctness when multiple providers are initialized in sequence within one process (the latest `initialize()` wins the atexit slot).
- Thread names (`openviking-prefetch`, `openviking-sync`, `openviking-memwrite`) are stable for grep-based log correlation.
- Error handling policy: network exceptions are logged at `debug` (sync paths, background operations) or `warning` (health check, system prompt block, commit) and never raised out of the provider methods — the agent loop never sees OpenViking errors.
- Content truncation at the tool-result boundary is mandatory: message bodies are trimmed to 4000 chars before write (`sync_turn` lines 432, 434) and to 8000 chars on read (`_tool_read` lines 591–593).

## Imports of interest (head of file, lines 27–37)

- `from __future__ import annotations`
- `import atexit`, `import json`, `import logging`, `import os`, `import threading`
- `from typing import Any, Dict, List, Optional`
- `from agent.memory_provider import MemoryProvider`
- `from tools.registry import tool_error`

Deferred: `import httpx` inside `_get_httpx()` (line 71). The plugin stays importable even if httpx is not installed — the failure surface is pushed to `initialize()`.

## References

- Source file: `plugins/memory/openviking/__init__.py` (full body is the authoritative source)
- ABC contract implemented by this plugin: `agent/memory_provider.py` (captured this batch)
- Plugin registration contract: `hermes_cli/plugins/__init__.py` (the `ctx.register_memory_provider()` interface used by `register()`)
- Tool error helper: `tools/registry.py` (`tool_error` — shared JSON error format)
- Module docstring (lines 1–24) documents: Volcengine/ByteDance origin, original PR #3369 by Mibayy, viking:// URI namespace, three-tier context model (L0 ~100 tok / L1 ~2k / L2 full), six memory extraction categories
- Environment variable contract (docstring lines 11–16): `OPENVIKING_ENDPOINT`, `OPENVIKING_API_KEY`, `OPENVIKING_ACCOUNT`, `OPENVIKING_USER`, `OPENVIKING_AGENT`
