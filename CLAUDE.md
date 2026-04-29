# hermes-agent 维护项目

## 角色

你是 `hermes-agent` 私人 fork 的长期维护助手。范围两件事：

- **A. 运维自用 fork**：跟 upstream 同步、解合并冲突、修本地跑飞的 bug
- **C. 在 fork 上加私人功能/skill**：用 feature 分支做个性化改造，一般不回 upstream

---

## 第一次接触必读

任何改代码前先 Read 以下文件，不要重复它们的内容到对话里：

- `**[AGENTS.md](AGENTS.md)`** —— 完整开发指南（项目结构、Agent Loop、加工具流程、profile 规则、踩坑表、测试）
- `**[README.md](README.md)**` —— 功能概览与用户视角命令
- `**[CONTRIBUTING.md](CONTRIBUTING.md)**` —— 仅当要回馈 upstream 时看

运行时状态**不在本仓库**，在用户目录：

- `~/.hermes/config.yaml` —— 当前 hermes 的实际配置
- `~/.hermes/skills/` —— 已安装 skill（30 个类别）
- `~/.hermes/auth.json` —— **含明文 OAuth token**，读可以，绝不复制到对话/提交里
- `~/.hermes/logs/` —— 运行日志，排错首站

---

## Git 拓扑

```
origin    https://github.com/lsl317603815-stack/hermes-agent.git   ← 你的 fork，默认 push 目标
upstream  https://github.com/NousResearch/hermes-agent.git         ← 官方源
default   main
```

### 同步 upstream 速记

```bash
git fetch upstream
git checkout main
git merge upstream/main          # 或 rebase，看冲突量
git push origin main
```

冲突时优先保留 upstream 逻辑，把私人改动挪到独立的 `feat/xxx` 分支。

### 分支约定

- `main` —— 始终可 fast-forward 到 `upstream/main`（即不在 main 上直接落私人 commit）
- `feat/<name>` —— 私人功能分支，基于 main
- `fix/<name>` —— 修本地跑飞的 bug；如果也影响 upstream，再额外 cherry-pick 到 upstream-PR 分支

---

## 环境

- **OS: macOS（Darwin）**。本机是主力 Mac 工作环境，多数 Python 代码 native 可跑，不需要 WSL
- **仓库路径**：`/Users/ryuka/Documents/GitHub/hermes-agent`
- **挂载点**：`cc-connect/hermes-agent` 是指向本仓库的软链，从 cc-connect 主目录可直接进入；改文件无差别落到本仓库
- 平台特定代码（terminal backends、voice、signal 处理）原作者主要按 Windows/Linux 测过，Mac 上偶有差异，遇到先看 `~/.hermes/logs/`
- venv 激活：`source venv/bin/activate`（zsh/bash 通用）
- 跑测试：按 `AGENTS.md` 的 Testing 节
- Shell：默认 zsh，POSIX 语法
- 后台 gateway 通过 LaunchAgent 常驻，plist 在 `~/Library/LaunchAgents/`；改 gateway 行为后用 `launchctl` 重启服务

---

## macOS 启动 Hermes

前台手动启动（终端 / iTerm）：

```bash
cd /Users/ryuka/Documents/GitHub/hermes-agent
source venv/bin/activate
hermes
```

LaunchAgent 重启 gateway：

```bash
launchctl list | grep hermes      # 找 label
launchctl kickstart -k gui/$(id -u)/<label>
```

---

## 加私人功能/skill 的位置选择


| 放哪                                     | 用场景                                                           |
| -------------------------------------- | ------------------------------------------------------------- |
| 仓库内 `optional-skills/<category>/`      | 通用能力，可能未来提 PR 回 upstream                                      |
| `~/.hermes/skills/<category>/`         | 纯本地偏好，不进仓库                                                    |
| 仓库内代码（`tools/`、`agent/`、`hermes_cli/`） | 改核心行为，按 AGENTS.md "Adding New Tools / Adding Configuration" 节 |


默认选 `**~/.hermes/skills/`**（本地），除非这个东西通用到想共享。

---

## 红线

- ❌ 不要 commit `~/.hermes/auth.json`、`.env`、任何含 `sk-ant-*` / `sk-ant-oat-*` / `sk-ant-ort-*` 的内容
- ❌ 不要 `git push` 到 `upstream` remote（不是你的仓库）
- ❌ 不要 `git push --force` 到 `origin/main`；feature 分支可以 force-with-lease
- ❌ 不要在代码里硬编码 `~/.hermes` —— 用 `get_hermes_home()`，见 AGENTS.md "Profiles" 节
- ❌ 不要为了让某个测试过就改 `tests/conftest.py` 的 `_isolate_hermes_home` fixture
- ❌ 不要在未沟通的情况下把 `venv/`、大型二进制、`logs/`、`__pycache__/`、`.DS_Store` 之类的加回 git
- ❌ 不要跨项目污染：本仓库跟 `/Users/ryuka/Documents/Claude/Projects/cc-connect/` 是两套完全独立的工作，别把 cc-connect / 飞书业务的东西搬进来

---

## 常见任务路由


| 任务                      | 入口                                                                         |
| ----------------------- | -------------------------------------------------------------------------- |
| Upstream 有新 release，想同步 | 按上面「同步 upstream 速记」走                                                       |
| hermes 运行时报错            | 先问用户是 CLI 还是 gateway 模式 → 复现路径 → 看 `~/.hermes/logs/`                       |
| 加一个新 tool               | AGENTS.md "Adding New Tools"（2 个文件：`tools/your_tool.py` + `toolsets.py`）   |
| 加一个 slash 命令            | AGENTS.md "Adding a Slash Command"（CommandDef + handler）                   |
| 改配置 schema              | AGENTS.md "Adding Configuration"（`DEFAULT_CONFIG` + 提升 `_config_version`）  |
| 加 CLI 主题                | AGENTS.md "Skin/Theme System"（`_BUILTIN_SKINS` 或 `~/.hermes/skins/*.yaml`） |
| 纯个人 skill，不入库           | 直接写到 `~/.hermes/skills/<category>/<name>/SKILL.md`                         |


---

## 相关的其他工作区（仅供上下文，不要混）

- `/Users/ryuka/Documents/Claude/Projects/cc-connect/` —— cc-connect 桥（飞书 / 微信 ↔ Claude Code），另一个 Claude Code 工作目录，完全独立
- 兄弟项目 `hermes短剧`、`hermes-novel` 等是基于 hermes-agent 派生的私人项目，不在本仓库内，别把私人改动落到这里
