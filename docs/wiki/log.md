# Wiki Log

**Append-only 时间线。** 每次 ingest / refresh / schema-bump / lint 批量结果都在此登记一条。
格式：`YYYY-MM-DD | phase-N | <action> | <summary>`。
合法 action：`init` · `ingest` · `refresh` · `canary` · `schema-bump` · `lint` · `drift` · `deviation` · `backlog-move`。

> **规则：** 只追加，不修改历史行；发现登记错误时**新**追加一条 `deviation` 更正，不改旧行。

---

## 2026

### 2026-04-24

- `2026-04-24 | phase-0 | init | Claude Code created skeleton under docs/wiki/ — 4 root files (README, SCHEMA, index, log), 5 _meta files (source-manifest, coverage-map, taxonomy, backlog, deviations), 7 dir .gitkeep (raw, entities, concepts, comparisons, queries, briefs, scripts)`
- `2026-04-24 | phase-0 | canary | 3 pages generated: entities/aiagent, concepts/agent-loop, queries/how-tools-enter-the-model-surface; _meta/source-manifest.md and _meta/coverage-map.md populated with 5 source rows and agent-core + tools/toolsets subsystem coverage`
- `2026-04-24 | phase-1 | ingest | raw/repo-docs/README-20260424.md and raw/repo-docs/AGENTS-20260424.md created as full doc snapshots with SCHEMA §3.3 frontmatter (sha256 7560ab78, c5df3e55); _meta/source-manifest.md backfilled snapshot_path+sha256 for AGENTS.md and added README.md row`
- `2026-04-24 | phase-1 | ingest | raw/code-snapshots/model_tools-20260424.md, raw/code-snapshots/toolsets-20260424.md, raw/code-snapshots/tools_registry-20260424.md created as structured code snapshots with SCHEMA §3.3 frontmatter (sha256 c05266e0, 7d97c6b3, b5693c03); _meta/source-manifest.md backfilled snapshot_path+sha256 for model_tools.py, toolsets.py, tools/registry.py`
- `2026-04-24 | phase-1 | ingest | raw/code-snapshots/agent_memory_provider-20260424.md, raw/code-snapshots/agent_context_engine-20260424.md, raw/code-snapshots/openviking_plugin-20260424.md created as structured code snapshots with SCHEMA §3.3 frontmatter (sha256 fb5a2f8e, faea2b31, d1d4a1a8); _meta/source-manifest.md appended three new rows for agent/memory_provider.py, agent/context_engine.py, plugins/memory/openviking/__init__.py`
- `2026-04-24 | phase-1 | refresh | entities/memoryprovider.md, entities/contextengine.md, entities/tool-registry.md created as entity pages in canary style (SCHEMA §4.1 5-section structure, all under 300 lines); index.md updated across By type / By subsystem / By tag slices; _meta/coverage-map.md advanced Memory and Context engine subsystems ⬜→🟡 and backfilled entity column for Tools, plus Phase 1 entity self-check list appended; _meta/source-manifest.md wiki_refs backfilled for tools/registry.py, agent/memory_provider.py, agent/context_engine.py, plugins/memory/openviking/__init__.py; canary forward wikilinks entities/tool-registry resolved in aiagent + how-tools-enter-the-model-surface`
- `2026-04-24 | phase-1 | refresh | concepts/toolset-system.md, concepts/memory-provider-lifecycle.md, comparisons/memory-provider-vs-context-engine.md, queries/where-to-add-a-new-tool.md created as concept/comparison/query pages in canary style (SCHEMA §4.1/4.2, all under 300 lines); index.md By type / By subsystem / By tag slices refreshed; _meta/coverage-map.md promoted Tools ✅ and Memory ✅, kept Context engine 🟡 and Plugins 🟡 with缺专属 concept/entity notes, Phase 1 concept/comparison/query self-check appended; _meta/source-manifest.md appended agent/memory_manager.py and hermes_cli/plugins.py rows and backfilled wiki_refs for run_agent.py, toolsets.py, tools/registry.py, agent/memory_provider.py, agent/context_engine.py; _meta/backlog.md replaced stale Phase-0 placeholder, populated P2-later with 6 entries (openviking-provider, plugin-system entity, context-engine-lifecycle concept, skills-loading, profile-aware-paths, cli-vs-gateway) and marked queries/how-memory-provider-hooks-join-the-agent-loop.md superseded by concepts/memory-provider-lifecycle.md`
- `2026-04-24 | phase-2 | script | scripts/ingest_seed.py, scripts/lint_wiki.py, scripts/drift_check.py implemented and verified locally; docs/wiki/README.md refreshed to reflect all three maintenance scripts; lint_wiki.py now exits clean in normal and --strict modes after cleanup of temporary lint fixture and forward-link wording in memoryprovider/coverage pages`
- `2026-04-24 | phase-3 | refresh | docs/wiki/README.md finalized for Phase 3 and briefs/onboarding-brief.template.md, briefs/pr-review-brief.template.md, briefs/debug-brief.template.md created; index.md briefs section updated to list available templates`
