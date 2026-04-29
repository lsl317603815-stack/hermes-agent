---
title: Where to add a new tool
type: query
tags: [tools, toolsets, plugins]
sources:
  - tools/registry.py
  - toolsets.py
  - hermes_cli/plugins.py
wikilinks_out: [entities/tool-registry, concepts/toolset-system, queries/how-tools-enter-the-model-surface, entities/memoryprovider, entities/contextengine, entities/aiagent]
last_refreshed: 2026-04-24
refreshed_by: claude-code
---

# Where to add a new tool

## TL;DR

问题：「我要加一个新工具，代码应该放哪？」答：按**归属**挑通路，不要按「工具长什么样」挑。四条互斥通路：(1) **built-in 工具** → 新建 `tools/<name>.py`，模块级 `registry.register(...)` + 把工具名加进 `toolsets.py` 的某个 toolset；(2) **plugin 工具（进 registry）** → 在 plugin 的 `register(ctx)` 里 `ctx.register_tool(name, schema, handler, toolset=...)`；(3) **memory provider 工具** → 在 provider 子类的 `get_tool_schemas()` + `handle_tool_call()` 里实现，**不走** registry；(4) **context engine 工具**（LCM 式）→ 在 engine 子类的 `get_tool_schemas()` + `handle_tool_call()` 里实现，也**不走** registry。搞混通路 = 工具要么不被模型看到（built-in / plugin 漏门），要么在 registry 里挂着但永远不执行（memory/engine 工具进了 registry）。本页只回答"放哪 + 怎样确保可见"；可见性为何是那三道门见 [[queries/how-tools-enter-the-model-surface]]。

## 责任边界

**本页回答：**

- 一个新工具按归属应走哪条通路（决策树）
- 每条通路需要改哪个文件、必须在**什么阶段**注册
- 如何确认新工具「真的被模型看到了」与「真的被 dispatch 到了」
- 共享 vs 平台专属 的 toolset 选型原则

**本页不回答：**

- 工具从注册到出现在 API 请求的 3 道门机制（见 [[queries/how-tools-enter-the-model-surface]]）
- tool registry 的内部结构与 shadowing 规则（见 [[entities/tool-registry]]）
- toolset 的解析、includes、plugin toolset 动态注入细节（见 [[concepts/toolset-system]]）
- memory provider / context engine 的契约（见 [[entities/memoryprovider]]、[[entities/contextengine]]）
- 端到端教程与 schema 字段字典（见 `website/docs/developer-guide/adding-tools.md`）

## 调用链 / 关系

### 决策树

```
新工具需求
    │
    ├─ 属于 agent 级**跨会话状态**的管理？
    │     （记忆召回、facts 抽取、长期偏好）
    │         │
    │         └─► 通路 (3): memory provider 工具
    │                  位置：provider 子类
    │                  入口：get_tool_schemas() + handle_tool_call()
    │                  注意：**不**走 registry；见 [[entities/memoryprovider]]
    │
    ├─ 属于**当前 context window 内**的内省 / 重写 / 检索？
    │     （LCM-grep、expand、describe）
    │         │
    │         └─► 通路 (4): context engine 工具
    │                  位置：engine 子类
    │                  入口：get_tool_schemas() + handle_tool_call()
    │                  注意：**不**走 registry；见 [[entities/contextengine]]
    │
    ├─ 来自外部 plugin 包（`plugins/*/__init__.py`，用户自行装插件）？
    │         │
    │         └─► 通路 (2): plugin 工具
    │                  位置：plugin 的 `register(ctx)` 函数
    │                  入口：ctx.register_tool(name, schema, handler, toolset=...)
    │                  委派：hermes_cli/plugins.py:133 → tools.registry.register
    │                  timing：discover_plugins() 必须在 AIAgent.__init__ 之前
    │
    └─ 通用 built-in（读写文件、调网络、终端、skill 等）？
              │
              └─► 通路 (1): built-in 工具
                       位置：新建 tools/<name>.py
                       入口：模块级 `registry.register(name, toolset, schema, handler, ...)`
                       自动发现：discover_builtin_tools() 做 AST 扫描（tools/registry.py:56）
                       门 2：在 toolsets.py 里加进 `_HERMES_CORE_TOOLS`
                              （若需平台共享）或指定 toolset 的 `tools=[...]`
```

### 通路 (1) built-in 工具 —— 文件级清单

1. 新建 `tools/<snake_case_name>.py`
2. 从 `from tools.registry import registry, tool_error, tool_result` 入手（`tool_error` / `tool_result` helper 见 `tools/registry.py:456`、`:470`，返回值契约是 JSON 字符串）
3. 在模块**顶层**（非函数体内）调：
   ```python
   registry.register(
       name="my_tool",
       toolset="...",           # 必填；见下文选择原则
       schema={...},            # OpenAI function-calling 格式
       handler=my_tool_handler, # 同步或 async 皆可；is_async 要显式标
       check_fn=None,           # 可选；返回 bool，按调用缓存（见坑点）
       requires_env=None,
       is_async=False,
       description="...",
       emoji="🔧",
   )
   ```
4. 在 `toolsets.py` 里让某个 toolset **认领**这个名字：
   - **跨平台共享** → 加进 `_HERMES_CORE_TOOLS`（`toolsets.py:31`）→ 自动出现在 `hermes-cli` + 所有 messaging 平台 toolset 里
   - **仅 CLI / 特定平台** → 去对应 toolset 定义里把名字加进 `tools=[...]`（例如 `hermes-cli` 在 `:278`）
   - **自定义集合** → 新建 toolset 条目 `TOOLSETS["my-set"] = {"description": ..., "tools": [...], "includes": []}`（或用 `includes` 组合 —— 见 [[concepts/toolset-system]]）
5. 自查：`python -c "from model_tools import get_tool_definitions; print([t['function']['name'] for t in get_tool_definitions(enabled_toolsets=['hermes-cli'], quiet_mode=False)])"`

### 通路 (2) plugin 工具（进 registry）

plugin 代码入口固定是 `register(ctx: PluginContext)`（由 `hermes_cli/plugins.py:729` `discover_plugins()` 调用）。里面调：

```python
def register(ctx):
    def my_handler(args, **kwargs):
        return json.dumps({...}, ensure_ascii=False)

    ctx.register_tool(
        name="my_plugin_tool",
        schema={...},
        handler=my_handler,
        toolset="my-plugin",  # plugin 专属 toolset；不要撞静态 TOOLSETS 的名字
    )
```

- `PluginContext.register_tool` 在 `hermes_cli/plugins.py:133`；内部就是 `registry.register`。
- plugin toolset 通过 `_get_plugin_toolset_names()`（`toolsets.py:519`）被 `get_all_toolsets()` / `resolve_toolset` 发现。
- plugin 新增的 toolset 名**不要**与静态 `TOOLSETS` 重名 —— 静态 dict 在 `get_toolset()` 内优先（`toolsets.py:401`），会把 plugin 注册的工具「藏」起来（见 [[concepts/toolset-system]] 坑点）。
- 用户在 `config.yaml` 的 `enabled_toolsets` 里加上 `"my-plugin"` 才会被模型看到。

### 通路 (3) memory provider 工具

provider 子类实现：

- `get_tool_schemas() -> List[dict]` —— 返回 OpenAI schema；由 `MemoryManager.get_all_tool_schemas()`（`agent/memory_manager.py:223`）聚合，AIAgent init 时**直接注入** `self.tools`（`run_agent.py:1311+`），**不**经 registry / toolset 系统
- `handle_tool_call(tool_name, args, **kwargs) -> str` —— 默认 `raise NotImplementedError`（`agent/memory_provider.py:131`），暴露了工具就必须实现
- 路由：agent loop 查 `manager._tool_to_provider` 索引 → `manager.handle_tool_call`（`agent/memory_manager.py:249`），**不**经 `registry.dispatch`
- 工具名不要加进 `toolsets.py` 的任何 toolset —— 通路不同；加了也会被 `registry.get_definitions` 在门 3 静默跳过（registry 里找不到）

### 通路 (4) context engine 工具

engine 子类实现：

- `get_tool_schemas() -> List[dict]` —— engine 自带；AIAgent init 合并到 `self.tools`
- `handle_tool_call(tool_name, args, **kwargs) -> str` —— 默认返回 error JSON（`agent/context_engine.py:137–147`，**与** provider 默认 `raise` **不对称**）
- 路由：`_AGENT_LOOP_TOOLS`（`model_tools.py:326`）之外的 engine-owned 名字由 agent loop 顶层拦截 → 调 `engine.handle_tool_call`
- 与通路 (3) 同理：**不进** registry、**不进** `toolsets.py`

## 坑点

- **通路搞错 = 工具永远沉默或永远不被 dispatch。** 最常见三种误配：
  1. 写了 memory 相关工具，本能地扔到 `tools/my_mem_tool.py` + `_HERMES_CORE_TOOLS` —— 工具能进 `self.tools`，但它访问不了 `MemoryManager` 的 provider 状态；handler 里拿不到 `self`（registry dispatch 没这回事）。正确：实现 provider 子类的 `get_tool_schemas`。
  2. 写了 context 相关工具，扔到通路 (1) —— 同理，拿不到 engine 实例。
  3. plugin 工具注册后忘了在 `config.yaml` 启用对应 plugin toolset —— 工具在 registry 里但 `get_tool_definitions` 不会取（不在 `enabled_toolsets` 解析出的 tool-name 集合里）。
- **模块级 `register` 不是模块级 `def`。** `discover_builtin_tools()`（`tools/registry.py:56`）的 AST 扫描只看 `tree.body` 顶层（`:41` `_module_registers_tools`）—— 把 `registry.register(...)` 塞进函数里（例如"懒注册"、"按 env 决定是否注册"）会让整个模块不被 import。想按条件禁用，走 `check_fn=lambda: <bool>`，而不是条件 register。
- **name shadow 默认被拒。** `registry.register` 发现同名来自不同 toolset 时 log error 并 return（`tools/registry.py:191–211`），**不覆盖**。唯一例外是 `mcp-*` 对 `mcp-*`。plugin 想替换 built-in 同名工具：先 `registry.deregister(name)` 再 `register` 新的，不要靠撞名（见 [[entities/tool-registry]] 坑点 §1）。
- **`_HERMES_CORE_TOOLS` 修改是跨平台事件。** 在这里塞一个新名字 = 同时出现在 `hermes-cli` / `hermes-telegram` / `hermes-slack` / `hermes-discord` / `hermes-signal` / `hermes-wecom` / `hermes-feishu` / `hermes-gateway`（via includes）+ 全部 messaging 平台。若工具在 messaging 语境下有风险（能写文件、能长时间占 runtime、需额外审批），**显式**只列入 `hermes-cli`（`toolsets.py:278`）或 `hermes-api-server`（`:245`）—— 后两者是已有"显式子集"示例（不继承 core）。见 [[concepts/toolset-system]] 坑点。
- **`check_fn` 在单次 `get_tool_definitions` 调用里被 memo 一次，跨调用不缓存。** 若把慢 I/O 写进 `check_fn`（例如探 HASS token、ping 服务），每次 agent 拉取工具列表都重跑。正确：`check_fn` 只读 env / 内存标志；真正的可达性探测放别处（启动脚本、后台任务）（见 [[entities/tool-registry]] 坑点 §5）。
- **plugin 必须在 `AIAgent.__init__` 前 `discover_plugins()`。** agent 的 `self.tools` 是 init 时的**快照**（见 [[entities/aiagent]]）—— plugin 后注册的工具对该 agent 不可见。正确时序在 `hermes_cli/tools_config.py:85+`：先 `discover_plugins()`，再 `get_plugin_toolsets()`，再构造 agent。
- **通路 (3)/(4) 的工具不要进 `toolsets.py`。** memory / engine 工具的 schema 是 provider / engine 自己负责 —— 写进 `toolsets.py` 的 toolset 名单里没有副作用，只是 `registry.get_definitions` 找不到该工具后**静默跳过**，反而污染 CI/lint 的一致性（Phase 2 `lint_wiki.py` 与 toolsets 侧自检会报 "ghost tool in toolset"）。

## References

- 源：`tools/registry.py:56` (`discover_builtin_tools` — AST 扫描)、`:176` (`register`)、`:191–211`（shadowing 规则）、`:229` (`deregister`)、`:258` (`get_definitions` + `check_fn` memo)、`:292` (`dispatch`)、`:437`（模块级单例 `registry`）、`:456`/`:470` (`tool_error`/`tool_result` helper)
- 源：`toolsets.py:31` (`_HERMES_CORE_TOOLS`)、`:68` (`TOOLSETS`)、`:245` (`hermes-api-server` 显式子集)、`:278` (`hermes-cli`)、`:392` (`hermes-gateway` 用 `includes`)、`:401` (`get_toolset`)、`:447` (`resolve_toolset`)、`:519` (`_get_plugin_toolset_names`)、`:593` (`validate_toolset`)、`:613` (`create_custom_toolset`)
- 源：`hermes_cli/plugins.py:133` (`PluginContext.register_tool`)、`:729` (`discover_plugins`)、`:801` (`get_plugin_toolsets`)
- 源：`model_tools.py:196` (`get_tool_definitions`)、`:326` (`_AGENT_LOOP_TOOLS`)
- 源：`agent/memory_provider.py:131`（provider `handle_tool_call` 默认 raise）、`agent/memory_manager.py:223` (`get_all_tool_schemas`)、`:249` (`handle_tool_call`)、`run_agent.py:1311+`（memory 工具 schema 注入 `self.tools`）
- 源：`agent/context_engine.py:137–147`（engine `handle_tool_call` 默认 error JSON）
- Raw 快照：`raw/code-snapshots/tools_registry-20260424.md`、`raw/code-snapshots/toolsets-20260424.md`、`raw/code-snapshots/model_tools-20260424.md`、`raw/code-snapshots/agent_memory_provider-20260424.md`、`raw/code-snapshots/agent_context_engine-20260424.md`
- 相关 wiki 页：[[entities/tool-registry]]、[[concepts/toolset-system]]、[[queries/how-tools-enter-the-model-surface]]、[[entities/memoryprovider]]、[[entities/contextengine]]、[[entities/aiagent]]
- 外部 how-to：`website/docs/developer-guide/adding-tools.md`（schema 字段字典、端到端添加教程，不替代本页的"放哪"决策）
