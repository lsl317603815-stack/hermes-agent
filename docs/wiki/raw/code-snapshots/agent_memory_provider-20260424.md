---
kind: snapshot
source_path: agent/memory_provider.py
captured_at: 2026-04-24
sha256: fb5a2f8eaa3f35efb5ab8426ba54e567fbf4fe0b94161369cfdce8d38a8bf4a7
supersedes: —
---

# agent/memory_provider.py — structured code snapshot

File stats: 231 lines · top-level classes: `MemoryProvider` · top-level functions: none.

## Public surface

- `MemoryProvider(ABC)` (line 42) — abstract base class that every external memory plugin subclasses. Built-in memory (`MEMORY.md` / `USER.md`) is always active as the first provider and cannot be removed; only one *external* provider runs at a time, enforced by `MemoryManager`.
- Abstract methods (subclass MUST implement):
  - `name -> str` (property, line 47) — short identifier (e.g. `'builtin'`, `'honcho'`, `'hindsight'`).
  - `is_available() -> bool` (line 53) — config + dependency check only; no network calls. Consumed during agent init to decide activation.
  - `initialize(session_id: str, **kwargs) -> None` (line 61) — one-shot setup at agent startup. Must accept a rich kwargs contract (see `kwargs` section below).
  - `get_tool_schemas() -> List[Dict[str, Any]]` (line 122) — return OpenAI-function-format schemas for tools this provider exposes; empty list for context-only providers.
- Optional methods (defaults provided on the ABC, override to opt in):
  - `system_prompt_block() -> str` (line 83) — static system-prompt text. Default: `""`. For dynamic per-turn recall, use `prefetch()` instead.
  - `prefetch(query: str, *, session_id: str = "") -> str` (line 92) — return formatted context to inject before each API call. Implementations must be fast (prefer cached background results).
  - `queue_prefetch(query: str, *, session_id: str = "") -> None` (line 106) — fire background recall after current turn; consumed by next turn's `prefetch()`. Default no-op.
  - `sync_turn(user_content: str, assistant_content: str, *, session_id: str = "") -> None` (line 114) — persist completed turn. Must be non-blocking.
  - `handle_tool_call(tool_name: str, args: Dict[str, Any], **kwargs) -> str` (line 131) — dispatch a tool call for a name returned by `get_tool_schemas()`. Default raises `NotImplementedError`. Must return a JSON string.
  - `shutdown() -> None` (line 139) — flush queues, close connections.
  - `on_turn_start(turn_number: int, message: str, **kwargs) -> None` (line 144) — per-turn tick; `kwargs` may include `remaining_tokens`, `model`, `platform`, `tool_count`.
  - `on_session_end(messages: List[Dict[str, Any]]) -> None` (line 153) — real session boundary only (CLI exit, `/reset`, gateway session expiry); NOT called per turn.
  - `on_pre_compress(messages: List[Dict[str, Any]]) -> str` (line 163) — called before context compression drops old messages; return text the compressor should fold into its summary prompt. Default: `""`.
  - `on_delegation(task: str, result: str, *, child_session_id: str = "", **kwargs) -> None` (line 175) — fires on the PARENT when a subagent completes; the subagent itself has no provider session (`skip_memory=True`).
  - `get_config_schema() -> List[Dict[str, Any]]` (line 188) — per-field descriptors for `hermes memory setup` wizard (keys: `key`, `description`, `secret`, `required`, `default`, `choices`, `url`, `env_var`).
  - `save_config(values: Dict[str, Any], hermes_home: str) -> None` (line 206) — write non-secret config to provider-native location (secrets go to `.env`). Default no-op for env-only providers.
  - `on_memory_write(action: str, target: str, content: str) -> None` (line 223) — mirror built-in memory tool writes; `action` ∈ {`'add'`, `'replace'`, `'remove'`}, `target` ∈ {`'memory'`, `'user'`}.

## Key wiring facts

- The `initialize()` `**kwargs` contract is documented in its docstring (lines 62–76) and is the public protocol that `run_agent.py` satisfies:
  - Always: `hermes_home` (str, profile-scoped storage root — providers must NOT hardcode `~/.hermes`), `platform` (str: `"cli"`, `"telegram"`, `"discord"`, `"cron"`, …).
  - Optional: `agent_context` (str: `"primary"`, `"subagent"`, `"cron"`, `"flush"` — providers SHOULD skip writes for non-primary contexts because cron system prompts would corrupt user representations), `agent_identity` (profile name, e.g. `"coder"`), `agent_workspace` (shared workspace name, e.g. `"hermes"`), `parent_session_id` (for subagents), `user_id` (gateway platform user).
- Registration paths (lines 13–15 of docstring): (1) `BuiltinMemoryProvider` is always present and not removable; (2) plugins ship in `plugins/memory/<name>/` and activate via `memory.provider` config.
- `prefetch()` is explicitly called out as needing session scoping (line 99): providers that serve concurrent sessions (gateway group chats, cached agents) should partition by `session_id`; others may ignore it.
- Compression integration: `on_pre_compress()` (line 163) is the hook that lets a memory provider extract insight *before* the compressor discards messages; the returned string is folded into the compressor's summary prompt so provider-extracted insight is preserved across compression events.

## Invariants enforced in this module

- File is a pure ABC — no runtime behavior, no side effects on import.
- Only two symbols are `@abstractmethod` beyond `name`: `is_available` and `initialize` and `get_tool_schemas`. All other methods have default implementations that are safe no-ops or safe empty returns.
- `handle_tool_call` default **raises** `NotImplementedError` rather than returning an error JSON — providers that expose any tool schema MUST override this, or their tools will crash the dispatcher.
- `queue_prefetch` default is no-op (not an error) — providers without background recall simply do nothing.
- Docstring (lines 28–30) codifies: one external provider at a time, built-in always first, built-in not removable. Enforcement lives in `MemoryManager` (a separate module), not this ABC.
- Configuration must support per-profile scoping via `hermes_home` kwarg — providers that persist state must route writes under that path, never `~/.hermes` directly (line 67–68).
- `save_config()` and `get_config_schema()` together form the plugin config contract: providers MUST implement either (a) `save_config()` for a native config file, or (b) pure env-var config with all schema fields carrying `env_var` set and `save_config` left as the default no-op (line 215–219).

## Imports of interest (head of file, lines 31–34)

- `from __future__ import annotations`
- `import logging` (module `logger = logging.getLogger(__name__)`, line 39)
- `from abc import ABC, abstractmethod`
- `from typing import Any, Dict, List`

No runtime dependencies beyond the standard library; the ABC is deliberately minimal so every plugin can import it without pulling heavy tool-registry or provider-specific libraries.

## References

- Source file: `agent/memory_provider.py` (full body is the authoritative source)
- Manager enforcing single-external-provider rule: `agent/memory_manager.py`
- Primary consumer wiring providers into the agent loop: `run_agent.py` (memory-provider init block at lines 1228–1303 per the `run_agent.py` snapshot)
- Example plugin implementation: `plugins/memory/openviking/__init__.py` (captured this batch)
- Built-in memory tool (sibling always-on provider): `tools/memory_tool.py` + `tools/user_memory_tool.py`
- Docstring authoritative reference for kwargs contract and lifecycle order: lines 1–29 of this file
