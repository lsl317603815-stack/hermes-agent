# Hermes 本地知识库实施计划（供审阅）

> **For Hermes:** 先不要直接改业务代码。先按本计划搭建知识库骨架、导入首批源码上下文、生成初始索引与专题页，再把结果交给用户审阅。执行时优先使用 Claude Code `-p` 模式做一次性任务；只有在需要多轮迭代整理时才切到交互式会话。

**日期：** 2026-04-24

**目标：** 为 `hermes-agent` 仓库建立一个 **本地、可持续维护、Obsidian 友好、Claude Code 可直接读写** 的项目知识库，让后续的代码理解、问题排查、功能设计和 review 不再每次都从 README + 全仓 grep 重新开始。

**设计依据：** 采用 Andrej Karpathy 的 LLM Wiki 模式：
- 原始资料层（raw sources）不可变
- Wiki 层由 LLM 持续维护
- 通过 `SCHEMA.md` 约束结构、命名、更新流程
- 通过 `index.md` 做内容导航
- 通过 `log.md` 记录时间线

**总体思路：** 先做一个 **repo-local markdown wiki**，放在 `docs/wiki/` 下，作为 Hermes 项目的“编译后知识层”；后续如有需要，再追加本地搜索（如 qmd）或对接 Hermes 的外部 memory/context plugin。第一阶段不碰运行时主链路，只建设知识库本身及其维护脚本。

---

## 一、为什么选这个方案

Karpathy 的关键点不是“再造一个 RAG”，而是：
1. 不在每次提问时重新从原始材料拼答案
2. 而是把知识 **增量编译** 为持续更新的 wiki
3. 让交叉引用、冲突、摘要、主题页提前沉淀

对 Hermes 这个仓库尤其合适，因为它：
- 代码面广：agent / tools / gateway / plugins / cli / tests / docs
- 概念层多：toolsets、memory providers、context engines、skills、gateway adapters、terminal backends
- 经常需要跨文件回答“这个功能到底怎么串起来的？”
- 已经有不少高价值说明性资料：`README.md`、`AGENTS.md`、skill 文档、插件 README、测试文件

---

## 二、范围与非目标

### 本阶段范围
1. 建立 wiki 目录结构
2. 写好 `SCHEMA.md` / `index.md` / `log.md`
3. 导入第一批 Hermes 资料到 `raw/`
4. 生成第一批核心概念页 / 实体页 / 比较页
5. 提供一个 **可重复执行** 的增量导入脚本
6. 提供一个 **wiki lint/health-check** 脚本
7. 提供 Claude Code 的使用说明，让后续能继续维护知识库

### 明确非目标
1. **本阶段不做** 向量数据库 / 远程服务依赖
2. **本阶段不做** Hermes 运行时自动读取这个 wiki 作为 memory provider
3. **本阶段不改** 主聊天回路、tool registry、context engine 主逻辑
4. **本阶段不追求** 一次性覆盖全仓每个文件
5. **本阶段不接** OpenViking / Mem0 / Honcho 等外部 provider

---

## 三、落地位置与目录结构

默认放在仓库内：`docs/wiki/`

```text
docs/wiki/
├── README.md
├── SCHEMA.md
├── index.md
├── log.md
├── raw/
│   ├── repo-docs/
│   ├── code-snapshots/
│   ├── skills/
│   └── assets/
├── entities/
├── concepts/
├── comparisons/
├── queries/
├── _meta/
│   ├── source-manifest.md
│   ├── coverage-map.md
│   └── taxonomy.md
└── scripts/
    ├── ingest_seed.py
    └── lint_wiki.py
```

### 这样放的理由
- `docs/` 下已有架构/迁移/计划文档，语义上最接近
- git 跟踪方便，review 清楚
- 可直接被 Obsidian 当 vault 子目录使用
- 不污染运行时目录，也不和 `~/.hermes/` 用户态数据混淆

---

## 四、Hermes 场景下的 wiki schema 设计

`SCHEMA.md` 需要针对 Hermes 项目定制，而不是套通用模板。

### 页面类型

#### 1. `entities/`
用于“具体对象”：
- `aiagent.md`
- `memoryprovider.md`
- `contextengine.md`
- `tool-registry.md`
- `gateway-session-store.md`
- `claude-code-skill.md`

#### 2. `concepts/`
用于“机制/主题”：
- `agent-loop.md`
- `tool-resolution.md`
- `toolset-filtering.md`
- `memory-provider-lifecycle.md`
- `context-engine-plugin-system.md`
- `skills-loading-and-config.md`
- `gateway-platform-architecture.md`
- `profile-aware-path-handling.md`

#### 3. `comparisons/`
用于并列分析：
- `memory-provider-vs-built-in-memory.md`
- `context-engine-vs-memory-provider.md`
- `cli-vs-gateway-entrypoints.md`
- `browser-vs-web-tools.md`

#### 4. `queries/`
用于沉淀高价值问答：
- `how-tools-enter-the-model-surface.md`
- `how-memory-provider-hooks-are-wired.md`
- `where-to-add-a-new-tool.md`

### 建议标签体系
- `agent-core`
- `cli`
- `gateway`
- `tools`
- `toolsets`
- `skills`
- `memory`
- `context-engine`
- `plugins`
- `testing`
- `config`
- `paths`
- `provider`
- `architecture`
- `workflow`

### 页面创建阈值
- 单个主题跨 2 个以上核心文件出现：建页
- 单个类/模块是关键入口：建页
- 临时细节、一次性修复点：不单独建页，写入现有主题页

---

## 五、首批导入源（Seed Sources）

Claude Code 第一轮只处理高价值源，避免一上来把全仓灌进去。

### A. 顶层说明
- `README.md`
- `AGENTS.md`

### B. 核心运行链路
- `run_agent.py`
- `model_tools.py`
- `toolsets.py`
- `hermes_state.py`

### C. CLI 与配置
- `cli.py`
- `hermes_cli/config.py`
- `hermes_cli/commands.py`
- `hermes_cli/memory_setup.py`
- `hermes_cli/plugins_cmd.py`

### D. 工具系统
- `tools/registry.py`
- `tools/file_tools.py`
- `tools/terminal_tool.py`
- `tools/delegate_tool.py`
- `tools/browser_tool.py`

### E. 插件扩展面
- `agent/memory_provider.py`
- `agent/context_engine.py`
- `plugins/memory/openviking/__init__.py`
- `plugins/memory/openviking/README.md`
- `plugins/context_engine/__init__.py`

### F. 高信号测试 / 文档样本
- `tests/test_toolsets.py`
- `tests/agent/test_memory_provider.py`
- `docs/acp-setup.md`
- `docs/honcho-integration-spec.md`

---

## 六、初始知识页规划

Claude Code 第一轮至少产出以下页面：

### 实体页
1. `entities/aiagent.md`
2. `entities/memoryprovider.md`
3. `entities/contextengine.md`
4. `entities/tool-registry.md`
5. `entities/openviking-memory-provider.md`

### 概念页
6. `concepts/agent-loop.md`
7. `concepts/tool-definition-resolution.md`
8. `concepts/toolset-system.md`
9. `concepts/built-in-memory-vs-external-memory.md`
10. `concepts/context-engine-plugin-system.md`
11. `concepts/skills-loading-and-config.md`
12. `concepts/profile-aware-paths.md`

### 比较页
13. `comparisons/memory-provider-vs-context-engine.md`
14. `comparisons/cli-vs-gateway.md`

### 查询沉淀页
15. `queries/how-hermes-exposes-tools-to-the-model.md`
16. `queries/how-memory-provider-hooks-join-the-agent-loop.md`

---

## 七、实施阶段

## Phase 0：搭骨架（最小可用 wiki）

**目标：** 先把 repo-local wiki 变成一个“可维护系统”，不是一堆散 markdown。

**Claude Code 任务：**
1. 创建 `docs/wiki/` 目录树
2. 创建 `README.md`
3. 创建 `SCHEMA.md`
4. 创建 `index.md`
5. 创建 `log.md`
6. 创建 `_meta/taxonomy.md`
7. 在 `log.md` 记录初始化条目

**验收标准：**
- 目录结构完整
- `SCHEMA.md` 明确页面类型、frontmatter、标签、更新规则
- `index.md` 有初始 section
- `log.md` 可 append

---

## Phase 1：导入首批 raw sources

**目标：** 把高价值源复制/整理到 `raw/`，形成“不可变材料层”。

**Claude Code 任务：**
1. 创建 `raw/repo-docs/` 下的 markdown 快照或索引说明
2. 为关键源码建立 `raw/code-snapshots/` 摘要入口（不是全量复制整个仓库）
3. 生成 `_meta/source-manifest.md`
4. 记录每个 source 的来源路径、抓取日期、用途

**建议策略：**
- 对文档类文件可直接保留 markdown 副本或引用说明
- 对大源码文件不要盲目整份复制，优先生成“结构化摘录 + 原路径引用”
- raw 层要强调 immutable：后续更新追加新快照，而不是偷偷改旧快照

**验收标准：**
- `source-manifest.md` 能回答“当前 wiki 基于哪些源构建”
- 至少覆盖 README、AGENTS、核心运行链路、memory/context plugin 入口

---

## Phase 2：生成第一批 wiki 页面

**目标：** 把源码与文档编译成可读的知识页。

**Claude Code 任务：**
1. 从 seed sources 提取核心实体与概念
2. 创建上面列出的首批 16 个页面（可略有调整，但数量不能太少）
3. 每页补足 frontmatter
4. 每页至少加入 2 个以上 wikilinks
5. 在 `index.md` 中注册这些页面
6. 在 `log.md` 中记录本轮 ingest/update

**页面要求：**
- 不要把源码逐行抄成文档
- 每页都要回答“它是什么、在哪、如何被使用、与什么相关、有什么坑”
- 对复杂主题给出调用链或责任边界
- 明确引用源文件

**验收标准：**
- `index.md` 能作为 Hermes 架构导航入口
- 阅读 3~5 页即可快速理解项目主干
- 页面之间形成图谱，而不是孤岛

---

## Phase 3：增加自动化维护脚本

**目标：** 让知识库不是一次性成果，而是可继续更新。

**新增脚本：**

### `docs/wiki/scripts/ingest_seed.py`
职责：
- 读取预定义 seed source 列表
- 更新 source manifest
- 生成待更新页面建议清单
- 支持 dry-run

### `docs/wiki/scripts/lint_wiki.py`
职责：
- 检查 orphan pages
- 检查 broken wikilinks
- 检查 frontmatter 完整性
- 检查 index 是否漏页
- 检查 tags 是否都在 taxonomy 中
- 检查过长页面（>200 行）

**验收标准：**
- 两个脚本都能在本地跑通
- 输出明确、可读
- dry-run 不改文件

---

## Phase 4：补充使用说明，交给 Claude Code 持续维护

**目标：** 让后续 agent/Claude Code 能按照固定纪律维护 wiki。

**Claude Code 任务：**
1. 在 `docs/wiki/README.md` 写清使用方式
2. 追加一个面向 Claude Code 的操作说明，例如：
   - 新 source 进入后先更新 raw
   - 再更新相关 concept/entity pages
   - 最后更新 index 和 log
3. 说明如何在 Obsidian 中打开
4. 说明如何在仓库开发流程中使用：
   - 新人 onboarding
   - 设计前背景调研
   - PR review 前定位架构影响面

**验收标准：**
- 新会话的 agent 拿到 `docs/wiki/README.md` + `SCHEMA.md` 就知道怎么维护

---

## 八、建议的实现文件清单

### 新增
- `docs/wiki/README.md`
- `docs/wiki/SCHEMA.md`
- `docs/wiki/index.md`
- `docs/wiki/log.md`
- `docs/wiki/_meta/source-manifest.md`
- `docs/wiki/_meta/coverage-map.md`
- `docs/wiki/_meta/taxonomy.md`
- `docs/wiki/scripts/ingest_seed.py`
- `docs/wiki/scripts/lint_wiki.py`
- `docs/wiki/entities/*.md`
- `docs/wiki/concepts/*.md`
- `docs/wiki/comparisons/*.md`
- `docs/wiki/queries/*.md`

### 暂不修改（第一阶段）
- `run_agent.py`
- `model_tools.py`
- `toolsets.py`
- `cli.py`
- `hermes_cli/*`
- `plugins/*`

也就是说：**第一阶段只新增知识库资产，不改运行时行为。**

---

## 九、Claude Code 的执行方式建议

优先用 print mode：

```bash
claude -p "Read docs/plans/2026-04-24-hermes-local-knowledge-base-plan.md and implement Phase 0 and Phase 1 only. Do not modify runtime code. Create the wiki skeleton under docs/wiki/, seed the raw source manifest, update index.md and log.md, then summarize what changed." --allowedTools "Read,Write,Edit,Bash" --max-turns 12
```

等你审完 Phase 0/1 结果，再继续：

```bash
claude -p "Continue from the existing docs/wiki/ knowledge base. Implement Phase 2 only: generate the initial entity/concept/comparison/query pages from the seeded Hermes sources, update index.md and log.md, and keep the diff tight." --allowedTools "Read,Write,Edit,Bash" --max-turns 16
```

最后再做维护脚本：

```bash
claude -p "Implement Phase 3 and Phase 4 for the Hermes project wiki: add ingest_seed.py, lint_wiki.py, and complete docs/wiki/README.md with maintenance instructions. Run the narrowest useful verification and summarize remaining gaps." --allowedTools "Read,Write,Edit,Bash" --max-turns 14
```

---

## 十、验证方案

### 结构验证
- `docs/wiki/` 目录完整存在
- `index.md` 可导航到所有知识页
- `log.md` 有时间线记录

### 内容验证
- 每个知识页都有 frontmatter
- 每个知识页至少 2 个内部链接
- 页面能回指具体源码或文档来源

### 维护性验证
- `python docs/wiki/scripts/lint_wiki.py` 可运行
- lint 能报出 broken links / orphan pages / missing index entries

### 实用性验证
人工抽样验证这几个问题是否能快速回答：
1. Hermes 的 tools 是如何进入 model surface 的？
2. memory provider 与 context engine 的区别是什么？
3. 新加一个工具需要改哪几处？
4. 为什么不能硬编码 `~/.hermes`？
5. OpenViking 在 Hermes 里扮演什么角色？

如果 wiki 不能让这些问题显著更快地回答，说明页面组织还不够好。

---

## 十一、第二阶段可选增强（先不做）

这些可以写进后续 backlog，但不应阻塞第一阶段：

1. **本地搜索增强**
   - 接入 qmd 或自定义 markdown search
   - 目前本机未发现 `qmd` 命令，可后补

2. **和 Hermes 运行时集成**
   - 未来可考虑做成 memory provider 或 context engine 的辅助数据源
   - 但这属于第二阶段，不该和 wiki 搭建绑死

3. **增量源码变更感知**
   - 监听 `git diff`，提示哪些 wiki 页面可能过期

4. **知识库 PR 审查机制**
   - 对知识页也跑 lint / link-check / taxonomy-check

---

## 十二、主要风险与对应策略

### 风险 1：一上来覆盖面太大，wiki 变成垃圾堆
**对策：** 第一轮只 ingest 高价值源，不全量扫描仓库。

### 风险 2：知识页只是 README 改写，没有真正结构化
**对策：** 页面必须强调责任边界、调用链、关系图、坑点。

### 风险 3：raw 层和 wiki 层混淆
**对策：** raw 不可变；解释写在 wiki 层。

### 风险 4：后续没人维护
**对策：** 第一阶段就做 `ingest_seed.py` + `lint_wiki.py` + README 维护说明。

### 风险 5：过早耦合 Hermes runtime
**对策：** 第一阶段零运行时改动，只新增 docs/wiki 资产。

---

## 十三、我建议的审批切分

为了降低风险，我建议你按 3 次审阅放行：

### 审批 A
只让 Claude Code 做：
- Phase 0
- Phase 1

### 审批 B
在你看过骨架后，再做：
- Phase 2

### 审批 C
最后做：
- Phase 3
- Phase 4

这样不会让 Claude Code 一次性写太多“看起来很完整但你还没校准风格”的内容。

---

## 十四、当前结论

**推荐方案：**
- 采用 Karpathy 的 LLM Wiki 模式
- 先在 `docs/wiki/` 搭一个 repo-local、本地 markdown 知识库
- 第一阶段只新增知识资产，不碰 Hermes 主运行链路
- 由 Claude Code 按分阶段计划实施，并在每阶段后给你审阅

如果你认可，这个计划之后我可以继续下一步：
1. 先不实施，只把计划微调到你满意
2. 然后我再替你调用 Claude Code，严格按 **审批 A** 开始干活
