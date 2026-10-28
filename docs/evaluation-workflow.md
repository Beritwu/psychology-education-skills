# AI 交叉审计与真人教师评价

适用日期：2026-10-28。AI 交叉审计已实际运行；真人教师评价仍为 **PENDING**。两者分开保存、分开计数。两个模型达成一致不能替代课堂判断、证据定位、教师签署或正式导出门禁。

## AI 交叉审计

本次入口为 Git Bash → `pi 1.4.0` → `opencode-go/deepseek-v4.1-flash`。原始审计、交叉质疑和裁决见 [首轮审计](audits/2026-10-28-cross-audit/README.md)；修复后的复审和验证见 [实现复审](audits/2026-10-28-implementation-review/README.md)。

**跨电脑使用不依赖 pi。** pi、Git Bash、DeepSeek 和本机路径只是本次审计的调用记录，不是技能运行、评分提交或正式导出门禁的必备条件。可由操作者使用其他 CLI/API 或模型界面完成同一审计流程，保留相同输入和完整审计记录。目前这是工具无关的文档流程，尚未实现自动选择、切换审计后端的适配器。没有第二审阅模型时，该次交叉审计如实记为未完成；其他满足自身依赖的技能可继续运行。

迁移时仍需在新电脑准备 Python 依赖、技能资源和课程生成模型服务。课程生成支持配置中的 `codex_exec` 或 `openai_compatible`；本机默认配置为前者。`skills/` 与 `patches/` 是 gitignored 运行资源，仅克隆 Git 仓库不会带走它们，需要在新机重新导入或正确迁移并验证路径。与 pi 无关的证据、渲染和人工签署要求保持有效。

AI 报告保存在 `docs/audits/`，不提交到 `/evaluation`，不计入 Human Score、Teacher Edit Ratio 或技能晋级。人工提交入口拒绝 `role != teacher` 或 `evaluation_kind != human`；这些来源标签是数据约束，**不是教师身份认证**。提交者仍需核实真实教师身份和评价来源。

复用流程：固定同一份证据 → 扫描并脱敏 → 两模型分别审阅 → 交换发现并质疑 → 本地复现 → 保留确认、撤回和未决结论。调用时禁用工具及自动上下文，仅发送明确选定的文件：

```bash
pi --provider opencode-go --model deepseek-v4.1-flash \
  --no-tools --no-extensions --no-mcp --no-skills \
  --no-prompt-templates --no-context-files --no-session \
  -p @prompt.md @packet.md > deepseek-review.md
```

每轮使用新目录，保留模型、输入哈希、提示词、原始输出与裁决。认证交给 pi；不要读取密钥文件或把密钥复制进材料包。

## 真人教师接续

1. 选定已成功完成且产物版本明确的课程。优先使用真实生产课程；合成 fixture 不计为三门真实课程验收。
2. 执行 `python -m pebs.cli benchmark --export-eval-kit`。新材料包路径为 `benchmarks/reports/evaluation_kit/<case>-<variant>/<run_id>-<target_hash>/`。每包包含完整文本、同版本门禁、运行摘要、版本清单和空白评分表。Direct 基线会将已有原文导入 Store，标为 `evaluation_import`，不调用模型、不伪造生成记录。
3. 教师阅读同一目录内的 `course.md`，填写 `*-human_eval.yaml`。保留 `target` 和 `run`。必须填写 reviewer、comment 和全部 14 个核心维度（1–5 分）；含脚本产物时另填 `spoken_naturalness`。非脚本可留空；口语分独立于 14 维核心均分。
4. 如有实际修改，填写修改前后文本与类别/严重度。未发生人工修改时不要填 AI 估计的修改比例。PPT 授课评价还应核对原项目中的可编辑文件和渲染图；文献核验应打开可定位的原始来源快照。文本包不能证明这些材料已通过人工检查。
5. 提交同一个冻结包的评分表：

```powershell
python -m pebs.cli benchmark --submit-eval "<完整评分表路径>" --project "<匹配的project_id>"
```

6. 核对返回的 `run_id`、`evaluation_id` 与 `binding.status`。`BOUND` 表示技能身份关联已完成；`FAILED` 表示评分已保存但关联未完成，CLI 返回非零。排除故障后原样重试；重复提交不增加构建次数。旧运行缺少生成时的技能身份快照时，不会用当前版本冒充旧版本。应保留旧评分，并重新生成有完整身份记录的课程后再评。
7. 执行 `python -m pebs.cli benchmark --report` 更新报告。报告只读取项目库中的对应运行评价，忽略 `run.json` 内嵌的任意评分。受评版本变化后，旧评分显示过期，不参与当前分数汇总。

材料包不可就地更新：已有包的课程或摘要哈希变化会被拒绝；新运行进入新目录；已填评分表保留。修改课程应通过项目生成新 revision，再导出新包。旧版平铺工作表没有 `target`，不能直接提交；请用新冻结包重新核对和填写。

## API 与历史读取

`GET /api/projects/<project_id>/evaluation` 返回当前运行和 `evaluation_target`。指定 `?run_id=<受评运行>` 可读取历史运行；提交 `POST /api/projects/<project_id>/evaluation` 时携带所阅读材料的 `target`、`run_id` 和 `mode`。项目/运行不匹配、缺少 target、版本过期、评分不完整均被拒绝。

教师评价保存为不可变的 `human_eval:<run_id>` 修订。AI 审计仍是独立文档。历史评价和旧技能统计保留；新技能版本不会继承旧版本的教师分数。

## 仍待真人完成的验收

至少三门真实生产课程的教师评价、真实修改记录与课堂适用性判断仍未完成。完整 A–G × 三模式真实模型基准也受配额与运行证据约束。本轮工程修复和 AI 审计不会改变 M6 的这两项状态，也不会绕过 G1–G8、fixture 隔离、证据核验或教师签署要求。
