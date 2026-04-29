---
title: Onboarding brief template
type: brief-template
usage: 当新人或新 agent 需要快速接手某个 Hermes 子系统时，实例化这份 brief，给出阅读顺序、关键页面、关键源码入口与首批验证动作。
tags: [onboarding, workflow]
wikilinks_out: [[index]], [[SCHEMA]], [[entities/aiagent]], [[concepts/agent-loop]], [[entities/tool-registry]]
last_refreshed: 2026-04-24
refreshed_by: claude-code
---

# Onboarding brief template

## Usage

当你要让一个新人开发者、评审者，或者新的 Claude Code 会话快速接手某个子系统时，先实例化这份模板。目标不是把所有知识重新讲一遍，而是：

1. 指出应该先读哪些 wiki 页
2. 指出对应源码入口在哪
3. 指出最容易踩的坑
4. 给出一个最小验证路径

实例化后的产物应写到：
- PR 描述
- `docs/plans/`
- 入职/交接文档
- 聊天消息

**不要**写回 `docs/wiki/`。

## Placeholders

请把下面占位项替换成真实内容：

- `<placeholder-subsystem-overview>` —— 该子系统的总览页（若没有，用 `[[index]]` + 最相关 entity/concept 组合代替）
- `<placeholder-primary-entity>` —— 该子系统最核心的 entity 页
- `<placeholder-primary-concept>` —— 该子系统最核心的 concept 页
- `<placeholder-comparison>` —— 如果该子系统有一个最容易混淆的比较页，放这里；没有可删
- `SOURCE_FILES` —— 需要直接打开的 2–5 个源码文件路径
- `FIRST_TASK` —— 新人接手后的第一个最小动作

建议输出结构：

```markdown
# <Subsystem> Onboarding Brief

## 你要先建立的心智模型
- 先读：<placeholder-subsystem-overview>
- 再读：<placeholder-primary-entity>
- 再读：<placeholder-primary-concept>
- 易混点：<placeholder-comparison>

## 必看的源码入口
- SOURCE_FILES

## 最容易踩的坑
- 从上述 wiki 页提炼 3 条

## 第一个最小验证动作
- FIRST_TASK
```

## Output destination

实例化后的结果写到以下任一位置：

- `docs/plans/<date>-<subsystem>-onboarding-brief.md`
- PR 描述中的 onboarding / handoff section
- Slack / 飞书消息
- 团队知识库或入职文档

**禁止**把实例化结果写回 `docs/wiki/briefs/`；这里只有模板。