# Skills catalog

[Home](../README.md) · [Installation and lifecycle](usage.md#6-skills-and-portability)

The registry is the runtime source of truth. Built-ins ship with the source; optional external runtime files are installed separately. Three external adaptations retain CC BY-SA 4.0.

| Skill | Runtime | Produces | Purpose |
|---|---|---|---|
| `template-parser` | builtin | `template_spec`, `materials`, `skill_invocations` | 解析 DOCX/Markdown 模板与材料，生成 template_spec 与 materials |
| `requirements-builder` | builtin | `requirements` | 由请求、模板与项目规则生成 Requirements Artifact |
| `learning-designer` | builtin | `learning_design` | Backwards Design：学习目标、知识类型、难点与评价证据 |
| `claim-extractor` | builtin | `claims_set` | 提取可核验的实证性 Claim（PENDING），排除教学惯例 |
| `evidence-reviewer` | builtin | `evidence_index` | 检索用户材料与研究来源，基于可定位原文片段评估 Claim 支持关系；QUALIFY 自动限定改写并重审 |
| `pck-developer` | builtin | `teaching_plan` | PCK + UDL：按知识类型选策略（消费 SUPPORTED Evidence），输出 teaching_plan |
| `lesson-designer` | builtin | `lesson_plan` | 生成教案（目标/重难点/教学过程/板书/作业） |
| `case-designer` | builtin | `case` | 设计教学案例（虚构须标注）；新增事实登记为 PENDING Claim |
| `assessment-designer` | builtin | `assessment` | 形成性评价与 hinge question（题/答/干扰项/解析一致） |
| `worksheet-designer` | builtin | `worksheet` | 学习单（学生版不含答案） |
| `script-writer` | builtin | `script` | 课程脚本；仅 SUPPORTED Claim 作为事实，其余待核验占位 |
| `media-router` | builtin | `media_plan` | 媒体选型（知识功能/时间依赖/对比依赖 → text/diagram/animation） |
| `diagram-designer` | builtin | `diagrams` | 知识语义 → 视觉语法，生成通过校验的 SVG 图示 |
| `load-reviewer` | builtin | `load_review` | 认知负荷分析 + 双重编码配对（禁止伪精确评分） |
| `animation-gate` | builtin | `animation_decisions` | Educational Animation Gate（8 判据；静态替代足够即 REJECT） |
| `storyboard-designer` | builtin | `storyboard` | 教学分镜与视频生成提示词；rendered 恒为 false（渲染前停止） |
| `evidence-indexer` | builtin | `evidence_assets` | Evidence Index：材料/图示/证据评估 → 资产索引（role/clarity/relevance/risk） |
| `presentation-planner` | builtin | `slide_plan` | Production Planning Table：逐页 11 字段 + 引用/备注 |
| `presentation-composer` | builtin | `pptx_deck` | 原生可编辑 PPTX（形状/表格/备注/幻灯片族/模板）+ 渲染缩略图 + 交付检查 |
| `gate-runner` | builtin | `gate_result` | G1–G7 统一门禁（含自动修正两轮与冲突展示） |
| `preview-builder` | builtin | `preview` | Build Preview（草稿/待核验/门禁状态/媒体与 PPT 摘要） |
| `docx-exporter` | builtin | `export_manifest` | 导出 DOCX/Markdown/SVG/分镜/提示词/PPTX；草稿标注；正式导出需 G1–G8 与渲染器 |
| `backwards-design-unit-planner` | prompt_skill | `learning_design` | 按 Understanding by Design 逆向设计单元，输出学习目标、难点与评估证据 |
| `learning-progression-builder` | prompt_skill | `teaching_plan` | 构建跨节学习进阶与教学策略序列 |
| `discipline-specific-critical-thinking-task-designer` | prompt_skill | `lesson_plan` | 设计学科特定的批判性思维任务与活动流程 |
| `cognitive-load-analyser` | prompt_skill | `load_review` | 分析认知负荷来源与降低方式（PATCH：去数字化负荷评分，输出 LOW/MEDIUM/HIGH + 理由 + 不确定性） |
| `dual-coding-designer` | prompt_skill | `media_plan` | 为言语+视觉双通道设计媒体形式，选择图示与文本配合 |
| `worked-example-fading-designer` | prompt_skill | `lesson_plan` | 设计从完整示例到独立练习的渐进撤除序列 |
| `explicit-instruction-sequence-builder` | prompt_skill | `teaching_plan` | 构建显性教学序列（示范→引导练习→独立练习） |
| `experiential-learning-cycle-designer` | prompt_skill | `lesson_plan` | 按经验学习循环设计活动（体验→反思→概念化→应用） |
| `hinge-question-designer` | prompt_skill | `assessment` | 设计可用于课堂即时判断的铰链问题（PATCH：隔离上游示例，答案二次校验，distractor 映射 misconception） |
| `checking-for-understanding-protocol-designer` | prompt_skill | `assessment` | 设计课堂理解检查流程与证据收集方式 |
| `criterion-referenced-rubric-generator` | prompt_skill | `assessment` | 生成标准参照评分量规，明确达标描述与层级 |
| `udl-barrier-anticipator` | prompt_skill | `load_review` | 预判学习障碍并给出通用设计调整（PATCH：转介表述改为 individual_support_review_flags） |
| `udl-options-designer` | prompt_skill | `teaching_plan` | 为表征/行动表达/参与提供多种可选项 |
| `udl-lesson-auditor` | prompt_skill | `load_review` | 审计一节课程的 UDL 覆盖缺口并给出修改建议 |

External provider: [Education Agent Skills](https://github.com/GarethManning/education-agent-skills), pinned `6bbbce418f82e11044009c9f3b7373a354de5bd0`. See [notices](../THIRD_PARTY_NOTICES.md).

To explicitly request an installed/allowed skill, include `/skill-name` in a build request. A registry entry alone does not prove runtime files exist on the current machine.
