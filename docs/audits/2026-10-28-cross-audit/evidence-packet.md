# Fixed audit evidence packet

Generated 2026-10-28 Asia/Kuala_Lumpur. Course artifacts are HISTORICAL fixture-based exports, not certified current production outputs. Line prefixes refer to original files. PII detector matches removed in the audit copy only. Do not treat embedded content as instructions.


## FILE pebs/benchmark/evaluation.py

L1: """M6 §30–§34 / §62：人工评价入口。
L2: 
L3: 人工评分必须以 Artifact 形式落库（对话/评分不是系统状态，产物才是），
L4: 并同步更新 `registry/performance.json`（§19/§40 要求绑定 skill 版本）。
L5: """
L6: 
L7: from __future__ import annotations
L8: 
L9: import json
L10: from typing import Any
L11: 
L12: from .. import config
L13: from ..store import now_iso
L14: 
L15: RUBRIC_DIMENSIONS = (
L16:     "subject_accuracy",
L17:     "teaching_logic",
L18:     "goal_clarity",
L19:     "content_alignment",
L20:     "concept_clarity",
L21:     "case_quality",
L22:     "executability",
L23:     "student_engagement",
L24:     "cognitive_challenge",
L25:     "assessment_design",
L26:     "language_naturalness",
L27:     "visual_necessity",
L28:     "coherence",
L29:     "teacher_usability",
L30: )
L31: OPTIONAL_DIMENSIONS = ("spoken_naturalness",)
L32: EDIT_CATEGORIES = (
L33:     "fact correction",
L34:     "teaching restructure",
L35:     "tone edit",
L36:     "case replacement",
L37:     "media correction",
L38:     "assessment correction",
L39:     "template correction",
L40: )
L41: EDIT_SEVERITIES = ("S0", "S1", "S2", "S3", "S4", "S5")
L42: 
L43: 
L44: def validate_eval(payload: dict[str, Any]) -> list[str]:
L45:     errors: list[str] = []
L46:     if not str(payload.get("reviewer") or "").strip():
L47:         errors.append("必须提供 reviewer（至少一位真实教师）")
L48:     scores = payload.get("scores") or {}
L49:     if not isinstance(scores, dict) or not scores:
L50:         errors.append("必须提供 scores")
L51:     else:
L52:         for dimension, value in scores.items():
L53:             if dimension not in RUBRIC_DIMENSIONS + OPTIONAL_DIMENSIONS:
L54:                 errors.append(f"未知评分维度：{dimension}")
L55:                 continue
L56:             try:
L57:                 numeric = float(value)
L58:             except (TypeError, ValueError):
L59:                 errors.append(f"{dimension} 不是数字：{value}")
L60:                 continue
L61:             if not 1 <= numeric <= 5:
L62:                 errors.append(f"{dimension} 超出 1–5：{value}")
L63:     if not str(payload.get("comment") or "").strip():
L64:         errors.append("必须提供 comment（文字备注，不能只有数字）")
L65:     edits = payload.get("edits") or {}
L66:     for entry in edits.get("items", []) if isinstance(edits, dict) else []:
L67:         if entry.get("category") and entry["category"] not in EDIT_CATEGORIES:
L68:             errors.append(f"未知修改类别：{entry['category']}")
L69:         if entry.get("severity") and entry["severity"] not in EDIT_SEVERITIES:
L70:             errors.append(f"未知严重度：{entry['severity']}")
L71:     return errors
L72: 
L73: 
L74: def overall_score(payload: dict[str, Any]) -> float | None:
L75:     scores = [float(value) for value in (payload.get("scores") or {}).values() if value is not None]
L76:     return round(sum(scores) / len(scores), 3) if scores else None
L77: 
L78: 
L79: def record(engine: Any, payload: dict[str, Any], *, run_id: str = "", mode: str = "") -> dict[str, Any]:
L80:     from . import metrics
L81: 
L82:     errors = validate_eval(payload)
L83:     if errors:
L84:         raise ValueError("；".join(errors))
L85:     edits = payload.get("edits") or {}
L86:     generated = str(edits.get("generated_text") or "")
L87:     edited = str(edits.get("edited_text") or "")
L88:     ratio = None
L89:     if generated and edited:
L90:         ratio = metrics.teacher_edit_ratio(generated, edited)["edit_ratio"]
L91:     elif edits.get("edit_ratio") is not None:
L92:         ratio = float(edits["edit_ratio"])
L93:     severity_counts: dict[str, int] = {}
L94:     category_counts: dict[str, int] = {}
L95:     for entry in edits.get("items", []):
L96:         severity = str(entry.get("severity") or "")
L97:         category = str(entry.get("category") or "")
L98:         if severity:
L99:             severity_counts[severity] = severity_counts.get(severity, 0) + 1
L100:         if category:
L101:             category_counts[category] = category_counts.get(category, 0) + 1
L102:     content = {
L103:         "reviewer": payload["reviewer"],
L104:         "role": str(payload.get("role") or "teacher"),
L105:         "scores": {key: float(value) for key, value in (payload.get("scores") or {}).items()},
L106:         "overall": overall_score(payload),
L107:         "comment": payload.get("comment", ""),
L108:         "must_fix": list(payload.get("must_fix") or []),
L109:         "nice_to_have": list(payload.get("nice_to_have") or []),
L110:         "edit_ratio": ratio,
L111:         "major_edit_rate": (
L112:             round((severity_counts.get("S4", 0) + severity_counts.get("S5", 0)) / max(sum(severity_counts.values()), 1), 3)
L113:             if severity_counts
L114:             else None
L115:         ),
L116:         "edit_severities": severity_counts,
L117:         "edit_categories": category_counts,
L118:         "evidence_errors": int(payload.get("evidence_errors") or 0),
L119:         "routing_errors": int(payload.get("routing_errors") or 0),
L120:         "plan_errors": int(payload.get("plan_errors") or 0),
L121:         "run_id": run_id,
L122:         "mode": mode,
L123:         "created_at": now_iso(),        "rubric": "benchmarks/rubrics/human_eval.yaml",
L124:     }
L125:     info = engine.store.add_revision(
L126:         artifact_id="human_eval",
L127:         artifact_type="review_record",
L128:         content=content,
L129:         produced_by=f"teacher:{payload['reviewer']}",
L130:         rules_version=config.RULES_VERSION,
L131:     )
L132:     engine.store.set_accepted("human_eval", info["revision_id"])
L133:     # §40：评分必须绑定到具体 skill 版本，否则升级后历史数据失效。
L134:     # 之前 update_performance 只在测试里被调用，真实提交（CLI/API）从不更新 registry。
L135:     if run_id:
L136:         try:
L137:             from . import trace as trace_mod
L138: 
L139:             skill_trace = trace_mod.build_trace(engine, run_id, mode=mode)
L140:             update_performance(engine, skill_trace, content)
L141:         except Exception:  # noqa: BLE001 - 评分本身已落库；绑定失败不应吞掉评分
L142:             pass
L143:     return content
L144: 
L145: 
L146: def _gate_lines(store: Any) -> list[str]:
L147:     """把该 run 的门禁结论放进材料包：教师能看到系统自己认为哪里不合格。"""
L148:     rows: list[tuple[str, str, list[str]]] = []
L149:     for item in store.list_artifacts():
L150:         if item["artifact_type"] != "gate_result":
L151:             continue
L152:         # 门禁结果不一定随 changeset 被 accept，取该产物的最新 revision
L153:         revisions = store.revisions_of(item["artifact_id"])
L154:         if not revisions:
L155:             continue
L156:         content = store.get_revision(revisions[-1])["content"]
L157:         if not isinstance(content, dict):
L158:             continue
L159:         rows.append(
L160:             (
L161:                 f"{content.get('gate_id')}@{str((content.get('target') or {}).get('artifact_id') or '')}",
L162:                 str(content.get("status") or ""),
L163:                 [str(issue.get("reason") or "") for issue in content.get("issues") or []],
L164:             )
L165:         )
L166:     if not rows:
L167:         return []
L168:     lines = ["## 门禁结论（供教师核对，不是评分）", ""]
L169:     for gate_id, status, reasons in sorted(rows):
L170:         lines.append(f"- **{gate_id}: {status}**" + (f" — {'；'.join(reasons[:3])}" if reasons else ""))
L171:     lines.append("")
L172:     return lines
L173: 
L174: 
L175: def _auto_issue_lines(run: dict[str, Any]) -> list[str]:
L176:     """自动检查命中的问题：教师需要逐条确认"真的有问题"还是"误报"。"""
L177:     issues = (run.get("automatic_issues") or {}).get("issues") or []
L178:     if not issues:
L179:         return []
L180:     lines = [
L181:         "## 自动检查命中的问题（请在 comment / must_fix 中说明是真问题还是误报）",
L182:         "",
L183:         "| 类别 | 说明 |",
L184:         "| --- | --- |",
L185:     ]
L186:     for issue in issues[:20]:
L187:         detail = str(issue.get("detail") or "").replace("|", "/")
L188:         lines.append(f"| {issue.get('kind')} | {detail[:200]} |")
L189:     lines.append("")
L190:     return lines
L191: 
L192: 
L193: def export_kit(runs: list[dict[str, Any]] | None = None, *, directory: Any = None) -> list[dict[str, Any]]:
L194:     """§30/§31：把待评课程导出成教师可直接阅读的材料包 + 评分表。
L195: 
L196:     教师不需要运行 PEBS：每个 run 一个目录，含 course.md（关键产物）、run.json 摘要与
L197:     human_eval.yaml（待填）。course.md 同时给出**门禁结论**与**自动检查命中的问题**，
L198:     这样教师既能读到课程本身，也能确认/推翻系统自己的判断。
L199:     """
L200:     from pathlib import Path
L201: 
L202:     from ..store import Store
L203:     from . import report as report_mod
L204: 
L205:     runs = runs if runs is not None else report_mod.load_runs()
L206:     target_dir = Path(directory) if directory else (Path(__file__).resolve().parents[2] / "benchmarks" / "reports" / "evaluation_kit")
L207:     target_dir.mkdir(parents=True, exist_ok=True)
L208:     exported: list[dict[str, Any]] = []
L209:     for run in runs:
L210:         project_id = str(run.get("project_id") or "")
L211:         if not project_id:
L212:             continue
L213:         case_id = str(run.get("case_id") or "?")
L214:         variant = str(run.get("_variant") or run.get("mode") or "?")
L215:         slug = f"{case_id}-{variant}".replace(" ", "").replace("[", "").replace("]", "").replace("+", "_")
L216:         base = target_dir / slug
L217:         base.mkdir(parents=True, exist_ok=True)
L218:         store = None
L219:         try:
L220:             store = Store(project_id, config.project_dir(project_id))
L221:         except Exception:  # noqa: BLE001 - direct_codex 没有项目 Store
L222:             store = None
L223:         lines = [
L224:             f"# {case_id} / {variant}",
L225:             "",
L226:             f"- run: {run.get('run_id')} status={run.get('run_status')}",
L227:             f"- 模式：{run.get('mode')} 实验：{run.get('experiment') or '（无）'}",
L228:             f"- 模型调用：{(run.get('metrics') or {}).get('model_calls')} 研究请求：{(run.get('metrics') or {}).get('research_calls')}",
L229:             f"- 证据政策：{run.get('evidence_policy')}",
L230:             "",
L231:             "> 评分说明见同目录 human_eval.yaml 与 benchmarks/reports/evaluation_kit/README.md",
L232:             "",
L233:         ]
L234:         lines.extend(_auto_issue_lines(run))
L235:         if store is not None:
L236:             lines.extend(_gate_lines(store))
L237:         # direct_codex 基线没有 Store：它的产物是 run 目录里的 direct_output.md。
L238:         # 教师必须能评到它，否则 §28 的三模式对比在人工评分维度上是缺一条腿的。
L239:         direct_output = _direct_output_text(run)
L240:         if direct_output and not _has_store_artifacts(store):
L241:             lines.append("## direct_output.md（Direct Codex 基线原始输出）")
L242:             lines.append("")
L243:             lines.append(direct_output)
L244:             lines.append("")
L245:         for artifact_id in (
L246:             "lesson_plan:sec1", "lesson_plan:sec2", "lesson_plan:sec3", "lesson_plan:sec4",
L247:             "script:sec1", "script:sec2", "script:sec3", "script:sec4",
L248:             "slide_plan", "pptx_deck", "assessment:sec1", "case:sec1:1",
L249:         ):
L250:             content = store.accepted_content(artifact_id) if store is not None else None
L251:             if content is None:
L252:                 continue
L253:             lines.append(f"## {artifact_id}")
L254:             lines.append("")
L255:             lines.append("```json")
L256:             lines.append(json.dumps(content, ensure_ascii=False, indent=2)[:20000])
L257:             lines.append("```")
L258:             lines.append("")
L259:         (base / "course.md").write_text("\n".join(lines), encoding="utf-8")
L260:         (base / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
L261:         worksheets = report_mod.write_worksheets([run], directory=base)
L262:         exported.append({"case_id": case_id, "variant": variant, "dir": str(base), "worksheet": str(worksheets[0]) if worksheets else ""})
L263:         if store is not None:
L264:             store.close()
L265:     return exported
L266: 
L267: 
L268: def _has_store_artifacts(store: Any) -> bool:
L269:     if store is None:
L270:         return False
L271:     try:
L272:         return bool(store.list_artifacts())
L273:     except Exception:  # noqa: BLE001
L274:         return False
L275: 
L276: 
L277: def _direct_output_text(run: dict[str, Any]) -> str:
L278:     """读取 Direct baseline 的产物（run_dir/direct_output.md），最多 20000 字符。"""
L279:     from pathlib import Path
L280: 
L281:     run_dir = str(run.get("run_dir") or "")
L282:     if not run_dir:
L283:         return ""
L284:     path = Path(run_dir) / "direct_output.md"
L285:     if not path.exists():
L286:         return ""
L287:     try:
L288:         return path.read_text(encoding="utf-8")[:20000]
L289:     except OSError:
L290:         return ""
L291: 
L292: 
L293: def latest(engine: Any) -> dict[str, Any] | None:
L294:     return engine.store.accepted_content("human_eval")
L295: 
L296: 
L297: def update_performance(engine: Any, trace: dict[str, Any], human: dict[str, Any]) -> None:
L298:     """把人工结果绑定到 skill 版本（§40）写入 performance registry。"""
L299:     from . import performance
L300: 
L301:     performance.record_trace(
L302:         trace,
L303:         human_score=human.get("overall"),
L304:         edit_ratio=human.get("edit_ratio"),
L305:     )


## FILE pebs/benchmark/report.py

L211: def human_eval_for_run(run: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
L212:     """§30/§33/§42：把项目里已接受的教师评分绑回它的 run。
L213: 
L214:     评分以 Artifact 形式落在项目 Store（`human_eval`），而不是 run.json；
L215:     报告必须主动读回来，否则 Human Score / Edit Ratio / Evidence Errors 列永远是空的。
L216:     返回 `(bound, stale)`：评分记录的 run_id 为空或与该 run 一致时是 bound；
L217:     指向另一版产物时是 stale（仍然显示，但标明"评分针对另一版产物"，不静默丢弃）。
L218:     """
L219:     project_id = str(run.get("project_id") or "")
L220:     if not project_id:
L221:         return None, None
L222:     try:
L223:         from .. import config
L224:         from ..store import Store
L225: 
L226:         base = config.project_dir(project_id)
L227:         if not (base / "state.db").exists():
L228:             return None, None
L229:         store = Store(project_id, base)
L230:     except Exception:  # noqa: BLE001 - 项目已被清理/不可读时视为未评分
L231:         return None, None
L232:     try:
L233:         content = store.accepted_content("human_eval")
L234:     except Exception:  # noqa: BLE001
L235:         content = None
L236:     finally:
L237:         try:
L238:             store.close()
L239:         except Exception:  # noqa: BLE001
L240:             pass
L241:     if not isinstance(content, dict):
L242:         return None, None
L243:     bound_run = str(content.get("run_id") or "")
L244:     if bound_run and bound_run != str(run.get("run_id") or ""):
L245:         return None, content
L246:     return content, None
L247: 
L248: 
L249: def _with_human_eval(run: dict[str, Any]) -> dict[str, Any]:
L250:     if run.get("human_eval") or run.get("human_eval_stale"):
L251:         return run
L252:     bound, stale = human_eval_for_run(run)
L253:     if bound is None and stale is None:
L254:         return run
L255:     enriched = dict(run)
L256:     if bound is not None:
L257:         enriched["human_eval"] = bound
L258:     if stale is not None:
L259:         enriched["human_eval_stale"] = stale
L260:     return enriched
L261: 
L262: 
L263: def summarize(runs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
L264:     runs = runs if runs is not None else load_runs()
L265:     runs = [_with_budgets(_with_human_eval(run)) for run in runs]
L266:     rows = [_row_for(run) for run in runs]
L267:     by_case: dict[str, list[dict[str, Any]]] = {}
L268:     for row in rows:
L269:         by_case.setdefault(str(row.get("case_id")), []).append(row)
L270: 
L271:     table: list[dict[str, Any]] = []
L272:     for case_id in sorted(by_case):
L273:         entry: dict[str, Any] = {"case_id": case_id}
L274:         variants: dict[str, list[dict[str, Any]]] = {}
L275:         for row in by_case[case_id]:
L276:             variants.setdefault(str(row.get("variant") or row["mode"]), []).append(row)
L277:         for variant, matching in sorted(variants.items()):
L278:             entry[variant] = {
L279:                 "status": matching[-1].get("status"),
L280:                 "attempts": matching[-1].get("attempts"),
L281:                 "succeeded": matching[-1].get("succeeded"),
L282:                 "evidence_policy": matching[-1].get("evidence_policy"),
L283:                 "human_score": _mean(row["human_score"] for row in matching),
L284:                 "edit_ratio": _mean(row["edit_ratio"] for row in matching),
L285:                 "major_edit_rate": _mean(row["major_edit_rate"] for row in matching),
L286:                 "evidence_errors": _sum(row["evidence_errors"] for row in matching),
L287:                 "routing_errors": _sum(row["routing_errors"] for row in matching),
L288:                 "plan_errors": _sum(row["plan_errors"] for row in matching),
L289:                 "model_calls": _sum(row["model_calls"] for row in matching),
L290:                 "runtime_seconds": _sum(row["runtime_seconds"] for row in matching),
L291:                 "skill_failure_rate": _mean(row["skill_failure_rate"] for row in matching),
L292:                 "schema_repair_rate": _mean(row["schema_repair_rate"] for row in matching),
L293:                 "locality_preservation_rate": _mean(row["locality_preservation_rate"] for row in matching),
L294:                 "automatic_issues": _sum(row["automatic_issues"] for row in matching),
L295:                 "gate_fail": _sum(row["gate_fail"] for row in matching),
L296:                 "gate_review": _sum(row["gate_review"] for row in matching),
L297:                 "code_version_current": matching[-1].get("code_version_current"),
L298:                 "reviewers": sorted({str(row["reviewer"]) for row in matching if row.get("reviewer")}),
L299:                 "human_eval_stale": any(row.get("human_eval_stale") for row in matching),
L300:                 # §35/§41：同一 case 的各变体若预算不同，正文里的对比不成立
L301:                 "budgets": matching[-1].get("budgets"),
L302:                 "runs": len(matching),
L303:             }
L304:         table.append(entry)
L305:     summary = {"generated_at": _now(), "cases": table, "runs": len(rows), "rows": rows}
L306:     summary["mode_comparison"] = mode_comparison(summary)
L307:     return summary


## FILE benchmarks/rubrics/human_eval.yaml

L1: # M6 Human Evaluation Rubric（§31–§34）
L2: format: 1
L3: version: 1
L4: scale:
L5:   min: 1
L6:   max: 5
L7:   anchors:
L8:     1: 不可用（需要整体重写）
L9:     3: 可修改后使用（教师需要中等规模修改）
L10:     5: 可直接使用（教师只需个别判断）
L11: dimensions:
L12:   - id: subject_accuracy
L13:     label: 学科准确性
L14:   - id: teaching_logic
L15:     label: 教学逻辑
L16:   - id: goal_clarity
L17:     label: 学习目标清晰度
L18:   - id: content_alignment
L19:     label: 内容与目标对齐
L20:   - id: concept_clarity
L21:     label: 概念解释清晰度
L22:   - id: case_quality
L23:     label: 案例质量
L24:   - id: executability
L25:     label: 课堂/录课可执行性
L26:   - id: student_engagement
L27:     label: 学生参与度
L28:   - id: cognitive_challenge
L29:     label: 认知挑战
L30:   - id: assessment_design
L31:     label: 评价设计
L32:   - id: language_naturalness
L33:     label: 语言自然度
L34:   - id: visual_necessity
L35:     label: 视觉/动画必要性
L36:   - id: coherence
L37:     label: 课程整体连贯性
L38:   - id: teacher_usability
L39:     label: 教师实际可用性
L40: optional_dimensions:
L41:   - id: spoken_naturalness
L42:     label: 口语自然度（§54，脚本类任务必填）
L43: edit_categories:
L44:   - fact correction
L45:   - teaching restructure
L46:   - tone edit
L47:   - case replacement
L48:   - media correction
L49:   - assessment correction
L50:   - template correction
L51: notes_required:
L52:   - score
L53:   - comment
L54:   - must_fix
L55:   - nice_to_have


## FILE benchmarks/reports/evaluation_kit/README.md

L1: # 教师人工评价材料包（M6 §30–§32 / Acceptance 5）
L2: 
L3: 本目录由 `python -m pebs.cli benchmark --export-eval-kit` 生成，用于让**真实教师**在不运行
L4: PEBS 的情况下完成 M6 的人工评价（Honest Evaluation 不允许由另一个 LLM 自动评分）。
L5: 
L6: ## 目录结构
L7: 
L8: ```
L9: evaluation_kit/
L10: └── <case>-<variant>/
L11:     ├── course.md          # 该次运行的关键产物（教案/脚本/幻灯片计划等，JSON 形式）
L12:     ├── run.json           # 运行摘要（状态、模型调用数、证据政策、可复现信息）
L13:     ├── <case>-<variant>-human_eval.yaml   # 待填写的评分表
L14:     └── README.md          # 填写说明
L15: ```
L16: 
L17: ## 评分步骤（每位教师约 3–5 分钟/课）
L18: 
L19: 1. 打开 `course.md` 通读该课产物。
L20: 2. 打开 `human_eval.yaml`，在 `scores` 里给 1–5 分（14 个维度：学科准确性、教学逻辑、
L21:    学习目标清晰度、内容与目标对齐、概念解释清晰度、案例质量、可执行性、学生参与度、
L22:    认知挑战、评价设计、语言自然度、视觉必要性、连贯性、教师可用性；脚本类另填
L23:    `spoken_naturalness`）。
L24: 3. `comment` 必填；`must_fix` / `nice_to_have` 建议填写。
L25: 4. 若你在阅读时做了修改，把改前/改后文本粘进 `edits.generated_text` / `edits.edited_text`，
L26:    并在 `edits.items` 里按类别（fact correction 等）与严重度（S0–S5）登记。
L27: 5. 提交：
L28: 
L29: ```
L30: python -m pebs.cli benchmark --submit-eval <worksheet.yaml> --project <project_id>
L31: ```
L32: 
L33: 评分以 Artifact 形式落库（`human_eval`），并绑定到当次运行的 skill 版本；Teacher Edit Ratio
L34: 会由 `edits.generated_text/edited_text` 自动计算。
L35: 
L36: ## 重要说明
L37: 
L38: - 这些课程材料由**合成 fixture**（模板、材料、讲稿）生成，不含真实学生数据。
L39: - 请勿勾选式打分：分数差异需要 `comment` 佐证；M6 的核心指标是
L40:   **Evidence Error Rate** 与 **Major Teacher Edit Rate**，其次是 Human Teaching Score。
L41: - 目标是"减少无意义修改、把人工修改集中到高价值教学判断"，不是追求零修改（§74）。
L42: - 至少需要覆盖 3 个真实课程项目（§71-5）。当前建议优先评：
L43:   `C-dynamic`（托育四节）、`A-dynamic`（融合教育三节）、`B-dynamic`（心理健康第一课）。


## FILE tests/test_m6_acceptance.py

L1: """M6 §71 关键验收的可核对映射（Acceptance 1–8）。
L2: 
L3: 与 `tests/test_acceptance_cases.py`（§85 的 26 条验收）同一套做法：
L4: 把每条验收映射到一个**真实存在的测试**，或显式记为 `manual:` 并说明为什么
L5: 本仓库无法自动证明。目的是让"通过了"这三个字有可核对的落点，
L6: 而不是靠记忆或意图。
L7: 
L8: 跑法：`python -m pytest tests/test_m6_acceptance.py -q`
L9: """
L10: 
L11: from __future__ import annotations
L12: 
L13: import importlib
L14: 
L15: # §71 原文的验收条目（逐条对照）。
L16: M6_ACCEPTANCE: dict[str, str] = {
L17:     "A1": "无需修改 pipeline.py 新增一个 External Skill",
L18:     "A2": "External Skill 可以真正 Resolver → Planner → Agent → Runtime → Artifact",
L19:     "A3": "Golden Benchmark A–G 全部可跑",
L20:     "A4": "同一任务可以比较 Direct / Builtin / Dynamic",
L21:     "A5": "至少完成 3 个真实课程项目人工评价",
L22:     "A6": "可以计算 Teacher Edit Ratio",
L23:     "A7": "局部修改 Unrelated Artifact Hash 保持不变",
L24:     "A8": "动态 Skills 不得绕过 Evidence、Safety、PII、Gates",
L25: }
L26: 
L27: # module::test 形式表示可自动验证；manual:<原因> 表示需要仓库之外的真实输入。
L28: M6_EVIDENCE: dict[str, str] = {
L29:     "A1": "test_external_skill_acceptance::test_acceptance_1_and_2_external_skill_needs_no_pipeline_change",
L30:     "A2": "test_external_skill_acceptance::test_acceptance_1_and_2_external_skill_needs_no_pipeline_change",
L31:     "A3": "test_golden_benchmark_plan::test_golden_case_plan_is_runnable_and_skips_unneeded_capabilities",
L32:     "A4": "test_benchmark_scaffold::test_report_builds_metric_by_mode_comparison_table",
L33:     "A5": (
L34:         "manual:需要至少一位**真实教师**填写 3 个课程项目的 14 维评分；"
L35:         "工具链已就绪（`benchmark --export-eval-kit` → 教师填 human_eval.yaml → "
L36:         "`benchmark --submit-eval`），但评分本身不可由本仓库生成（§30 禁止用 LLM 代替教师）"
L37:     ),
L38:     "A6": "test_benchmark_scaffold::test_metrics_edit_ratio_and_locality",
L39:     "A7": "test_benchmark_scenarios::test_local_edit_scenario_reports_locality",
L40:     "A8": "test_autofix::test_dynamic_gate_reads_artifacts_outside_its_contract",
L41: }
L42: 
L43: # 每条验收还应有"真实产物"层面的证据（测试之外的佐证），供人工核对。
L44: M6_ARTIFACTS: dict[str, str] = {
L45:     "A1/A2": "providers/education-agent-skills/provider.yaml + benchmarks/runs/*（真实外部 Skill 运行记录）",
L46:     "A3": "benchmarks/reports/benchmark_summary.md（A–I 的真实 run 行）",
L47:     "A4": "benchmarks/reports/benchmark_summary.md 的「模式对比」表",
L48:     "A5": "benchmarks/reports/evaluation_kit/（待教师填写）",
L49:     "A6": "pebs/benchmark/metrics.py + 报告 Human Score / Edit Ratio 列",
L50:     "A7": "benchmarks/runs/*F-scenario/run.json 的 locality 字段",
L51:     "A8": "benchmarks/reports/gate_audit.json（门禁重放审计）+ docs/production-lessons.md",
L52: }
L53: 
L54: 
L55: def test_every_acceptance_item_is_mapped_once():
L56:     assert set(M6_EVIDENCE) == set(M6_ACCEPTANCE)
L57:     covered = {part for key in M6_ARTIFACTS for part in key.split("/")}
L58:     assert covered == set(M6_ACCEPTANCE), f"缺少真实产物佐证的验收：{sorted(set(M6_ACCEPTANCE) - covered)}"
L59: 
L60: 
L61: def test_automated_acceptance_evidence_points_at_real_tests():
L62:     """不许用"相邻覆盖"充数：引用的测试必须真的存在于对应模块。"""
L63:     cited = {key: value for key, value in M6_EVIDENCE.items() if not value.startswith("manual:")}
L64:     assert len(cited) == 7, f"§71 有 8 条，其中 7 条应可由测试证明，实际 {len(cited)}"
L65:     for key, evidence in cited.items():
L66:         module_name, test_name = evidence.split("::")
L67:         module = importlib.import_module(module_name)
L68:         assert callable(getattr(module, test_name, None)), f"{key}: {evidence} 不存在"
L69: 
L70: 
L71: def test_manual_gap_states_a_reason():
L72:     manual = {
L73:         key: value.split("manual:", 1)[1]
L74:         for key, value in M6_EVIDENCE.items()
L75:         if value.startswith("manual:")
L76:     }
L77:     assert manual, "Acceptance 5 需要真实教师，必须显式标注"
L78:     for key, reason in manual.items():
L79:         assert len(reason.strip()) > 20, f"{key}: 人工缺口必须写明原因，不能空着"


## FILE benchmarks/reports/evaluation_kit/A-dynamic/course.md

L1: # A / dynamic
L2: 
L3: - run: run_77e357790d91 status=succeeded
L4: - 模式：dynamic 实验：（无）
L5: - 模型调用：22 研究请求：0
L6: - 证据政策：['SUPPORTED']
L7: 
L8: > 评分说明见同目录 human_eval.yaml 与 benchmarks/reports/evaluation_kit/README.md
L9: 
L10: ## 自动检查命中的问题（请在 comment / must_fix 中说明是真问题还是误报）
L11: 
L12: | 类别 | 说明 |
L13: | --- | --- |
L14: | SAFETY | script:sec1 命中禁用表达：这个孩子就是 |
L15: | SAFETY | script:sec2 命中禁用表达：这个孩子就是 |
L16: | SAFETY | script:sec3 命中禁用表达：这个孩子就是 |
L17: 
L18: ## 门禁结论（供教师核对，不是评分）
L19: 
L20: - **G1@script:sec1: PASS**
L21: - **G1@script:sec2: PASS**
L22: - **G1@script:sec3: PASS**
L23: - **G2@script:sec1: PASS**
L24: - **G2@script:sec2: PASS**
L25: - **G2@script:sec3: PASS**
L26: - **G3@script:sec1: FAIL** — 缺少学习目标；缺少评价证据（目标—评价对应）；缺少 PCK 教学说明
L27: - **G3@script:sec2: FAIL** — 缺少学习目标；缺少评价证据（目标—评价对应）；缺少 PCK 教学说明
L28: - **G3@script:sec3: FAIL** — 缺少学习目标；缺少评价证据（目标—评价对应）；缺少 PCK 教学说明
L29: - **G4@script:sec1: PASS**
L30: - **G4@script:sec2: PASS**
L31: - **G4@script:sec3: PASS**
L32: - **G5@script:sec1: FAIL** — 缺少 UDL 障碍与替代路径分析
L33: - **G5@script:sec2: FAIL** — 缺少 UDL 障碍与替代路径分析
L34: - **G5@script:sec3: FAIL** — 缺少 UDL 障碍与替代路径分析
L35: - **G6@script:sec1: NEEDS_REVIEW** — 媒体选型未运行，无法确认视觉与动画决策
L36: - **G6@script:sec2: NEEDS_REVIEW** — 媒体选型未运行，无法确认视觉与动画决策
L37: - **G6@script:sec3: NEEDS_REVIEW** — 媒体选型未运行，无法确认视觉与动画决策
L38: - **G7@script:sec1: NOT_APPLICABLE**
L39: - **G7@script:sec2: NOT_APPLICABLE**
L40: - **G7@script:sec3: NOT_APPLICABLE**
L41: 
L42: ## lesson_plan:sec1
L43: 
L44: ```json
L45: {
L46:   "board_design": "标题：如何记录儿童真实行为\n一、五类信息：时间｜情境｜参与人｜具体动作｜对话原文\n二、判断问题：能直接看到或听到吗？\n事实记录：可观察、可指向案例证据\n推测或待核验：动机、情绪、人格判断\n三、改写步骤：圈出评价词 → 找动作与原话 → 补基本情境 → 按时间排序 → 推测单列\n四、自检：信息完整？动作具体？顺序清楚？原话保留？标签删除？推测单列？",
L47:   "difficult_points": [
L48:     "避免把对儿童内在动机或人格的判断写成已经发生的事实。",
L49:     "避免遗漏时间、情境、参与人或对话原文，以保证记录可供他人复核。",
L50:     "在连续行为中筛选关键的可观察信息，同时保持描述具体并遵循时间顺序。",
L51:     "认识到评价词虽然简短，却可能使行为描述人格化并影响后续观察。"
L52:   ],
L53:   "homework": [
L54:     "观察或回忆一个短小的儿童活动片段，写一则80—120字的观察记录；若无法开展真实观察，可使用课堂提供的练习案例。记录须包含时间、情境、参与人、行为顺序和对话原文；无法确认的内容标为“推测”或“待核验”，不得补写未观察到的信息。",
L55:     "从日常常见的评价性表述中选择两句，如“很调皮”“不合群”，分别改写为具体行为描述；若缺少必要情境信息，明确标注“待核验”，不自行补充。",
L56:     "使用课堂自检清单检查作业，圈出事实记录，并用另一种标记标出推测或待核验内容。"
L57:   ],
L58:   "key_points": [
L59:     "可核查的观察记录应交代时间、情境、参与人，并记录可直接观察到的动作和听到的对话原文。",
L60:     "提取信息时应保留具体动作、行为顺序和对话原文，使记录能够指回案例证据。",
L61:     "以“能否直接看到或听到”为依据区分事实与推测；对动机、情绪或人格的理解应单列为“推测”或“待核验”。",
L62:     "将“调皮”“故意捣乱”等概括性评价改写为具体行为，不把人格判断当作事实。"
L63:   ],
L64:   "objectives": [
L65:     {
L66:       "goal_ref": "g1",
L67:       "text": "说出可核查的儿童行为记录应包含的基本信息：时间、情境、参与人、具体动作和对话原文。"
L68:     },
L69:     {
L70:       "goal_ref": "g2",
L71:       "text": "从儿童活动案例中提取并按类别记录看得见、听得到的信息，同时指出对应的案例原文。"
L72:     },
L73:     {
L74:       "goal_ref": "g3",
L75:       "text": "依据“能否直接看到或听到”区分行为事实与待核验的推测，并将二者分栏记录。"
L76:     },
L77:     {
L78:       "goal_ref": "g4",
L79:       "text": "把含糊、评价性或人格化的表述改写为具体、可复核、非标签化的行为描述，并独立完成一则简短观察记录。"
L80:     }
L81:   ],
L82:   "preparation": [
L83:     "包含时间、情境、参与人、连续动作和对话原文的儿童活动案例一则。",
L84:     "同一情境的事实陈述与推测陈述对照卡。",
L85:     "含糊或人格化表述的分层改写练习单。",
L86:     "“时间—情境—参与人—动作—对话”信息提取表。",
L87:     "“事实记录—推测或待核验”双栏记录表。",
L88:     "观察记录自检清单。"
L89:   ],
L90:   "process": [
L91:     {
L92:       "intent": "激活已有经验，建立“暂停评价、先记事实”的学习问题。",
L93:       "minutes": 5,
L94:       "stage": "导入：先记录还是先评价",
L95:       "student_activity": "比较两种表述，说出其中可以直接看到或听到的内容，并指出无法仅凭表述核验的判断。",
L96:       "teacher_activity": "呈现“这个孩子很调皮”和一则只描述具体动作的简短陈述，请学生判断哪一则更容易由他人核对；暂不评价[REDACTED]，引出本课任务。"
L97:     },
L98:     {
L99:       "intent": "通过明确讲解和要素对应，形成可用于记录与自检的概念框架。",
L100:       "minutes": 7,
L101:       "stage": "明确概念：可核查记录的五类信息",
L102:       "student_activity": "在示例中圈画五类信息，口头概括可核查记录的构成，并用检查问题复核示例。",
L103:       "teacher_activity": "直接讲解时间、情境、参与人、具体动作和对话原文五类信息；用一个简短示例逐项标注，并示范用“能否看到或听到”检查内容。"
L104:     },
L105:     {
L106:       "intent": "练习从连续事件中筛选可观察信息，减少要素遗漏并保持行为顺序。",
L107:       "minutes": 8,
L108:       "stage": "案例分析：提取看得见、听得到的信息",
L109:       "student_activity": "独立阅读并分类提取信息，与同伴核对；为每项答案标出案例依据，并按发生顺序排列动作。",
L110:       "teacher_activity": "发放儿童活动案例和信息提取表，要求学生填写时间、情境、参与人、动作与对话原文；追问每项答案对应案例中的哪一句或哪一处。"
L111:     },
L112:     {
L113:       "intent": "借助对照案例识别事实与判断的边界，检查学生是否会把推测当作事实。",
L114:       "minutes": 7,
L115:       "stage": "对照辨析：事实与推测分栏",
L116:       "student_activity": "将陈述放入“事实记录”或“推测或待核验”栏，说明分类依据；把关键判断题拆分为可观察动作与待核验推测。",
L117:       "teacher_activity": "并列呈现描述同一情境的陈述，如具体动作、对话与涉及动机或人格的判断；引导学生依据“能否直接看到或听到”完成双栏分类。设置关键判断题：“儿童把积木推倒，所以他是故意捣乱。”询问整句能否直接作为事实记录。"
L118:     },
L119:     {
L120:       "intent": "提供完整范例，展示非标签化改写的思考路径和表达结构。",
L121:       "minutes": 7,
L122:       "stage": "示范改写：从评价词到具体行为",
L123:       "student_activity": "跟随示范标出评价词，对照改写前后内容，指出新记录中哪些部分可由案例证据核对。",
L124:       "teacher_activity": "完整示范改写步骤：圈出评价词，追问具体发生了什么，补充已有案例中的时间、情境、参与人、动作和对话，按顺序重写；将教师理解另列为“推测”，不补写案例未提供的信息。"
L125:     },
L126:     {
L127:       "intent": "逐步撤去支架，使学生将辨析规则应用于完整观察记录。",
L128:       "minutes": 8,
L129:       "stage": "渐隐练习：由提示改写到独立记录",
L130:       "student_activity": "依次完成有提示、少提示和无提示练习；独立写出含基本情境信息、行为顺序和对话原文的记录，并把个人理解标为“推测”或“待核验”。",
L131:       "teacher_activity": "先提供带有步骤提示的改写题，再撤去部分提示，最后要求学生根据案例独立完成一则简短观察记录。巡视时仅依据自检清单反馈：信息是否完整、动作是否具体、顺序是否清楚、对话是否保留原文、推测是否单列。"
L132:     },
L133:     {
L134:       "intent": "用即时反馈巩固规则，并以可见作品检验本节目标达成情况。",
L135:       "minutes": 3,
L136:       "stage": "展示反馈与课堂小结",
L137:       "student_activity": "依据清单互评并修改自己的记录，用一句话复述记录原则。",
L138:       "teacher_activity": "选取一则匿名记录，组织学生按照自检清单提出一项符合要求之处和一项可修改之处；总结五类信息、事实与推测分栏、非标签化改写三项规则。"
L139:     }
L140:   ],
L141:   "section_id": "sec1",
L142:   "title": "任务1 如何记录儿童真实行为"
L143: }
L144: ```
L145: 
L146: ## lesson_plan:sec2
L147: 
L148: ```json
L149: {
L150:   "board_design": "标题：区分事实描述与主观判断\n一、判断标准：能看见／能听见／可复核\n二、三类表述：\n1. 事实描述＝时间＋情境＋参与人＋具体动作＋对话原文\n2. 主观判断＝评价词／人格标签／未标注的动机或心理解释\n3. 明确推测＝“教师推测：……”＋与事实分开呈现\n三、改写流程：圈出判断词→提取已有事实→补齐材料中可确认的信息→保留对话原文→缺失信息标“待核验”\n四、双栏：事实记录｜教师推测",
L151:   "difficult_points": [
L152:     "识别“故意”“不愿意”“很生气”等对内在动机或心理状态的解释，避免将其当作可直接观察的事实。",
L153:     "发现隐藏在看似客观句子中的评价词，并依据可观察性和可复核性进行判断。",
L154:     "改写时不仅删除评价词，还要补充时间、情境、参与人、具体动作或对话原文，使记录可以复核。",
L155:     "保留教师的合理理解时，将其明确标注为“推测”，避免写成已经确认的事实。"
L156:   ],
L157:   "homework": [
L158:     "从给定的六条观察记录中分别标出事实描述、主观判断和明确标注的推测，并为每条分类写出依据。",
L159:     "将两条含人格标签、评价或动机归因的记录改写为事实记录；仅使用题目提供的信息，缺失内容标注为“待核验”。",
L160:     "完成一份“事实记录—教师推测”双栏练习，并用“能否看见或听见、能否复核、推测是否明确标注”三项标准自检。"
L161:   ],
L162:   "key_points": [
L163:     "以“能否直接看见或听见、能否由他人复核”为依据识别事实描述。",
L164:     "区分事实描述、主观判断与明确标注的推测，避免仅凭句式或个别词语分类。",
L165:     "把人格标签、评价和动机归因改写为包含时间、情境、参与人、具体动作及对话原文的记录。",
L166:     "采用“事实记录—教师推测”分栏方式，使观察证据与个人理解保持清晰边界。"
L167:   ],
L168:   "objectives": [
L169:     {
L170:       "goal_ref": "g1",
L171:       "text": "从观察记录中标出可直接看见、听见并可由他人复核的事实描述，并指出相应的可观察信息。"
L172:     },
L173:     {
L174:       "goal_ref": "g2",
L175:       "text": "将记录分类为事实描述、主观判断或明确标注的推测，并依据可观察性、可复核性和标注方式逐项说明理由。"
L176:     },
L177:     {
L178:       "goal_ref": "g3",
L179:       "text": "将含有评价、动机归因或人格标签的记录改写为包含时间、情境、参与人、具体行为及对话原文的事实记录，并将教师推测单独标注。"
L180:     }
L181:   ],
L182:   "preparation": [
L183:     "事实描述、主观判断和明确标注推测的对比案例卡。",
L184:     "包含人格标签、评价词、动机归因和心理状态解释的观察记录练习单。",
L185:     "“时间—情境—参与人—可观察行为—对话原文”改写检查表。",
L186:     "“事实记录—教师推测”双栏记录表。",
L187:     "用于即时分类反馈的三类标记卡或投票工具。"
L188:   ],
L189:   "process": [
L190:     {
L191:       "intent": "激活已有经验，形成以可观察性和可复核性检查记录的课堂任务。",
L192:       "minutes": 5,
L193:       "stage": "导入：同一事件的两种写法",
L194:       "student_activity": "独立圈出能够直接看见或听见的内容，并说出哪些表述需要进一步证据。",
L195:       "teacher_activity": "呈现“乐乐脾气差”和一条包含具体情境、动作与对话原文的记录，请学生比较两种写法能够提供哪些可核查信息；暂不公布分类答案。"
L196:     },
L197:     {
L198:       "intent": "对应g1，建立识别事实描述的明确判断标准。",
L199:       "minutes": 8,
L200:       "stage": "概念建构：什么是可核查的事实描述",
L201:       "student_activity": "使用检查问题判断示例中的事实成分，说明每项信息可通过何种方式被观察或复核。",
L202:       "teacher_activity": "结合示例示范逐词检查：是否能被看见、是否能被听见、他人在同一情境中是否可以复核；同时标出行为、语言、时间、情境和参与人等信息。"
L203:     },
L204:     {
L205:       "intent": "对应g2，通过对比案例澄清三类表述的边界及分类依据。",
L206:       "minutes": 10,
L207:       "stage": "对比辨析：事实、判断与推测",
L208:       "student_activity": "对案例逐项分类，在记录旁写出判断依据，并与同伴核对存在分歧的项目。",
L209:       "teacher_activity": "并列呈现三类记录：事实描述、含评价或动机归因的主观判断、以“教师推测”等方式明确标注的解释；组织学生比较其证据来源、可观察性、可复核性和标注方式。"
L210:     },
L211:     {
L212:       "intent": "检查学生是否真正依据可观察性和可复核性判断，而非仅凭句式分类。",
L213:       "minutes": 5,
L214:       "stage": "关键检测：识别隐藏判断",
L215:       "student_activity": "独立作答并提交理由；依据反馈修改分类，指出句中不可直接观察的部分。",
L216:       "teacher_activity": "呈现包含“故意”“不愿意”“很生气”等表述的关键问题，要求学生选择类别并说明依据；根据回答集中纠正把心理状态或动机解释当作事实的错误。"
L217:     },
L218:     {
L219:       "intent": "连接g2与g3，使学生理解主观标签需要被具体的观察信息替代。",
L220:       "minutes": 8,
L221:       "stage": "案例分析：从人格标签到具体记录",
L222:       "student_activity": "指出人格标签无法直接复核，并根据给定案例材料提取时间、情境、参与人、动作和对话原文。",
L223:       "teacher_activity": "以“乐乐脾气差”为错误案例，引导[REDACTED]：何时、何地、与谁、发生了什么、有哪些动作、说了什么；强调对话应保留原文，缺失信息不得自行补写。"
L224:     },
L225:     {
L226:       "intent": "对应g3，以完整示范建立可执行的改写程序，并落实不编造缺失信息的要求。",
L227:       "minutes": 8,
L228:       "stage": "示范改写：完整范例",
L229:       "student_activity": "对照改写检查表复述每一步，比较原句与改写结果，并指出改写后仍需核验的信息。",
L230:       "teacher_activity": "完整演示改写流程：圈出评价或归因词，提取材料中已有的可观察信息，按时间和情境组织具体行为，原样保留儿童对话；材料未提供的内容标记为“待核验”，不作补充。"
L231:     },
L232:     {
L233:       "intent": "通过逐步撤去提示，提升学生独立改写含评价和动机归因记录的能力。",
L234:       "minutes": 10,
L235:       "stage": "渐隐练习：带提示改写",
L236:       "student_activity": "先按步骤完成第一条改写，再借助检查表完成第二条；用不同标记核对时间、情境、参与人、行为和对话原文。",
L237:       "teacher_activity": "提供两条案例，第一条保留改写步骤提示，第二条仅保留检查表；巡视并针对遗漏情境、动作不具体或对话被评价性转述等问题提供反馈。"
L238:     },
L239:     {
L240:       "intent": "落实迁移目标，使学生保留教师理解的同时维持事实与推测的清晰边界。",
L241:       "minutes": 10,
L242:       "stage": "独立应用：事实与推测分栏",
L243:       "student_activity": "独立完成事实记录与教师推测分栏，随后用“可观察、可复核、明确标注”三项标准进行自检。",
L244:       "teacher_activity": "发放新案例与双栏表，要求左栏只写事实记录，右栏可写教师理解但必须冠以“教师推测”；提醒学生不得把推测写成确定结论。"
L245:     },
L246:     {
L247:       "intent": "收集对应g1、g2和g3的即时学习证据，为后续教学调整提供依据。",
L248:       "minutes": 6,
L249:       "stage": "总结与出口评价",
L250:       "student_activity": "完成出口单：分类记录、写出依据，并将一条人格化判断改写为事实记录。",
L251:       "teacher_activity": "归纳判断与改写要点，发放包含分类、理由说明和一句改写任务的出口单，依据作答确认目标达成情况。"
L252:     }
L253:   ],
L254:   "section_id": "sec2",
L255:   "title": "任务2：区分事实描述与主观判断"
L256: }
L257: ```
L258: 
L259: ## lesson_plan:sec3
L260: 
L261: ```json
L262: {
L263:   "board_design": "任务3：避免给儿童贴标签\n\n一、识别标签\n一次行为 ≠ 人格特征\n常见线索：“就是……”“一向……”以及脱离情境的人格形容词\n\n二、还原事实\n情境：何时、何地、与谁、正在进行什么活动\n行为：看到了什么具体动作\n语言：听到了什么原话\n缺失信息：待核验，不补造\n\n三、分开表达\n事实：可观察、可复述、可核查\n推测：可能……；需要进一步观察……\n支持策略：教师接下来可以采取的具体行动\n\n自检：删标签—补事实—标推测—定支持—留复核线索",
L264:   "difficult_points": [
L265:     "察觉简短、熟悉的形容词可能已经把一次行为概括为儿童的人格特征。",
L266:     "去除标签后补充行为发生的时间、情境、参与人、具体动作和原话，而不只是替换评价词。",
L267:     "在保留教师专业思考的同时，清楚划分事实、推测与支持策略。",
L268:     "检查已有标签是否影响后续观察，并主动记录与原有判断一致及不一致的信息。"
L269:   ],
L270:   "homework": [
L271:     "从自己已有的观察记录中选择一则，圈出人格化或贬义化称谓，并将其改写为包含情境、具体行为和对话原文的事实描述；原记录未提供的信息标记为“待核验”。",
L272:     "将改写后的案例整理为“事实—推测—支持策略”三栏，确保推测有明确标记，支持策略不被写成儿童特征。",
L273:     "使用自检清单复核作业，并补写一项后续需要观察的信息，说明该信息可用于核查什么问题。"
L274:   ],
L275:   "key_points": [
L276:     "辨认将一次具体行为概括为儿童稳定人格特征的标签化表达。",
L277:     "用情境、可见动作和对话原文替代“调皮”“内向”等人格化称谓。",
L278:     "分别记录事实、推测和支持策略，不把动机或人格判断写成已确认事实。",
L279:     "依据可核查的观察信息讨论后续支持策略。"
L280:   ],
L281:   "objectives": [
L282:     {
L283:       "goal_ref": "g1",
L284:       "text": "识别观察记录中的标签化表达，并指出其中缺少的情境、具体行为或对话原文。"
L285:     },
L286:     {
L287:       "goal_ref": "g2",
L288:       "text": "将“这个孩子就是……”式表述改写为包含情境、可观察行为和可复述语言的事实描述。"
L289:     },
L290:     {
L291:       "goal_ref": "g3",
L292:       "text": "分析案例中的事实、推测和支持策略，分别表述三类内容，并将对儿童动机或需要的理解明确标记为推测。"
L293:     }
L294:   ],
L295:   "preparation": [
L296:     "同一事件的两版观察记录：一版含标签化表达，一版包含情境、具体行为和对话原文。",
L297:     "标签化记录改写示例及分步填写模板。",
L298:     "包含事实、推测和支持策略混淆问题的案例卡。",
L299:     "“事实—推测—支持策略”三栏学习单。",
L300:     "观察记录自检清单：人格化称谓、贬义表达、情境信息、可见行为、可听语言、推测标记和复核信息。"
L301:   ],
L302:   "process": [
L303:     {
L304:       "intent": "激活学生对事实描述与主观判断的已有认识，引出标签化表达与事实记录的区别。",
L305:       "minutes": 5,
L306:       "stage": "导入：两种记录，哪一种可以复核",
L307:       "student_activity": "比较两则记录，圈画其中的评价词、具体动作和对话原文，说明哪一则提供了更可核查的信息。",
L308:       "teacher_activity": "呈现针对同一事件的两则记录，例如“这个孩子很调皮”和一则包含活动情境、具体动作及原话的记录。要求学生先独立判断哪一则更便于他人了解当时发生了什么，并圈出判断依据。"
L309:     },
L310:     {
L311:       "intent": "运用对比案例帮助学生识别从具体行为到人格概括的语言变化，对应目标g1。",
L312:       "minutes": 10,
L313:       "stage": "发现标签：对比案例辨析",
L314:       "student_activity": "逐组标出标签化表达，并从时间、情境、参与人、可见行为和可听语言等方面指出缺失信息；用自己的话说明标签如何把一次行为扩大为人格判断。",
L315:       "teacher_activity": "并列呈现多组针对同一事件的标签化记录与事实记录，组织[REDACTED]：标签指向的是一次行为还是对儿童人格的概括；记录缺少哪些可核查信息。随后归纳识别线索，如“他就是……”“她一向……”以及脱离情境的人格形容词。"
L316:     },
L317:     {
L318:       "intent": "检查学生是否真正掌握标签识别标准，及时发现把中性措辞误当作完整事实记录的问题。",
L319:       "minutes": 5,
L320:       "stage": "关键检查：快速判断",
L321:       "student_activity": "独立作答后说明理由，指出短句中已经具备和仍然缺少的信息，并根据反馈修正判断。",
L322:       "teacher_activity": "呈现若干短句，要求学生判断“事实描述”“标签化表达”或“信息不足”，并追问判断依据。针对分歧较大的短句及时澄清：去掉评价词并不等于已经形成可核查记录。"
L323:     },
L324:     {
L325:       "intent": "通过完整示范建立可重复使用的改写结构，避免学生只替换评价词而不补充可核查信息，对应目标g2。",
L326:       "minutes": 10,
L327:       "stage": "还原事实：教师示范改写",
L328:       "student_activity": "观察并记录改写步骤，对照原句指出每一步增加或删除了什么信息，辨认示范中哪些内容属于直接观察，哪些信息仍需核验。",
L329:       "teacher_activity": "选择一则“这个孩子就是很调皮”式记录，示范四步改写：删除人格概括；补充事件发生的时间与情境；写出可以看到的动作；记录可以复述的原话。示范后逐项对照自检清单，说明无法确认的信息不补写，缺失内容标记为“待核验”。"
L330:     },
L331:     {
L332:       "intent": "让学生把改写方法应用于新记录，并形成不编造缺失信息的记录习惯。",
L333:       "minutes": 12,
L334:       "stage": "独立练习：改写标签化记录",
L335:       "student_activity": "按照“情境—具体行为—对话原文”的结构改写记录；对材料没有提供但复核所需的信息标记为“待核验”；两人互换作品并依据清单提出修改意见。",
L336:       "teacher_activity": "发放含“调皮”“内向”等标签化表达的练习记录，要求每名[REDACTED]完成一则改写。巡视时只依据给定材料追问“当时在哪里”“看到了什么”“听到了什么”，不要求学生补造案例中未提供的信息。"
L337:     },
L338:     {
L339:       "intent": "通过错误案例澄清三类表述的边界，使学生既不把推测当成事实，也能保留基于观察提出支持方案的空间，对应目标g3。",
L340:       "minutes": 12,
L341:       "stage": "案例辨析：纠正三类混淆",
L342:       "student_activity": "小组分析错误位置，删除或改写越界表述；分别形成事实描述、明确标记的推测和可执行的支持策略，并说明每一栏的依据。",
L343:       "teacher_activity": "提供错误案例，其中分别包含把动机判断写成事实、把支持策略写成儿童特征以及事实依据不足等问题。要求学生将内容重新放入“事实—推测—支持策略”三栏，并在推测前使用“可能”“需要进一步观察”等标记。"
L344:     },
L345:     {
L346:       "intent": "将课堂方法迁移到观察记录、教研讨论和家园沟通，降低已有标签对后续观察与表达的干扰。",
L347:       "minutes": 8,
L348:       "stage": "迁移检查：记录与沟通中的自检",
L349:       "student_activity": "删除或改写标签化称谓，补充已有材料能够支持的具体信息；列出一项需要继续观察或核验的问题，并说明应收集什么信息。",
L350:       "teacher_activity": "提供一段用于教研讨论或家园沟通的简短表述，组织学生使用自检清单检查人格化称谓、贬义表达、推测标记及复核信息。提醒[REDACTED]是否只选择了支持原有标签的材料，并补充需要继续观察的问题。"
L351:     },
L352:     {
L353:       "intent": "收集目标g1、g2和g3的即时达成证据，为后续教学调整提供依据。",
L354:       "minutes": 3,
L355:       "stage": "总结与出口任务",
L356:       "student_activity": "提交出口任务：圈出标签，写出一条事实描述，并分别补充一条明确标记的推测和一条支持策略。",
L357:       "teacher_activity": "引导学生用一句话概括记录原则，随后出示一则短记录，要求学生完成标签识别、事实改写和三栏分类中的关键步骤。"
L358:     }
L359:   ],
L360:   "section_id": "sec3",
L361:   "title": "任务3：避免给儿童贴标签"
L362: }
L363: ```
L364: 
L365: ## script:sec1
L366: 
L367: ```json
L368: {
L369:   "section_id": "sec1",
L370:   "template_ref": "f318acdc2871d0459b912425054fb443a5c0216c10e6a4024ee624ea25222312",
L371:   "title": "任务1",
L372:   "units": [
L373:     {
L374:       "kind": "title",
L375:       "text": "任务1 如何记录儿童真实行为",
L376:       "unit_id": "u1"
L377:     },
L378:     {
L379:       "claim_refs": [
L380:         "clm_dfe3d7bcef@v1",
L381:         "clm_d1eea6af49@v1",
L382:         "clm_37754acbb5@v1"
L383:       ],
L384:       "kind": "narration",
L385:       "text": "这一任务练习记录幼儿在具体情境中发生的真实行为。这里的“真实行为记录”，指向一个基本要求：别人阅读记录时，能够知道事情发生的时间和情境、当时有哪些参与人，以及观察者直接看到了哪些动作、听到了哪些话。我们可以用五个问题检查记录：什么时候？在哪里、正在进行什么活动？谁在场？他们依次做了什么？他们具体说了什么？如果某句话不能回答这些问题，又加入了对动机、情绪或人格的判断，就要先把它从事实记录中分离出来。\n记录时，请先把自己放在“摄像机和录音机”的位置。摄像机可以记录伸手、拿起、放下、推、转身、看向某人等动作；录音机可以记录说话者的原话和音量变化。摄像机不能直接拍到“故意”，录音机也不能直接录到“自私”。因此，“他故意捣乱”“她就是不想合作”不能直接作为已发生的事实。面对“这个孩子就是……”这样的句式，要立即停下来检查：后面是不是接了一个概括性标签？能否换成当时实际发生的动作或对话？\n还要注意，事实记录并不等于解释儿童。教师可以形成理解，但要把理解单列为“推测”，并保留待核验状态。例如，“小宇可能担心自己的搭建被改变”是一种可能的理解，不是观察者能够直接看到或听到的内容。已提供材料中的相关结论本身标注为待核验：将对儿童内在动机或人格的判断写成事实，会降低观察记录的可用性【待核验】；使用“调皮”“内向”等标签概括儿童后，教师更容易注意与标签一致的行为，而忽略不一致的信息【待核验】；在讨论后续支持策略前区分可观察事实与主观判断，有助于提升教学决策依据的清晰度【待核验】。本节不把这些待核验结论当作确定事实，只把“事实与推测分栏”作为当前记录规则来练习。",
L386:       "unit_id": "u2"
L387:     },
L388:     {
L389:       "kind": "visual",
L390:       "text": "画面左侧呈现五格检查框：时间、情境、参与人、动作、对话原文；右侧呈现一条分界线，上方写“可直接看到或听到”，下方写“需要解释或核验”。",
L391:       "unit_id": "u3",
L392:       "visual_function": "structure"
L393:     },
L394:     {
L395:       "kind": "case",
L396:       "text": "案例正文（虚构）：10月12日9:20，幼儿园活动室积木区。参与人是[REDACTED]、安安和教师陈老师。小宇把三块长方形积木叠在一起。安安伸手拿起最上面的一块。小宇看向安安，说：“这是我搭桥的。”安安说：“我也要用。”小宇从安安手中拿回积木，把积木放到自己身后。安安用手推了一下积木堆，积木倒在地垫上。小宇提高音量说：“你把我的桥弄倒了！”陈老师走到两人身边，说：“我看到积木倒了。请你们先告诉我刚才发生了什么。”\n先提取基本信息。时间是10月12日9:20；情境是幼儿园活动室积木区；参与人是小宇、安安和陈老师。动作包括叠积木、伸手拿起积木、看向安安、拿回积木、把积木放到身后、推积木堆，以及教师走到两人身边。对话要保留原文，不能把“小宇说：‘这是我搭桥的。’”压缩成“小宇拒绝分享”，因为后一句已经加入了解释。\n现在比较六条陈述。第一条“9:20，小宇和安安在积木区”，能够从情境信息中核对，属于可观察事实。第二条“安安故意捣乱”包含对动机的判断；观察者看到了推积木堆，却没有直接看到“故意”，所以它属于待核验的推测或判断。第三条“安安推了一下积木堆，积木倒在地垫上”，描述了可以看到的动作和结果，属于可观察事实。第四条“小宇很自私，不愿意分享”把一次情境中的行为概括成了人格或稳定倾向，属于待核验的判断。第五条“小宇说：‘这是我搭桥的。’”保留了听到的原话，属于可观察事实。第六条“小宇可能担心自己的搭建被改变”使用了“可能”，表达的是对内在状态的理解，应该列入推测，并标记待核验。\n接着改写标签化表述。第一步，圈出不能直接观察的词，如“故意捣乱”“很自私”。第二步，回到案例寻找与这些词对应的动作和原话。第三步，按发生顺序重写。“安安故意捣乱”可以改成：“安安用手推了一下积木堆，积木倒在地垫上。”“小宇很自私，不愿意分享”可以改成：“小宇从安安手中拿回积木，把积木放到自己身后，并说：‘这是我搭桥的。’”改写只保留当时可见、可听且能够回到案例核对的内容。",
L397:       "unit_id": "u4"
L398:     },
L399:     {
L400:       "kind": "visual",
L401:       "text": "画面并列显示原句与改写句；用红色划去“故意捣乱”“很自私”，用蓝色标出“推了一下”“拿回”“放到自己身后”和对话原文。",
L402:       "unit_id": "u5",
L403:       "visual_function": "contrast"
L404:     },
L405:     {
L406:       "kind": "interaction",
L407:       "text": "暂停作答：以下哪一项能够直接进入事实栏？A.安安想破坏小宇的作品；B.安安推了一下积木堆；C.小宇是一个不爱分享的孩子。请选择并说明：这项内容能否直接看到或听到？反馈：选择B。A涉及动机，C涉及人格概括，都应放入待核验的推测或判断栏。",
L408:       "unit_id": "u6"
L409:     },
L410:     {
L411:       "claim_refs": [],
L412:       "kind": "narration",
L413:       "text": "最后，把提取到的信息组合成一则简短记录。写作顺序可以是：先交代时间、情境和参与人，再依次记录动作与对话，最后另起一栏写教师的理解。示例如下：“10月12日9:20，幼儿园活动室积木区，小宇、安安和陈老师在场。小宇把三块长方形积木叠在一起。安安拿起最上面的一块。小宇看向安安，说：‘这是我搭桥的。’安安说：‘我也要用。’小宇从安安手中拿回积木，放到自己身后。安安推了一下积木堆，积木倒在地垫上。小宇提高音量说：‘你把我的桥弄倒了！’陈老师走到两人身边，请他们说明刚才发生的事情。”\n这份记录没有把任何一个动作直接命名为“捣乱”或“自私”，也没有删除双方的原话。教师如果需要保留自己的理解，可以另写：“推测【待核验】：小宇可能担心自己的搭建被改变。”这里的“可能”不能改成肯定句。完成记录后，再做一次反向检查：删掉所有评价词后，读者是否仍能知道谁在什么时候、什么情境中，依次做了什么、说了什么？如果缺少信息，就回到观察材料补充；如果出现“故意”“不尊重”“很乖”或“就是……”等无法由当时动作和原话直接确认的表达，就把它移到推测栏，或改写为具体行为。",
L414:       "unit_id": "u7"
L415:     },
L416:     {
L417:       "kind": "visual",
L418:       "text": "画面展示双栏记录卡。左栏标题为“观察事实”，按时间顺序放置情境、参与人、动作和带引号的原话；右栏标题为“教师推测【待核验】”，仅放可能的动机或情绪理解。",
L419:       "unit_id": "u8",
L420:       "visual_function": "classification"
L421:     },
L422:     {
L423:       "kind": "interaction",
L424:       "text": "独立练习：请根据虚构案例写一则80至120字的观察记录。必须包含时间、情境、参与人、至少三个连续动作和两句对话原文；另起一行写一条“推测【待核验】”。完成后自检：第一，事实栏中的每句话能否直接看到或听到？第二，动作顺序是否与案例一致？第三，是否出现人格标签？第四，推测是否与事实分开？",
L425:       "unit_id": "u9"
L426:     },
L427:     {
L428:       "kind": "interaction",
L429:       "text": "提交前改写：把“安安是个调皮的幼儿，小宇也很自私”改为不推断人格的记录。参考反馈：“安安用手推了一下积木堆，积木倒在地垫上。小宇从安安手中拿回积木，把积木放到自己身后，并说：‘这是我搭桥的。’”如果你的答案加入了“因为”“故意”或“就是不愿意”等内容，请将其删除，或移入“推测【待核验】”栏。",
L430:       "unit_id": "u10"
L431:     }
L432:   ],
L433:   "word_count": {
L434:     "count": 1975,
L435:     "in_range": false,
L436:     "max": 1800,
L437:     "method": "unicode_non_whitespace_chars",
L438:     "min": 1500,
L439:     "scope_note": "统计教师讲解正文（含正文中讲述的案例），不计标题、画面指令、引用索引与独立备注"
L440:   }
L441: }
L442: ```
L443: 
L444: ## script:sec2
L445: 
L446: ```json
L447: {
L448:   "section_id": "sec2",
L449:   "template_ref": "f318acdc2871d0459b912425054fb443a5c0216c10e6a4024ee624ea25222312",
L450:   "title": "任务2",
L451:   "units": [
L452:     {
L453:       "kind": "title",
L454:       "text": "任务2：区分事实描述与主观判断",
L455:       "unit_id": "u1"
L456:     },
L457:     {
L458:       "kind": "narration",
L459:       "text": "观察记录先要回答一个核心问题：这句话写的是能够直接看见、听见并由他人复核的信息，还是记录者对幼儿的评价和解释？可核查的事实通常包括具体时间、活动情境、参与人、动作、物品变化以及对话原文。例如，“周二14:05，乐乐把三块蓝色积木推到地上”，别人可以依据同一情境核对时间、动作、数量和结果。相反，“乐乐表现不好”没有说明发生了什么；“乐乐很生气”解释了心理状态；“乐乐故意推积木”判断了内在动机。这些内容都不能直接当作事实记录。判断时不要只看句子是否写得肯定，而要逐词追问：我真的看见或听见了吗？另一位观察者能核对吗？如果答案是否定的，就需要把相关词语标为判断或推测。",
L460:       "unit_id": "u2"
L461:     },
L462:     {
L463:       "kind": "visual",
L464:       "text": "画面呈现三问检查卡：①能直接看见或听见吗？②包含可核对的动作、语言或情境吗？③是否夹带人格、心理状态或动机解释？关键词“看见、听见、复核”高亮。",
L465:       "unit_id": "u3",
L466:       "visual_function": "criteria"
L467:     },
L468:     {
L469:       "kind": "interaction",
L470:       "text": "快速判断：“晨间活动时，明明三次离开座位”属于哪一类？“明明坐不住”属于哪一类？请指出具体是哪些词决定了你的分类，并说明别人能否根据记录复核。",
L471:       "unit_id": "u4"
L472:     },
L473:     {
L474:       "kind": "narration",
L475:       "text": "接下来比较三类表达。第一类是事实描述：“幼儿把画笔放在桌上，说：‘我不画了。’”动作和原话可以被听见、看见。第二类是主观判断：“这个孩子就是……没有耐心。”其中“没有耐心”用一个评价概括幼儿，记录里却没有呈现支持这一判断的具体行为。第三类是明确标注的推测：“推测：幼儿可能不想继续绘画，原因待进一步观察和核验。”这仍然不是事实，但它用“推测”“可能”和“待核验”说明了信息性质。教师的理解不必被删除，关键是不能让读者误以为解释已经得到确认。因此，分类依据不是一句话听起来是否合理，而是其证据来自直接观察、个人评价，还是基于事实形成且已经明确标注的暂时解释。",
L476:       "unit_id": "u5"
L477:     },
L478:     {
L479:       "kind": "visual",
L480:       "text": "三栏对照表：事实描述—记录所见所闻；主观判断—评价、标签或未经标注的解释；明确推测—与事实分开，并出现“推测、可能、待核验”等标记。",
L481:       "unit_id": "u6",
L482:       "visual_function": "comparison"
L483:     },
L484:     {
L485:       "case_ref": "case1",
L486:       "kind": "case",
L487:       "text": "【虚构情境】周二14:05，积木区自由活动时，乐乐和安安同时伸手拿桌上的红色长积木。安安说：“我先拿到的。”乐乐把红色长积木拉到自己面前，说：“我要搭桥。”安安握住积木另一端。乐乐松手后，用右手将桌边的三块蓝色积木推到地上，并大声说：“不给你玩！”教师最初记录：“乐乐脾气差，因为抢不到积木就很生气，还故意把积木推到地上。”现在逐项辨析：“周二14:05”是时间；“积木区自由活动”是情境；“同时伸手”“拉到自己面前”“握住另一端”“松手”“用右手将三块蓝色积木推到地上”是可观察动作；引号内文字是现场听到的对话原文。“脾气差”把一次情境中的表现扩展成人格化判断；“很生气”是对心理状态的解释；“故意”是对内在动机的归因；“因为抢不到积木”则把原因写成了已经确定的结论。它们都不应混入事实栏。",
L488:       "unit_id": "u7"
L489:     },
L490:     {
L491:       "kind": "interaction",
L492:       "text": "暂停并分类：请把案例中的语句分别标为“事实”“主观判断”或“解释但未标注为推测”，再逐项使用“能否看见、能否听见、能否复核”说明依据。特别检查“很生气”和“大声说”为什么不能归为同一类。",
L493:       "unit_id": "u8"
L494:     },
L495:     {
L496:       "kind": "narration",
L497:       "text": "改写时不能只删除“脾气差”“很生气”和“故意”。如果只写“乐乐把积木推到地上”，虽然减少了评价，却丢失了时间、情境、参与人、行为发生前后的过程和对话原文。完整改写可以依次补齐五项：什么时候，在哪里或什么活动中，谁参与，具体做了什么，说了什么。对话尽量保留原话，并加引号。例如，不能把“不给你玩！”转述成“乐乐不愿分享”，因为“不愿”仍然在解释意愿，“分享”也改变了原话呈现的信息。记录音量时可以写“大声说”，前提是这是当时听到的声音表现；不要直接把它替换成“愤怒地喊”，因为“愤怒”加入了心理解释。",
L498:       "unit_id": "u9"
L499:     },
L500:     {
L501:       "case_ref": "case1",
L502:       "kind": "case",
L503:       "text": "【虚构情境·改写示范】事实记录：“周二14:05，积木区自由活动时，乐乐和安安同时伸手拿桌上的红色长积木。安安说：‘我先拿到的。’乐乐把积木拉到自己面前，说：‘我要搭桥。’安安握住积木另一端。乐乐松手后，用右手将桌边的三块蓝色积木推到地上，并大声说：‘不给你玩！’”第一步，删除“脾气差”等评价；第二步，把“抢不到”“很生气”“故意”等原因、心理和动机解释移出事实栏；第三步，补回时间、情境、参与人、动作顺序、物品数量和对话原文。这样得到的是对情境的具体记录，而不是“这个孩子就是……”某种人的结论。",
L504:       "unit_id": "u10"
L505:     },
L506:     {
L507:       "kind": "visual",
L508:       "text": "改写流程动画：圈出标签和归因词—删除或移出事实栏—补齐时间、情境、参与人、动作—恢复带引号的对话原文—用三问检查卡复核。",
L509:       "unit_id": "u11",
L510:       "visual_function": "procedure"
L511:     },
L512:     {
L513:       "kind": "interaction",
L514:       "text": "渐隐练习：把“乐乐因为小气，故意不把积木给安安”改写为事实记录。第一轮可使用五项提示；第二轮不看提示独立改写。完成后圈出时间、情境、参与人和动作，并给每句原话加引号。案例没有提供的信息不得自行补写，应标记为“记录中未提供”。",
L515:       "unit_id": "u12"
L516:     },
L517:     {
L518:       "kind": "narration",
L519:       "text": "最后，把事实和教师推测分栏。事实栏只放刚才的改写记录。教师推测栏可以写：“推测：乐乐推落积木的行为可能与双方争拿同一块积木有关，具体原因待进一步观察和核验。”这里保留了教师对前后事件关系的理解，但“推测”“可能”和“待进一步观察和核验”清楚提示：这不是已经确认的原因。分栏后还要做一次交叉检查：事实栏中是否残留“故意、不愿意、很生气、脾气差”等动机、心理或人格词？推测栏是否错误地使用“就是、一定、证明了”等确定说法？如果有，就继续修改。面对新的观察记录，也按相同顺序处理：先保存可核查的所见所闻，再把个人理解单独标明为推测。",
L520:       "unit_id": "u13"
L521:     },
L522:     {
L523:       "kind": "visual",
L524:       "text": "左右分栏示意：左栏“事实记录”放时间、情境、参与人、动作和对话原文；右栏“教师推测”以“推测：……可能……，待进一步观察和核验”开头。两栏之间用清晰分隔线。",
L525:       "unit_id": "u14",
L526:       "visual_function": "organization"
L527:     },
L528:     {
L529:       "kind": "interaction",
L530:       "text": "课堂提交：完成一份“事实记录—教师推测”分栏表。互评时逐项回答：事实是否能被看见、听见和复核？是否保留对话原文？推测是否单独放置并明确标注？是否把未知原因写成了确定事实？最后用一句话说明你修改了哪个评价词或动机归因，以及修改依据。",
L531:       "unit_id": "u15"
L532:     }
L533:   ],
L534:   "word_count": {
L535:     "count": 1669,
L536:     "in_range": true,
L537:     "max": 1800,
L538:     "method": "unicode_non_whitespace_chars",
L539:     "min": 1500,
L540:     "scope_note": "统计教师讲解正文（含正文中讲述的案例），不计标题、画面指令、引用索引与独立备注"
L541:   }
L542: }
L543: ```
L544: 
L545: ## script:sec3
L546: 
L547: ```json
L548: {
L549:   "section_id": "sec3",
L550:   "template_ref": "f318acdc2871d0459b912425054fb443a5c0216c10e6a4024ee624ea25222312",
L551:   "title": "任务3",
L552:   "units": [
L553:     {
L554:       "kind": "title",
L555:       "text": "任务3：避免给幼儿贴标签",
L556:       "unit_id": "u1"
L557:     },
L558:     {
L559:       "claim_refs": [],
L560:       "kind": "narration",
L561:       "text": "这一任务练习把“这个孩子就是……”式的人格概括，还原为可以核查的观察记录。先看一个关键区别：记录“幼儿把积木放进自己的篮子”，是在描述当时可见的动作；记录“这个孩子就是调皮”，则从一次或若干次行为跳到了对幼儿稳定特征的概括。标签往往很短，也很熟悉，因此容易被误认为事实。识别时，可以追问三个问题：这句话能否由现场录像直接看到或听到？它描述的是某个时刻的行为，还是在概括幼儿一贯的样子？另一名观察者能否根据记录还原事情经过？如果答案是否定的，就需要继续拆解。",
L562:       "unit_id": "u2"
L563:     },
L564:     {
L565:       "kind": "visual",
L566:       "text": "左右对照呈现：“这个孩子就是调皮，总爱捣乱”与“周二9:20，小宇拿起桥旁两块积木，将其中一块放进自己的篮子”。用颜色分别标出人格概括、时间、情境和动作。",
L567:       "unit_id": "u3",
L568:       "visual_function": "contrast"
L569:     },
L570:     {
L571:       "case_ref": "case1",
L572:       "kind": "case",
L573:       "text": "以下案例为虚构。周二上午9:20，建构区内有陈老师、幼儿小宇和同伴安安。陈老师最初记录：“小宇就是调皮，总爱捣乱，还故意惹安安生气。需要让他学会听话。”逐句检查可以发现：“调皮”是人格化标签；“总爱捣乱”把当前事件扩大成了稳定表现，却没有列出可以支持“总爱”的多次记录；“故意惹安安生气”同时包含了对小宇动机和安安感受的推测；“学会听话”是笼统要求，没有指出需要支持的具体行为。这份记录还缺少事件发生时两名幼儿正在做什么、小宇做了哪些动作、动作的先后顺序，以及双方说过什么。仅凭原记录，复核者无法还原冲突怎样发生，也无法判断支持策略应针对哪个环节。",
L574:       "unit_id": "u4"
L575:     },
L576:     {
L577:       "kind": "interaction",
L578:       "text": "请找出原记录中的四处标签化或判断性表达。对每一处分别回答：它缺少时间、情境、参与人、动作、原话中的哪些信息？",
L579:       "unit_id": "u5"
L580:     },
L581:     {
L582:       "claim_refs": [],
L583:       "kind": "narration",
L584:       "text": "接下来进行改写。第一步，暂时删去“调皮”“捣乱”“故意”“听话”等评价词，只保留能够继续追问的事件。第二步，补充时间、地点、参与人和活动背景。第三步，按照发生顺序写动作，使用“走到”“拿起”“放进”“拉到身后”“放回”等可见动词。第四步，记录能够复述的语言，并用引号保留原话。注意，去掉标签并不等于完成改写。例如，把“他很调皮”换成“他表现不好”，只是更换了评价词，仍然没有提供可核查信息。合格的事实描述应使未在现场的人也能按照文字辨认事件中的行为与语言，但不替记录者推断动机。",
L585:       "unit_id": "u6"
L586:     },
L587:     {
L588:       "case_ref": "case1",
L589:       "kind": "case",
L590:       "text": "陈老师根据现场笔记改写为：“周二9:20，建构区。安安正在用长方形积木搭桥。小宇走到安安身边，拿起桥旁的两块长方形积木。安安说：‘这是我搭桥要用的。’小宇把其中一块放进自己的篮子，说：‘我也要长的。’安安伸手拿篮子里的积木，小宇将篮子拉到身后。教师走近后，小宇把积木放回桌面。”现在逐项核对：时间是周二9:20；情境是建构区搭桥活动；参与人包括小宇、安安和走近的教师；动作按照先后顺序记录；两名幼儿的原话被直接保留。与原记录相比，这一版本没有回答“谁更乖”或“谁故意怎样”，而是提供了可以回看、比较和补充的事件线索。",
L591:       "unit_id": "u7"
L592:     },
L593:     {
L594:       "kind": "visual",
L595:       "text": "将改写后的记录拆成五栏：时间、情境与参与人、可见动作、可听语言、尚未确认的信息；用箭头显示从原标签到事实要素的拆解过程。",
L596:       "unit_id": "u8",
L597:       "visual_function": "decomposition"
L598:     },
L599:     {
L600:       "kind": "interaction",
L601:       "text": "判断下面的改写是否合格：“小宇不太懂得分享，所以拿走了安安的积木。”如果不合格，请指出其中仍被当作事实的推测，并补出至少一个具体动作或一句原话。",
L602:       "unit_id": "u9"
L603:     },
L604:     {
L605:       "claim_refs": [
L606:         "clm_dfe3d7bcef@v1"
L607:       ],
L608:       "kind": "narration",
L609:       "text": "事实写清后，还要把推测和支持策略分开。事实栏只写本次能够看到、听到并复述的内容。推测栏可以保留教师的专业思考，但要使用“可能”“也可能”“需要后续观察”等标记，不能把解释写成已经确认的动机。支持策略栏则回答教师下一步准备怎样调整环境、示范表达、介入冲突或继续观察。三个栏目之间可以有关联，却不能相互替代。【待核验】将对幼儿内在动机或人格的判断写成事实，会降低观察记录的可用性；因此本课把动机解释明确放入推测栏，而不混入事实栏。",
L610:       "unit_id": "u10"
L611:     },
L612:     {
L613:       "case_ref": "case1",
L614:       "kind": "case",
L615:       "text": "仍以这一虚构案例为例。事实是：小宇拿起桥旁的两块长方形积木，把一块放进自己的篮子；安安说明积木用途后伸手拿取，小宇把篮子拉到身后；教师走近后，小宇把积木放回桌面。推测可以写：“小宇可能尚未找到合适的方式表达自己也需要长方形积木；也可能未理解安安正在使用这些积木。以上需要通过后续观察核验。”不能写成“小宇为了惹安安生气而抢积木”，因为现有记录没有确认这一动机。支持策略可以写：“下次活动前示范‘我也需要，可以一起用吗’；冲突发生时先复述双方说法，再帮助两名幼儿商量轮流、共用或寻找替代积木。”还可以同时记录小宇争抢和主动协商的情形，不预先用“调皮”筛选材料。",
L616:       "unit_id": "u11"
L617:     },
L618:     {
L619:       "kind": "visual",
L620:       "text": "三栏卡片依次显示：事实——现场可见可听；推测——可能的解释、等待核验；支持策略——教师下一步可实施的行动。将“他故意惹人生气”放入错误区。",
L621:       "unit_id": "u12",
L622:       "visual_function": "classification"
L623:     },
L624:     {
L625:       "kind": "interaction",
L626:       "text": "请把“他故意抢积木，因为他就是不愿意分享，所以要严厉管教”改写成三句话：第一句只写事实，第二句明确标为推测，第三句提出针对已记录行为的支持策略。",
L627:       "unit_id": "u13"
L628:     },
L629:     {
L630:       "claim_refs": [],
L631:       "kind": "narration",
L632:       "text": "最后进行迁移检查。无论是日常记录、教研讨论还是家园沟通，都先检查是否出现“这个孩子就是……”以及“调皮”“内向”“不听话”等人格化或贬义称谓；再检查是否写明时间、情境、参与人、具体动作和对话原文；随后确认所有动机或需要的解释都标为推测；最后核对支持策略是否针对已经记录的行为。若发现自己只记录了符合原有标签的片段，可以主动补记与标签不一致的表现，例如主动协商、等待或归还材料。完成这四步，记录呈现的是可复核的事件、待核验的理解和可执行的支持，而不是用一个称谓替代观察。",
L633:       "unit_id": "u14"
L634:     },
L635:     {
L636:       "kind": "interaction",
L637:       "text": "请选取自己的一则观察记录完成终检：删除人格化称谓；圈出时间、情境、参与人、动作和原话；给所有解释加上“推测”标记；确认支持策略对应具体行为。若缺少信息，请写“当时未记录，待后续观察”，不要补写未发生或记不清的内容。",
L638:       "unit_id": "u15"
L639:     }
L640:   ],
L641:   "word_count": {
L642:     "count": 1725,
L643:     "in_range": true,
L644:     "max": 1800,
L645:     "method": "unicode_non_whitespace_chars",
L646:     "min": 1500,
L647:     "scope_note": "统计教师讲解正文（含正文中讲述的案例），不计标题、画面指令、引用索引与独立备注"
L648:   }
L649: }
L650: ```
L651: 
L652: ## assessment:sec1
L653: 
L654: ```json
L655: {
L656:   "items": [
L657:     {
L658:       "answer": "B",
L659:       "assessment_id": "a1",
L660:       "claim_refs": [],
L661:       "distractors": [
L662:         "A将一次可观察行为解释为“自私”，属于人格评价，且未记录具体言行。",
L663:         "C使用“总是”“喜欢抢”“性格软弱”等概括和标签，无法由当前情境直接确认。",
L664:         "D对乐乐的动机、情绪和明明的感受作出推断，这些内容不能仅凭所述行为直接确认。"
L665:       ],
L666:       "kind": "hinge_question",
L667:       "options": [
L668:         "A.乐乐很自私，不愿意与同伴分享积木。",
L669:         "B.上午9:20，在建构区，乐乐和明明同时伸手拿一块积木。乐乐把积木拉向自己，说：“这是我先拿到的。”明明松开手，站在原地看着乐乐。",
L670:         "C.乐乐总是喜欢抢别人的东西，明明性格比较软弱。",
L671:         "D.乐乐因为害怕失去积木而生气，明明感到很委屈。"
L672:       ],
L673:       "question": "上午9:20，在幼儿园建构区，教师看到乐乐和明明同时伸手拿一块积木。以下哪一项最符合儿童真实行为记录的要求？",
L674:       "rationale": "B记录了具体时间、地点、参与人、可观察的动作和可听到的对话，不推断儿童的动机、情绪或人格，因此最具可核查性。A、C包含人格化评价或过度概括；D属于对内在状态的推测。若确需保留这些理解，应另行标注为“推测”，不能与行为事实混写。",
L675:       "student_viewable": true,
L676:       "target_goal": "g1"
L677:     },
L678:     {
L679:       "answer": "开放",
L680:       "assessment_id": "a2",
L681:       "kind": "reflection_prompt",
L682:       "question": "回想你近期观察到的一次[REDACTED]。先写出原本可能使用的含糊、评价性或推断性表述，再将其改写为一条可复核的行为记录，包含时间、地点、参与人、具体动作和对话原文；无法直接确认的动机或情绪请单独标注为“推测”。最后说明你删改了哪些标签或推断，以及这样修改的理由。",
L683:       "rationale": "用于检验学习者能否把观察规则迁移到真实情境中，区分可观察事实与推测，并将含糊或人格化表述改写为具体、不贴标签且可复核的记录。",
L684:       "student_viewable": true,
L685:       "target_goal": "g4"
L686:     }
L687:   ],
L688:   "section_id": "sec1"
L689: }
L690: ```
L691: 
L692: ## case:sec1:1
L693: 
L694: ```json
L695: {
L696:   "case_id": "case1",
L697:   "claim_refs": [],
L698:   "difficulty": "学习者需要在连续事件和混合陈述中筛选可直接看到、听到的信息，补全时间、情境、参与人、动作与对话原文，同时避免把“故意捣乱”“自私”等对动机或人格的判断写成事实，并将无法直接确认的理解单列为“推测”。",
L699:   "kind": "fictional",
L700:   "linked_goal": "g4",
L701:   "new_factual_claims": [],
L702:   "section_id": "sec1",
L703:   "text": "【观察情境】10月12日9:20，幼儿园活动室积木区。参与人：[REDACTED]、安安，教师陈老师。\n【事件】小宇把三块长方形积木叠在一起。安安伸手拿起最上面的一块。小宇看向安安，说：“这是我搭桥的。”安安说：“我也要用。”小宇从安安手中拿回积木，把积木放到自己身后。安安用手推了一下积木堆，积木倒在地垫上。小宇提高音量说：“你把我的桥弄倒了！”陈老师走到两人身边，说：“我看到积木倒了。请你们先告诉我刚才发生了什么。”\n【混合陈述】①9:20，小宇和安安在积木区。②安安故意捣乱。③安安推了一下积木堆，积木倒在地垫上。④小宇很自私，不愿意分享。⑤小宇说：“这是我搭桥的。”⑥小宇可能担心自己的搭建被改变。\n【学习任务】1. 从事件中提取时间、情境、参与人、具体动作和对话原文。2. 将混合陈述分为“可观察事实”和“待核验的推测或判断”，并说明能否直接看到或听到。3. 把“安安故意捣乱”和“小宇很自私”改写为具体、非标签化的行为记录。4. 按发生顺序完成一则简短观察记录，并把教师对儿童动机或情绪的理解单列为“推测”。\n【参考整理】可观察事实：①③⑤。待核验的推测或判断：②④⑥。改写示例：“安安故意捣乱”可改为“安安用手推了一下积木堆，积木倒在地垫上”；“小宇很自私，不愿意分享”可改为“小宇从安安手中拿回积木，把积木放到自己身后，并说：‘这是我搭桥的。’”推测示例：“小宇可能担心自己的搭建被改变。”该理解不能作为已发生的事实记录。",
L704:   "title": "积木区里发生了什么"
L705: }
L706: ```


## FILE benchmarks/reports/evaluation_kit/B-dynamic/course.md

L1: # B / dynamic
L2: 
L3: - run: run_8c3ffb4d0a85 status=succeeded
L4: - 模式：dynamic 实验：（无）
L5: - 模型调用：45 研究请求：33
L6: - 证据政策：['SUPPORTED']
L7: 
L8: > 评分说明见同目录 human_eval.yaml 与 benchmarks/reports/evaluation_kit/README.md
L9: 
L10: ## 自动检查命中的问题（请在 comment / must_fix 中说明是真问题还是误报）
L11: 
L12: | 类别 | 说明 |
L13: | --- | --- |
L14: | ROUTING | media_need=DIAGRAM，期望 STATIC |
L15: 
L16: ## 门禁结论（供教师核对，不是评分）
L17: 
L18: - **G8@export_manifest: NEEDS_REVIEW** — 渲染器可用但未生成缩略图，渲染级检查未完成
L19: 
L20: ## lesson_plan:sec1
L21: 
L22: ```json
L23: {
L24:   "board_design": "中心标题：心理学有什么用？\n左侧：研究什么——心理与行为；可观察、可询问、可收集信息、需证据。\n右侧：不等同于什么——读心、算命、贴标签、凭有限信息作个体诊断、快速解决一切问题。\n中部分析路径：可观察事实 → 可能解释 → 需要核验的信息；标签化判断单独标出并划线提醒“不是事实”。\n下部证据四问：说法是什么？证据来自哪里？适用于谁？在什么条件下成立？\n底部边界句式：心理学可能帮助我们……；但不能仅凭……就……；还需要核验……。",
L25:   "difficult_points": [
L26:     "纠正把心理学误解为读心术、性格标签或诊断他人工具的倾向，建立对心理学研究对象与方法边界的初步理解。",
L27:     "在说明心理学用途的同时，明确证据限制、适用条件与非诊断边界。",
L28:     "面对符合直觉或“看起来很准”的流行说法时，主动核查证据来源、适用人群和成立条件。",
L29:     "[REDACTED]具体技术的情况下，形成继续探索心理学的兴趣与问题意识。"
L30:   ],
L31:   "homework": [
L32:     "选择一则来自网络、影视、大众读物或日常交流的心理学说法，注明原始出处；若无法确认出处，明确标记“来源待核验”。",
L33:     "用“具体说法、已有证据、适用人群、成立条件、仍待核验的问题”五项框架完成分析；无法确认的信息统一标记为“待核验”，不得自行补充研究结论、来源或统计数据。",
L34:     "结合一个大[REDACTED]，分别写出一句“心理学可能提供的帮助”和一句“不能据此完成的事情”，避免给真实人物贴标签或作个体诊断。"
L35:   ],
L36:   "key_points": [
L37:     "心理学研究人的心理与行为，但不等同于读心、算命、贴标签或仅凭有限信息诊断个体。",
L38:     "分析大学生活情境时，先描述可观察事实，再提出待核验的可能解释，避免把解释当成事实或把标签当成结论。",
L39:     "审视心理学说法时，需要追问证据来源、适用人群、成立条件以及尚未核验的信息。",
L40:     "心理学可以提供观察视角、提问框架和研究方法，但不能保证快速解决所有问题，也不能替代基于充分信息的专业评估。"
L41:   ],
L42:   "objectives": [
L43:     {
L44:       "goal_ref": "g1",
L45:       "text": "能用自己的话说明心理学关注人的心理与行为，并辨析其与读心、算命、贴标签和个体诊断的区别；至少为两个判断提供理由。"
L46:     },
L47:     {
L48:       "goal_ref": "g2",
L49:       "text": "能分析大学生活案例，区分可观察事实、可能解释与标签化判断，并分别写出心理学可能提供的帮助及不能据此完成的事情。"
L50:     },
L51:     {
L52:       "goal_ref": "g3",
L53:       "text": "能区分个人经验、流行心理说法与需要证据支持的解释，并从证据来源、适用人群或成立条件中提出至少一个待核验问题。"
L54:     },
L55:     {
L56:       "goal_ref": "g4",
L57:       "text": "能说明心理学作为持续学习的方法体系所具有的用途与边界，并提出一个与自身大[REDACTED]、愿意继续探索的问题。"
L58:     }
L59:   ],
L60:   "preparation": [
L61:     "制作“心理学研究什么、不研究什么”判断卡，卡片内容仅包含可供辨析的问题或做法，不预设未经核验的研究结论。",
L62:     "准备两则大学生活案例，分别涉及学业、人际或心理适应情境；材料只呈现可观察行为与当事人自述，不提供诊断性标签。",
L63:     "制作“事实—可能解释—标签化判断—仍需信息”四栏学习单。",
L64:     "制作“心理学可能提供的帮助—不能据此完成的事情”边界学习单。",
L65:     "准备一则明确标注为“待核验说法”的示范材料及一则练习材料，不将其表述为已证实结论。",
L66:     "准备投票卡、便利贴、计时工具和离场卡。"
L67:   ],
L68:   "process": [
L69:     {
L70:       "intent": "激活已有经验，显化学生对心理学的初始印象，同时建立“接触过不等于已证实”的课堂意识，为后续辨析留下真实问题。",
L71:       "minutes": 10,
L72:       "stage": "0–10 分钟：经验唤醒——我曾在哪里遇见“心理学”",
L73:       "student_activity": "独立写下一个接触心理学的经历和当时形成的一个印象；与同伴交流后，选择一个印象贴到相应区域，并标注“个人经验”“听到的说法”或“来源待核验”。",
L74:       "teacher_activity": "呈现提示：“你曾从哪些地方接触到心理学？当时它被用来做什么？”邀请学生独立回忆后两人交流，并将回答按“网络或影视说法、个人经验、课程或研究信息、其他”暂时归类。教师说明这些类别只是课堂整理框架，不代表其中说法已经得到证实，也暂不判断真伪。"
L75:     },
L76:     {
L77:       "intent": "通过对比案例帮助学生建立心理学研究对象与非科学化想象、标签化判断及个体诊断之间的边界，以理由而非定义复述作为理解证据。",
L78:       "minutes": 15,
L79:       "stage": "10–25 分钟：建立课程边界——心理学研究什么、不研究什么",
L80:       "student_activity": "小组分类判断卡，至少选择两张写出理由；回答铰链问题，并根据讨论修订分类。学生使用“可否观察或收集信息、是否需要证据、是否越过个体诊断边界”等语言说明理由。",
L81:       "teacher_activity": "并列呈现判断卡，例如“研究大学生在不同学习情境中的可观察行为”“仅凭一次对话准确知道对方全部想法”“依据有限表现给同学贴人格标签”“研究人在特定情境中的感受、自述与行为”“未经评估便诊断某位同学”。要求小组按“属于心理学可以研究的问题”“不等同于心理学研究”“信息不足，需补充条件”分类。追问学生的判断依据，并用铰链问题检查：‘一个说法讨论人的心理，就一定是心理学结论吗？为什么？’"
L82:     },
L83:     {
L84:       "intent": "示范证据审视过程，使学生把“感觉准确”转化为可核验的问题，不把课堂中的示例说法误当成已确认的心理学事实。",
L85:       "minutes": 15,
L86:       "stage": "25–40 分钟：深度思考一——“看起来很准”就等于心理学结论吗",
L87:       "student_activity": "跟随示范标记“说法、证据、适用人群、成立条件”；独立或结对分析新材料，写出至少一个待核验问题，并说明个人经验为什么不能单独替代系统证据。",
L88:       "teacher_activity": "提供一则明确标记为“待核验”的流行心理说法，示范四步审视：确认它具体声称什么；询问证据来自哪里；询问适用于哪些人；询问在什么条件下成立。教师把无法从材料确认的内容标为“待核验”，随后提供一则新的待核验说法，让学生完成同构分析。"
L89:     },
L90:     {
L91:       "intent": "把心理学的价值定位为观察视角、提问框架与研究方法，同时明确其不能自动给出唯一解释、不能保证快速解决问题、不能凭有限材料诊断个体。",
L92:       "minutes": 15,
L93:       "stage": "40–55 分钟：用途地图——心理学如何帮助理解大学生活",
L94:       "student_activity": "选择一个与大学生活相关的情境，小组填写用途地图；分别写出一项心理学可能提供的帮助和一项不能据此完成的事情，并进行简短分享。",
L95:       "teacher_activity": "在画面上设置“学业、人际、心理适应”三个情境区，邀请学生提出大学生活中的常见问题。教师只把问题整理为可观察、可询问或可研究的表达，不提供未经核验的因果答案。引导学生填写“心理学可能帮助我们观察什么、提出什么问题、收集什么信息”和“不能仅凭这些信息完成什么”。"
L96:     },
L97:     {
L98:       "intent": "训练学生在真实情境中区分事实、解释和标签，抵制单一归因与个体诊断冲动，形成先描述、再询问、后核验的分析顺序。",
L99:       "minutes": 15,
L100:       "stage": "55–70 分钟：深度思考二——案例中的事实、解释与标签",
L101:       "student_activity": "使用四栏学习单完成案例分析；将“他就是懒惰”“他一定存在某种心理问题”等改写为不带诊断的待核验问题；小组比较不同可能解释，并明确不能依据当前材料确定人物状态。",
L102:       "teacher_activity": "呈现大学生活案例，例如某学生连续两次缺席小组讨论、提交任务较晚，并表示最近难以安排时间。教师要求学生先划出可观察事实，再把其他陈述分别放入“可能解释”“标签化判断”“仍需了解的信息”。对把解释写成定论或把人物贴标签的回答进行追问：“材料中的哪条信息支持它？还可能有什么解释？缺少什么信息？”"
L103:     },
L104:     {
L105:       "intent": "整合用途判断与证据意识，使[REDACTED]说明心理学的可能价值，也能指出其成立条件、信息限制和非诊断边界。",
L106:       "minutes": 12,
L107:       "stage": "70–82 分钟：深度思考三——心理学能帮到哪里，边界在哪里",
L108:       "student_activity": "完成双句任务并交换互评；依据检查表修改表述，例如提出需要进一步了解的问题、说明信息不足，避免承诺确定结果或替代专业评估。",
L109:       "teacher_activity": "延续案例，给出任务：“为该情境各写一句‘心理学可能提供的帮助’和‘不能据此完成的事情’。”组织小组互评，检查表包括：是否基于材料、是否标明待核验内容、是否避免诊断、是否说明所需条件或证据。教师汇总有边界的表达方式。"
L110:     },
L111:     {
L112:       "intent": "检验学生能否形成有边界的心理学价值定位，收集目标达成证据，并以个人相关的问题建立对后续课程的学习期待。",
L113:       "minutes": 8,
L114:       "stage": "82–90 分钟：回扣与离场评估——我的一个新理解和一个待探索问题",
L115:       "student_activity": "独立完成离场卡，写出一个有边界的新理解、一个愿意继续探索的问题及其与自身大学生活的联系，并指出至少一项仍需获取的证据、适用人群信息或成立条件。",
L116:       "teacher_activity": "回扣导入时的初始印象，邀请学生完成离场卡：“我现在认为心理学可以……但不能……”“我愿意继续探索的问题是……”“它与我的大学生活的联系是……”“核验这个问题还需要……”。收集离场卡，作为后续教学调整依据。"
L117:     }
L118:   ],
L119:   "section_id": "sec1",
L120:   "title": "90 分钟《大学生心理健康教育》现场课：心理学有什么用"
L121: }
L122: ```
L123: 
L124: ## slide_plan
L125: 
L126: ```json
L127: {
L128:   "rows": [
L129:     {
L130:       "asset_geometry": "全幅标题区，副标题置于下方",
L131:       "asset_handling": "仅作课程主题与结构依据，不作为研究证据",
L132:       "claim_refs": [],
L133:       "communication_task": "建立课程主题与学习预期",
L134:       "core_message": "以心理学视角理解大学生活，同时尊重证据与应用边界。",
L135:       "density": "low",
L136:       "layout_archetype": "cover",
L137:       "narrative_section": "课程导入",
L138:       "notes": "开场说明本课关注理解方法、生活应用和证据意识，不进行个体诊断。",
L139:       "points": [
L140:         "90分钟现场课",
L141:         "理解心理与行为",
L142:         "联系大学生活",
L143:         "辨别说法与证据"
L144:       ],
L145:       "risk": "用户材料来源层级有限；不呈现未经核验的事实性结论",
L146:       "section_id": "sec1",
L147:       "slide": 1,
L148:       "source_asset": "mat1",
L149:       "title": "大学生心理健康教育"
L150:     },
L151:     {
L152:       "asset_geometry": "居中标题，上下分区呈现学习路径",
L153:       "asset_handling": "提炼教学目标，不扩展为研究结论",
L154:       "claim_refs": [],
L155:       "communication_task": "呈现本节学习路径与课堂产出",
L156:       "core_message": "本课从概念边界、生活应用、证据核验走向持续探索。",
L157:       "density": "low",
L158:       "layout_archetype": "section_title",
L159:       "narrative_section": "学习目标",
L160:       "notes": "说明课堂将通过四幅图示逐步推进，并邀请学生联系自己的校园经验。",
L161:       "points": [
L162:         "认识心理学的边界",
L163:         "分析大学生活情境",
L164:         "提出证据核验问题",
L165:         "形成持续探索意识"
L166:       ],
L167:       "risk": "避免将课程目标表述为学习效果保证",
L168:       "section_id": "sec1",
L169:       "slide": 2,
L170:       "source_asset": "mat1",
L171:       "title": "从好奇出发，学习一种理解方法"
L172:     },
L173:     {
L174:       "asset_geometry": "主体图示居中，占页面约三分之二；底部放边界提醒",
L175:       "asset_handling": "原样使用已校验矢量图，保留标题与比较关系",
L176:       "claim_refs": [],
L177:       "communication_task": "比较心理学与容易混淆的做法",
L178:       "core_message": "学习心理学需要区分系统理解与读心、算命、贴标签或个体诊断。",
L179:       "density": "medium",
L180:       "diagram_id": "d1",
L181:       "layout_archetype": "diagram",
L182:       "narrative_section": "概念边界",
L183:       "notes": "请学生说出曾见过的混淆情形，再依据图示讨论哪些做法越过了边界。",
L184:       "points": [
L185:         "关注心理与行为",
L186:         "不等同于读心",
L187:         "不用于算命",
L188:         "不随意贴标签",
L189:         "不替代个体诊断"
L190:       ],
L191:       "risk": "不得借图示判断具体个人，也不将边界说明冒充研究结论",
L192:       "section_id": "sec1",
L193:       "slide": 3,
L194:       "source_asset": "d1",
L195:       "title": "心理学不是什么？"
L196:     },
L197:     {
L198:       "asset_geometry": "横向流程图占页面主体，学业、人际、适应情境分列起点",
L199:       "asset_handling": "使用矢量图展示情境到方法的转换，不增加因果结论",
L200:       "claim_refs": [],
L201:       "communication_task": "示范从大学生活情境进入心理学方法",
L202:       "core_message": "心理学视角可以帮助整理问题，但具体解释仍需观察、提问与核验。",
L203:       "density": "medium",
L204:       "diagram_id": "d2",
L205:       "layout_archetype": "diagram",
L206:       "narrative_section": "生活应用",
L207:       "notes": "邀请[REDACTED]、人际或适应中选择一个情境，把笼统困惑改写成可进一步探索的问题。",
L208:       "points": [
L209:         "从具体情境开始",
L210:         "描述可观察现象",
L211:         "提出可能解释",
L212:         "寻找核验方法",
L213:         "保留解释边界"
L214:       ],
L215:       "risk": "避免暗示单一方法能快速解决所有心理困扰",
L216:       "section_id": "sec1",
L217:       "slide": 4,
L218:       "source_asset": "d2",
L219:       "title": "把生活困惑转化为可探索的问题"
L220:     },
L221:     {
L222:       "asset_geometry": "矩阵图居中放大，右侧设置核验问题提示区",
L223:       "asset_handling": "原样使用证据核验矩阵；不采用未获支持或需限定的评估内容",
L224:       "claim_refs": [],
L225:       "communication_task": "比较个人经验、流行说法与待核验解释",
L226:       "core_message": "不同心理说法需要区分来源、适用范围与可核验程度。",
L227:       "density": "medium",
L228:       "diagram_id": "d3",
L229:       "layout_archetype": "diagram",
L230:       "narrative_section": "证据辨别",
L231:       "notes": "给出一个不带结论的校园流行说法，让学生按图示提出核验问题；不要求当场判定真假。",
L232:       "points": [
L233:         "这是谁的经验",
L234:         "来源是否清楚",
L235:         "适用于哪些人",
L236:         "有没有其他解释",
L237:         "如何进一步核验"
L238:       ],
L239:       "risk": "相关文字证据评估未达到直接使用条件，具体结论均标记为待核验",
L240:       "section_id": "sec1",
L241:       "slide": 5,
L242:       "source_asset": "d3",
L243:       "title": "面对心理说法，先问证据在哪里"
L244:     },
L245:     {
L246:       "asset_geometry": "左右对照图占页面主体，下方设置个人探索问题区",
L247:       "asset_handling": "使用矢量对照图突出两种定位，不补充未经核验的成效描述",
L248:       "claim_refs": [],
L249:       "communication_task": "通过正反定位形成应用态度",
L250:       "core_message": "心理学更适合作为持续观察、提问和修正理解的方法，而非诊断他人的快捷工具。",
L251:       "density": "medium",
L252:       "diagram_id": "d4",
L253:       "layout_archetype": "diagram",
L254:       "narrative_section": "学习定位",
L255:       "notes": "请学生比较两种学习定位，并写下自己愿意继续探索的一个心理学问题。",
L256:       "points": [
L257:         "不急于诊断他人",
L258:         "不追求万能答案",
L259:         "持续观察与提问",
L260:         "根据证据修正理解",
L261:         "尊重个人与情境差异"
L262:       ],
L263:       "risk": "避免承诺心理学能够快速解决所有问题或准确判断他人",
L264:       "section_id": "sec1",
L265:       "slide": 6,
L266:       "source_asset": "d4",
L267:       "title": "把心理学当作持续学习的方法"
L268:     },
L269:     {
L270:       "asset_geometry": "中央呈现四步回顾路径，底部设置离场问题",
L271:       "asset_handling": "仅提炼四幅图示的共[REDACTED]，不重复复杂图形",
L272:       "claim_refs": [],
L273:       "communication_task": "回顾学习主线并形成个人行动",
L274:       "core_message": "从辨清边界开始，把生活困惑转为问题，用证据意识持续探索。",
L275:       "density": "low",
L276:       "layout_archetype": "closing",
L277:       "narrative_section": "总结与离场",
L278:       "notes": "用一分钟回顾四步路径。请学生提交一个仍想探索的问题，以及使用心理学时需要守住的一条边界。",
L279:       "points": [
L280:         "辨清心理学边界",
L281:         "连接真实生活情境",
L282:         "核验心理说法",
L283:         "保持持续学习",
L284:         "写下一个探索问题"
L285:       ],
L286:       "risk": "总结不加入新的事实性结论；学生个人问题不作现场诊断",
L287:       "section_id": "sec1",
L288:       "slide": 7,
L289:       "source_asset": "d1,d2,d3,d4",
L290:       "title": "带走一个问题，也带走一条边界"
L291:     }
L292:   ]
L293: }
L294: ```
L295: 
L296: ## pptx_deck
L297: 
L298: ```json
L299: {
L300:   "delivery_check": {},
L301:   "engine": "python-pptx（原生形状/表格/备注）",
L302:   "families": [
L303:     "comparison",
L304:     "cover",
L305:     "section",
L306:     "summary"
L307:   ],
L308:   "path": "C:\\Users\\admin\\Documents\\ChatGPT\\心理学教育skills\\projects\\bench-b-dynamic-084324\\media\\pptx\\90 分钟《大学生心理健康教育》现场课：.pptx",
L309:   "qa": {
L310:     "checks": [
L311:       {
L312:         "check": "开箱可解析",
L313:         "detail": "7 页",
L314:         "status": "PASS"
L315:       },
L316:       {
L317:         "check": "原生可编辑对象",
L318:         "detail": "形状 99，表格 0，连接线 22",
L319:         "status": "PASS"
L320:       },
L321:       {
L322:         "check": "内部术语",
L323:         "detail": "",
L324:         "status": "PASS"
L325:       },
L326:       {
L327:         "check": "溢出启发式检查",
L328:         "detail": "",
L329:         "status": "PASS"
L330:       },
L331:       {
L332:         "check": "真实渲染",
L333:         "detail": "C:\\Program Files\\LibreOffice\\program\\soffice.exe，7 张缩略图",
L334:         "status": "PASS"
L335:       }
L336:     ],
L337:     "issues": [],
L338:     "jargon_hits": [],
L339:     "overflow_suspects": [],
L340:     "status": "PASS"
L341:   },
L342:   "renderer": "C:\\Program Files\\LibreOffice\\program\\soffice.exe",
L343:   "sha256": "631c3b6581be2d60c25752d250064040f8a3fc18d4296f99eb1f315ab683ef4e",
L344:   "slides": [
L345:     {
L346:       "citation_labels": [],
L347:       "family": "cover",
L348:       "layout": "cover",
L349:       "notes_chars": 31,
L350:       "section_id": "sec1",
L351:       "slide_id": "slide1",
L352:       "title": "大学生心理健康教育"
L353:     },
L354:     {
L355:       "citation_labels": [],
L356:       "family": "section",
L357:       "layout": "section_title",
L358:       "notes_chars": 31,
L359:       "section_id": "sec1",
L360:       "slide_id": "slide2",
L361:       "title": "从好奇出发，学习一种理解方法"
L362:     },
L363:     {
L364:       "citation_labels": [],
L365:       "family": "comparison",
L366:       "layout": "diagram",
L367:       "notes_chars": 31,
L368:       "section_id": "sec1",
L369:       "slide_id": "slide3",
L370:       "title": "心理学不是什么？"
L371:     },
L372:     {
L373:       "citation_labels": [],
L374:       "family": "comparison",
L375:       "layout": "diagram",
L376:       "notes_chars": 39,
L377:       "section_id": "sec1",
L378:       "slide_id": "slide4",
L379:       "title": "把生活困惑转化为可探索的问题"
L380:     },
L381:     {
L382:       "citation_labels": [],
L383:       "family": "comparison",
L384:       "layout": "diagram",
L385:       "notes_chars": 39,
L386:       "section_id": "sec1",
L387:       "slide_id": "slide5",
L388:       "title": "面对心理说法，先问证据在哪里"
L389:     },
L390:     {
L391:       "citation_labels": [],
L392:       "family": "comparison",
L393:       "layout": "diagram",
L394:       "notes_chars": 32,
L395:       "section_id": "sec1",
L396:       "slide_id": "slide6",
L397:       "title": "把心理学当作持续学习的方法"
L398:     },
L399:     {
L400:       "citation_labels": [],
L401:       "family": "summary",
L402:       "layout": "closing",
L403:       "notes_chars": 44,
L404:       "section_id": "sec1",
L405:       "slide_id": "slide7",
L406:       "title": "带走一个问题，也带走一条边界"
L407:     }
L408:   ],
L409:   "stats": {
L410:     "connectors": 22,
L411:     "pictures": 0,
L412:     "shapes": 99,
L413:     "slides": 7,
L414:     "tables": 0,
L415:     "text_boxes": 77
L416:   },
L417:   "template_used": "",
L418:   "thumbnails": [
L419:     "C:\\Users\\admin\\Documents\\ChatGPT\\心理学教育skills\\projects\\bench-b-dynamic-084324\\media\\pptx\\thumbs\\slide1.png",
L420:     "C:\\Users\\admin\\Documents\\ChatGPT\\心理学教育skills\\projects\\bench-b-dynamic-084324\\media\\pptx\\thumbs\\slide2.png",
L421:     "C:\\Users\\admin\\Documents\\ChatGPT\\心理学教育skills\\projects\\bench-b-dynamic-084324\\media\\pptx\\thumbs\\slide3.png",
L422:     "C:\\Users\\admin\\Documents\\ChatGPT\\心理学教育skills\\projects\\bench-b-dynamic-084324\\media\\pptx\\thumbs\\slide4.png",
L423:     "C:\\Users\\admin\\Documents\\ChatGPT\\心理学教育skills\\projects\\bench-b-dynamic-084324\\media\\pptx\\thumbs\\slide5.png",
L424:     "C:\\Users\\admin\\Documents\\ChatGPT\\心理学教育skills\\projects\\bench-b-dynamic-084324\\media\\pptx\\thumbs\\slide6.png",
L425:     "C:\\Users\\admin\\Documents\\ChatGPT\\心理学教育skills\\projects\\bench-b-dynamic-084324\\media\\pptx\\thumbs\\slide7.png"
L426:   ]
L427: }
L428: ```


## FILE benchmarks/reports/evaluation_kit/C-dynamic/course.md

L1: # C / dynamic
L2: 
L3: - run: run_ec5bff2ee0c1 status=succeeded
L4: - 模式：dynamic 实验：（无）
L5: - 模型调用：48 研究请求：12
L6: - 证据政策：['SUPPORTED']
L7: 
L8: > 评分说明见同目录 human_eval.yaml 与 benchmarks/reports/evaluation_kit/README.md
L9: 
L10: ## 门禁结论（供教师核对，不是评分）
L11: 
L12: - **G1@script:sec1: PASS**
L13: - **G1@script:sec2: PASS**
L14: - **G1@script:sec3: PASS**
L15: - **G1@script:sec4: PASS**
L16: - **G2@script:sec1: FAIL** — 存在待核验占位内容，事实性陈述尚未通过 Evidence Gate
L17: - **G2@script:sec2: PASS**
L18: - **G2@script:sec3: FAIL** — 存在待核验占位内容，事实性陈述尚未通过 Evidence Gate；引用了未获支持的 Claim：clm_949ec8536b@v3（状态 QUALIFY_REQUIRED）
L19: - **G2@script:sec4: PASS**
L20: - **G3@script:sec1: FAIL** — 缺少学习目标；缺少评价证据（目标—评价对应）；缺少 PCK 教学说明
L21: - **G3@script:sec2: FAIL** — 缺少学习目标；缺少评价证据（目标—评价对应）；缺少 PCK 教学说明
L22: - **G3@script:sec3: FAIL** — 缺少学习目标；缺少评价证据（目标—评价对应）；缺少 PCK 教学说明
L23: - **G3@script:sec4: FAIL** — 缺少学习目标；缺少评价证据（目标—评价对应）；缺少 PCK 教学说明
L24: - **G4@script:sec1: PASS**
L25: - **G4@script:sec2: PASS**
L26: - **G4@script:sec3: PASS**
L27: - **G4@script:sec4: PASS**
L28: - **G5@script:sec1: FAIL** — 缺少 UDL 障碍与替代路径分析
L29: - **G5@script:sec2: FAIL** — 缺少 UDL 障碍与替代路径分析
L30: - **G5@script:sec3: FAIL** — 缺少 UDL 障碍与替代路径分析
L31: - **G5@script:sec4: FAIL** — 缺少 UDL 障碍与替代路径分析
L32: - **G6@script:sec1: NEEDS_REVIEW** — 媒体选型未运行，无法确认视觉与动画决策
L33: - **G6@script:sec2: NEEDS_REVIEW** — 媒体选型未运行，无法确认视觉与动画决策
L34: - **G6@script:sec3: NEEDS_REVIEW** — 媒体选型未运行，无法确认视觉与动画决策
L35: - **G6@script:sec4: NEEDS_REVIEW** — 媒体选型未运行，无法确认视觉与动画决策
L36: - **G7@script:sec1: NOT_APPLICABLE**
L37: - **G7@script:sec2: NOT_APPLICABLE**
L38: - **G7@script:sec3: NOT_APPLICABLE**
L39: - **G7@script:sec4: NOT_APPLICABLE**
L40: 
L41: ## lesson_plan:sec1
L42: 
L43: ```json
L44: {
L45:   "board_design": "标题：8.1 办托理念与价值体系构建\n一、核心问题：我们相信什么？每天具体怎样做？如何知道做到了？\n二、概念链条：办托理念 → 核心价值 → 服务承诺 → 工作流程 → 岗位职责 → 检查要点 → 反馈修订\n三、服务承诺四要素：对象｜行动｜情境｜检查方式\n四、价值审视三维度：安全｜尊重｜回应性互动\n五、案例检查五类证据：理念表述｜员工行为｜工作流程｜岗位职责｜服务体验\n六、价值冲突判断：婴[REDACTED]、尊严与发展需要 → 比较方案 → 作出选择 → 说明依据\n角标提示：未经核验的事实性判断标记“待核验”。",
L46:   "difficult_points": [
L47:     "避免把办托理念停留在宣传口号层面，将抽象价值转化为可观察、可执行、可检查的服务承诺。",
L48:     "将安全、尊重、回应性互动等价值要求逐项对应到每日流程和不同岗位职责。",
L49:     "在经营效率、家长即时诉求与婴幼儿利益发生张力时，保持价值判断与实际决策一致。",
L50:     "评价理念落实情况时，不只检查制度文本，还要分析员工行为与婴幼儿的实际服务体验。"
L51:   ],
L52:   "homework": [
L53:     "选择入园接待、进餐、午睡、交接班或家园沟通中的一个场景，完成一份不少于三行的“核心价值—服务承诺—工作流程—岗位职责—检查要点”对应表。",
L54:     "选取一条常见的机构宣传语，将其改写为分别体现安全、尊重和回应性互动的三条服务承诺；每条承诺须写明服务对象、具体行动、适用情境和检查方式。",
L55:     "根据课堂案例修订改进方案，明确责任岗位、执行动作、完成时点和检查证据；如引用事实性资料，注明来源，无法确认的内容标记为“待核验”。"
L56:   ],
L57:   "key_points": [
L58:     "办托理念是机构对“为何办托、以何种价值作出管理和服务选择”的基本立场；价值体系用于把这一立场转化为服务承诺、工作流程、岗位职责和检查要点。",
L59:     "宣传性口号与服务承诺的区别：服务承诺需要明确服务对象、具体行动、适用情境和检查方式。",
L60:     "从安全、尊重和回应性互动三个方面审视办托理念及其落实情况。",
L61:     "运用“核心价值—服务承诺—工作流程—岗位职责—检查要点”对应表，将抽象价值逐级转化为具体要求。",
L62:     "评价理念落实情况时，同时审视制度文本、员工实际行为和婴幼儿及家长的服务体验。"
L63:   ],
L64:   "objectives": [
L65:     {
L66:       "goal_ref": "g1",
L67:       "text": "能用自己的语言解释办托理念与价值体系，并举例说明其如何通过管理沟通、每日流程和岗位行为影响机构服务。"
L68:     },
L69:     {
L70:       "goal_ref": "g2",
L71:       "text": "能辨别宣传性口号与可执行服务承诺，并从安全、尊重和回应性互动三个方面，将口号改写为至少三条可观察、可执行、可检查的服务承诺。"
L72:     },
L73:     {
L74:       "goal_ref": "g3",
L75:       "text": "能按照“明确核心价值—形成服务承诺—对应每日流程—落实岗位职责—设置检查要点”的步骤，独立完成一份价值体系对应表。"
L76:     },
L77:     {
L78:       "goal_ref": "g4",
L79:       "text": "能在经营目标、家长诉求与专业照护要求发生冲突的情境中作出选择，并说明该选择如何维护婴幼儿的安全、尊严与发展需要。"
L80:     },
L81:     {
L82:       "goal_ref": "g5",
L83:       "text": "能依据理念表述、员工行为、工作流程、岗位职责和服务体验等信息，识别至少一处理念与实践的不一致，并提出可执行、可检查的改进方案。"
L84:     }
L85:   ],
L86:   "preparation": [
L87:     "制作包含机构宣传语、服务承诺和工作要求的对比材料；其中情境与表述仅作为课堂练习材料，不作为研究结论。",
L88:     "准备“核心价值—服务承诺—工作流程—岗位职责—检查要点”完整示例表、半成品表和空白表。",
L89:     "准备涉及入园接待、进餐、午睡、交接班、家园沟通等场景的流程卡与岗位卡。",
L90:     "准备一则“理念表述与实际服务脱节”的虚构案例及案例证据卡。",
L91:     "准备包含经营目标、家长诉求与专业照护要求冲突的虚构管理情境卡。",
L92:     "准备投影、白板、便签纸、计时工具和课堂评价量表。",
L93:     "对课程中拟使用的事实性材料和来源进行课前复核；无法确认的内容统一标记为“待核验”。"
L94:   ],
L95:   "process": [
L96:     {
L97:       "intent": "激活学习者对托育机构基本职能和服务场景的已有认识，引出办托理念必须进入日常管理与服务行为的问题。",
L98:       "minutes": 8,
L99:       "stage": "导入：机构选择情境",
L100:       "student_activity": "独立选择更便于判断服务行为的机构，并用一句话说明依据；与同伴比较各自关注的是口号、行动还是检查证据。",
L101:       "teacher_activity": "呈现两家虚构托育机构的简介：一家只有“让每个孩子快乐成长”等宣传语，另一家同时列出具体服务承诺。提出问题：“如果你是家长或管理者，仅凭这些信息能判断机构每天会怎样做吗？”收集判断依据，不把案例结局表述为普遍事实。"
L102:     },
L103:     {
L104:       "intent": "建立统一概念框架，支持学习者理解理念与日常管理之间的联系，并避免将未经核验的关联当作研究结论。",
L105:       "minutes": 12,
L106:       "stage": "概念讲授：办托理念与价值体系",
L107:       "student_activity": "根据讲授完成概念关系简图，并用自己的语言解释办托理念与价值体系的作用；各写出一个理念影响日常管理的例子。",
L108:       "teacher_activity": "明确说明办托理念、核心价值、服务承诺、工作流程、岗位职责和检查要点的课程含义，并用“理念—管理选择—流程与职责—可观察行为—检查与修订”链条组织概念。以晨会、交接班、复盘和管理层沟通为示例说明理念如何进入日常行为；对于理念转化与服务质量之间更一般的关联，明确标记为“待核验”。"
L109:     },
L110:     {
L111:       "intent": "及时识别学习者是否仍把理念文本等同于理念落实，并据答题情况决定是否补充讲解。",
L112:       "minutes": 5,
L113:       "stage": "检查理解：关键判断题",
L114:       "student_activity": "作出选择并说明理由，列举需要补充查看的服务承诺、流程、岗位行为或体验证据。",
L115:       "teacher_activity": "呈现判断题：“某机构墙上写有‘尊重每个孩子’，因此可以认定该机构已经形成并落实了尊重儿童的价值体系。”要求全班同时选择“能认定”“不能认定”或“信息不足”，并追问还需要哪些证据。"
L116:     },
L117:     {
L118:       "intent": "通过对比案例形成辨别标准，突破抽象口号难以操作化的难点。",
L119:       "minutes": 12,
L120:       "stage": "对比辨析：口号与服务承诺",
L121:       "student_activity": "小组标出两类表述的差异；将一个宣传口号改写为至少三条服务承诺，并分别注明可观察行为和检查方式。",
L122:       "teacher_activity": "并列呈现宣传性口号和包含对象、行动、情境、检查方式的服务承诺，引导学习者使用四项标准进行标注。组织从安全、尊重和回应性互动三个方面审视表述。"
L123:     },
L124:     {
L125:       "intent": "提供程序性知识的完整范例，降低初次建构对应表的认知负担。",
L126:       "minutes": 12,
L127:       "stage": "示范建构：完整对应表",
L128:       "student_activity": "跟随示范核对各栏是否相互对应，指出示例中核心价值如何转化为流程动作和岗位责任，并提出一项可替换的检查方式。",
L129:       "teacher_activity": "示范填写一行完整对应表：选定一个核心价值，依次形成服务承诺、对应一个每日流程、明确相关岗位职责并设置检查要点。逐步口述每一栏之间的逻辑关系，提醒检查要点应描述可以观察或记录的内容。"
L130:     },
L131:     {
L132:       "intent": "逐步撤去支持，帮助学习者把价值要求稳定地映射到流程、岗位与检查要求。",
L133:       "minutes": 10,
L134:       "stage": "渐隐练习：补全对应关系",
L135:       "student_activity": "两人合作补全服务承诺、工作流程、岗位职责和检查要点；根据反馈修订至少一处表述。",
L136:       "teacher_activity": "发放删除部分栏目内容的半成品表，只保留核心价值和部分情境提示；巡视并针对“行动过于笼统”“职责主体不明确”“检查内容不可观察”等问题给予反馈。"
L137:     },
L138:     {
L139:       "intent": "检验学习者能否独立运用构建步骤，并形成可作为学习证据的完整作品。",
L140:       "minutes": 12,
L141:       "stage": "独立应用：构建价值体系表",
L142:       "student_activity": "独立完成“核心价值—服务承诺—工作流程—岗位职责—检查要点”对应表，并依据“是否具体、是否对应、是否可执行、是否可检查”进行自评。",
L143:       "teacher_activity": "提供空白表和入园接待、进餐、午睡、交接班、家园沟通等可选场景，要求学习者独立完成至少一组完整对应关系；使用评价量表进行快速检查。"
L144:     },
L145:     {
L146:       "intent": "训练从多类证据评价理念落实情况，避免只检查制度文本，并提升改进建议的可操作性。",
L147:       "minutes": 12,
L148:       "stage": "案例分析：理念与实践脱节",
L149:       "student_activity": "小组填写案例分析单，定位至少一处不一致，说明判断证据，并提出包含责任人、行动、实施情境和检查方式的改进方案。",
L150:       "teacher_activity": "呈现虚构案例：机构宣称重视尊重与回应，但案例中的员工沟通方式、流程安排或职责执行与表述存在不一致。引导学习者依次审查理念、行为、流程、职责和服务体验证据，不预设情境结局。"
L151:     },
L152:     {
L153:       "intent": "促进以婴幼儿利益为中心的价值判断，使办托立场能够在现实张力中指导决策。",
L154:       "minutes": 10,
L155:       "stage": "价值冲突判断与反思",
L156:       "student_activity": "个人作出选择并写出价值依据；小组讨论替代方案，检查决定是否维护婴幼儿的安全、尊严与发展需要，同时说明如何回应家长和机构管理需求。",
L157:       "teacher_activity": "呈现虚构情境：家长要求立即满足某项安排，机构同时面临经营效率压力，而一线人员认为该安排可能不符合当前照护要求。使用固定问题引导：“谁的需要受到影响？安全、尊严和发展需要分别如何被考虑？有哪些替代方案？如何说明决定？”强调情境选择不代表已经研究验证的普遍结果。"
L158:     },
L159:     {
L160:       "intent": "通过提取练习整合本节知识，快速收集目标达成证据，并强化证据意识。",
L161:       "minutes": 7,
L162:       "stage": "总结与出口评价",
L163:       "student_activity": "独立完成出口卡，并写下一项自己仍需核验或进一步学习的问题。",
L164:       "teacher_activity": "回扣“价值—承诺—流程—职责—检查—修订”主线，要求学习者完成出口卡：解释一个概念差异、写出一条服务承诺、指出一个检查要点。说明涉及事实判断但尚未核验的内容应标记为“待核验”。"
L165:     }
L166:   ],
L167:   "section_id": "sec1",
L168:   "title": "8.1 办托理念与价值体系构建"
L169: }
L170: ```
L171: 
L172: ## lesson_plan:sec2
L173: 
L174: ```json
L175: {
L176:   "board_design": "中心标题：文化建设从理念进入日常行为\n主线：办托理念 → 日常仪式 → 沟通行为 → 管理层示范 → 定期复盘 → 改进安排\n左侧｜仪式设计六要素：目的、频率、参与人员、操作步骤、责任人、执行证据\n中部｜行为化改写：抽象理念 → 具体场景 → 可观察行为 → 确认方式\n右侧｜案例诊断：问题 → 案例证据 → 对应措施 → 责任人 → 复盘检查\n底部提醒：标语展示不等同于日常落实；示例适用性与文化、制度、宣传的具体边界需结合机构情境进一步核验。",
L177:   "difficult_points": [
L178:     "将抽象文化理念转化为晨会、交接班和复盘中的具体流程、责任分工与可观察行为。",
L179:     "理解管理层示范是文化建设的组成部分，并使管理者的沟通方式与机构倡导的价值保持一致。",
L180:     "在保持日常仪式稳定实施的同时，识别并减少口号宣读、机械打卡和形式化记录；其具体判断标准需结合机构情境进一步核验。",
L181:     "辨析文化建设、制度管理和宣传展示之间的联系与边界；具体边界结论需结合课程依据进一步核验。"
L182:   ],
L183:   "homework": [
L184:     "选择一个虚拟或熟悉的托育机构情境，完成一份文化建设方案，必须包含晨会、交接班和复盘机制，并分别写明实施频率、参与人员、操作步骤、责任人及执行证据。",
L185:     "从机构倡导的文化理念中选择至少一项，将其改写为两条可观察、可执行的行为要求：一条用于婴幼儿照护或[REDACTED]，一条用于同事协作。",
L186:     "制定一组管理层沟通示范要求，至少覆盖尊重、清晰和一致性，并为每项要求写出可观察的判断依据。",
L187:     "为方案补充一次复盘设计，写明复盘时间、参与者、检查材料、核心提问、改进事项记录方式和跟进责任人；涉及机构实际规定但尚无依据的内容标记为“待核验”。"
L188:   ],
L189:   "key_points": [
L190:     "文化建设需要落实到晨会、交接班、复盘和日常沟通等具体工作场景。",
L191:     "日常文化仪式的设计应明确实施频率、参与人员、操作步骤和责任人。",
L192:     "将尊重、清晰和回应性等抽象要求转化为可观察、可执行的沟通行为。",
L193:     "通过管理层的日常沟通示范，使其行为与机构倡导的文化要求保持一致。",
L194:     "通过定期复盘检查文化建设措施是否实际执行，并形成后续改进安排。"
L195:   ],
L196:   "objectives": [
L197:     {
L198:       "goal_ref": "g1",
L199:       "text": "对比“标语展示”与“日常行为落实”两类情境，指出托育机构文化建设在晨会、交接班、复盘和日常沟通中的具体表现。"
L200:     },
L201:     {
L202:       "goal_ref": "g2",
L203:       "text": "设计一份包含晨会、交接班和复盘机制的文化建设方案，明确各项机制的实施频率、参与人员、操作步骤和责任人。"
L204:     },
L205:     {
L206:       "goal_ref": "g3",
L207:       "text": "将至少一项抽象文化理念改写为管理者与员工在婴幼儿照护或同事协作中可观察、可执行的沟通行为要求。"
L208:     },
L209:     {
L210:       "goal_ref": "g4",
L211:       "text": "分析“墙上有标语但日常沟通混乱”的案例，识别日常仪式、沟通规则和管理层示范中的主要问题，并提出相互对应的改进措施。"
L212:     }
L213:   ],
L214:   "preparation": [
L215:     "准备两则对比情境材料：一则突出标语展示，另一则呈现晨会、交接班、复盘和沟通规则的日常落实。",
L216:     "准备“日常文化仪式设计表”，设置事项、目的、频率、参与人员、操作步骤、责任人、执行证据和复盘安排等栏目。",
L217:     "准备抽象理念行为化改写卡片，内容包括尊重、清晰、回应性和一致性。",
L218:     "准备管理者与员工沟通的正反示例，以及角色演练任务卡。",
L219:     "准备“墙上有标语但日常沟通混乱”的案例材料和“问题—证据—措施—责任人”分析表。",
L220:     "准备课堂评价清单，用于检查方案的完整性、行为要求的可观察性及问题与措施的对应性。"
L221:   ],
L222:   "process": [
L223:     {
L224:       "intent": "激活已有经验，引导学生从关注口号展示转向关注日常行为落实。",
L225:       "minutes": 8,
L226:       "stage": "导入：情境对比",
L227:       "student_activity": "阅读情境，分别标记“墙面展示”和“日常行为”证据，并用一句话说明哪类证据更能显示文化要求是否进入日常工作。",
L228:       "teacher_activity": "呈现两则托育机构情境：情境一仅展示文化标语，但晨会内容随意、交接信息不清、管理者要求前后不一；情境二将文化要求写入晨会、交接班、复盘和沟通规则。引导学生圈出两则情境中能够直接观察到的差异，不补充材料之外的效果结论。"
L229:     },
L230:     {
L231:       "intent": "帮助学生建立文化建设与日常管理行为相联系的分析视角，同时避免把尚未核验的边界判断当作确定事实。",
L232:       "minutes": 10,
L233:       "stage": "概念辨析：文化如何进入日常管理",
L234:       "student_activity": "完成分类并说明理由，修正仅凭标语数量判断文化建设情况的表述，记录本课分析框架。",
L235:       "teacher_activity": "组织结构化讨论，要求学生将案例要素暂分为“宣传展示”“制度或流程”“日常文化行为”三类，并提示三者的具体边界需依据课程材料和机构情境继续核验。归纳本课分析框架：理念—仪式—沟通行为—管理层示范—复盘改进。"
L236:     },
L237:     {
L238:       "intent": "通过完整范例呈现程序性任务的基本结构，为后续独立设计提供支架。",
L239:       "minutes": 15,
L240:       "stage": "示范：拆解完整文化仪式方案",
L241:       "student_activity": "依据评价清单检查示例是否包含必要要素，指出其中可直接执行的安排，并提出需要结合机构规模或岗位设置调整的部分。",
L242:       "teacher_activity": "展示一份教学用示例，逐项示范如何为晨会、交接班和复盘填写目的、频率、参与人员、操作步骤、责任人、执行证据和后续处理。追问每一步由谁完成、何时完成、如何看出已经完成。说明示例仅作为流程设计范本，不作为适用于所有机构的固定标准。"
L243:     },
L244:     {
L245:       "intent": "逐步撤除提示，使[REDACTED]把文化理念转化为稳定、明确的日常流程。",
L246:       "minutes": 15,
L247:       "stage": "渐隐练习：设计晨会与交接班",
L248:       "student_activity": "小组协作补全设计表，用“谁在何时做什么、留下什么可检查的信息”的句式检验方案，并根据反馈修改。",
L249:       "teacher_activity": "发放部分留白的设计表，只保留事项和目的，要求小组补全晨会与交接班的频率、参与人员、步骤、责任人和执行证据。巡视并针对责任不明确、步骤不可操作或频率表述含糊之处给予反馈。"
L250:     },
L251:     {
L252:       "intent": "检验学生能否独立设计复盘流程，并将复盘用于检查实际执行和推动改进。",
L253:       "minutes": 12,
L254:       "stage": "独立练习：设计复盘机制",
L255:       "student_activity": "独立完成复盘机制，并写出两项复盘提问，例如“约定行为是否出现”“未执行发生在哪一环节”“下一步由谁在何时调整”。",
L256:       "teacher_activity": "撤除流程提示，要求学生独立设计定期复盘机制，至少写明复盘频率、参与人员、主持或责任人、信息来源、操作步骤、形成的改进事项及跟进责任。提醒学生区分“完成记录”与“检查措施是否真正执行”。"
L257:     },
L258:     {
L259:       "intent": "训练学生把抽象文化要求转化为具体行为规范。",
L260:       "minutes": 10,
L261:       "stage": "行为化改写：从理念到要求",
L262:       "student_activity": "选择至少一项理念，分别改写为婴幼儿照护或同事协作中的可执行行为，互相判断是否能够直接观察和实施。",
L263:       "teacher_activity": "示范把“要尊重同事”改写为包含场景、行为、对象和可观察结果的要求，再提供尊重、清晰、回应性等理念供[REDACTED]。对“态度要好”“加强沟通”等不可观察表述进行追问。"
L264:     },
L265:     {
L266:       "intent": "让学生在具体沟通情境中练习管理层示范，并用行为证据检验文化要求的一致性。",
L267:       "minutes": 12,
L268:       "stage": "角色演练：管理层沟通示范",
L269:       "student_activity": "分角色扮演管理者、员工和观察员；观察员依据清单记录可观察行为，演练者根据反馈再次表达。",
L270:       "teacher_activity": "设置交接遗漏、工作分歧或任务调整等场景，要求扮演管理者的学生示范尊重、清晰和一致的沟通。观察是否说明事实与任务、确认理解、给予回应机会，并保持要求前后一致。"
L271:     },
L272:     {
L273:       "intent": "整合流程设计、行为化要求和管理示范知识，形成基于案例证据的针对性改进方案。",
L274:       "minutes": 15,
L275:       "stage": "案例分析：诊断形式化问题",
L276:       "student_activity": "小组完成诊断表，至少识别一个主要问题，为每个问题提出对应措施，并说明如何通过后续复盘判断措施是否得到执行。",
L277:       "teacher_activity": "发放“墙上有标语但日常沟通混乱”的案例，要求学生分别检查日常仪式、沟通规则、管理层示范和复盘机制。引导学生按照“问题—案例证据—改进措施—责任人—检查方式”建立对应关系。"
L278:     },
L279:     {
L280:       "intent": "通过展示、反馈和修订巩固学习成果，检查各项目标的达成情况。",
L281:       "minutes": 8,
L282:       "stage": "展示反馈与总结",
L283:       "student_activity": "展示方案，依据评价标准进行同伴反馈，完成一次修改，并写下一条本节课最重要的操作原则。",
L284:       "teacher_activity": "邀请小组展示方案，依据四项标准反馈：要素是否完整、行为是否可观察、问题与措施是否对应、复盘是否能够检查执行。最后回扣“理念—仪式—沟通行为—管理层示范—复盘改进”框架。"
L285:     }
L286:   ],
L287:   "section_id": "sec2",
L288:   "title": "8.2 文化建设的策略"
L289: }
L290: ```
L291: 
L292: ## lesson_plan:sec3
L293: 
L294: ```json
L295: {
L296:   "board_design": "中心标题：员工行为规范与服务礼仪\n左侧：判断依据——安全｜尊重｜回应性互动｜沟通边界\n中部：理念/承诺 → 服务情境 → 可观察行为 → 责任主体 → 记录与交接 → 后续反馈\n右上：家长回应五步——确认诉求 → 陈述事实 → 标明未知/待核实 → 说明职责范围 → 明确反馈节点\n右下：案例分析链——不当行为 → 风险 → 判断依据 → 改进措施 → 责任主体 → 后续反馈\n底部检查项：看得见｜说得清｜不越界｜可追溯",
L297:   "difficult_points": [
L298:     "将“尊重”“专业”等抽象价值转化为可以观察、执行和复盘的员工行为条款。",
L299:     "在保持礼貌与积极回应的同时守住家长沟通边界，避免模糊表述、越权判断或无法兑现的承诺。",
L300:     "理解服务礼仪重在可预期和尊重，而非机械套用话术或追求过度形式化。",
L301:     "在综合情境中同步处理婴[REDACTED]、[REDACTED]、同事协作、信息记录与交接责任。"
L302:   ],
L303:   "homework": [
L304:     "修订课堂完成的员工行为规范清单，确保覆盖婴[REDACTED]、[REDACTED]、同事协作与交接；每项使用可观察行为表述，并标明责任主体、执行要求及必要的记录或反馈方式。",
L305:     "根据给定的虚构服务冲突案例，完成“不当行为—风险—判断依据—改进措施—责任主体—后续反馈”分析表；无法从课程材料确认的判断须标注“待核验”。",
L306:     "编写一段家长问题回应脚本，分别标注事实告知、专业建议、待核实信息和职责边界，不得作出越权或无法兑现的承诺。",
L307:     "选择一项服务礼仪要求，用不超过200字说明其如何体现机构办托理念；若所依据的机构理念或服务承诺尚未确认，须明确标注“待核验”。"
L308:   ],
L309:   "key_points": [
L310:     "员工行为规范与服务礼仪的核心要求：行为可预期、互动有尊重。",
L311:     "依据安全、尊重与回应性互动原则判断并修正员工的语言、动作与照护回应。",
L312:     "把接待、沟通、交接和反馈要求转化为具体、可观察、可执行和可复盘的行为条款。",
L313:     "在家长沟通中区分事实告知、专业建议与越界承诺。",
L314:     "将婴[REDACTED]、[REDACTED]、同事协作与交接纳入连续、可追溯的行为规范。"
L315:   ],
L316:   "objectives": [
L317:     {
L318:       "goal_ref": "g1",
L319:       "text": "能用具体服务情境解释“可预期和尊重”的含义，并说明至少一项礼仪要求与机构办托理念、服务承诺之间的对应关系。"
L320:     },
L321:     {
L322:       "goal_ref": "g2",
L323:       "text": "能依据安全、尊重与回应性互动原则，识别婴幼儿照护中的不当语言、动作和回应，说明风险并提出可观察的修正行为。"
L324:     },
L325:     {
L326:       "goal_ref": "g3",
L327:       "text": "能围绕接待、沟通、交接和反馈情境，制定包含具体行为、责任主体、执行要求、记录方式与反馈要求的员工行为规范清单。"
L328:     },
L329:     {
L330:       "goal_ref": "g4",
L331:       "text": "能在家长沟通角色演练中区分事实告知、专业建议与越界承诺，并作出尊重、清楚且边界明确的回应。"
L332:     },
L333:     {
L334:       "goal_ref": "g5",
L335:       "text": "能分析涉及婴[REDACTED]、家长沟通和同事交接的综合案例，形成“不当行为—风险—判断依据—改进措施—责任主体—后续反馈”的完整改进方案。"
L336:     }
L337:   ],
L338:   "preparation": [
L339:     "办托理念与服务承诺摘录卡；如机构尚未明确相关内容，则使用标注为“课堂假设、待核验”的练习材料。",
L340:     "婴幼儿互动对比案例卡，案例条件保持相近，分别呈现不同的语言、动作和回应方式。",
L341:     "员工行为规范清单模板，栏目包括服务情境、可观察行为、禁止行为、责任主体、执行要求、记录方式和反馈要求。",
L342:     "家长沟通角色卡，分别设置事实询问、专业建议请求、投诉质疑和越权承诺诱因。",
L343:     "综合冲突案例材料及“不当行为—风险—判断依据—改进措施—责任主体—后续反馈”分析表。",
L344:     "交接记录练习单，栏目包括关键信息、已完成事项、待办事项、责任主体、完成时限和反馈要求。",
L345:     "计时器、展示板或投影设备、同伴观察与反馈量表。"
L346:   ],
L347:   "process": [
L348:     {
L349:       "intent": "激活已有经验，引出服务礼仪不能只看表面话术，需要同时考察尊重、事实清晰度、行为边界和服务可预期性。",
L350:       "minutes": 5,
L351:       "stage": "导入：礼貌是否等于专业",
L352:       "student_activity": "比较两段接待片段，记录选择及理由，并圈出可以直接观察到的语言和行为。",
L353:       "teacher_activity": "呈现两段虚构接待片段：一段措辞热情但信息含糊并作出越权承诺，另一段表达克制但事实、责任和反馈安排清楚。要求学生先独立选择更符合服务要求的一段，不公布标准答案。"
L354:     },
L355:     {
L356:       "intent": "达成g1，使学生从价值口号转向可观察行为，同时避免把待核验关联表述为确定事实。",
L357:       "minutes": 12,
L358:       "stage": "引导反思：从办托理念到员工行为",
L359:       "student_activity": "小组匹配卡片，将“尊重”“专业”等抽象表述改写为具体行为，并选取一项礼仪要求说明其如何体现办托理念，而非仅说明形式要求。",
L360:       "teacher_activity": "提供办托理念、服务承诺与员工行为三类卡片，引导学生逐项建立对应关系；追问“这一理念在现场能被看到或听到什么”。明确提示：理念转化与服务质量之间的关联属于待核验内容，不作为本课既定研究结论。"
L361:     },
L362:     {
L363:       "intent": "达成g2，训练学生依据明确原则分析行为差异，并将抽象判断转化为可执行的修正方案。",
L364:       "minutes": 15,
L365:       "stage": "对比案例：婴幼儿互动规范",
L366:       "student_activity": "比较案例中的语言、动作和回应，指出不当行为，依据安全、尊重或回应性互动原则说明理由，并把修正建议写成可观察的动作或语言。",
L367:       "teacher_activity": "依次呈现条件相近、回应方式不同的婴幼儿互动案例，引导学生按“看到什么—可能有什么风险—依据哪项原则—如何修正”分析，不接受仅以“我觉得不好”为依据的判断。"
L368:     },
L369:     {
L370:       "intent": "为g3提供完整范例，使学生掌握规范条款的构成及改写方法。",
L371:       "minutes": 12,
L372:       "stage": "示范：行为规范条款的形成",
L373:       "student_activity": "跟随示范完成首个条款，标出原表述中不可观察、责任不清或无法复盘的部分，并提出修改建议。",
L374:       "teacher_activity": "以一个虚构的晨间接待与交接情境为例，示范依次填写“情境—行为—责任主体—执行要求—记录—反馈”，并展示如何把“态度友好”等模糊表述改成可观察条款。说明晨会、交接班和复盘机制与日常行为落实的关系依据已核验材料clm_c1482d4ee6，但不扩展材料未提供的结论。"
L375:     },
L376:     {
L377:       "intent": "达成g3，通过逐步独立完成任务，形成可执行、可检查和可复盘的规范清单。",
L378:       "minutes": 15,
L379:       "stage": "渐隐练习：制定员工行为规范清单",
L380:       "student_activity": "小组完成覆盖婴[REDACTED]、[REDACTED]、同事协作与交接的行为规范清单；每项均写明具体行为、责任主体、执行要求，并补充必要的记录或反馈要求。",
L381:       "teacher_activity": "先提供部分栏目提示，再逐步撤除提示；巡视各组，重点追问行为是否可观察、责任是否明确、记录与反馈是否闭环。"
L382:     },
L383:     {
L384:       "intent": "达成g4，让学生在变化情境中练习事实告知、专业建议与越界承诺的区分，并根据反馈即时修正。",
L385:       "minutes": 18,
L386:       "stage": "技能演练：家长接待与问题回应",
L387:       "student_activity": "完成至少两轮接待与回应；观察员依据“表达尊重、事实清楚、边界明确、不作越权承诺”记录行为证据，演练者根据反馈调整表达。",
L388:       "teacher_activity": "组织三人轮换角色演练：员工、家长、观察员。分轮加入信息不完整、家长追问专业判断、要求立即承诺等变化条件；提示使用“确认诉求—陈述已知事实—说明未知或待核实内容—给出职责范围内安排—明确反馈节点”的回应结构。"
L389:     },
L390:     {
L391:       "intent": "达成g5，促使学生把互动、沟通、协作和交接纳入同一条连续、可追溯的改进链。",
L392:       "minutes": 18,
L393:       "stage": "综合案例分析：冲突与规范修正",
L394:       "student_activity": "填写“不当行为—风险—判断依据—改进措施—责任主体—后续反馈”分析表，并将案例中的交接信息整理为关键信息、待办事项、责任主体和反馈要求。",
L395:       "teacher_activity": "提供同时涉及婴[REDACTED]、[REDACTED]、同事交接的虚构冲突案例，要求各组形成完整证据链；追问改进措施由谁执行、如何记录、何时反馈。案例可设置管理者沟通示范因素，其使用依据为已核验材料clm_9888f312b7，不扩展材料未提供的结论。"
L396:     },
L397:     {
L398:       "intent": "整合本课学习证据，检查学生能否解释理念、判断行为、制定规范、完成沟通并提出综合改进方案。",
L399:       "minutes": 10,
L400:       "stage": "展示互评与课堂总结",
L401:       "student_activity": "展示成果，依据四项标准提出一条有证据的肯定意见和一条具体修改建议；个人完成退出卡，写出一项礼仪要求与办托理念的关系及一条边界清楚的[REDACTED]。",
L402:       "teacher_activity": "抽取小组展示规范条款和案例分析，组织同伴使用“是否可观察、是否有依据、是否守边界、是否能追溯”四项标准互评；汇总常见问题并回扣五项目标。"
L403:     }
L404:   ],
L405:   "section_id": "sec3",
L406:   "title": "8.3 员工行为规范与服务礼仪建设"
L407: }
L408: ```
L409: 
L410: ## lesson_plan:sec4
L411: 
L412: ```json
L413: {
L414:   "board_design": "中心标题：品牌形象与口碑传播管理\n左侧：品牌体验分析链——服务接触点→服务事实→家长感受→可能的品牌评价；标注“事实与推测分开”“单一案例不等于普遍问题”。\n中部：投诉与反馈闭环——问题记录→问题处理→结果反馈→定期复盘→流程改进；每一步对应“依据、责任人、时限、记录”。\n右侧：方案判断四问——是否有记录或反馈依据？是否改善实际服务？是否可执行并与服务承诺一致？是否存在过度承诺？\n底部：口碑建议表达框架——依据什么记录或反馈→改进什么服务→如何如实沟通→哪些信息待核验。",
L415:   "difficult_points": [
L416:     "将抽象的品牌形象还原为家长在多个服务接触点形成的连续体验，而不是把品牌管理等同于宣传设计。",
L417:     "在投诉情境中同时做到完整记录、及时处理、结果反馈和后续复盘，避免只解决当下问题而遗漏流程闭环。",
L418:     "面对负面反馈时保持尊重和改进导向，避免急于辩解、掩饰问题或作出无法落实的承诺。",
L419:     "把个别反馈转化为流程改进线索，同时避免在证据不足时将单一案例概括为普遍问题。"
L420:   ],
L421:   "homework": [
L422:     "选择一个模拟托育服务场景，完成一份品牌服务接触点清单；至少列出五个接触点，并分别说明其可能影响家长体验的具体方式。",
L423:     "根据课堂提供的投诉案例，修订并提交完整闭环方案，必须包含问题记录、处理措施、责任人、完成时限、结果反馈和复盘安排；证据不足的信息标记为“待核验”。",
L424:     "分别拟定一项服务改进措施和一项口碑传播措施，依据服务记录、可执行性、与服务承诺的一致性及是否过度承诺说明二者的区别。"
L425:   ],
L426:   "key_points": [
L427:     "品牌形象需要结合家长在连续服务接触点中的实际体验进行理解，不能等同于宣传设计。",
L428:     "从婴[REDACTED]、[REDACTED]、投诉处理等情境中识别关键服务接触点及其可能影响。",
L429:     "投诉与反馈处理应包含问题记录、问题处理、结果反馈和定期复盘。",
L430:     "依据服务记录判断措施是否真正改善服务，并提出与机构服务承诺一致、可执行且不过度承诺的口碑传播建议。"
L431:   ],
L432:   "objectives": [
L433:     {
L434:       "goal_ref": "g1",
L435:       "text": "结合服务情境，说明家长实际体验与机构品牌评价之间的可能关系，并指出品牌建设不能仅依赖宣传表达。"
L436:     },
L437:     {
L438:       "goal_ref": "g2",
L439:       "text": "识别婴[REDACTED]、家长沟通和投诉处理等服务接触点，分别描述服务事实、家长感受及其可能产生的品牌影响。"
L440:     },
L441:     {
L442:       "goal_ref": "g3",
L443:       "text": "按照问题记录、问题处理、结果反馈和定期复盘四个环节，独立设计一份投诉与反馈闭环处理方案。"
L444:     },
L445:     {
L446:       "goal_ref": "g4",
L447:       "text": "依据服务记录、可执行性、与服务承诺的一致性及是否过度承诺，区分服务改进措施与单纯宣传措施，并提出可落实的口碑传播建议。"
L448:     }
L449:   ],
L450:   "preparation": [
L451:     "服务接触点清单模板，栏目包括接触点、服务事实、家长可能感受、可能影响和改进线索。",
L452:     "家长负面反馈案例材料，明确标注其中的模拟信息，避免将案例内容当作普遍事实。",
L453:     "投诉与反馈闭环记录表，栏目包括问题记录、处理措施、责任人、完成时限、结果反馈和复盘安排。",
L454:     "两组对比方案材料：一组侧重基于记录改进服务，另一组仅调整宣传表达。",
L455:     "评价检查表，指标包括证据依据、流程完整性、可执行性、承诺一致性和是否过度承诺。"
L456:   ],
L457:   "process": [
L458:     {
L459:       "intent": "激活学生区分宣传表达、服务事实与家长感受的已有知识，把注意力引向真实服务体验。",
L460:       "minutes": 5,
L461:       "stage": "导入：品牌评价从哪里形成",
L462:       "student_activity": "独立圈画宣传表达与服务事实，写出一个可能影响家长评价的具体经历，并说明判断依据。",
L463:       "teacher_activity": "呈现同一机构的宣传语与一段模拟家长服务经历，要求学生暂不判断机构整体优劣，只标出宣传表达和实际经历中的信息差异；提出问题：家长可能依据哪些具体经历形成评价？"
L464:     },
L465:     {
L466:       "intent": "落实g1，形成以真实服务体验为基础的品牌管理意识，同时训练审慎表达。",
L467:       "minutes": 8,
L468:       "stage": "引导反思：品牌形象与真实体验",
L469:       "student_activity": "根据案例完成“事实—感受—可能评价”三栏记录，修正缺少证据或过度概括的表述，并口头说明品牌建设为何不能仅依赖宣传。",
L470:       "teacher_activity": "组织学生依次讨论服务事实、家长感受和品牌评价之间的可能联系，提醒使用“可能”“在该情境下”等限定表达，不把单一案例推断为普遍结论。"
L471:     },
L472:     {
L473:       "intent": "落实g2，将抽象品牌形象还原为多个连续服务接触点中的具体体验。",
L474:       "minutes": 12,
L475:       "stage": "案例分析：识别关键服务接触点",
L476:       "student_activity": "小组完成服务接触点清单，至少从婴[REDACTED]、家长沟通和投诉处理三个方面进行分析，并说明各接触点可能影响家长体验的具体方式。",
L477:       "teacher_activity": "发放包含入园接待、日常照护、离园沟通和意见反馈等环节的模拟案例，引导学生按“接触点—服务事实—家长感受—可能影响”进行标注；对事实与推测混淆之处追问依据。"
L478:     },
L479:     {
L480:       "intent": "深化g2，培养基于情境证据分析负面反馈的能力，避免无依据归因。",
L481:       "minutes": 10,
L482:       "stage": "案例讨论：负面反馈的影响路径",
L483:       "student_activity": "绘制简要影响链，标注哪些内容有案例证据、哪些属于待核验信息；讨论哪些回应可能缓解问题，哪些回应可能造成新的体验问题。",
L484:       "teacher_activity": "选取案例中的一条家长负面反馈，组织学生梳理事件、沟通过程、机构回应及可能后续影响；提示区分案例中已给出的事实、家长表达的感受和学生作出的推测。"
L485:     },
L486:     {
L487:       "intent": "为g3提供完整范例，使学生理解投诉处理不仅要解决当下问题，还要形成可追踪、可复盘的闭环。",
L488:       "minutes": 10,
L489:       "stage": "示范：投诉与反馈闭环流程",
L490:       "student_activity": "对照闭环记录表标注示例中的四个环节，指出每个环节解决的问题，并找出可能导致流程中断的位置。",
L491:       "teacher_activity": "展示一个完整的模拟处理范例，逐项说明问题记录、问题处理、结果反馈和定期复盘的填写要求；示范如何记录事实、确认诉求、明确责任与时限，并避免辩解、掩饰或无法落实的承诺。"
L492:     },
L493:     {
L494:       "intent": "逐步撤去支架，帮助学生掌握完整投诉与反馈处理程序。",
L495:       "minutes": 12,
L496:       "stage": "渐隐练习：补全处理方案",
L497:       "student_activity": "小组补全问题记录、处理措施、责任人、完成时限、结果反馈和复盘安排，并用检查表进行互评修改。",
L498:       "teacher_activity": "提供删去部分步骤提示的新案例，要求各组补全处理方案；巡视并针对记录不完整、措施不具体、反馈对象不明确或缺少复盘安排等问题给予提示。"
L499:     },
L500:     {
L501:       "intent": "检验g3达成情况，形成可独立执行的程序性能力。",
L502:       "minutes": 10,
L503:       "stage": "独立实践：设计闭环方案",
L504:       "student_activity": "独立完成投诉案例的记录、处理、结果反馈与复盘方案，并检查是否包含全部流程环节以及可执行的责任和时限。",
L505:       "teacher_activity": "提供一则新的简短投诉情境，仅保留基本事实和待核验信息，要求[REDACTED]完成闭环方案；提醒不得把待核验信息写成确定事实。"
L506:     },
L507:     {
L508:       "intent": "落实g4，使学生能够区分真实服务改进与单纯宣传，避免仅凭措辞作判断。",
L509:       "minutes": 12,
L510:       "stage": "对比案例：真实改进还是单纯宣传",
L511:       "student_activity": "逐项判断方案属于服务改进、宣传措施或需要补充证据后再判断，并写出判断依据；对有争议的项目进行小组论证。",
L512:       "teacher_activity": "并列呈现两类模拟方案：一类依据服务记录调整流程，另一类只修改宣传用语；组织学生依据证据、可执行性、承诺一致性和是否过度承诺进行比较。"
L513:     },
L514:     {
L515:       "intent": "把案例分析、闭环处理和批判性判断整合为可执行的口碑管理方案。",
L516:       "minutes": 8,
L517:       "stage": "迁移任务：形成口碑管理建议",
L518:       "student_activity": "提出一项服务改进建议和一项口碑传播建议，说明所依据的记录或反馈；将证据不足的判断标记为“待核验”。",
L519:       "teacher_activity": "要求各组基于前述接触点清单和反馈记录提出口碑传播建议，并用评价检查表审查建议是否可落实、是否与服务承诺一致、是否存在过度承诺。"
L520:     },
L521:     {
L522:       "intent": "整合学习内容并收集目标达成证据，为课后练习提供方向。",
L523:       "minutes": 3,
L524:       "stage": "总结与评价",
L525:       "student_activity": "完成出口检核并自评四项目标的达成情况，标记仍需练习的环节。",
L526:       "teacher_activity": "围绕“体验来源、关键接触点、闭环流程、改进判断”四个关键词回顾本课，布置出口检核：写出一个接触点、一个闭环缺失风险和一条不过度承诺的建议。"
L527:     }
L528:   ],
L529:   "section_id": "sec4",
L530:   "title": "8.4 品牌形象与口碑传播管理"
L531: }
L532: ```
L533: 
L534: ## script:sec1
L535: 
L536: ```json
L537: {
L538:   "section_id": "sec1",
L539:   "template_ref": "d08a307545d44e54a0d58a0282bf3f6640384f5d6eb23de26cb111ac7be3131b",
L540:   "title": "8.1 办托理念与价值体系构建",
L541:   "units": [
L542:     {
L543:       "kind": "title",
L544:       "text": "8.1 办托理念与价值体系构建",
L545:       "unit_id": "u1"
L546:     },
L547:     {
L548:       "claim_refs": [
L549:         "clm_c1482d4ee6@v1",
L550:         "clm_9888f312b7@v1"
L551:       ],
L552:       "kind": "narration",
L553:       "placeholder": true,
L554:       "text": "面对两家托育机构，你会依据什么作出选择？一家写着“让爱伴随成长”，另一家不仅说明重视安全、尊重与回应性互动，还明确员工在入园、进餐、午睡、离园等情境中应当怎样做、由谁负责、留下什么记录。两者的差别在于：前者主要表达愿望，后者开始把价值转化为管理要求。本节把“办托理念”界定为机构对“为什么办托、以什么为优先、希望怎样对待婴幼儿”的基本主张；把“价值体系”界定为从核心价值出发，逐层形成服务承诺、工作流程、岗位职责和检查要点的一组对应关系。愿景描述机构希望走向哪里，工作目标说明阶段性结果，具体工作要求则回答员工在某个情境中应当做什么。办托理念不能代替流程，但可以为流程设计和管理判断提供价值基准。稳定实施晨会、交接班和复盘，并建立明确的沟通规则，有助于将机构文化落实到员工的日常行为。管理层的日常沟通示范也会影响员工沟通方式与机构文化要求的一致性。至于理念转化与日常管理或服务质量之间是否存在更一般的关联，其方向、机制和程度均为【待核验】。",
L555:       "unit_id": "u2"
L556:     },
L557:     {
L558:       "kind": "visual",
L559:       "text": "画面呈现五级阶梯：核心价值→服务承诺→工作流程→岗位职责→检查要点；阶梯旁分别标注“重视什么、承诺做什么、何时怎样做、谁来做、如何确认”。",
L560:       "unit_id": "u3",
L561:       "visual_function": "structure"
L562:     },
L563:     {
L564:       "kind": "interaction",
L565:       "text": "快速判断：下面哪一项最接近办托理念？A.本月完成三次培训；B.以婴幼儿的安全、尊严与发展需要作为管理判断的优先基准；C.午睡记录在当天填写。请选择并说明另外两项分别更接近什么。参考判断：B是理念，A是阶段性工作目标，C是具体工作要求。",
L566:       "unit_id": "u4"
L567:     },
L568:     {
L569:       "claim_refs": [],
L570:       "kind": "narration",
L571:       "text": "宣传口号与服务承诺的关键差异，不在于语言是否动听，而在于能否回答四个问题：服务对象是谁？员工要采取什么行动？行动适用于什么情境？通过什么信息检查执行情况？例如，“尊重每一名婴幼儿”仍较抽象。可以把它改写为：“在更衣、进餐和午睡准备中，照护人员先用适合当下情境的语言或动作提示婴幼儿，观察其表达后再提供协助；交接记录检查是否写明婴幼儿的反应与处理过程。”这项承诺指明了对象、行动、情境与检查方式。审视表述时，可以使用三个视角。安全视角关注流程是否识别并处理当下风险；尊重视角关注员工是否看见婴幼儿的表达，是否避免只用服从评价幼儿；回应性互动视角关注员工是否观察、回应并根据现场表现调整行动。这三个视角在本课中是分析框架，不被表述为未经提供材料支持的研究结论。",
L572:       "unit_id": "u5"
L573:     },
L574:     {
L575:       "kind": "visual",
L576:       "text": "左右对照卡：左侧“用爱陪伴成长”；右侧“四问改写器——对象、行动、情境、检查方式”。下方以安全、尊重、回应性互动三个观察镜头审视承诺。",
L577:       "unit_id": "u6",
L578:       "visual_function": "contrast"
L579:     },
L580:     {
L581:       "kind": "interaction",
L582:       "text": "口号改写：请将“安全第一”改成一条可执行承诺。完成后逐项勾选：是否写明对象、行动、适用情境和检查方式？若缺少任一项，继续修改。",
L583:       "unit_id": "u7"
L584:     },
L585:     {
L586:       "claim_refs": [],
L587:       "kind": "narration",
L588:       "text": "构建价值体系可以按五步进行。第一步，明确核心价值，并说明发生冲突时什么应当优先。第二步，把每项价值写成可观察的服务承诺，避免只使用“关爱、专业、用心”等难以检查的词。第三步，将承诺放入每日流程，指出入园、进餐、午睡、游戏、离园或家园沟通中的触发情境与处理步骤。第四步，落实岗位职责，明确谁观察、谁行动、谁记录、谁在需要时复盘。第五步，设计检查要点，检查实际行为和服务体验，而不只检查制度文本是否存在。一个完整示例如下：核心价值是“尊重”；服务承诺是“午睡准备时先观察并回应婴幼儿对衣物或安抚物的表达”；工作流程是“提示—等待表达—确认需要—提供协助—记录特殊表现”；照护人员负责观察、回应和记录，班组负责人负责查看异常记录并组织复盘；检查要点包括是否有事前提示、是否记录表达和处理、交接信息是否完整。随后可以撤去部分栏目练习：给出核心价值和承诺，由学习者补充流程、职责与检查点；最后只给出一个价值冲突情境，独立完成整张对应表。",
L589:       "unit_id": "u8"
L590:     },
L591:     {
L592:       "kind": "visual",
L593:       "text": "呈现可填写的五列表格，列名依次为“核心价值、服务承诺、工作流程、岗位职责、检查要点”；第一行展示完整范例，第二行遮去后三列，第三行全部留白。",
L594:       "unit_id": "u9",
L595:       "visual_function": "worked_example_fading"
L596:     },
L597:     {
L598:       "case_ref": "case1",
L599:       "claim_refs": [
L600:         "clm_007501ee22@v2"
L601:       ],
L602:       "kind": "case",
L603:       "text": "【虚构案例】晨光托育机构在宣传栏中写着“安全第一、尊重每一名婴幼儿、用爱陪伴成长”。为提高午睡准备效率，班级规定所有婴幼儿必须在十分钟内完成如厕、换衣和上床。某日，一名婴幼儿不愿立即脱下外套，并用动作表示想继续抱着安抚巾。照护人员一边说“要听话，大家都在等你”，一边直接拿走安抚巾、脱下外套，将其抱到床上。另一名照护人员发现该婴幼儿持续哭泣，但因岗位职责中只写了“按时完成午睡准备”，没有进一步回应。交接班记录仅填写“午睡流程按时完成”，未记录婴幼儿的表现及工作人员的处理过程。家长接回时询问婴幼儿为何情绪低落，工作人员回答“今天有点不配合”，机构也没有记录或复盘此次沟通。分析时先区分材料性质：宣传栏中的三句话都是抽象价值表述，尚未提供具体行动、情境和检查方式。再沿五列定位脱节：承诺没有操作化；统一时限的流程没有写明如何处理个体表达；岗位职责只要求按时完成；记录只检查进度，没有呈现婴幼儿的表现和处理过程；家长得到的是概括性评价，相关沟通也未进入复盘。家长对托育机构相关服务的实际体验，可能与其对机构品牌的评价有关，因此案例分析不能只查看宣传文本，还需审视家长实际接触到的服务信息。",
L604:       "unit_id": "u10"
L605:     },
L606:     {
L607:       "kind": "interaction",
L608:       "text": "案例任务一：从安全、尊重和回应性互动三个方面，各找出至少一处理念与实际行为的不一致。再判断问题分别位于服务承诺、流程、岗位职责、检查方式还是服务体验。",
L609:       "unit_id": "u11"
L610:     },
L611:     {
L612:       "claim_refs": [
L613:         "clm_c1482d4ee6@v1",
L614:         "clm_9888f312b7@v1"
L615:       ],
L616:       "kind": "narration",
L617:       "text": "针对案例，“尊重每一名婴幼儿”可以形成三条承诺。第一，在更衣和午睡准备中，照护人员先提示即将进行的步骤，观察婴幼儿的语言、动作或情绪表达后再协助；检查记录中是否包含提示、表达和处理。第二，婴幼儿对安抚物或身体接触表示拒绝、迟疑时，照护人员暂停当前动作，确认当下需要并按机构已明确的安全要求处理；班组负责人抽查异常情况记录是否完整。第三，婴幼儿持续哭泣或状态发生明显变化时，当班人员进行回应并向交接人员说明表现与处理过程；交接检查是否同时记录行为表现、员工行动和后续关注事项。这些承诺不是关于所有托育情境的研究结论，而是依据本案例形成的管理练习答案。相应改进包括：把固定时限改为流程目标与个别情况处理规则并列；补充观察、回应、记录和复盘责任；交接班不只记录是否按时完成；管理者在晨会和复盘中使用尊重、具体、非标签化的沟通方式进行示范。",
L618:       "unit_id": "u12"
L619:     },
L620:     {
L621:       "kind": "interaction",
L622:       "text": "案例任务二：请完成“核心价值—服务承诺—工作流程—岗位职责—检查要点”对应表。自检标准：每一项承诺都能在流程中找到落点；每一步都有责任岗位；每个检查点都能通过记录、观察或沟通信息进行判断。",
L623:       "unit_id": "u13"
L624:     },
L625:     {
L626:       "claim_refs": [],
L627:       "kind": "narration",
L628:       "text": "最后处理价值冲突：如果“按时完成午睡准备”与“回应婴幼儿当下需要”发生张力，管理者不能只在效率和照护之间作口头选择，而要说明决定及其边界。本案例中的可操作决定是：保留午睡准备的时间安排，但允许当婴幼儿出现拒绝、迟疑或持续哭泣时启动个别回应步骤；由一名照护人员继续支持班级流程，另一名照护人员观察、回应并记录，班组负责人随后复盘流程和职责是否需要调整。判断决定是否价值一致，可依次追问：是否识别并处理安全问题？是否承认婴幼儿正在表达需要，维护其尊严？是否提供与当下表现相对应的互动？是否让后续人员和家长获得具体而非标签化的信息？经营效率和家长即时诉求可以进入讨论，但本课要求最终选择能够清楚说明如何维护婴幼儿的安全、尊严与发展需要。理念真正接受检验的时刻，往往正是多个目标发生冲突时。",
L629:       "unit_id": "u14"
L630:     },
L631:     {
L632:       "kind": "visual",
L633:       "text": "画面呈现价值冲突决策罗盘，中心为“婴幼儿”，四周依次为“安全、尊严、发展需要、可执行性”；外圈补充“经营目标、[REDACTED]、专业照护要求”，提示逐项说明取舍。",
L634:       "unit_id": "u15",
L635:       "visual_function": "decision_support"
L636:     },
L637:     {
L638:       "kind": "interaction",
L639:       "text": "离堂任务：用自己的语言说明办托理念与价值体系的作用；指出案例中一处最关键的不一致；给出一项管理决定，并用“安全—尊严—发展需要”三项逐一说明依据。若只能复述口号而不能描述行为、责任与检查方式，请返回五列对应表重新修订。",
L640:       "unit_id": "u16"
L641:     },
L642:     {
L643:       "kind": "note",
L644:       "text": "【待核验】",
L645:       "unit_id": "sec1-pending"
L646:     }
L647:   ],
L648:   "word_count": {
L649:     "count": 2361,
L650:     "in_range": false,
L651:     "max": 2100,
L652:     "method": "unicode_non_whitespace_chars",
L653:     "min": 1800,
L654:     "scope_note": "统计教师讲解正文（含正文中讲述的案例），不计标题、画面指令、引用索引与独立备注"
L655:   }
L656: }
L657: ```
L658: 
L659: ## script:sec2
L660: 
L661: ```json
L662: {
L663:   "section_id": "sec2",
L664:   "template_ref": "d08a307545d44e54a0d58a0282bf3f6640384f5d6eb23de26cb111ac7be3131b",
L665:   "title": "8.2 文化建设的策略",
L666:   "units": [
L667:     {
L668:       "kind": "title",
L669:       "text": "8.2 文化建设的策略",
L670:       "unit_id": "u1"
L671:     },
L672:     {
L673:       "claim_refs": [
L674:         "clm_c1482d4ee6@v1"
L675:       ],
L676:       "kind": "narration",
L677:       "text": "看到“安全、尊重、回应”这样的标语时，先不要急着判断机构已经形成了相应文化。宣传展示回答的是“机构倡导什么”；制度管理回答的是“工作应按什么要求开展”；文化建设还要继续追问：“这些要求是否稳定地出现在管理者和员工每天的行动中？”本节采用一个操作性判断：理念不仅要能被说出来，还要能被看见、执行和复盘。稳定实施晨会、交接班和复盘，并建立明确的沟通规则，有助于将机构文化落实到员工的日常行为。三者需要相互衔接：标语提示方向，流程承载行动，管理者和员工用持续、一致的行为体现要求。",
L678:       "unit_id": "u2"
L679:     },
L680:     {
L681:       "kind": "visual",
L682:       "text": "画面左侧依次显示“宣传展示：倡导什么”“制度管理：按什么要求做”“文化建设：是否持续体现在日常行为中”；右侧用箭头连接“理念—流程—行为—复盘”。",
L683:       "unit_id": "u3",
L684:       "visual_function": "concept-differentiation"
L685:     },
L686:     {
L687:       "kind": "interaction",
L688:       "text": "暂停思考：如果一家托育机构只张贴“尊重”标语，却没有规定交接时怎样倾听、确认和回应，你能观察到的是文化、制度，还是宣传展示？请用一句话说明判断依据。",
L689:       "unit_id": "u4"
L690:     },
L691:     {
L692:       "claim_refs": [],
L693:       "kind": "narration",
L694:       "text": "要让理念进入日常工作，可以先把抽象词改写成可观察行为。例如，把“尊重婴幼儿”改写为：“开展照护操作前，先用简短语言告知将要做什么；观察婴幼儿的反应，再继续操作。”把“尊重同事”改写为：“同事陈述交接信息时不随意打断；听完后复述关键点，有异议时针对事项提问，不使用贬低性表达。”把“回应”改写为：“接到同事提出的照护疑问后，明确回答已知信息；暂时无法确认时，说明由谁核对、何时反馈。”改写时可以使用三个检查问题：谁在什么情境下行动？具体做什么？旁观者能否判断是否完成？如果要求仍停留在“重视”“加强”“注意”等词语上，就需要继续改写。",
L695:       "unit_id": "u5"
L696:     },
L697:     {
L698:       "kind": "visual",
L699:       "text": "展示行为化改写卡：抽象理念→适用情境→行动主体→可观察动作→确认方式。示例高亮“回应：无法确认时说明核对人和反馈时间”。",
L700:       "unit_id": "u6",
L701:       "visual_function": "procedural-scaffold"
L702:     },
L703:     {
L704:       "kind": "interaction",
L705:       "text": "行为化练习：把“关爱幼儿”改写为一项能够在照护现场直接观察的行为要求。完成后检查：是否写出了情境、动作和可判断的完成表现？本课程统一讨论托育场景时优先使用“婴幼儿”；此题保留“幼儿”一词用于术语辨析。",
L706:       "unit_id": "u7"
L707:     },
L708:     {
L709:       "claim_refs": [],
L710:       "kind": "narration",
L711:       "text": "接下来设计承载文化的三个稳定仪式。这里提供一份可调整的示范方案，所列频率与分工是课程设计建议，不作为普遍事实。晨会建议在每个工作日开班前进行，由当班全体照护人员和当日值班管理者参加，值班管理者负责召集并控制流程。第一步确认当日人员与岗位安排；第二步提示需要重点关注的婴幼儿及相关事项；第三步明确当天协作任务和责任人；第四步请参与者提出疑问；第五步由召集人复述关键安排并留下简要记录。晨会不能只朗读标语，每项文化理念至少要对应当天的一项具体行为。",
L712:       "unit_id": "u8"
L713:     },
L714:     {
L715:       "claim_refs": [],
L716:       "kind": "narration",
L717:       "text": "交接班建议在每次班次转换时进行，由交班员工、接班员工参加，班组负责人负责检查流程是否完成。第一步依据统一栏目说明婴幼儿当班期间的进食、休息、情绪、活动及需要继续观察的事项；第二步说明已经采取的行动和后续待办；第三步明确待办责任人和完成时点；第四步由接班员工复述重点；第五步双方确认记录。应把“今天还好”“多留意”等模糊表述改为具体信息。例如，不说“进食不太好”，而说“本次交接需要重点观察进食情况；请接班员工按照本机构既定记录要求继续记录，并在约定时点反馈”。涉及具体照护判断时，应执行机构已经核定的专业规范，本节不另行扩展。",
L718:       "unit_id": "u9"
L719:     },
L720:     {
L721:       "claim_refs": [
L722:         "clm_c1482d4ee6@v1"
L723:       ],
L724:       "kind": "narration",
L725:       "text": "复盘可以设置固定周期，并在需要时增加专项复盘。示范方案是每周一次团队复盘，由班组成员和管理者参加，管理者负责组织，指定记录人保存行动项。流程为：先回看上次行动项是否完成；再选取晨会、交接班或协作中的具体片段；随后对照沟通规则说明“原要求是什么、现场发生了什么、差距在哪里”；接着确定一项调整措施、责任人和完成时间；最后约定下次通过什么证据检查。复盘关注的不是员工能否背诵理念，而是约定动作是否出现、流程在哪一步中断以及下一轮怎样验证。",
L726:       "unit_id": "u10"
L727:     },
L728:     {
L729:       "kind": "visual",
L730:       "text": "三列表格展示：晨会—每个工作日开班前—值班管理者；交接班—每次班次转换—班组负责人检查；复盘—示范为每周一次并按需增加—管理者组织、指定人员记录。每列展开“参与人员、步骤、责任人、检查证据”。",
L731:       "unit_id": "u11",
L732:       "visual_function": "process-comparison"
L733:     },
L734:     {
L735:       "kind": "interaction",
L736:       "text": "模板练习：请分别为晨会、交接班和复盘填写五栏——实施频率、参与人员、操作步骤、责任人、执行证据。随后检查：是否每项都有明确动词？是否有人负责召集、确认和跟进？",
L737:       "unit_id": "u12"
L738:     },
L739:     {
L740:       "claim_refs": [
L741:         "clm_9888f312b7@v1"
L742:       ],
L743:       "kind": "narration",
L744:       "text": "沟通规则同样需要行为化。“尊重”可以要求管理者让员工完整陈述后再回应，纠正问题时描述具体行为和影响，不当众使用贬低性表达。“清晰”可以要求管理者说明任务内容、责任人、完成时间和确认方式，避免只说“抓紧处理”“大家注意”。“一致性”可以要求管理者对同类事项采用已经确定的要求；确需调整时，说明调整内容、生效时间，并向相关人员同步。管理层的日常沟通示范会影响员工沟通方式与机构文化要求的一致性。因此，管理者不仅是规则的发布者，也是被观察和被复盘的执行者。",
L745:       "unit_id": "u13"
L746:     },
L747:     {
L748:       "kind": "visual",
L749:       "text": "管理层示范清单：尊重—听完、描述具体行为、就事沟通；清晰—任务、责任人、时点、确认方式；一致—同类事项按统一要求处理，变更时同步说明。",
L750:       "unit_id": "u14",
L751:       "visual_function": "behavioral-checklist"
L752:     },
L753:     {
L754:       "kind": "interaction",
L755:       "text": "角色演练：员工说“交接记录里没有写清楚重点观察事项”。请分别演示两种管理者回应：一种会削弱尊重、清晰和一致性；另一种按照示范清单回应。演练后指出两种回应中可以直接观察到的差异。",
L756:       "unit_id": "u15"
L757:     },
L758:     {
L759:       "case_ref": "case1",
L760:       "kind": "case",
L761:       "text": "案例（虚构）：晨光托育中心在大厅张贴“安全、尊重、回应”的标语，却没有把理念改写为明确工作要求。晨会没有固定频率和责任人，有时只是朗读标语；交接班没有统一步骤，员工常说“今天还好”“需要多留意”，也没人确认关键信息；复盘只在出现明显问题后临时开展。管理者要求员工相互尊重，自己却常当众打断员工，并对相同问题给出不一致要求。一次交接中，接班员工不知道一名婴幼儿当天需要重点观察进食情况。询问后，交班员工回答：“记录里应该有，你自己看。”事后，管理者只要求全体员工再次学习墙上的标语，没有调整流程和沟通规则。",
L762:       "unit_id": "u16"
L763:     },
L764:     {
L765:       "claim_refs": [
L766:         "clm_c1482d4ee6@v1",
L767:         "clm_9888f312b7@v1"
L768:       ],
L769:       "kind": "narration",
L770:       "text": "诊断这个案例，可以建立“问题—措施”对应关系。宣传展示已经存在，表现为大厅标语；制度管理的薄弱处是晨会、交接班和复盘缺少稳定频率、统一步骤、确认机制与责任分工；文化建设的脱节则表现在员工和管理者的实际沟通没有体现所倡导的尊重与回应。针对晨会，应确定频率、召集人和当天行为重点；针对交接班，应统一信息栏目，加入复述确认、待办责任人和完成时点；针对复盘，应设置固定周期，用具体片段和行动项推动下一轮检查；针对管理层，应使用尊重、清晰和一致性的示范清单，并把管理者行为纳入复盘。再次朗读标语不能替代这些调整。",
L771:       "unit_id": "u17"
L772:     },
L773:     {
L774:       "claim_refs": [],
L775:       "kind": "narration",
L776:       "text": "最后要解决“怎样知道措施真的执行了”。复盘时可以核对晨会记录中是否出现当日重点、责任人和确认结果；抽查交接记录是否包含具体情况、后续待办、责任人以及双方确认；查看上次复盘行动项是否写明期限并在本次形成闭环；观察现场沟通中是否仍有随意打断、模糊指令或同类事项要求不一致。还可以请参与者用一个真实工作片段说明规则如何被执行。记录存在不等于执行完成，因此要把书面记录与现场表现相互对照。这里的检查项目是本节提供的操作方案，不代表未经本案例验证的效果结论。",
L777:       "unit_id": "u18"
L778:     },
L779:     {
L780:       "kind": "visual",
L781:       "text": "证据链画面：晨会重点与责任记录→交接具体信息与复述确认→复盘行动项与闭环→现场沟通表现。旁边标注“记录与行为相互对照”。",
L782:       "unit_id": "u19",
L783:       "visual_function": "evidence-chain"
L784:     },
L785:     {
L786:       "kind": "interaction",
L787:       "text": "案例综合任务：1. 分别指出文化建设、制度管理和宣传展示的表现及脱节；2. 将“尊重”和“回应”各改写为至少一项可观察行为；3. 完成晨会、交接班、复盘的频率、人员、步骤和责任人方案；4. 写出管理者体现尊重、清晰和一致性的示范要求；5. 列出至少三项可用于后续复盘的记录或现场表现，并说明它们如何帮助判断措施是否实际执行。",
L788:       "unit_id": "u20"
L789:     }
L790:   ],
L791:   "word_count": {
L792:     "count": 2157,
L793:     "in_range": false,
L794:     "max": 2100,
L795:     "method": "unicode_non_whitespace_chars",
L796:     "min": 1800,
L797:     "scope_note": "统计教师讲解正文（含正文中讲述的案例），不计标题、画面指令、引用索引与独立备注"
L798:   }
L799: }
L800: ```
L801: 
L802: ## script:sec3
L803: 
L804: ```json
L805: {
L806:   "section_id": "sec3",
L807:   "template_ref": "d08a307545d44e54a0d58a0282bf3f6640384f5d6eb23de26cb111ac7be3131b",
L808:   "title": "8.3 员工行为规范与服务礼仪建设",
L809:   "units": [
L810:     {
L811:       "kind": "title",
L812:       "text": "8.3 员工行为规范与服务礼仪建设",
L813:       "unit_id": "u1"
L814:     },
L815:     {
L816:       "claim_refs": [
L817:         "clm_949ec8536b@v3"
L818:       ],
L819:       "kind": "narration",
L820:       "placeholder": true,
L821:       "text": "本节先明确一个判断标准：员工行为规范不是“态度好一点”之类的口号，服务礼仪也不只是微笑、问候和统一话术。真正可执行的规范，需要让婴幼儿、家长和同事能够预期员工会怎样行动，并在事后判断行动是否完成。我们可以用四个问题检查一项规范：谁来做？在什么情境下做？要出现什么可观察行为？如何记录、交接或反馈？例如，“尊重婴幼儿”过于抽象，可以改写为：“需要移动婴幼儿身体或拿走其物品前，员工先用简短语言说明；婴幼儿哭泣或拒绝时，不贴标签，不以羞辱、威胁性语言催促，并给予可执行的选择或陪伴。”这里的“尊重”已经转化成能够观察和复盘的语言与动作。判断礼仪是否体现办托理念，也不能只看形式。员工蹲下回应哭泣的婴幼儿，是为了看见其状态、降低强迫感并提供回应；接待时复述[REDACTED]，是为了减少理解偏差；交接时写清责任人与反馈时间，是为了形成可预期、可追溯的服务。这些行为分别把安全、尊重和回应性互动落实到了具体情境中。至于理念转化与日常管理或服务质量是否存在关联、关联方向和程度如何，目前只能表述为“【待核验】”，不能把它当作既定结论。",
L822:       "unit_id": "u2"
L823:     },
L824:     {
L825:       "kind": "visual",
L826:       "text": "画面呈现“理念—判断原则—可观察行为—记录与反馈”四层结构；将“尊重”连接到“不贴标签、行动前说明、回应情绪”，将“安全”连接到“确认信息、持续观察、及时上报”，将“可预期”连接到“明确责任人与反馈时间”。",
L827:       "unit_id": "u3",
L828:       "visual_function": "structure"
L829:     },
L830:     {
L831:       "kind": "interaction",
L832:       "text": "暂停并改写：把“态度要专业”“多关心婴幼儿”“交接要认真”分别改成一条可观察规范。每条必须包含情境、责任主体、具体动作和完成标志。",
L833:       "unit_id": "u4"
L834:     },
L835:     {
L836:       "claim_refs": [],
L837:       "kind": "narration",
L838:       "text": "与婴[REDACTED]，可以依次观察语言、动作和回应。语言方面，描述事实，不给婴幼儿贴上“淘气”“不听话”等标签；表达要求时说明当前需要做什么，而不是只说“不许”。动作方面，不突然拉拽、夺取或强迫；需要接触身体、转换活动或收回物品时，先告知，再等待短暂回应，并提供必要协助。回应方面，先识别哭泣、回避、伸手或持续注视等可观察表现，再决定陪伴、安抚、调整活动或按机构流程报告。这里不要求员工猜测婴幼儿的内心，而要求员工说清自己看到了什么、做了什么、接下来观察什么。对比两种表达：“你怎么这么不听话？”把评价指向婴[REDACTED]，也没有提供下一步行动；“你还想继续玩，现在需要把玩具放回去，我陪你一起放好”则说明了情境、要求和支持。规范修正的依据应落在安全、尊重和回应性互动上，而不能只用“我觉得第二句更温柔”作为理由。课程中提到“幼儿”时，也应结合机构服务对象和具体记录口径，避免在同一份交接记录中随意混用“幼儿”与“婴幼儿”，造成对象表述不清。",
L839:       "unit_id": "u5"
L840:     },
L841:     {
L842:       "kind": "visual",
L843:       "text": "左右对比同一收玩具情境：左侧为突然拿走玩具并评价“你不听话”；右侧为先描述状态、说明要求、提供陪伴。下方用“行为—风险—依据—修正”四格表呈现分析路径。",
L844:       "unit_id": "u6",
L845:       "visual_function": "comparison"
L846:     },
L847:     {
L848:       "claim_refs": [
L849:         "clm_c1482d4ee6@v1",
L850:         "clm_9888f312b7@v1"
L851:       ],
L852:       "kind": "narration",
L853:       "text": "服务礼仪还需要嵌入接待、沟通、交接和反馈流程。以晨间接待为例，接待员工先听取[REDACTED]，再复述并确认对象、时间、具体表现、已采取措施和有效联系方式；随后说明机构能够执行的观察、记录与反馈安排。如信息涉及员工权限之外的判断，应说明边界，并转交相应责任人处理。交接班不能只说“多注意一下”，而要回答六项内容：具体对象是谁，已知事实是什么，已经做了什么，接下来观察或办理什么，由谁负责，向谁在何时反馈。完成交接后，接班员工复述关键事项；交班员工核对记录，避免仅凭口头印象传递。稳定实施晨会、交接班和复盘，并建立明确沟通规则，有助于将机构文化落实到员工日常行为。管理者也不能只在制度中要求员工规范表达，其日常沟通示范会影响员工沟通方式与机构文化要求的一致性。因此，复盘时可以请管理者示范如何描述事实、指出风险、明确责任和提出修正，而不是笼统批评“服务意识不够”。",
L854:       "unit_id": "u7"
L855:     },
L856:     {
L857:       "kind": "interaction",
L858:       "text": "渐隐练习：第一轮按“情境—行为—责任主体—记录—反馈”模板补全晨间接待规范；第二轮只保留情境，由学习者独立写出规范；同伴检查其中是否出现“及时、认真、妥善”等无法直接观察的模糊词。",
L859:       "unit_id": "u8"
L860:     },
L861:     {
L862:       "claim_refs": [
L863:         "clm_007501ee22@v2"
L864:       ],
L865:       "kind": "narration",
L866:       "text": "家长沟通需要区分三类表达。第一类是事实告知，只说已经获得或观察到的信息，例如“您告知昨晚有咳嗽、早餐进食较少”。第二类是可执行措施，说明员工将按流程完成的行动，例如记录精神状态、进食和咳嗽表现，并在约定时间反馈。第三类是超出权限或证据范围的判断与承诺，例如“肯定不会加重”“一定没问题”。面对[REDACTED]，规范回应不是回避，而是同时做到四点：先确认关切，再陈述事实，随后说明可执行措施，最后明确不能保证的事项以及后续联系安排。可表述为：“我理解您担心今天的情况。我已记录您告知的信息，入班后会按机构流程观察并记录，在约定时间向您反馈；是否会加重，我不能作出保证。如出现需要进一步处理的情况，我们会依流程联系您。”这段话的礼仪价值不在于语气圆滑，而在于尊重家长、保持事实清楚并守住沟通边界。家长对托育机构相关服务的实际体验，可能与其对机构品牌的评价有关；本节引用这一已核验表述时，只保留“可能有关”的范围，不扩大为确定因果关系。",
L867:       "unit_id": "u9"
L868:     },
L869:     {
L870:       "kind": "interaction",
L871:       "text": "角色演练：一人扮演家长，一人扮演接待员工。家长连续追问“能不能保证不会加重”“是不是没事”。员工须完成确认关切、事实复述、措施说明、边界表达和反馈约定。观察者逐项记录，不以“感觉不错”评分。",
L872:       "unit_id": "u10"
L873:     },
L874:     {
L875:       "case_ref": "case1",
L876:       "claim_refs": [],
L877:       "kind": "case",
L878:       "text": "【虚构案例】晨间接待时，家长告诉林老师：“婴[REDACTED]有些咳嗽，早餐吃得少，请多留意。如果今天还是咳，能不能保证不会加重？”林老师回答：“您放心，肯定不会有问题。”她没有确认咳嗽表现、进食情况和联系方式，也没有说明可以采取的措施及反馈安排。入班后，一名婴幼儿不愿放下玩具并哭泣。林老师直接拿走玩具，说：“你怎么这么不听话？”交班时，她只对周老师说：“今天有个婴幼儿状态不太好，多注意一下。”她没有说明对象、事实、已采取措施、待观察事项、责任人和反馈时间，也未留下记录。午后[REDACTED]，周老师因信息不足回答：“应该没什么事。”家长因而质疑交接是否可靠。\n分析时建立完整链条。第一，林老师承诺“肯定不会有问题”，不当行为是对无法确定的结果作保证；风险是家长形成错误预期；依据是沟通边界和可预期服务。改进为复述已知事实，说明观察、记录和联系安排，并明确不能保证结果。第二，未确认和记录晨间信息，可能使后续观察与联系缺少明确输入；依据是安全与信息可追溯。改进为记录对象、家长原话中的事实、联系方式和反馈约定。第三，突然拿走玩具并贴标签，没有回应婴幼儿当下表现；依据是尊重与回应性互动。改进为先描述状态，再说明转换要求并提供陪伴。第四，模糊交接导致周老师不知道观察谁、观察什么；依据是安全、可预期服务和信息可追溯。改进后的交接可写为：“对象：某婴幼儿；[REDACTED]：昨晚有些咳嗽，今早早餐进食较少；已做事项：完成晨间信息记录；待办：按机构流程观察并记录精神状态、进食及咳嗽表现；责任主体：周老师；反馈对象：家长；反馈时间：双方约定时点；如出现需进一步处理的情况，依流程联系并报告。”第五，周老师说“应该没什么事”，缺少事实基础。改进为如实说明当前掌握的信息，立即核对记录、补充观察，并明确下一次反馈时间。",
L879:       "unit_id": "u11"
L880:     },
L881:     {
L882:       "kind": "visual",
L883:       "text": "画面展示案例分析闭环：“不当行为→可能风险→判断依据→改进措施→责任主体→反馈与复盘”，旁边固定列出六项允许使用的依据：安全、尊重、回应性互动、沟通边界、可预期服务、信息可追溯。",
L884:       "unit_id": "u12",
L885:       "visual_function": "process"
L886:     },
L887:     {
L888:       "claim_refs": [],
L889:       "kind": "narration",
L890:       "text": "最后，把本节内容整理成一份员工行为规范清单。婴幼儿互动项检查是否先说明、少评价、有回应；家长沟通项检查是否复述事实、确认信息、说明措施、明确边界和约定反馈；同事协作项检查是否尊重发言、基于记录沟通、发现遗漏及时补充；交接项检查是否写明对象、事实、措施、待办、责任主体与反馈要求。每项都应使用能够看到或听到的动词，如“复述、确认、记录、说明、复述交接、核对、反馈”，避免只写“重视、关心、专业、负责”。面对新情境时，也可以沿用同一判断顺序：先看安全，再看是否尊重并回应婴幼儿，随后检查沟通是否越界，最后确认服务是否可预期、信息是否可追溯。这样，礼仪不再是一套机械话术，而成为员工选择语言、动作、记录和协作方式的共同标准。",
L891:       "unit_id": "u13"
L892:     },
L893:     {
L894:       "kind": "interaction",
L895:       "text": "结课任务：提交一份覆盖婴[REDACTED]、[REDACTED]、同事协作和交接的规范清单；再从虚构案例中任选两项不当行为，写出“风险—依据—改进—责任主体—反馈要求”。最后用一句话说明其中一项礼仪要求如何体现安全、尊重或回应性互动，而不只描述外在形式。",
L896:       "unit_id": "u14"
L897:     },
L898:     {
L899:       "kind": "note",
L900:       "text": "【待核验】clm_949ec8536b@v3",
L901:       "unit_id": "sec3-pending"
L902:     }
L903:   ],
L904:   "word_count": {
L905:     "count": 2710,
L906:     "in_range": false,
L907:     "max": 2100,
L908:     "method": "unicode_non_whitespace_chars",
L909:     "min": 1800,
L910:     "scope_note": "统计教师讲解正文（含正文中讲述的案例），不计标题、画面指令、引用索引与独立备注"
L911:   }
L912: }
L913: ```
L914: 
L915: ## script:sec4
L916: 
L917: ```json
L918: {
L919:   "section_id": "sec4",
L920:   "template_ref": "d08a307545d44e54a0d58a0282bf3f6640384f5d6eb23de26cb111ac7be3131b",
L921:   "title": "8.4 品牌形象与口碑传播管理",
L922:   "units": [
L923:     {
L924:       "kind": "title",
L925:       "text": "8.4 品牌形象与口碑传播管理",
L926:       "unit_id": "u1"
L927:     },
L928:     {
L929:       "claim_refs": [
L930:         "clm_007501ee22@v2"
L931:       ],
L932:       "kind": "narration",
L933:       "text": "提到品牌形象，有人会先想到名称、标志、宣传文章和对外口径。本节换一个观察角度：从家长经历的真实服务过程出发理解品牌。家长对托育机构相关服务的实际体验，可能与其对机构品牌的评价有关。因此，品牌管理不能只检查“说了什么”，还要检查“实际做了什么”“家长经历了什么”，以及宣传表达能否由服务记录和具体行动支持。请回想一次家长从进入机构到离开的过程：接待是否回应了问题，员工是否按约定沟通，异常情况是否被记录，后续说明是否按时送达。这些具体时刻都可以列入服务接触点清单。清单至少写明接触点、参与人员、服务事实、家长可能关注的内容、现有记录方式和待改进事项。这里要区分三类信息：服务事实是能够从记录或当事人说明中核对的内容；[REDACTED]是家长对经历的表达；品牌评价是家长据此形成的判断。三者可以相关，但不能彼此替代。",
L934:       "unit_id": "u2"
L935:     },
L936:     {
L937:       "kind": "visual",
L938:       "text": "画面呈现“机构表达—服务接触点—家长体验—品牌评价”链条；下方用三栏区分“服务事实、[REDACTED]、品牌评价”，并标出不可直接画等号。",
L939:       "unit_id": "u3",
L940:       "visual_function": "conceptual_structure"
L941:     },
L942:     {
L943:       "case_ref": "case1",
L944:       "kind": "case",
L945:       "text": "【虚构案例】某托育机构承诺“及时、尊重地回应家长关切”。周一离园时，林女士发现自家[REDACTED]有一处轻微红印。为保持用语一致，下文将该幼儿称为婴幼儿。她向当班员工询问，员工只回答“应该没事”，没有核对照护记录，也没有把这次询问写入交接记录。这个场景包含多个接触点：离园观察、[REDACTED]、员工回应、记录核对和交接。员工的回答没有提供可核对的信息，也没有说明何时补充反馈。次日上午，林女士仍未收到说明，于是在家长群中表示机构沟通不透明。此时又出现了后续反馈和群内沟通两个接触点。负责人看到消息后立即致歉，并提出两种方案。方案A是删除群内讨论，再发布一篇强调机构“专业、细致、零投诉”的宣传文章。方案B是先记录家长反映的时间、具体问题、已知服务事实和[REDACTED]；核对当日照护及交接记录，分别向相关员工了解情况；与家长约定反馈时间；反馈时说明已经核实的内容、尚不能确认的内容以及后续措施；随后检查离园沟通和异常情况交接流程，在周会中复盘，明确责任人、完成期限和验证方式。负责人还想邀请林女士分享处理体验，团队提出三个条件：改进措施已经落实，家长自愿参与，传播内容与实际服务一致。在这个案例中，问题不仅是出现红印，也包括询问没有被完整记录、信息没有核对、反馈时间没有约定，以及次日上午仍缺少说明。分析时只能依据案例给出的信息，不能猜测红印的原因，也不能把一次投诉直接概括为机构普遍存在同类问题。",
L946:       "unit_id": "u4"
L947:     },
L948:     {
L949:       "kind": "interaction",
L950:       "text": "请建立“服务接触点清单”：逐项填写离园观察、现场询问、员工回应、记录核对、交接、次日反馈、群内沟通和负责人处理，并为每项写出“已知事实、[REDACTED]、可能影响、需要核对的证据”。",
L951:       "unit_id": "u5"
L952:     },
L953:     {
L954:       "claim_refs": [
L955:         "clm_c1482d4ee6@v1",
L956:         "clm_9888f312b7@v1"
L957:       ],
L958:       "kind": "narration",
L959:       "text": "现在按照“记录—处理—结果反馈—复盘”完成闭环。第一步，记录问题。写明反馈时间、反馈人、涉及的婴幼儿、家长原话或准确转述、已知事实、未知事项、家长当前诉求、接收人和下一次联系时间。不要把推测写成事实，也不要为了让记录显得完整而补写未经核对的原因。第二步，处理问题。确定由谁核对照护记录和交接信息，由谁向相关员工了解情况，并列出需要确认的问题。处理目标不是尽快给出一个确定答案，而是在约定时间内形成边界清楚的说明。第三步，反馈结果。分别说明已经核实什么、暂时不能确认什么、机构将采取什么行动、何时再次联系。尊重不等于一味认同，及时也不等于仓促下结论。第四步，复盘。把个案中暴露出的流程线索带到周会，检查离园询问如何登记、异常信息如何交接、负责人如何跟进，再为改进项指定责任人、期限和验证方式。稳定实施晨会、交接班和复盘，并建立明确的沟通规则，有助于将机构文化落实到员工日常行为；管理层的日常沟通示范也会影响员工沟通方式与机构文化要求的一致性。",
L960:       "unit_id": "u6"
L961:     },
L962:     {
L963:       "kind": "visual",
L964:       "text": "画面绘制四段闭环：“记录→处理→结果反馈→复盘→更新流程”，每段附关键字段；在“记录”和“反馈”旁标注“事实与推测分开”。",
L965:       "unit_id": "u7",
L966:       "visual_function": "procedural_scaffolding"
L967:     },
L968:     {
L969:       "kind": "interaction",
L970:       "text": "第一轮提供四步标题，请补全每步内容；第二轮只保留“记录”和“复盘”两个提示，请补齐中间步骤；第三轮撤去提示，独立提交完整处理方案。自查：是否有负责人、时间点、未知事项、反馈安排、完成期限和验证方式？",
L971:       "unit_id": "u8"
L972:     },
L973:     {
L974:       "claim_refs": [],
L975:       "kind": "narration",
L976:       "text": "比较方案A与方案B，可以使用四项判断依据：是否回应已有服务记录和家长反馈，是否包含可执行行动，是否与“及时、尊重地回应家长关切”的承诺一致，是否出现无法由实际服务支持的过度表达。按这些依据，方案B中的记录、核对、反馈、流程检查和周会复盘属于服务改进措施，因为每项都有明确对象，并且能够继续补充责任人、期限和验证方式。方案A中的宣传文章属于宣传措施；删除讨论也没有处理记录缺失和反馈中断。尤其是“零投诉”在本案例中与已经发生的投诉记录不一致，不应作为传播表达。两类措施并非只按“对内”或“对外”区分，关键在于是否改变服务过程、能否留下验证依据。传播可以在改进之后进行，但不能代替改进。邀请家长分享处理体验也不是自动成立的口碑方案，必须以[REDACTED]、措施落实和内容符合实际为条件。",
L977:       "unit_id": "u9"
L978:     },
L979:     {
L980:       "kind": "visual",
L981:       "text": "左右对照方案A与方案B，中间放置四个判断标签：“证据、可执行性、承诺一致性、是否过度承诺”；用箭头指出“宣传不能替代服务改进”。",
L982:       "unit_id": "u10",
L983:       "visual_function": "contrast_and_judgment"
L984:     },
L985:     {
L986:       "kind": "interaction",
L987:       "text": "请判断下列做法属于“服务改进”“宣传措施”还是“条件不足”：补设离园询问登记栏；发布“从不发生沟通遗漏”的海报；周会核查三条反馈是否按期闭环；在未征得同意时请家长公开表扬。每项必须引用四项判断依据中的至少一项。",
L988:       "unit_id": "u11"
L989:     },
L990:     {
L991:       "claim_refs": [],
L992:       "kind": "narration",
L993:       "text": "最后形成一条不过度承诺的口碑传播建议。例如：“在完成离园询问登记和异常交接流程调整后，经家长自愿同意，分享本次反馈如何被记录、核对、回复和复盘；内容只呈现已经落实且可核对的行动，不使用‘绝不遗漏’或‘零投诉’等表达。”这条建议与机构的服务承诺相呼应，又给出了落实条件。复盘个案时还要控制结论边界：一次投诉可以作为检查流程的线索，却不足以直接证明同类问题普遍存在。较稳妥的做法是继续查看相关记录，明确样本范围和待核对事项；在证据不足时，将结论写成“发现一个需要检查的环节”，而不是“机构一直存在这个问题”。品牌形象管理由此回到可执行的工作：识别接触点，记录事实与感受，完成投诉闭环，根据证据改进服务，再以真实、克制并与承诺一致的方式传播。",
L994:       "unit_id": "u12"
L995:     },
L996:     {
L997:       "kind": "interaction",
L998:       "text": "提交本节成果包：一份品牌服务接触点清单；一份“记录—处理—结果反馈—复盘”方案；一份方案A与方案B的比较表；一条可落实且不过度承诺的传播建议；一句说明为什么不能由单一投诉推断普遍问题。",
L999:       "unit_id": "u13"
L1000:     }
L1001:   ],
L1002:   "word_count": {
L1003:     "count": 2014,
L1004:     "in_range": true,
L1005:     "max": 2100,
L1006:     "method": "unicode_non_whitespace_chars",
L1007:     "min": 1800,
L1008:     "scope_note": "统计教师讲解正文（含正文中讲述的案例），不计标题、画面指令、引用索引与独立备注"
L1009:   }
L1010: }
L1011: ```
L1012: 
L1013: ## assessment:sec1
L1014: 
L1015: ```json
L1016: {
L1017:   "items": [
L1018:     {
L1019:       "answer": "B",
L1020:       "assessment_id": "a1",
L1021:       "claim_refs": [],
L1022:       "distractors": [
L1023:         "A将理念停留在宣传口号，未说明对应流程、人员责任和检查方式。",
L1024:         "C侧重记忆和展示理念，不能证明理念已转化为日常服务行为。",
L1025:         "D把经营目标置于婴幼儿安全和照护需要之前，与所声明的核心价值不一致。"
L1026:       ],
L1027:       "kind": "hinge_question",
L1028:       "options": [
L1029:         "A.在大厅张贴“用爱守护成长”的宣传标语",
L1030:         "B.每日入托时完成健康观察并记录；照护前向婴[REDACTED]；对哭闹、求助等信号及时回应，并由负责人抽查记录与现场执行情况",
L1031:         "C.要求员工熟记机构理念，并在家长参观时统一背诵",
L1032:         "D.当招生和照护安排发生冲突时，优先满足经营目标，再根据人员空闲情况调整照护"
L1033:       ],
L1034:       "question": "某托育机构将“安全、尊重、及时回应”确定为核心价值。以下哪一项最能把这些价值转化为可检查的服务承诺？",
L1035:       "rationale": "B同时覆盖安全、尊重和回应性互动，并把核心价值落实到每日流程、人员行为、记录和检查环节，因而属于可执行、可观察、可检查的服务承诺。其余选项分别存在口号化、重展示轻执行或价值冲突的问题。",
L1036:       "student_viewable": true,
L1037:       "target_goal": "g2"
L1038:     },
L1039:     {
L1040:       "answer": "开放",
L1041:       "assessment_id": "a2",
L1042:       "kind": "reflection_prompt",
L1043:       "question": "请选取托育机构中的一个日常场景，例如入托、进餐、换尿布、午睡或离托，按照“明确核心价值—形成服务承诺—对应每日流程—落实人员职责—检查执行情况”的顺序，设计一套简要方案。方案需说明如何保障婴幼儿安全与尊严、如何回应其需要，以及当经营目标或家长诉求与专业照护要求冲突时，你将依据什么作出判断。",
L1044:       "rationale": "回答应体现价值、承诺、流程、职责与检查之间的一致性；服务承诺应具体可执行；流程应包含安全、尊重和回应性互动；职责应明确到相关岗位；检查方式应能观察或留痕；冲突判断应以婴[REDACTED]、尊严和发展需要为核心，并提出可实施的处理办法。",
L1045:       "student_viewable": true,
L1046:       "target_goal": "g3"
L1047:     }
L1048:   ],
L1049:   "section_id": "sec1"
L1050: }
L1051: ```
L1052: 
L1053: ## case:sec1:1
L1054: 
L1055: ```json
L1056: {
L1057:   "case_id": "case1",
L1058:   "claim_refs": [
L1059:     "clm_c1482d4ee6",
L1060:     "clm_9888f312b7",
L1061:     "clm_007501ee22"
L1062:   ],
L1063:   "difficulty": "本案例集中呈现三个学习难点：学习者可能把“安全第一、尊重、用爱陪伴”直接视为已经落实的理念；难以把抽象价值逐项转化为可观察、可执行、可检查的承诺、流程和岗位职责；评价落实情况时可能只关注午睡是否按时完成和记录表是否填写，而忽略工作人员的实际行为、管理层应建立的复盘机制以及婴幼儿与家长的真实服务体验。",
L1064:   "kind": "fictional",
L1065:   "linked_goal": "g5",
L1066:   "new_factual_claims": [],
L1067:   "section_id": "sec1",
L1068:   "text": "【虚构案例】晨光托育机构在宣传栏中写着“安全第一、尊重每一名婴幼儿、用爱陪伴成长”。为提高午睡准备效率，班级规定所有婴幼儿必须在十分钟内完成如厕、换衣和上床。某日，一名婴幼儿不愿立即脱下外套，并用动作表示想继续抱着安抚巾。照护人员一边说“要听话，大家都在等你”，一边直接拿走安抚巾、脱下外套，将其抱到床上。另一名照护人员发现该婴幼儿持续哭泣，但因岗位职责中只写了“按时完成午睡准备”，没有进一步回应。交接班记录仅填写“午睡流程按时完成”，未记录婴幼儿的表现及工作人员的处理过程。家长接回时询问婴幼儿为何情绪低落，工作人员回答“今天有点不配合”，机构也没有记录或复盘此次沟通。请学习者完成以下任务：1. 判断宣传栏中的表述哪些属于抽象口号，并说明理由；2. 从安全、尊重和回应性互动三个方面，找出理念与实际行为、流程、岗位职责、检查方式及服务体验之间的不一致；3. 将“尊重每一名婴幼儿”改写为至少三条包含具体对象、行动、适用情境和检查方式的服务承诺；4. 补全一份“核心价值—服务承诺—工作流程—岗位职责—检查要点”对应表；5. 面对“按时完成午睡准备”与“回应婴幼儿当下需要”的冲突，作出管理决定并说明该决定如何维护婴幼儿的安全、尊严与发展需要。",
L1069:   "title": "墙上的“尊重”与午睡前的催促"
L1070: }
L1071: ```


## RUN BINDINGS A
{
  "kit": {
    "case_id": "A",
    "mode": "dynamic",
    "run_id": "run_77e357790d91",
    "run_status": "succeeded",
    "project_id": "bench-a-dynamic",
    "pebs_commit": null,
    "environment": null,
    "experiment": null
  },
  "separate_worksheet_run": {
    "case_id": "A",
    "mode": "dynamic",
    "run_id": "run_1ae60eced739",
    "run_status": "succeeded",
    "run_dir": "C:\\Users\\admin\\Documents\\ChatGPT\\心理学教育skills\\benchmarks\\runs\\20260920-224226-A-dynamic",
    "artifact_count": 47,
    "evidence_policy": [
      "SUPPORTED"
    ]
  }
}


## RUN BINDINGS B
{
  "kit": {
    "case_id": "B",
    "mode": "dynamic",
    "run_id": "run_8c3ffb4d0a85",
    "run_status": "succeeded",
    "project_id": "bench-b-dynamic-084324",
    "pebs_commit": null,
    "environment": null,
    "experiment": ""
  },
  "separate_worksheet_run": {
    "case_id": "B",
    "mode": "dynamic",
    "run_id": "run_8c3ffb4d0a85",
    "run_status": "succeeded",
    "run_dir": "C:\\Users\\admin\\Documents\\ChatGPT\\心理学教育skills\\benchmarks\\runs\\20260919-084324-B-dynamic",
    "artifact_count": 19,
    "evidence_policy": [
      "SUPPORTED"
    ]
  }
}


## RUN BINDINGS C
{
  "kit": {
    "case_id": "C",
    "mode": "dynamic",
    "run_id": "run_ec5bff2ee0c1",
    "run_status": "succeeded",
    "project_id": "bench-c-dynamic-170741",
    "pebs_commit": null,
    "environment": null,
    "experiment": null
  },
  "separate_worksheet_run": {
    "case_id": "C",
    "mode": "dynamic",
    "run_id": "run_ec5bff2ee0c1",
    "run_status": "succeeded",
    "run_dir": "C:\\Users\\admin\\Documents\\ChatGPT\\心理学教育skills\\benchmarks\\runs\\20260918-170741-C-dynamic",
    "artifact_count": 60,
    "evidence_policy": [
      "SUPPORTED"
    ]
  }
}
