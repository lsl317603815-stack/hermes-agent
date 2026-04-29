---
kind: snapshot
source_path: agent/context_engine.py
captured_at: 2026-04-24
sha256: faea2b31d04490bb7660d66ffac6e93634ab13f573f86e0070983341cdcb8b20
supersedes: —
---

# agent/context_engine.py — structured code snapshot

File stats: 184 lines · top-level classes: `ContextEngine` · top-level functions: none.

## Public surface

- `ContextEngine(ABC)` (line 32) — abstract base class every context-management engine subclasses. Exactly one engine is active per agent instance; selection is config-driven via `context.engine` in config.yaml (default `"compressor"` → built-in `ContextCompressor`; alternatives live under `plugins/context_engine/<name>/`).
- Class attributes (read directly by `run_agent.py` — subclasses MUST keep these updated):
  - `last_prompt_tokens: int = 0` (line 55)
  - `last_completion_tokens: int = 0` (line 56)
  - `last_total_tokens: int = 0` (line 57)
  - `threshold_tokens: int = 0` (line 58) — absolute token count at which compaction fires
  - `context_length: int = 0` (line 59) — current model's context window
  - `compression_count: int = 0` (line 60) — lifetime count of compactions this session
- Compaction-parameter defaults (overridable via `__init__` or property):
  - `threshold_percent: float = 0.75` (line 68)
  - `protect_first_n: int = 3` (line 69) — oldest messages never summarized
  - `protect_last_n: int = 6` (line 70) — most recent messages never summarized
- Abstract methods (subclass MUST implement):
  - `name -> str` (property, line 39) — short identifier (e.g. `'compressor'`, `'lcm'`).
  - `update_from_response(usage: Dict[str, Any]) -> None` (line 66) — called after every LLM call; engine updates its tracked token fields from the `usage` dict.
  - `should_compress(prompt_tokens: int = None) -> bool` (line 73) — predicate consulted after each turn to decide if `compress()` must fire.
  - `compress(messages: List[Dict[str, Any]], current_tokens: int = None) -> List[Dict[str, Any]]` (line 77) — main entry point: receives the full message list, returns a (possibly shorter) OpenAI-format message sequence that fits within budget. Implementation is free to summarize, build a DAG, or do anything else provided the return shape is valid.
- Optional methods (ABC provides defaults):
  - `should_compress_preflight(messages) -> bool` (line 93) — cheap pre-API estimate. Default returns `False` (skip pre-flight).
  - `on_session_start(session_id: str, **kwargs) -> None` (line 103) — load persisted state for the session; `kwargs` may include `hermes_home`, `platform`, `model`, etc.
  - `on_session_end(session_id: str, messages: List[Dict[str, Any]]) -> None` (line 110) — real session boundary only (CLI exit, `/reset`, gateway expiry). NOT per-turn.
  - `on_session_reset() -> None` (line 117) — resets `last_prompt_tokens`, `last_completion_tokens`, `last_total_tokens`, and `compression_count` to `0` (lines 122–125).
  - `get_tool_schemas() -> List[Dict[str, Any]]` (line 129) — return tools the engine exposes to the agent (e.g. `lcm_grep`, `lcm_describe`, `lcm_expand`). Default `[]`.
  - `handle_tool_call(name: str, args: Dict[str, Any], **kwargs) -> str` (line 137) — dispatch a tool call; default returns `json.dumps({"error": f"Unknown context engine tool: {name}"})`. Must return JSON string. `kwargs` may include `messages` for live ingestion.
  - `get_status() -> Dict[str, Any]` (line 151) — display/logging dict. Default returns `last_prompt_tokens`, `threshold_tokens`, `context_length`, `usage_percent` (clamped to ≤100), `compression_count`.
  - `update_model(model: str, context_length: int, base_url: str = "", api_key: str = "", provider: str = "") -> None` (line 169) — called on model switch or fallback activation; default recomputes `threshold_tokens = int(context_length * threshold_percent)` (line 182–183).

## Key wiring facts

- Selection is documented as config-driven (lines 9–13 of module docstring): `context.engine` in config.yaml; default `"compressor"`; third-party engines live under `plugins/context_engine/<name>/`.
- The lifecycle order documented in the module docstring (lines 18–26) is:
  1. Engine instantiated and registered (plugin `register()` or built-in default)
  2. `on_session_start()` when a conversation begins
  3. `update_from_response()` after each API response with usage data
  4. `should_compress()` checked after each turn
  5. `compress()` called when `should_compress()` returns `True`
  6. `on_session_end()` at real session boundaries only
- `run_agent.py` reads the token-state class attributes directly (not via getters) — see `run_agent.py` snapshot lines 1421–1479 for engine selection and 1509–1517 for tool injection. The engine must keep attributes live between turns.
- Tool exposure (lines 129–148): engines that expose tools participate in the same agent-loop schema/dispatch surface as memory providers. An engine with no tools returns `[]` and will not see `handle_tool_call` invocations.

## Invariants enforced in this module

- File is a pure ABC — no runtime behavior on import; no global state; no side effects.
- Token-state attributes are class-level defaults. Subclasses that need per-instance state MUST shadow them in `__init__` (they start as class attributes shared across instances until first assignment).
- Only four methods are `@abstractmethod`: `name`, `update_from_response`, `should_compress`, `compress`. Every other method has a safe default.
- `on_session_reset()` default implementation resets exactly four fields (lines 122–125) — `threshold_tokens` and `context_length` are deliberately NOT reset because they are model-scoped, not session-scoped.
- `update_model()` default recomputes `threshold_tokens` from the canonical formula `int(context_length * threshold_percent)` — subclasses overriding this must preserve the post-condition that `threshold_tokens` reflects the new `context_length`.
- `get_status()` `usage_percent` is clipped at 100 and returns 0 when `context_length == 0` (line 160–163) to avoid divide-by-zero during pre-initialization.
- `handle_tool_call` default returns an error JSON string — NOT `raise` — so a misdispatched tool call degrades gracefully instead of crashing the agent loop.

## Imports of interest (head of file, lines 28–29)

- `from abc import ABC, abstractmethod`
- `from typing import Any, Dict, List`

Local deferred import: `import json` inside `handle_tool_call` default (line 147) — the ABC stays dependency-free at module scope.

## References

- Source file: `agent/context_engine.py` (full body is the authoritative source)
- Default implementation: `agent/context_compressor.py` (built-in `ContextCompressor`; not captured this batch)
- Plugin loading path: `plugins/context_engine/<name>/` (per docstring lines 5–8)
- Consumer wiring the engine into the agent loop: `run_agent.py` (engine selection at lines 1421–1479, tool injection at lines 1509–1517 per the `run_agent.py` snapshot)
- Docstring authoritative reference for lifecycle ordering: lines 15–26 of this file
- Sibling ABC in the extension surface: `agent/memory_provider.py` (captured this batch)
