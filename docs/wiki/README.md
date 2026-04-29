# Hermes Wiki

**本仓库的编译后知识层。** 为 Hermes 开发者在「架构理解 / 调试定位 / 设计评审 / Onboarding / PR review」时提供一个不用每次都从 `README.md + grep` 重新开始的导航入口。

---

## 30 秒 TL;DR

- **这是什么：** `docs/wiki/` 下的 repo-local、markdown、Obsidian 友好、Claude Code 可维护的知识库
- **放在哪儿：** `docs/wiki/`（git 一起走，不污染 `~/.hermes/` 或 `plugins/`）
- **谁读：** 新人、Claude Code 会话、PR 审阅者
- **谁写：** Claude Code 做增量编译；人类选材、提问、审阅
- **不是什么：** 不替代 `AGENTS.md`（那是开发规则的权威）；不是 release notes；不是 chat log；不是 runtime memory provider / context engine

---

## 它是什么

- **Repo-local 的派生知识层。** `AGENTS.md` 与源码是权威；wiki 是把它们**编译**成便于浏览、反向链接、graph view 的形式。
- **增量维护的。** 每次源文件变动后，走 `scripts/ingest_seed.py` → Claude Code 连接改写 → `scripts/lint_wiki.py --strict` 的小步循环，不做一次性全量生成。
- **分层治理的。** `raw/`（不可变源层）→ `entities/` / `concepts/` / `comparisons/` / `queries/`（解释层）→ `briefs/`（一次性产出模板）→ `_meta/`（治理层）。规则详见 [[SCHEMA]]。
- **多读者设计的：**
  - **新人** 打开 Obsidian graph view 看全局；
  - **Claude Code 会话** 读 [[SCHEMA]] + 本页后自助维护；
  - **PR 审阅者** 从 `_meta/source-manifest.md` 的 `wiki_refs` 反查受影响的页。

## 它不是什么（硬边界）

- **不替代 `AGENTS.md`：** AGENTS.md 是权威的「开发规则」；wiki 是派生的「理解层」。若两者冲突，以 AGENTS.md 为准。
- **不是归档：** 一次性交付物（具体 PR 描述、onboarding 邮件、debug 报告）**不**回流 wiki；它们属于 `docs/plans/`、PR body、Slack 等位置。wiki 只保存「模板」（`briefs/`）与可重用的「知识」。
- **非 runtime 依赖：** 任何运行时代码（`run_agent.py` / `model_tools.py` / `agent/memory_provider.py` / `agent/context_engine.py`）不得加载本 wiki 文件。详见 [[SCHEMA]] §10。
- **不是 release notes / changelog。** 不记录版本变更；变更由 git history + PR description 追溯。
- **不是向量检索 / RAG / 聊天记录。** 纯 markdown + wikilinks，Obsidian graph view 是唯一导航工具。

---

## 30 秒浏览路径

1. 打开 Obsidian（或任一 markdown viewer），以**仓库根**为 vault。
2. 打开 [[index]]。
3. 按 **tag** / **子系统** / **页面类型** 三个切片之一找感兴趣的入口。
4. 每页结构固定：TL;DR → 责任边界 → 调用链 / 关系 → 坑点 → References。
5. 沿 wikilinks 继续跳转；Obsidian graph view 帮你看全局。

常用起点：

- **Agent 主流程** → [[entities/aiagent]] → [[concepts/agent-loop]]
- **工具系统** → [[entities/tool-registry]] → [[concepts/toolset-system]] → [[queries/how-tools-enter-the-model-surface]]
- **插件 / 扩展面** → [[entities/memoryprovider]] · [[entities/contextengine]]
- **新工具放哪** → [[queries/where-to-add-a-new-tool]]
- **不确定归哪类页** → [[SCHEMA]] §1

---

## Obsidian setup（推荐前端）

### Vault 根 = 仓库根

> **不要**把 vault 设为 `docs/wiki/`。wiki 的 `raw/` 层会引用仓库内源文件路径（如 `run_agent.py`），vault 根对齐仓库根才能让这些相对路径生效。

1. 安装 Obsidian：https://obsidian.md/
2. 新建 vault → **Open folder as vault** → 选择 `hermes-agent/` 仓库根。
3. 首次打开时 Obsidian 会创建 `.obsidian/` —— 此目录**不入 git**（依赖仓库 `.gitignore` 默认排除；如缺失请手动补上 `.obsidian/`）。

### 必装核心插件（Settings → Core plugins）

- **Backlinks** —— 必开，wiki 的反向链接靠它。
- **Outgoing links** —— 必开，方便看当前页去向。
- **Graph view** —— 必开，孤立节点 = 应补 wikilinks 或进 backlog。
- **Tag pane** —— 必开，按 `_meta/taxonomy.md` 导航。
- **Templates** —— 可选，若你经常从 `briefs/*.template.md` 实例化。

### 推荐社区插件（非强制）

- **Obsidian Git** —— 提示本地 vault 与 remote 同步状态。
- **Obsidian Terminal** —— 可选增强，用于直接在 vault 内跑 `claude -p`（进 backlog，不列入第一期）。

### 推荐 workspace 布局

- 左栏：文件树 + Tag pane
- 中栏：当前页
- 右栏：Backlinks + Outgoing links + Graph view（local mode）

### 用其它 viewer 也能用

README / SCHEMA / index / log 都是纯 markdown，**VS Code + markdown preview** 能读。Obsidian 是推荐前端，不是硬依赖 —— 不用 Obsidian 知识库依然可用，只是 graph view 与反向链接体验会差一些。

---

## Claude Code 维护会话范式

所有维护会话的起手式：先读 [[SCHEMA]] + 本页（[[README]]），再读目标页；收尾必须以 `python docs/wiki/scripts/lint_wiki.py --strict` exit 0 为终点，并在 [[log]] 追加一条动作记录。

### 增量导入（ingest · dry-run）

```bash
claude -p "You are maintaining docs/wiki/. Read docs/wiki/SCHEMA.md and docs/wiki/README.md. Then run: python docs/wiki/scripts/ingest_seed.py --dry-run. For each candidate, decide: (a) which wiki pages need refresh, (b) whether a new page is warranted. Do NOT apply. Output a refresh plan with file-level diffs." --allowedTools "Read,Bash"
```

### 连接 / 改写（connect）

```bash
claude -p "Refresh docs/wiki/entities/memoryprovider.md based on the current agent/memory_provider.py. Preserve frontmatter structure. Update wikilinks_out if new entities were referenced. Append a log.md entry. Run docs/wiki/scripts/lint_wiki.py --strict at the end." --allowedTools "Read,Write,Edit,Bash" --max-turns 10
```

### 漂移检测（drift · weekly）

```bash
claude -p "Run python docs/wiki/scripts/drift_check.py --days 7. For each drifted page, inspect what changed in the source file since last_refreshed, and propose a refresh plan (dry-run; do NOT apply). Output a prioritized list of pages to refresh this week." --allowedTools "Read,Bash"
```

### briefs 实例化（output · 不回流 wiki）

```bash
claude -p "Using docs/wiki/briefs/pr-review-brief.template.md, produce a review brief for PR #NNNN. Cite relevant wiki pages. Output to stdout — do NOT write to docs/wiki/." --allowedTools "Read,Bash"
```

### 会话纪律

- 会话**开始**：读 [[SCHEMA]] + [[README]]；再读当前要动的页。
- 会话**中**：改 frontmatter 的 `sources` 必同步改 `_meta/source-manifest.md`；改 `wikilinks_out` 必同步修正被链目标的反向链接。
- 会话**结束**：跑 `python docs/wiki/scripts/lint_wiki.py --strict` → exit 0；`python docs/wiki/scripts/drift_check.py` → 确认改动页不再 drift；最后在 [[log]] 追加一条。
- 不确定时：先登记 `_meta/deviations.md`，**不**静默改规则。

---

## 工作流：收录 → 连接 → 输出

```
INGEST   →   CONNECT   →   OUTPUT
raw/ 新快照    wiki 页改写      briefs 实例化
source 登记    wikilinks 更新   产物写到 PR / plans / IM
log 追加       comparison 补齐  **不回流 wiki**
```

- **INGEST** 产生 `raw/` 新快照与 `_meta/source-manifest.md` 新行；不改 wiki 页内容。
- **CONNECT** 由 Claude Code 根据 refresh 候选清单增量改写 wiki 页，产出新 wikilinks、新 comparisons、log 条目。
- **OUTPUT** 是一次性产出（PR 描述、onboarding brief、debug brief），**不回流 wiki**；但 OUTPUT 产生的高价值问答可以在下次 CONNECT 沉淀成 `queries/` 页。

### briefs 的边界

`briefs/` 下的 `*.template.md` 是**模板**，不是内容。当前可用模板：

- `briefs/onboarding-brief.template.md` —— 新人接手某子系统时的入门 brief
- `briefs/pr-review-brief.template.md` —— PR review 时的上下文 brief
- `briefs/debug-brief.template.md` —— 定位 bug / 回归时的结构化调查 brief

实例化后：

- PR 审阅类 → 贴到 PR 正文或 `docs/plans/`
- Onboarding 类 → 贴到 Notion / 新人欢迎邮件 / Slack DM
- Debug 类 → 贴到 debug issue / 工单 / PR 正文
- 以上任一 → **绝不**写回 `docs/wiki/`

每个模板的 `## Output destination` 章节给出落地位置清单。

---

## 脚本速查

| 脚本 | 何时跑 | 示例 |
|------|--------|------|
| `scripts/ingest_seed.py --dry-run` | 源文件改动后 / 每周 | 列出候选 refresh，不写盘 |
| `scripts/ingest_seed.py --apply` | 审完 dry-run 后 | append raw 快照 + 更新 manifest |
| `scripts/ingest_seed.py --source <path>` | 定点刷新单个源 | 只针对一个文件 ingest |
| `scripts/lint_wiki.py` | 每次 PR 前 | 结构 / 链接 / frontmatter / Hermes 规则检查 |
| `scripts/lint_wiki.py --strict` | 合并前 · CI gate | warning 也算失败 |
| `scripts/lint_wiki.py --path <file>` | 修完某页时 | 只 lint 单文件 |
| `scripts/drift_check.py` | 每周一 | 找出 source 已变但 wiki 未更新的页 |
| `scripts/drift_check.py --days N` | 可配阈值 | 只看 > N 天未刷新的 |

三个脚本均 stdlib only（Python 3.11+），`python3` 直接跑；不依赖 `venv/` 激活，不引入外部包。退出码契约写在各脚本 docstring 顶部。

---

## 贡献规则

### 新建页流程

1. 读 [[SCHEMA]] —— 确认你的页属哪类、放哪个目录。
2. 检查 `_meta/backlog.md` —— 看看是否已登记为 P1/P2。
3. 按 SCHEMA §4 的最小章节起草；frontmatter 按 §3 填齐。
4. 所有 `sources` 必须先在 `_meta/source-manifest.md` 登记（先 ingest 新源，再写页）。
5. `python docs/wiki/scripts/lint_wiki.py --strict` 本地 exit 0 → PR → 审阅者看风格一致性。
6. [[log]] 追加一条 `refresh` 或 `ingest` 记录。

### 命名规则

- 文件名 `kebab-case`（全小写 + 连字符），无空格 / 下划线 / 驼峰。
- 一页只讲一个主题；相关但不同的主题拆两页。
- 长度硬上限：**300 行**（含 frontmatter）。
- `briefs/` 下模板名必须以 `.template.md` 结尾；`raw/` 下快照名必须以 `-YYYYMMDD.md` 结尾。

### 何时拆页

- 页超过 300 行。
- 一个 section 讲两个以上对象 —— 拆成独立 entity。
- 同时出现 ≥3 个「这个不同于 X」→ 把 X 拆到 `comparisons/`。

### 何时**不**建页

- 只是一次性调查结果 —— 写到 `docs/plans/` 或 PR 描述。
- 只是 release notes / changelog —— 本 wiki 不收。
- 页面会被 `run_agent.py` 运行时依赖 —— 禁止，见 [[SCHEMA]] §10。
- 已由 `briefs/*.template.md` 覆盖的一次性产出场景 —— 走模板实例化，不新建 wiki 页。

---

## 审阅者契约

- 每个 Phase Gate 必须明确签字（PR 评论或 commit 消息引用 gate 编号）。
- Canary 阶段不签字 **不** 放行到下一 Phase。
- 每 2 周跑一次 `scripts/drift_check.py`；drift > 14 天的页进当周修复清单。
- `_meta/deviations.md` 每月 review 一次：判断是否升级为 SCHEMA / README 更新。
- 连续 2 个月 `open` 未推进的偏差 → 升为正式 issue 或拒绝。

---

## 参考

- 设计方案：`docs/plans/2026-04-24-hermes-local-knowledge-base-review-edition-by-claude.md`
- 初稿方案：`docs/plans/2026-04-24-hermes-local-knowledge-base-plan.md`
- 上游 brief：`docs/plans/2026-04-24-hermes-local-knowledge-base-claude-brief.md`
- Schema：[[SCHEMA]]
- 导航入口：[[index]]
- 时间线：[[log]]
- Backlog：`_meta/backlog.md`
- 覆盖度：`_meta/coverage-map.md`
- 偏差登记：`_meta/deviations.md`
