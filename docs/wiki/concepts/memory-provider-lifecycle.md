---
title: Memory provider lifecycle
type: concept
tags: [memory, architecture, workflow]
sources:
  - agent/memory_provider.py
  - agent/memory_manager.py
  - run_agent.py
wikilinks_out: [entities/memoryprovider, entities/contextengine, entities/aiagent, concepts/agent-loop, comparisons/memory-provider-vs-context-engine]
last_refreshed: 2026-04-24
refreshed_by: claude-code
---

# Memory provider lifecycle

## TL;DR

这条时间线回答「一个 memory provider 从**进程启动**到**会话终结**会被哪些钩子、按什么顺序、从**哪个调用点**敲到」。总共分三段：(1) **init** —— 进程级 setup（`MemoryManager.initialize_all`，`agent/memory_manager.py:356`）；(2) **per-turn loop** —— 每轮 agent loop 里按序触发 `on_turn_start → prefetch_all → (tool calls, on_memory_write) → sync_all → queue_prefetch_all`；压缩时额外触发 `on_pre_compress`；(3) **真边界 teardown** —— `shutdown_memory_provider`（`run_agent.py:3189`）调 `on_session_end` 再 `shutdown_all`，**仅**在 CLI exit / `/reset` / gateway session expiry 等真边界触发，不是每轮。本页是时间线；契约定义见 [[entities/memoryprovider]]，与 [[entities/contextengine]] 的职责辨析见 [[comparisons/memory-provider-vs-context-engine]]。

## 责任边界

**做什么：**

- **定义每个 hook 的**触发调用点**** —— 不解释契约（那归 [[entities/memoryprovider]]），只画"这个函数在 `run_agent.py` 的哪一行被调"
- **说明调用**顺序保证**** —— 例如 `on_turn_start` 严格发生在 `prefetch_all` **之前**（`run_agent.py:8511` vs `:8527`），provider 借此做 cadence 门控
- **标出"一次性 vs 每轮 vs 真边界"三种节奏**
- **展示父 agent ↔ 子 agent 的 `on_delegation` 跨 agent 时序**

**不做什么：**

- **不复述契约条目** —— 每个 hook 的 signature、默认行为、kwargs 语义见 [[entities/memoryprovider]]
- **不做 provider 内部设计建议** —— OpenViking 等具体实现见 `plugins/memory/*`（entity 页在 backlog）
- **不涉及 context engine 内部细节** —— 只在 `on_pre_compress` 交汇点展示交互；engine 自己的生命周期见 [[entities/contextengine]]
- **不包含 BuiltinMemoryProvider 的专属逻辑** —— builtin 跑在 MemoryManager 第一位，与 external 共用接口；两者差异放 entity 页

## 调用链 / 关系

### 1. Init（进程启动 / agent `__init__`）

```
run_agent.py AIAgent.__init__ (~:552)
        │
        │  mem_config.get("provider")  ── 空 ⇒ 跳过整段；自动迁移 Honcho 例外（:1237–1256）
        │
        ▼
run_agent.py:1261   MemoryManager()                    ── agent/memory_manager.py:83
run_agent.py:1262   load_memory_provider(name)         ── plugins/memory/__init__.py:159
run_agent.py:1264   manager.add_provider(_mp)          ── memory_manager.py:97
                    ├─ builtin 永远先在；非 builtin 第二个被 reject + warn
                    └─ _tool_to_provider 索引 schema → provider 的工具路由表
run_agent.py:1265   if manager.providers:              ── 至少 1 个 provider 在场
run_agent.py:1268      _init_kwargs = {
                          "session_id":    self.session_id,
                          "platform":      platform or "cli",
                          "hermes_home":   str(get_hermes_home()),  # 来自 hermes_constants
                          "agent_context": "primary",               # subagent/cron 入口会改值
                          # 条件附加：
                          "session_title":        from _session_db
                          "user_id":              gateway 注入
                          "gateway_session_key":  gateway 注入
                          "agent_identity":       active profile
                          "agent_workspace":      "hermes"
                      }
run_agent.py:1296      manager.initialize_all(**_init_kwargs)  ── memory_manager.py:356
                       ├─ 对每个 provider 调 provider.initialize(session_id, **kwargs)
                       └─ 失败不传染（失败 provider 从 providers list 移除，不崩进程）

run_agent.py:1311  self.tools is not None:          ── 工具快照注入
                    └─ for schema in manager.get_all_tool_schemas() (memory_manager.py:223):
                          跳过已被 plugin 注册的同名工具（dedupe）
                          self.tools.append({"type":"function","function":schema})
                          self.valid_tool_names.add(name)
```

### 2. Per-turn loop（每轮 `run_conversation`）

```
run_agent.py run_conversation (~:8169)
        │
        │  build system prompt（含 manager.build_system_prompt() — memory_manager.py:157）
        │         每轮重建；拼入 provider 的 system_prompt_block() 结果
        │
        ▼
run_agent.py:8511   manager.on_turn_start(turn_number, user_msg)   ── memory_manager.py:271
                                   ╚═ 严格发生在 prefetch_all 之前
                                      provider 借此做 contextCadence / dialecticCadence
run_agent.py:8527   _ext_prefetch_cache = manager.prefetch_all(query)  ── memory_manager.py:178
                                   ╚═ **一次性**；缓存被整个 while 循环复用
                                      避免 N 次 tool call 触发 N 次远端召回
        │
        ▼  (while api_call_count < max_iterations …)
        │
        │  model → tool_calls (if any)
        │
        ├─► memory 工具名 in _tool_to_provider:
        │     run_agent.py:7317 / :7868  manager.handle_tool_call(...)   ── memory_manager.py:249
        │                                   路由到对应 provider.handle_tool_call
        ├─► builtin memory 工具 (action in add/replace):
        │     run_agent.py:7307–7316 / :7790–7798  manager.on_memory_write(action, target, content)
        │                                   ── memory_manager.py:315
        │                                   provider 镜像 built-in 写入到自己后端
        │
        │  （若上下文压缩触发）
        ├─► run_agent.py:7157  manager.on_pre_compress(messages)       ── memory_manager.py:296
        │                                   provider 返回 str 折入 compressor summary prompt
        │                                   这是 provider → context engine 的**唯一**桥
        │                                   详见 [[entities/contextengine]]
        │
        │  （若子 agent 通过 delegate_task 完成）
        └─► parent agent: manager.on_delegation(task, result, child_session_id)
                                               ── memory_manager.py:331
                                               父 provider 观察 subagent 结果
                                               subagent 侧 skip_memory=True，无 provider session

        ▼  (tool_calls 耗尽，生成 final_response)
run_agent.py:11263  manager.sync_all(user_msg, final_response)       ── memory_manager.py:210
                                   非阻塞写入；后端有延迟应内部排队
run_agent.py:11264  manager.queue_prefetch_all(user_msg)              ── memory_manager.py:197
                                   后台起**下一轮**召回（返回时由 prefetch_all 取走）
```

### 3. 真边界 teardown

`run_conversation()` 返回**不**触发 teardown（多轮会话共享 provider 状态）。仅以下路径才调：

```
CLI exit / atexit ────┐
/reset command ──────┼──► AIAgent.shutdown_memory_provider(messages)   ── run_agent.py:3189
gateway session      │       │
  expiry ────────────┤       ├─► manager.on_session_end(messages)       ── memory_manager.py:285
                     │       │       provider 做 end-of-session 抽取（facts、summary）
                     │       │
                     │       ├─► manager.shutdown_all()                  ── memory_manager.py:345
                     │       │       provider 关连接、flush 队列、kill background threads
                     │       │
                     │       └─► context_compressor.on_session_end(session_id, messages)
                     │                   engine 自己的真边界，不由 manager 负责
                     │
/new 或长会话         │
  session_id 轮换 ───┴──► AIAgent.commit_memory_session(messages)        ── run_agent.py:3216
                             只调 manager.on_session_end；**不**调 shutdown_all
                             provider 继续在旧 session_id 下活着
```

## 坑点

- **`run_conversation` 不是 session 终点。** 一个 CLI / gateway 会话里会跑**多次** `run_conversation`（每条用户消息一次）。把 `on_session_end` 当作"每次对话结束"调是最常见误解 —— 它只在**真**边界触发（CLI atexit、`/reset`、gateway session expiry；docstring `agent/memory_provider.py:153–160`）。一旦 per-turn 调了 shutdown，provider 的连接池 / 后台线程会被杀，第二条消息直接踩空指针。
- **`on_turn_start` 必须发生在 `prefetch_all` 之前。** `run_agent.py:8511 → 8527` 是强制顺序 —— provider 用 `on_turn_start` 递增内部 turn counter，`prefetch_all` 才能按 `contextCadence`（例如"每 5 轮才刷一次 profile"）门控。若你改 loop 顺序把 `prefetch_all` 提前，provider 侧 cadence 判断基于**上一轮**的 counter，漂移一轮。源内注释 `:8510` 明说「Must happen BEFORE prefetch_all()」。
- **`prefetch_all` 的缓存贯穿整个 tool loop。** `_ext_prefetch_cache`（`run_agent.py:8523`）只在 `run_conversation` 入口计算一次，之后每次 API 调用 reuse。这是刻意设计 —— 10 个 tool call 不应触发 10 次远端召回（10× 延迟与费用）。provider 侧不要假设 `prefetch(query)` 每轮都被调；它每 user-turn 只调一次，tool-call sub-turns 不触发。
- **`on_memory_write` 只对 builtin memory 工具触发。** 当 agent 调 `memory(action=add/replace/...)` 时才分派（`run_agent.py:7307–7316`）；**不是**每次 provider 内部写入都被镜像。若 provider 自己有工具做写入（例如 `viking_add_memory`），那是走 `handle_tool_call` 的 provider-native 路径，不二次触发 `on_memory_write`。
- **初始化 kwargs 里的 `agent_context` 决定写入策略。** `"primary"`（`run_agent.py:1271`）= 真实用户会话；`"subagent"` / `"cron"` / `"flush"` 在其它入口被填（subagent spawn、cronjob trigger、`/flush` 手动扫 memory）。provider 必须在 `initialize` 里读 `kwargs["agent_context"]`（`agent/memory_provider.py:70`）并对非 primary 上下文**跳过写入** —— cron 触发时生成的 system prompt 与 tool results 若被当成用户画像存到记忆，是致命污染。OpenViking 的处理见 `plugins/memory/openviking/__init__.py:320+`（`initialize` 内读 `agent_context` 并设 `_is_readonly` 标志）。
- **`on_pre_compress` 返回值只单向进 summary prompt。** compressor 把这段文本折入 LLM 的总结指令，但**不**反馈"最终保留了哪些内容"给 provider。若 provider 想做双向一致（例如"若这条洞见被丢弃，留到下次 sync 里手动存"），必须在 `sync_turn` 里自行复制；压缩事件之后 `messages` 已经是压缩后的列表。与 engine 的契约见 [[entities/contextengine]] 坑点 §3。
- **`on_session_end` 与 `commit_memory_session` 的区分。** 都调 `manager.on_session_end`，但 `shutdown_memory_provider`（`run_agent.py:3189`）多一步 `shutdown_all`（关资源、kill 后台线程），而 `commit_memory_session`（`:3216`）**只**做抽取、provider 继续活着。`/new` 与压缩触发的 session_id 轮换走后者；真的进程退出走前者。改动这段代码时要保持两条路径的**资源释放语义**不同。

## References

- 源：`agent/memory_provider.py:42`（`class MemoryProvider`）、`:61`（`initialize`）、`:70`（`agent_context` 语义）、`:114`（`sync_turn`）、`:131`（`handle_tool_call` 默认 raise）、`:144`（`on_turn_start`）、`:153`（`on_session_end`）、`:163`（`on_pre_compress`）、`:175`（`on_delegation`）、`:223`（`on_memory_write`）
- 源：`agent/memory_manager.py:83`（`class MemoryManager`）、`:97`（`add_provider` — single-external enforcement）、`:157`（`build_system_prompt`）、`:178`（`prefetch_all`）、`:197`（`queue_prefetch_all`）、`:210`（`sync_all`）、`:223`（`get_all_tool_schemas`）、`:249`（`handle_tool_call`）、`:271`（`on_turn_start`）、`:285`（`on_session_end`）、`:296`（`on_pre_compress`）、`:315`（`on_memory_write`）、`:331`（`on_delegation`）、`:345`（`shutdown_all`）、`:356`（`initialize_all`）
- 源：`run_agent.py:1261–1302`（init 段）、`:1311+`（tool schema 注入）、`:3189`（`shutdown_memory_provider`）、`:3216`（`commit_memory_session`）、`:3427`（system prompt 拼接）、`:7157`（`on_pre_compress` 触发点）、`:7307–7316` / `:7790–7798`（`on_memory_write` 触发点）、`:7317` / `:7868+`（`handle_tool_call` 路由）、`:8511`（`on_turn_start`）、`:8527`（`prefetch_all`）、`:11263–11264`（`sync_all` + `queue_prefetch_all`）
- 源：`plugins/memory/__init__.py:159`（`load_memory_provider`）
- Raw 快照：`raw/code-snapshots/agent_memory_provider-20260424.md`、`raw/code-snapshots/openviking_plugin-20260424.md`
- 相关 wiki 页：[[entities/memoryprovider]]、[[entities/aiagent]]、[[concepts/agent-loop]]、[[entities/contextengine]]、[[comparisons/memory-provider-vs-context-engine]]
