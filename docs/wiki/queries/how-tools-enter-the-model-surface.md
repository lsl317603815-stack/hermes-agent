---
title: How tools enter the model surface
type: query
tags: [tools, toolsets]
sources:
  - tools/registry.py
  - toolsets.py
  - model_tools.py
  - run_agent.py
wikilinks_out: [entities/aiagent, concepts/agent-loop, entities/tool-registry]
last_refreshed: 2026-04-24
refreshed_by: claude-code
---

# How tools enter the model surface

## TL;DR

问题：「我写了个新 tool，它什么时候真的会出现在模型请求里？」答：必须**同时**过三道门 —— (1) registry 注册 → (2) 至少一个 toolset 把它白名单 → (3) agent init 时 `get_tool_definitions()` 选中它。任何一步缺失都不会出现在 `tools=` 参数里，模型根本看不到。本页只回答"可见性"；如何被**执行**见 [[concepts/agent-loop]]。

## 责任边界

**本页回答：**

- 工具从源码到 API 请求的具体三步路径
- 若工具"没被模型看见"，在哪一道门被过滤
- toolset 与 plugin toolset 在暴露性上的差异
- `self.tools` 为什么是快照、何时需要重建

**本页不回答：**

- 工具如何被**执行**（见 [[concepts/agent-loop]]）
- 具体工具（terminal / memory / todo …）的语义（见对应 entity 页，Phase 1/2 建）
- 添加新工具的端到端 how-to 步骤（见 `website/docs/developer-guide/adding-tools.md`）

## 调用链 / 关系

### 门 1 —— registry 注册（`tools/registry.py:176` `register()`）

每个 `tools/*.py` 文件 `from tools.registry import registry`，在模块加载时调 `registry.register(name, schema, handler)`。`model_tools.py` 启动时调 `discover_builtin_tools()`（见 `model_tools.py:29` 的 import）扫描 `tools/` 下所有模块，从而触发这些 `register` 调用。

Plugin 侧同走 registry：`hermes_cli/plugins.py:133` 的 `PluginContext.register_tool()` 最终委派到 `tools.registry.register()`（见 `hermes_cli/plugins.py:24` 的 docstring）。无论来源，所有工具最终落到**同一个** registry 实例。

> **这一步过不去 → 模型永远看不到你的工具。**

### 门 2 —— toolset 白名单（`toolsets.py:31` `_HERMES_CORE_TOOLS` 等）

仅仅注册不够；**工具必须属于至少一个 toolset**（`model_tools.py` 注释原话："All tools must be part of a toolset to be accessible"）。核心 toolset 是 `_HERMES_CORE_TOOLS`（`toolsets.py:31`），内含 web / terminal / file / vision / browser / todo / memory / cronjob / send_message / ha_* 等约 30 个工具名。每个平台 toolset（`hermes-cli`、`hermes-telegram`、`hermes-slack`、`hermes-discord` …）在 `toolsets.py:280+` 起逐个声明 `"tools": _HERMES_CORE_TOOLS`。

Plugin toolsets 走 `_get_plugin_toolset_names()`（`toolsets.py:519`）动态注入，由 `hermes_cli/plugins.py:801` 的 `get_plugin_toolsets()` 提供。

> **工具名不在任何 toolset → 即使注册了，也会被门 3 过滤掉。**

### 门 3 —— agent 初始化过滤（`model_tools.py:196` `get_tool_definitions()`）

AIAgent 在 `run_agent.py:1086` 调用：

```python
self.tools = get_tool_definitions(
    enabled_toolsets=enabled_toolsets,
    disabled_toolsets=disabled_toolsets,
    quiet_mode=self.quiet_mode,
)
```

`get_tool_definitions` 的语义：

1. 若 `enabled_toolsets` 给定，对每个 toolset 名调 `resolve_toolset()`（`toolsets.py:447`）并聚合所有工具名
2. 否则从全体 toolset 汇合，再扣掉 `disabled_toolsets`
3. 按最终 tool-name 集合，从 registry 取每个工具的 OpenAI 格式 schema
4. 返回 `List[Dict[str, Any]]`，直接作为模型 API 请求的 `tools=` 参数

> **CLI / gateway 传错 `enabled_toolsets`（比如打错 toolset 名）→ 模型请求里会少工具；`quiet_mode=False` 时会在终端打印 `✅ Enabled toolset '...'` 以便核查。**

### 三门关系图

```
tools/*.py  ──register()──►  tools/registry.py              ─┐  门 1
                                                              │
toolsets.py._HERMES_CORE_TOOLS  ─resolve_toolset()─► tool-name set  ─┐  门 2
                                                                      │
run_agent.py  ─enabled_toolsets─►  get_tool_definitions()  ──► self.tools  ─┐  门 3
                                                                             │
                                                                             ▼
                                                              API request tools=[...]
                                                                     （模型可见）
```

## 坑点

- **门 1 过、门 2 缺 → 最常见的"幽灵工具"。** 注册完代码没在任何 toolset 里白名单 → 跑任何平台 toolset 都看不到。不要只看「registry 里有」，要查 `toolsets.py` 中 `_HERMES_CORE_TOOLS` 或对应 plugin toolset。
- **`self.tools` 是 snapshot，不是动态视图。** agent `__init__` 后才 register 的工具（例如 plugin 在 agent 创建后动态注册）不会自动进入 `self.tools`；必须像 `cli.py:6633` 那样显式 `self.agent.tools = get_tool_definitions(...)` 重建。Plugin 规范把工具注册放在 `discover_plugins()` 阶段（agent init 前），就是为了躲这个坑（见 [[entities/aiagent]] 坑点 §1）。
- **`_AGENT_LOOP_TOOLS`（`model_tools.py:326`）是"schema 对模型可见、但执行路径被 agent loop 拦截"。** 它们在门 1-3 全过（schema 照常进 API 请求），但 `handle_function_call` 对它们只回 stub —— 实际执行在 agent loop 内。这不是 bug，是契约：`todo` / `memory` / `session_search` / `delegate_task` 需要 agent 级状态（`TodoStore` / `MemoryStore` / delegate spawning）。
- **`quiet_mode=True` 时丢失关键诊断。** `get_tool_definitions(quiet_mode=True)` 不打印 toolset 解析结果；调试「模型为什么看不见工具」时先把 `quiet_mode` 关掉，或直接在 REPL 里调 `get_tool_definitions(enabled_toolsets=["hermes-cli"], quiet_mode=False)` 观察输出。

## References

- 源：`tools/registry.py:176` (`register`)
- 源：`toolsets.py:31` (`_HERMES_CORE_TOOLS`)、`toolsets.py:280+`（平台 toolset 定义）、`toolsets.py:447` (`resolve_toolset`)、`toolsets.py:519` (`_get_plugin_toolset_names`)
- 源：`model_tools.py:29` (`discover_builtin_tools` import)、`model_tools.py:196` (`get_tool_definitions`)、`model_tools.py:326` (`_AGENT_LOOP_TOOLS`)、`model_tools.py:421` (`handle_function_call`)
- 源：`run_agent.py:1086`（AIAgent 中的门 3 调用点）、`cli.py:6633`（运行时重建 `self.tools` 范例）
- 相关 wiki 页：[[entities/aiagent]]、[[concepts/agent-loop]]
- 未来页：[[entities/tool-registry]]（Phase 1/2 展开 registry 内部结构 —— `discover_builtin_tools`、schema 归一化、plugin 注册路径）
- 外部 how-to：`website/docs/developer-guide/adding-tools.md`（端到端添加步骤，不替代本页的"为什么"）
