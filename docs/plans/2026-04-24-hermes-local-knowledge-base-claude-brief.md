# Claude Code Brief — Hermes 本地知识库方案再设计

你是 Claude Code（请使用 **Opus** 模型、**max** 思考强度）为 `hermes-agent` 项目做 **实施方案设计**，不是直接编码实现。

## 你的任务

请基于下面的背景、讨论结论、学习资料和约束，输出一份 **供 Hermes 审核** 的实施方案 markdown。

**重要：**
- 你这次只产出方案，不修改仓库文件。
- 你要用 **superpowers 风格** 来处理：
  - 方案必须结构化、可执行、可审阅
  - 要有明确阶段、文件路径、验收标准、风险、验证方式
  - 重点是让后续执行者“几乎不用猜”
- 请特别吸收 Karpathy LLM Wiki 方法 + Obsidian/Claude Code 工作流思路。

---

## 项目背景

仓库：`hermes-agent`

这是一个复杂的 agent 项目，包含：
- agent loop
- tool registry / toolsets
- CLI / gateway
- memory providers
- context engines
- skills system
- tests / docs / plugins

我们希望为这个项目建立一个 **本地知识库 / LLM Wiki**，用于：
- 更快理解架构
- 更快定位功能入口
- 更快做调试、设计、review、onboarding
- 避免每次都从 README + 全仓 grep 重新开始

---

## 我们已经讨论出的初步方向

当前偏好的大方向是：

1. **采用 Andrej Karpathy 的 LLM Wiki 模式**
   - raw sources 不可变
   - wiki 层由 LLM 持续维护
   - 通过 `SCHEMA.md` 管结构
   - 通过 `index.md` 管导航
   - 通过 `log.md` 管时间线

2. **第一阶段先做 repo-local markdown wiki**
   - 倾向于放在 `docs/wiki/`
   - 作为 Hermes 项目的“编译后知识层”

3. **第一阶段尽量不碰 runtime 主链路**
   - 不先改 `run_agent.py`
   - 不先改 `model_tools.py`
   - 不先把 wiki 直接接进 memory provider / context engine
   - 先把知识资产本身搭起来

4. **知识库应该服务工程产出，不只是存档**
   - 不只是“记笔记”
   - 还要支撑：
     - 架构理解
     - debug briefing
     - 设计说明
     - code review 背景
     - onboarding

5. **Obsidian + Claude Code 是推荐组合**
   - Obsidian 更像浏览/导航 IDE
   - Claude Code 是维护者
   - wiki 是共享工作区

6. **推荐采用“收录 → 连接 → 输出”工作流**
   - 收录：导入高价值 docs / code / tests
   - 连接：生成 entities / concepts / comparisons / queries
   - 输出：把高价值问答和工程结论沉淀回知识库

---

## 我们当前已有的一版计划（你需要参考，但不要被它限制）

请阅读：
- `docs/plans/2026-04-24-hermes-local-knowledge-base-plan.md`

这是一版初稿。你要做的不是复述它，而是：
- 吸收其中合理部分
- 补足其中不够产品化/不够闭环的部分
- 给出一版更成熟、更适合后续执行的方案

---

## 你还需要吸收的外部思路

### 1. Karpathy 的 LLM Wiki 核心思想
核心不是 RAG，而是：
- 知识增量编译为持久化 wiki
- 提前沉淀交叉引用、摘要、冲突和专题页
- 人负责选材料和提问题
- agent 负责维护知识层

### 2. 一篇中文实践文章给我们的启发
我们额外看了一篇飞书文档，核心启发如下：
- Obsidian + Claude Code 可以形成顺畅工作流
- 知识库不只是归档，而是一个“收录、连接、输出”的系统
- 强调本地存储、知识归自己所有
- 强调知识是累积资产，不是一次性问答
- 强调最终要支撑“产出”，而不仅是“存储”

这对 Hermes 的启发是：
- 方案里应该明确 **Obsidian 是推荐前端**，而不仅仅是“兼容”
- 方案里应该明确 **输出层 / query 沉淀 / engineering outputs**
- 方案里应该明确 **README 使用工作流**，而不只是目录说明
- Obsidian Terminal 插件这类东西可以作为 **可选增强**，不是首期硬依赖

---

## 我们已经确认/观察过的 Hermes 代码结构重点

请优先围绕这些区域考虑首批知识库覆盖面：

### 顶层与项目说明
- `README.md`
- `AGENTS.md`

### 核心运行链路
- `run_agent.py`
- `model_tools.py`
- `toolsets.py`
- `hermes_state.py`

### CLI / 配置 / 插件配置入口
- `cli.py`
- `hermes_cli/config.py`
- `hermes_cli/commands.py`
- `hermes_cli/memory_setup.py`
- `hermes_cli/plugins_cmd.py`

### 工具系统
- `tools/registry.py`
- `tools/file_tools.py`
- `tools/terminal_tool.py`
- `tools/delegate_tool.py`
- `tools/browser_tool.py`

### memory/context plugin 体系
- `agent/memory_provider.py`
- `agent/context_engine.py`
- `plugins/memory/openviking/__init__.py`
- `plugins/memory/openviking/README.md`
- `plugins/context_engine/__init__.py`

---

## 重要设计约束

你输出的方案要认真权衡这些约束：

1. **先易后难**
   - 第一阶段优先做低风险、高收益方案

2. **不要过早把 wiki 接入 runtime**
   - 第一阶段不要求做 memory provider / context engine 集成

3. **要 git-friendly**
   - 方案要适合版本管理、代码审阅、协作

4. **要本地优先**
   - 尽量不依赖远程数据库或 SaaS

5. **要可维护**
   - 不能是一次性生成一堆 md 然后无人维护

6. **要考虑 Claude Code 作为执行者**
   - 后续很可能真的是 Claude Code 来实施
   - 所以方案应便于 Claude Code 分阶段执行

---

## 你需要回答的关键问题

请在方案中明确回答：

1. 知识库应该放在哪里？为什么？
2. 首期目录结构应该长什么样？
3. `raw / wiki / schema` 三层如何映射到 Hermes 仓库？
4. 首批应该 ingest 哪些 source？为什么？
5. 首批应该生成哪些 page 类型？为什么？
6. 是否需要单独的 outputs / queries 层？如何设计更合适？
7. `README.md` / `SCHEMA.md` / `index.md` / `log.md` 各自的职责应该怎么定义？
8. 如何把 Obsidian + Claude Code 纳入推荐工作流？
9. 是否需要维护脚本？需要哪些？
10. 第一阶段、第二阶段、第三阶段应该各做什么？
11. 哪些内容坚决不要在第一阶段做？
12. 如何验证知识库真的提升了 Hermes 工程效率？

---

## 输出要求

请输出一份 **审阅版实施方案**，要求：

- 用 markdown
- 面向“我（Hermes）要先审核，再决定是否放行执行”
- 结构尽量包含：
  1. Executive summary
  2. Recommended architecture
  3. Directory structure
  4. Source ingestion strategy
  5. Page taxonomy
  6. Workflow（收录/连接/输出）
  7. Phase plan
  8. Validation plan
  9. Risks and non-goals
  10. Review checkpoints
- 要明确哪些是：
  - **必须做**
  - **推荐做**
  - **以后再做**
- 要尽量具体，能直接进入下一轮审核

---

## 额外要求

- 请优先给一个 **高质量、可落地、不过度设计** 的方案
- 如果你觉得当前 `docs/wiki/` 不是最佳位置，可以挑战它，但必须给出充分理由
- 如果你觉得 `queries/` 应该重命名或拆分，也可以提出
- 如果你觉得应增加 `outputs/` 或 `_meta/` 下额外文件，也可以提出
- 但请始终遵守：**第一阶段尽量不动 Hermes runtime 主链路**

---

## 你要读的本地文件

至少请参考这些：
- `docs/plans/2026-04-24-hermes-local-knowledge-base-plan.md`
- `README.md`
- `AGENTS.md`
- `run_agent.py`
- `model_tools.py`
- `toolsets.py`
- `agent/memory_provider.py`
- `agent/context_engine.py`
- `plugins/memory/openviking/README.md`
- `plugins/memory/openviking/__init__.py`
- `hermes_cli/memory_setup.py`
- `hermes_cli/plugins_cmd.py`

如果时间有限，至少先阅读计划、README、AGENTS、memory/context 相关文件。

---

## 最终交付

请只输出：
- 一份完整的审阅版实施方案
- 不要执行代码修改
- 不要输出“我接下来可以做什么”这种客套话
