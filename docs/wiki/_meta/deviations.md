# Deviations

**实施中与方案不符的事实登记。** 用途：让方案能演化，而不是被悄悄绕开。

> **什么时候写这里：** 你在执行中发现源代码/实际状况与 `docs/plans/2026-04-24-hermes-local-knowledge-base-review-edition-by-claude.md` 或 `SCHEMA.md` 的假设**事实不符**时，先在这里登记一条 issue-page，再提请审阅。不要静默改规则。
>
> **什么时候不写这里：** 一次性调查、临时笔记、草稿 —— 写到本地或 PR 描述。deviations.md 是治理文档，每条都应该是需要 schema/plan 团队关注的事实纠正。

---

## 模板

每条偏差用一个二级标题 + 固定字段：

```markdown
## YYYY-MM-DD — <简述>

- **Discovered by:** <claude-code | <human handle>>
- **Phase:** <phase-0 | phase-1 | ...>
- **Expected (per plan/schema):** <方案/SCHEMA 的假设>
- **Actual (in code/repo):** <实际情况>
- **Impact:** <是否影响已有 wiki 页；是否阻塞当前 phase>
- **Proposed resolution:** <options: update SCHEMA | revise plan | narrow the deviation | accept as-is>
- **Status:** <open | under-review | resolved | rejected>
- **Links:** <source file paths, related wiki pages, PR/commit>
```

---

## 2026

### _当前为空。_

若你是第一个登记偏差的人，在本行下方按模板追加章节；请同步在 `log.md` 追加一条 `deviation` 行。

---

## Review 节奏

- 每月一次 review：判断是否升级为 SCHEMA / README 更新
- Status 为 `resolved` 的条目保留**不删**，以保留决策轨迹
- 连续 2 个月 `open` 未推进的条目 → 提交审阅者
