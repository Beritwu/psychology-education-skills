# Response to review, final verification
Your findings 1/3/4/5/6/7/8 have been addressed with public-seam red/green tests. Note 2: all static+dynamic skill steps resolve in existing integration tests. An unresolved step is now labeled unresolved_step and remains FAILED rather than silently dropping execution provenance. BOUND for a historical version means exact identity saved in human_evaluations ledger; it deliberately does not overwrite the current skill version record. Real teachers still PENDING. Full suite before these final followups:520 passed. Targeted final regression running. Review only the delta below against prior review packet, not broad new areas. Return any remaining demonstrable P1/P2 regressions in changed paths; otherwise state no additional confirmed issue with static-review limits. No execution or teacher claims.

--- pebs/benchmark/evaluation.py(reviewed)
+++ pebs/benchmark/evaluation.py(current)
@@ -423,7 +423,7 @@
             stage = Path(staging)
             (stage / "course.md").write_text("\n".join(lines), encoding="utf-8")
             (stage / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
-            worksheets = report_mod.write_worksheets([{**run, "evaluation_target": target}], directory=stage)
+            worksheets = report_mod.write_worksheets([{**run, "evaluation_target": target, "evaluation_package": True}], directory=stage)
             if len(worksheets) != 1:
                 raise ValueError("无法生成唯一的评分表")
             worksheet_name = worksheets[0].name
--- pebs/benchmark/performance.py(reviewed)
+++ pebs/benchmark/performance.py(current)
@@ -9,6 +9,8 @@
 import os
 import tempfile
 import time
+import sqlite3
+from functools import wraps
 from threading import RLock
 from pathlib import Path
 from typing import Any
@@ -17,6 +19,23 @@
 
 MODES = ("direct_codex", "builtin", "dynamic", "mixed")
 _EVALUATION_LOCK = RLock()
+
+
+def _serialized_update(function):
+    """Serialize JSON read/modify/replace across threads and CLI/server processes."""
+    @wraps(function)
+    def wrapped(*args, **kwargs):
+        with _EVALUATION_LOCK:
+            directory = Path(config.REGISTRY_DIR)
+            directory.mkdir(parents=True, exist_ok=True)
+            connection = sqlite3.connect(directory / "performance.lock.sqlite3", timeout=30)
+            try:
+                connection.execute("BEGIN IMMEDIATE")
+                return function(*args, **kwargs)
+            finally:
+                connection.rollback()
+                connection.close()
+    return wrapped
 
 PROMOTION_THRESHOLD = {
     "min_runs": 10,
@@ -54,6 +73,7 @@
     return path
 
 
+@_serialized_update
 def record_evaluation(trace: dict[str, Any], human: dict[str, Any]) -> None:
     """Idempotent human-score ledger. Evaluating is not an additional build run."""
     if human.get("evaluation_kind") != "human" or human.get("role") != "teacher":
@@ -118,6 +138,7 @@
     }
 
 
+@_serialized_update
 def record_run(
     *,
     skill: str,
@@ -134,9 +155,17 @@
     failure_mode: str = "",
     human_score: float | None = None,
     edit_ratio: float | None = None,
+    run_key: str = "",
 ) -> dict[str, Any]:
     data = load_performance()
+    if run_key and run_key in data.get("build_records", {}):
+        return data["build_records"][run_key]
     record = data["skills"].get(skill) or _empty_record(skill, version)
+    identity = {"version": version, "provider_sha": provider_sha,
+                "package_sha256": package_sha256, "patch": patch}
+    if version and any(record.get(key, "") != value for key, value in identity.items()):
+        data.setdefault("skill_history", []).append(dict(record))
+        record = {**_empty_record(skill, version), **identity}
     if version:
         record["version"] = version
     if provider_sha:
@@ -177,6 +206,8 @@
     modes = list(dict.fromkeys(list(record.get("known_failure_modes", [])) + ([failure_mode] if failure_mode else [])))
     record["known_failure_modes"] = modes[-10:]
     data["skills"][skill] = record
+    if run_key:
+        data.setdefault("build_records", {})[run_key] = dict(record)
     save_performance(data)
     return record
 
@@ -197,7 +228,18 @@
     latency_by_skill = latency_by_skill or {}
     model_calls_by_skill = model_calls_by_skill or {}
     recorded: list[dict[str, Any]] = []
+    grouped: dict[tuple[str, ...], dict[str, Any]] = {}
     for skill in trace.get("skills", []):
+        identity = tuple(str(skill.get(key) or "") for key in ("skill", "version", "upstream_sha", "package_sha256", "patch"))
+        if identity not in grouped:
+            grouped[identity] = dict(skill)
+        else:
+            merged = grouped[identity]
+            merged["schema_repairs"] = int(merged.get("schema_repairs") or 0) + int(skill.get("schema_repairs") or 0)
+            if skill.get("status") != "SUCCEEDED":
+                merged["status"] = skill.get("status")
+                merged["error"] = skill.get("error")
+    for identity, skill in grouped.items():
         name = str(skill.get("skill") or "")
         if not name:
             continue
@@ -219,6 +261,7 @@
                 failure_mode=(error[:120] if status in ("FAILED", "BLOCKED") else ""),
                 human_score=human_score,
                 edit_ratio=edit_ratio,
+                run_key=json.dumps([trace["run_id"], *identity]) if trace.get("run_id") else "",
             )
         )
     return recorded
--- pebs/benchmark/report.py(reviewed)
+++ pebs/benchmark/report.py(current)
@@ -311,6 +311,8 @@
             }
         table.append(entry)
     summary = {"generated_at": _now(), "cases": table, "runs": len(rows), "rows": rows}
+    summary["failure_category_lines"] = failure_category_section(runs)
+    summary["quality_lines"] = quality_section(runs)
     summary["mode_comparison"] = mode_comparison(summary)
     return summary
 
@@ -499,7 +501,7 @@
                 lines.append(f"| | 教师：{('、'.join(reviewers)) or '—'}{note} | | | | | | | | | | | |")
     lines.extend(budget_mismatch_notes(summary))
     lines.extend(render_mode_comparison(summary))
-    lines.extend(failure_category_section())
+    lines.extend(summary.get("failure_category_lines", []))
     lines.extend(_gate_audit_section())
     if any(
         case.get(variant, {}).get("code_version_current") is not True
@@ -516,7 +518,7 @@
                 "> `tools/reevaluate_checks.py` 在当前代码上重放已存项目。",
             ]
         )
-    lines.extend(quality_section())
+    lines.extend(summary.get("quality_lines", []))
     lines.extend(performance_section())
     lines.append("")
     return "\n".join(lines)
@@ -528,9 +530,13 @@
         return True
     if str(data.get("comment") or "").strip():
         return True
+    if any(data.get(key) for key in ("must_fix", "nice_to_have", "evidence_errors", "routing_errors", "plan_errors")):
+        return True
     if any(value is not None for value in (data.get("scores") or {}).values()):
         return True
     edits = data.get("edits") or {}
+    if edits.get("edit_ratio") is not None:
+        return True
     if str(edits.get("generated_text") or "").strip() or str(edits.get("edited_text") or "").strip():
         return True
     return any(item.get("category") or item.get("severity") for item in (edits.get("items") or []))
@@ -572,6 +578,28 @@
         if not is_evaluable(run):
             # 失败/无产物的 run 不生成评分表：教师无法给一份不存在的课程打 14 个维度分，
             # 它的信息已经在报告的 Status / Attempts / Auto Issues 列里
+            continue
+        target = run.get("evaluation_target")
+        if not target and run.get("project_id"):
+            from .. import config
+            from ..store import Store, StoreError
+            from . import evaluation
+
+            base = config.project_dir(str(run["project_id"]))
+            if (base / "state.db").exists():
+                store = Store(str(run["project_id"]), base)
+                try:
+                    rid = (evaluation.direct_evaluation_run(store, run) if run.get("mode") == "direct_codex"
+                           else str(run.get("run_id") or ""))
+                    if rid:
+                        target = evaluation.target_for_run(store, rid)
+                        run = {**run, "run_id": rid}
+                except StoreError:
+                    pass
+                finally:
+                    store.close()
+        if not target:
+            # Do not ask a teacher to fill a sheet that cannot be submitted.
             continue
         case_id = str(run.get("case_id") or "?")
         mode = str(run.get("mode") or "?")
@@ -585,11 +613,12 @@
             try:
                 existing = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
             except yaml.YAMLError:
-                existing = {}
-            if _worksheet_is_filled(existing):
+                continue  # Malformed teacher input is still irreplaceable input.
+            if not isinstance(existing, dict) or _worksheet_is_filled(existing):
                 continue
         template = {
-            "target": run.get("evaluation_target"),
+            "package_manifest": "manifest.json" if run.get("evaluation_package") else None,
+            "target": target,
             "evaluation_kind": "human",
             "run": {
                 "case_id": case_id,
@@ -657,8 +686,15 @@
     """把教师填写的工作表转换成 /evaluation 的 payload。"""
     import yaml
 
-    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
+    try:
+        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
+    except yaml.YAMLError as exc:
+        raise ValueError("评分表 YAML 格式错误，请检查缩进和括号") from exc
+    if not isinstance(data, dict):
+        raise ValueError("评分表必须是 YAML 对象")
     manifest_path = Path(path).parent / "manifest.json"
+    if (data.get("package_manifest") or (Path(path).parent / "course.md").exists()) and not manifest_path.exists():
+        raise ValueError("冻结材料缺少 manifest.json；请恢复完整原包")
     if manifest_path.exists():
         manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
         if manifest.get("target") != data.get("target") or (data.get("run") or {}).get("run_id") != (data.get("target") or {}).get("run_id"):
--- pebs/benchmark/trace.py(reviewed)
+++ pebs/benchmark/trace.py(current)
@@ -205,8 +205,14 @@
             {"artifact_id": rev["artifact_id"], "revision_id": rev["revision_id"], "content_hash": rev["content_hash"]}
         )
 
-    route = store.accepted_content("router_result") or {}
-    plan = store.accepted_content("build_plan_dynamic") or {}
+    from .evaluation import target_for_run
+
+    target = target_for_run(store, run_id)["artifacts"]
+    def run_content(aid: str) -> dict[str, Any]:
+        return store.get_revision(target[aid]["revision_id"])["content"] if aid in target else {}
+
+    route = run_content("router_result")
+    plan = run_content("build_plan_dynamic")
     skills: list[dict[str, Any]] = []
     snapshot = _run_inputs(run).get("skill_snapshot")
     node_by_skill: dict[str, dict[str, Any]] = {}
@@ -233,7 +239,7 @@
             identity = snapshot["identities"][skill_name]
         # §39：优先用执行器记录的 input_revs/output_revs（精确到 revision，含失败节点）；
         # 旧数据没有这些列，回退到按 produced_by 反查（只到 artifact_id，且需去重）。
-        node = node_by_skill.get(step["step_id"]) or {}
+        node = node_by_skill.get(skill_name) or {}
         stored_inputs = _parse_rev_list(step.get("input_revs"))
         stored_outputs = _parse_rev_list(step.get("output_revs"))
         if stored_inputs or stored_outputs:
@@ -247,7 +253,8 @@
         skills.append(
             {
                 **identity,
-                "identity_source": "run_snapshot" if snapshot is not None else "current_registry",
+                "identity_source": ("unresolved_step" if not resolved else
+                                    "run_snapshot" if snapshot is not None else "current_registry"),
                 "step_id": step["step_id"],
                 "status": step["status"],
                 "attempts": step.get("attempts", 0),
@@ -271,9 +278,9 @@
 
     gate_results = []
     for artifact in store.list_artifacts():
-        if artifact["artifact_type"] != "gate_result" or not artifact.get("accepted_rev"):
+        if artifact["artifact_type"] != "gate_result" or artifact["artifact_id"] not in target:
             continue
-        content = store.accepted_content(artifact["artifact_id"]) or {}
+        content = run_content(artifact["artifact_id"])
         gate_results.append(
             {
                 "gate": content.get("gate_id"),
@@ -288,6 +295,9 @@
         if artifact["artifact_type"] != "review_record" or not artifact.get("accepted_rev"):
             continue
         content = store.accepted_content(artifact["artifact_id"]) or {}
+        revision = store.get_revision(artifact["accepted_rev"])
+        if revision.get("produced_by_run") != run_id:
+            continue
         human_review.append(
             {
                 "changeset_id": content.get("changeset_id"),
--- tests/test_evaluation_integrity.py(reviewed)
+++ tests/test_evaluation_integrity.py(current)
@@ -269,7 +269,6 @@
 def test_teacher_binding_keeps_build_time_skill_version_after_registry_upgrade(client):
     import json
     from pebs import config
-    from pebs.benchmark import performance
 
     engine, run_id = _prepared_project(client, "skill-provenance")
     engine.store.add_step(run_id, "script-writer", "Script", status="SUCCEEDED")
@@ -284,8 +283,26 @@
         target=before["evaluation_target"], run_id=run_id, mode="dynamic"))
     assert response.status_code == 200, response.text
     assert response.json()["binding"]["status"] == "BOUND"
-    stored = performance.load_performance()["human_evaluations"][response.json()["evaluation_id"]]
-    assert stored["skills"][0]["version"] == version
+    stored = client.get("/api/projects/skill-provenance/evaluation").json()
+    assert stored["trace"]["skills"][0]["version"] == version
+    assert stored["performance"]["script-writer"]["version"] == version
+
+
+def test_new_skill_build_does_not_inherit_an_older_versions_teacher_score(client):
+    from pebs.benchmark import performance
+
+    engine, run_id = _prepared_project(client, "new-skill-score")
+    engine.store.add_step(run_id, "script-writer", "Script", status="SUCCEEDED")
+    before = client.get("/api/projects/new-skill-score/evaluation").json()
+    response = client.post("/api/projects/new-skill-score/evaluation", json=_valid_payload(
+        target=before["evaluation_target"], run_id=run_id, mode="dynamic"))
+    assert response.json()["binding"]["status"] == "BOUND"
+    # A newly recorded build is the event that changes the displayed skill version.
+    performance.record_run(skill="script-writer", version="999.0", success=True)
+    current = client.get("/api/projects/new-skill-score/evaluation").json()["performance"]["script-writer"]
+    assert current["version"] == "999.0"
+    assert current["human_score"] is None
+    assert current["teacher_edit_ratio"] is None
 
 
 def test_evaluation_api_can_retrieve_an_older_run_without_using_the_latest_score(client):
@@ -322,3 +339,97 @@
     (Path(package["dir"]) / "course.md").write_text("Replaced after export", encoding="utf-8")
     assert cli.main(["benchmark", "--submit-eval", str(sheet), "--project", engine.project_id]) != 0
     assert client.get("/api/projects/changed-package/evaluation").json()["human_eval"] is None
+
+
+def test_plain_worksheet_export_resolves_the_reviewed_target(client, tmp_path):
+    from pebs.benchmark import report
+
+    engine, run_id = _prepared_project(client, "plain-worksheet")
+    artifact = engine.store.accepted_revision("lesson_plan:sec1")
+    run = {"project_id": engine.project_id, "run_id": run_id, "case_id": "A", "mode": "dynamic",
+           "run_status": "succeeded", "artifact_hashes": {"lesson_plan:sec1": artifact["content_hash"]}}
+    paths = report.write_worksheets([run], directory=tmp_path / "worksheets")
+    payload = report.load_worksheet(paths[0])
+    assert payload["target"] == client.get("/api/projects/plain-worksheet/evaluation").json()["evaluation_target"]
+
+
+@pytest.mark.parametrize("field,value", [("must_fix", ["Keep this feedback"]), ("evidence_errors", 2), ("invalid_yaml", "scores: [")])
+def test_worksheet_export_preserves_partial_or_malformed_teacher_input(client, tmp_path, field, value):
+    import yaml
+    from pebs.benchmark import report
+
+    engine, run_id = _prepared_project(client, "partial-feedback")
+    artifact = engine.store.accepted_revision("lesson_plan:sec1")
+    run = {"project_id": engine.project_id, "run_id": run_id, "case_id": "A", "mode": "dynamic",
+           "run_status": "succeeded", "artifact_hashes": {"lesson_plan:sec1": artifact["content_hash"]}}
+    path = report.write_worksheets([run], directory=tmp_path / "worksheets")[0]
+    sheet = yaml.safe_load(path.read_text(encoding="utf-8"))
+    sheet[field] = value
+    path.write_text(value if field == "invalid_yaml" else yaml.safe_dump(sheet), encoding="utf-8")
+    before = path.read_bytes()
+    report.write_worksheets([run], directory=path.parent)
+    assert path.read_bytes() == before
+
+
+def test_historical_evaluation_trace_reads_that_runs_route(client):
+    engine, run_id = _prepared_project(client, "historical-route")
+    for rid, intent in [(run_id, "Original course"),
+                        (engine.store.create_run(inputs={"planner": "dynamic"}), "New course")]:
+        revision = engine.store.add_revision(artifact_id="router_result", artifact_type="router_result",
+            content={"task_intent": intent}, produced_by="dynamic-planner", run_id=rid)
+        engine.store.set_accepted("router_result", revision["revision_id"])
+        engine.store.set_run_status(rid, "succeeded")
+    historical = client.get("/api/projects/historical-route/evaluation", params={"run_id": run_id})
+    assert historical.json()["trace"]["route"]["task_intent"] == "Original course"
+
+
+def test_rendered_report_keeps_the_same_run_set_as_its_summary(tmp_path, monkeypatch):
+    import json
+    from pebs.benchmark import report, cases
+
+    run_dir = tmp_path / "runs" / "20261028-010000-A-dynamic"
+    run_dir.mkdir(parents=True)
+    global_run = {"case_id": "A", "mode": "dynamic", "run_status": "succeeded",
+                  "automatic_issues": {"counts": {"UNRELATED_GLOBAL_FAILURE": 1}}}
+    (run_dir / "run.json").write_text(json.dumps(global_run), encoding="utf-8")
+    monkeypatch.setattr(cases, "runs_dir", lambda: run_dir.parent)
+    local_run = {**global_run, "automatic_issues": {"counts": {"LOCAL_ONLY_FAILURE": 1}}}
+    rendered = report.render_markdown(report.summarize([local_run]))
+    assert "LOCAL_ONLY_FAILURE" in rendered
+    assert "UNRELATED_GLOBAL_FAILURE" not in rendered
+
+
+@pytest.mark.parametrize("damage", ["missing_manifest", "invalid_yaml"])
+def test_cli_reports_damaged_evaluation_packages_without_recording_scores(client, tmp_path, capsys, damage):
+    from pathlib import Path
+    import yaml
+    from pebs import cli
+    from pebs.benchmark import evaluation
+
+    engine, run_id = _prepared_project(client, "damaged-evaluation")
+    artifact = engine.store.accepted_revision("lesson_plan:sec1")
+    run = {"project_id": engine.project_id, "run_id": run_id, "case_id": "A", "mode": "dynamic",
+           "run_status": "succeeded", "artifact_hashes": {"lesson_plan:sec1": artifact["content_hash"]}}
+    package = evaluation.export_kit([run], directory=tmp_path / "kit")[0]
+    path = Path(package["worksheet"])
+    sheet = yaml.safe_load(path.read_text(encoding="utf-8"))
+    sheet.update(_valid_payload())
+    path.write_text(yaml.safe_dump(sheet), encoding="utf-8")
+    if damage == "missing_manifest":
+        (path.parent / "manifest.json").unlink()
+    else:
+        path.write_text("scores: [", encoding="utf-8")
+    assert cli.main(["benchmark", "--submit-eval", str(path), "--project", engine.project_id]) != 0
+    assert client.get("/api/projects/damaged-evaluation/evaluation").json()["human_eval"] is None
+
+
+def test_replaying_a_build_trace_does_not_inflate_displayed_skill_runs(client):
+    from pebs.benchmark import performance
+
+    engine, run_id = _prepared_project(client, "trace-retry")
+    engine.store.add_step(run_id, "script-writer", "Script", status="SUCCEEDED")
+    trace = client.get("/api/projects/trace-retry/evaluation").json()["trace"]
+    performance.record_trace(trace)
+    performance.record_trace(trace)
+    result = client.get("/api/projects/trace-retry/evaluation").json()
+    assert result["performance"]["script-writer"]["runs"] == 1
