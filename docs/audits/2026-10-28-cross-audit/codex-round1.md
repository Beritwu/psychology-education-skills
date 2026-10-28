# Codex 独立审计记录（第一轮）

日期：2026-10-28；代码基线：a335a7c6cb3fb1cc1af4f60d2f0f31e2b3e63a7a。
本记录在读取 DeepSeek 第一轮结果之前固定。对象为 evidence-packet.md 中的评价代码与 A/B/C 历史材料包；另对当前函数做内存/临时目录复现。没有向真实 Store 或 performance 注册表写入评分。

## 发现

### C1 / P1：AI 与真人评分没有入口级隔离（已复现，高置信）

`pebs/benchmark/evaluation.py:44` 仅要求 reviewer 非空；不验证 role 或评价来源。`record():101–130` 接受 `role=ai`，仍写 artifact_id `human_eval`，并把 produced_by 拼成 `teacher:...`。给一个维度 5 分也能得到 overall=5.0。`report.human_eval_for_run():211–246` 不检查来源。

触发：把 AI 评审结果按当前评分接口提交。影响：AI 结果可污染人工指标；有 run_id 时还会进入 skill performance 更新。复现证据见 codex-probes.json（MemoryStore，不是真实数据库）。建议独立的 ai_review 记录与明确来源枚举；人工入口拒绝非人工来源，不能靠 reviewer 名字做身份判断。本次 AI 报告绝不通过现有人工入口提交。

### C2 / P1：课程材料更新与已填评分表保护相冲突（已复现，高置信）

`evaluation.export_kit():221–268` 使用 case/variant 固定目录，覆写 course.md 和 run.json 后调用保留已填内容的 write_worksheets。后者保护旧表是正确的，但整体材料包没有一致性检查。临时目录复现：先导出 old-run，填 reviewer，再导出 new-run，得到 course/run=new-run、worksheet=old-run。

建议每个 run_id/产物版本使用独立目录，并把内容摘要、评分表与 manifest 一同绑定；已填包整体冻结。现有实际 A 的独立 worksheets 表绑定 run_1ae60eced739，而 evaluation_kit/A-dynamic 绑定 run_77e357790d91。这两个目录本可各自保留历史版本，差异本身不是损坏证据，但不能交叉配对交给教师。

### C3 / P2：评分完整性不足（已复现，高置信）

`validate_eval():44–71` 不要求 14 个核心维度齐全，也不根据脚本类型要求 spoken_naturalness；overall_score 平均所有已给维度。只给 goal_clarity=5 可形成满分 overall，无法与完整 14 维评分公平比较。另模板将可选 spoken_naturalness 写成 null，而验证遇 null 会报错，非脚本教师原样保留可选字段也会失败。

建议区分 incomplete draft 与可汇总 complete 状态，核心维度完整后才计入总体分；可选维度按任务适用性处理，汇总口径固定。

### C4 / P2：评分绑定只检查 run_id，不验证具体内容（代码已确认，未做真实数据库复现）

`record()` 不保存被审产物 revision/hash；`human_eval_for_run()` 允许空 run_id，非空时也只做字符串匹配。相同项目产物在后续 accept/局部修改后，旧评分无法凭此检查确认仍适用。建议强制 run 身份与受评产物版本清单，内容变更后标 stale，不使用旧评分证明新产物质量。仅凭本次代码片段不能断言所有 API 调用路径都允许空 run_id；这是底层入口能力与报告绑定的缺口。

### C5 / P2：历史课程字数与门禁摘要矛盾（文本已重算，高置信；不推断当前门禁仍有同样缺陷）

用当前 pipeline.count_words 对原始导出 JSON 重算：A/sec1=1975（该 run 自带上限1800）；C/sec1=2361、sec2=2157、sec3=2710（该 run 自带上限2100）。metadata 的 in_range=false 与重算相符，但材料包顶端 G1 均为 PASS。应核对当时规则容差、产物修订与门禁目标版本，再用同一版本门禁重放；不能直接把历史 PASS 当今天的正式交付证据。

### C6 / P2：C 的教学文本仍含待核验内容（历史材料中已确认）

C/script:sec1/u2 与 sec3/u2 的 placeholder=true，后者关联 clm_949ec8536b@v3；材料包已有 G2 FAIL。不能因为双方审计意见一致就改为 SUPPORTED。可采取核验来源、收窄/移除不被支持的依赖，无法做到则维持草稿。本包不含源文献快照，不能替教师作学科准确性认证。

## 课程定性审阅

- A：目标、事实/推测分栏、观察记录改写与课堂练习方向一致，值得保留。三个教案分别为45/70/65分钟；不是已证实的时长违规，但交给教师前应说明是完整课堂方案还是短脚本配套活动，避免把脚本篇幅当完整授课时长。标签表达经常出现在否定和反例语境，不能把正则命中直接判为伤害性主张。教师需检查真实班级能否完成活动及评价量规是否够用。
- B：90分钟教案含目标、证据四问、事实/解释区分和生活情境，教学结构有基础。需要教师判断第一课的兴趣建立与反误解/边界说明是否平衡。材料包不含源证据快照和幻灯片渲染图，因此不能判定事实核验与视觉交付达标；仅有一条 G8 NEEDS_REVIEW 也不等于其他门禁全部已过。
- C：把理念映射到可观察行为、流程、岗位与检查点的练习有可执行方向；优先处理占位内容及篇幅问题。教案时长为100/105/105/90分钟，应明确使用方式。导出包仅展示 assessment:sec1/case:sec1:1；不能据此断言其他章节没有评价或案例，因为 export_kit 使用固定导出清单。

## 交叉核查要求

请 DeepSeek 对 C1–C6 分别给出确认/缩小结论/反驳/证据不足，并指出其独立发现中有无将反例、缺失导出内容或历史门禁错误误当作当前实现缺陷的情况。最终保留分歧，不用两模型平均分替代真人验收。
