---
title: Agent loop
type: concept
tags: [agent-core, architecture, workflow]
sources:
  - run_agent.py
  - model_tools.py
  - AGENTS.md
wikilinks_out: [entities/aiagent, queries/how-tools-enter-the-model-surface]
last_refreshed: 2026-04-24
refreshed_by: claude-code
---

# Agent loop

## TL;DR

**Agent loop** 指 `AIAgent.run_conversation()`（`run_agent.py:8169`）内的 while 循环：每一轮 = 「调模型 → 若有 tool_calls 则执行并 append 结果 → 再调模型」。循环终止于「模型不再要工具」或「迭代上限 / 预算耗尽 / 被外部 interrupt」。它是 Hermes 的核心执行模型 —— 任何 CLI / gateway / ACP 对话最终都在这个循环里度过。本页只讲**机制**；实例化方见 [[entities/aiagent]]，工具进入 `self.tools` 的路径见 [[queries/how-tools-enter-the-model-surface]]。

## 责任边界

**做什么：**

- 维持一个 `messages` 列表（OpenAI 格式），每轮 API 响应与工具结果都 append 进去
- 把 `self.tools`（init 时从 registry 过滤而来）作为 API 请求的 `tools=` 参数传入
- 分派 `tool_calls`：多工具 / 独立工具走并发路径，交互 / 单工具 / 路径冲突走顺序路径
- 维护三个独立闸：`api_call_count < max_iterations`、`iteration_budget.remaining > 0`、`_interrupt_requested` —— 任一触发即退出
- 调度持久化副作用：trajectory / session log / memory commit / rate-limit capture

**不做什么：**

- **不管 provider 切换** —— HTTP 封装在 provider adapters（`agent/anthropic_adapter.py` 等）
- **不管工具实现** —— 工具逻辑在 `tools/*.py`；loop 只负责分派
- **不做 compaction 决策** —— 上下文压缩由 `agent/context_engine.py` 在合适时机**被** loop 调用，策略不归 loop
- **不做 memory 决策** —— loop 只在 lifecycle 点通知 [[entities/memoryprovider]]；读写策略在 provider 内

## 调用链 / 关系

核心伪代码（源自 `AGENTS.md:108-122`「Agent Loop」章节，与 `run_agent.py:8169+` 语义一致）：

```python
while api_call_count < self.max_iterations and self.iteration_budget.remaining > 0:
    response = client.chat.completions.create(
        model=model, messages=messages, tools=self.tools,
    )
    if response.tool_calls:
        for tool_call in response.tool_calls:
            result = handle_function_call(tool_call.name, tool_call.args, task_id)
            messages.append(tool_result_message(result))
        api_call_count += 1
    else:
        return response.content
```

分派路径（实际实现比伪代码多一层并发/顺序分流）：

```
run_conversation (run_agent.py:8169)
       │
       ├─► provider API call (tools=self.tools)
       │       │
       │       ▼
       │   response.tool_calls? ──► No:  return final content
       │       │ Yes
       │       ▼
       ├─► _execute_tool_calls (run_agent.py:7235)
       │       │
       │       ├─► _execute_tool_calls_concurrent (run_agent.py:7370)   ──┐
       │       │     （只读 / 路径不冲突 / 独立批量）                       │
       │       │                                                            ├─► handle_function_call
       │       └─► _execute_tool_calls_sequential (run_agent.py:7637)    ──┘   (model_tools.py:421)
       │             （交互 / 单工具 / 路径冲突批量）                            │
       │                                                                        ▼
       │                                                     ┌─ 普通工具：执行、返回结果
       │                                                     └─ _AGENT_LOOP_TOOLS:
       │                                                        {todo, memory, session_search,
       │                                                         delegate_task} —— agent loop
       │                                                        自己拦截；registry stub 兜底
       │
       └─► append tool_result messages → 回到 while 顶
```

每一轮的"出口"都有对应的持久化 hooks：trajectory append（`_convert_to_trajectory_format`，`run_agent.py:2593`）、session log flush（`_flush_messages_to_session_db`，`run_agent.py:2490`）、rate-limit 读回（`_capture_rate_limits`，`run_agent.py:3148`）。这些是"旁路"，不影响主循环控制流。

## 坑点

- **并发 vs 顺序不是你能手工选的。** `_execute_tool_calls` 根据 tool 名字 / 参数（例如写入路径是否重叠）自动切分。新增文件类工具时务必考虑「与其他 file 工具并发跑时，冲突判定能否识别你的目标路径」—— 否则可能因并发写同一文件踩坑。
- **Agent-loop tools 只走顺序分派。** `_AGENT_LOOP_TOOLS`（`model_tools.py:326`）里的 4 个工具**必须**在 agent loop 中执行；`handle_function_call` 对它们只返回 stub 错误作兜底。若你试图在 `tools/*.py` 里"实现"这 4 个中的某一个的执行逻辑，属于误读契约 —— 改动会被 stub 吞掉或在并发路径上破坏 agent 级状态。
- **API 响应 `content` 与 `tool_calls` 可能并存。** 某些 provider（尤其是 Anthropic）会在同一轮同时给出文字与 `tool_calls`；loop 在执行 `tool_calls` 后仍保留 `content` 作为 assistant 消息的一部分。外部若想"捕获最终回复"，要区分「loop 退出点的 content」与「中间轮的 content」，别直接取最后一个 assistant 消息。
- **过早的 `break` / `raise` 吞掉 retry。** 错误分类器（`agent/error_classifier.py`）会把某些 transient API 错误拆包成 retry；若你改 loop 结构，务必保留 retry 路径。直接硬中断会让系统丢掉原本能优雅恢复的状况。
- **`iteration_budget` 跨 `run_conversation` 累积，不是每次重置。** gateway 一个长 session 里 10 轮对话共享同一 budget；把 `max_iterations` 当作"每次对话上限"是误解 —— 它只是单次 run 的硬上限。

## References

- 源：`run_agent.py:8169` (`run_conversation`)、`run_agent.py:7235` (`_execute_tool_calls`)、`run_agent.py:7370` (并发)、`run_agent.py:7637` (顺序)
- 源：`model_tools.py:196` (`get_tool_definitions` —— 决定 `self.tools` 持有哪些 schema)、`model_tools.py:326` (`_AGENT_LOOP_TOOLS`)、`model_tools.py:421` (`handle_function_call`)
- 权威伪代码：`AGENTS.md:108-122`「Agent Loop」
- 相关 wiki 页：[[entities/aiagent]]、[[queries/how-tools-enter-the-model-surface]]
