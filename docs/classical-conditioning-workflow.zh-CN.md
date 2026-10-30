# 经典条件作用单元操作说明

当前内容包为0.7.0：四个概念、八条待验证误解、四道诊断及四道复测，另有五项核心术语定义及四语言完整名称；反射性假设、泛化测试刺激未配对条件与观察边界已补齐。使用固定官方历史版本的CC BY 4.0教材正文。来源定位LOCATED_ONLY不表示真人课堂审核。此前的0.5.0教师接续包保留历史内容。

最新冻结课程见0.7.0教师审核包：20分钟、1546字讲稿、四道主评价及对应新情境复测、师生材料和四张静态图。完整补救与复测按错误在课后/下一次课进行，另计每个分支约3—5分钟；不计入20分钟。

课程采用有支架的形成性练习。当前使用审核包内reviewed-delivery-v3的一体式打印题或学习单，两者均含观察表；教师先阅读包内教学说明及v3的版本约定。v3是发放修订，不冒称系统新正式产物。历史0.5.0/0.6.0课程另行保留，不就地更新。负荷审阅绑定讲稿修订及哈希，讲稿改变后需从load_review重跑，旧审阅不能作为当前结论。

启动 `python -m pebs.cli serve --port 8710` 后，可在 `http://127.0.0.1:8710/docs` 使用以下接口。示例 project_id 为 `classical_course`，所有 revision_id 和哈希都应复制实际响应，不能填写示例值。

## 1. 创建项目并保存学科快照

1. `POST /api/projects`，请求 `{"project_id":"classical_course"}`。
2. `POST /api/projects/classical_course/psychology/units/classical-conditioning`。
3. 保存响应的 artifact_id、revision_id、content_hash。相同内容重复导入复用快照；新内容产生新修订。新快照包含来源正文及元数据。

## 2. 运行课程构建

CLI 请求中追加 `学科修订=<实际 revision_id>`，使用同一个项目；`--planner static` 与 `--planner dynamic` 均支持。示例：

```bash
python -m pebs.cli build --project classical_course --planner dynamic --max-model-calls 20 --max-research 8 --max-seconds 900 --request "Create one introductory lesson on classical conditioning. Include fictional cases, diagnostics, remediation and retests. No PPT. No animation. 学科修订=<实际 revision_id>"
```

需要已配置且可用的生成和研究服务。失败、超预算或未通过证据核验时保留实际状态。实际示例最终运行run_dff2e1330425已完成并接受；复现请求、增量重跑及审计记录保存在审核包和审计目录。不要在另一个进程新建Engine来观察活动运行，初始化包含恢复写入逻辑；使用运行本身的CLI输出或原服务进程。

## 3. 查看及下载冻结材料

- `GET /api/projects/classical_course/psychology/units/classical-conditioning/materials?revision_id=<实际修订>&audience=student`。
- 同路径将 audience 改为 teacher 可读取概念、解析、补救及审核记录。
- 将路径尾部 materials 改为 export 下载 Markdown。文件含修订及哈希；mode=formal 被拒绝，正式交付使用原项目正式导出及当前适用门禁。

学科材料与构建生成的整课产物是不同记录：学科材料是固定课程输入及练习包，整课教案、脚本、证据与评价仍从现有项目产物和评价入口读取。

## 4. 按版本答题并获得补救

从学生材料读取 assessment_id 与 option_details.option_id，提交：

`POST /api/projects/classical_course/psychology/units/classical-conditioning/diagnose`

```json
{"revision_id":"<实际修订>","assessment_id":"extinction-diagnostic","option_id":"extinction-diagnostic-b"}
```

错误回答返回补救、复测目标和不含评分说明的复测题，状态为 needs_followup。一个回答不能认定学生存在稳定误解。此接口不收集学生身份、不建立学生档案。

## 5. 提交与审核教师反馈

向同一单元的 `/feedback` POST：revision_id、content_hash、reviewer、role=teacher、comment、category、basis。category 沿用现有评价修改类别，例如 assessment correction、case replacement、fact correction。

响应返回反馈 artifact_id 与 revision_id。向 `/feedback/decide` POST：feedback_id、expected_revision_id、decision、reviewer、basis；decision 为 ACCEPTED、REJECTED 或 MORE_EVIDENCE。过期修订被拒绝。

MORE_EVIDENCE 后先向 `/feedback/supplement` POST feedback_id、expected_revision_id、reviewer、basis，形成新的待审核修订，再使用新 revision_id 审核。旧提交、旧审核和补充记录保留。采纳仅表示接受这条反馈，不发布全局规则，也不批准事实或正式输出。

## 6. 真人内容审核与原有评分路径

向 `/review` POST revision_id、content_hash、reviewer、role=teacher、decision、basis；decision 为 APPROVED 或 CHANGES_REQUIRED。教师材料及下载文件显示该修订的审核结果。该标签不提供身份认证，部署与使用方应核实提交者身份。

整课真人评分、Teacher Edit Ratio、版本冻结材料包和正式签署继续使用 [评价流程](evaluation-workflow.md)。内容审核不替代它们。没有真人教师时保持 PENDING，不让模型填入真人记录。

## 7. 开发验证

规则候选接续：对已采纳反馈向 `/rules` POST feedback_id、feedback_revision_id、concept_refs、recommendation、reviewer、basis；结果为 DRAFT。建议文本先通过隐私扫描。

向 `/rules/verify` POST rule_id、expected_revision_id、reviewer、role=teacher、basis，以及至少包含 positive 和 counterexample 的 cases；每项填写 text、passed 和 rationale。这是人工案例核对记录，不是系统自动验证了教学效果。任一项失败会形成 VERIFICATION_FAILED。

验证通过后向 `/rules/decide` POST rule_id、expected_revision_id、decision=PUBLISHED、reviewer、basis。撤回使用最新修订与 decision=WITHDRAWN。`GET /rules?revision_id=<学科修订>` 查看当前可用规则。

规则限于本项目、匹配学科内容哈希。构建将所选规则及版本冻结到 materials.psychology_rules，纳入预算和依赖；撤回不修改历史材料。跨内容版本需重新审核适用性。发布教学建议不提升任何陈述支持状态。

```bash
python -m pytest tests/test_psychology_unit.py tests/test_evaluation_integrity.py -q
python -m compileall -q pebs
```

交叉审计原始结果及整改记录见审计目录。当前代码全量623项测试通过；人工审核、真实课堂效果及另外两个单元分别跟踪，不由软件测试替代。pi只是本次使用的第二模型入口，核心教学和教师审核不依赖pi或固定模型。
