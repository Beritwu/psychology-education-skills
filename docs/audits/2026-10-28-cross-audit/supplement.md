# Additional code evidence

## pebs/benchmark/report.py
L546: def write_worksheets(
L547:     runs: list[dict[str, Any]] | None = None,
L548:     *,
L549:     directory: Path | None = None,
L550:     preserve_filled: bool = True,
L551: ) -> list[Path]:
L552:     """§30–§32：为每次 run 生成教师评分工作表（人工填写后可用 CLI 回收）。
L553: 
L554:     教师填写的评分是不可再生的外部输入：重新生成报告时绝不能覆盖已填写的工作表，
L555:     否则一位老师刚写好的 14 个维度评分会被 `--report` 静默清空。
L556:     `preserve_filled=True`（默认）下只刷新空白工作表里的 run 绑定信息。"""
L557:     import yaml
L558: 
L559:     runs = runs if runs is not None else load_runs()
L560:     target_dir = directory or (cases.reports_dir() / "worksheets")
L561:     target_dir.mkdir(parents=True, exist_ok=True)
L562:     written: list[Path] = []
L563:     for run in runs:
L564:         if not is_evaluable(run):
L565:             # 失败/无产物的 run 不生成评分表：教师无法给一份不存在的课程打 14 个维度分，
L566:             # 它的信息已经在报告的 Status / Attempts / Auto Issues 列里
L567:             continue
L568:         case_id = str(run.get("case_id") or "?")
L569:         mode = str(run.get("mode") or "?")
L570:         # §46：实验变体（external-assessment 等）是不同产物，工作表必须分开命名，
L571:         # 否则「只生成 PPT」这类变体会覆盖该 case 的主工作表。
L572:         experiment = str(run.get("experiment") or "")
L573:         stem = f"{case_id}-{mode}-{experiment}" if experiment else f"{case_id}-{mode}"
L574:         path = target_dir / f"{stem}-human_eval.yaml"
L575:         if preserve_filled and path.exists():
L576:             try:
L577:                 existing = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
L578:             except yaml.YAMLError:
L579:                 existing = {}
L580:             if _worksheet_is_filled(existing):
L581:                 continue
L582:         template = {
L583:             "run": {
L584:                 "case_id": case_id,
L585:                 "mode": mode,
L586:                 "run_id": run.get("run_id"),
L587:                 "run_status": run.get("run_status"),
L588:                 "run_dir": run.get("run_dir"),
L589:                 "artifact_count": len(run.get("artifact_hashes") or {}),
L590:                 "evidence_policy": run.get("evidence_policy"),
L591:             },
L592:             "reviewer": "",
L593:             "role": "teacher",
L594:             "scores": {
L595:                 "subject_accuracy": None,
L596:                 "teaching_logic": None,
L597:                 "goal_clarity": None,
L598:                 "content_alignment": None,
L599:                 "concept_clarity": None,
L600:                 "case_quality": None,
L601:                 "executability": None,
L602:                 "student_engagement": None,
L603:                 "cognitive_challenge": None,
L604:                 "assessment_design": None,
L605:                 "language_naturalness": None,
L606:                 "visual_necessity": None,
L607:                 "coherence": None,
L608:                 "teacher_usability": None,
L609:                 "spoken_naturalness": None,
L610:             },
L611:             "comment": "",
L612:             "must_fix": [],
L613:             "nice_to_have": [],
L614:             "evidence_errors": 0,
L615:             "routing_errors": 0,
L616:             "plan_errors": 0,
L617:             "edits": {
L618:                 "generated_text": "",
L619:                 "edited_text": "",
L620:                 "items": [{"category": "", "severity": ""}],
L621:             },
L622:             "notes": [
L623:                 "填写说明见 benchmarks/reports/worksheets/README.md",
L624:                 "scores 使用 1–5；spoken_naturalness 仅脚本类任务必填",
L625:                 "edits.items 的 category 取值：fact correction / teaching restructure / tone edit / case replacement / media correction / assessment correction / template correction",
L626:                 "edits.items 的 severity 取值：S0 cosmetic / S1 wording / S2 local teaching improvement / S3 conceptual correction / S4 factual-evidence correction / S5 major redesign",
L627:             ],
L628:         }
L629:         path.write_text(yaml.safe_dump(template, allow_unicode=True, sort_keys=False), encoding="utf-8")
L630:         written.append(path)
L631:     readme = target_dir / "README.md"
L632:     if not readme.exists():
L633:         readme.write_text(
L634:             "# 教师评分工作表（M6 §30–§32）\n\n"
L635:             "1. 打开对应的 `<case>-<mode>-human_eval.yaml`，在 `scores` 中给 1–5 分（14 个维度；脚本类任务另填 `spoken_naturalness`）。\n"
L636:             "2. `comment` 必填（文字备注），`must_fix` / `nice_to_have` 选填。\n"
L637:             "3. 若做过人工修改，把修改前后的文本填入 `edits.generated_text` / `edits.edited_text`，并按类别与严重度登记 `edits.items`。\n"
L638:             "4. 提交：`python -m pebs.cli benchmark --submit-eval <worksheet.yaml> --project <project_id>`\n"
L639:             "   （等价于 POST /api/projects/<project_id>/evaluation；评分以 Artifact 形式落库并绑定 Skill 版本）\n",
L640:             encoding="utf-8",
L641:         )
L642:     return written

## pebs/server.py
L121: class HumanEvalIn(BaseModel):
L122:     reviewer: str
L123:     role: str = "teacher"
L124:     run_id: str = ""
L125:     mode: str = ""
L126:     scores: dict[str, float] = Field(default_factory=dict)
L127:     comment: str = ""
L128:     must_fix: list[str] = Field(default_factory=list)
L129:     nice_to_have: list[str] = Field(default_factory=list)
L130:     evidence_errors: int = 0
L131:     routing_errors: int = 0
L132:     plan_errors: int = 0
L133:     edits: dict[str, Any] = Field(default_factory=dict)

## pebs/server.py
L442: @app.post("/api/projects/{project_id}/evaluation")
L443: def record_evaluation(project_id: str, payload: HumanEvalIn) -> dict[str, Any]:
L444:     from .benchmark import evaluation as evaluation_mod
L445: 
L446:     engine = get_engine(project_id)
L447:     try:
L448:         content = evaluation_mod.record(engine, payload.model_dump())
L449:     except ValueError as exc:
L450:         return JSONResponse(status_code=409, content={"ok": False, "reason": str(exc)})
L451:     return content

## Same-directory worksheet verification
A kit and its colocated worksheet both bind run_77e357790d91. B both bind run_8c3ffb4d0a85. C both bind run_ec5bff2ee0c1. All these colocated worksheets are blank. The different A worksheet in the initial packet was explicitly labeled separate_worksheet_run.
