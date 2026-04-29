# Hermes 本地知识库 — 审阅版实施方案（review edition）

**日期：** 2026-04-24
**作者：** Claude Code（Opus · max thinking）
**上游输入：** `docs/plans/2026-04-24-hermes-local-knowledge-base-claude-brief.md` + `docs/plans/2026-04-24-hermes-local-knowledge-base-plan.md`（初稿）
**交付物：** 本文一份 markdown 方案；**不改任何仓库文件**。
**状态：** 待 Hermes 分阶段审阅 → 授权后再进入 Phase 0 执行。

> **给执行者（Claude Code）：** 每个 Phase 结束必须停下等待人工审阅，不要自动进入下一个 Phase。Steps 使用 `- [ ]` 勾选。允许偏离方案的唯一场景是：你在阅读代码时发现与方案假设**事实不符** —— 此时先开 issue-page 在 `_meta/deviations.md`，再提请审阅。

---

## 目录

1. Executive summary
2. Recommended architecture（相对初稿的关键改动）
3. Directory structure（含 raw/wiki/schema 映射）
4. Source ingestion strategy
5. Page taxonomy（含 `queries/` vs `briefs/` 拆分）
6. Workflow：收录 → 连接 → 输出
7. Phase plan（含 superpowers-style 任务）
8. Validation plan
9. Risks and non-goals
10. Review checkpoints
11. 附录 A：Brief 12 个关键问题的答复索引
12. 附录 B：必须 / 推荐 / 以后再做
13. 附录 C：维护者契约（Claude Code + Obsidian 用户）

---

## 1. Executive summary

**我们要造什么：** 一个放在 `docs/wiki/` 的 repo-local、markdown、Obsidian 友好、Claude Code 可维护的**编译后知识层**，帮助 Hermes 开发者在 **架构理解 / 调试定位 / 设计评审 / Onboarding / PR review** 时不再每次从 `README.md + grep` 重新开始。

**我们不造什么：**
- 不是运行时 memory provider / context engine（第一阶段坚决不碰 `run_agent.py` / `model_tools.py` / `agent/memory_provider.py`）
- 不是 `AGENTS.md` 的替代品（AGENTS.md 是权威的「开发规则」；wiki 是派生的「理解层」）
- 不是 release notes / chat log / trajectory dump

**核心理念：** 采用 Andrej Karpathy 的 LLM Wiki 模式 —— raw 源不可变，wiki 层由 LLM 增量编译，schema 约束结构，index/log 约束导航与时间线。**与初稿最大的不同**：明确「Obsidian 是推荐前端，不是兼容选项」、「`queries/` 与 `briefs/` 分离」、「先 canary 后批量」、「漂移检测是一等公民」。

**成本与风险：** 第一阶段无代码改动、无新依赖、无运行时风险；产物完全落在 `docs/wiki/` 下，git 可逐文件 review。唯一真实成本是 Claude Code 的 LLM token 开销（估算 <200k tokens 可完成 Phase 0+1+2）。

**建议：** 按 3 次审阅切分放行（见 §10）。

---

## 2. Recommended architecture

### 2.1 三层知识栈（Karpathy 式映射到 Hermes）

| 层 | Hermes 下对应 | 可变性 | 作者 |
|----|---------------|--------|------|
| **raw / source** | `docs/wiki/raw/` —— 只复制或索引，不解释 | **不可变**（append-only） | 人或自动化脚本 |
| **wiki / explained** | `docs/wiki/{entities,concepts,comparisons,queries}/` | 可增量改写 | Claude Code 作为维护者 |
| **meta / governance** | `docs/wiki/SCHEMA.md`、`_meta/*.md` | 慎改，改动留痕 | 人审阅 + Claude 执行 |

### 2.2 相对初稿的关键改动

| # | 初稿 | 审阅版 | 动机 |
|---|------|--------|------|
| 1 | `queries/` 笼统吸收所有「输出」 | 拆成 `queries/`（Q&A 沉淀）+ `briefs/`（一次性工程产出**模板**，非内容） | 让 wiki 面向重复查询；一次性产物仍归 `docs/plans/`、`docs/specs/`，避免 wiki 污染 |
| 2 | Phase 2 一次产 16 页 | Phase 1 先产 3 页 canary，Phase 2 再补到 10 页（8 个核心 + 2 个可选） | 先对齐风格；避免 16 页一次性生成后风格漂移无法回滚 |
| 3 | Lint 只查链路/孤儿/frontmatter | 新增 Hermes-specific 规则（profile 路径、tool 注册、cross-toolset 引用） | lint 必须体现 Hermes 的「已知坑」，否则沦为通用 markdown linter |
| 4 | 没有漂移检测 | 新增 `drift_check.py` —— 对比源文件 mtime 与 wiki 页 `last_refreshed` frontmatter | 这是 Karpathy 式增量编译最容易坏的地方 |
| 5 | Obsidian 只是「兼容」一笔带过 | Obsidian 是推荐前端，`docs/wiki/README.md` 有 Obsidian 配置章节与必装插件清单 | brief 明确要求；也是决定知识库能否被日常使用的关键 |
| 6 | 「人工抽样验证」即为 validation | Validation 分自动 + 半自动 + 人工三档，每档有明确出口 | 初稿的验证靠嘴说，易流于形式 |
| 7 | 没有偏差登记 | 新增 `_meta/deviations.md` —— 执行中与方案不符的事实纠正登记 | 让方案能演化，而不是被悄悄绕开 |

### 2.3 技术栈

- **纯 markdown + frontmatter (YAML)** —— 无外部服务
- **Python 3.11** 维护脚本（与仓库一致，`source venv/bin/activate` 即可运行）
- **Obsidian (推荐前端)** —— 直接把仓库根或 `docs/wiki/` 作为 vault，依赖其原生 wikilinks / graph view
- **Git** —— 唯一的版本存储与协作通道

---

## 3. Directory structure

**位置：** `docs/wiki/` **（维持初稿判断，不挑战）**

**理由（明确回答 brief Q1）：**
- `docs/` 已承载 `plans/`、`specs/`、`migration/`、`skins/` —— wiki 语义同层
- git-friendly，PR review 自然
- 不污染 `~/.hermes/`（运行时用户态）也不污染 `plugins/`（运行时代码）
- Obsidian 只需把仓库根打开为 vault，`docs/wiki/` 作为子目录自动工作

**挑战过但没选的位置：**
- `~/.hermes/wiki/` —— 多机协作差，git 不 track
- 顶层 `wiki/` —— 与仓库已有顶层文档习惯不一致，pollute repo root
- 单独仓库 `hermes-wiki` —— 知识与代码脱钩，第一阶段过重

### 3.1 首期目录树

```text
docs/wiki/
├── README.md                    # 面向人的使用说明（双读者：dev + Claude Code）
├── SCHEMA.md                    # 结构/命名/frontmatter/更新规则（机读 + 人审）
├── index.md                     # 导航入口，按 tag × 类型组织
├── log.md                       # append-only 时间线，记录每次 ingest/refresh
│
├── raw/                         # 不可变源层
│   ├── repo-docs/               # 仓内 markdown 的快照或索引（README/AGENTS/spec）
│   ├── code-snapshots/          # 关键源码的结构化摘录（不复制整文件）
│   ├── skills/                  # 与 skills 系统相关的样本
│   └── assets/                  # 引用到的图片/图表
│
├── entities/                    # 名词页：具体对象
├── concepts/                    # 动词/机制页：系统如何工作
├── comparisons/                 # A-vs-B 页：辨析容易混淆的相邻概念
├── queries/                     # 高频问答沉淀（"如何 X"、"在哪 Y"）
├── briefs/                      # 一次性工程产出的 **模板**（onboarding-brief.md 等）
│
├── _meta/                       # 治理与可观测
│   ├── source-manifest.md       # 当前 wiki 是从哪些 source 构建的
│   ├── coverage-map.md          # 核心子系统 × wiki 页对照表
│   ├── taxonomy.md              # 合法 tags 与类别（lint 参考依据）
│   ├── backlog.md               # 暂不做但已识别的页面需求
│   └── deviations.md            # 实施中与方案不符的事实纠正
│
└── scripts/                     # 本地维护脚本
    ├── ingest_seed.py           # 增量导入 source，生成待更新清单
    ├── lint_wiki.py             # 结构/链接/frontmatter/Hermes 规则检查
    └── drift_check.py           # 源文件 mtime vs 页 last_refreshed 比对
```

### 3.2 raw / wiki / meta 三层职责边界（回答 brief Q3）

| 层 | 允许的内容 | 禁止的内容 |
|----|-----------|-----------|
| `raw/` | 源文件副本、结构化摘录、原路径指针、抓取日期 | 解释、结论、wikilinks |
| `entities/` `concepts/` 等 | 解释、调用链、坑点、wikilinks、frontmatter | 大段源码（用引用或 code-snapshot 链接替代）、版本化的变更日志 |
| `_meta/` | 治理、清单、taxonomy、偏差 | 具体知识页内容 |

**规则：** raw 只能 **append** 新快照（带日期后缀），不能原地覆盖；当你想「更新」raw，实际做的是 append 一个新快照 + 在 `source-manifest.md` 标记旧版 superseded。

### 3.3 四个根文件职责（回答 brief Q7）

| 文件 | 职责 | 被谁读 | 被谁写 |
|------|------|--------|--------|
| `README.md` | 面向人的 30 秒 onboarding；面向 Claude Code 的维护指令总入口 | 新人、Claude Code 会话初始 | Phase 0 一次性，Phase 4 补完 |
| `SCHEMA.md` | 机读级规则：合法目录、合法页类型、frontmatter 字段、wikilink 规范、更新流程 | `lint_wiki.py`、Claude Code | 版本化更新，每次改都打 tag |
| `index.md` | 导航：按 tag、按子系统、按页面类型三个切片 | 人类浏览、Obsidian graph view | 每次 ingest 后自动刷新 |
| `log.md` | append-only 时间线：每次 ingest/refresh/lint 结果摘要 | 审阅者、回溯 | 每个 Phase 与每次增量自动追加 |

**边界陷阱：** `index.md` 不要手写成静态清单 —— Phase 3 的 `ingest_seed.py` 会按 `SCHEMA.md` 规则重生成。在它被脚本化之前，手写内容要加 `<!-- autogen-guarded -->` 标记。

---

## 4. Source ingestion strategy

### 4.1 首批 source 清单（回答 brief Q4）

已核对 `ls` + `AGENTS.md` 的项目结构；以下确认存在：

**A. 顶层说明**（必须）
- `README.md`
- `AGENTS.md`

**B. 核心运行链路**（必须）
- `run_agent.py`
- `model_tools.py`
- `toolsets.py`
- `hermes_state.py`

**C. CLI / 配置 / 插件注册**（必须）
- `cli.py`
- `hermes_cli/config.py`
- `hermes_cli/commands.py`
- `hermes_cli/memory_setup.py`
- `hermes_cli/plugins_cmd.py`

**D. 工具系统**（必须，示范 registry pattern）
- `tools/registry.py`
- `tools/file_tools.py`
- `tools/terminal_tool.py`

**E. 插件扩展面**（必须，是 wiki 最大价值区）
- `agent/memory_provider.py`
- `agent/context_engine.py`
- `plugins/memory/openviking/__init__.py`
- `plugins/memory/openviking/README.md`
- `plugins/context_engine/__init__.py`

**F. 高信号测试与外部 spec**（推荐，帮助对齐语义）
- `tests/test_toolsets.py`
- `docs/honcho-integration-spec.md`
- `docs/acp-setup.md`

**暂不纳入首批：**
- `tools/*.py` 中除 registry/file/terminal 以外的文件（进 backlog）
- `gateway/platforms/*.py`（进 backlog）
- `acp_adapter/`、`cron/`、`environments/`、`tinker-atropos`（进 backlog）
- 任何 `RELEASE_vX.Y.md`（非知识，属 release notes）

**为什么这样切：** 首批的宗旨是「能回答 AGENTS.md 暴露的 5 个最常见问题」（见 §8.3），而不是「覆盖全仓」。registry/memory_provider/context_engine/toolsets 四件套 + README/AGENTS 就能串起 Hermes 的主干。

### 4.2 raw 导入策略

**对文档类 (`.md`)：** 全量快照到 `raw/repo-docs/<name>-<YYYYMMDD>.md`，并在 `source-manifest.md` 登记 `{source_path, snapshot_path, captured_at, sha256}`。

**对源码 (`.py`)：** **不全量复制**。生成结构化摘录：
```markdown
# raw/code-snapshots/agent_memory_provider-20260424.md
source: agent/memory_provider.py
captured_at: 2026-04-24
sha256: <hash>

## Public surface
- class MemoryProvider (abstract)
  - is_available() -> bool
  - initialize(session_id, **kwargs) -> None
  - system_prompt_block() -> str
  - prefetch(query, session_id) -> str
  - sync_turn(user, assistant, session_id) -> None
  - (等等, 每方法一行说明)

## Key invariants
- Built-in provider 始终激活，不可禁用
- 外部 provider 一次只激活一个
- kwargs 契约: hermes_home, platform, agent_context, ...

## Reference
见源文件当前状态: agent/memory_provider.py
```

**理由：** 源码是活的，快照意义不大且体积爆炸；结构化摘录抓住「公开契约」，这是 wiki 真正要长期追踪的东西。

### 4.3 `source-manifest.md` 结构

```markdown
# Source Manifest

| source_path | kind | captured_at | snapshot_path | sha256 | supersedes | wiki_refs |
|-------------|------|-------------|---------------|--------|------------|-----------|
| README.md | doc | 2026-04-24 | raw/repo-docs/README-20260424.md | abc... | — | entities/hermes-agent.md, index.md |
| agent/memory_provider.py | code | 2026-04-24 | raw/code-snapshots/agent_memory_provider-20260424.md | def... | — | entities/memoryprovider.md, concepts/memory-provider-lifecycle.md |
```

`wiki_refs` 列由 `ingest_seed.py` 自动回填（基于 wikilinks grep）。

---

## 5. Page taxonomy

### 5.1 页面类型定义（回答 brief Q5 + Q6）

| 类型 | 一句话定义 | 触发阈值 | 示例 |
|------|-----------|----------|------|
| `entities/` | 一个有名字的对象（类、模块、插件、系统角色） | 跨 2+ 源文件出现，或是插件契约 | `aiagent.md`、`memoryprovider.md`、`tool-registry.md` |
| `concepts/` | 一个机制或流程 | 跨 2+ 源文件、需要调用链才能解释清楚 | `agent-loop.md`、`tool-resolution.md`、`memory-provider-lifecycle.md` |
| `comparisons/` | 两个相邻概念的辨析 | 新人常混淆、或代码中有显式「这个不是那个」注释 | `memory-provider-vs-context-engine.md`、`cli-vs-gateway.md` |
| `queries/` | 高频工程问题的沉淀答案（短、可复用） | 问题真的被问过 ≥2 次，或 AGENTS.md 已经隐含答过 | `how-tools-enter-the-model-surface.md`、`where-to-add-a-new-tool.md` |
| `briefs/` | 一次性工程输出的**模板**（不是内容） | 一类交付物反复产生 | `onboarding-brief.template.md`、`pr-review-brief.template.md`、`debug-brief.template.md` |

### 5.2 `queries/` vs `briefs/` —— 为什么拆开

初稿把「输出」都塞进 `queries/`，但这两个东西有本质差异：

| 维度 | `queries/` | `briefs/` |
|------|-----------|----------|
| 生存期 | 长期（沉淀知识） | 即用即弃（一次性产物） |
| 粒度 | 单个问答 | 完整场景（onboarding、review、debug） |
| 本身是知识还是脚手架 | 知识 | 脚手架（模板） |
| 实例化结果去哪 | 就在 wiki 内 | 实例化到 PR 描述、`docs/plans/`、Slack 消息里，**不回流 wiki** |

**推论：** `briefs/` 不应该存放具体工程产物的实例，只存放模板。这让 wiki 保持「知识库」身份，不变成「过去工作归档」。

### 5.3 首批页面规划（回答 brief Q5）

**Phase 1 canary（3 页）：** 先证明模式，再批量化。

1. `entities/aiagent.md`
2. `concepts/agent-loop.md`
3. `queries/how-tools-enter-the-model-surface.md`

**Phase 2 核心批量（补到 10 页，加入上面 3 页共 10）：**

4. `entities/memoryprovider.md`
5. `entities/contextengine.md`
6. `entities/tool-registry.md`
7. `concepts/toolset-system.md`
8. `concepts/memory-provider-lifecycle.md`
9. `comparisons/memory-provider-vs-context-engine.md`
10. `queries/where-to-add-a-new-tool.md`

**暂缓（进 `_meta/backlog.md`）：** `concepts/skills-loading-and-config.md`、`concepts/profile-aware-paths.md`、`comparisons/cli-vs-gateway.md`、`entities/openviking-memory-provider.md`、`queries/how-memory-provider-hooks-join-the-agent-loop.md` —— 共 5 页，视 Phase 2 表现再决定是否进 Phase 2.5。

### 5.4 页面 frontmatter 强制字段

```yaml
---
title: AIAgent
type: entity
tags: [agent-core, architecture]
sources:
  - run_agent.py
  - agent/prompt_builder.py
wikilinks_out: [tool-registry, memory-provider-lifecycle, toolset-system]
last_refreshed: 2026-04-24
refreshed_by: claude-code
---
```

`sources` 必须都在 `source-manifest.md` 登记；`lint_wiki.py` 会校验。

---

## 6. Workflow：收录 → 连接 → 输出

### 6.1 三阶段工作流（回答 brief Q8）

```
┌─────────────────────────────────────────────────────────────────┐
│                      INGEST（收录）                             │
│  触发：新增/修改源文件；每周定期；手动指定                       │
│  动作：ingest_seed.py --dry-run → 人审 → ingest_seed.py --apply │
│  产出：raw/ 新快照、source-manifest.md 新行、refresh 候选清单   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CONNECT（连接）                            │
│  触发：收录完成后；也可独立于收录由维护者触发                    │
│  动作：Claude Code 基于 refresh 候选清单改写相关 wiki 页         │
│        → 新建需要的 comparison/concept → 更新 index.md          │
│  产出：新 wikilinks、新 comparisons、`log.md` 新条目            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      OUTPUT（输出）                             │
│  触发：有人需要产出一个 PR 描述 / onboarding / debug brief      │
│  动作：从 briefs/<template>.md 拷贝，引用 wiki 页生成实例       │
│        实例写到 PR body / docs/plans / Slack 等外部位置         │
│  产出：工程交付物 —— **不回流 wiki**                            │
└─────────────────────────────────────────────────────────────────┘
```

**关键纪律：**
- OUTPUT 的实例永远不落到 `docs/wiki/` 下（避免 wiki 变成归档堆）
- 但 OUTPUT 阶段如果产生了**高价值问答**，可以在下次 CONNECT 循环中沉淀成 `queries/` 页
- CONNECT 永远伴随 `log.md` 记录，确保可追溯

### 6.2 Obsidian + Claude Code 分工（回答 brief Q8）

| 角色 | 职责 | 工具 |
|------|------|------|
| **Obsidian** | 浏览、导航、graph view、反向链接；轻量笔记和草稿 | 用户本机 |
| **Claude Code** | 增量编译、维护 wikilinks、lint、drift 检测、briefs 实例化 | `claude -p ...` 或交互会话 |
| **人** | 选材料、提问题、审阅增量、决策 page 是否建 | git / PR |

**推荐的 Obsidian 配置（写进 `docs/wiki/README.md`）：**
- Vault = 仓库根（不是 `docs/wiki/`，因为需要能访问 `raw/` 引用到的源文件）
- Core plugins：Backlinks、Outgoing links、Graph view、Tag pane、Templates
- 必装 community plugin（推荐不强制）：`Obsidian Git`（提示本地 vault 与 remote 同步）
- 可选增强：`Obsidian Terminal` 插件直接在 vault 内 `claude -p`（进 backlog，不列入第一期）

### 6.3 维护节奏

| 场景 | 动作 | 节奏 |
|------|------|------|
| 有人改了 §4.1 清单里的某个源文件 | `drift_check.py` 会在下次运行时标红该页 | 建议每周一跑 |
| 新增一个 memory provider | ingest → connect（至少更新 `entities/memoryprovider.md` 的 provider 列表） | 变更当天 |
| 准备一个新功能设计 | 先跑 `briefs/design-brief.template.md` → 引用相关 wiki 页 | 按需 |
| PR review | 先跑 `briefs/pr-review-brief.template.md` → 用 wiki 页定位影响面 | 按需 |
| 新人 onboarding | 先跑 `briefs/onboarding-brief.template.md` | 按需 |

---

## 7. Phase plan

### Phase 0 — 骨架 + canary（审批 A 第一部分）

**目标：** 建立一个「可维护系统」的最小形态。不是一堆散 markdown，而是带治理约束的目录。

**Files:**
- Create: `docs/wiki/README.md`
- Create: `docs/wiki/SCHEMA.md`
- Create: `docs/wiki/index.md`
- Create: `docs/wiki/log.md`
- Create: `docs/wiki/_meta/source-manifest.md`
- Create: `docs/wiki/_meta/coverage-map.md`
- Create: `docs/wiki/_meta/taxonomy.md`
- Create: `docs/wiki/_meta/backlog.md`
- Create: `docs/wiki/_meta/deviations.md`
- Create: `docs/wiki/raw/.gitkeep`、`entities/.gitkeep`、`concepts/.gitkeep`、`comparisons/.gitkeep`、`queries/.gitkeep`、`briefs/.gitkeep`、`scripts/.gitkeep`

**Tasks:**

- [ ] **Step 0.1 — 创建目录骨架**
  - `mkdir -p docs/wiki/{raw,entities,concepts,comparisons,queries,briefs,_meta,scripts}`
  - 每个空目录放 `.gitkeep`

- [ ] **Step 0.2 — 写 `SCHEMA.md`（规则版）**
  - 定义 5 个页面类型（§5.1）
  - 定义强制 frontmatter 字段（§5.4）
  - 定义合法 tags（列出 §11.1 的 16 个）
  - 定义 wikilink 格式：`[[type/slug]]`，不允许 relative path
  - 定义文件名规范：`kebab-case`、`.md`
  - 定义「页必须存在的最小章节」（TL;DR、责任边界、调用链/关系、坑点、References）

- [ ] **Step 0.3 — 写 `README.md`（入口版）**
  - 5 行 TL;DR：这是什么、哪儿放、谁读、谁写、为什么不是 AGENTS.md 的替代
  - 「新人 30 秒上手」流程：打开 Obsidian → 读 `index.md` → 按 tag 找子系统
  - 「Claude Code 维护会话」最小指令（见附录 C）
  - Obsidian 配置章节（§6.2 详展开）

- [ ] **Step 0.4 — 写 `index.md`（种子版）**
  - 三个切片（by type / by subsystem / by tag）都创建但只有占位行
  - 顶部放 `<!-- autogen-guarded -->` 注释，说明此文件会在 Phase 3 后被脚本刷新

- [ ] **Step 0.5 — 写 `log.md`（首条记录）**
  - 记录：`2026-04-24 | phase-0 | init | Claude Code created skeleton under docs/wiki/`

- [ ] **Step 0.6 — 写 `_meta/taxonomy.md`（tag 清单 + 禁用词）**
  - 允许 tags（§11.1）
  - 显式禁止的 tag：`misc`、`general`、`notes`、`todo`

- [ ] **Step 0.7 — 写 `_meta/backlog.md`（占位）**
  - 首行：「当前为空；Phase 1 canary 通过审阅后由 Claude Code 填入暂缓页面」

- [ ] **Step 0.8 — 生成 canary：`entities/aiagent.md`**
  - 按 SCHEMA 最小形式：frontmatter + 5 个强制章节
  - 明确 source: `run_agent.py`
  - 至少 2 条 wikilinks（向 `tool-registry` 和 `memory-provider-lifecycle` —— 这两个页还不存在，但 Phase 2 会建，所以暂时是「未来链接」，lint 会标 warning 而非 error）

- [ ] **Step 0.9 — 生成 canary：`concepts/agent-loop.md`**
  - 必须包含调用链图（ASCII 或 mermaid）
  - 必须引用 `run_agent.py:run_conversation` 的伪代码段（来自 AGENTS.md 的 loop 代码块）

- [ ] **Step 0.10 — 生成 canary：`queries/how-tools-enter-the-model-surface.md`**
  - 要能在不打开任何源文件的前提下，让读者知道：
    1. 工具如何被 registry 发现（tools/registry.py 的 `register()`）
    2. 工具集如何过滤（toolsets.py 的 `_HERMES_CORE_TOOLS`）
    3. schema 如何进 API 请求（model_tools.py 的 `get_tool_definitions`）

- [ ] **Step 0.11 — 手工 append `log.md`**
  - `2026-04-24 | phase-0 | canary | 3 pages generated: aiagent, agent-loop, how-tools-enter-the-model-surface`

**Phase 0 验收：**
- 目录结构完整存在
- `SCHEMA.md` 可被「一个陌生的 Claude Code」理解并据以产页（这是 Phase 0 最硬的标准）
- 3 个 canary 页通过人工审阅：风格、粒度、frontmatter、wikilinks 质量均 OK
- **审阅者对三个 canary 页的风格明确签字**，Phase 1 不允许偏离此风格

**⛔ Gate 1：** 未获审阅者书面确认 canary 合格前，不得进入 Phase 1。

---

### Phase 1 — Seed raw + 补齐核心批量页（审批 A 第二部分）

**目标：** 把 §4.1 的 source 都进 raw 层，把 §5.3 的 10 页补齐。

**Files:**
- Create: `docs/wiki/raw/repo-docs/README-20260424.md`
- Create: `docs/wiki/raw/repo-docs/AGENTS-20260424.md`
- Create: `docs/wiki/raw/code-snapshots/run_agent-20260424.md`
- Create: `docs/wiki/raw/code-snapshots/model_tools-20260424.md`
- Create: `docs/wiki/raw/code-snapshots/toolsets-20260424.md`
- Create: `docs/wiki/raw/code-snapshots/tools_registry-20260424.md`
- Create: `docs/wiki/raw/code-snapshots/agent_memory_provider-20260424.md`
- Create: `docs/wiki/raw/code-snapshots/agent_context_engine-20260424.md`
- Create: `docs/wiki/raw/code-snapshots/openviking_plugin-20260424.md`
- Modify: `docs/wiki/_meta/source-manifest.md`
- Create: `docs/wiki/entities/memoryprovider.md`
- Create: `docs/wiki/entities/contextengine.md`
- Create: `docs/wiki/entities/tool-registry.md`
- Create: `docs/wiki/concepts/toolset-system.md`
- Create: `docs/wiki/concepts/memory-provider-lifecycle.md`
- Create: `docs/wiki/comparisons/memory-provider-vs-context-engine.md`
- Create: `docs/wiki/queries/where-to-add-a-new-tool.md`
- Modify: `docs/wiki/index.md` (registers 10 pages)
- Modify: `docs/wiki/log.md` (appends Phase 1 entries)
- Modify: `docs/wiki/_meta/coverage-map.md`
- Modify: `docs/wiki/_meta/backlog.md` (登记 5 个暂缓页)

**Tasks：** 按 §4 + §5 执行。每批 3 页为一个子提交（`git add docs/wiki/... && git commit`），便于 review。

**关键 guard rails：**
- 每次新建页都要同步更新 `source-manifest.md` 的 `wiki_refs` 字段
- 页面之间必须至少形成一个闭环 wikilink 图（不能 10 页全部只单向指向 canary）
- 每个 comparison 页必须明确说「这两个东西不是什么」—— 否则沦为罗列

**Phase 1 验收：**
- `git ls-files docs/wiki/ | wc -l` ≥ 30
- `grep -l "wikilinks_out" docs/wiki/**/*.md | wc -l` = 10（10 个内容页）
- 人工抽样：从 `index.md` 随机点 3 个链接，能在 2 跳内找到源文件路径
- `source-manifest.md` 的 wiki_refs 列每个源都至少有 1 个页引用

**⛔ Gate 2：** Phase 1 的所有页面必须经一次 PR review（即使是自 merge），以让审阅者整体看到风格一致性。

---

### Phase 2 — 维护脚本（审批 B）

**目标：** 让知识库不是一次性成果。

**Files:**
- Create: `docs/wiki/scripts/ingest_seed.py`
- Create: `docs/wiki/scripts/lint_wiki.py`
- Create: `docs/wiki/scripts/drift_check.py`

#### 2.1 `ingest_seed.py` 契约

```
Usage:
  python docs/wiki/scripts/ingest_seed.py --dry-run
  python docs/wiki/scripts/ingest_seed.py --apply
  python docs/wiki/scripts/ingest_seed.py --source README.md --apply

Behavior (dry-run):
  - 读取 _meta/source-manifest.md 中所有登记的 source
  - 对每个 source: stat mtime, compute sha256
  - 如果 sha256 与上次记录不同 → 列为「待 refresh 候选」
  - 打印列表到 stdout，不写任何文件

Behavior (--apply):
  - 等同 dry-run，但同时为每个候选 append 一个新 snapshot 到 raw/
  - 更新 source-manifest.md（旧行加 supersedes 标记，新行带当天日期）
  - 不改动 wiki 页（连接步骤是人 + Claude Code 的事，不自动化）

Exit codes:
  0 — 无变化，或 apply 成功
  1 — apply 冲突（如目标 snapshot 已存在）
  2 — manifest 损坏

Stdout sample (dry-run):
  Candidate refreshes (2):
    - agent/memory_provider.py (sha256 changed: abc → def, mtime 2026-04-24 → 2026-04-25)
      affects: entities/memoryprovider.md, concepts/memory-provider-lifecycle.md
    - toolsets.py (sha256 changed: ... )
      affects: concepts/toolset-system.md, queries/where-to-add-a-new-tool.md
  Up-to-date: 7
```

#### 2.2 `lint_wiki.py` 契约

```
Usage:
  python docs/wiki/scripts/lint_wiki.py
  python docs/wiki/scripts/lint_wiki.py --strict   # 警告也算失败

Checks (generic):
  - 所有 md 有强制 frontmatter 字段
  - 所有 wikilinks 目标存在
  - 无 orphan page（不在 index.md 中出现）
  - frontmatter tags 全部在 taxonomy.md 中
  - 页面长度 <= 300 行（超过要拆）

Checks (Hermes-specific):
  - 任何 body 提到 "~/.hermes" 字面量的页，必须也提到 get_hermes_home() 或 profile
  - 任何 body 提到 "register a tool"/"添加工具" 的页，必须至少 wikilink 到 tool-registry
  - 任何 body 提到 "memory provider" 的页，必须至少 wikilink 到 memoryprovider
  - comparison 页必须显式含 "不是" 或 "vs" 或 "区别" 的章节
  - queries/ 页必须引用 ≥1 entity 或 concept 页

Exit codes:
  0 — 全部通过
  1 — 有 error（default：frontmatter 缺失、broken link、orphan、非法 tag）
  2 — 有 warning 且 --strict（default：Hermes-specific 规则）
```

#### 2.3 `drift_check.py` 契约

```
Usage:
  python docs/wiki/scripts/drift_check.py
  python docs/wiki/scripts/drift_check.py --days 14

Behavior:
  - 读取每个 wiki 页的 frontmatter.last_refreshed
  - 读取 source-manifest.md 中 sources 的当前 mtime（相对仓库根）
  - 如果 source mtime > last_refreshed + N days (default 7) → 列为 drifted
  - 输出 markdown 表格到 stdout，可直接粘贴到 issue

Stdout sample:
  | page | source | source_mtime | page_last_refreshed | days_stale |
  |------|--------|--------------|---------------------|-----------|
  | entities/memoryprovider.md | agent/memory_provider.py | 2026-04-30 | 2026-04-24 | 6 |

Exit codes:
  0 — 无 drift
  1 — 有 drift
```

**Phase 2 验收：**
- 三个脚本都能在 `source venv/bin/activate` 后无外部依赖（或仅标准库 + `pyyaml`）运行
- `lint_wiki.py` 对当前 Phase 1 产物 exit 0
- `drift_check.py` 对当前产物 exit 0（所有 source 刚刚捕获）
- `ingest_seed.py --dry-run` 不修改任何文件（用 `git status` 验证）

**⛔ Gate 3：** Phase 2 合并前，必须至少跑一次**真实**流程：人为修改一个 `.py` 源文件的注释 → `ingest_seed.py --dry-run` 应报出候选 → 回滚修改。

---

### Phase 3 — Obsidian & briefs & README 收尾（审批 C）

**目标：** 让 Obsidian + Claude Code 的工作流可被新人复现；让 briefs 有模板。

**Files:**
- Modify: `docs/wiki/README.md`（最终版，含 Obsidian 章节与 Claude Code 维护会话范式）
- Create: `docs/wiki/briefs/onboarding-brief.template.md`
- Create: `docs/wiki/briefs/pr-review-brief.template.md`
- Create: `docs/wiki/briefs/debug-brief.template.md`

**README 需要的章节：**
1. 这是什么
2. 它不是什么（明确：不替代 AGENTS.md、不是归档）
3. 30 秒浏览路径
4. Obsidian setup（§6.2 的完整展开：vault 根、必装插件、推荐 workspace 布局）
5. Claude Code 维护会话范式（附录 C）
6. 工作流：收录 → 连接 → 输出（§6.1 的用户版）
7. 脚本速查（ingest / lint / drift）
8. 贡献规则（新建页流程、命名规则、何时拆页）

**briefs/ 模板要求：**
- 纯脚手架，不含具体内容
- 每个模板开头有 YAML 头：`usage:` 一句话说明何时用
- 模板引用到的 wikilink 用 `[[placeholder-page]]` 形式占位，实例化时替换

**Phase 3 验收：**
- 新人能按 README 配出 Obsidian 环境（人工测试一次即可）
- 拿 `onboarding-brief.template.md` 在 5 分钟内实例化出一份针对「memory 子系统」的 onboarding brief

---

## 8. Validation plan

### 8.1 自动验证（CI-friendly）

| 项 | 命令 | 期望 |
|----|------|------|
| 结构完整 | `ls docs/wiki/{raw,entities,concepts,comparisons,queries,briefs,_meta,scripts}` | 全部存在 |
| frontmatter | `python docs/wiki/scripts/lint_wiki.py` | exit 0 |
| 严格 lint | `python docs/wiki/scripts/lint_wiki.py --strict` | exit 0 |
| 漂移检测 | `python docs/wiki/scripts/drift_check.py` | exit 0（Phase 2 刚完成时） |
| ingest dry-run 不副作用 | `python docs/wiki/scripts/ingest_seed.py --dry-run && git status --porcelain` | 输出为空 |

### 8.2 半自动验证（grep-able）

| 项 | 方法 | 期望 |
|----|------|------|
| wikilink 密度 | `grep -oE '\[\[[^\]]+\]\]' docs/wiki/**/*.md \| wc -l` | ≥ 30（10 页，均值 3 条） |
| 引用源文件比例 | `grep -l 'sources:' docs/wiki/entities/*.md docs/wiki/concepts/*.md docs/wiki/queries/*.md \| wc -l` | = 页面总数 |
| 无 orphan | lint_wiki.py 结果 | no orphan warnings |

### 8.3 实用性人工抽样（回答 brief Q12）

**Bar：拿着 wiki，在不打开任何 `.py` 文件的前提下，能否在 5 分钟内回答以下问题？**

1. Hermes 的 tools 是如何进入 model surface 的？（应能 1 跳找到）
2. memory provider 与 context engine 的区别？（应能在 `comparisons/memory-provider-vs-context-engine.md` 直接读到）
3. 新加一个 tool 需要改哪些文件？（应能在 `queries/where-to-add-a-new-tool.md` 直接读到）
4. 为什么不能硬编码 `~/.hermes`？（应能在引用 profile-aware-paths 的页找到）
5. OpenViking 在 Hermes 里扮演什么角色？（应能在 `entities/memoryprovider.md` 的 provider 列表里找到指针）

**5 个问题中至少 4 个通过 → wiki 可用。**

### 8.4 可持续性验证

- Phase 2 完成 2 周后（约 2026-05-08），让另一个 Claude Code 会话只读 `docs/wiki/README.md + SCHEMA.md`，尝试新增一个 wiki 页（例如 `entities/gateway-session-store.md`）
- 如果它不需要进一步澄清就能产出合规页 → 维护契约立住
- 如果它频繁问「frontmatter 应该写什么」「这个 tag 合法吗」→ SCHEMA.md 或 README.md 需补强

---

## 9. Risks and non-goals

### 9.1 非目标（第一阶段坚决不做，回答 brief Q11）

| 不做项 | 理由 | 何时可考虑 |
|--------|------|-----------|
| 接入 memory provider / context engine | brief 明确禁止；也会破坏 prompt caching | Phase 3+ |
| 向量检索 / 本地 RAG | 违反「local-first 纯 markdown」原则 | 只在 wiki 规模 > 100 页时才有意义 |
| 改 `run_agent.py` / `model_tools.py` / `toolsets.py` | 第一阶段零运行时改动 | 一旦改动，就不再是「知识库」项目 |
| `runbooks/` | 与 AGENTS.md 重叠；先观察是否真有缺口 | Phase 3 评估 |
| 自动生成整份 wiki（scrape 全仓） | Karpathy 明确反对；人必须参与选材 | 永远不做 |
| 接入 Mem0 / Honcho / Hindsight | 与 wiki 目标正交；先把 wiki 做好 | 与运行时集成讨论一起 |
| `.obsidian/` 强制入库 | 每人 vault 偏好不同；会污染 git | 永远不做（README 给推荐配置即可） |
| GitHub Action / pre-commit hook | 先证明脚本本地跑得通；再加 CI | Phase 3+ |

### 9.2 主要风险与对策

| 风险 | 触发场景 | 对策 |
|------|---------|------|
| **风险 A：页面成为 README 复述** | Claude Code 在页里直接抄源码注释 | SCHEMA.md 强制 5 章节，其中「责任边界」「坑点」是硬性要求 |
| **风险 B：wiki 滞后于代码** | 运行时快速迭代，wiki 半年不更新 | `drift_check.py` 每周跑；超过 14 天 drift 的页进 backlog |
| **风险 C：raw 与 wiki 混淆** | 有人把解释写进 raw snapshot | SCHEMA.md 明确：raw 禁止 wikilinks + frontmatter 必须 `kind: snapshot` |
| **风险 D：页面数爆炸后失控** | 3 个月后 50+ 页、tag 乱、孤儿多 | lint 在 `orphan` + `unknown tag` 上 fail；页总数 > 25 触发 `coverage-map.md` 强制回顾 |
| **风险 E：Obsidian 配置门槛劝退** | 新人没 Obsidian，读 raw markdown 不愿意用 | README 明确说：「纯 VS Code + preview」也能用；Obsidian 只是推荐 |
| **风险 F：briefs 模板被当内容用** | 有人往 briefs/ 塞实际 PR 描述 | SCHEMA 明文禁止；lint 对 briefs/*.template.md 以外文件 warn |
| **风险 G：一次性 LLM 生成风格漂移** | Phase 2 一次产 10 页风格不一 | 分 3 子提交 + Phase 1 canary 先定型 |
| **风险 H：过早把 wiki 接入 runtime** | 有人想把 wiki 塞进 memory provider 作为 prefetch 数据源 | §9.1 明确列为非目标；SCHEMA.md 开头写明「非 runtime 依赖」 |

---

## 10. Review checkpoints

**三次审阅（建议切分）：**

### ⛔ Gate 1（审批 A）：Phase 0 骨架 + 3 个 canary 页

**触发条件：** Phase 0 完成。

**审阅者需确认：**
- 目录结构与方案一致
- `SCHEMA.md` 规则清晰、可执行
- 3 个 canary 页的**风格**获得明确签字（粒度、tone、wikilink 质量、章节深度）
- 不同意 canary 风格的话，回炉重练 —— **不允许在此阶段放行到 Phase 1**

**产物尺寸：** 预计 ~12 文件、<3000 行 markdown。

### ⛔ Gate 2（审批 B）：Phase 1 + 10 页 + source-manifest

**触发条件：** Phase 1 完成。

**审阅者需确认：**
- 10 页整体风格一致（不退步于 canary）
- source-manifest.md 的 wiki_refs 双向一致
- index.md 可用作导航入口
- 至少随机点 3 页能在 2 跳内定位到源码

**产物尺寸：** 预计 +20 文件、+5000 行。

### ⛔ Gate 3（审批 C）：Phase 2 + Phase 3（脚本 + 工作流收尾）

**触发条件：** Phase 2 与 Phase 3 均完成。

**审阅者需确认：**
- 三个脚本都能本地跑通、exit code 正确
- drift 回归测试通过
- README 里 Obsidian 章节能被新人跟做
- briefs/ 模板能即时实例化

**产物尺寸：** +3 脚本、+4 文档。

### 审阅之外：2 周后的持续性检查（软 gate）

- 2026-05-08：第二 Claude Code 会话冷启动产页测试（§8.4）
- 如不通过 → `deviations.md` 登记 → 补强 SCHEMA / README

---

## 11. 附录 A — Brief 12 个关键问题的答复索引

| # | 问题 | 简答 | 详见 |
|---|------|------|------|
| 1 | 知识库放哪里？为什么？ | `docs/wiki/`；git-friendly + Obsidian vault 子目录 + 不污染 runtime | §3 |
| 2 | 首期目录结构？ | entities/concepts/comparisons/queries/briefs + raw + _meta + scripts | §3.1 |
| 3 | raw/wiki/schema 映射？ | raw 不可变源层 / wiki 可演化解释层 / SCHEMA + _meta 治理层 | §3.2 |
| 4 | 首批 ingest 哪些 source？ | README + AGENTS + run_agent + model_tools + toolsets + registry + memory_provider + context_engine + openviking + 2 测试 + honcho/acp 两份 spec | §4.1 |
| 5 | 首批生成哪些 page？ | Phase 1 canary 3 页；Phase 2 补到 10 页；5 页进 backlog | §5.3 |
| 6 | 要不要 outputs / queries 层？怎么设计？ | **拆** —— `queries/` 做 Q&A 沉淀（知识）；`briefs/` 做一次性产出**模板**（脚手架），实例不回流 wiki | §5.2 |
| 7 | README / SCHEMA / index / log 职责？ | 人口 / 机读规则 / 导航 / 时间线 | §3.3 |
| 8 | Obsidian + Claude Code 如何纳入？ | Obsidian 是**推荐**前端（不是兼容）；Claude Code 是维护者；README 含配置指南 | §6.2 |
| 9 | 需要哪些维护脚本？ | `ingest_seed.py` + `lint_wiki.py` + `drift_check.py` 三件套 | §7 Phase 2 |
| 10 | 三阶段各做什么？ | Phase 0 骨架+canary；Phase 1 raw+10 页；Phase 2 脚本；Phase 3 Obsidian+briefs | §7 |
| 11 | 什么坚决不在第一阶段做？ | runtime 集成、向量检索、Mem0/Honcho、runbooks、自动全仓 scrape、CI hook | §9.1 |
| 12 | 如何验证有效？ | 3 档验证（auto/grep/人工）；5 个基准问题 ≥ 4 通过；2 周后冷启动复现 | §8 |

### 11.1 合法 tags（taxonomy 首版）

`agent-core` · `cli` · `gateway` · `tools` · `toolsets` · `skills` · `memory` · `context-engine` · `plugins` · `testing` · `config` · `paths` · `provider` · `architecture` · `workflow` · `onboarding`

---

## 12. 附录 B — 必须 / 推荐 / 以后再做

### 必须做（第一阶段放行即需完成）

- `docs/wiki/` 目录骨架
- `SCHEMA.md` / `README.md` / `index.md` / `log.md` / `_meta/*.md` 齐全
- Phase 1 的 3 个 canary 页
- Phase 2 的 10 页核心批量
- `source-manifest.md` 双向一致
- `lint_wiki.py` 含 Hermes-specific 规则

### 推荐做（第一阶段内，审阅者可豁免）

- `drift_check.py`
- `briefs/` 三个模板
- Obsidian setup 章节
- `_meta/deviations.md` 空文件加占位

### 以后再做（显式延后，放 `_meta/backlog.md`）

- `runbooks/`
- 插件系统（gateway/acp/cron/environments）的 wiki 页
- 与 memory provider / context engine 的 runtime 集成
- CI hook（lint on PR）
- Obsidian Terminal 插件配置范式
- 跨项目 wiki 模板化（把本方案抽象成 skill）
- 中英双语页面

---

## 13. 附录 C — 维护者契约

### C.1 Claude Code 的「维护会话」契约（写进 `docs/wiki/README.md`）

**增量导入场景：**
```bash
claude -p "You are maintaining docs/wiki/. Read docs/wiki/SCHEMA.md and docs/wiki/README.md. Then run: python docs/wiki/scripts/ingest_seed.py --dry-run. For each candidate, decide: (a) which wiki pages need refresh, (b) whether a new page is warranted. Do NOT apply. Output a refresh plan with file-level diffs." --allowedTools "Read,Bash"
```

**连接/改写场景：**
```bash
claude -p "Refresh docs/wiki/entities/memoryprovider.md based on the current agent/memory_provider.py. Preserve frontmatter structure. Update wikilinks_out if new entities were referenced. Append a log.md entry. Run docs/wiki/scripts/lint_wiki.py --strict at the end." --allowedTools "Read,Write,Edit,Bash" --max-turns 10
```

**briefs 实例化场景：**
```bash
claude -p "Using docs/wiki/briefs/pr-review-brief.template.md, produce a review brief for PR #NNNN. Cite relevant wiki pages. Output to stdout — do NOT write to docs/wiki/." --allowedTools "Read,Bash"
```

### C.2 Obsidian 用户契约

- Vault 根 = 仓库根（不是 `docs/wiki/`）
- 不把 `.obsidian/` 提交到 git（已在 `.gitignore` 默认排除，Phase 0 确认一次）
- 任何笔记/草稿放 `docs/wiki/_meta/deviations.md` 或 backlog；**不要**直接新建 `entities/xxx.md`，先让 Claude Code 按 SCHEMA 生成
- Graph view 是主要工具：孤立节点 = 应补 wikilinks 或进 backlog

### C.3 审阅者契约

- 每个 Gate 明确签字（PR 评论或 commit 消息引用 gate 编号）
- canary 阶段不签字就不放行；宁愿 Phase 1 多跑一次，不要 Phase 2 十页返工
- 每 2 周跑一次 drift_check；drift > 14 天的页进当周修复清单
- `deviations.md` 每月一次 review；是否升级为 SCHEMA / README 更新

---

**（方案正文完）**