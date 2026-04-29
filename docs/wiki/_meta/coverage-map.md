# Coverage Map

**核心子系统 × wiki 页对照。** 让「哪块讲清楚了 / 哪块还是黑箱」一目了然。

> **读法：** `✅` = 已覆盖（至少 entity + concept 各 1 页，形成局部链路）；`🟡` = 种子存在但未展开（canary / stub / 共享覆盖）；`⬜` = 未覆盖（backlog 或未登记）。
>
> **Phase 0 验收目标：** 仅 `agent-core` 与 `tools/toolsets` 子系统出现 `🟡` —— 这是 canary 的最小闭环；其他子系统 `⬜` 是**预期**的未覆盖状态，不是缺陷。
>
> **Phase 1 实际交付：** 补齐 `memory` / `context-engine` entity，并追加 `concepts/toolset-system`、`concepts/memory-provider-lifecycle`、`comparisons/memory-provider-vs-context-engine`、`queries/where-to-add-a-new-tool` —— `tools` 与 `memory` 满足 entity + concept 升级为 `✅`；`context-engine` 仅借共享 comparison 进入局部图，保持 `🟡`；`plugins` 通过 `concepts/toolset-system` + `queries/where-to-add-a-new-tool` 首次触及，缺专属 entity，保持 `🟡`。Phase 2 目标是补 `provider` / `cli` / `gateway` / `skills` / `config` / `paths`，并为 `context-engine` + `plugins` 补专属 entity / concept。

---

## 子系统覆盖矩阵

| 子系统 | taxonomy tag | entity 页 | concept 页 | comparison 页 | query 页 | 状态 |
|--------|-------------|-----------|-----------|---------------|----------|------|
| Agent core | `agent-core` | [[entities/aiagent]] | [[concepts/agent-loop]] | — | — | 🟡 canary |
| Tools | `tools` · `toolsets` | [[entities/tool-registry]] | [[concepts/toolset-system]] | — | [[queries/how-tools-enter-the-model-surface]] · [[queries/where-to-add-a-new-tool]] | ✅ entity + concept + 2 queries |
| Memory | `memory` | [[entities/memoryprovider]] | [[concepts/memory-provider-lifecycle]] | [[comparisons/memory-provider-vs-context-engine]] | — | ✅ entity + concept + comparison |
| Context engine | `context-engine` | [[entities/contextengine]] | — | [[comparisons/memory-provider-vs-context-engine]] _(shared)_ | — | 🟡 entity + 共享 comparison；缺专属 concept |
| Plugins | `plugins` | — | [[concepts/toolset-system]] _(部分覆盖)_ | — | [[queries/where-to-add-a-new-tool]] _(部分覆盖)_ | 🟡 仅借其它子系统页切入；缺专属 entity |
| Provider | `provider` | — | — | — | — | ⬜ Phase 2 |
| CLI | `cli` | — | — | — | — | ⬜ Phase 2 |
| Gateway | `gateway` | — | — | — | — | ⬜ backlog |
| Skills | `skills` | — | — | — | — | ⬜ Phase 2 |
| Config / paths | `config` · `paths` | — | — | — | — | ⬜ Phase 2 |
| Testing | `testing` | — | — | — | — | ⬜ Phase 2+ |

---

## Phase 0 canary 自检清单

- [x] `agent-core`：`AIAgent` 类有 entity 页；`run_conversation` 主循环有 concept 页 → **🟡 通过**
- [x] `tools` + `toolsets`：tool 从 registry 到 API 请求的三道门有 query 页 → **🟡 通过**
- [x] 至少形成一个闭环 wikilink：`aiagent → agent-loop → aiagent` 且 `aiagent → how-tools-enter-the-model-surface → aiagent`（即不是 3 页全部单向指向 canary 源，满足方案 §7 Phase 1 「关键 guard rail」的雏形） → **✅ 通过**
- [x] 所有 canary 页 `sources` 均在 `_meta/source-manifest.md` 登记 → **✅ 通过**
- [x] 所有 canary 页 `tags` 均来自 `_meta/taxonomy.md` 白名单 → **✅ 通过**

---

## Phase 1 entity 批次自检清单（2026-04-24）

- [x] `memory`：`MemoryProvider` ABC 有 entity 页；OpenViking 满实现已以 raw snapshot 形式登记，独立 entity 页延后到 P2-later backlog → **🟡 通过**
- [x] `context-engine`：`ContextEngine` ABC 有 entity 页；与 memory provider 通过 `on_pre_compress` 桥建立双向 wikilink → **🟡 通过**
- [x] `tools`：`ToolRegistry` 单例有 entity 页，解决 canary 期间 `aiagent` 与 `how-tools-enter-the-model-surface` 中的两个 forward wikilink → **🟡 通过**
- [x] 三页 `sources` 均在 `_meta/source-manifest.md` 登记并回填 `wiki_refs` → **✅ 通过**
- [x] 三页 `tags` 均来自 `_meta/taxonomy.md` 白名单（`memory`、`context-engine`、`tools`、`plugins`、`architecture`） → **✅ 通过**
- [x] 三页均遵守 SCHEMA §4.1 的 5 段结构、`.md` 行数 < 300 → **✅ 通过**

---

## Phase 1 concept / comparison / query 批次自检清单（2026-04-24）

- [x] `tools` / `toolsets`：`concepts/toolset-system.md` 覆盖 `_HERMES_CORE_TOOLS` + `TOOLSETS` + plugin / MCP 三源合并；与 `queries/how-tools-enter-the-model-surface.md` 一起完成"可见性"叙事 → **✅ 通过**
- [x] `tools` / `plugins`：`queries/where-to-add-a-new-tool.md` 建立新工具四通路决策树，解决 `concepts/toolset-system.md` 的 forward wikilink → **✅ 通过**
- [x] `memory`：`concepts/memory-provider-lifecycle.md` 覆盖 init / per-turn / teardown 时间线，消化 backlog 中 "how-memory-provider-hooks-join-the-agent-loop" 的意图 → **✅ 通过**
- [x] `memory` + `context-engine`：`comparisons/memory-provider-vs-context-engine.md` 建立两 ABC 辨析页；`on_pre_compress` 单向桥同时被两个 entity 页反链 → **✅ 通过**
- [x] 四页 `sources` 引入了两个新源（`agent/memory_manager.py`、`hermes_cli/plugins.py`），已同步登记到 `_meta/source-manifest.md` → **✅ 通过**
- [x] 四页 `tags` 均来自 `_meta/taxonomy.md` 白名单（`tools`、`toolsets`、`plugins`、`memory`、`context-engine`、`architecture`、`workflow`） → **✅ 通过**
- [x] 四页均遵守 SCHEMA §4.1/4.2 的最小章节（query/concept 5 段；comparison 含「vs / 不是 / 区别」章） 且 `.md` 行数 < 300 → **✅ 通过**

---

## 升级规则

- 子系统进入 `🟡`：至少 1 个 canary 页（entity / concept / query 任意一种）
- 子系统进入 `✅`：同时满足 entity 页 + concept 页（query 不强制）；或 SCHEMA §4 要求的 5 段结构齐全且 ≥3 页组成局部图
- 永远不要跳过 `🟡` 直接写 `✅`：canary 必须先通过审阅才能批量化

---

## 参考

- 背后的 Phase 计划：`docs/plans/2026-04-24-hermes-local-knowledge-base-review-edition-by-claude.md` §5.3（首批页面规划）、§7（Phase plan）
- 当前 canary 页列表由 `index.md` 「By subsystem」切片同步；本文件与 `index.md` 出现不一致视为 lint error（Phase 2 脚本强制）。
- `_meta/backlog.md` 记录暂缓的页面；每条应能对应到本表一个 ⬜ 子系统。
