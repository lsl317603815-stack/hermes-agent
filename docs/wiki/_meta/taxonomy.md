# Taxonomy

**合法 tag 白名单。** 页 frontmatter 的 `tags` 字段必须全部来自本文件；`lint_wiki.py`（Phase 2）会拒绝未列出的 tag。

新增 tag 需走审阅：PR 改本文件，理由写 commit 消息，log.md 追加 `schema-bump` 条目。

---

## 合法 tags（16 个，首版）

| tag | 适用范围 | 样例页（现有或计划） |
|-----|---------|------------------|
| `agent-core` | AIAgent 主类、顶层协调、conversation flow | [[entities/aiagent]], [[concepts/agent-loop]] |
| `cli` | `cli.py`、`hermes_cli/*`、slash command registry、skin engine | _Phase 1+_ |
| `gateway` | `gateway/*`、platform adapters、cross-platform messaging | _backlog_ |
| `tools` | `tools/*.py`、registry、tool registration/discovery | [[queries/how-tools-enter-the-model-surface]] |
| `toolsets` | `toolsets.py`、`_HERMES_CORE_TOOLS`、toolset resolution | [[queries/how-tools-enter-the-model-surface]] |
| `skills` | `~/.hermes/skills/`、skill commands、skill manage tool | _backlog_ |
| `memory` | `agent/memory_provider.py`、OpenViking、Mem0 / Honcho 插件 | _Phase 1+_ |
| `context-engine` | `agent/context_engine.py`、compaction、context window 管理 | _Phase 1+_ |
| `plugins` | `plugins/*`、`hermes_cli/plugins.py`、plugin discovery | _Phase 1+_ |
| `testing` | `tests/*`、smoke test、高信号 tests 用作语义对齐 | _Phase 1+_ |
| `config` | `config.yaml`、`.env`、`load_cli_config()` 等配置层 | _Phase 1+_ |
| `paths` | profile-aware paths、`get_hermes_home()`、`~/.hermes` | _Phase 1+_ |
| `provider` | inference provider 切换、模型路由、acp | _Phase 1+_ |
| `architecture` | 跨子系统的架构叙事（不该被任何单一 tag 概括时） | [[entities/aiagent]], [[concepts/agent-loop]] |
| `workflow` | 开发工作流、PR review、onboarding 流程 | [[concepts/agent-loop]] |
| `onboarding` | 面向新人的导引页；briefs 中 onboarding 模板 | _Phase 3 briefs_ |

---

## 显式禁止的 tag

以下 tag 在任何页 frontmatter 中出现都会触发 lint error。

- `misc` —— 若你想用它，说明页面主题不清；请先决定真正的 tag 或拆页
- `general` —— 同上
- `notes` —— wiki 不收散碎笔记；写到 `_meta/deviations.md` 或 `_meta/backlog.md`
- `todo` —— 未完成的事进 `_meta/backlog.md`，不作为 tag

---

## tag 选用指引

- **每页至少 1 个、至多 4 个 tag**。多于 4 个通常意味着页面粒度太大，应拆页。
- 必须包含至少一个**子系统 tag**（`agent-core` / `cli` / `gateway` / `tools` / `toolsets` / `skills` / `memory` / `context-engine` / `plugins` / `config` / `paths` / `provider`）。
- `architecture`、`workflow`、`onboarding`、`testing` 是**横切 tag**，不能单独作为子系统代表。
- 同义词不要并用：用 `memory` 不用 `memory-system`；用 `paths` 不用 `filesystem` / `locations`。

---

## 新增 tag 的判断门槛

加一个 tag 之前自问：

1. 是否已经有 tag 能**勉强**涵盖这个页？→ 如果能，先用旧 tag；tag 数量克制是第一原则
2. 至少 2 个实际或计划中的页会用这个 tag 吗？→ 少于 2 个不加
3. 是否与子系统/横切这两层分类逻辑自洽？→ 否则考虑是否真的需要改分类模型

通过 3 个门槛 → 改本文件 + log.md 追加 `schema-bump` + PR。
