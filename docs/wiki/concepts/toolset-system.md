---
title: Toolset system
type: concept
tags: [toolsets, tools, plugins, architecture]
sources:
  - toolsets.py
  - tools/registry.py
  - hermes_cli/plugins.py
wikilinks_out: [entities/tool-registry, queries/how-tools-enter-the-model-surface, queries/where-to-add-a-new-tool, entities/aiagent, concepts/agent-loop, entities/memoryprovider, entities/contextengine]
last_refreshed: 2026-04-24
refreshed_by: claude-code
---

# Toolset system

## TL;DR

**Toolset** 是 Hermes 用来把工具分组 / 给平台选择性暴露的命名集合。两条声明路径：静态 `TOOLSETS` dict（`toolsets.py:68`）与插件在 `PluginContext.register_tool(..., toolset=...)`（`hermes_cli/plugins.py:133`）时动态注入；解析走 `resolve_toolset(name)`（`toolsets.py:447`）做递归展开（支持 `includes` 组合与 `"all"` / `"*"` 通配）。它与 [[entities/tool-registry]] 不是同一层 —— registry 说「哪些工具**存在**」，toolset 说「哪些工具**被暴露**给某平台的 agent」。这是 [[queries/how-tools-enter-the-model-surface]] 描述三道门中间那一道。

## 责任边界

**做什么：**

- **命名分组** —— 静态 toolset 在 `TOOLSETS` dict（`toolsets.py:68`）里声明 `{description, tools, includes}`，一条条手写
- **平台共享核心** —— `_HERMES_CORE_TOOLS`（`toolsets.py:31`）是跨 messaging 平台共享的 tool-name 列表；`hermes-cli` / `hermes-telegram` / `hermes-slack` / `hermes-discord` / `hermes-signal` / `hermes-wecom` / …（`:278+`）全部 `tools=_HERMES_CORE_TOOLS`。改一处等于改全部（见 §坑点）
- **组合 via `includes`** —— `hermes-gateway`（`toolsets.py:392`）通过 `includes=["hermes-telegram", "hermes-discord", …]` 形成所有 messaging 平台工具的并集；`debugging`（`:207`）、`safe`（`:213`）、以及运行时 `create_custom_toolset()`（`:613`）皆走同一组合路径
- **递归解析** —— `resolve_toolset(name, visited)`（`:447`）做 DFS 展开；`visited` 集合在兄弟 includes 间**共享**（`:494`）以保证 diamond 依赖只解一次；`"all"` / `"*"` 两个特殊别名（`:464`）聚合所有已知 toolset 的工具
- **插件动态注入** —— `hermes_cli/plugins.py:133` `PluginContext.register_tool(name, toolset=..., ...)` 委派到 `registry.register`；`toolset=` 参数**同时**让插件工具出现在该 toolset 名下。`toolsets.py:519` `_get_plugin_toolset_names()` 从 registry 回读；`get_toolset(name)`（`:401`）在静态 dict miss 时走插件 / MCP 分支
- **MCP toolset 别名** —— MCP server refresh 路径会调 `registry.register_toolset_alias(alias, canonical)`（`tools/registry.py:151`），把短名映射到规范 toolset 名；`get_toolset` 在插件路径里解这层别名（`toolsets.py:411–421`）
- **列举 / 校验** —— `get_toolset_names()`（`:570`）、`get_all_toolsets()`（`:545`）、`validate_toolset(name)`（`:593`）为 CLI 的 `hermes tools` TUI 与 `--enabled-toolsets` 参数校验提供接口

**不做什么：**

- **不注册工具** —— toolset 仅**引用** tool name；工具存在性由 [[entities/tool-registry]] 决定。一个名字在 toolset 里出现不代表 registry 里有它（最常见"幽灵工具"症状源自这一步 —— 见 §坑点）
- **不做可用性校验** —— `check_fn` 由 registry 条目自带；`resolve_toolset` 不关心「工具当前是否能跑」，只给名字
- **不决定模型是否看见** —— 决定权在 `get_tool_definitions(enabled_toolsets, disabled_toolsets)`（`model_tools.py:196`）；toolset 只负责给候选集合
- **不涵盖 memory provider / context engine 的工具** —— memory provider 的 tool schema 由 `MemoryManager` 注入到 `self.tools`（`run_agent.py:1311+`），**不**经 toolset 系统；[[entities/contextengine]] 的工具同理。这些是第二条工具通路

## 调用链 / 关系

```
toolsets.py                                tools/registry.py
        │                                          │
        │  _HERMES_CORE_TOOLS (:31)    ┌───────────┤  registry._tools
        │  (List[str])                 │           │  (tool 存在性层)
        │                              ▼           │
        │  TOOLSETS dict (:68)    ┌─ tool names ──►│
        │        │                │                │
        │        ▼                │                │
        │  resolve_toolset (:447) ◄─┐              │
        │     │ includes 递归        │              │
        │     │ visited 共享（:494） │              │
        │     │ "all"/"*" (:464)    │              │
        │     ▼                    │              │
        │  tool-name set ──────────┘              │
        │                                          │
        │  _get_plugin_toolset_names (:519)        │
        │    ── reads registered toolsets ──►      │
        │  _get_registry_toolset_aliases (:536)    │
        │    ── reads MCP 别名 ──►                 │
        │                                          │
hermes_cli/plugins.py                              │
        │                                          │
        │  PluginContext.register_tool (:133) ────►│  registry.register(
        │    （plugin code inside register(ctx)）  │    toolset=<plugin-toolset-name>, ...)
        │                                          │
        │  discover_plugins() (:729)               │  registry.register_toolset_alias(:151)
        │    必须在 get_tool_definitions 之前调用  │    （MCP refresh）
        ▼                                          ▼
model_tools.get_tool_definitions(enabled_toolsets, disabled_toolsets, quiet_mode)
        │
        ├─► for each toolset: resolve_toolset → tool-name set（并集）
        ├─► registry.get_definitions(tool_names) → OpenAI schema list
        ▼
self.tools  (AIAgent.__init__ 时快照；见 [[entities/aiagent]])
```

详细三道门全图见 [[queries/how-tools-enter-the-model-surface]]；添加新工具时该选哪条路径见 [[queries/where-to-add-a-new-tool]]。

## 坑点

- **列在 toolset ≠ 已注册。** `_HERMES_CORE_TOOLS` 里写了一个名字，但对应的 `tools/<name>.py` 若从未被 `discover_builtin_tools`（`tools/registry.py:56`）扫到（AST 顶层无 `registry.register(...)`；见 [[entities/tool-registry]] 坑点 §3），工具在 registry 里根本不存在。`resolve_toolset("hermes-cli")` 照样会返回这个名字，但 `registry.get_definitions` 遇到未注册名**静默跳过**，不 raise。症状：CLI 启动无报错，模型看不到该工具。自查：`get_tool_definitions(quiet_mode=False)` 看 toolset 解析输出，或 REPL 里 `from tools.registry import registry; registry.get_all_tool_names()`。
- **`_HERMES_CORE_TOOLS` 是跨平台共享，慎改。** 往这个列表塞一个新工具，它**同时**出现在 15+ 个 toolset 里（`hermes-cli` / `hermes-telegram` / `hermes-discord` / `hermes-slack` / `hermes-signal` / `hermes-wecom` / `hermes-feishu` / …）。若新工具在 messaging 平台有风险（例如文件写入缺额外审批），不要塞 `_HERMES_CORE_TOOLS` —— 应显式列入 `hermes-cli` 与选定平台的 `tools=[..., "new_tool"]`，或走 `includes`。`hermes-acp`（`:226`）与 `hermes-api-server`（`:245`）就是**显式不继承** `_HERMES_CORE_TOOLS` 的例子 —— 它们手写子集，去掉 `send_message` / `clarify` 等 UI 工具。
- **插件 toolset 只在 `discover_plugins()` 之后可见。** `_get_plugin_toolset_names()`（`toolsets.py:519`）读的是 `registry.get_registered_toolset_names()`；而 registry 里的 plugin toolset 是 plugin 的 `register(ctx)` 里调 `ctx.register_tool(..., toolset=...)` 落地的。若 `discover_plugins()` 尚未跑，`get_plugin_toolsets()`（`hermes_cli/plugins.py:801`）返回空，`resolve_toolset("my-plugin")` 得不到任何工具。`hermes_cli/tools_config.py:85+` 的模式是**显式** `discover_plugins()` 后再 `get_plugin_toolsets()` —— 复制这个模式，不要先取后 discover。
- **`includes` 里的 cycle / diamond 被静默吞掉。** `resolve_toolset` 的 `visited` 集合跨兄弟 includes 共享（`:494`）；发现重复时返回 `[]` 且不警告（源内注释 `:471–475` 说明是「安全跳过，不是 bug」）。但若你意外创建真正的 cycle（A includes B, B includes A），你不会看到 lint / 报错 —— 只是两边的工具各自在首次解析时被收集一次，第二次返回空。调试大型 `includes` 链失效时，直接 `print(resolve_toolset(name))` 是唯一可靠验证。
- **`get_toolset()` 对未知名返回 `None`（不 raise）。** 若你传 `enabled_toolsets=["typo-name"]` 到 agent init，`resolve_toolset("typo-name")` 返回 `[]`，最终 `self.tools` 只剩其它 toolset 的并集 —— 症状与"工具列得不对"相同。在 CLI 入口用 `validate_toolset(name)`（`:593`）做白名单校验才能提前报错；不要等 agent 跑起来再发现。
- **静态 `TOOLSETS` 与插件 toolset 共享名字空间。** 若静态 dict 里已有 `"foo"`（例如 `"memory"` — `:184`），插件再用 `toolset="foo"` 注册工具，`get_toolset("foo")` 走静态分支（`:401` 先 `TOOLSETS.get(name)`）；插件注册的工具能进 registry，但静态 toolset 的 `tools=[...]` 不会自动合并它们。想扩展已有静态 toolset 请走 `includes`（不改原 dict），或在插件里用新 toolset 名。
- **`create_custom_toolset()` 不持久化。** `:613` 只往进程内 `TOOLSETS` 变量加条目；进程退出即丢。若需长期暴露，应改 `toolsets.py` 源码或走插件路径。

## References

- 源：`toolsets.py:31`（`_HERMES_CORE_TOOLS`）、`:68`（`TOOLSETS`）、`:184`（`"memory"` toolset 例）、`:207`（`debugging`）、`:213`（`safe`）、`:226`（`hermes-acp` — 显式子集）、`:245`（`hermes-api-server`）、`:278`（`hermes-cli` — 共享 core）、`:284`（`hermes-telegram`）、`:392`（`hermes-gateway` — `includes` union）、`:401`（`get_toolset`）、`:447`（`resolve_toolset`）、`:464`（`"all"` / `"*"`）、`:494`（`visited` 共享）、`:500`（`resolve_multiple_toolsets`）、`:519`（`_get_plugin_toolset_names`）、`:536`（`_get_registry_toolset_aliases`）、`:545`（`get_all_toolsets`）、`:570`（`get_toolset_names`）、`:593`（`validate_toolset`）、`:613`（`create_custom_toolset`）
- 源：`tools/registry.py:151`（`register_toolset_alias`）、`:176`（`register` 的 `toolset` 参数）、`:371`（`get_available_toolsets`）、`:379`（`get_registered_toolset_names`）
- 源：`hermes_cli/plugins.py:133`（`PluginContext.register_tool`）、`:729`（`discover_plugins`）、`:801`（`get_plugin_toolsets`）
- Raw 快照：`raw/code-snapshots/toolsets-20260424.md`、`raw/code-snapshots/tools_registry-20260424.md`
- 相关 wiki 页：[[entities/tool-registry]]、[[queries/how-tools-enter-the-model-surface]]、[[queries/where-to-add-a-new-tool]]、[[entities/aiagent]]、[[concepts/agent-loop]]
- 相邻但独立的工具通路：[[entities/memoryprovider]]（provider 工具走 `MemoryManager` 注入，不经本系统）、[[entities/contextengine]]（engine 自己的 `get_tool_schemas`）
