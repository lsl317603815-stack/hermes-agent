---
title: MemoryProvider
type: entity
tags: [memory, plugins, architecture]
sources:
  - agent/memory_provider.py
  - plugins/memory/openviking/__init__.py
wikilinks_out: [entities/aiagent, entities/contextengine, entities/tool-registry, concepts/memory-provider-lifecycle, comparisons/memory-provider-vs-context-engine]
last_refreshed: 2026-04-24
refreshed_by: claude-code
---

# MemoryProvider

## TL;DR

`MemoryProvider`（`agent/memory_provider.py:42`）是 Hermes **外部记忆后端**的抽象基类。Honcho / Hindsight / Mem0 / OpenViking 等插件通过继承它把跨会话记忆能力接入 agent。**任一时刻至多一个 external provider 生效**，与**永远在场**的 built-in memory（`MEMORY.md` / `USER.md`）并存 —— 后者是 `BuiltinMemoryProvider`，不可被替换或移除。本页是契约本身；OpenViking 作为当前满实现样例已在原始快照 `raw/code-snapshots/openviking_plugin-20260424.md` 中登记，后续若需要可单独升格为实体页。完整生命周期拼接见 [[concepts/memory-provider-lifecycle]]。它不是 compaction 引擎（那是 [[entities/contextengine]]），也不把自己的工具注入 [[entities/tool-registry]]。

## 责任边界

**做什么：**

- **声明身份与可用性** —— 4 个 `@abstractmethod`：`name`（property，`agent/memory_provider.py:47`）、`is_available()`（`:53`）、`initialize(session_id, **kwargs)`（`:61`）、`get_tool_schemas()`（`:122`）。`is_available()` **只**做配置 + 依赖检查，不发网络请求（docstring `:54–58`）；连接与资源创建全归 `initialize()`。
- **挂接 lifecycle hooks** —— `initialize` / `shutdown`（`:139`）做进程级 setup / teardown；`sync_turn`（`:114`）每轮结束非阻塞写；`prefetch` / `queue_prefetch`（`:92` / `:106`）两段式：后者在当前 turn 末尾后台启动召回，前者在下一 turn 开始**前**取回缓存并拼进 context
- **向 agent 暴露工具** —— `get_tool_schemas()` 返回 OpenAI function-calling 格式 schema；模型触发时 `handle_tool_call(tool_name, args)`（`:131`）被分派。provider 自己持有工具语义，**不经过** `tools/registry.py` 的 `register()`
- **桥接 context engine** —— `on_pre_compress(messages)`（`:163`）是 provider → compressor 的**唯一**接口：返回的文本会折入 compressor 的 summary prompt，使 provider 抽出的洞见穿过压缩事件得以保留
- **配置契约** —— `get_config_schema()`（`:188`）给 `hermes memory setup` wizard 列字段；`save_config(values, hermes_home)`（`:206`）写非 secret 配置到 provider 原生位置（secrets 一律去 `.env`）

**不做什么：**

- **不替代 built-in memory** —— docstring `:13–15` 明说 `BuiltinMemoryProvider` 永远第一位、不可移除；external 是叠加不是替换
- **不决定压缩策略** —— 压缩由 [[entities/contextengine]] 在需要时调用；provider 只通过 `on_pre_compress` 被动通知与贡献摘要材料
- **不拼完整 system prompt** —— `system_prompt_block()`（`:83`）只返回 provider 自己的**静态**文本；per-turn 动态召回归 `prefetch()`
- **不硬编码路径** —— 所有 profile-scoped 存储**必须**落在 `initialize` kwargs 里的 `hermes_home`（`:67`），由 `get_hermes_home()` 解析当前 profile；`~/.hermes` 字面量禁止出现在 plugin 代码里
- **不做单机 fallback** —— 单 external provider 约束由 `MemoryManager` 裁决；plugin 侧不要自行做 "A 不在就退回 B" 的逻辑

## 调用链 / 关系

```
config.yaml  memory.provider = "<name>"
        │
        ▼
MemoryManager (agent/memory_manager.py)
   │  provider.is_available() ── False: 跳过激活
   │  provider.initialize(session_id,
   │                      hermes_home=<profile root>,
   │                      platform="cli|telegram|discord|cron|...",
   │                      agent_context="primary|subagent|cron|flush",
   │                      agent_identity, agent_workspace,
   │                      parent_session_id, user_id, ...)
   ▼
[[entities/aiagent]] / run_agent.py  lifecycle 分派点
   │
   ├─► on_turn_start(turn_number, message, **kwargs)       # 每轮开始
   ├─► prefetch(query, session_id)                         # API 调用前
   ├─► [ model call → tool_calls → handle_tool_call(...) ] # 若 get_tool_schemas 非空
   ├─► sync_turn(user_content, assistant_content)          # 每轮结束（非阻塞）
   ├─► queue_prefetch(next_query, session_id)              # 后台起下轮召回
   ├─► on_pre_compress(messages) ─────────────► [[entities/contextengine]].compress()
   ├─► on_memory_write(action, target, content)            # 镜像 built-in memory 工具
   ├─► on_delegation(task, result, child_session_id)       # 父 agent 观察 subagent
   └─► on_session_end(messages)   # 真边界：CLI exit / /reset / gateway expiry
                                  # 非 per-turn
```

`get_tool_schemas()` 的产物**不**进 [[entities/tool-registry]]；agent loop 在 `self.tools` 外单独持有 provider schemas 并路由 `handle_tool_call`。这是 memory provider 与普通 `tools/*.py` 工具的根本区别。

## 坑点

- **`handle_tool_call` 默认 `raise NotImplementedError`**（`agent/memory_provider.py:131`）—— **不是** error JSON。凡 `get_tool_schemas()` 返回非空的 provider 必须 override；否则模型第一次触到 provider 工具就把 agent 抛出。其他 optional hooks 默认都是 no-op / 空串，独 `handle_tool_call` 是 `raise`，设计上逼你显式实现。
- **`is_available()` 禁网络调用。** docstring `:54–58` 明令 "should not make network calls — just check config and installed deps"。在里面写 `requests.get(...)` / `httpx` probe 会阻塞 agent init，CLI 启动感知为卡顿。连接 probe 归 `initialize()`（OpenViking 示例见 `plugins/memory/openviking/__init__.py:312`，`initialize` 内调 `_VikingClient.health()`）。
- **`initialize` kwargs 必须尊重 `hermes_home` 与 `agent_context`。** `hermes_home`（`:67`）是**唯一**合法存储根；硬写 `~/.hermes` 会在 profile 切换时污染错误目录 —— 所有 profile-aware provider 必须 `path = os.path.join(kwargs["hermes_home"], ...)`。`agent_context`（`:70`）取值 `"primary"` / `"subagent"` / `"cron"` / `"flush"`；**非 primary 必须跳过写入** —— cron 触发的 system prompt 写入会把 agent 生成的元文本当作用户画像污染（docstring `:71–73`）。
- **`on_session_end` ≠ per-turn。** 只在真会话边界触发（CLI exit、`/reset`、gateway session expiry；docstring `:158–160`）。把它当作"每轮结束 hook"是最常见误读 —— 每轮结束用 `sync_turn`。
- **`on_pre_compress` 是**单向**桥。** 返回值只进 compressor 的 summary prompt；compressor 不会反馈"最终保留了哪些内容"给你。若 provider 想做双向一致，必须在 `sync_turn` 里自行复制副本 —— 压缩事件之后你看到的 `messages` 已经是压缩后的序列。
- **单 external provider 由 MemoryManager 强制。** docstring `:5–9` 明说 "Only one external provider runs at a time to prevent tool schema bloat and conflicting memory backends"。plugin 侧不要自己做 fallback；plugin 只需保证 `is_available()` 正确 reflect 配置即可，裁决在 manager 层。

## References

- 源：`agent/memory_provider.py:42`（`class MemoryProvider(ABC)`）、`:47`（`name`）、`:53`（`is_available`）、`:61`（`initialize`）、`:83`（`system_prompt_block`）、`:92`（`prefetch`）、`:106`（`queue_prefetch`）、`:114`（`sync_turn`）、`:122`（`get_tool_schemas`）、`:131`（`handle_tool_call` 默认 `raise`）、`:139`（`shutdown`）、`:144`（`on_turn_start`）、`:153`（`on_session_end`）、`:163`（`on_pre_compress`）、`:175`（`on_delegation`）、`:188`（`get_config_schema`）、`:206`（`save_config`）、`:223`（`on_memory_write`）
- 源：`plugins/memory/openviking/__init__.py:255`（`class OpenVikingMemoryProvider(MemoryProvider)`）、`:273`（`is_available` — 零网络调用实例）、`:312`（`initialize` + 健康探测）、`:448`（`on_session_end` 带 atexit 兜底）、`:672`（`register(ctx)` 插件入口）
- Raw 快照：`raw/code-snapshots/agent_memory_provider-20260424.md`、`raw/code-snapshots/openviking_plugin-20260424.md`
- 相关 wiki 页：[[entities/aiagent]]、[[entities/contextengine]]、[[entities/tool-registry]]
- 相关 / 后续页：[[concepts/memory-provider-lifecycle]]、[[comparisons/memory-provider-vs-context-engine]]；若后续需要实现级 entity，可新增 `entities/openviking-memory-provider.md`
