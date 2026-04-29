---
title: AIAgent
type: entity
tags: [agent-core, architecture]
sources:
  - run_agent.py
  - AGENTS.md
wikilinks_out: [concepts/agent-loop, queries/how-tools-enter-the-model-surface, entities/tool-registry, concepts/memory-provider-lifecycle]
last_refreshed: 2026-04-24
refreshed_by: claude-code
---

# AIAgent

## TL;DR

`AIAgent`（定义于 `run_agent.py:535`）是 Hermes 顶层 agent 类：它**协调一次对话**的所有环节 —— 拼装 system prompt、调模型、解析 `tool_calls`、分派工具执行、把结果喂回下一轮 API，直到模型不再要求工具调用或达到迭代上限。它不是模型，不是 memory provider，也不是 context engine；它是**把这些东西串起来**的那个对象。所有 CLI / gateway / ACP 入口最终都实例化一个 `AIAgent`。

## 责任边界

**做什么：**

- **构造阶段（`__init__`，`run_agent.py:552`）** —— 根据 `enabled_toolsets` / `disabled_toolsets` 调 `get_tool_definitions(...)`（`run_agent.py:1086`）拿到过滤后的工具 schema，存到 `self.tools`；挂接 memory provider、context engine、provider client 等外围依赖
- **对话阶段（`run_conversation`，`run_agent.py:8169`）** —— 驱动 while 循环（见 [[concepts/agent-loop]]）
- **工具派发** —— 把模型返回的 `tool_calls` 路由到 `_execute_tool_calls_concurrent`（`run_agent.py:7370`）或 `_execute_tool_calls_sequential`（`run_agent.py:7637`），最终调 `model_tools.handle_function_call`
- **生命周期 hooks** —— 按 lifecycle 调用 [[entities/memoryprovider]]（commit / shutdown）与 context engine（compaction trigger），完整时序见 [[concepts/memory-provider-lifecycle]]
- **持久化副作用** —— trajectory（`_save_trajectory`）、session log（`_save_session_log`）、中断/恢复（`interrupt` / `clear_interrupt`）、rate-limit 捕获

**不做什么：**

- **不是 inference provider** —— 不直接封 HTTP；provider 适配在 `agent/anthropic_adapter.py` / `agent/bedrock_adapter.py` / `agent/copilot_acp_client.py` 等，AIAgent 只持有 client 句柄
- **不是 memory provider** —— 不定义记忆存储；只按契约调用 `agent/memory_provider.py` 暴露的钩子
- **不是 context engine** —— 不决定 compaction 策略；只调用 `agent/context_engine.py`
- **不是 tool 实现** —— 工具逻辑在 `tools/*.py`；AIAgent 只派发，不实现
- **不直接定义 toolset** —— toolset 定义在 `toolsets.py`；AIAgent 只接收 `enabled_toolsets` 参数，init 时一次性 resolve

## 调用链 / 关系

```
┌────────── caller ──────────┐
│  cli.py / gateway/* / acp  │
└───────────┬────────────────┘
            │ AIAgent(enabled_toolsets=..., provider=..., ...)
            ▼
┌────────── AIAgent.__init__ (run_agent.py:552) ──────────┐
│  self.tools = get_tool_definitions(enabled_toolsets)    │──► [[entities/tool-registry]]
│  self.memory_provider = ... (optional)                  │──► [[concepts/memory-provider-lifecycle]]
│  self.context_engine  = ... (optional)                  │
│  self.enabled_toolsets / disabled_toolsets 存储          │
└───────────┬─────────────────────────────────────────────┘
            │ .run_conversation(user_message, ...)
            ▼
┌────────── run_conversation (run_agent.py:8169) ─────────┐
│  while api_call_count < max_iterations                  │
│        and iteration_budget.remaining > 0:              │
│    response = provider.chat.completions.create(         │
│        tools=self.tools, messages=messages)             │
│    if response.tool_calls:                              │
│        self._execute_tool_calls(...)  ──────────────────┼──► handle_function_call
│    else:                                                │     (model_tools.py:421)
│        return final_response                            │
└─────────────────────────────────────────────────────────┘
```

更完整的循环语义见 [[concepts/agent-loop]]；工具从 registry 到 `self.tools` 的三道门见 [[queries/how-tools-enter-the-model-surface]]。

## 坑点

- **`self.tools` 是 init 时快照，不是动态视图。** 若外部（例如 plugin `ctx.register_tool()`）在 agent 已创建后才注册新工具，当前 agent 看不到。CLI 在 reload 路径显式 `self.agent.tools = get_tool_definitions(...)` 重置（`cli.py:6633`、`acp_adapter/server.py:192`）。做集成时若期望运行时新增工具，必须显式重置 `self.tools`。
- **内部工具 vs 模型可见工具。** `_AGENT_LOOP_TOOLS = {"todo", "memory", "session_search", "delegate_task"}`（`model_tools.py:326`）这 4 个工具的**执行**被 agent loop 拦截（它们需要 agent 级状态：TodoStore / MemoryStore / delegate spawning）；registry 里照常有 schema。新增需要 agent 级状态的工具时，**必须**同步改 agent loop 分派逻辑，否则 `handle_function_call` 只会返回 stub 错误。
- **AIAgent 是同步的。** `run_conversation()` 的主循环是纯同步调用；异步只出现在工具内部（经 `_get_tool_loop()` / `_get_worker_loop()`）。不要在外层 `await` 整个 agent —— 它不是 coroutine。
- **`max_iterations` 与 `iteration_budget` 是两个独立的闸。** `max_iterations=90` 默认值只限单次 `run_conversation`；`iteration_budget` 跨多次 run（gateway 长会话）累积。两者任一耗尽都会中止循环。把 `max_iterations` 当作"每次对话上限"是常见误解。

## References

- 源：`run_agent.py:535` (`class AIAgent`)、`run_agent.py:552` (`__init__`)、`run_agent.py:1086` (`self.tools = ...`)、`run_agent.py:8169` (`run_conversation`)、`run_agent.py:7235` (`_execute_tool_calls`)
- 源：`AGENTS.md:85` 起「AIAgent」权威公共契约
- 相关 wiki 页：[[concepts/agent-loop]]、[[queries/how-tools-enter-the-model-surface]]
- 未来页（Phase 1/2 建，现为 forward wikilink）：[[entities/tool-registry]]、[[concepts/memory-provider-lifecycle]]
