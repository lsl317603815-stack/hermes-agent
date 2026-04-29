---
kind: snapshot
source_path: tools/registry.py
captured_at: 2026-04-24
sha256: b5693c0334e4c7caa4ee0ac0f02d102fed3f18252529804291a49c0bc9efbc40
supersedes: —
---

# tools/registry.py — structured code snapshot

File stats: 482 lines · top-level classes: `ToolEntry`, `ToolRegistry` · top-level functions: `_is_registry_register_call`, `_module_registers_tools`, `discover_builtin_tools`, `tool_error`, `tool_result` · module-level singleton: `registry = ToolRegistry()`.

## Public surface

- `ToolEntry` (line 76) — slot-based metadata container. Slots: `name`, `toolset`, `schema`, `handler`, `check_fn`, `requires_env`, `is_async`, `description`, `emoji`, `max_result_size_chars`. Constructor at line 85.
- `ToolRegistry` (line 100) — singleton class. `__init__` (line 103) creates `_tools: Dict[str, ToolEntry]`, `_toolset_checks: Dict[str, Callable]`, `_toolset_aliases: Dict[str, str]`, and `_lock: threading.RLock`.
  - `register(name, toolset, schema, handler, check_fn=None, requires_env=None, is_async=False, description="", emoji="", max_result_size_chars=None)` (line 176) — called at module-import time by each tool file.
  - `deregister(name)` (line 229) — removes a tool; cleans up toolset check + aliases when the last tool in a toolset is removed (used by MCP `notifications/tools/list_changed` nuke-and-repave).
  - `get_definitions(tool_names: Set[str], quiet=False) -> List[dict]` (line 258) — returns OpenAI-format schemas for the requested names; only tools whose `check_fn()` returns True are included.
  - `dispatch(name, args, **kwargs) -> str` (line 292) — executes a handler; bridges async handlers via `model_tools._run_async`; catches all exceptions and returns `{"error": "Tool execution failed: <Type>: <msg>"}`.
  - `register_toolset_alias(alias, toolset)` (line 151), `get_registered_toolset_aliases()` (line 162), `get_toolset_alias_target(alias)` (line 167) — alias management for plugin / MCP toolset names.
  - Query helpers: `get_entry` (line 135), `get_registered_toolset_names` (line 140), `get_tool_names_for_toolset` (line 144), `get_max_result_size` (line 315), `get_all_tool_names` (line 325), `get_schema` (line 329), `get_toolset_for_tool` (line 338), `get_emoji` (line 343), `get_tool_to_toolset_map` (line 348), `is_toolset_available` (line 352), `check_toolset_requirements` (line 362), `get_available_toolsets` (line 371), `get_toolset_requirements` (line 393), `check_tool_availability` (line 414).
- `discover_builtin_tools(tools_dir=None) -> List[str]` (line 56) — AST-scans `tools/*.py`, imports modules whose top-level body contains a `registry.register(...)` call. Excludes `__init__.py`, `registry.py`, `mcp_tool.py`. Returns the list of imported module names.
- `tool_error(message, **extra) -> str` (line 456), `tool_result(data=None, **kwargs) -> str` (line 470) — helpers that produce the JSON strings every tool handler must return.
- Module-level singleton: `registry = ToolRegistry()` (line 437) — the single source of truth across the process.

## Key wiring facts

- AST-based discovery: `_is_registry_register_call(node)` (line 28) matches the `ast.Expr` → `ast.Call` → `ast.Attribute(attr="register")` → `ast.Name(id="registry")` pattern. `_module_registers_tools(module_path)` (line 41) parses the file and returns True when at least one top-level statement matches.
- `discover_builtin_tools` (line 56) preserves a sorted import order via `sorted(tools_path.glob("*.py"))` so registration order is deterministic across platforms.
- Thread-safe mutation: every write to `_tools` / `_toolset_checks` / `_toolset_aliases` happens under `self._lock` (an `RLock`); reads use `_snapshot_state()` / `_snapshot_entries()` (lines 112, 117) to copy state under the lock and operate on stable snapshots outside.
- `get_definitions()` (line 258) memoizes `check_fn` results per call via `check_results: Dict[Callable, bool]` so a single `check_fn` shared by multiple tools (e.g. browser tools) only fires once per `get_tool_definitions` invocation.
- Schemas returned by `get_definitions()` are normalized to always include `"name": entry.name` at the top of the function block (line 282), even if the registered schema omitted the field.
- `dispatch()` (line 292) uses `from model_tools import _run_async` lazily to avoid the module-level circular import (`tools.registry` ← `model_tools` ← tool files ← `tools.registry`).

## Invariants enforced in this module

- Tool name shadowing protection (lines 191–211): when a `register(name, toolset)` call would overwrite an existing entry from a different toolset, the call is rejected with a logged error — UNLESS both toolsets are MCP (`startswith("mcp-")`), in which case overwrite is allowed (legitimate server refresh / overlapping tool names).
- The first `check_fn` registered for a toolset wins: `if check_fn and toolset not in self._toolset_checks: self._toolset_checks[toolset] = check_fn` (line 222–223).
- `deregister()` (line 229) removes the toolset check and all aliases pointing at the toolset only when the last tool in that toolset is removed.
- `_evaluate_toolset_check()` (line 125) treats `None` checks as available and treats raised exceptions as unavailable, swallowing the exception and returning False with a debug log.
- `tool_error` always emits `{"error": str(message)}` — the message is coerced to `str` (line 466), so passing exception objects works.
- `tool_result` requires either a positional `data` dict OR keyword args, not both — lines 481–483 check `if data is not None: return json.dumps(data, ...)` else falls through to kwargs.
- Module-level singleton `registry` (line 437) is the only `ToolRegistry` instance in the process; tool files import it by name, never instantiate.

## Imports of interest (head of file, lines 17–23)

- `import ast`, `import importlib`, `import json`, `import logging`, `import threading`
- `from pathlib import Path`
- `from typing import Callable, Dict, List, Optional, Set`
- Local imports inside methods: `from model_tools import _run_async` (line 304, in `dispatch`), `from tools.budget_config import DEFAULT_RESULT_SIZE_CHARS` (line 322, in `get_max_result_size`).

## References

- Source file: `tools/registry.py` (full body is the authoritative source)
- Orchestrator: `model_tools.py` (calls `discover_builtin_tools`, holds the import-time discovery sequence, dispatches via `registry`)
- Toolset resolver: `toolsets.py` (consumes `registry.get_registered_toolset_names`, `get_registered_toolset_aliases`, `get_toolset_alias_target`, `get_tool_names_for_toolset`)
- MCP refresh path: `tools/mcp_tool.py` (calls `register` / `deregister` on `notifications/tools/list_changed`)
- Tool files: every module in `tools/*.py` whose top-level body contains `registry.register(...)` (discovered via AST scan)
- Budget defaults: `tools/budget_config.py` (`DEFAULT_RESULT_SIZE_CHARS`)
- Async bridge: `model_tools._run_async` (lazy import in `dispatch` to break circular import)
