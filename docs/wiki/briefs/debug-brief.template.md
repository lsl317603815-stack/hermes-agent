---
title: Debug brief template
type: brief-template
usage: 当 Hermes 某个行为异常、测试失败、工具不可见、provider/engine 生命周期异常时，实例化这份 brief，先把上下文和排查顺序结构化，再进入调试。
tags: [workflow, architecture]
wikilinks_out: [[concepts/agent-loop]], [[entities/memoryprovider]], [[entities/contextengine]], [[entities/tool-registry]], [[queries/how-tools-enter-the-model-surface]]
last_refreshed: 2026-04-24
refreshed_by: claude-code
---

# Debug brief template

## Usage

Hermes 的很多问题都跨多个文件和多个契约面。遇到 bug / regression / 工具不可见 / provider 不工作 / 压缩行为异常时，先实例化这份模板，把：

1. 症状
2. 最可能涉及的子系统
3. 先读哪些 wiki 页
4. 先查哪些源码入口
5. 先做哪几个最小验证

写清楚，再进入调试。这样能避免一上来全仓乱搜。

实例化后的产物适合写到：
- debug issue
- `docs/plans/`
- PR 描述里的 root-cause section
- 团队聊天线程

## Placeholders

请替换以下占位项：

- `SYMPTOM` —— 现象描述
- `LIKELY_SUBSYSTEMS` —— 可能相关的 1–3 个子系统
- `<placeholder-page-1>`, `<placeholder-page-2>` —— 先读的 wiki 页
- `SOURCE_FILES` —— 要打开的源码入口
- `MIN_CHECKS` —— 先做的最小检查动作
- `OPEN_QUESTIONS` —— 暂未确定但需要验证的假设

建议输出结构：

```markdown
# Debug Brief

## 症状
- SYMPTOM

## 最可能相关的子系统
- LIKELY_SUBSYSTEMS

## 先读这些 wiki 页
- <placeholder-page-1>
- <placeholder-page-2>

## 先查这些源码入口
- SOURCE_FILES

## 最小验证动作
- MIN_CHECKS

## 当前开放问题
- OPEN_QUESTIONS
```

## Output destination

实例化后的结果写到：

- `docs/plans/<date>-debug-brief.md`
- issue / bug ticket
- PR root-cause section
- 团队聊天线程

**不要**把实例化结果写回 `docs/wiki/briefs/`。这里仅保存模板。