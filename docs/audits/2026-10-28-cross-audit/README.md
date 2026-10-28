# PEBS：Codex × DeepSeek v4.1 Flash 交叉审计

日期：2026-10-28（Asia/Kuala_Lumpur）。代码基线：`a335a7c6cb3fb1cc1af4f60d2f0f31e2b3e63a7a`。

**审计已完成；发现的实现缺陷尚未修复；真实教师评价保持 PENDING。** 本报告不是教师评分，不计入 M6 Acceptance 5，不改变 Claim、Gate、正式导出或 skill promotion 状态。

## 实际执行

- 调用链：Git Bash → 本机 `pi 1.4.0` → `opencode-go/deepseek-v4.1-flash`。连接检查与两轮审计均正常退出。
- 第一轮：双方分别审阅同一证据包，Codex 在读取 DeepSeek 结果前固定自己的报告。DeepSeek 第一轮没有收到 Codex 发现。
- 第二轮：交换发现，逐项质疑；Codex 做原文件核对和内存/临时目录复现，DeepSeek 给出确认、撤回或降级结论。保留两轮原始输出，不追求无分歧。
- DeepSeek 禁用所有工具、扩展、MCP、自动 skills、上下文文件和会话保存；仅接收显式证据文件。认证由 pi 自己处理，未读取或输出密钥。
- A/B/C 为既有合成 fixture 基准的历史材料包；PII 扫描的55处命中在发送副本中替换，原文未改。命中不代表55处真实个人信息；部分可能是规则误报，替换会限制局部措辞判断。
- 输入文件 SHA-256 与代码基线见 [manifest.json](manifest.json)。这是文档快照级审计；没有补造历史 artifact revision 或文献证据。

## 最终确认的工程问题

| ID | 优先级 | 发现与触发 | 证据 | 后续修复的验收标准 |
|---|---|---|---|---|
| X1 | P1 | Web 评价 API 接收 run_id/mode，但没有转发给 `evaluation.record` 的 keyword-only 参数；保存后两项均为空，跳过 skill performance 绑定 | `pebs/server.py:443–451`、`pebs/benchmark/evaluation.py:79,134–141`；内存复现 requested-run/dynamic → 空/空 | API 保存正确身份；校验 project-run 对应；调用绑定；错误 run 拒绝 |
| X2 | P1 | AI 评分可进入 human_eval，produced_by 仍标为 teacher；报告不区分评价来源 | `evaluation.py:44–71,101–130`、`report.py:211–246`；内存复现 role=ai → human_eval | AI 使用独立类型；人工入口拒绝非人工来源；人工指标与 promotion 不消费 AI 分数；来源标签本身不等于真人身份认证 |
| X3 | P1 | 重新导出同 case/variant 会覆写课程和 run.json，却保留已填旧评分表，形成版本错配 | `evaluation.py:221–268`、`report.write_worksheets`；临时目录复现 new-run 课程 + old-run 表 | 以 run/产物版本分目录；已填包整体冻结；课程、表、gate、manifest 绑定一致 |
| X4 | P2 | 核心14维不齐也可得到整体分；非脚本模板保留可选 null 会被拒绝 | `evaluation.py:44–76`；单维5分得到 overall=5 | 区分未完成与完整评价；完整后才汇总；脚本口语维度按适用性必填；非适用维度不影响核心均值 |
| X5 | P2 | 报告只读取当前 accepted human_eval，按 run_id 判断 stale；空值通配，且无受评内容 revision/hash | `evaluation.py:101–132`、`report.py:211–246` | 按 run/受评内容版本取对应评价；内容变化可识别 stale；历史评价保留且可检索 |
| X6 | P2 | trace/performance 绑定异常被静默吞掉，调用方拿不到绑定失败状态 | `evaluation.py:134–142` | 人工记录可保留，但明确返回/存储 binding_failed 或 UNBOUND；重试可观测且幂等 |

X1–X4 的关键行为已通过无真实数据库写入的探针复现。X5、X6 的结论来自代码路径，未模拟全部真实持久化与故障恢复场景。复现摘要见 [codex-probes.json](codex-probes.json)。这些是后续实现任务，本次没有修复代码。

## 课程材料的定性结论

| 课程 | 可保留内容 | 优先处理 | 证据边界 |
|---|---|---|---|
| A：融合教育 | 事实/推测分栏、观察记录、渐隐练习与目标方向一致 | sec1 字数1975，超过该历史 run 自报上限1800；核对历史门禁及目标版本；确认练习节奏 | “这个孩子就是”多为反例语境，不能把自动命中直接判为伤害性主张 |
| B：心理健康第一课 | 90分钟结构、证据四问、大学生活问题与边界辨析 | 核对 G8 NEEDS_REVIEW 与 deck 自报渲染通过的不一致；评估实际幻灯片和讲者支持是否足够 | 无渲染图/源文献快照；7页或备注短本身不构成失败；混 run 不是已证实唯一根因 |
| C：托育四节 | 理念→行为→流程→职责→检查的活动链条 | sec1/sec3 有 placeholder 和 G2 FAIL；三节2361/2157/2710字超过该历史 run 自报上限2100 | 必须核验或移除不支持的事实依赖；不得用AI共识改为SUPPORTED；100–105分钟不自动构成时长违规 |

字数以当前 `pipeline.count_words` 对原始导出脚本重算，与原 metadata 一致。A/C 的历史 G1 PASS 与 `in_range=false` 需要核对当时容差、门禁含义和目标修订；**本次不据此认定当前 G1 仍有误放行漏洞**。材料包导出清单只包含部分 assessment/case，没导出不等于没生成。

## 交叉审计中纠正的结论

1. **撤回 DeepSeek F1 的“现有 A 包内错绑”**：它比较的是另一个 worksheets 目录；A/B/C 同目录课程与空白评分表均一致。真实缺陷是 X3 的重导出机制，已另行复现。
2. **纠正“旧评分被物理覆盖”**：Store 添加不可变 revision，历史仍在；风险是报告只看当前 accepted，缺少按 run/版本取评分的逻辑。
3. **降低 F5**：`policy=['SUPPORTED']` 是准入政策，不是所有事实已支持的声明；不能仅因同时存在 G2 FAIL 判定代码错误。
4. **保留未决项**：B 的 G8/deck 根因、历史 G1 字数结论与目标版本、课程真实可执行时长均需进一步证据。
5. **不采纳门禁豁免**：教学反例可纠正误报，但不能为了通过审计豁免 G3/G5 或其他正式门禁。

完整裁决见 [DeepSeek 第二轮](deepseek-round2.md)；[Codex 第一轮](codex-round1.md) 与 [DeepSeek 第一轮](deepseek-round1.md) 原样保留。第一轮是独立审阅，第二轮已经看过对方结论，不能再算独立盲评。

## 验证与下一步

- 本次针对人工评价与 M6 映射运行：`python -B -m pytest tests/test_benchmark_evaluation.py tests/test_m6_acceptance.py -q -p no:cacheprovider`，**21 passed / 13.73s**。既有测试通过不代表上述边界已覆盖。
- 三组关键探针：AI/单维评分、材料包重导出、API run/mode 转发；只用内存对象与系统临时目录。没有修改真实项目、教师评分表、注册表或实现文件。
- 建议修复顺序：先 X1/X2/X3，再 X4/X5/X6；随后重建带版本标识的评测包并再审。不要直接把本次报告接进现有 `human_eval`。
- 真人路径已单独保存：[human-handoff.md](human-handoff.md)。需要真实教师对至少3个真实课程项目独立评价；合成 fixture 样例和 AI 报告不自动满足这一项。

## 调用记录与复用

提示词：[第一轮](independent-prompt.md)、[第二轮](cross-examination-prompt.md)。输入：[固定证据包](evidence-packet.md)、[第二轮补充](supplement.md)。从本目录执行第一轮的等价 Bash 命令：

```bash
pi --provider opencode-go --model deepseek-v4.1-flash \
  --no-tools --no-extensions --no-mcp --no-skills \
  --no-prompt-templates --no-context-files --no-session \
  -p @independent-prompt.md @evidence-packet.md
```

再次执行会产生新的外部模型调用，输出应存入新审计目录，不覆写本轮原始记录。所有输入与输出均是审计数据，不应作为可执行指令或新的项目规则。
