"""M6 §30–§34 / §62：人工评价入口。

人工评分必须以 Artifact 形式落库（对话/评分不是系统状态，产物才是），
并同步更新 `registry/performance.json`（§19/§40 要求绑定 skill 版本）。
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from typing import Any

from .. import config
from ..store import now_iso

RUBRIC_DIMENSIONS = (
    "subject_accuracy",
    "teaching_logic",
    "goal_clarity",
    "content_alignment",
    "concept_clarity",
    "case_quality",
    "executability",
    "student_engagement",
    "cognitive_challenge",
    "assessment_design",
    "language_naturalness",
    "visual_necessity",
    "coherence",
    "teacher_usability",
)
OPTIONAL_DIMENSIONS = ("spoken_naturalness",)
EDIT_CATEGORIES = (
    "fact correction",
    "teaching restructure",
    "tone edit",
    "case replacement",
    "media correction",
    "assessment correction",
    "template correction",
)
EDIT_SEVERITIES = ("S0", "S1", "S2", "S3", "S4", "S5")


def validate_eval(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("role", "teacher") != "teacher" or payload.get("evaluation_kind", "human") != "human":
        errors.append("human_eval 只接受真人教师评价；AI 审计必须单独保存")
    if not str(payload.get("reviewer") or "").strip():
        errors.append("必须提供 reviewer（至少一位真实教师）")
    scores = payload.get("scores") or {}
    if not isinstance(scores, dict) or not scores:
        errors.append("必须提供 scores")
    else:
        missing = [key for key in RUBRIC_DIMENSIONS if scores.get(key) is None]
        if missing:
            errors.append("缺少必填评分维度：" + ", ".join(missing))
        for dimension, value in scores.items():
            if dimension in OPTIONAL_DIMENSIONS and value is None:
                continue
            if dimension not in RUBRIC_DIMENSIONS + OPTIONAL_DIMENSIONS:
                errors.append(f"未知评分维度：{dimension}")
                continue
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                errors.append(f"{dimension} 不是数字：{value}")
                continue
            if not 1 <= numeric <= 5:
                errors.append(f"{dimension} 超出 1–5：{value}")
    if not str(payload.get("comment") or "").strip():
        errors.append("必须提供 comment（文字备注，不能只有数字）")
    edits = payload.get("edits") or {}
    for entry in edits.get("items", []) if isinstance(edits, dict) else []:
        if entry.get("category") and entry["category"] not in EDIT_CATEGORIES:
            errors.append(f"未知修改类别：{entry['category']}")
        if entry.get("severity") and entry["severity"] not in EDIT_SEVERITIES:
            errors.append(f"未知严重度：{entry['severity']}")
    return errors


def overall_score(payload: dict[str, Any]) -> float | None:
    scores = payload.get("scores") or {}
    if any(scores.get(key) is None for key in RUBRIC_DIMENSIONS):
        return None
    values = [float(scores[key]) for key in RUBRIC_DIMENSIONS]
    return round(sum(values) / len(values), 3)


def target_for_run(store: Any, run_id: str) -> dict[str, Any]:
    """Resolve immutable run outputs and its baseline, never another run's outputs."""
    run = store.get_run(run_id)
    if run["project_id"] != store.project_id:
        raise ValueError("run_id 不属于当前项目")
    baseline = json.loads(run.get("baseline") or "{}")
    direct_artifact = (run.get("inputs") or {}).get("direct_artifact")
    artifacts = {}
    for item in store.list_artifacts():
        if direct_artifact and item["artifact_id"] != direct_artifact:
            continue
        if item["artifact_type"] in ("review_record", "ai_review"):
            continue
        aid = item["artifact_id"]
        revision = store.get_revision(baseline[aid]) if baseline.get(aid) else None
        for rid in store.revisions_of(aid):
            candidate = store.get_revision(rid)
            if candidate.get("produced_by_run") == run_id:
                revision = candidate
        if revision:
            artifacts[aid] = {
                "revision_id": revision["revision_id"],
                "content_hash": revision["content_hash"],
                "artifact_type": revision["artifact_type"],
                "rules_version": revision.get("rules_version"),
            }
    return {
        "format": 1, "project_id": store.project_id, "run_id": run_id,
        "rules_version": config.RULES_VERSION, "artifacts": artifacts,
    }


def target_is_current(store: Any, target: dict[str, Any]) -> bool:
    if not target or not target.get("artifacts") or target.get("project_id") != store.project_id:
        return False
    if target.get("rules_version") != config.RULES_VERSION:
        return False
    for aid, expected in target["artifacts"].items():
        rid = store.accepted_rev_id(aid)
        if not rid:
            revisions = store.revisions_of(aid)
            rid = revisions[-1] if revisions else None
        if rid != expected.get("revision_id") or store.is_stale(aid):
            return False
        if store.get_revision(rid)["content_hash"] != expected.get("content_hash"):
            return False
    return True


def for_run(store: Any, run_id: str) -> dict[str, Any] | None:
    """Read a run-specific evaluation; unbound legacy records remain visibly stale."""
    content = store.accepted_content(f"human_eval:{run_id}") if run_id else None
    if content is None:
        legacy = store.accepted_content("human_eval")
        if legacy:
            content = legacy
    if not isinstance(content, dict):
        return None
    human = dict(content)
    human["stale"] = (
        human.get("evaluation_kind") != "human" or human.get("role") != "teacher"
        or not run_id or human.get("run_id") != run_id
        or not target_is_current(store, human.get("target") or {})
    )
    return human


def record(engine: Any, payload: dict[str, Any], *, run_id: str = "", mode: str = "") -> dict[str, Any]:
    from . import metrics

    errors = validate_eval(payload)
    if errors:
        raise ValueError("；".join(errors))
    from ..store import StoreError

    if not run_id:
        raise ValueError("必须提供受评 run_id")
    try:
        run = engine.store.get_run(run_id)
    except StoreError as exc:
        raise ValueError("run_id 不属于当前项目") from exc
    if run["project_id"] != engine.project_id or run["status"] != "succeeded":
        raise ValueError("只能评价当前项目中已完成的运行")
    expected_mode = str((run.get("inputs") or {}).get("planner") or "builtin")
    expected_mode = "builtin" if expected_mode == "static" else expected_mode
    if mode and mode != expected_mode:
        raise ValueError("mode 与受评运行不一致")
    mode = expected_mode
    target = target_for_run(engine.store, run_id)
    supplied_target = payload.get("target")
    if not supplied_target:
        raise ValueError("必须提供受评材料的 target；请从评价 API 或冻结材料包获取")
    if supplied_target != target:
        raise ValueError("受评产物版本已变化，请重新获取评价材料")
    if not target_is_current(engine.store, target):
        raise ValueError("受评产物已过期或尚未就绪")
    if any(item["artifact_type"] == "script" for item in target["artifacts"].values()):
        if (payload.get("scores") or {}).get("spoken_naturalness") is None:
            raise ValueError("脚本评价必须提供 spoken_naturalness")
    edits = payload.get("edits") or {}
    generated = str(edits.get("generated_text") or "")
    edited = str(edits.get("edited_text") or "")
    ratio = None
    if generated and edited:
        ratio = metrics.teacher_edit_ratio(generated, edited)["edit_ratio"]
    elif edits.get("edit_ratio") is not None:
        ratio = float(edits["edit_ratio"])
    severity_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    for entry in edits.get("items", []):
        severity = str(entry.get("severity") or "")
        category = str(entry.get("category") or "")
        if severity:
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        if category:
            category_counts[category] = category_counts.get(category, 0) + 1
    content = {
        "evaluation_kind": "human",
        "target": target,
        "reviewer": payload["reviewer"],
        "role": str(payload.get("role") or "teacher"),
        "scores": {key: float(value) for key, value in (payload.get("scores") or {}).items() if value is not None},
        "overall": overall_score(payload),
        "comment": payload.get("comment", ""),
        "must_fix": list(payload.get("must_fix") or []),
        "nice_to_have": list(payload.get("nice_to_have") or []),
        "edit_ratio": ratio,
        "major_edit_rate": (
            round((severity_counts.get("S4", 0) + severity_counts.get("S5", 0)) / max(sum(severity_counts.values()), 1), 3)
            if severity_counts
            else None
        ),
        "edit_severities": severity_counts,
        "edit_categories": category_counts,
        "evidence_errors": int(payload.get("evidence_errors") or 0),
        "routing_errors": int(payload.get("routing_errors") or 0),
        "plan_errors": int(payload.get("plan_errors") or 0),
        "run_id": run_id,
        "mode": mode,
        "rubric": "benchmarks/rubrics/human_eval.yaml",
    }
    content["evaluation_id"] = hashlib.sha256(json.dumps({
        "target": target, "reviewer": payload["reviewer"],
    }, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    submission = hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    existing = engine.store.accepted_content(f"human_eval:{run_id}")
    if existing and existing.get("submission_hash") == submission and existing.get("binding", {}).get("status") == "BOUND":
        return existing
    content["submission_hash"] = submission
    content["created_at"] = now_iso()
    content["binding"] = {"status": "PENDING"}
    info = engine.store.add_revision(
        artifact_id=f"human_eval:{run_id}",
        artifact_type="review_record",
        content=content,
        produced_by=f"teacher:{payload['reviewer']}",
        run_id=run_id,
        deps=[item["revision_id"] for item in target["artifacts"].values()],
        rules_version=config.RULES_VERSION,
    )
    engine.store.set_accepted(f"human_eval:{run_id}", info["revision_id"])
    # §40：评分必须绑定到具体 skill 版本，否则升级后历史数据失效。
    # 之前 update_performance 只在测试里被调用，真实提交（CLI/API）从不更新 registry。
    try:
        from . import trace as trace_mod

        skill_trace = trace_mod.build_trace(engine, run_id, mode=mode)
        update_performance(engine, skill_trace, content)
        content["binding"] = {"status": "BOUND"}
    except Exception as exc:  # Record failure without exposing provider details or losing the score.
        content["binding"] = {"status": "FAILED", "error_type": type(exc).__name__}
    final = engine.store.add_revision(
        artifact_id=f"human_eval:{run_id}", artifact_type="review_record", content=content,
        produced_by=f"teacher:{payload['reviewer']}", run_id=run_id,
        deps=[item["revision_id"] for item in target["artifacts"].values()], rules_version=config.RULES_VERSION,
    )
    engine.store.set_accepted(f"human_eval:{run_id}", final["revision_id"])
    return content


def _gate_lines(store: Any, target: dict[str, Any] | None = None) -> list[str]:
    """把该 run 的门禁结论放进材料包：教师能看到系统自己认为哪里不合格。"""
    rows: list[tuple[str, str, list[str]]] = []
    for item in store.list_artifacts():
        if item["artifact_type"] != "gate_result":
            continue
        # 门禁结果不一定随 changeset 被 accept，取该产物的最新 revision
        bound = (target or {}).get("artifacts", {}).get(item["artifact_id"])
        if target is not None and not bound:
            continue
        revisions = [bound["revision_id"]] if bound else store.revisions_of(item["artifact_id"])
        if not revisions:
            continue
        content = store.get_revision(revisions[-1])["content"]
        if not isinstance(content, dict):
            continue
        rows.append(
            (
                f"{content.get('gate_id')}@{str((content.get('target') or {}).get('artifact_id') or '')}",
                str(content.get("status") or ""),
                [str(issue.get("reason") or "") for issue in content.get("issues") or []],
            )
        )
    if not rows:
        return []
    lines = ["## 门禁结论（供教师核对，不是评分）", ""]
    for gate_id, status, reasons in sorted(rows):
        lines.append(f"- **{gate_id}: {status}**" + (f" — {'；'.join(reasons[:3])}" if reasons else ""))
    lines.append("")
    return lines


def _auto_issue_lines(run: dict[str, Any]) -> list[str]:
    """自动检查命中的问题：教师需要逐条确认"真的有问题"还是"误报"。"""
    issues = (run.get("automatic_issues") or {}).get("issues") or []
    if not issues:
        return []
    lines = [
        "## 自动检查命中的问题（请在 comment / must_fix 中说明是真问题还是误报）",
        "",
        "| 类别 | 说明 |",
        "| --- | --- |",
    ]
    for issue in issues[:20]:
        detail = str(issue.get("detail") or "").replace("|", "/")
        lines.append(f"| {issue.get('kind')} | {detail[:200]} |")
    lines.append("")
    return lines


def export_kit(runs: list[dict[str, Any]] | None = None, *, directory: Any = None) -> list[dict[str, Any]]:
    """§30/§31：把待评课程导出成教师可直接阅读的材料包 + 评分表。

    教师不需要运行 PEBS：每个 run 一个目录，含 course.md（关键产物）、run.json 摘要与
    human_eval.yaml（待填）。course.md 同时给出**门禁结论**与**自动检查命中的问题**，
    这样教师既能读到课程本身，也能确认/推翻系统自己的判断。
    """
    from pathlib import Path

    from ..store import Store
    from . import report as report_mod

    runs = runs if runs is not None else report_mod.load_runs()
    target_dir = Path(directory) if directory else (Path(__file__).resolve().parents[2] / "benchmarks" / "reports" / "evaluation_kit")
    target_dir.mkdir(parents=True, exist_ok=True)
    exported: list[dict[str, Any]] = []
    for run in runs:
        if not report_mod.is_evaluable(run):
            continue
        project_id = str(run.get("project_id") or "")
        if not project_id:
            continue
        case_id = str(run.get("case_id") or "?")
        variant = str(run.get("_variant") or run.get("mode") or "?")
        slug = re.sub(r"[^a-zA-Z0-9_.-]", "_", f"{case_id}-{variant}")[:100]
        store = None
        if run.get("mode") == "direct_codex" or (config.project_dir(project_id) / "state.db").exists():
            store = Store(project_id, config.project_dir(project_id))
        try:
            direct_output = _direct_output_text(run) if run.get("mode") == "direct_codex" else ""
            if run.get("mode") == "direct_codex":
                imported_run_id = _import_direct_output(store, run, direct_output)
                run = {**run, "run_id": imported_run_id, "source_run_id": run.get("run_id")}
            target = target_for_run(store, str(run.get("run_id") or "")) if store else None
            if target is None:
                if not direct_output:
                    raise ValueError(f"{case_id}/{variant} 缺少可追溯的课程产物")
                raise ValueError("受评项目缺少可追溯的 Store")
            for aid, digest in (run.get("artifact_hashes") or {}).items():
                if target["artifacts"].get(aid, {}).get("content_hash") != digest:
                    raise ValueError(f"{case_id}/{variant} 的运行摘要与产物版本不一致：{aid}")
            target_key = hashlib.sha256(json.dumps(target, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
            run_slug = re.sub(r"[^a-zA-Z0-9_.-]", "_", str(run.get("run_id") or "direct"))[:80]
            base = target_dir / slug / f"{run_slug}-{target_key}"
            if base.exists():
                import yaml

                manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
                worksheets = list(base.glob("*-human_eval.yaml"))
                if manifest["target"] != target or len(worksheets) != 1:
                    raise ValueError("已有评价材料包身份不一致，拒绝覆盖")
                for name in ("course.md", "run.json"):
                    if hashlib.sha256((base / name).read_bytes()).hexdigest() != manifest.get("files", {}).get(name):
                        raise ValueError(f"已有评价材料包已被修改：{name}；拒绝覆盖")
                sheet = yaml.safe_load(worksheets[0].read_text(encoding="utf-8"))
                if sheet.get("target") != target or sheet.get("run", {}).get("run_id") != target["run_id"]:
                    raise ValueError("已有评分表版本不一致，拒绝覆盖")
                exported.append({"case_id": case_id, "variant": variant, "dir": str(base), "worksheet": str(worksheets[0])})
                continue
            content_by_id = {
                aid: store.get_revision(ref["revision_id"])["content"]
                for aid, ref in target["artifacts"].items()
            } if store else {}
            gate_lines = _gate_lines(store, target) if store else []
        finally:
            if store is not None:
                store.close()
        lines = [
            f"# {case_id} / {variant}",
            "",
            f"- run: {run.get('run_id')} status={run.get('run_status')}",
            f"- 模式：{run.get('mode')} 实验：{run.get('experiment') or '（无）'}",
            f"- 模型调用：{(run.get('metrics') or {}).get('model_calls')} 研究请求：{(run.get('metrics') or {}).get('research_calls')}",
            f"- 证据政策：{run.get('evidence_policy')}",
            "",
            "> 评分说明见同目录 human_eval.yaml 与 benchmarks/reports/evaluation_kit/README.md",
            "",
        ]
        lines.extend(_auto_issue_lines(run))
        lines.extend(gate_lines)
        # direct_codex 基线没有 Store：它的产物是 run 目录里的 direct_output.md。
        # 教师必须能评到它，否则 §28 的三模式对比在人工评分维度上是缺一条腿的。
        if direct_output:
            lines.append("## direct_output.md（Direct Codex 基线原始输出）")
            lines.append("")
            lines.append(direct_output)
            lines.append("")
        for artifact_id, content in content_by_id.items():
            if target["artifacts"][artifact_id]["artifact_type"] not in {
                "lesson_plan", "script", "slide_plan", "pptx_deck", "assessment", "case",
                "learning_design", "teaching_plan", "evidence_index", "media_plan", "load_review",
            }:
                continue
            lines.append(f"## {artifact_id}")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(content, ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")
        base.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".kit-", dir=base.parent) as staging:
            stage = Path(staging)
            (stage / "course.md").write_text("\n".join(lines), encoding="utf-8")
            (stage / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            worksheets = report_mod.write_worksheets([{**run, "evaluation_target": target, "evaluation_package": True}], directory=stage)
            if len(worksheets) != 1:
                raise ValueError("无法生成唯一的评分表")
            worksheet_name = worksheets[0].name
            (stage / "manifest.json").write_text(json.dumps({
                "format": 1, "target": target,
                "files": {name: hashlib.sha256((stage / name).read_bytes()).hexdigest()
                          for name in ("course.md", "run.json")},
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            stage.rename(base)
        exported.append({"case_id": case_id, "variant": variant, "dir": str(base), "worksheet": str(base / worksheet_name)})
    return exported


def _has_store_artifacts(store: Any) -> bool:
    if store is None:
        return False
    try:
        return bool(store.list_artifacts())
    except Exception:  # noqa: BLE001
        return False


def _direct_output_text(run: dict[str, Any]) -> str:
    """Read the complete Direct baseline, so the teacher sees all scored content."""
    from pathlib import Path

    run_dir = str(run.get("run_dir") or "")
    if not run_dir:
        return ""
    path = Path(run_dir) / "direct_output.md"
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _direct_artifact_id(run: dict[str, Any]) -> str:
    from pathlib import Path

    origin = str(Path(run["run_dir"]).resolve())
    return "direct_output:" + hashlib.sha256(origin.encode()).hexdigest()[:24]


def direct_evaluation_run(store: Any, run: dict[str, Any]) -> str:
    """Resolve an imported Direct snapshot without creating anything on report reads."""
    if not run.get("run_dir"):
        return ""
    revision = store.accepted_revision(_direct_artifact_id(run))
    if not revision or revision["content"].get("text") != _direct_output_text(run):
        return ""
    return str(revision.get("produced_by_run") or "")


def _import_direct_output(store: Any, run: dict[str, Any], text: str) -> str:
    """Import an existing baseline for evaluation; no generation or fabricated model run."""
    if not text.strip():
        raise ValueError("Direct baseline 没有课程内容")
    existing = direct_evaluation_run(store, run)
    if existing:
        return existing
    aid = _direct_artifact_id(run)
    run_id = store.create_run(
        environment=str(run.get("environment") or "production"),
        inputs={"planner": "direct_codex", "evaluation_import": True,
                "direct_artifact": aid, "source_run_dir": run["run_dir"]},
    )
    revision = store.add_revision(
        artifact_id=aid, artifact_type="benchmark_output", content={"text": text},
        produced_by="benchmark-evaluation-import", run_id=run_id,
        fixture=run.get("environment") == "test_fixture", rules_version=config.RULES_VERSION,
    )
    store.set_accepted(aid, revision["revision_id"])
    store.set_run_status(run_id, "succeeded")
    return run_id


def latest(engine: Any) -> dict[str, Any] | None:
    run = engine.store.latest_run()
    return for_run(engine.store, run["run_id"] if run else "")


def update_performance(engine: Any, trace: dict[str, Any], human: dict[str, Any]) -> None:
    """把人工结果绑定到 skill 版本（§40）写入 performance registry。"""
    from . import performance

    performance.record_evaluation(trace, human)
