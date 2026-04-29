# Backlog

**已识别但暂不做的页。** 分三档：`P1-soon` / `P2-later` / `deferred`。

Phase 0 canary 与 Phase 1 entity + concept/comparison/query 两批已交付；下列 P2-later 条目以 `_meta/coverage-map.md` 的 🟡 / ⬜ 子系统为触发依据。计划上下文：`docs/plans/2026-04-24-hermes-local-knowledge-base-review-edition-by-claude.md` §5.3。

---

## P1-soon（Phase 1 可能触及）

_暂无。Phase 1 的 entity + concept/comparison/query 两批均已交付；剩余页面整体归属 Phase 2 及以后。_

---

## P2-later（Phase 2 考虑）

- **`entities/openviking-memory-provider.md`**
  - 为什么延后：`entities/memoryprovider.md` 已覆盖 ABC 契约；OpenViking 作为目前唯一满实现仅以 forward wikilink 占位，暂无第二实现对比需求。
  - 触发条件：`plugins/memory/openviking/__init__.py` 有非日常改动，或新增第二个 external provider 进入 `MemoryManager.add_provider` 的 external 槽位（需要做实现对比）。
- **`entities/plugin-system.md`**
  - 为什么延后：`plugins` 子系统在 coverage-map 仍为 🟡（仅借 `concepts/toolset-system.md` + `queries/where-to-add-a-new-tool.md` 切入），缺专属 entity 描述 `PluginContext` 的 registration surface。
  - 触发条件：新增非 memory 类 plugin（context engine plugin、通用工具 plugin）时 `hermes_cli/plugins.py` 的 `PluginContext` 表面足以独立建 entity。
- **`concepts/context-engine-lifecycle.md`**
  - 为什么延后：`context-engine` 子系统在 coverage-map 为 🟡（仅 entity + 共享 comparison），缺专属 concept 页串起 `update_from_response` / `should_compress` / `compress` / `on_session_start`-`on_session_reset`-`on_session_end` 的 per-turn 与真边界时序。
  - 触发条件：第二个 engine 实现落地（LCM 之后的第二种压缩范式），或 compression cadence / preflight 策略需要跨 entity 统一解释。
- **`concepts/skills-loading-and-config.md`**
  - 为什么延后：`skills` 子系统在 coverage-map 为 ⬜；本批未触及 skills 运行时；entity 页也尚未建立。
  - 触发条件：skills 加载路径出现实质变更，或与 memory provider / context engine 的交互（例如 skill 触发注入上下文）需要 wiki 化。
- **`concepts/profile-aware-paths.md`**
  - 为什么延后：`config` / `paths` 子系统在 coverage-map 为 ⬜；`hermes_home` / profile 目录语义目前零散出现在 entity / lifecycle 页的 §坑点，未统一成文。
  - 触发条件：profile-aware 路径语义在 CLI vs gateway 出现系统性分歧，或 plugin 作者反复误用 `hermes_home` kwarg。
- **`comparisons/cli-vs-gateway.md`**
  - 为什么延后：`cli` / `gateway` 子系统均为 ⬜，对比需要两侧 entity 页先行；现阶段主要边界只在 `agent_context` kwarg + 路由工具上。
  - 触发条件：新增平台入口（signal / wecom 等）使两者分界点已呈系统性，或 `agent_context` 写入策略在非 primary 分支进一步分化。

---

## Superseded（已被其它页吸收，不再作为独立 backlog 条目）

- **`queries/how-memory-provider-hooks-join-the-agent-loop.md`**
  - 状态：吸收进 `concepts/memory-provider-lifecycle.md`（init / per-turn / 真边界 三段已完整覆盖原规划意图，包含 `on_pre_compress` 作为 provider ↔ context engine 的唯一桥）。
  - 反向指针：`_meta/coverage-map.md` 「Phase 1 concept / comparison / query 批次自检清单」已记录该吸收决定。

---

## deferred（显式延后，不在本期路线图）

_来自方案附录 B — "以后再做"：_

- `runbooks/` —— 与 AGENTS.md 重叠；先观察是否真有缺口
- Gateway / ACP / Cron / Environments / Tinker-Atropos 的 wiki 覆盖
- 与 memory provider / context engine 的 runtime 集成
- CI hook（lint on PR）
- Obsidian Terminal 插件配置范式
- 跨项目 wiki 模板化（把本方案抽象成 skill）
- 中英双语页面

---

## 新增 backlog 条目的契约

- 每条至少写：**slug** + **为什么延后** + **触发条件（何时升级到 P1/P2）**
- 若某条已在 `deviations.md` 中登记为方案偏差，这里只放反向指针
- 每月 review：P2-soon 条目 > 30 天 → 升级到 P1 或降级到 deferred
