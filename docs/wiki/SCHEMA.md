# SCHEMA

**状态：** Phase 0 首版（2026-04-24）
**读者：** `lint_wiki.py`（Phase 2 实施）、Claude Code 维护会话、审阅者
**性质：** **非 runtime 依赖** —— 本 wiki 任何文件都不得被 `run_agent.py` / `model_tools.py` / `agent/memory_provider.py` / `agent/context_engine.py` 在运行时读取或加载。

> 本文件定义 `docs/wiki/` 的机读规则。任何 `.md` 页要合规，必须同时满足：
> 1. 放在合法目录
> 2. 具备合法 frontmatter
> 3. 拥有强制最小章节（按页类型）
> 4. wikilinks 使用规范格式
> 5. 引用的 source 在 `_meta/source-manifest.md` 登记

---

## 1. 合法目录 × 页类型

只有以下 7 个目录合法。**每个目录只接受一种页类型**。

| 目录 | 页类型 | 一句话定义 | 触发阈值 |
|------|--------|-----------|---------|
| `entities/` | entity | 一个有名字的对象（类、模块、插件、系统角色） | 跨 2+ 源文件出现，或是插件契约 |
| `concepts/` | concept | 一个机制或流程 | 跨 2+ 源文件、需要调用链才能解释清楚 |
| `comparisons/` | comparison | 两个相邻概念的辨析 | 新人常混淆，或代码中有显式「这个不是那个」注释 |
| `queries/` | query | 高频工程问题的沉淀答案 | 真的被问过 ≥2 次，或 AGENTS.md 已隐含答过 |
| `briefs/` | brief-template | 一次性工程产出的**模板**（不是内容） | 一类交付物反复产生 |
| `raw/` | snapshot | 不可变源层：文档快照或源码结构化摘录 | append-only，不得原地覆盖 |
| `_meta/` | meta | 治理、清单、taxonomy、偏差登记 | 固定集合，新增需审阅 |

**不允许**在根或非上述目录下放内容页。根目录只允许 4 个固定文件：`README.md`、`SCHEMA.md`、`index.md`、`log.md`。

---

## 2. 文件名规范

- `kebab-case`（全小写 + 连字符），无空格、无下划线、无驼峰
- 扩展名 `.md`（除 `scripts/*.py`）
- slug 即文件名去掉 `.md` 后的部分
- `briefs/` 下模板文件名必须以 `.template.md` 结尾
- `raw/` 下快照文件名必须以 `-YYYYMMDD.md` 结尾

**合法示例：**
`entities/aiagent.md` · `concepts/agent-loop.md` · `comparisons/memory-provider-vs-context-engine.md` · `queries/how-tools-enter-the-model-surface.md` · `briefs/pr-review-brief.template.md` · `raw/repo-docs/README-20260424.md`

**非法示例：**
`entities/AIAgent.md`（大写）· `concepts/agent_loop.md`（下划线）· `queries/Q1.md`（无语义）· `briefs/my-brief.md`（缺 `.template`）

---

## 3. 强制 frontmatter

### 3.1 内容页（entity / concept / comparison / query）

```yaml
---
title: <人类可读标题>
type: <entity|concept|comparison|query>
tags: [<tag1>, <tag2>, ...]      # 至少 1，来自 _meta/taxonomy.md
sources:                          # 至少 1，必须在 _meta/source-manifest.md 登记
  - <repo 相对路径>
wikilinks_out: [<type/slug>, ...]  # 允许为空数组；但孤岛页会触发 lint warning
last_refreshed: YYYY-MM-DD
refreshed_by: <claude-code|human-author 标识>
---
```

### 3.2 briefs（brief-template）

```yaml
---
title: <模板标题>
type: brief-template
usage: <一句话说明何时实例化此模板>
tags: [<tag1>, ...]
wikilinks_out: [[placeholder-page]]   # 允许用占位 wikilinks
last_refreshed: YYYY-MM-DD
refreshed_by: <...>
---
```

### 3.3 raw snapshots

```yaml
---
kind: snapshot
source_path: <repo 相对路径>
captured_at: YYYY-MM-DD
sha256: <hex>
supersedes: <旧快照路径或 —>
---
```

**硬规则：** raw 文件不得含 `wikilinks_out`，不得含 `tags`，不得有解释性正文 —— 只放客观快照/摘录。

---

## 4. 强制最小章节（按页类型）

### 4.1 entity / concept / query

必须包含以下 5 个二级标题（顺序不强制，但全部存在）：

- `## TL;DR` —— 3–6 行，说清「这是什么 / 为什么重要」
- `## 责任边界` —— 明说「做什么 / 不做什么」，消除与邻近概念的混淆
- `## 调用链 / 关系` —— ASCII 图、mermaid 图，或清晰的上下游列表
- `## 坑点` —— 至少 1 条「不读这页会踩的坑」；可为「暂未发现」但需注明搜索过哪些来源
- `## References` —— 指向 source 文件、相关页面、可选的外部链接

**页总长上限：300 行**（含 frontmatter）。超长必须拆页。

### 4.2 comparison

追加要求：必须出现至少一个含「不是」、「vs」或「区别」字样的章节标题。否则判定为「罗列而非辨析」。

### 4.3 brief-template

最小章节：

- `## Usage` —— 复述 frontmatter `usage`，多展开成段
- `## Placeholders` —— 列出所有 `[[placeholder-page]]` 并说明替换指引
- `## Output destination` —— 明示实例化产物写到何处（**不得**写回 `docs/wiki/`）

---

## 5. wikilinks 规范

- 内容页默认格式：`[[type/slug]]` —— 例如 `[[entities/aiagent]]`、`[[concepts/agent-loop]]`
- 根级固定文件允许直接写：`[[README]]`、`[[SCHEMA]]`、`[[index]]`、`[[log]]`
- **禁止**相对路径链接（`./foo.md`、`../entities/bar.md`）
- **禁止**带 `.md` 扩展名的 wikilink
- 别名语法允许：`[[entities/aiagent|AIAgent 类]]`
- 指向「未来页」（尚未创建）允许存在，但会触发 lint **warning**；指向已删除目标触发 lint **error**
- 反向链接由 Obsidian / `lint_wiki.py` 自动推导，作者**不**手写「Backlinks」章节

---

## 6. raw / wiki / meta 边界

| 层 | 允许的内容 | 禁止的内容 |
|----|-----------|-----------|
| `raw/` | 源文件副本、结构化摘录、原路径指针、抓取日期 | 解释、结论、wikilinks、tags |
| `entities/` / `concepts/` / `comparisons/` / `queries/` | 解释、调用链、坑点、wikilinks、frontmatter | 大段源码（用 code-snapshot 链接替代）、版本化变更日志 |
| `briefs/` | 脚手架模板、占位 wikilinks | 具体工程产物实例（实例写到 PR / `docs/plans/` 等外部位置） |
| `_meta/` | 治理、清单、taxonomy、偏差登记 | 知识内容（解释、对比、调用链） |
| 根 4 文件 | 入口、规则、导航、时间线 | 知识内容 |

**append-only 规则：** raw 只能新增（带日期后缀快照），不得原地覆盖；如需「更新」，append 新快照 + 在 `source-manifest.md` 的 `supersedes` 列标记旧版。

---

## 7. 更新流程（CONNECT 阶段的最小契约）

1. **Claude Code** 读取 `_meta/source-manifest.md` 与目标源文件当前状态
2. 决定：刷新现有页 or 新建页 or 标记为「需要人审」（写入 `_meta/backlog.md` 或 `_meta/deviations.md`）
3. 改写时保持 frontmatter 结构；更新 `last_refreshed` 与 `refreshed_by`
4. 修改 `wikilinks_out` 以反映新增/删除的引用
5. 同步更新 `_meta/source-manifest.md` 的 `wiki_refs` 列
6. 在 `log.md` 追加条目：`YYYY-MM-DD | phase-N | refresh | <file1>, <file2>, ...`
7. 运行 `python docs/wiki/scripts/lint_wiki.py --strict`（Phase 2 之后）

---

## 8. Hermes-specific lint 规则（Phase 2 `lint_wiki.py` 实施）

以下规则在 SCHEMA 层预先约定，Phase 2 脚本化后强制。

1. 任何正文含字面量 `~/.hermes` 的页，必须同时出现 `get_hermes_home()` 或 `profile` 关键词（否则 warn：硬编码路径反模式）
2. 任何正文含 `register a tool` 或「添加工具」的页，必须至少 wikilink 到 `[[entities/tool-registry]]`
3. 任何正文含 `memory provider` 的页，必须至少 wikilink 到 `[[entities/memoryprovider]]`
4. `comparison` 页必须显式含「不是」、「vs」或「区别」章节（同 §4.2）
5. `query` 页必须 wikilink 到 ≥1 个 entity 或 concept 页
6. 页面总行数 > 300 → error（拆页）
7. frontmatter `sources` 中列出的路径必须存在于 `_meta/source-manifest.md`
8. frontmatter `tags` 必须全部属于 `_meta/taxonomy.md` 的白名单

---

## 9. 版本化

- 本文件每次修改需在 `log.md` 追加一条 `schema-bump` 条目
- 重大修改（影响现有页合规性）需在 `_meta/deviations.md` 登记，并给出迁移路径
- 禁止静默改规则 —— 改规则必打 log

---

## 10. 非目标（明确不做）

- 不做 runtime 集成（见 §0 标头说明）
- 不做向量检索 / 本地 RAG
- 不自动生成整份 wiki（Karpathy 式人类必须选材）
- 不强制 `.obsidian/` 入库
- 不加 CI hook（Phase 3+ 评估）
- 不接入 Mem0 / Honcho / Hindsight

详见 `docs/plans/2026-04-24-hermes-local-knowledge-base-review-edition-by-claude.md` §9.1。
