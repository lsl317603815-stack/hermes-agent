---
title: Tool Registry
type: entity
tags: [tools, plugins, architecture]
sources:
  - tools/registry.py
wikilinks_out: [entities/aiagent, concepts/agent-loop, queries/how-tools-enter-the-model-surface, entities/memoryprovider]
last_refreshed: 2026-04-24
refreshed_by: claude-code
---

# Tool Registry

## TL;DR

`ToolRegistry`（`tools/registry.py:100`）是 Hermes 所有工具的**唯一**注册中心；模块级单例 `registry = ToolRegistry()`（`:437`）是整个进程内的 single source of truth。每个 `tools/*.py` 在模块加载时调 `registry.register(...)`（`:176`）把 `(name, toolset, schema, handler, check_fn, ...)` 塞进去；`model_tools.py` 的 `get_tool_definitions()`、toolset 解析、MCP 动态刷新、async handler bridge —— 全部委派到这一个对象。本页是契约本身；工具从注册到进 API 请求的"三道门"完整路径见 [[queries/how-tools-enter-the-model-surface]]。它与 memory / context engine 的工具**不是**同一层：memory provider 的工具走 `provider.handle_tool_call`（见 [[entities/memoryprovider]]），不经过 registry。

## 责任边界

**做什么：**

- **注册 / 注销** —— `register(name, toolset, schema, handler, ...)`（`tools/registry.py:176`）在 `_lock: threading.RLock` 下写入 `_tools: Dict[str, ToolEntry]`；`deregister(name)`（`:229`）移除单工具，当 toolset 最后一个工具被移除时连带清理 `_toolset_checks` 与 `_toolset_aliases`
- **AST-based 自发现** —— `discover_builtin_tools(tools_dir=None)`（`:56`）按 `sorted(tools_path.glob("*.py"))` 遍历；`_module_registers_tools(path)`（`:41`）AST 扫文件 body，只取含顶层 `registry.register(...)` 调用的模块；`__init__.py`、`registry.py`、`mcp_tool.py` 硬排除
- **Schema 检索与归一化** —— `get_definitions(tool_names, quiet=False)`（`:258`）返回 OpenAI function-calling 格式；被调用者通过 `tool_names` 集合筛；对每个工具的 `check_fn()` 结果**按调用 memo**（同一 `check_fn` 多工具共享只 eval 一次）；schema 输出强制注入 `"name": entry.name`（`:282`）即使登记时 schema 漏写
- **异步桥** —— `dispatch(name, args, **kwargs)`（`:292`）自动用 `model_tools._run_async`（lazy import，`:304`）把 async handler 接入同步 agent loop；所有异常包成 `{"error": "Tool execution failed: <Type>: <msg>"}`
- **Toolset 元数据** —— `get_registered_toolset_names`、`get_tool_names_for_toolset`、`register_toolset_alias`、`is_toolset_available`、`check_toolset_requirements`、`get_available_toolsets` 等 query 方法为 `toolsets.py` 的解析层与 UI 显示提供稳定快照（所有 reader 走 `_snapshot_state()` `:112` 复制一份后操作，避免 MCP 刷新时读写打架）
- **JSON helper** —— `tool_error(message, **extra)`（`:456`）与 `tool_result(data=None, **kwargs)`（`:470`）是"每个工具 handler 必须返回 JSON 字符串"这个契约的标准助手，省掉重复的 `json.dumps({"error": msg}, ensure_ascii=False)` 样板

**不做什么：**

- **不决定"哪些工具暴露给模型"** —— 那是 toolset 的职责（`toolsets.py` + `model_tools.get_tool_definitions`）；registry 只回答"who's registered"
- **不实现工具语义** —— 工具逻辑在 `tools/*.py` 的 handler 里；registry 只存引用并 dispatch
- **不 import `model_tools`** —— 为了断掉循环 import（`tools.registry` ← `model_tools` ← 每个 tool 文件 ← `tools.registry`），`_run_async` 必须 lazy import（`:304`）。碰它等于点燃循环引用
- **不处理 memory provider / context engine 的工具** —— 它们自己 `get_tool_schemas()` 返回，agent loop 在 `self.tools` 之外单路径路由（见 [[entities/memoryprovider]]、[[concepts/agent-loop]]）

## 调用链 / 关系

```
model_tools.py 启动
        │
        ▼
registry.discover_builtin_tools()  (tools/registry.py:56)
   │  扫 tools/*.py  →  _module_registers_tools(path)  (AST 查顶层 registry.register 调用)
   │  importlib.import_module("tools.<name>")  → 触发模块级 registry.register(...)
   ▼
registry._tools  填充为 {name: ToolEntry}
        │
        │  plugins 走同一条路径：hermes_cli.plugins 的 PluginContext.register_tool
        │  内部最终还是 registry.register(...)
        │
        │  MCP 走 tools/mcp_tool.py：server refresh 触发 register / deregister 循环
        │
        ▼
get_tool_definitions(enabled_toolsets, disabled_toolsets, quiet)  (model_tools.py)
   │  聚合 toolset → tool-name 集合
   │  registry.get_definitions(tool_names, quiet)  (:258)
   │        │  check_fn memo → 过滤不可用
   │        │  schema 归一化（注入 name）
   │        ▼
   │  返回 List[{"type": "function", "function": schema}]
   ▼
AIAgent.self.tools  (快照；见 [[entities/aiagent]] 坑点 §1)
        │
        ▼
API request  tools=self.tools  → 模型看见
        │
        ▼  (若 tool_calls 触发)
registry.dispatch(name, args, **kwargs)  (:292)
   │  entry.is_async  → from model_tools import _run_async  (lazy; :304)
   │  except Exception  → json.dumps({"error": ...})
   ▼
handler(args, **kwargs) -> str  (JSON)
```

三道门全图见 [[queries/how-tools-enter-the-model-surface]]；循环中 dispatch 的位置见 [[concepts/agent-loop]]。

## 坑点

- **工具名 shadow 默认被拒。** `register()` 发现同名 entry 来自不同 toolset 时**不覆盖**而是 log error 并直接 return（`tools/registry.py:191–211`）。**唯一例外**：`existing.toolset.startswith("mcp-")` 且 `toolset.startswith("mcp-")` 同时成立 —— 此时允许覆盖（合法场景：MCP server refresh、两个 MCP server 有重名工具）。这条规则是 built-in / plugin / MCP 三方的反 shadowing 防线：plugin 想替换 built-in 工具，必须先 `deregister` 旧的再 `register` 新的，不能靠撞名。
- **注册是 import-time 的一次性事件；agent init **后**才 register 的工具对当前 agent 不可见。** `AIAgent.self.tools` 是 init 时从 registry 取的**快照**；plugin 若在 agent 创建后才动态注册，必须显式 `self.agent.tools = get_tool_definitions(...)`（`cli.py:6633` 做过这件事）重建快照。把新工具 register 路径尽量放在 `discover_plugins()` 阶段（agent 之前）能躲过此坑。
- **AST 扫描只看 top-level。** `_module_registers_tools`（`:41`）只检查 `tree.body`；把 `registry.register(...)` 写在函数里（例如 lazy 初始化）时，`discover_builtin_tools` **不会**把这个模块纳入 import 列表。必须在模块级调 `register`，否则 AST 扫描看不见、模块不被 import、工具永远不在 registry 里。
- **`dispatch` 吞所有异常。** `:302–309` 里 `except Exception as e:` → `json.dumps({"error": f"Tool execution failed: {type(e).__name__}: {e}"})`。**不要**在 handler 里再包一层自家的 try/except 并返回你自己的 error JSON —— 它会被 dispatch 当作正常 string 返回，而若你不返回 JSON、抛 `ValueError`，dispatch 照样兜底。保持 handler 不吞异常、返回 JSON 即可；错格式反而让双层 wrapping 变难诊断。
- **`_run_async` 的 lazy import 是硬性防火墙。** `tools.registry` 模块顶层**不能**出现 `from model_tools import ...`，否则 circular import 立刻炸。`dispatch` 内 `from model_tools import _run_async`（`:304`）是刻意设计；改动这里前确认 `model_tools.py` 还没有开始 import `tools.registry` 的相对路径。循环一启，整个进程起不来。
- **`get_definitions` 的 `check_fn` memo 仅在单次调用内生效。** `check_results: Dict[Callable, bool]`（`:262`）是函数局部；下一次 `get_tool_definitions` 会重新跑所有 `check_fn`。若 check_fn 很贵（例如探测远程服务可达性），把 check_fn 写成纯内存读取并在别处做异步探测，不要把慢 I/O 塞进去。

## References

- 源：`tools/registry.py:28`（`_is_registry_register_call` AST pattern）、`:41`（`_module_registers_tools`）、`:56`（`discover_builtin_tools`）、`:76`（`class ToolEntry` + slots）、`:100`（`class ToolRegistry`）、`:103`（`__init__` with `_lock: RLock`）、`:112`（`_snapshot_state`）、`:135`（`get_entry`）、`:151`（`register_toolset_alias`）、`:176`（`register`）、`:191–211`（shadowing 规则 + MCP 例外）、`:229`（`deregister`）、`:258`（`get_definitions` + check_fn memo）、`:282`（schema name 归一化）、`:292`（`dispatch`）、`:304`（`_run_async` lazy import）、`:315`（`get_max_result_size`）、`:325`（`get_all_tool_names`）、`:329`（`get_schema`）、`:338`（`get_toolset_for_tool`）、`:352`（`is_toolset_available`）、`:362`（`check_toolset_requirements`）、`:371`（`get_available_toolsets`）、`:414`（`check_tool_availability`）、`:437`（模块级单例 `registry`）、`:456`（`tool_error`）、`:470`（`tool_result`）
- Raw 快照：`raw/code-snapshots/tools_registry-20260424.md`
- 相关 wiki 页：[[entities/aiagent]]、[[concepts/agent-loop]]、[[queries/how-tools-enter-the-model-surface]]、[[entities/memoryprovider]]
- 周边协作者（尚未建 wiki 页，仅作源指针）：`model_tools.py`（orchestrator）、`toolsets.py`（toolset → tool-name 解析层，见 raw 快照 `raw/code-snapshots/toolsets-20260424.md`）、`tools/mcp_tool.py`（MCP 动态 register / deregister 路径）、`hermes_cli/plugins.py`（plugin 侧 `PluginContext.register_tool` 最终委派到 `tools.registry.register`）
