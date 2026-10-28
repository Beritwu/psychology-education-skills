## 核心结论与覆盖边界

三份材料教学骨架可用，但不能据此认证或放行。A 最完整，C 最系统但明显超载，B 结构清楚而包内证据不足以评语言与评价设计。历史 run 均 `succeeded`，仅表示执行完成；A/C 的 G3/G5 FAIL、C 的 G2 FAIL、B 的 G8 NEEDS_REVIEW 是**待复核历史证据**，不等于当前代码缺陷。当前代码片段只证明存在某些分支，未见运行结果，不能把注释当已修复行为。

边界：仅有文本导出，无源文献快照、真实课堂、渲染图；PII 替换使局部语句不可复原，B 的 PPT QA 为自报且包内无缩略图，不能算视觉通过。材料包未列出的脚本/评价，不等于项目没有。AI 审计不填教师分、不把 Claim 变 SUPPORTED、不放行导出，也不替代 M6 Acceptance 5。

## 具体发现

**F1 P1｜已证实缺陷｜A-dynamic/course.md L3；RUN BINDINGS A**  
引文：`run: run_77e357790d91 status=succeeded`；worksheet 却是 `run_1ae60eced739`。触发：教师提交包内 A 评分表。影响：评分可能绑错 run。建议：kit/worksheet 共用唯一 run_id 并断言一致。置信：高。

**F2 P1｜已证实缺陷｜evaluation.py L125-132；report.py L243-245**  
引文：`artifact_id="human_eval"`；空 `run_id` 仍被视为 bound。触发：同项目多 run，或提交未传 run_id。影响：旧分被覆盖、跨 run 污染。建议：改为 `human_eval:{run_id}`，run_id 必填并校验 project-run 一致。置信：高。

**F3 P1｜已证实缺陷｜evaluation.py L121-123；report.py L243-246**  
引文：仅存 `"run_id": run_id`，无 artifact revision/hash；仅 run_id 不同才 stale。触发：同一 run 重新 accept 产物。影响：旧评分被当现行。建议：manifest 绑定 artifact_id/revision_id/sha256，任一变更标 stale。置信：高。

**F4 P1｜已证实缺陷｜evaluation.py L149-156**  
引文：`for item in store.list_artifacts():`、`revisions[-1]`。触发：项目存在多轮或多 run 的 gate_result。影响：把旧门禁/他 run 门禁当本课；B 的 G8“未生成缩略图”与 pptx_deck“真实渲染 PASS，7 张缩略图”冲突即例。建议：按 run manifest 与 gate revision 过滤，未绑定显式标 UNBOUND。置信：高。

**F5 P1｜已证实包装缺陷；SUPPORTED 语义待验证｜C-dynamic/course.md L6、L18；C script:sec3 L900**  
引文：`证据政策：['SUPPORTED']`；`clm_949ec8536b@v3（状态 QUALIFY_REQUIRED）`。触发：读者只看头信息。影响：把“策略”误读为 Claim 已支持，掩盖待核验与 G2 FAIL。建议：分列 execution/gate/claim/export；claim 表列来源、适用条件、状态、快照；未决即 fail closed。置信：中高。

**F6 P2｜已证实缺陷｜evaluation.py L135-142**  
引文：`except Exception:  # noqa: BLE001` / `pass`。触发：trace 或 performance 更新失败。影响：评分已落库但未绑 skill 版本，§40 静默失效。建议：写 binding_result 或显式失败，报告标 UNBOUND。置信：高。

**F7 P2｜已证实缺陷｜evaluation.py L48-52；README L20**  
引文：`if not isinstance(scores, dict) or not scores:`，未要求 14 维；脚本 `spoken_naturalness` 未强制。触发：只提交少数维度。影响：均值不可比、可规避低分维度。建议：14 维必填，脚本加口语维度，固定聚合与缺失处理。置信：高。

**F8 P2｜已证实内容缺陷｜A script:sec1 L433-439；C script:sec3 L904-910**  
引文：`"count": 1975` / `"max": 1800`；`"count": 2710` / `"max": 2100`。触发：按现稿授课。影响：超时、教师被迫大删；C sec1 环节合计 100 分钟，若按单次 90 分钟设计则不可执行（时长推断）。建议：拆分或压缩并重算，设每节硬预算。置信：高（字数）/中（时长）。

## A/B/C 审阅

**A**：可保留四目标、五要素记录、事实/推测分栏、渐隐练习与出口任务，sec1 评价与 g1/g4 有一定对应。优先修订：SAFETY 把教学反例“这个孩子就是”判为禁用表达，应支持引用/反例语境或人工复核；处理 G3/G5 FAIL 或说明豁免；1975 字压到 1800 内；sec2/3 评价包内未见，需回原项目核验。真人须判断：观察记录相关主张的来源与准确性、反例用语对幼儿教师的适宜性、45 分钟可执行性。

**B**：可保留 90 分钟时间块、边界—证据四问—案例辨析—离场卡主线，适合大一课。优先修订：包内仅见 lesson_plan/sec1、slide_plan、pptx_deck，未见脚本、评价、案例，不能评语言自然度与评价设计；G8 与 pptx_deck 冲突按 F4 查绑定；`media_need=DIAGRAM，期望 STATIC` 需解释；7 页/90 分钟与备注仅 31–44 字是否足够。真人须判断：视觉可读性、互动密度、心理学说法的证据与适用边界。

**C**：可保留四节“价值—承诺—流程—职责—检查—复盘”链条、案例和待核验标记，系统性最强。优先修订：sec1/2/3 字数 2361/2157/2710 均超 2100，sec1 环节合计 100 分钟；G2 因 placeholder 与 `clm_949ec8536b@v3` QUALIFY_REQUIRED 未闭环；G3/G5 全 FAIL；assessment 仅 sec1，sec2–4 对齐待核验；大量 `[REDACTED]` 影响语句判断。真人须判断：婴幼儿照护规范的地方性/法规依据、案例敏感性与年龄适宜性、100+ 分钟是否可教、是否过度合规化。

## 最小 AI 交叉审计流程

①冻结包：记录 run_id、project_id、artifact_id/revision_id/sha256、gate_id/target/revision、claim_id/status/source；缺源即标 UNVERIFIED。②AI 只出 finding，存 `ai_audit`，禁写 `human_eval`，禁改 claim 状态或导出决定。③机械校验：kit=worksheet run、14+1 维完整、gate 与 manifest 一致、无 QUALIFY_REQUIRED，失败即 fail closed。④第二名 AI 独立复现，只裁决可复现差异，不以共识代替证据。⑤真人教师独立评分并签身份/独立性声明，绑定冻结 manifest；AI 报告仅供参考。⑥放行需 claim/gate/导出检查加真人评分；M6 Acceptance 5 仍只认真实教师 3 个项目。

可复现检查点：A 的 kit run_id 是否等于 worksheet run_id；同项目第二次评分后旧评分是否仍可读；同 run 重新 accept 后是否标 stale；B 的 G8 与缩略图是否同一 revision；C 的 `SUPPORTED` 与 G2/claim 状态是否同屏冲突；仅交 3 个维度是否被接受；A/C 字数与分钟数复算。
