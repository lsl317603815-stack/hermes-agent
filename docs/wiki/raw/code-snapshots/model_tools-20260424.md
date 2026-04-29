---
kind: snapshot
source_path: model_tools.py
captured_at: 2026-04-24
sha256: c05266e03661fac5ac736db935a822a850ffc0b92115abbc8fbf622f3235dd9e
supersedes: —
---

# model_tools.py — structured code snapshot

File stats: 562 lines · top-level classes: none · top-level functions: `_get_tool_loop`, `_get_worker_loop`, `_run_async`, `get_tool_definitions`, `coerce_tool_args`, `_coerce_value`, `_coerce_number`, `_coerce_boolean`, `handle_function_call`, `get_all_tool_names`, `get_toolset_for_tool`, `get_available_toolsets`, `check_toolset_requirements`, `check_tool_availability`.

## Public surface

- `get_tool_definitions(enabled_toolsets=None, disabled_toolsets=None, quiet_mode=False) -> List[Dict[str, Any]]` (line 196) — main schema provider for model API calls. Resolves enabled vs. disabled toolsets (with `_LEGACY_TOOLSET_MAP` fallback for old `*_tools` names), then delegates to `registry.get_definitions(tools_to_include, quiet)` for OpenAI-format schemas.
- `handle_function_call(function_name, function_args, task_id=None, tool_call_id=None, session_id=None, user_task=None, enabled_tools=None, skip_pre_tool_call_hook=False) -> str` (line 421) — main dispatcher; coerces args, fires plugin pre/post hooks, routes to `registry.dispatch()`, returns a JSON string.
- `coerce_tool_args(tool_name, args) -> Dict[str, Any]` (line 334) — coerces stringy LLM args (`"42"` → `42`, `"true"` → `True`) against the registered JSON Schema (`integer` / `number` / `boolean` / union types). Mutates input dict in place.
- `TOOL_TO_TOOLSET_MAP: Dict[str, str]` (line 153) — built once after discovery from `registry.get_tool_to_toolset_map()`; consumed by `batch_runner.py`.
- `TOOLSET_REQUIREMENTS: Dict[str, dict]` (line 155) — built once after discovery from `registry.get_toolset_requirements()`; consumed by `cli.py` and `doctor.py`.
- `get_all_tool_names()` (line 540), `get_toolset_for_tool(name)` (line 545), `get_available_toolsets()` (line 550), `check_toolset_requirements()` (line 555), `check_tool_availability(quiet=False)` (line 560) — thin proxies over the registry singleton, preserved for backward compat.

## Key wiring facts

- Tool discovery is driven at module import time: `discover_builtin_tools()` runs unconditionally at line 132. MCP discovery (`tools.mcp_tool.discover_mcp_tools`) and plugin discovery (`hermes_cli.plugins.discover_plugins`) follow inside try/except guards (lines 134–146).
- `_AGENT_LOOP_TOOLS = {"todo", "memory", "session_search", "delegate_task"}` (line 326) — schemas live in the registry but execution is intercepted by the agent loop. If a call slips through to `handle_function_call`, it returns `{"error": "<name> must be handled by the agent loop"}` before dispatch.
- `_READ_SEARCH_TOOLS = {"read_file", "search_files"}` (line 327) — gates the `notify_other_tool_call` reset hook in `tools.file_tools` (resets the consecutive-read counter when a non-read/search tool fires).
- `_LEGACY_TOOLSET_MAP` (line 166) maps deprecated `*_tools` names (`web_tools`, `terminal_tools`, `vision_tools`, `moa_tools`, `image_tools`, `skills_tools`, `browser_tools`, `cronjob_tools`, `rl_tools`, `file_tools`, `tts_tools`) to tool-name lists; resolved alongside the canonical toolset path inside `get_tool_definitions()`.
- `_last_resolved_tool_names: List[str]` (line 159) — process-global mirror of the tool names returned by the most recent `get_tool_definitions()` call. Consumed by `code_execution_tool` to know which sandbox tools are alive when `enabled_tools=` is not provided to `handle_function_call`.
- `execute_code` schema is rebuilt dynamically in `get_tool_definitions()` (lines 257–266): only sandbox tools that pass `check_fn` are advertised, computed via `SANDBOX_ALLOWED_TOOLS & available_tool_names`.
- `browser_navigate` description is patched (lines 271–286) to strip the "prefer web_search or web_extract" suggestion when `web_search` / `web_extract` are not in the available set.

## Invariants enforced in this module

- Every tool handler must return a JSON string; errors are normalized via `json.dumps({"error": ...}, ensure_ascii=False)` (lines 532–534).
- `_run_async()` (line 81) is the single source of truth for sync→async bridging from inside tool handlers — three lifecycles: (1) inside a running loop (gateway / RL env) it spawns a disposable thread and uses `asyncio.run()`; (2) on a worker thread it uses `_get_worker_loop()` (per-thread persistent loop in `_worker_thread_local`); (3) otherwise it uses `_get_tool_loop()` (process-global persistent loop guarded by `_tool_loop_lock`). Persistent loops are required so cached httpx / AsyncOpenAI clients don't trigger "Event loop is closed" on GC.
- Tools in `_AGENT_LOOP_TOOLS` must never be dispatched via the registry from `handle_function_call` — the short-circuit at line 459 returns an error stub before dispatch.
- `coerce_tool_args` mutates the input dict in place (line 363); callers needing the original must copy first.
- `_coerce_value` returns the original `value` object identity on no-op, so callers detect coercion via `coerced is not value` (line 361).
- When `skip_pre_tool_call_hook=True`, the `pre_tool_call` hook still fires for observers but its return value is ignored — callers that already checked must pass `True` to avoid double-firing the block-message check (lines 463–488).

## Imports of interest (head of file, lines 23–28)

- `from tools.registry import discover_builtin_tools, registry`
- `from toolsets import resolve_toolset, validate_toolset`
- Local imports inside functions: `from toolsets import get_all_toolsets` (lines 235, 252), `from tools.code_execution_tool import SANDBOX_ALLOWED_TOOLS, build_execute_code_schema` (line 258), `from hermes_cli.plugins import get_pre_tool_call_block_message` (line 467), `from hermes_cli.plugins import invoke_hook` (lines 484, 522), `from tools.file_tools import notify_other_tool_call` (line 498).

## References

- Source file: `model_tools.py` (full body is the authoritative source)
- Registry: `tools/registry.py` (provides `discover_builtin_tools`, `registry`, dispatch, schema retrieval)
- Toolset definitions: `toolsets.py` (provides `resolve_toolset`, `validate_toolset`, `get_all_toolsets`)
- Sandbox tool registry: `tools/code_execution_tool.py` (`SANDBOX_ALLOWED_TOOLS`, `build_execute_code_schema`)
- Plugin hook contract: `hermes_cli/plugins/__init__.py` (`get_pre_tool_call_block_message`, `invoke_hook`, `discover_plugins`)
- Read-loop tracker: `tools/file_tools.py` (`notify_other_tool_call`)
- MCP discovery: `tools/mcp_tool.py` (`discover_mcp_tools`)
- Agent loop callers: `run_agent.py` (uses `get_tool_definitions`, `handle_function_call`, `_run_async`)
