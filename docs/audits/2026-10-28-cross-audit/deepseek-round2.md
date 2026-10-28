## 裁决表（C1–C6）

| 项 | 裁决 | 理由与修正 |
|---|---|---|
| C1 | 确认，P1（限入口层） | `validate_eval` 只查 reviewer；`role=ai` 仍写 `human_eval`，`produced_by=teacher:...`；单维 5 分可得 overall=5。无法认证真人身份，但入口应拒绝非人工来源，或分离 `ai_review`。 |
| C2 | 确认，P1 | `export_kit` 用 case/variant 固定目录，重导出覆写 course/run，`write_worksheets` 保留已填表，形成“新课程+旧表”。临时目录已复现。 |
| C3 | 确认，P2 | 不要求 14 维齐全，overall 只平均已填维度；脚本未强制 `spoken_naturalness`。另：模板把可选维度写成 `null`，验证会当非数字报错。 |
| C4 | 确认，缩小到代码层 | 只存 run_id，不存 artifact revision/hash；空 run_id 视为 bound。不能据此断言所有 API 路径都允许空值，但新证据证明 server 路径确实丢 run_id。 |
| C5 | 部分确认 | 字数可复算：A/sec1=1975>1800；C 三节 2361/2157/2710>2100。但 G1 PASS 与 `in_range=false` 是否同一门禁语义，缺 G1 定义、容差、目标 revision，不能判门禁缺陷。 |
| C6 | 确认（内容状态，非代码缺陷） | C 的 placeholder 与 G2 FAIL 是历史材料事实；不能因审计意见一致改 SUPPORTED。包内无源文献快照，不能替教师认证学科准确性。 |

## 对 F1–F8 的纠正

- **F1：撤回“包内错绑”**。初始包 A 的差异是 `separate_worksheet_run`（run_1ae60eced739）与 kit（run_77e357790d91）分属不同目录；同目录表与 course 均为同 run。不能称当前包内错绑。保留 C2 的重导出机制缺陷：旧已填表配新 course/run，P1。
- **F2：缩小并改写**。`add_revision` 不物理删除历史；`set_accepted` 只切当前 accepted，报告只读当前 accepted。故问题是“旧 run 评分在报告中消失/被新 accepted 取代”，不是物理删除；空 run_id 被 `human_eval_for_run` 视为 bound，造成跨 run 绑定。绑定缺陷仍成立，P1。
- **F3：确认**。无 artifact revision/hash；同一 run 新 revision 不会 stale。历史修订仍在，但报告无法判断现行评分对应哪版产物。P2。
- **F4：确认机制，降根因断言**。`_gate_lines` 遍历全部 `gate_result`，各取最新 revision，未按 run 过滤，可能混入旧门禁。B 的 G8 与 deck 自报 QA 矛盾只能证明包内结论不一致；缺源 gate revision、缩略图、时间线，不能证明唯一根因是混 run。
- **F5：降为 P3 显示改进**。`policy=['SUPPORTED']` 是准入政策，不是“所有 Claim 已支持”；旁边已有 G2 FAIL。读者误读风险真实，但不是已证实功能缺陷。建议分列 execution/gate/claim/export。
- **F6：确认，P2**。`except Exception: pass` 使 §40 绑定失败无痕迹；应写 `binding_result` 或标 UNBOUND，不能吞错。
- **F7：确认，P2**。14 维不齐可形成满分 overall；模板 `spoken_naturalness: null` 会被验证拒绝，非脚本教师原样保留即失败。
- **F8：部分确认**。字数超该 run 自报 max 可复算；但“超时、教师被迫大删”是推断。C 的 100/105/105/90 是材料分钟合计，未证每节应 90 分钟；7 页/90 分钟、notes 31–44 字本身不是硬错误。A 的“这个孩子就是”多为例句/反例；G3/G5 FAIL 不得建议豁免正式门禁。

## 新发现 N1（第一轮未发现）

`server.HumanEvalIn` 定义 `run_id/mode`，但 `record_evaluation` 调 `record(engine, payload.model_dump())`，未传 keyword-only 参数。内存复现：requested-run/dynamic 记录为 `''/''`。后果：API 评分不触发 `build_trace/update_performance`，skill 版本绑定失效；报告按空 run_id 跨 run bound。标记 P1，不假称第一轮已发现。

## 双方仍有分歧

1. B 的 G8 与 deck 冲突：包内不一致可确认；“混 run 是唯一根因”证据不足。
2. C5：字数确认；G1 PASS 是否门禁矛盾，取决于 G1 定义与历史 revision，未定。
3. F5：显示误读风险 vs 已证实缺陷，应降级。
4. C 的时长：分钟合计是事实；“应每节 90 分钟”未被证明。
5. A 的 SAFETY 命中：反例语境可能误报；可人工复核，但不能豁免正式门禁。

## 前三个修复优先级

1. **绑定身份**：server 传 `run_id/mode`；评分记录强制 run_id，artifact 改按 run 区分；保存受评产物 revision/hash，变更即 stale。
2. **材料包冻结**：每 run/产物版本独立目录；course、worksheet、gate、manifest 一体绑定；gate 摘要按 run/revision 过滤，禁止跨目录配对。
3. **评分完整性**：14 维齐全才汇总；脚本强制口语维度；human_eval 拒绝 AI 来源；修复可选 null；绑定失败显式标 UNBOUND；报告分列政策/门禁/Claim 状态。

## 留给真实教师的步骤

1. 只用冻结且同 run 的包，核对 course/run/worksheet/manifest；拒收跨目录配对。
2. 先读 G2/G3/G5/G8、字数与分钟，区分反例与禁用表达；G3/G5 失败不豁免。
3. 独立填 14+1 维、comment、must_fix；提交后回读报告，确认 run_id 与 skill 版本；空 run_id 视为未绑定。
4. 视觉需原缩略图/渲染图；B 确认 7 页与备注是否够；C 确认实际课时与使用方式。
5. 至少 3 个真实项目，教师签名及独立性声明；AI 报告仅供参考，不写入 human_eval。
