# Personal Wiki Master Architecture — 审阅版方案（review edition）

- **作者**：Claude (opus-4-7, effort=max)
- **日期**：2026-04-24
- **配套 brief**：`docs/plans/2026-04-24-personal-wiki-master-architecture-and-bootstrap-claude-brief.md`
- **状态**：Part A 产出。方案落地由 Part B 执行。本文档本身不创建任何 wiki 文件。
- **主路径**：`/Users/ryuka/personal-wiki/`（即将由 Part B 创建）
- **Hermes 子库路径**：`/Users/ryuka/Documents/GitHub/hermes-agent/docs/wiki/`（已有，本次不动）

---

## TL;DR

1. 现有 `docs/wiki/` 是 Hermes repo 专属的**项目子库**，锚定代码仓库生命周期。它不具备长期、跨领域、跨项目、与个人记忆连接的能力。
2. 需要一个**独立于任何 repo 的个人总库**，部署在 `/Users/ryuka/personal-wiki/`，和 Hermes repo 解耦。
3. 二级结构：**总库（master）** 负责跨域知识与长期概念、**子库（sub）** 负责项目内精确知识。Hermes 子库通过 `domains/hermes/` 入口页被总库“感知”，但不被复制或迁移。
4. 跨域连接靠三类载体：`concepts/`（抽象概念）、`comparisons/`（跨域比较）、`queries/`（问题驱动的组合页）。第一阶段各出 1 个 canary。
5. Taxonomy 重新起盘。Hermes 子库的 16-tag 白名单是代码域专用，**不能直接外推**。总库用 13-tag 跨域白名单。
6. 项目切换是**寻址问题**而非代码问题。总库提供 `_meta/coverage-map.md` 作为索引，Hermes agent 将来查询子库路径与上下文打包范围就能完成“切换”。本阶段只建骨架。
7. 知识库（wiki）= 可检索、结构化、手动维护、跨会话持久。记忆（claude-mem / runtime memory）= 会话轨迹、观察流、机器维护。两者相互索引，但不互替代。
8. Phase 1 只落 9 根文件 + 3 canary 页 + 空目录骨架，**不做内容扩写、不做脚本、不做 ingest、不做 Hermes 迁移**。

---

## 1. 为什么现有 Hermes repo-local wiki 只是子库，不是总库

观察事实（已在 Hermes 子库实际存在并通过 Phase 0-3 构建）：

- 路径绑定：`/Users/ryuka/Documents/GitHub/hermes-agent/docs/wiki/` 位于 Hermes git 仓库内，随 repo clone / branch / 归档。
- 内容绑定：`_meta/source-manifest.md` 只声明代码源和 repo 文档源（如 `hermes/model_tools.py`、`tools/registry.py`、`AGENTS.md`），**没有也不应有**“小说第三章”“AI 短视频 hook 案例库”这类条目。
- Taxonomy 绑定：16-tag 白名单（例如 `provider`、`tool-registry`、`memory-provider`、`runtime`）全是代码域名词，标完即死，外推到小说/短视频等于污染。
- Lint 规则绑定：`scripts/lint_wiki.py` 的 schema 把 brief-template 结构、entity 必填字段、代码 snapshot 哈希、orphan 检查都写死成 Hermes 规约。
- 生命周期绑定：当 Hermes 被归档、更名、fork 上游时，这份 wiki 的路径与内容都会一起断裂。
- 主体绑定：它服务的主体是**“维护 Hermes 这个 codebase 的工程师”**，不是**“ryuka 这个人”**。

结论：repo-local wiki 是 Hermes 工程知识快照与治理机制，**不是**用户的长期知识中枢。两者的主体、路径、生命周期、taxonomy、工具链都不同。用它当总库会出现四类冲突：域外知识会被 lint 拒绝、跨域概念会被 source-manifest 拒绝、Hermes 归档会拖累个人知识、其他项目无法共享 taxonomy。

---

## 2. 总库 / 子库的两级架构

```
┌─────────────────────────────────────────────────────┐
│  /Users/ryuka/personal-wiki/   (MASTER / 个人总库)   │
│  - 主体：用户长期知识中枢                             │
│  - 生命周期：与 macOS 用户账户绑定，不随任何 repo    │
│  - 负责：跨域概念 / 跨域比较 / 跨域查询 / 域导航       │
│                                                     │
│  domains/                                           │
│  ├── hermes/          ── 入口页 + 指向子库路径        │
│  ├── fiction/         ── 入口页（未来可含子库）        │
│  ├── ai-short-video/  ── 入口页（未来可含子库）        │
│  └── workflows/       ── 跨域通用工作流               │
└───────────────┬─────────────────────────────────────┘
                │ 通过 coverage-map + 子库入口页引用
                ▼
┌─────────────────────────────────────────────────────┐
│ SUB-LIBRARIES (项目/领域子库，各自独立生命周期)       │
│                                                     │
│ /Users/ryuka/Documents/GitHub/hermes-agent/docs/wiki │
│   — Hermes 工程子库（已有 Phase 0-3）                │
│                                                     │
│ <未来> fiction 子库（可能嵌在小说项目 repo 中）       │
│ <未来> ai-short-video 子库（可能嵌在视频 repo 中）    │
└─────────────────────────────────────────────────────┘
```

**关键契约**：

- 总库**只引用、不复制**子库内容。子库里 `hermes/docs/wiki/concepts/tool-registry.md` 继续在子库维护；总库 `domains/hermes/README.md` 只记录入口路径 + 子库摘要。
- 总库可以**沉淀子库中通用化的概念**。例如 Hermes 的 `brief` 写作规约如果证明是通用方法论，可**原创**一页 `concepts/brief-writing.md` 在总库（不拷贝子库原文），并在其 "Relates to" 里 wikilink 回子库入口页。
- 子库**不感知总库存在**。子库是总库的下游引用对象，但不依赖总库运行。这保证子库在 repo 被分享、归档、fork 时仍自洽。

---

## 3. 推荐本地绝对路径与目录结构

**总库绝对路径**：`/Users/ryuka/personal-wiki/`

选择理由：
- 不放在 `~/Documents/GitHub/`，因为它不是 git 项目（虽然 Part B+ 可以 `git init`，但它不该被视作“项目”）。
- 不放在 iCloud 同步路径（`~/Documents` 实际可能开启 iCloud Drive 时会同步），**本次保守放到** `$HOME` 根下的 `personal-wiki/`，避开 iCloud 延迟/冲突。
- 不放进 Obsidian vault 默认路径，避免跟未来 Obsidian 配置耦合。Obsidian 可以把 `/Users/ryuka/personal-wiki/` 作为 vault 打开，但不强依赖。
- 全小写、kebab-case、无空格，保证 CLI / wikilink 友好。

**第一阶段骨架**（照 brief 要求，这里是最终形态约定）：

```
/Users/ryuka/personal-wiki/
├── README.md                     # 总库入口与使用约定
├── SCHEMA.md                     # 总库 schema（跨域版，非 Hermes 规约）
├── index.md                      # 人工维护的页面清单
├── log.md                        # 变更日志（append-only）
├── _meta/
│   ├── taxonomy.md               # 跨域 tag 白名单 v0
│   ├── source-manifest.md        # 外部源清单（书、课程、仓库、论文等）
│   ├── coverage-map.md           # 域覆盖度与子库入口索引
│   ├── backlog.md                # 待建 / 待整理
│   └── deviations.md             # 暂不遵守 schema 的例外记录
├── domains/
│   ├── hermes/                   # 入口页 + 指向子库
│   ├── fiction/
│   ├── ai-short-video/
│   └── workflows/
├── entities/                     # 命名实体（人物、工具、产品、组织、作品）
├── concepts/                     # 抽象概念（跨域通用）
├── comparisons/                  # 两个及以上对象的对比
├── queries/                      # 问题驱动的组合页
├── briefs/                       # 面向 agent 的简报与工作指令
├── raw/
│   ├── articles/                 # 文章原文 snapshot
│   ├── notes/                    # 临时笔记 / 手写速记
│   └── imports/                  # 从外部工具导入的原文件
└── scripts/                      # 预留；第一阶段不产出脚本
```

与 Hermes 子库的**结构差异**（刻意）：
- 新增 `domains/`：总库特有，作域路由。
- 新增 `raw/imports/`：总库需要吞外部导出（iA Writer、Notion、ChatGPT 导出等），子库不需要。
- `scripts/` 暂留空：第一阶段明确不产出 `ingest_seed.py` / `lint_wiki.py` / `drift_check.py` 的总库版本。它们应在 **Phase 3** 之后参照子库经验重建，taxonomy 和路径规则不同，不能直接拷贝。
- `entities/` 语义比子库更宽：子库中 `entities/` = 代码中的类/模块/服务；总库中 `entities/` = 世界上的具体物（人、书、工具、项目）。

---

## 4. 哪些内容放总库，哪些放子库

判定表（作为 Phase 1 及之后的落盘依据）：

| 内容类型 | 放总库 | 放子库 | 判定要点 |
|---|---|---|---|
| 代码文件 snapshot | ✗ | ✓ | snapshot 与 repo 绑定，归档时跟 repo 走 |
| 某 repo 的 `AGENTS.md` snapshot | ✗ | ✓ | 仅对该 repo 有效 |
| 跨项目复用的 brief 写作方法论 | ✓ | ✗ | 原创页面放 `concepts/`，不是拷贝 |
| 小说章节稿 | ✗ (见右列) | ✓ (若小说项目成立 repo) | 若尚无项目，暂放总库 `raw/` 并标注 `status: pending-extraction` |
| 小说角色设定、世界观 | ✓ | — | `entities/` + `concepts/` |
| AI 短视频单条脚本草稿 | ✗ | ✓ (若有创作 repo) | 同小说 |
| AI 短视频 hook 模式库 | ✓ | — | `concepts/`、`comparisons/` |
| 通用生产力工作流（如「一日双创」） | ✓ | — | `domains/workflows/` |
| 个人履历 / 学习笔记 / 读书笔记 | ✓ | — | `entities/person-*`、`raw/articles/` |
| Hermes 上游 release note 追踪 | ✗ | ✓ | 属于 Hermes 工程治理 |
| 「写小说 vs 做短视频」对比策略 | ✓ | — | `comparisons/` 典型 |
| Hermes 某次 incident 复盘 | ✗ | ✓ | 项目内经验 |
| 从上述复盘中抽象出的「多 agent 调度模式」 | ✓ | ✗ | 已脱离 Hermes 代码上下文的抽象 |

**一个反复出现的判定启发**：**如果这条知识在 Hermes repo 归档后仍有用，就放总库。**

---

## 5. 总库如何支持跨域连接

跨域连接靠三类页面和一套 tag 约定：

### 5.1 Three connector page types

- **`concepts/<name>.md`** — 抽象单元。例如 `story-hook.md` 可以同时被小说域和短视频域引用，天然跨域。
- **`comparisons/<a>-vs-<b>.md`** — 显式对比。例如 `novel-hook-vs-short-video-hook.md` 把两域里表面相似的对象并列，抽公共结构与差异。
- **`queries/<question>.md`** — 问题驱动。例如 `how-to-link-fiction-and-ai-short-video-workflows.md` 从用户实际需求出发，横向组装多个域的知识片段。

### 5.2 Wikilink conventions

- 所有跨域引用**必须**用 `[[path/to/page]]` 相对 wikilink，不写 HTML 链接。
- 连接 Hermes 子库时**不用 wikilink**（因为子库不在同一个 vault），用常规 markdown 链接到绝对路径或 repo 内相对路径，且由 `_meta/coverage-map.md` 显式登记。Hermes 子库的内部 wikilink 继续在子库里用。
- 禁止 `../../../` 跨库路径污染；跨库引用只从 `domains/<name>/README.md` 出发。

### 5.3 Tag-based 横向索引

Taxonomy v0（见 §9）里有一组**跨域 tag**，例如 `hooks`、`narrative`、`adaptation`、`cross-domain`。当一个 `concepts/` 页同时挂 `fiction` 与 `ai-short-video`，Obsidian 或 grep 就能把两域下共用此概念的页聚拢。

### 5.4 示例连接（第一阶段 canary 所体现的形态）

```
concepts/story-hook.md
   ├─ tags: [storytelling, hooks, narrative, cross-domain]
   ├─ 被引用：
   │   ├─ comparisons/novel-hook-vs-short-video-hook.md
   │   └─ queries/how-to-link-fiction-and-ai-short-video-workflows.md
   └─ Relates to:
       ├─ domains/fiction/
       └─ domains/ai-short-video/
```

这是第一阶段唯一需要闭合验证的连接图。

---

## 6. Hermes 将来如何基于总库 + 子库进行项目切换

**核心观点：项目切换不是代码问题，是寻址问题。**

本阶段不写任何 runtime 代码。下列是方案层面约定，Phase 4+ 才会落到 Hermes runtime。

### 6.1 总库端的职责

- `_meta/coverage-map.md` 维护一张**域 → 子库路径 + 子库摘要 + active/archived 状态**的表，作为权威索引。
- `domains/<name>/README.md` 作为每个域的“入口简报”，包含：子库绝对路径、子库构建状态、进入该子库该读哪些页、出该子库时应带走哪些记忆摘要。
- `briefs/<task>.md` 作为 agent 接手具体任务时的参照。例如 `briefs/work-on-hermes-release-upgrade.md`。

### 6.2 Hermes runtime 端的未来约定（仅方案，不实现）

- Hermes 读取 `coverage-map.md` + 当前任务 brief → 决定上下文载入哪个子库的哪些页。
- 切换项目 = 切换 brief 指向的 domain 入口 + 切换 memory 摘要命名空间（如 claude-mem 的 corpus）。
- 总库的 `concepts/` 永远默认在上下文池中。子库是按需载入。

### 6.3 为什么本阶段只建骨架

- 不预先设计没有消费者的 API。等 Hermes runtime 真的要切项目时，再据现状设计接口。
- 但**入口页 (`domains/*/README.md`) 的形状现在就要定对**，否则后面会一次性重写。这也是第一阶段必须落 `domains/hermes/` 入口页的原因。

### 6.4 第一阶段 `domains/hermes/README.md` 应包含的字段（作为 Part B 的硬约束）

- `domain_name`
- `sub_library_path: /Users/ryuka/Documents/GitHub/hermes-agent/docs/wiki/`
- `sub_library_status: active | stale | archived`
- `entry_pages: [...]`（子库中最重要的 3-5 页入口路径）
- `memory_namespace: hermes-agent`（对齐 claude-mem project 名）
- `last_synced_at`（人工维护的 sanity check 时间戳）

---

## 7. 知识库与记忆之间如何分工

两者是互补机制，不是冗余。

| 维度 | 知识库（personal-wiki） | 记忆（claude-mem / runtime memory） |
|---|---|---|
| 主体 | 用户手工或 agent 审阅后维护 | agent 在会话中自动写入 |
| 形态 | markdown + frontmatter + wikilink | 观察条目 + 向量索引 |
| 粒度 | 页（>= 数百字） | 观察（一句到数句） |
| 稳定性 | 长期稳定，需要刻意更新 | 高频变动，衰减快 |
| 查找方式 | 文件检索 + wikilink 遍历 + 人工目录 | mem-search 语义查询 |
| 角色 | 结构化、可版本化的“事实与概念地图” | 会话事件流“我最近做过什么、学过什么” |
| 失效风险 | 过时（stale），但不消失 | 过多噪音，需要定期压缩 |

**接口约定（方案层，Phase 3+ 再实现）：**

- wiki 的 `_meta/source-manifest.md` 里引用某条外部源时，可以再加一行 `memory_query_hint:` 指示 claude-mem 去查什么 keyword。
- claude-mem 的重要观察（例如一条决策 ⚖️）将来应允许“提升”到 wiki 的 `concepts/` 或 `entities/`，但这属于后续阶段。
- **不要**把 claude-mem 观察整批 dump 进 wiki。总库要的是**提炼后的条目**，不是事件流。

**一条实操规则**：如果一个念头 24 小时后仍觉得重要，才写进 wiki；否则让它留在记忆里。

---

## 8. 第一阶段（Bootstrap）应落哪些文件

### 8.1 Phase 0 — 空目录骨架（Part B step 1）

在 `/Users/ryuka/personal-wiki/` 下 `mkdir` 以下目录（全部为空，不放 `.gitkeep`，因为第一阶段不 `git init`）：

```
_meta/
domains/hermes/
domains/fiction/
domains/ai-short-video/
domains/workflows/
entities/
concepts/
comparisons/
queries/
briefs/
raw/articles/
raw/notes/
raw/imports/
scripts/
```

### 8.2 Phase 1 — 9 根文件 + meta（Part B step 2）

所有文件必须带 frontmatter。frontmatter schema 见 §8.5。

| # | 路径 | 角色 | 必含要点 |
|---|---|---|---|
| 1 | `README.md` | 总库入口 | 总库目的 / 目录说明 / 与 Hermes 子库的关系 / 读者如何开始 |
| 2 | `SCHEMA.md` | 总库规约 | frontmatter schema / 各目录允许的页类型 / wikilink 约定 / 跨库引用规则 |
| 3 | `index.md` | 人工目录 | 列出 Phase 1 所有已创建页 (含 canary) |
| 4 | `log.md` | 变更日志 | 一条创建记录：Phase 1 bootstrap, 日期, 文件清单 |
| 5 | `_meta/taxonomy.md` | tag 白名单 v0 | 13 tag，按 §9 分组 |
| 6 | `_meta/source-manifest.md` | 外部源清单 | 第一阶段可为空表 + 表头 + 字段说明 |
| 7 | `_meta/coverage-map.md` | 域覆盖度 | 4 个 domain 的入口状态（hermes=active, 其余=seed） |
| 8 | `_meta/backlog.md` | 待办 | 明确列出 Phase 2/3 目标（见 §10） |
| 9 | `_meta/deviations.md` | 例外登记 | 第一阶段唯一例外：`scripts/` 目录为空、未 lint、未 ingest；列明原因 |

### 8.3 Phase 1 — 3 canary 页（Part B step 3）

| 路径 | 类型 | 作用 |
|---|---|---|
| `concepts/story-hook.md` | concept | 验证一个抽象概念页能被两个域同时引用 |
| `comparisons/novel-hook-vs-short-video-hook.md` | comparison | 验证跨域比较页能引用 concept 与两个 domain 入口 |
| `queries/how-to-link-fiction-and-ai-short-video-workflows.md` | query | 验证问题驱动页能集成 concept、comparison、两个 domain |

### 8.4 Phase 1 — domain 入口页（Part B step 4）

同时必须建立的隐含文件（brief 未明说，但 coverage-map 和 canary wikilink 需要它们存在，否则 orphan）：

| 路径 | 内容最小版本 |
|---|---|
| `domains/hermes/README.md` | §6.4 全部字段 + 一句话描述 |
| `domains/fiction/README.md` | 域名、目的、status=seed、无子库路径 |
| `domains/ai-short-video/README.md` | 同上 |
| `domains/workflows/README.md` | 域名、目的、status=seed、说明这是跨域通用工作流栖息地 |

> 审阅建议：Part B 执行时务必同步建这 4 个入口页，否则 canary 的 `[[domains/fiction/...]]` wikilink 会是 dangling。如果严格按 brief 只建 9+3 文件，会出现断链。**请 Part B 在执行前确认此偏差，并在 `deviations.md` 或 brief 补丁中合法化它。**

### 8.5 Frontmatter schema v0（由 `SCHEMA.md` 规范化）

所有内容页（README / SCHEMA / index / log 除外）顶部：

```yaml
---
title: <人类可读标题>
type: concept | comparison | query | entity | domain | brief | note
domain: [hermes | fiction | ai-short-video | workflows | cross-domain, ...]
tags: [<taxonomy.md 白名单子集>]
status: seed | draft | stable | stale
created: 2026-04-24
updated: 2026-04-24
relates_to: [[wikilink1]], [[wikilink2]]
sources: []     # 指向 _meta/source-manifest.md 条目 id，第一阶段可空
---
```

根级文件（README/SCHEMA/index/log）frontmatter 最简：`title`、`type: meta`、`updated`。

### 8.6 Phase 1 验证清单（Part B 自检）

- [ ] 9 根文件全部存在、frontmatter 合法
- [ ] 3 canary 页全部存在、frontmatter 合法
- [ ] 4 domain README 全部存在
- [ ] canary 之间双向可达：concept ↔ comparison ↔ query
- [ ] 每个 canary 至少 1 条 wikilink 指向 `domains/*/README.md`
- [ ] `index.md` 列出上述 9 + 3 + 4 = 16 个文件
- [ ] `log.md` 追加一条「Phase 1 bootstrap」记录，含日期与文件数
- [ ] `_meta/coverage-map.md` 标明 hermes=active, 其余=seed
- [ ] `_meta/deviations.md` 显式记录 scripts/ 空、未 lint、未 ingest
- [ ] grep `\[\[` 确认没有指向不存在路径的 wikilink（dangling-link 手工巡检）

---

## 9. Taxonomy v0 — 跨域白名单（非 Hermes-only）

Hermes 子库的 16 个 tag 是代码域词汇（`provider`、`tool-registry`、`memory-provider`、`runtime` 等），**不能直接迁移**。总库 v0 白名单如下，共 13 个，分 4 组：

### 9.1 Domain tags（5）
- `hermes-engineering`
- `fiction`
- `ai-short-video`
- `workflow`
- `tooling`

### 9.2 Structural tags（4）
- `knowledge-design`
- `memory`
- `project-switching`
- `cross-domain`

### 9.3 Narrative tags（3）
- `hooks`
- `narrative`
- `adaptation`

### 9.4 Reserved（1）
- `storytelling`（作为 `fiction` 与 `ai-short-video` 之上更高层父 tag）

### 9.5 明确禁用（避免与 Hermes 子库 taxonomy 混淆）

`provider`、`tool-registry`、`memory-provider`、`runtime`、`telegram`、`discord` 等 Hermes-only tag **不进总库**。如果总库页需要谈 Hermes 内部组件，就用 `hermes-engineering` + wikilink 到子库入口，而非复用子库 tag。

### 9.6 Taxonomy 扩展规则

- 任何新 tag 必须先在 `_meta/taxonomy.md` 注册，说明用途与示例页。
- 一个页的 tags 数量上限 6，超出必须拆页或换 comparison/query 形式。
- 每季度做一次 tag 使用频次审计，出现频次 < 3 的 tag 考虑合并。

### 9.7 Taxonomy 审阅建议

brief 给了 13 个候选 tag，这里全数采纳，仅加入 `storytelling` 作为父 tag（共 14 - 1 reserved = 13 活跃 + 1 储备）。若 Part B 严格要求 13 个，可把 `storytelling` 延到 Phase 2，不影响 canary。建议**保留 13+1** 方案，因为 canary `concepts/story-hook.md` 天然挂 `storytelling`。

---

## 10. 后续扩展路线

按 Phase 粒度推进，每 Phase 可独立验证、可回滚。

### Phase 2 — 结构加固（不扩内容）

- 在 `scripts/` 实现总库版 `lint_wiki.py`。**不直接拷贝 Hermes 子库版本**，schema 与目录规则不同。
- 在 `SCHEMA.md` 里机器可读化 frontmatter rules（参照 Hermes 子库 SCHEMA.md 的机器可读片段风格，但 tag 白名单换成总库版）。
- `lint_wiki.py --strict` 必须对 Phase 1 产出全绿。
- `_meta/deviations.md` 清空其中「未 lint」这一条。

### Phase 3 — ingest 与 drift 检测

- 实现 `scripts/ingest_seed.py` 总库版。与子库版差异：总库源非代码、为文章/书/视频等，frontmatter 与 sha 策略不同。
- 实现 `scripts/drift_check.py` 总库版。对 `_meta/source-manifest.md` 进行来源活性检查（例如 URL 4xx、本地文件不存在）。
- `raw/articles/` 开始被 ingest 使用。

### Phase 4 — Hermes runtime 接入（第一次动 Hermes 代码）

- 为 Hermes 增加读取 `~/personal-wiki/_meta/coverage-map.md` 与 `domains/hermes/README.md` 的能力。
- 项目切换能读总库 brief 与子库入口页，打包成 context。
- 不做向量检索；第一版就是路径加载 + markdown 解析。

### Phase 5 — 其他域实体化

- `fiction` 与 `ai-short-video` 子库按需建立。可能的位置：
  - `/Users/ryuka/Documents/GitHub/<novel-project>/docs/wiki/`
  - `/Users/ryuka/Documents/GitHub/<video-project>/docs/wiki/`
- 各自子库遵循总库提供的 schema（Phase 2 输出），而不是 Hermes 子库的代码 schema。

### Phase 6 — 记忆-知识双向同步（谨慎）

- 设计 claude-mem 观察 → wiki 页的“提升”流程（半自动，需人工确认）。
- 设计 wiki 页变更 → claude-mem 摘要的反向同步。
- 本 Phase 前不要触碰此机制。

### 非目标（至少 Phase 4 前不做）

- 向量数据库 / RAG
- 自动同步 / 自动 ingest
- 复杂项目切换机制代码
- 迁移 Hermes 子库内容到总库
- Obsidian 插件 / 自定义 CSS
- 任何 git remote 推送

---

## 11. 审阅问题（Part B 执行前建议与用户确认）

1. `/Users/ryuka/personal-wiki/` 路径 ok？是否要加 `.iCloudIgnore` / 确认不在 iCloud 同步目录？
2. Phase 1 是否 `git init`？本方案倾向**不 init**，等 Phase 2 lint 稳定后再 init。
3. `domains/*/README.md` 4 个入口页是否同步建（§8.4）？brief 没明说但 wikilink 需要。建议：**建**。
4. taxonomy 是 13 还是 14（加 `storytelling`）？建议：**14（13 活跃 + 1 储备）**。
5. `_meta/source-manifest.md` 第一阶段要不要预登记 Hermes 子库作为外部源？建议：**不登记**。子库由 `coverage-map.md` 管。source-manifest 留给文章/书/课程。

> 若用户未特别回复，Part B 按上述默认建议执行，并在 `_meta/deviations.md` 中登记所有默认取舍。

---

## 12. 附录：与 Hermes 子库的边界契约（硬约束）

- Part B 执行中**不得**读写 `/Users/ryuka/Documents/GitHub/hermes-agent/docs/wiki/` 下任何文件。
- Part B 执行中**不得**修改 `/Users/ryuka/Documents/GitHub/hermes-agent/` 下除本 plans 目录外的任何文件。
- 总库 `domains/hermes/README.md` **只允许**记录路径与元信息，**不允许**抄录子库页内容。
- 若子库路径变更（未来 Hermes 改名），总库仅更新 `domains/hermes/README.md` 与 `_meta/coverage-map.md`。

## 13. 附录：验证命令（Part B 完成后手动跑）

```bash
# 目录存在
ls /Users/ryuka/personal-wiki

# 全部根文件 + canary 存在
ls /Users/ryuka/personal-wiki/{README.md,SCHEMA.md,index.md,log.md}
ls /Users/ryuka/personal-wiki/_meta/{taxonomy,source-manifest,coverage-map,backlog,deviations}.md
ls /Users/ryuka/personal-wiki/concepts/story-hook.md
ls /Users/ryuka/personal-wiki/comparisons/novel-hook-vs-short-video-hook.md
ls /Users/ryuka/personal-wiki/queries/how-to-link-fiction-and-ai-short-video-workflows.md
ls /Users/ryuka/personal-wiki/domains/{hermes,fiction,ai-short-video,workflows}/README.md

# frontmatter 存在（每个内容页首三行应含 '---'）
for f in $(find /Users/ryuka/personal-wiki -name '*.md' -not -name 'log.md' -not -name 'index.md' -not -name 'README.md'); do head -1 "$f" | grep -q '^---$' || echo "MISSING FRONTMATTER: $f"; done

# dangling wikilink 粗查
grep -rhoE '\[\[[^]]+\]\]' /Users/ryuka/personal-wiki | sort -u
```

---

## 结束语

本方案严格限定 Part A 范围：**只产出本文档**，不动任何 wiki 文件，不动 Hermes 子库。后续 Part B 依据 §8 直接落 Phase 1 bootstrap。Phase 2 起由用户单独命令触发。
