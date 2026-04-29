# Source Manifest

**wiki 当前引用的所有源文件登记表。** 每个内容页 frontmatter 的 `sources` 字段必须对应这里的某一行；Phase 2 `lint_wiki.py --strict` 会以本文件为权威校验。

新增源：每次 Claude Code 在 wiki 页 `sources` 中引入新路径，同时在此追加一行；人工 PR 同理。删除：永远不删；标 `supersedes` 指向新行，或留 tombstone。

> **Phase 0 状态说明：** 本期仅登记 canary 页所用的源文件；`snapshot_path` 与 `sha256` 两列待 Phase 1 `ingest_seed.py` 落地后回填，目前统一留 `—`。`wiki_refs` 列暂手工维护，Phase 3 脚本化后自动回填。

---

## Active sources

| source_path | kind | captured_at | snapshot_path | sha256 | supersedes | wiki_refs |
|-------------|------|-------------|---------------|--------|------------|-----------|
| `run_agent.py` | code | 2026-04-24 | — | — | — | `entities/aiagent.md`, `concepts/agent-loop.md`, `queries/how-tools-enter-the-model-surface.md`, `concepts/memory-provider-lifecycle.md`, `comparisons/memory-provider-vs-context-engine.md` |
| `toolsets.py` | code | 2026-04-24 | `raw/code-snapshots/toolsets-20260424.md` | `7d97c6b3` | — | `queries/how-tools-enter-the-model-surface.md`, `concepts/toolset-system.md`, `queries/where-to-add-a-new-tool.md` |
| `model_tools.py` | code | 2026-04-24 | `raw/code-snapshots/model_tools-20260424.md` | `c05266e0` | — | `concepts/agent-loop.md`, `queries/how-tools-enter-the-model-surface.md` |
| `tools/registry.py` | code | 2026-04-24 | `raw/code-snapshots/tools_registry-20260424.md` | `b5693c03` | — | `entities/tool-registry.md`, `queries/how-tools-enter-the-model-surface.md`, `concepts/toolset-system.md`, `queries/where-to-add-a-new-tool.md` |
| `AGENTS.md` | doc | 2026-04-24 | `raw/repo-docs/AGENTS-20260424.md` | `c5df3e55` | — | `entities/aiagent.md`, `concepts/agent-loop.md` |
| `README.md` | doc | 2026-04-24 | `raw/repo-docs/README-20260424.md` | `7560ab78` | — | — |
| `agent/memory_provider.py` | code | 2026-04-24 | `raw/code-snapshots/agent_memory_provider-20260424.md` | `fb5a2f8e` | — | `entities/memoryprovider.md`, `concepts/memory-provider-lifecycle.md`, `comparisons/memory-provider-vs-context-engine.md` |
| `agent/context_engine.py` | code | 2026-04-24 | `raw/code-snapshots/agent_context_engine-20260424.md` | `faea2b31` | — | `entities/contextengine.md`, `comparisons/memory-provider-vs-context-engine.md` |
| `plugins/memory/openviking/__init__.py` | code | 2026-04-24 | `raw/code-snapshots/openviking_plugin-20260424.md` | `d1d4a1a8` | — | `entities/memoryprovider.md` |
| `agent/memory_manager.py` | code | 2026-04-24 | — | — | — | `concepts/memory-provider-lifecycle.md`, `comparisons/memory-provider-vs-context-engine.md` |
| `hermes_cli/plugins.py` | code | 2026-04-24 | — | — | — | `concepts/toolset-system.md`, `queries/where-to-add-a-new-tool.md` |

---

## 列字段定义

- **`source_path`** — 仓库相对路径。唯一主键。
- **`kind`** — `code`（Python/shell 等源码，不做全量快照，Phase 1 生成结构化摘录）、`doc`（markdown 文档，Phase 1+ 做全量快照）、`config`（YAML/JSON/env 模板）
- **`captured_at`** — `YYYY-MM-DD`。首次登记日；快照刷新时保留此列为原始登记日，另在本表追加一行新快照。
- **`snapshot_path`** — `raw/` 下快照位置；`code` 类型永远为 `—`，仅 `doc` / `config` 生成 `raw/repo-docs/*-YYYYMMDD.md`。
- **`sha256`** — 快照文件 sha256 前 8 位；`—` 表示本期未计算（Phase 1 ingest 回填）。
- **`supersedes`** — 旧版 `source_path` 或旧快照路径，或 `—`。
- **`wiki_refs`** — 引用此 source 的 wiki 页列表；Phase 3 脚本自动回填。

---

## 规则

1. **append-only 优先** —— source 被移动 / 删除时**不**删除行；改 `supersedes` 指向新行或留 tombstone。
2. **wiki_refs 双向绑定** —— 任何 wiki 页 `sources` 中出现的路径必须登记于此；反之 `wiki_refs` 列必须与各页 frontmatter `sources` 一致。Phase 2 `lint_wiki.py --strict` 强制校验（SCHEMA §8 rule 7）。
3. **Phase 0 不做快照** —— 本期只登记「哪些源被 canary 页引用」；Phase 1 ingest 才开始落地 `raw/` 快照并回填 `snapshot_path` / `sha256`。
4. **`kind` 取值受限** —— 仅允许 `code` / `doc` / `config`。超出请先在 `deviations.md` 登记并提请审阅。
5. **修改后必打 log** —— 每次增删行都应在 `log.md` 追加 `ingest` 或 `refresh` 条目（canary 首次登记使用 `canary` 动作）。
