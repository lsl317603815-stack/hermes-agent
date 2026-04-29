---
title: Memory provider vs Context engine
type: comparison
tags: [memory, context-engine, architecture]
sources:
  - agent/memory_provider.py
  - agent/context_engine.py
  - agent/memory_manager.py
  - run_agent.py
wikilinks_out: [entities/memoryprovider, entities/contextengine, concepts/memory-provider-lifecycle, concepts/agent-loop, entities/aiagent]
last_refreshed: 2026-04-24
refreshed_by: claude-code
---

# Memory provider vs Context engine

## TL;DR

两个长得像、但管两件不同事的可插拔 ABC。**MemoryProvider**（`agent/memory_provider.py:42`）回答「**跨会话**应该记住什么」—— 持久化、召回、facts 抽取、provider-owned 工具；**ContextEngine**（`agent/context_engine.py:32`）回答「**当前会话**如何塞进 context window」—— token 跟踪、压缩时机、压缩执行、engine-owned 工具（LCM 的 `lcm_grep` 等）。两者通过 `on_pre_compress` 单向交汇：provider 向 engine 贡献一段 summary 原料，engine **不**回调 provider。混淆最常见症状：把 "session 历史压得太狠导致找不到早先对话" 当成 memory provider bug（其实是 engine），或把 "再开新会话记不起用户名" 当成 engine bug（其实是 provider）。详见 §区别（vs）。实体页见 [[entities/memoryprovider]] 与 [[entities/contextengine]]；时间线拼接见 [[concepts/memory-provider-lifecycle]]。

## 责任边界

**MemoryProvider 做的：**

- 管 `~/.hermes/<profile>/memory/*.md` 与 external backend（Honcho / Hindsight / Mem0 / OpenViking）的跨会话持久化
- `prefetch(query) → str`（`memory_provider.py:92`）在 API 调用前注入召回上下文
- `sync_turn(user, assistant)` 每轮非阻塞写入
- `on_session_end(messages)` 做 end-of-session facts 抽取
- `get_tool_schemas()` 暴露 memory-specific 工具（例如 `memory`、`viking_search`）；`handle_tool_call` 派发（默认 **raise**）
- 多 provider 同时在场：builtin 永远在 + 至多 1 个 external（`MemoryManager.add_provider` 强制，`agent/memory_manager.py:97`）

**ContextEngine 做的：**

- 跟踪 token：`last_prompt_tokens`、`last_total_tokens`、`threshold_tokens`、`context_length`、`compression_count` 等 6 个类属性（`context_engine.py:55–60`）
- `should_compress(prompt_tokens=None) → bool` 每轮问一次
- `compress(messages, current_tokens) → List[message]` 执行压缩（summary / DAG / 丢旧）
- `update_from_response(usage)` 每次 API 响应后被调
- `get_tool_schemas()` 暴露 engine-specific 工具（LCM 的 `lcm_grep` / `lcm_describe` / `lcm_expand`）；`handle_tool_call` 派发（默认返回 **error JSON**）
- 单 engine 独占：`config.yaml` 的 `context.engine` 指定唯一一个

## 调用链 / 关系

```
                 config.yaml
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
  memory.provider          context.engine
     = "honcho"             = "compressor" | "lcm" | …
         │                         │
         ▼                         ▼
  MemoryManager              ContextCompressor / LCMEngine / …
  (agent/memory_manager.py)  (agent/context_compressor.py / plugin)
         │                         │
         │  add_provider(...)      │  唯一引擎，挂在 AIAgent.context_compressor
         │  builtin + 至多 1 external
         │                         │
         ▼                         ▼
 ┌───────────────── run_agent.py AIAgent ──────────────────┐
 │                                                         │
 │ init:                                                   │
 │   manager.initialize_all(session_id, hermes_home,       │
 │                          platform, agent_context)       │
 │   engine.on_session_start(session_id, ...)              │
 │   (两条路径都传 hermes_home / session_id；参数形状不同) │
 │                                                         │
 │ per-turn (inside run_conversation):                     │
 │   manager.on_turn_start(n, msg)                         │
 │   manager.prefetch_all(q)  ──► 注入 context             │
 │   ...                                                   │
 │   response = provider.chat.completions.create(...)      │
 │   engine.update_from_response(response.usage)           │
 │                                                         │
 │   if engine.should_compress(prompt_tokens):             │
 │      manager.on_pre_compress(messages) ──► str          │
 │                             ╚═ 单向桥；返回串折入         │
 │                                engine.compress 的       │
 │                                summary prompt           │
 │      messages = engine.compress(messages, tokens)       │
 │                                                         │
 │   manager.sync_all(user, final)                         │
 │   manager.queue_prefetch_all(user)                      │
 │                                                         │
 │ true session boundary:                                  │
 │   shutdown_memory_provider(messages):                   │
 │     manager.on_session_end → manager.shutdown_all       │
 │     engine.on_session_end(session_id, messages)         │
 └─────────────────────────────────────────────────────────┘
```

详细时间线见 [[concepts/memory-provider-lifecycle]]；loop 机制见 [[concepts/agent-loop]]。

## 区别（vs）

| 维度 | MemoryProvider | ContextEngine |
|------|----------------|---------------|
| **本质关切** | 跨会话"应该记住什么" | 当前会话"如何塞进 context window" |
| **时间尺度** | 多会话 / 跨天 / 跨设备 | 单会话内，从 turn 1 到压缩事件 |
| **多实例？** | builtin（永远在）+ 至多 1 个 external；由 `MemoryManager.add_provider` 强制（`memory_manager.py:97–120`） | 整个 agent **恰好** 1 个；由 `config.yaml` 的 `context.engine` 指定 |
| **`initialize` 签名** | `initialize(session_id, **kwargs)`，kwargs 必含 `hermes_home` / `platform`，常含 `agent_context` / `user_id` / `agent_identity`（`memory_provider.py:61–80`） | `on_session_start(session_id, **kwargs)`（`context_engine.py:103`）；kwargs 可含 `hermes_home` / `platform` / `model` 但不是强约束 |
| **`handle_tool_call` 默认** | `raise NotImplementedError`（`memory_provider.py:131`）—— 暴露了工具就必须实现 | 返回 `{"error": "Unknown context engine tool: <name>"}` JSON（`context_engine.py:137–147`）—— 误分派不崩 loop |
| **工具进 `self.tools` 路径** | `MemoryManager.get_all_tool_schemas()` 注入，**不**经 [[entities/tool-registry]]（`run_agent.py:1311+`） | 同样**不**经 registry；engine 自己 `get_tool_schemas` 被 agent 合并到 `self.tools`（具体注入点在 agent init 内） |
| **per-turn hook 节奏** | `on_turn_start` + `prefetch_all` + `sync_all` + `queue_prefetch_all`；每个 user turn **一次** | `update_from_response` 每次 API 调用**一次**（tool-call 子轮也算）；`should_compress` 每轮后问一次 |
| **真边界 teardown** | `manager.on_session_end` + `manager.shutdown_all`（`run_agent.py:3189`） | `engine.on_session_end(session_id, messages)`（同函数内，`run_agent.py:3206–3214`） |
| **`on_session_end` per-turn？** | 否 —— 仅真边界（docstring `memory_provider.py:153–160`） | 否 —— 仅真边界（docstring `context_engine.py:18–26`）；两者在这一点**完全一致** |
| **`on_session_reset`** | 无（provider 不负责 reset） | 有（`context_engine.py:117`）；`/new`/`/reset` 只清 4 个 field，不清 `threshold_tokens`/`context_length` |
| **决定压缩？** | **不**决定。provider 只在 `on_pre_compress` 被**动**通知 | 决定。`should_compress` / `should_compress_preflight` 是 engine 的职权 |
| **跨两者的唯一桥** | `on_pre_compress(messages) → str` 返回串进 summary prompt；**单向** | compressor 不回调 provider（见 [[entities/contextengine]] 坑点 §3） |
| **失败隔离** | `MemoryManager` try/except 单 provider；failure 记 log，不崩 agent | engine 失败会冒泡到 loop 错误分类器；更严重 |
| **用户为何切换** | 想换跨会话后端（Honcho → Mem0 → OpenViking） | 想换压缩范式（summary → DAG → LCM） |

## 坑点

- **把压缩后"找不到早先对话"当成 memory bug。** Context engine 压缩把旧 messages 折成 summary，用户看到"它记不住我们几小时前说的话了"—— 这不是 memory provider 的职责范围。provider 管的是**下一个会话**能不能记起这件事；当前会话的历史是 engine 的事。若希望被压缩的洞见跨会话留下，provider 必须实现 `on_pre_compress` 并在里面抽取想保留的事实写到后端 —— 返回的 str 只进 summary prompt，不等于被持久化。
- **把"新会话记不住用户名"当成压缩 bug。** 反过来：跨会话遗失 ≠ 压缩太狠。若重开 CLI 后 provider 不记得你是谁，查 `agent_context`（必须 `"primary"`）、`hermes_home`（必须指向正确 profile 根）、`is_available()`（连接是否通）—— 这些都在 provider / manager 侧，与 engine 无关。
- **两边都暴露工具，但**不共享分派路径**。** memory 工具走 `manager.handle_tool_call`（`agent/memory_manager.py:249`）；engine 工具走 `engine.handle_tool_call`（`context_engine.py:137`）；**两者都**不走 [[entities/tool-registry]] 的 `dispatch`。新增 LCM 工具时不要试图「让它也走 registry」—— `_AGENT_LOOP_TOOLS` 的路由逻辑在 agent loop 顶层拦截；registry 里放 stub 不会解决 engine 工具的分派。
- **`handle_tool_call` 默认行为刻意不对称。** provider `raise` / engine `error JSON` 是合同级差异（`memory_provider.py:131` vs `context_engine.py:137–147`）。provider 暴露工具 = 承诺实现；engine 工具纯可选，不实现就降级。**不要"统一"这两条**（把 engine 也改成 raise，或把 provider 改成 error JSON）—— 会破坏各自的契约：provider 静默返回 error 会让模型误以为工具能用只是这次坏了，engine raise 会让 LCM 插件没实现某工具时直接崩 loop。
- **`on_pre_compress` 是唯一合法 cross-talk 点。** 若你想写一个 engine 做完全不同的压缩（例如丢弃而非总结），你仍**必须**显式决定是否 honor provider 返回的那段文本 —— 忽略它等于静默打破契约（见 [[entities/contextengine]] 坑点 §3）。整个设计的精神是"让 provider 抽出的洞见穿过压缩事件"；engine 侧拒绝之前先确认新语义下"穿过"换成什么。
- **hermes_home 路径穿透两条** —— 但契约形态不同。provider 的 `initialize` **强制**需要 `hermes_home` kwarg（否则 profile-scoped 存储会污染错误目录；docstring `memory_provider.py:67`）；engine 的 `on_session_start` 把 `hermes_home` 塞在 `**kwargs` 里但**不强制**（`context_engine.py:103–108`）。为 LCM 做 profile-scoped DAG 持久化时，要自己从 kwargs 取并校验；不能假设总是有。

## References

- 源：`agent/memory_provider.py:42`（`class MemoryProvider`）、`:61`（`initialize` — 需要 `hermes_home` / `agent_context`）、`:131`（`handle_tool_call` 默认 raise）、`:153`（`on_session_end`）、`:163`（`on_pre_compress` — 桥的 provider 端）
- 源：`agent/context_engine.py:32`（`class ContextEngine`）、`:55–60`（token-state 类属性）、`:66`（`update_from_response`）、`:73`（`should_compress`）、`:77`（`compress`）、`:103`（`on_session_start`）、`:110`（`on_session_end`）、`:117`（`on_session_reset`）、`:137–147`（`handle_tool_call` 默认 error JSON）、`:169`（`update_model`）
- 源：`agent/memory_manager.py:97–120`（`add_provider` single-external）、`:249`（`handle_tool_call`）、`:296`（`on_pre_compress` — 桥的 manager 端）、`:345`（`shutdown_all`）
- 源：`run_agent.py:1261–1302`（provider init）、`:1311+`（provider 工具注入 `self.tools`）、`:3189–3214`（`shutdown_memory_provider` 一并调 engine `on_session_end`）、`:7157`（`on_pre_compress` 触发点）
- Raw 快照：`raw/code-snapshots/agent_memory_provider-20260424.md`、`raw/code-snapshots/agent_context_engine-20260424.md`
- 相关 wiki 页：[[entities/memoryprovider]]、[[entities/contextengine]]、[[concepts/memory-provider-lifecycle]]、[[concepts/agent-loop]]、[[entities/aiagent]]
