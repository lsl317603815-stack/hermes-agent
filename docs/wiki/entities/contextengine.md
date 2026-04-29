---
title: ContextEngine
type: entity
tags: [context-engine, architecture]
sources:
  - agent/context_engine.py
wikilinks_out: [entities/aiagent, concepts/agent-loop, entities/memoryprovider, comparisons/memory-provider-vs-context-engine]
last_refreshed: 2026-04-24
refreshed_by: claude-code
---

# ContextEngine

## TL;DR

`ContextEngine`（`agent/context_engine.py:32`）是 Hermes **上下文窗口管理**的抽象基类。每个 `AIAgent` 实例**恰好**挂一个引擎，选型由 `config.yaml` 的 `context.engine` 字段决定（默认 `"compressor"` → 内置 `ContextCompressor`；替代实现位于 `plugins/context_engine/<name>/`）。引擎负责三件事：**跟踪 token 使用量**、**决定何时压缩**、**执行压缩**（可选还暴露 agent 可见工具，如 LCM 的 `lcm_grep`）。它与 [[entities/memoryprovider]] 是邻而不同的两个契约：memory 管"跨会话记得什么"；context engine 管"当前会话如何塞进 context window"。职责辨析见 [[comparisons/memory-provider-vs-context-engine]]。

## 责任边界

**做什么：**

- **跟踪 token 状态** —— 6 个类属性必须维护：`last_prompt_tokens`、`last_completion_tokens`、`last_total_tokens`、`threshold_tokens`、`context_length`、`compression_count`（`agent/context_engine.py:55–60`）。`run_agent.py` **直接**读这些属性（不走 getter），每轮 API 响应后引擎必须在 `update_from_response(usage)`（`:66`）里写新。
- **决定何时压缩** —— `should_compress(prompt_tokens=None)`（`:73`，abstract）每轮后被问一次；返回 True 即触发 `compress()`。可选 `should_compress_preflight(messages)`（`:93`）做 API 调用前的粗估，默认返回 False（跳过 preflight）。
- **执行压缩** —— `compress(messages, current_tokens=None)`（`:77`，abstract）是主入口：拿到完整消息列表，返回任意长度的**合法 OpenAI-format** 消息序列。如何压缩（总结 / DAG / 丢旧）由实现自定；仅约束返回 shape。
- **可选暴露工具** —— `get_tool_schemas()`（`:129`，默认 `[]`）返回引擎自己的工具 schema；`handle_tool_call(name, args, **kwargs)`（`:137`，默认 error JSON）分派。LCM 引擎通过这条暴露 `lcm_grep`、`lcm_describe`、`lcm_expand`。
- **模型切换响应** —— `update_model(model, context_length, ...)`（`:169`）在换模型 / fallback 激活时被调；默认实现重算 `threshold_tokens = int(context_length * threshold_percent)`（`:182–183`）。

**不做什么：**

- **不拼 system prompt** —— system prompt 来源在 `run_agent.py` 的组装阶段；engine 不参与
- **不替代 memory provider** —— 跨会话持久化归 [[entities/memoryprovider]]；engine 只管当前会话 message 列表的"瘦身"
- **不决定 API 调用时机** —— agent loop（[[concepts/agent-loop]]）按自己的节奏跑；engine 只被动响应 `update_from_response` / `should_compress` 询问
- **`on_session_end` 不是 per-turn** —— 只在真会话边界（CLI exit、`/reset`、gateway expiry）触发（docstring `:18–26`）。per-turn 逻辑写在 `update_from_response` 里
- **默认工具分派不 `raise`** —— 与 memory provider 的 `handle_tool_call` 默认 `raise NotImplementedError` 相反，context engine 默认返回 `json.dumps({"error": f"Unknown context engine tool: {name}"})`（`:147`），让误分派降级不崩 loop

## 调用链 / 关系

```
config.yaml  context.engine = "compressor" | "<plugin name>"
        │
        ▼
run_agent.py  engine = <selected engine>()
   │
   ├─► engine.on_session_start(session_id, hermes_home, platform, model, ...)
   │
   ▼  (loop; 每轮)
[[concepts/agent-loop]]
   │
   ├─► [可选] engine.should_compress_preflight(messages)  ── True 时压缩
   ├─► response = provider.chat.completions.create(...)
   ├─► engine.update_from_response(response.usage)        # 更新 6 个类属性
   ├─► if engine.should_compress(prompt_tokens):
   │       ┌─► [[entities/memoryprovider]].on_pre_compress(messages)  # 桥：拿 provider 洞见
   │       │        │ 返回字符串折入 summary prompt
   │       └─► messages = engine.compress(messages, current_tokens)
   │                 │   ── 新 messages 序列，engine.compression_count += 1
   ├─► [可选] tool_calls 含 engine 自己的工具 → engine.handle_tool_call(...)
   │
   ▼  (session 结束)
engine.on_session_end(session_id, messages)   # CLI exit / /reset / gateway expiry
engine.on_session_reset()                     # /new 或 /reset：reset 4 字段
```

`on_session_reset()`（`:117–125`）**只**清 4 个 field：`last_prompt_tokens`、`last_completion_tokens`、`last_total_tokens`、`compression_count`；**不**清 `threshold_tokens` 与 `context_length` —— 那两者是 model-scoped，跟着当前模型走，不该被 session reset 抹掉。

## 坑点

- **类属性是 shared default，不是 per-instance。** 6 个 token-state field（`agent/context_engine.py:55–60`）与 3 个 compaction-parameter（`:68–70`）都是**类属性**。子类若不在 `__init__` 里显式 `self.foo = 0` 覆盖，多实例会共享 default 直到首次写；并发场景会交叉污染。内置 `ContextCompressor` 在 `__init__` 里 shadow 了这些字段。
- **`handle_tool_call` 默认不 `raise`** —— 与 [[entities/memoryprovider]] 的 `handle_tool_call` 默认 `raise NotImplementedError` 完全相反（`:137` vs memory_provider `:131`）。这是刻意设计：memory provider 暴露工具等于承诺实现；context engine 的工具是纯可选，不实现就返回 error JSON 保持 agent loop 不崩。
- **`update_model` 的后置条件必须保留。** 默认实现（`:169–183`）做且仅做：写 `context_length`、重算 `threshold_tokens = int(context_length * threshold_percent)`。子类 override 若新增逻辑（例如重算 DAG 预算、切换 summary 模型），必须**保留** `threshold_tokens` 的后置条件 —— 否则下次 `should_compress` 用旧阈值判断新 context_length，压缩时机漂移。
- **`on_pre_compress` 是 memory provider 向 context engine 的**单向**桥。** 流程：压缩前 agent 先调 memory provider 的 `on_pre_compress(messages)` → 拿返回字符串 → 喂给 engine 的 `compress()` 作为 summary prompt 辅料。engine 侧**不**回调 memory provider。若你实现新的 engine 做完全不同的压缩范式（例如丢弃而非 summary），必须显式决定是否 honor 这条 provider 返回串 —— 整个 contract 的精神是"让 memory provider 的洞见穿过压缩事件"，忽略它等于静默打破与 memory provider 的集成。
- **`get_status()` 的 `usage_percent` 会被 clip 到 100。** `:160–163` 写明 `min(100, last_prompt_tokens / context_length * 100)` 且 `context_length == 0` 时返回 0。监控脚本读此值不会溢出，但也不要用它做"超载多少"的度量 —— 超载区域（>100%）被平掉了。

## References

- 源：`agent/context_engine.py:32`（`class ContextEngine(ABC)`）、`:39`（`name`）、`:55–60`（token-state 类属性）、`:66`（`update_from_response`）、`:68–70`（compaction 参数默认）、`:73`（`should_compress`）、`:77`（`compress`）、`:93`（`should_compress_preflight`）、`:103`（`on_session_start`）、`:110`（`on_session_end`）、`:117`（`on_session_reset`）、`:129`（`get_tool_schemas`）、`:137`（`handle_tool_call` 默认 error JSON）、`:151`（`get_status`）、`:169`（`update_model`）
- Raw 快照：`raw/code-snapshots/agent_context_engine-20260424.md`
- 相关 wiki 页：[[entities/aiagent]]、[[concepts/agent-loop]]、[[entities/memoryprovider]]
- 未来页（Phase 1 建，现为 forward wikilink）：[[comparisons/memory-provider-vs-context-engine]]
- 内置默认实现（Phase 1 建 entity）：`agent/context_compressor.py`（未建 wiki 页，暂无 forward wikilink）
