---
title: PR review brief template
type: brief-template
usage: 当需要对 Hermes 的一个 PR 或一组改动做结构化评审时，实例化这份 brief，快速列出影响子系统、应读页面、源码入口、关键风险和验证建议。
tags: [workflow, tools]
wikilinks_out: [[index]], [[entities/tool-registry]], [[concepts/toolset-system]], [[queries/where-to-add-a-new-tool]], [[concepts/agent-loop]]
last_refreshed: 2026-04-24
refreshed_by: claude-code
---

# PR review brief template

## Usage

当你要 review 一个 Hermes PR 时，不要直接扎进 diff。先实例化这份模板，把 PR 涉及的子系统、wiki 页、源码入口和主要风险列出来。这样 reviewer 可以先建立上下文，再看 diff。

这份模板适合：
- 代码评审
- 架构评审
- 发布前风险扫一遍
- 让另一个 agent 接手 review

实例化后的产物应写到：
- PR 描述
- review comment 草稿
- `docs/plans/`
- 外部聊天消息

## Placeholders

请替换以下占位项：

- `PR_SCOPE` —— 本次改动涉及的子系统/文件范围
- `<placeholder-entity-1>`, `<placeholder-concept-1>` —— 本次 review 前必须先读的 wiki 页
- `DIFF_FILES` —— 本次 diff 的主要文件列表
- `RISK_AREAS` —— 重点风险（例如 tool visibility、memory hook、context compression、profile path）
- `CHECKS` —— 最小验证动作（lint/test/manual checks）

建议输出结构：

```markdown
# PR Review Brief

## 改动范围
- PR_SCOPE

## 先读哪些 wiki 页
- <placeholder-entity-1>
- <placeholder-concept-1>

## 重点源码入口
- DIFF_FILES

## Review 风险清单
- RISK_AREAS

## 最小验证动作
- CHECKS
```

## Output destination

实例化后的结果写到：

- PR 正文
- PR 顶部 review brief comment
- `docs/plans/<date>-pr-review-brief.md`
- 团队消息线程

**不要**把实例化结果回写到 `docs/wiki/`。