# Personal Wiki Phase 2 — Batch 1 Claude Brief

## 任务目标

继续推进 `/Users/ryuka/personal-wiki` 的 Phase 2。

**这次只做一个窄目标：**
- 实现 `scripts/lint_wiki.py`
- 让它能对当前 Phase 1 页面集跑通基础检查
- 运行并修掉它发现的真实问题（如果有）
- 更新相关文档与日志

## 非目标

这批不要做：
- `ingest_seed.py`
- `drift_check.py`
- 自动 ingest
- 大规模扩页
- Hermes runtime 集成
- Git 初始化
- 修改 Hermes 子库

## 重要执行要求

你必须显式使用已安装的 Claude Code skill：
- 先执行 `/using-superpowers`

不是“按 superpowers 风格”，而是**真的触发这个 skill**。

## 当前已有状态

个人总库路径：
- `/Users/ryuka/personal-wiki`

当前总库已有：
- 根文件：`README.md`, `SCHEMA.md`, `index.md`, `log.md`
- meta：`_meta/taxonomy.md`, `_meta/source-manifest.md`, `_meta/coverage-map.md`, `_meta/backlog.md`, `_meta/deviations.md`
- domain 入口页：`domains/hermes/README.md`, `domains/fiction/README.md`, `domains/ai-short-video/README.md`, `domains/workflows/README.md`
- canary 页：`concepts/story-hook.md`, `comparisons/novel-hook-vs-short-video-hook.md`, `queries/how-to-link-fiction-and-ai-short-video-workflows.md`

已知当前人工验收结果：
- markdown 文件总数：16
- frontmatter 缺失：0
- dangling wikilink：0

## 本批要求实现的 linter 范围

实现文件：
- `/Users/ryuka/personal-wiki/scripts/lint_wiki.py`

至少检查：
1. `.md` 文件是否存在 frontmatter（当前所有页面都应该有）
2. `type` 是否与目录角色匹配
3. 内容页是否具备：
   - `title`
   - `type`
   - `domain`
   - `tags`
   - `status`
   - `created`
   - `updated`
   - `relates_to`
   - `sources`
4. meta 页是否具备：
   - `title`
   - `type: meta`
   - `updated`
5. `tags` 是否都在 `_meta/taxonomy.md` 白名单内
6. `status` 是否属于允许值：`seed | draft | stable | stale`
7. wikilink 是否都指向存在页面（允许 `README`, `SCHEMA`, `index`, `log` 这些根级目标）
8. page 数量与 index 中登记情况做基础一致性检查
9. 输出清晰的 findings；无问题时输出 clean/no findings
10. 支持 `--strict` 模式；strict 下有任何 error 就非 0 退出

## 实施原则

- 小批次
- 不扩 scope
- 直接改文件
- 先让 linter 在当前页面集上可运行
- 如果 linter 报的是当前真实问题，就顺手修当前总库文件，让它最终通过
- 但不要因此扩成 Phase 2 全量项目

## 允许修改的范围

仅允许修改：
- `/Users/ryuka/personal-wiki/scripts/lint_wiki.py`
- `/Users/ryuka/personal-wiki/SCHEMA.md`（如果 linter 实现需要微调说明）
- `/Users/ryuka/personal-wiki/index.md`
- `/Users/ryuka/personal-wiki/log.md`
- `/Users/ryuka/personal-wiki/_meta/deviations.md`
- `/Users/ryuka/personal-wiki/_meta/backlog.md`
- `/Users/ryuka/personal-wiki/` 下被 linter 发现且必须修复的 markdown 页

不允许修改：
- `/Users/ryuka/Documents/GitHub/hermes-agent/docs/wiki/` 下任何文件
- Hermes runtime 文件

## 完成后必须做的验证

至少运行：

```bash
python3 /Users/ryuka/personal-wiki/scripts/lint_wiki.py
python3 /Users/ryuka/personal-wiki/scripts/lint_wiki.py --strict
```

并在最终输出里报告：
- 创建/修改了哪些文件
- lint 普通模式结果
- lint strict 模式结果
- 还有哪些 Phase 2 项目未做

## 一句话

这是 **Phase 2 的第一小批**：只把 `lint_wiki.py` 做出来、跑通、把当前总库 lint 到干净。