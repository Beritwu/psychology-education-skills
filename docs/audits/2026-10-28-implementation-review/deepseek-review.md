# 只读实现审计（未执行）

只读静态审计；没有运行任何命令或测试，因此不声称 68 个测试或全套测试的结果。以下结论均来自代码路径推断，并标注“代码可证”或“条件触发”。不涉及真实学生材料、凭据或正式签核；人工评分不得伪造，AI 报告仍应独立。

## P1

### 1. Skill Performance Registry 把不同 Skill 版本混在同一条记录里（代码可证）
**位置**：`performance.record_run()`、`performance.record_evaluation()`、`review_promotions()`。

**触发**：同一 `skill` 先有 v1 的 `human_score`，随后 registry 升级到 v2，再记录 v2 的 run 或人工评价。`record_run()` 以 `data["skills"].get(skill)` 取旧记录，只覆盖 truthy 的 `version/provider_sha/package_sha256/patch`，但保留旧 `human_score`、`teacher_edit_ratio`、`human_evaluations` 等。若先 `record_run(v2)` 再评价 v2，`record_evaluation()` 可能因 identity 已变为 v2 而重新计算；但在人工评价到来前，v2 已暂时携带 v1 的人工分。若未先 `record_run(v2)`，`record_evaluation()` 看到旧 record identity 不匹配会直接 `continue`，但仍保存 `human_evaluations` 条目并最终让外层标记 `BOUND`。

**影响**：`BOUND` 可能表示“评分已保存”，但对应版本的 skill record 没有更新；或者 v2 继承了 v1 的人工分。`review_promotions()` 会基于错误版本的 `human_score` 给出 promotion 判断，直接破坏 §40/§68/§69 的版本绑定语义。

**最小修复**：将 `skills` 记录按不可变 identity 分组，例如 `(skill, version, provider_sha, package_sha256, patch)`，或在 identity 变化时新建 record 并重置 `human_score`/`teacher_edit_ratio`/`human_evaluations`。`record_evaluation()` 不应静默 `continue`；应写入与 trace identity 完全一致的 record，无法写入则明确 `FAILED`。

### 2. 未解析步骤被当作 `run_snapshot` 的“空版本 skill”，导致合法运行绑定失败（条件触发，代码路径可证）
**位置**：`trace.build_trace()`、`performance.record_evaluation()`。

**触发**：run 中存在一个 `step_id` 既不在 `snapshot["identities"]`，也不在 `snapshot["step_skills"]` 中，例如内部编排步骤、门禁步骤、重命名后的 handler step，或 registry snapshot 未覆盖的步骤。`build_trace()` 会生成 `skill="step:..."`、`version=""` 的伪 identity，但仍把 `identity_source` 设为 `"run_snapshot"`。`record_evaluation()` 的第一道检查通过，随后在循环中因 `not version` 抛出 `Cannot bind an evaluation without a skill version`。

**影响**：即使该 run 中真实 skill 都有 build-time snapshot，人工评分也会以 `binding=FAILED` 保存；CLI 返回非零，performance registry 不更新。若真实 pipeline 中存在非 skill 步骤，可能所有评价都无法绑定。

**最小修复**：`build_trace()` 对未解析步骤使用独立来源标记，例如 `identity_source="unresolved_step"`，不要伪装成 `run_snapshot`；`record_evaluation()` 只对已解析的真实 skill 执行 snapshot/version 校验，把未解析步骤单独记录或忽略，若没有任何可绑定 skill 才明确失败。

### 3. `report.write_worksheets()` 的普通路径会写出 `target: null` 的工作表（条件触发，取决于调用点）
**位置**：`report.write_worksheets()`、`report.load_runs()`、`evaluation.record()`、测试 `test_teacher_must_submit_the_snapshot_they_reviewed`。

**触发**：调用 `write_worksheets(load_runs())` 或任何没有显式补充 `evaluation_target` 的 run 字典。`load_runs()` 从 `run.json` 读取的记录没有 `evaluation_target`；`write_worksheets()` 只写 `template["target"] = run.get("evaluation_target")`，不会像 `evaluation.export_kit()` 那样计算 target。教师填完后，`load_worksheet()` 返回 `target=None`，`evaluation.record()` 直接报“必须提供受评材料的 target”。

**影响**：教师完成 14 维评分后无法提交，属于人工评价入口的阻断。现有回归测试主要覆盖 `export_kit()` 路径，因此不一定暴露这个公共函数的问题。

**最小修复**：`write_worksheets()` 对每个 run 解析 `evaluation.target_for_run()`，或要求调用方提供 target 并在缺失时立即报错，禁止生成不可提交的工作表；README/CLI 也应明确 target 来源。

## P2

### 4. `_worksheet_is_filled()` 漏掉部分教师输入，仍可能覆盖已填工作表（代码可证）
**位置**：`report._worksheet_is_filled()`、`report.write_worksheets(preserve_filled=True)`。

**触发**：教师只填写了 `must_fix`、`nice_to_have`、`evidence_errors`、`routing_errors` 或 `plan_errors`，尚未填写 `reviewer`、`comment`、`scores` 或 `edits`。`_worksheet_is_filled()` 对这些字段返回 `False`，后续 `write_worksheets()` 会重写该文件。

**影响**：教师已录入的定性修改意见或错误计数被静默覆盖，是 X3 的残留数据丢失面。虽不是完整评分，但仍是不可再生的教师输入。

**最小修复**：`_worksheet_is_filled()` 覆盖所有教师可编辑字段；只要任一字段非空/非默认即视为已填写。YAML 解析失败也不应当作空白覆盖。

### 5. `build_trace()` 不是 run-scoped，历史 trace 会混入最新/其他 run 的 route、plan、gates、reviews（代码可证）
**位置**：`trace.build_trace()`。

**触发**：项目内有多个 run，或之后重新计算门禁/新增 review，再请求旧 run 的 trace。`build_trace()` 使用 `store.accepted_content("router_result")`、`store.accepted_content("build_plan_dynamic")`，并遍历所有 `gate_result`/`review_record` artifact，没有按 `run_id` 或 `produced_by_run` 过滤。另有一处 `node = node_by_skill.get(step["step_id"])`，但 `node_by_skill` 是按 `node["skill"]` 建的，step_id 与 skill 名不同时会丢失 gate/reuse/parallel/reason 元数据。

**影响**：Evaluation Tab 和历史审计可能把最新 route/plan、其他 run 的门禁和 review 展示成该 run 的事实；不是人工评分伪造，但会误导审计判断。

**最小修复**：route/plan/gates/reviews 均按 run 或 revision provenance 过滤；优先读取 run 自己的 trace 快照。plan 元数据应按 `skill_name` 或 step→node 映射取值，而不是直接用 `step_id`。

### 6. `record_trace()` / `record_run()` 仍缺少 run_id 幂等，重复记录会放大 runs（残留 X6 面，代码可证）
**位置**：`performance.record_trace()`、`performance.record_run()`。

**触发**：同一 run 的 trace 被重复写入（重试、刷新、补偿任务），或同一 skill 在一次 build 中出现在多个 step。`record_trace()` 不读取 `trace["run_id"]`，`record_run()` 每次都执行 `runs = previous + 1` 并累加 success/schema 计数。

**影响**：`runs`、`success_rate`、`schema_failure_rate` 被重复计数，影响 `PROMOTION_THRESHOLD["min_runs"]` 和 promotion/demotion 判断。人工评分账本已经幂等，但构建表现账本仍不幂等。

**最小修复**：按 `(run_id, skill, identity)` 保存构建记录，或在 `record_trace()` 内按 run_id 去重/聚合；同一 build 中同一 skill 的多个 step 应聚合为一次 run。写入时也应使用与 `record_evaluation()` 相同的锁。

### 7. `render_markdown()` 重新加载全局 runs，导致 Markdown 与传入 summary 不一致（代码可证）
**位置**：`report.render_markdown()`、`failure_category_section()`、`quality_section()`。

**触发**：调用 `summarize(custom_runs)` 或传入过滤后的 summary，再 `render_markdown(summary)`。`render_markdown()` 中 `failure_category_section()` 和 `quality_section()` 不接收参数，内部再次 `load_runs()`，因此会追加全局 runs 的失败类别和质量指标，而不是 summary 中的 runs。

**影响**：同一份报告的表格、失败分布、质量指标可能来自不同 run 集合；`benchmark_summary.json` 与 Markdown 不一致。测试或历史快照报告尤其容易误判。

**最小修复**：在 `summarize()` 中保留 source runs 或 failure/quality 摘要，`render_markdown()` 显式传入 `summary["runs"]`；不要让渲染阶段重新读取全局目录。

### 8. 较小 P2：CLI 不捕获 YAML 解析错误；manifest 缺失时冻结校验可被跳过
**位置**：`cli.cmd_benchmark()`、`report.load_worksheet()`。

- `load_worksheet()` 使用 `yaml.safe_load()`，CLI 只捕获 `ValueError/OSError`，不捕获 `yaml.YAMLError`。教师工作表格式损坏时 CLI 会 traceback，而不是给出可操作错误。
- `load_worksheet()` 仅在 `manifest.json` 存在时校验 `course.md`/`run.json` 哈希。若 kit 目录中 manifest 被删除或从未生成，冻结材料校验被跳过；target 仍绑定 Store，但教师实际阅读的 `course.md` 可能已被替换。

**最小修复**：CLI 捕获 `yaml.YAMLError`；kit 目录缺少 manifest 时默认拒绝提交，或要求显式 `--allow-unfrozen` 并记录风险。

## 范围与限制

- 未执行测试，未验证 68 个或全套测试的实际结果；以上均为静态代码审计。
- 未获得 `Store.get_run()` 的完整序列化行为、registry 加载实现、CLI/report 的实际调用点、runner 是否重复调用 `record_trace()`。因此部分问题标注为“条件触发”。
- 已确认 X1/X2/X4/X5 的修复在当前代码中基本存在：run_id/mode 绑定、human-only 校验、target/revision stale、optional null 处理；未发现直接回归。主要残留集中在 X3 的工作表覆盖面、X6 的构建计数面，以及 performance registry 的版本绑定。
- 现有测试覆盖 `export_kit()`、API 评分、stale、binding failure 等；对公共 `write_worksheets()`、重复 `record_trace()`、历史 trace scoping、YAML 损坏路径覆盖不足。
- 本审计不构成门禁豁免、发布批准或正式签核；人工评分必须继续由真实教师提交，AI 审计不得进入 human score。
