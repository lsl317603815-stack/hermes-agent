# Personal Wiki Master Architecture + Bootstrap — Claude Code Brief

## 任务目标

为用户搭建一套**本地化的个人知识库 wiki 总库**，它不是 Hermes 项目专用 wiki，而是用户的长期知识中枢。Hermes 工程维护只是其中一个子域。

你需要先产出一份**审阅级方案文档**，然后继续**实施搭建第一阶段可运行骨架**。

## 关键背景

当前仓库中已经存在一个 Hermes 项目专用 repo-local wiki：
- `/Users/ryuka/Documents/GitHub/hermes-agent/docs/wiki`

它已经完成了 Phase 0-3，适合作为“项目子库”方法样板，但**不能等同于用户最终想要的个人总知识库**。

用户新的明确目标是：
- 打造一个本地化的个人知识库 wiki
- Hermes 工程只是其中一部分
- 还要覆盖小说写作、AI短视频等领域
- 这些领域之间未来要能产生连接
- Hermes 最终应具备在多个项目/子域之间灵活切换，并保持连续知识库与记忆的能力

## 你本次要做的事

分两段执行：

### Part A：先写审阅版方案
输出一份审阅版方案到：
- `docs/plans/2026-04-24-personal-wiki-master-architecture-review-by-claude.md`

这份方案必须讲清楚：
1. 为什么现有 Hermes repo-local wiki 只是子库，不是总库
2. 个人总库与项目子库的两级架构
3. 推荐的本地绝对路径与目录结构
4. 哪些内容放总库，哪些内容放子库
5. 总库如何支持跨域连接（Hermes / 小说 / AI短视频）
6. Hermes 将来如何基于总库 + 子库进行项目切换
7. 知识库与记忆之间如何分工
8. 第一阶段（bootstrap）应该搭哪些文件和 canary 页面
9. taxonomy 应如何设计为跨域可扩展，而不是 Hermes-only
10. 后续扩展路线

写法要求：
- 使用“superpowers”风格
- 方案必须有清晰阶段划分
- 尽量小批次、可验证、可落盘
- 文风直接，不空泛
- 给出明确文件路径

### Part B：实施第一阶段 bootstrap
在用户本地新建一个**个人总库**，默认路径定为：
- `/Users/ryuka/personal-wiki`

如果目录不存在，就创建。

第一阶段只做总库 bootstrap，不做深度内容扩写。目标是把总库骨架搭起来，并让它能和现有 Hermes 子库形成概念上的两级结构。

## 总库第一阶段要求

在 `/Users/ryuka/personal-wiki` 下搭建：

```text
personal-wiki/
├── README.md
├── SCHEMA.md
├── index.md
├── log.md
├── _meta/
│   ├── taxonomy.md
│   ├── source-manifest.md
│   ├── coverage-map.md
│   ├── backlog.md
│   └── deviations.md
├── domains/
│   ├── hermes/
│   ├── fiction/
│   ├── ai-short-video/
│   └── workflows/
├── entities/
├── concepts/
├── comparisons/
├── queries/
├── briefs/
├── raw/
│   ├── articles/
│   ├── notes/
│   └── imports/
└── scripts/
```

## 第一阶段文件要求

至少创建并填充：
- `README.md`
- `SCHEMA.md`
- `index.md`
- `log.md`
- `_meta/taxonomy.md`
- `_meta/source-manifest.md`
- `_meta/coverage-map.md`
- `_meta/backlog.md`
- `_meta/deviations.md`

并创建 3 个跨域 canary 页面：
- `concepts/story-hook.md`
- `comparisons/novel-hook-vs-short-video-hook.md`
- `queries/how-to-link-fiction-and-ai-short-video-workflows.md`

要求：
- 所有内容页都有 frontmatter
- wikilinks 合法
- index.md 录入这些页面
- log.md 追加创建记录

## 设计原则

1. **总库 ≠ 子库**
   - 总库用于长期、跨领域、跨项目知识连接
   - 子库用于项目内精确知识（如 Hermes repo-local wiki）

2. **总库支持跨域连接**
   - 小说写作与 AI短视频之间可以通过 hook、节奏、角色、叙事、情绪驱动等概念互连
   - Hermes 工程经验也可能和创作 workflow、briefing 方法相连

3. **不要污染现有 Hermes 子库**
   - 本次不要去重构 `/Users/ryuka/Documents/GitHub/hermes-agent/docs/wiki`
   - 只在总库中把 `domains/hermes/` 作为一个子域占位与导航入口

4. **Obsidian 友好**
   - 使用 markdown + wikilinks + frontmatter

5. **小批次落地**
   - 先 bootstrap，不要一口气填很多内容
   - 每一步完成后可验证

## 强约束

- 本次不要改 Hermes runtime
- 本次不要实现向量数据库或 RAG
- 本次不要做自动同步逻辑
- 本次不要实现复杂项目切换机制代码
- 本次只做：
  - 架构方案文档
  - personal wiki 总库骨架
  - 首批 taxonomy
  - 首批 canary 页面

## taxonomy 方向

请为总库设计一套**跨域 taxonomy 初版**，不要沿用 Hermes-only tags。

建议至少涵盖：
- hermes-engineering
- fiction
- ai-short-video
- storytelling
- workflow
- tooling
- knowledge-design
- memory
- project-switching
- cross-domain
- hooks
- narrative
- adaptation

可以调整，但要自洽。

## 对 domains/ 的处理

`domains/` 先作为导航域目录使用，不需要在第一阶段写很多内容。
但请至少让 README / index / coverage-map 明确：
- `domains/hermes/` 对应 Hermes 这一子域
- `domains/fiction/` 对应小说写作
- `domains/ai-short-video/` 对应短视频创作
- `domains/workflows/` 对应通用工作流

## 实施风格要求（非常重要）

你必须按“superpowers”风格执行：
- 一次只做一个明确小目标
- 先写方案，再建骨架
- 不要顺手扩 scope
- 每产出一批后保持可验证
- 不要输出空泛 roadmapping 语言
- 直接创建文件

## 推荐模型与参数

使用：
- `claude-opus-4-7`
- `--effort max`

## 交付结果

完成后，应至少落地：
1. 审阅版方案文档
2. `/Users/ryuka/personal-wiki/` 骨架
3. 首批根文件与 meta 文件
4. 3 个 canary 页面
5. `index.md` / `log.md` 同步完成

## 完成后请自检

至少检查：
- 文件是否存在
- frontmatter 是否完整
- canary 页面是否能互链
- index 是否录入
- log 是否记录
- 总库与 Hermes 子库的边界是否清楚

## 你不需要做的事

- 不需要写很多真实知识内容
- 不需要大规模 ingest 教程
- 不需要把 Hermes 子库内容迁移进总库
- 不需要做 runtime 级记忆切换实现

## 一句话总结

你是在为用户搭建“个人总知识库”的第一阶段，不是继续扩写 Hermes 项目子库。先把总库的架构、边界、taxonomy 和最小可运行骨架做对。