# 交叉审计后的实现与复审

日期：2026-10-28。基于 `a335a7c6cb3fb1cc1af4f60d2f0f31e2b3e63a7a` 的未提交工作区修改。首轮只读审计保持原样；本目录记录用户随后授权的实现。**真人教师评价仍为 PENDING。**

## 实现结果

| 原问题 | 当前行为 | 公共边界验证 |
|---|---|---|
| X1 运行身份丢失 | API/CLI 传递并校验 project、run、mode；必须提交所读材料的 target | API 保存和查询；CLI 冻结包往返 |
| X2 AI 进入教师指标 | 人工入口拒绝 AI 来源；报告只读取 Store 中的真人记录；AI 审计保存在独立文档 | AI 提交拒绝；嵌入 run.json 的 AI 分数不进入报告 |
| X3 包与已填表错配 | run + target 哈希分目录；先在临时目录完成整包再发布；既有包校验；所有已填或损坏工作表保留 | 重导出、新版本导出、只填 must_fix/错误计数、损坏 YAML |
| X4 不完整评分 | 14 维完整后才有核心均分；脚本口语分按适用性必填，非脚本 null 可接受且不改变核心均值 | 缺维拒绝、脚本必填、可选分稳定均值 |
| X5 内容/历史错绑 | 不可变 human_eval:<run_id> 与受评 revision/hash 关联；过期不计入当前报告；API 可指定历史 run | 内容变更 stale、历史运行读取、旧评分不能套到新课程 |
| X6 静默失败及重试 | 评分保留 PENDING/BOUND/FAILED；CLI 失败非零；评价与构建分开计数；提交/trace 重放幂等；跨进程写锁和原子替换 | 文件系统故障→重试；重复提交/重复 trace；新版本不继承旧分 |

补齐的教师路径：Direct 基线导出完整原文并导入评价快照（`evaluation_import=true`），不调用模型；普通工作表解析目标，无法解析时不生成不可提交的表；CLI 验证冻结包哈希和 manifest，格式损坏时返回可操作错误。新运行记录无凭据的技能身份快照。旧运行缺少该快照时，教师评分仍可保存，但技能绑定明确 FAILED，不用当前注册表猜历史版本。

## 与 DeepSeek 的复审裁决

实际通过 Git Bash 调用 `pi 1.4.0` 的 `opencode-go/deepseek-v4.1-flash`，工具/扩展/MCP/自动上下文/会话保存均关闭。只发送实现代码和合成测试；输入 PII 扫描 0 命中。文件身份见 [input-manifest.json](input-manifest.json)，原始意见见 [deepseek-review.md](deepseek-review.md)。

| 复审意见 | 裁决与处理 |
|---|---|
| 1：技能新版本继承旧分 | 确认并复现，已修复：身份变更新建统计并保留 skill_history。历史评分完整身份保存在 human_evaluations；BOUND 表示身份账本已写入，不把历史评分强行写到当前版本统计。 |
| 2：未解析步骤导致绑定失败 | 接受“来源标记不准确”，改为 unresolved_step。没有采纳忽略未知步骤：缺少技能版本仍明确 FAILED。已有静态/动态完整构建测试证明已注册步骤可绑定；不能为得到 BOUND 而猜测缺失身份。 |
| 3：普通工作表 target:null | 确认并复现，已修复自动解析；无可追溯目标时不生成表。 |
| 4：只填修改意见或错误数仍被覆盖 | 确认并复现，已保护全部教师输入；语法损坏的表也不重写。 |
| 5：历史 trace 混入最新元数据 | 确认并复现，route/plan/gate 按 run 的目标修订读取；review 按生产运行筛选；节点以 skill 身份查找。 |
| 6：重复构建 trace 累加 runs | 确认并复现，以 run + skill 完整身份去重，同一 trace 的同技能步骤聚合。无 run_id 的旧手工 record_run 接口仍按每次调用记录一次，不能将其用作重放入口。 |
| 7：Markdown 和 summary 来自不同运行集合 | 确认并修复，失败分布和质量摘要在 summarize 时固定，渲染不重新读取全局 runs。 |
| 8：损坏 YAML traceback、缺 manifest 绕过验证 | 确认并复现，CLI 返回错误；冻结表携带 package_manifest，缺完整包时拒绝提交。 |

补充复核的输入见 [followup.md](followup.md)。第一次补充返回了无效 DSML 工具调用文本，见 [deepseek-followup.md](deepseek-followup.md)；工具已禁用，这不是实际执行证据，也不作为通过结论。随后以明确只读 system prompt 重试，输出另存 [deepseek-followup-retry.md](deepseek-followup-retry.md)。本地复现与测试才是实现验收依据。

补充复核没有报告新 P1，提出的三项 P2 均继续做了失败复现并修复：

1. **部分身份参数不能被误认作换版。** `record_run` 用 None 表示“未提供”，同版本继承已有字段；显式空值与真实新版本仍按完整身份处理。API 回读验证同版本累计次数与原教师分保留。
2. **同 run 恢复后需要更新表现。** build_records 保存每次运行贡献，重放相同观测不变，更正观测时扣除旧贡献、加入新贡献，runs 不增加；较旧版本的更正写回历史统计，不覆盖当前版本。API 验证 BLOCKED→SUCCEEDED 后 success_rate/schema_repair_rate 更新。
3. **历史 review 不能依赖最新 accepted 指针。** trace 从受评运行的 review 修订读取，后续运行接受另一份 review 不会使旧记录消失。历史 API 回读验证保留原评价者。

最终这三项由本地回归验证；未将 DeepSeek 的静态意见冒称为对最终代码的执行验收。

## 验证证据

- 按 diagnosing-bugs 与 TDD 技能推进；用户事先确认的边界为评价 API/CLI、课程材料包导出、评价报告读取。新行为均通过这些边界观察，缺陷先复现失败再修复。
- 全套：`python -B -m pytest tests -vv -p no:cacheprovider -o faulthandler_timeout=60` → **520 passed / 524.91s**。这是补充复审修复前的全套结果。
- 最终全部补充修复后的相关回归：`python -B -m pytest tests/test_evaluation_integrity.py tests/test_benchmark_evaluation.py tests/test_benchmark_scaffold.py tests/test_benchmark_scenarios.py tests/test_m6_acceptance.py tests/test_store.py -q -p no:cacheprovider` → **100 passed / 57.01s**，见 [最终日志](tests-final.log)。与全套结果有重叠，不是 620 个独立测试。此前一轮 97 项通过的日志也保留。
- Python 编译、`git diff --check`、页面内 JavaScript 的 `node --check` 通过。没有声称真实浏览器交互验收或真人课堂效果验证。
- 测试中发现并清理了本次造成的少量模拟注册表项及一个临时 Direct 导入项目；新评价测试统一隔离临时注册表和项目目录。真实 performance.json 已与原内容核对一致。

运行日志与最终源文件哈希随本目录保存。没有提交 Git commit、发布或改变正式导出要求。

## 真人接续与剩余验收

按 [教师评价工作流](../../evaluation-workflow.md) 导出冻结包、让真实教师独立填写、提交并核对绑定状态。至少三门真实生产课程评价以及完整 A–G × 三模式真实基准仍待完成。AI 一致意见不能替代这些验收，也不能将不支持的 claim 改为 SUPPORTED。
