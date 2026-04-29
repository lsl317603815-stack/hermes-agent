<!-- autogen-guarded -->
<!--
  此文件的 3 个切片（by type / by subsystem / by tag）将在 Phase 3 之后由
  `docs/wiki/scripts/ingest_seed.py` 自动重生成。Phase 0/1 期间为手写种子版。
  若你手动增删条目，请同步更新 `_meta/coverage-map.md` 与 `_meta/source-manifest.md`。
-->

# Hermes Wiki Index

**入口说明：** 三个切片对应三种导航习惯。新人建议从「按子系统」开始；日常查阅用「按 tag」；看全局用「按类型」+ Obsidian graph view。

---

## By type

### entities/（有名字的对象）

- [[entities/aiagent]] —— Hermes 主 agent 类，conversation flow + tool execution 的协调者
- [[entities/memoryprovider]] —— 外部记忆后端的抽象基类；插件契约，单 external provider + 永远在场的 built-in memory
- [[entities/contextengine]] —— 上下文窗口管理的抽象基类；每 agent 实例恰好一个引擎，默认 compressor
- [[entities/tool-registry]] —— 进程内唯一的工具注册中心；模块级单例，thread-safe，AST-based 自发现

### concepts/（机制或流程）

- [[concepts/agent-loop]] —— `run_conversation()` 内的主循环，定义一次 turn 的生命周期
- [[concepts/toolset-system]] —— toolset 命名分组、静态 / plugin / MCP 三源合并与 `resolve_toolset` 递归展开
- [[concepts/memory-provider-lifecycle]] —— memory provider 从 init → per-turn → 真边界 teardown 的完整时间线

### comparisons/（A-vs-B 辨析）

- [[comparisons/memory-provider-vs-context-engine]] —— 跨会话记忆 vs 当前会话压缩；`on_pre_compress` 是两者唯一交汇点

### queries/（高频问答）

- [[queries/how-tools-enter-the-model-surface]] —— 工具从注册到出现在 model API 请求里经过的 3 道门
- [[queries/where-to-add-a-new-tool]] —— 新工具按归属归类到 built-in / plugin / memory / context-engine 四条通路

### briefs/（一次性产出模板）

- `briefs/onboarding-brief.template.md` —— 新人/新 agent 接手某子系统时的 onboarding brief 模板
- `briefs/pr-review-brief.template.md` —— PR review 前的上下文 brief 模板
- `briefs/debug-brief.template.md` —— bug / regression / 工具不可见时的 debug brief 模板

---

## By subsystem

### Agent core

- [[entities/aiagent]]
- [[concepts/agent-loop]]

### Tools

- [[entities/tool-registry]]
- [[concepts/toolset-system]]
- [[queries/how-tools-enter-the-model-surface]]
- [[queries/where-to-add-a-new-tool]]

### Toolsets

- [[concepts/toolset-system]]
- [[queries/how-tools-enter-the-model-surface]]
- [[queries/where-to-add-a-new-tool]]

### Memory

- [[entities/memoryprovider]]
- [[concepts/memory-provider-lifecycle]]
- [[comparisons/memory-provider-vs-context-engine]]

### Context engine

- [[entities/contextengine]]
- [[comparisons/memory-provider-vs-context-engine]]

### Plugins

- [[concepts/toolset-system]]
- [[queries/where-to-add-a-new-tool]]

### CLI
### Gateway
### Skills
### Config / paths
### Testing

_Phase 0 canary + Phase 1 首批建 agent-core、tools、toolsets、memory、context-engine、plugins；其余子系统在 Phase 2 补齐。参见 `_meta/coverage-map.md` 追踪覆盖度。_

---

## By tag

> 合法 tag 列表见 `_meta/taxonomy.md`。未列出的 tag 会被 lint 拒绝。

- `agent-core` —— [[entities/aiagent]] · [[concepts/agent-loop]]
- `architecture` —— [[entities/aiagent]] · [[concepts/agent-loop]] · [[entities/memoryprovider]] · [[entities/contextengine]] · [[entities/tool-registry]] · [[concepts/toolset-system]] · [[concepts/memory-provider-lifecycle]] · [[comparisons/memory-provider-vs-context-engine]]
- `tools` —— [[entities/tool-registry]] · [[concepts/toolset-system]] · [[queries/how-tools-enter-the-model-surface]] · [[queries/where-to-add-a-new-tool]]
- `toolsets` —— [[concepts/toolset-system]] · [[queries/how-tools-enter-the-model-surface]] · [[queries/where-to-add-a-new-tool]]
- `memory` —— [[entities/memoryprovider]] · [[concepts/memory-provider-lifecycle]] · [[comparisons/memory-provider-vs-context-engine]]
- `context-engine` —— [[entities/contextengine]] · [[comparisons/memory-provider-vs-context-engine]]
- `plugins` —— [[entities/memoryprovider]] · [[entities/tool-registry]] · [[concepts/toolset-system]] · [[queries/where-to-add-a-new-tool]]
- `workflow` —— [[concepts/agent-loop]] · [[concepts/memory-provider-lifecycle]]
- `onboarding` —— `briefs/onboarding-brief.template.md`
- `cli` · `gateway` · `skills` · `testing` · `config` · `paths` · `provider` —— _尚无页面；Phase 2 补齐_

---

## Meta 导航

- [[README]] —— 入口与 Obsidian 配置
- [[SCHEMA]] —— 机读规则
- [[log]] —— 时间线
- `_meta/source-manifest.md` —— source 登记
- `_meta/coverage-map.md` —— 子系统 × 页对照
- `_meta/taxonomy.md` —— 合法 tags
- `_meta/backlog.md` —— 已识别但暂不做的页
- `_meta/deviations.md` —— 实施与方案不符的事实登记

---

_本页为 Phase 0 种子；Phase 2+ 会由脚本刷新，不要在 `<!-- autogen-guarded -->` 之后手写大段内容。_
