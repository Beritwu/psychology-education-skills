# 第二轮：双向质疑与裁决

你已完成第一轮独立审计。现提供双方独立报告、内存/临时目录复现结果、补充代码与相同证据包。保持无工具、只读审计；这是 AI 建议，不是真人评分。

请逐项审阅 Codex C1–C6，回答确认/缩小结论/反驳/证据不足，给出理由。另对你的 F1–F8 做必要纠正，尤其：

1. 你 F1 说“包内评分表”错绑，但初始包明确是 separate_worksheet_run（另一个 worksheets 目录），不是同目录表。已核对 A 同目录表与 course 都是 run_77e357790d91，B/C 同样一致。撤回当前包内错绑结论；另评估 Codex 已复现的 export_kit 重导出导致已填表旧 run、新课程新 run 的机制缺陷。
2. human_eval 使用同一 artifact 的新 revision，不代表旧分物理删除。请区分历史修订仍在、报告只取当前 accepted 评分，以及空 run_id 跨 run 绑定。
3. policy=['SUPPORTED'] 是准入政策，不是“所有 Claim 已支持”的断言；旁边已有 G2 FAIL。请判断 F5 是否应降为显示改进而非已证实缺陷。
4. B 的 G8 和 deck 自报 QA 矛盾，能够证明包内结论不一致，但没有源 gate revision、thumbnail 和运行时间线，不能证明唯一根因就是混 run；请保留根因不确定性。
5. A 的标签用语多为反例；G3/G5 失败不能建议豁免正式门禁。C 没有被证明应是每节90分钟，不可当已证实时长违规。7页/90分钟或notes字数少本身也不是硬错误。
6. 新补充：server.HumanEvalIn 定义 run_id/mode，但 record_evaluation 调用 evaluation.record(engine,payload.model_dump())，未传这两个 keyword-only 参数；内存复现 requested-run/dynamic 变成空字符串/空字符串。请审计此问题与技能版本绑定影响，标为新发现，不假称第一轮已发现。

请不超过2000字输出：裁决表、撤回/降级项、双方仍有分歧、最终前三个修复优先级、留给真实教师的步骤。不用多数票、共识分数或模型身份认证结论。
