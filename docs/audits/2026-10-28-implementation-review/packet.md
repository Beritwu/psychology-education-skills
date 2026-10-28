# Implementation evidence packet
Repository-local code and synthetic tests only. No real student materials or credential files.

## pebs/benchmark/evaluation.py
```python
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
            worksheets = report_mod.write_worksheets([{**run, "evaluation_target": target}], directory=stage)
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

```

## pebs/benchmark/performance.py
```python
"""Skill Performance Registry（M6 §19, §40, §68, §69）。

记录必须绑定 Skill 版本（provider SHA / package hash / patch），否则升级后历史数据失效。
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from threading import RLock
from pathlib import Path
from typing import Any

from .. import config

MODES = ("direct_codex", "builtin", "dynamic", "mixed")
_EVALUATION_LOCK = RLock()

PROMOTION_THRESHOLD = {
    "min_runs": 10,
    "max_schema_failure_rate": 0.1,
    "min_human_score": 3.5,
    "forbid_unresolved_safety": True,
}


def performance_path() -> Path:
    return Path(config.REGISTRY_DIR) / "performance.json"


def load_performance() -> dict[str, Any]:
    path = performance_path()
    if not path.exists():
        return {"format": 1, "skills": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("skills", {})
    return data


def save_performance(data: dict[str, Any]) -> Path:
    path = performance_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return path


def record_evaluation(trace: dict[str, Any], human: dict[str, Any]) -> None:
    """Idempotent human-score ledger. Evaluating is not an additional build run."""
    if human.get("evaluation_kind") != "human" or human.get("role") != "teacher":
        raise ValueError("Only human evaluations may update skill quality metrics")
    if any(skill.get("identity_source") != "run_snapshot" for skill in trace.get("skills", [])):
        raise ValueError("Historical run lacks a build-time skill snapshot; binding requires provenance")
    with _EVALUATION_LOCK:
        data = load_performance()
        entries = data.setdefault("human_evaluations", {})
        entry = {
            "run_id": human["run_id"], "target": human["target"],
            "reviewer": human["reviewer"], "overall": human["overall"],
            "edit_ratio": human.get("edit_ratio"), "skills": trace.get("skills", []),
        }
        evaluation_id = human["evaluation_id"]
        if entries.get(evaluation_id) == entry:
            return
        entries[evaluation_id] = entry
        for skill in trace.get("skills", []):
            name, version = str(skill.get("skill") or ""), str(skill.get("version") or "")
            if not name or not version:
                raise ValueError("Cannot bind an evaluation without a skill version")
            identity = {"version": version, "provider_sha": skill.get("upstream_sha", ""),
                        "package_sha256": skill.get("package_sha256", ""), "patch": skill.get("patch", "")}
            record = data["skills"].get(name) or {**_empty_record(name, version), **identity}
            if any(record.get(key, "") != value for key, value in identity.items()):
                continue
            matching = [item for item in entries.values() if any(
                s.get("skill") == name and s.get("version") == version
                and s.get("upstream_sha", "") == skill.get("upstream_sha", "")
                and s.get("patch", "") == skill.get("patch", "")
                and s.get("package_sha256", "") == skill.get("package_sha256", "")
                for s in item["skills"]
            )]
            record["human_score"] = round(sum(item["overall"] for item in matching) / len(matching), 3)
            ratios = [item["edit_ratio"] for item in matching if item["edit_ratio"] is not None]
            record["teacher_edit_ratio"] = round(sum(ratios) / len(ratios), 4) if ratios else None
            record["human_evaluations"] = len(matching)
            data["skills"][name] = record
        save_performance(data)


def _empty_record(skill: str, version: str) -> dict[str, Any]:
    return {
        "skill": skill,
        "version": version,
        "provider_sha": "",
        "package_sha256": "",
        "patch": "",
        "domain": "",
        "status": "EXPERIMENTAL",
        "runs": 0,
        "success_rate": 0.0,
        "schema_failure_rate": 0.0,
        "schema_repair_rate": 0.0,
        "human_score": None,
        "teacher_edit_ratio": None,
        "average_model_calls": 0.0,
        "average_latency": 0.0,
        "known_failure_modes": [],
        "last_verified": "",
    }


def record_run(
    *,
    skill: str,
    version: str = "",
    provider_sha: str = "",
    package_sha256: str = "",
    patch: str = "",
    domain: str = "",
    success: bool,
    schema_failure: bool = False,
    schema_repair: bool = False,
    model_calls: int = 0,
    latency: float = 0.0,
    failure_mode: str = "",
    human_score: float | None = None,
    edit_ratio: float | None = None,
) -> dict[str, Any]:
    data = load_performance()
    record = data["skills"].get(skill) or _empty_record(skill, version)
    if version:
        record["version"] = version
    if provider_sha:
        record["provider_sha"] = provider_sha
    if package_sha256:
        record["package_sha256"] = package_sha256
    if patch:
        record["patch"] = patch
    if domain:
        record["domain"] = domain
    runs = int(record.get("runs", 0)) + 1
    successes = round(float(record.get("success_rate", 0.0)) * (runs - 1)) + (1 if success else 0)
    schema_failures = round(float(record.get("schema_failure_rate", 0.0)) * (runs - 1)) + (1 if schema_failure else 0)
    schema_repairs = round(float(record.get("schema_repair_rate", 0.0)) * (runs - 1)) + (1 if schema_repair else 0)
    model_total = float(record.get("average_model_calls", 0.0)) * (runs - 1) + max(int(model_calls), 0)
    latency_total = float(record.get("average_latency", 0.0)) * (runs - 1) + max(float(latency), 0.0)
    record.update(
        {
            "runs": runs,
            "success_rate": round(successes / runs, 4),
            "schema_failure_rate": round(schema_failures / runs, 4),
            "schema_repair_rate": round(schema_repairs / runs, 4),
            "average_model_calls": round(model_total / runs, 2),
            "average_latency": round(latency_total / runs, 2),
            "last_verified": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        }
    )
    if human_score is not None:
        previous = record.get("human_score")
        record["human_score"] = round(
            human_score if previous is None else (float(previous) + human_score) / 2, 3
        )
    if edit_ratio is not None:
        previous = record.get("teacher_edit_ratio")
        record["teacher_edit_ratio"] = round(
            edit_ratio if previous is None else (float(previous) + edit_ratio) / 2, 4
        )
    modes = list(dict.fromkeys(list(record.get("known_failure_modes", [])) + ([failure_mode] if failure_mode else [])))
    record["known_failure_modes"] = modes[-10:]
    data["skills"][skill] = record
    save_performance(data)
    return record


def record_trace(
    trace: dict[str, Any],
    *,
    human_score: float | None = None,
    edit_ratio: float | None = None,
    latency_by_skill: dict[str, float] | None = None,
    model_calls_by_skill: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """§19/§39/§40：把一次 Build 的 Skill Trace 写入 performance registry。

    记录必须绑定 skill version / provider SHA / package hash / patch；
    只做 observe/record（§47：M6 不允许历史表现影响路由）。
    """
    latency_by_skill = latency_by_skill or {}
    model_calls_by_skill = model_calls_by_skill or {}
    recorded: list[dict[str, Any]] = []
    for skill in trace.get("skills", []):
        name = str(skill.get("skill") or "")
        if not name:
            continue
        status = str(skill.get("status") or "")
        error = str(skill.get("error") or "")
        recorded.append(
            record_run(
                skill=name,
                version=str(skill.get("version") or ""),
                provider_sha=str(skill.get("upstream_sha") or ""),
                package_sha256=str(skill.get("package_sha256") or ""),
                patch=str(skill.get("patch") or ""),
                domain=str(skill.get("domain") or ""),
                success=status == "SUCCEEDED",
                schema_failure=bool(status == "FAILED" and "Schema" in error),
                schema_repair=int(skill.get("schema_repairs") or 0) > 0,
                model_calls=int(model_calls_by_skill.get(name, 0) or 0),
                latency=float(latency_by_skill.get(name, 0.0) or 0.0),
                failure_mode=(error[:120] if status in ("FAILED", "BLOCKED") else ""),
                human_score=human_score,
                edit_ratio=edit_ratio,
            )
        )
    return recorded


def review_demotions(*, max_schema_failure_rate: float = 0.3) -> list[dict[str, Any]]:
    """§69：用已记录数据找出该降级的 Skill（只报告，不改注册表，§47）。

    M6 阶段的可判定信号目前只有 schema 不稳定（`schema_failure_rate`）；
    evidence error / safety regression 需要人工或案件数据，由调用方通过
    `demotion_decision(evidence_error=..., safety_regression=...)` 显式传入。
    """
    data = load_performance()
    candidates: list[dict[str, Any]] = []
    for name, record in sorted(data.get("skills", {}).items()):
        rate = float(record.get("schema_failure_rate", 0.0) or 0.0)
        if int(record.get("runs", 0)) < 3:
            continue
        decision = demotion_decision(schema_instability=rate > max_schema_failure_rate)
        if not decision["demote"]:
            continue
        candidates.append(
            {
                "skill": name,
                "version": record.get("version"),
                "runs": record.get("runs"),
                "schema_failure_rate": rate,
                "triggers": decision["triggers"],
                "action": decision["action"],
                "note": "§69：观察结论；实际禁用/回退需人工执行注册表变更",
            }
        )
    return candidates


def review_promotions(*, unresolved_safety: dict[str, bool] | None = None) -> dict[str, Any]:
    """§68/§69：只做观察与判定，不改变路由（§47：M6 不允许历史表现影响 Resolver）。"""
    unresolved_safety = unresolved_safety or {}
    data = load_performance()
    promote: list[dict[str, Any]] = []
    stay: list[dict[str, Any]] = []
    demote: list[dict[str, Any]] = []
    for name, record in sorted(data.get("skills", {}).items()):
        decision = promotion_decision(record, unresolved_safety=bool(unresolved_safety.get(name)))
        row = {
            "skill": name,
            "version": record.get("version"),
            "runs": record.get("runs", 0),
            "success_rate": record.get("success_rate"),
            "schema_failure_rate": record.get("schema_failure_rate"),
            "human_score": record.get("human_score"),
            "teacher_edit_ratio": record.get("teacher_edit_ratio"),
            "current_status": record.get("status", "EXPERIMENTAL"),
            "target_status": decision["target"],
            "blocking": decision["reasons"],
        }
        (promote if decision["eligible"] else stay).append(row)
        if record.get("status") == "DISABLED":
            demote.append({**row, "reason": "已禁用（历史降级）"})
    return {
        "promote_candidates": promote,
        "experimental": stay,
        "disabled": demote,
        "demotion_candidates": review_demotions(),
        "thresholds": PROMOTION_THRESHOLD,
        "note": "§47：M6 仅记录与判定；promotion 的实际生效由 M7 的 performance-aware routing 决定",
    }


def promotion_decision(record: dict[str, Any], *, unresolved_safety: bool = False) -> dict[str, Any]:
    """§68：EXPERIMENTAL → STABLE 的门槛；数据不足时不让外部 Skill 默认优先。"""
    reasons: list[str] = []
    if int(record.get("runs", 0)) < PROMOTION_THRESHOLD["min_runs"]:
        reasons.append(f"runs<{PROMOTION_THRESHOLD['min_runs']}")
    if float(record.get("schema_failure_rate", 0.0)) > PROMOTION_THRESHOLD["max_schema_failure_rate"]:
        reasons.append("schema_failure_rate too high")
    score = record.get("human_score")
    if score is None or float(score) < PROMOTION_THRESHOLD["min_human_score"]:
        reasons.append("human_score below threshold")
    if unresolved_safety:
        reasons.append("unresolved safety failure")
    return {"eligible": not reasons, "reasons": reasons, "target": "STABLE" if not reasons else "EXPERIMENTAL"}


def demotion_decision(*, evidence_error: bool = False, safety_regression: bool = False, schema_instability: bool = False) -> dict[str, Any]:
    """§69：出现证据/安全/schema 退化时自动降级。"""
    triggers = [
        name
        for name, flag in (
            ("evidence_error", evidence_error),
            ("safety_regression", safety_regression),
            ("schema_instability", schema_instability),
        )
        if flag
    ]
    return {"demote": bool(triggers), "triggers": triggers, "action": "DISABLED" if triggers else "KEEP"}

```

## pebs/benchmark/report.py
```python
"""Benchmark Report（M6 §42）：Direct Codex / Builtin / Dynamic 对比表。"""

from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path
from typing import Any

from . import cases

COLUMNS = ("direct_codex", "builtin", "dynamic", "mixed")

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


def quality_score(record: dict[str, Any]) -> float | None:
    """Comparable 14-dimension score; optional script quality stays separate."""
    from . import evaluation

    if record.get("evaluation_kind") != "human" or record.get("role") != "teacher":
        return None
    if evaluation.validate_eval(record):
        return None
    return evaluation.overall_score(record)


def _run_order_key(path: Path) -> tuple[str, float]:
    """§41：run 的先后顺序取自 run 目录名里的时间戳，而不是文件 mtime。

    复评工具（tools/reevaluate_checks.py）会重写 run.json，mtime 一变，
    "最新一次成功 run"就会漂移，报告与教师工作表会指向另一个产物。"""
    stamp = path.parent.name.split("-", 2)[:2]
    if len(stamp) == 2 and stamp[0].isdigit() and stamp[1].isdigit():
        return ("-".join(stamp), path.stat().st_mtime)
    return ("", path.stat().st_mtime)


def load_runs(runs_dir: Path | None = None) -> list[dict[str, Any]]:
    """每个 (case, mode, experiment) 取一个代表 run，并统计尝试次数与成功次数。

    真实运行的证据核验存在模型波动：同一 case 可能一次 succeeded、一次 blocked。
    只显示"最新一次"会误导；因此代表 run 优先取最近的成功记录（没有成功记录才取最新），
    并附 attempts/succeeded 计数。"""
    directory = runs_dir or cases.runs_dir()
    if not directory.exists():
        return []
    grouped: dict[tuple[str, str, str], list[tuple[tuple[str, float], dict[str, Any]]]] = {}
    for path in sorted(directory.glob("*/run.json")):
        try:
            # 用 utf-8-sig 读取：Windows 上写出的 run.json 可能带 BOM，
            # 带 BOM 时 json.loads 会抛 JSONDecodeError，这个 run 就会从报告里静默消失。
            record = json.loads(path.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            continue
        # §46：Builtin / External / Hybrid 是不同实验，必须分行对比而不是互相覆盖
        key = (
            str(record.get("case_id")),
            str(record.get("mode")),
            str(record.get("experiment") or ""),
        )
        grouped.setdefault(key, []).append((_run_order_key(path), record))
    representatives: list[dict[str, Any]] = []
    for (case_id, mode, experiment), items in sorted(grouped.items()):
        items.sort(key=lambda pair: pair[0])
        succeeded = [pair for pair in items if pair[1].get("run_status") == "succeeded"]
        chosen = succeeded[-1][1] if succeeded else items[-1][1]
        chosen["_attempts"] = len(items)
        chosen["_succeeded"] = len(succeeded)
        chosen["_variant"] = f"{mode} [+{experiment}]" if experiment else mode
        representatives.append(chosen)
    return representatives


def budget_mismatch_notes(summary: dict[str, Any]) -> list[str]:
    """§35/§41：同一 case 的变体若用了不同预算，横向对比不成立，必须显式提示。

    真实教训：case B 的"Builtin 被阻断 vs Dynamic 成功"曾经是预算差异造成的
    （250/120 对 70–80/20），而不是模式差异；报告若不提示，读者会得出错误结论。
    """
    notes: list[str] = []
    for case in summary.get("cases", []):
        seen: dict[str, list[str]] = {}
        for variant, entry in case.items():
            if variant == "case_id" or not isinstance(entry, dict):
                continue
            budgets = entry.get("budgets")
            if not budgets:
                continue
            label = f"model={budgets.get('model_calls')}/research={budgets.get('research_requests')}"
            seen.setdefault(label, []).append(str(variant))
        if len(seen) > 1:
            detail = "；".join(f"{label}（{'+'.join(variants)}）" for label, variants in sorted(seen.items()))
            notes.append(f"- case {case.get('case_id')}：变体使用不同预算，**不可直接比较** —— {detail}")
    if not notes:
        return []
    return ["", "> ⚠ 预算差异提示（§35/§41）：", *notes, ""]


def budgets_for_run(run: dict[str, Any]) -> dict[str, Any] | None:
    """§35/§41：取该 run 的生效预算。

    新 run 直接写在 run.json 里；历史 run 没有这个字段，就从项目 Store 的 runs 行读回来
    （只读，不改写已有记录）——否则"不同预算不可比较"这条提示对历史数据永远不生效。
    """
    if run.get("budgets"):
        return run["budgets"]
    project_id = str(run.get("project_id") or "")
    run_id = str(run.get("run_id") or "")
    if not project_id or not run_id:
        return None
    try:
        from .. import config
        from ..store import Store

        base = config.project_dir(project_id)
        if not (base / "state.db").exists():
            return None
        store = Store(project_id, base)
        try:
            row = store.get_run(run_id)
        finally:
            store.close()
    except Exception:  # noqa: BLE001 - 项目已清理时视为未知
        return None
    return {
        "model_calls": row.get("budget_model_calls"),
        "research_requests": row.get("budget_research"),
        "run_seconds": row.get("budget_seconds"),
    }


def _with_budgets(run: dict[str, Any]) -> dict[str, Any]:
    if run.get("budgets"):
        return run
    budgets = budgets_for_run(run)
    if budgets is None:
        return run
    return {**run, "budgets": budgets}


def _same_code_version(run: dict[str, Any]) -> bool | None:
    """run 的 PEBS commit 是否等于当前代码版本；未知（旧记录无 commit）返回 None。"""
    from . import trace as trace_mod

    recorded = str((run.get("reproducibility") or {}).get("pebs_commit") or "")
    if not recorded:
        return None
    current = trace_mod.pebs_commit()
    if not current:
        return None
    return recorded == current


def _row_for(run: dict[str, Any]) -> dict[str, Any]:
    metrics = run.get("metrics") or {}
    human = run.get("human_eval") or {}
    return {
        "run_id": run.get("run_id"),
        "case_id": run.get("case_id"),
        "mode": run.get("mode"),
        "variant": run.get("_variant") or run.get("mode"),
        "experiment": run.get("experiment") or "",
        "status": run.get("run_status"),
        "attempts": run.get("_attempts", 1),
        "succeeded": run.get("_succeeded", 1 if run.get("run_status") == "succeeded" else 0),
        "evidence_policy": run.get("evidence_policy"),
        "human_score": quality_score(human) if human else None,
        "edit_ratio": human.get("edit_ratio"),
        "major_edit_rate": human.get("major_edit_rate"),
        "evidence_errors": human.get("evidence_errors"),
        "routing_errors": human.get("routing_errors"),
        "plan_errors": human.get("plan_errors"),
        "reviewer": human.get("reviewer"),
        "human_eval_run_id": human.get("run_id"),
        "human_eval_stale": bool(run.get("human_eval_stale")),
        # §35 Cost：scenario 的成本 = 本轮 phase + 它必须先跑完的基线课程。
        # 只报 phase（5/9 次）会让 F/G 看起来比实际便宜约 10 倍。
        "model_calls": metrics.get("total_model_calls") or metrics.get("model_calls"),
        "research_calls": metrics.get("research_calls"),
        "runtime_seconds": metrics.get("wall_time_seconds") or run.get("wall_time_seconds"),
        "skill_failure_rate": metrics.get("skill_failure_rate"),
        "schema_repair_rate": metrics.get("schema_repair_rate"),
        "locality_preservation_rate": metrics.get("locality_preservation_rate"),
        "automatic_issues": len((run.get("automatic_issues") or {}).get("issues", [])),
        # §35/§71-8：门禁 FAIL 与"自动问题"是两层，报告必须能同时看到，
        # 否则会出现"Auto Issues = 0 但 G6 FAIL"这种互相矛盾的行。
        "gate_fail": len([g for g in (run.get("trace") or {}).get("gates", []) if g.get("status") == "FAIL"]),
        "budgets": run.get("budgets"),
        "gate_review": len(
            [g for g in (run.get("trace") or {}).get("gates", []) if g.get("status") == "NEEDS_REVIEW"]
        ),
        # §41：该 run 是否由当前代码版本产生。不同版本的检查器/门禁口径会有差异
        # （见 docs/production-lessons.md），报告必须能一眼区分，不能让读者跨版本比较。
        "code_version_current": _same_code_version(run),
    }


def human_eval_for_run(run: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """§30/§33/§42：把项目里已接受的教师评分绑回它的 run。

    评分以 Artifact 形式落在项目 Store（`human_eval`），而不是 run.json；
    报告必须主动读回来，否则 Human Score / Edit Ratio / Evidence Errors 列永远是空的。
    返回 `(bound, stale)`：评分记录的 run_id 为空或与该 run 一致时是 bound；
    指向另一版产物时是 stale（仍然显示，但标明"评分针对另一版产物"，不静默丢弃）。
    """
    project_id = str(run.get("project_id") or "")
    if not project_id:
        return None, None
    try:
        from .. import config
        from ..store import Store

        base = config.project_dir(project_id)
        if not (base / "state.db").exists():
            return None, None
        store = Store(project_id, base)
    except Exception:  # noqa: BLE001 - 项目已被清理/不可读时视为未评分
        return None, None
    try:
        from . import evaluation

        evaluated_run_id = str(run.get("run_id") or "")
        if run.get("mode") == "direct_codex":
            evaluated_run_id = evaluation.direct_evaluation_run(store, run)
        content = evaluation.for_run(store, evaluated_run_id)
    except Exception:  # noqa: BLE001
        content = None
    finally:
        try:
            store.close()
        except Exception:  # noqa: BLE001
            pass
    if not isinstance(content, dict):
        return None, None
    bound_run = str(content.get("run_id") or "")
    if content.get("stale") or not bound_run or bound_run != evaluated_run_id:
        return None, content
    return content, None


def _with_human_eval(run: dict[str, Any]) -> dict[str, Any]:
    # A run.json snapshot is not authority for human provenance or currentness.
    bound, stale = human_eval_for_run(run)
    enriched = dict(run)
    enriched.pop("human_eval", None)
    enriched.pop("human_eval_stale", None)
    if bound is not None:
        enriched["human_eval"] = bound
    if stale is not None:
        enriched["human_eval_stale"] = stale
    return enriched


def summarize(runs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    runs = runs if runs is not None else load_runs()
    runs = [_with_budgets(_with_human_eval(run)) for run in runs]
    rows = [_row_for(run) for run in runs]
    by_case: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_case.setdefault(str(row.get("case_id")), []).append(row)

    table: list[dict[str, Any]] = []
    for case_id in sorted(by_case):
        entry: dict[str, Any] = {"case_id": case_id}
        variants: dict[str, list[dict[str, Any]]] = {}
        for row in by_case[case_id]:
            variants.setdefault(str(row.get("variant") or row["mode"]), []).append(row)
        for variant, matching in sorted(variants.items()):
            entry[variant] = {
                "status": matching[-1].get("status"),
                "attempts": matching[-1].get("attempts"),
                "succeeded": matching[-1].get("succeeded"),
                "evidence_policy": matching[-1].get("evidence_policy"),
                "human_score": _mean(row["human_score"] for row in matching),
                "edit_ratio": _mean(row["edit_ratio"] for row in matching),
                "major_edit_rate": _mean(row["major_edit_rate"] for row in matching),
                "evidence_errors": _sum(row["evidence_errors"] for row in matching),
                "routing_errors": _sum(row["routing_errors"] for row in matching),
                "plan_errors": _sum(row["plan_errors"] for row in matching),
                "model_calls": _sum(row["model_calls"] for row in matching),
                "runtime_seconds": _sum(row["runtime_seconds"] for row in matching),
                "skill_failure_rate": _mean(row["skill_failure_rate"] for row in matching),
                "schema_repair_rate": _mean(row["schema_repair_rate"] for row in matching),
                "locality_preservation_rate": _mean(row["locality_preservation_rate"] for row in matching),
                "automatic_issues": _sum(row["automatic_issues"] for row in matching),
                "gate_fail": _sum(row["gate_fail"] for row in matching),
                "gate_review": _sum(row["gate_review"] for row in matching),
                "code_version_current": matching[-1].get("code_version_current"),
                "reviewers": sorted({str(row["reviewer"]) for row in matching if row.get("reviewer")}),
                "human_eval_stale": any(row.get("human_eval_stale") for row in matching),
                # §35/§41：同一 case 的各变体若预算不同，正文里的对比不成立
                "budgets": matching[-1].get("budgets"),
                "runs": len(matching),
            }
        table.append(entry)
    summary = {"generated_at": _now(), "cases": table, "runs": len(rows), "rows": rows}
    summary["mode_comparison"] = mode_comparison(summary)
    return summary


def _mean(values) -> float | None:
    numbers = [float(value) for value in values if value is not None]
    return round(sum(numbers) / len(numbers), 3) if numbers else None


def _sum(values) -> float | None:
    numbers = [float(value) for value in values if value is not None]
    return round(sum(numbers), 3) if numbers else None


def _now() -> str:
    import time

    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def failure_category_section(runs: list[dict[str, Any]] | None = None) -> list[str]:
    """§65：把自动失败按 taxonomy 类别分布写进报告。

    只统计"当前代表 run"的自动问题；类别为空的 case 不占行。
    若出现不在 `failure_taxonomy.yaml` 里的 kind，单独列出（不静默丢弃）。
    """
    runs = runs if runs is not None else load_runs()
    totals: dict[str, int] = {}
    unknown: dict[str, list[str]] = {}
    for run in runs:
        automatic = run.get("automatic_issues") or {}
        for kind, count in (automatic.get("counts") or {}).items():
            totals[str(kind)] = totals.get(str(kind), 0) + int(count)
        for kind in automatic.get("unknown_categories") or []:
            unknown.setdefault(str(kind), []).append(str(run.get("case_id")))
    if not totals and not unknown:
        return []
    lines = ["", "## 失败类别分布（§65 failure taxonomy；仅统计代表 run 的自动问题）", ""]
    if totals:
        lines.append("| 类别 | 次数 |")
        lines.append("| --- | ---: |")
        for kind in sorted(totals, key=lambda item: (-totals[item], item)):
            lines.append(f"| {kind} | {totals[kind]} |")
        lines.append("")
    if unknown:
        lines.append("> ⚠ 以下 kind 不在 failure_taxonomy.yaml 中（分类无效）：")
        for kind, case_ids in sorted(unknown.items()):
            lines.append(f"> - {kind}（{ '、'.join(sorted(set(case_ids))) }）")
        lines.append("")
    return lines


def _gate_audit_section() -> list[str]:
    """§35 Gate FP/FN：读已生成的 gate_audit.json（重放昂贵，不在生成报告时重跑）。"""
    from . import gates_audit

    try:
        return gates_audit.section()
    except Exception:  # noqa: BLE001 - 审计缺失不应让报告生成失败
        return []


def _base_mode(variant: str) -> str:
    """把 `dynamic [+external-media]` 这类实验变体归回它的基础模式（§28/§46）。"""
    return variant.split(" ", 1)[0].strip() or variant


def mode_comparison(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """§42：Metric × Direct Codex / Builtin / Dynamic 汇总（每个基础模式一行）。

    Human Score 按 case 取均值（避免调用量大的 case 压过其他 case），
    计数类指标求和。混合模式（mixed）单独一行。
    """
    buckets: dict[str, list[dict[str, Any]]] = {}
    for case in summary.get("cases", []):
        for variant, entry in case.items():
            if variant == "case_id" or not isinstance(entry, dict):
                continue
            buckets.setdefault(_base_mode(str(variant)), []).append(entry)

    def mean(key: str, entries: list[dict[str, Any]]) -> float | None:
        values = [float(entry[key]) for entry in entries if entry.get(key) is not None]
        return round(sum(values) / len(values), 3) if values else None

    def total(key: str, entries: list[dict[str, Any]]) -> float | None:
        values = [float(entry[key]) for entry in entries if entry.get(key) is not None]
        return round(sum(values), 3) if values else None

    order = [mode for mode in COLUMNS if mode in buckets]
    order += sorted(mode for mode in buckets if mode not in COLUMNS)
    return {
        mode: {
            "variants": len(buckets[mode]),
            "human_score": mean("human_score", buckets[mode]),
            "edit_ratio": mean("edit_ratio", buckets[mode]),
            "evidence_errors": total("evidence_errors", buckets[mode]),
            "routing_errors": total("routing_errors", buckets[mode]),
            "plan_errors": total("plan_errors", buckets[mode]),
            "schema_repair_rate": mean("schema_repair_rate", buckets[mode]),
            "skill_failure_rate": mean("skill_failure_rate", buckets[mode]),
            "model_calls": total("model_calls", buckets[mode]),
            "runtime_seconds": total("runtime_seconds", buckets[mode]),
            "succeeded": total("succeeded", buckets[mode]),
            "attempts": total("attempts", buckets[mode]),
        }
        for mode in order
    }


def render_mode_comparison(summary: dict[str, Any]) -> list[str]:
    comparison = mode_comparison(summary)
    if not comparison:
        return []
    lines = [
        "",
        "## 模式对比（§42：Metric × Direct Codex / Builtin / Dynamic）",
        "",
        "| Metric | " + " | ".join(comparison) + " |",
        "| --- | " + " | ".join("---:" for _ in comparison) + " |",
    ]
    metrics = (
        ("Human Score（1–5 均值）", "human_score"),
        ("Teacher Edit Ratio（均值）", "edit_ratio"),
        ("Evidence Errors（合计）", "evidence_errors"),
        ("Routing Errors（合计）", "routing_errors"),
        ("Plan Errors（合计）", "plan_errors"),
        ("Skill Failure Rate（均值）", "skill_failure_rate"),
        ("Schema Repair Rate（均值）", "schema_repair_rate"),
        ("Model Calls（合计）", "model_calls"),
        ("Runtime(s)（合计）", "runtime_seconds"),
        ("Succeeded / Attempts", None),
    )
    for label, key in metrics:
        cells = []
        for mode in comparison:
            entry = comparison[mode]
            if key is None:
                cells.append(f"{entry.get('succeeded') or 0} / {entry.get('attempts') or 0}")
            else:
                cells.append("—" if entry.get(key) is None else str(entry.get(key)))
        lines.append("| " + label + " | " + " | ".join(cells) + " |")
    lines.append("")
    return lines


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# M6 Benchmark Summary",
        "",
        f"生成时间：{summary.get('generated_at')}；run 数（每 case×mode 取最新）：{summary.get('runs', 0)}",
        "",
        "| Case | Variant | Status | Attempts | Human Score | Edit Ratio | Evidence Errors | Routing Errors | Plan Errors | Model Calls | Runtime(s) | Auto Issues | Gate FAIL/Review |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for case in summary.get("cases", []):
        for variant, entry in sorted(case.items()):
            if variant == "case_id" or not isinstance(entry, dict):
                continue
            note = ""
            if entry.get("human_eval_stale"):
                note = " ⚠评分针对另一版产物"
            reviewers = entry.get("reviewers") or []
            # §41：`*` = 已知由不同代码版本产生；`?` = 记录里没有 PEBS commit（早于 §41），
            # 两种情况的门禁/检查器口径都无法与当前代码对齐，不能跨行直接比较。
            version_state = entry.get("code_version_current")
            marker = " *" if version_state is False else (" ?" if version_state is None else "")
            lines.append(
                "| {case} | {mode}{marker} | {status} | {attempts} | {human} | {edit} | {evidence} | {routing} | {plan} | {calls} | {runtime} | {issues} | {gates} |".format(
                    case=case["case_id"],
                    mode=variant,
                    marker=marker,
                    status=entry.get("status"),
                    attempts=f"{entry.get('succeeded', 0)}/{entry.get('attempts', 1)}",
                    human=entry.get("human_score"),
                    edit=entry.get("edit_ratio"),
                    evidence=entry.get("evidence_errors"),
                    routing=entry.get("routing_errors"),
                    plan=entry.get("plan_errors"),
                    calls=entry.get("model_calls"),
                    runtime=entry.get("runtime_seconds"),
                    issues=entry.get("automatic_issues"),
                    gates=f"{entry.get('gate_fail') or 0}/{entry.get('gate_review') or 0}",
                )
            )
            if reviewers or note:
                lines.append(f"| | 教师：{('、'.join(reviewers)) or '—'}{note} | | | | | | | | | | | |")
    lines.extend(budget_mismatch_notes(summary))
    lines.extend(render_mode_comparison(summary))
    lines.extend(failure_category_section())
    lines.extend(_gate_audit_section())
    if any(
        case.get(variant, {}).get("code_version_current") is not True
        for case in summary.get("cases", [])
        for variant in case
        if isinstance(case.get(variant), dict)
    ):
        lines.extend(
            [
                "",
                "> `*` = 该 run 由**不同代码版本**产生；`?` = 记录中没有 PEBS commit（早于 §41 provenance）。",
                "> 检查器与门禁的实现会随版本变化（例如门禁契约修复），",
                "> 因此带标记的行不应与其它行直接比较；必要时用 `tools/reevaluate_gates.py`、",
                "> `tools/reevaluate_checks.py` 在当前代码上重放已存项目。",
            ]
        )
    lines.extend(quality_section())
    lines.extend(performance_section())
    lines.append("")
    return "\n".join(lines)


def _worksheet_is_filled(data: dict[str, Any]) -> bool:
    """教师是否已经在这份工作表里填过东西（§30–§32）。"""
    if str(data.get("reviewer") or "").strip():
        return True
    if str(data.get("comment") or "").strip():
        return True
    if any(value is not None for value in (data.get("scores") or {}).values()):
        return True
    edits = data.get("edits") or {}
    if str(edits.get("generated_text") or "").strip() or str(edits.get("edited_text") or "").strip():
        return True
    return any(item.get("category") or item.get("severity") for item in (edits.get("items") or []))


def is_evaluable(run: dict[str, Any]) -> bool:
    """§30/§32：只有真正产出了课程产物的 run 才值得教师评分。

    失败的基线（0 产物）也生成工作表，会诱导教师给一份不存在的课程打 14 个维度分；
    这类 run 应该在报告的 Status/Attempts 列里被看到，而不是变成一张评分表。
    direct_codex 的产物是 run 目录里的 direct_output.md，不是 store 产物。
    """
    if str(run.get("run_status") or "") != "succeeded":
        return False
    if run.get("artifact_hashes"):
        return True
    run_dir = str(run.get("run_dir") or "")
    return bool(run_dir) and (Path(run_dir) / "direct_output.md").exists()


def write_worksheets(
    runs: list[dict[str, Any]] | None = None,
    *,
    directory: Path | None = None,
    preserve_filled: bool = True,
) -> list[Path]:
    """§30–§32：为每次 run 生成教师评分工作表（人工填写后可用 CLI 回收）。

    教师填写的评分是不可再生的外部输入：重新生成报告时绝不能覆盖已填写的工作表，
    否则一位老师刚写好的 14 个维度评分会被 `--report` 静默清空。
    `preserve_filled=True`（默认）下只刷新空白工作表里的 run 绑定信息。"""
    import yaml

    runs = runs if runs is not None else load_runs()
    target_dir = directory or (cases.reports_dir() / "worksheets")
    target_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for run in runs:
        if not is_evaluable(run):
            # 失败/无产物的 run 不生成评分表：教师无法给一份不存在的课程打 14 个维度分，
            # 它的信息已经在报告的 Status / Attempts / Auto Issues 列里
            continue
        case_id = str(run.get("case_id") or "?")
        mode = str(run.get("mode") or "?")
        # §46：实验变体（external-assessment 等）是不同产物，工作表必须分开命名，
        # 否则「只生成 PPT」这类变体会覆盖该 case 的主工作表。
        experiment = str(run.get("experiment") or "")
        stem = f"{case_id}-{mode}-{experiment}" if experiment else f"{case_id}-{mode}"
        stem = re.sub(r"[^a-zA-Z0-9_.-]", "_", stem)[:120]
        path = target_dir / f"{stem}-human_eval.yaml"
        if preserve_filled and path.exists():
            try:
                existing = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                existing = {}
            if _worksheet_is_filled(existing):
                continue
        template = {
            "target": run.get("evaluation_target"),
            "evaluation_kind": "human",
            "run": {
                "case_id": case_id,
                "mode": mode,
                "run_id": run.get("run_id"),
                "run_status": run.get("run_status"),
                "run_dir": run.get("run_dir"),
                "artifact_count": len(run.get("artifact_hashes") or {}),
                "evidence_policy": run.get("evidence_policy"),
            },
            "reviewer": "",
            "role": "teacher",
            "scores": {
                "subject_accuracy": None,
                "teaching_logic": None,
                "goal_clarity": None,
                "content_alignment": None,
                "concept_clarity": None,
                "case_quality": None,
                "executability": None,
                "student_engagement": None,
                "cognitive_challenge": None,
                "assessment_design": None,
                "language_naturalness": None,
                "visual_necessity": None,
                "coherence": None,
                "teacher_usability": None,
                "spoken_naturalness": None,
            },
            "comment": "",
            "must_fix": [],
            "nice_to_have": [],
            "evidence_errors": 0,
            "routing_errors": 0,
            "plan_errors": 0,
            "edits": {
                "generated_text": "",
                "edited_text": "",
                "items": [{"category": "", "severity": ""}],
            },
            "notes": [
                "填写说明见 benchmarks/reports/worksheets/README.md",
                "scores 使用 1–5；spoken_naturalness 仅脚本类任务必填",
                "edits.items 的 category 取值：fact correction / teaching restructure / tone edit / case replacement / media correction / assessment correction / template correction",
                "edits.items 的 severity 取值：S0 cosmetic / S1 wording / S2 local teaching improvement / S3 conceptual correction / S4 factual-evidence correction / S5 major redesign",
            ],
        }
        path.write_text(yaml.safe_dump(template, allow_unicode=True, sort_keys=False), encoding="utf-8")
        written.append(path)
    readme = target_dir / "README.md"
    if not readme.exists():
        readme.write_text(
            "# 教师评分工作表（M6 §30–§32）\n\n"
            "1. 打开对应的 `<case>-<mode>-human_eval.yaml`，在 `scores` 中给 1–5 分（14 个维度；脚本类任务另填 `spoken_naturalness`）。\n"
            "2. `comment` 必填（文字备注），`must_fix` / `nice_to_have` 选填。\n"
            "3. 若做过人工修改，把修改前后的文本填入 `edits.generated_text` / `edits.edited_text`，并按类别与严重度登记 `edits.items`。\n"
            "4. 提交：`python -m pebs.cli benchmark --submit-eval <worksheet.yaml> --project <project_id>`\n"
            "   （等价于 POST /api/projects/<project_id>/evaluation；评分以 Artifact 形式落库并绑定 Skill 版本）\n",
            encoding="utf-8",
        )
    return written


def load_worksheet(path: Path) -> dict[str, Any]:
    """把教师填写的工作表转换成 /evaluation 的 payload。"""
    import yaml

    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    manifest_path = Path(path).parent / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("target") != data.get("target") or (data.get("run") or {}).get("run_id") != (data.get("target") or {}).get("run_id"):
            raise ValueError("评分表与冻结材料版本不一致")
        for name in ("course.md", "run.json"):
            digest = hashlib.sha256((manifest_path.parent / name).read_bytes()).hexdigest()
            if digest != manifest.get("files", {}).get(name):
                raise ValueError(f"冻结材料已被修改：{name}")
    scores = {key: value for key, value in (data.get("scores") or {}).items() if value is not None}
    edits = data.get("edits") or {}
    edits["items"] = [item for item in (edits.get("items") or []) if item.get("category") or item.get("severity")]
    run = data.get("run") or {}
    return {
        "reviewer": str(data.get("reviewer") or ""),
        "evaluation_kind": str(data.get("evaluation_kind") or "human"),
        "target": data.get("target"),
        "role": str(data.get("role") or "teacher"),
        "run_id": str(run.get("run_id") or ""),
        "mode": str(run.get("mode") or ""),
        "scores": scores,
        "comment": str(data.get("comment") or ""),
        "must_fix": list(data.get("must_fix") or []),
        "nice_to_have": list(data.get("nice_to_have") or []),
        "evidence_errors": int(data.get("evidence_errors") or 0),
        "routing_errors": int(data.get("routing_errors") or 0),
        "plan_errors": int(data.get("plan_errors") or 0),
        "edits": edits,
    }


def performance_section(*, provider_skills: set[str] | None = None) -> list[str]:
    """§19/§68：把 Skill Performance Registry 摘要写进报告（只观察，不改路由）。"""
    from . import performance as performance_mod

    data = performance_mod.load_performance().get("skills", {})
    if not data:
        return []
    rows = []
    for name, record in sorted(data.items()):
        if provider_skills is not None and name not in provider_skills:
            continue
        rows.append(
            "| {name} | {version} | {runs} | {success} | {schema} | {human} | {edit} | {status} |".format(
                name=name,
                version=str(record.get("version") or "")[:12],
                runs=record.get("runs", 0),
                success=record.get("success_rate"),
                schema=record.get("schema_failure_rate"),
                human=record.get("human_score"),
                edit=record.get("teacher_edit_ratio"),
                status=record.get("status", "EXPERIMENTAL"),
            )
        )
    if not rows:
        return []
    return [
        "",
        "## Skill Performance Registry（§19/§40；内部 skills 全部记录）",
        "",
        "| Skill | Version | Runs | Success | Schema Fail | Human | Edit Ratio | Status |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        *rows,
        "",
    ]


def render_selection_report(records: list[dict[str, Any]]) -> str:
    """§46 Skill Selection Experiment（零模型调用）：Builtin vs 显式外部 Skill 的 DAG 差异。"""
    lines = [
        "# M6 Skill Selection Experiment（plan-only）",
        "",
        "同一任务在不同 Skill 组合下的 DAG 与选择理由；不调用任何模型，可离线复现（§46/§47）。",
        "",
        "| Case | Variant | Nodes | Terminal outputs | Explicit-skill note |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for record in records:
        lines.append(
            "| {case} | {variant} | {nodes} | {terminals} | {note} |".format(
                case=record.get("case_id"),
                variant=record.get("variant"),
                nodes=len(record.get("plan_nodes") or []),
                terminals="、".join(record.get("terminal_outputs") or []),
                note="；".join(record.get("explicit_skills_note") or []) or "—",
            )
        )
    lines.append("")
    for record in records:
        trace = record.get("selection_trace") or []
        if not trace:
            continue
        lines.append(f"## {record.get('case_id')} / {record.get('variant')}")
        lines.append("")
        lines.append("| 产物 | 选中 Skill | 分数 | 被拒候选（分数） | 理由 |")
        lines.append("| --- | --- | ---: | --- | --- |")
        for entry in trace:
            rejected_items = entry.get("rejected_candidates", [])
            rejected = "；".join(
                f"{item['candidate']}({item['score']})"
                + (f" — {item['rejected_because']}" if item.get("rejected_because") else "")
                for item in rejected_items[:3]
            )
            if len(rejected_items) > 3:
                rejected += f"；等 {len(rejected_items)} 个候选"
            lines.append(
                f"| {entry.get('artifact')} | {entry.get('selected')} | {entry.get('selected_score')} | {rejected or '—'} | {entry.get('reason')} |"
            )
        lines.append("")
    return "\n".join(lines)


def find_run_for_project(project_id: str) -> dict[str, Any] | None:
    """§62：Evaluation Tab 需要把项目映射回它的 benchmark run（含自动问题清单）。"""
    if not project_id:
        return None
    for run in load_runs():
        if str(run.get("project_id") or "") == project_id:
            return run
    return None


def quality_section(runs: list[dict[str, Any]] | None = None) -> list[str]:
    """§53/§54/§58：把语言、口语、PPT 的频度/分布写进报告（供人工评分参考，不做硬门）。"""
    runs = runs if runs is not None else load_runs()
    rows: list[str] = []
    for run in runs:
        quality = run.get("quality_metrics") or {}
        language = quality.get("language") or {}
        oral = quality.get("oral") or {}
        ppt = quality.get("ppt") or {}
        if not (language or oral or ppt):
            continue
        rows.append(
            "| {case} | {variant} | {per1000} | {long} | {spoken} | {dense} | {notes} |".format(
                case=run.get("case_id"),
                variant=run.get("_variant") or run.get("mode"),
                per1000=language.get("per_1000_chars", "—"),
                long=oral.get("long_sentence_ratio", "—"),
                spoken=oral.get("spoken_marker_ratio", "—"),
                dense=ppt.get("dense_ratio", "—"),
                notes=len(ppt.get("missing_notes") or []) if ppt else "—",
            )
        )
    if not rows:
        return []
    return [
        "",
        "## 质量指标（§53/§54/§58；频度与分布，人工评分参考，不设自动阈值）",
        "",
        "| Case | Variant | 机械连接词/千字 | 长句比例 | 口语标记比例 | 密集页比例 | 缺 Teacher Notes |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        *rows,
        "",
    ]


def write_selection_report(records: list[dict[str, Any]], *, path: Path | None = None) -> Path:
    target = path or (cases.reports_dir() / "skill_selection.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_selection_report(records), encoding="utf-8")
    (target.parent / "skill_selection.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return target


def write_report(summary: dict[str, Any] | None = None, *, path: Path | None = None) -> Path:
    summary = summary or summarize()
    target = path or (cases.reports_dir() / "benchmark_summary.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_markdown(summary), encoding="utf-8")
    (target.parent / "benchmark_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return target

```

## pebs/benchmark/trace.py
```python
"""Skill Trace（M6 §39–§41）：把一次 Build 的 Skill/版本/门禁/人工复核记录成可复现的 trace。"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from importlib import metadata
from pathlib import Path
from typing import Any

from .. import config, registry


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def registry_hash() -> str:
    path = Path(config.REGISTRY_DIR) / "skills.json"
    if not path.exists():
        return ""
    return _sha256_text(path.read_text(encoding="utf-8"))[:16]


def pebs_version() -> str:
    try:
        return metadata.version("pebs")
    except metadata.PackageNotFoundError:
        return "0.6.0-dev"


def pebs_commit() -> str:
    """§41：run 记录必须能回答"哪个 commit 跑出来的"（版本号不足以复现）。"""
    env = os.environ.get("PEBS_COMMIT")
    if env and env.strip():
        return env.strip()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(Path(__file__).resolve().parents[2]),
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def reproducibility(
    *, fixture_hashes: dict[str, str] | None = None, skills: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """§41：每次 benchmark run 必须能回答"用什么跑出来的"。

    `skills` 来自 Skill Trace：补上 provider SHA 与 patch —— 只记 "dual-coding
    performed well" 在升级后没有意义（§40）。
    """
    provider_shas = sorted({str(item.get("upstream_sha") or "") for item in (skills or []) if item.get("upstream_sha")})
    patches = sorted(
        {f"{item.get('skill')}@{item.get('patch')}" for item in (skills or []) if item.get("patch")}
    )
    package_hashes = sorted(
        {str(item.get("package_sha256") or "") for item in (skills or []) if item.get("package_sha256")}
    )
    return {
        "pebs_commit": pebs_commit(),
        "pebs_version": pebs_version(),
        "registry_hash": registry_hash(),
        "rules_version": config.RULES_VERSION,
        "model": str((config.PROVIDERS.get("llm") or {}).get("model") or ""),
        "provider_kind": str((config.PROVIDERS.get("llm") or {}).get("kind") or ""),
        "reasoning_effort": str((config.PROVIDERS.get("llm") or {}).get("reasoning_effort") or ""),
        "skill_provider_shas": provider_shas,
        "skill_patches": patches,
        "skill_package_sha256": package_hashes,
        "fixture_hashes": fixture_hashes or {},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
    }


def _skill_identity(name: str, record: dict[str, Any] | None = None) -> dict[str, Any]:
    record = record if record is not None else (registry.get(name) or {})
    pinned = record.get("pinned_version")
    versions = [item for item in (record.get("versions") or []) if isinstance(item, dict)]
    active = next((item for item in versions if item.get("version") == pinned), versions[-1] if versions else {})
    patches = [item for item in (record.get("patches") or []) if isinstance(item, dict)]
    active_patch = next(
        (item for item in reversed(patches) if item.get("upstream_version") == active.get("version")),
        patches[-1] if patches else {},
    )
    return {
        "skill": name,
        "version": str(pinned or active.get("version") or record.get("version") or ""),
        "provider": str(record.get("provider") or ("builtin" if record.get("runtime") == "builtin" else "")),
        "runtime": str(record.get("runtime") or ""),
        "agent": str(record.get("agent") or ""),
        "upstream_sha": str(active.get("upstream_sha") or ""),
        "package_sha256": str(active.get("package_sha256") or ""),
        "patch": str(active_patch.get("patch_version") or ""),
        "pinned": bool(pinned),
    }


def skill_snapshot() -> dict[str, Any]:
    """Only non-secret execution identities, captured before a run starts."""
    records = registry.load_skills()
    return {
        "identities": {name: _skill_identity(name, record) for name, record in records.items()},
        "step_skills": {step: name for name, record in records.items()
                        for step in (record.get("handler") or {}).get("steps", [])},
    }


def _parse_rev_list(raw: Any) -> list[str]:
    """steps.input_revs / output_revs 存的是 JSON 数组字符串。"""
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if not raw:
        return []
    try:
        value = json.loads(str(raw))
    except json.JSONDecodeError:
        return []
    return [str(item) for item in value] if isinstance(value, list) else []


def _artifact_of(revision_id: str) -> str:
    """`script:sec1@r2` → `script:sec1`。"""
    return revision_id.split("@", 1)[0]


def _schema_repairs(note: str) -> int:
    """§35：从 step note 里读出 Schema 修复次数（外部 Skill 第二次生成）。"""
    import re

    match = re.search(r"Schema 修复 (\d+) 次", note or "")
    return int(match.group(1)) if match else 0


def _all_revisions(store: Any) -> list[dict[str, Any]]:
    revisions: list[dict[str, Any]] = []
    for artifact in store.list_artifacts():
        for revision_id in store.revisions_of(artifact["artifact_id"]):
            revisions.append(store.get_revision(revision_id))
    return revisions


def _run_inputs(run: dict[str, Any]) -> dict[str, Any]:
    raw = run.get("inputs") or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return {}
    return raw if isinstance(raw, dict) else {}


def _skill_for_step(step_id: str) -> str:
    """把 pipeline step id（静态模式的步骤名）解析回 Registry 中的 Skill 名。

    §40：perf 记录必须绑定 skill 版本；用步骤标题当 skill 名会让历史数据失效。
    """
    if registry.get(step_id):
        return step_id
    for name, record in registry.load_skills().items():
        if step_id in ((record.get("handler") or {}).get("steps") or []):
            return name
    return ""


def _step_duration(step: dict[str, Any]) -> float | None:
    """§39：Skill Trace 需要 per-skill duration；steps 表有 started_at/ended_at（秒精度）。"""
    started = str(step.get("started_at") or "")
    ended = str(step.get("ended_at") or "")
    if not started or not ended:
        return None
    try:
        start_ts = time.mktime(time.strptime(started, "%Y-%m-%dT%H:%M:%S"))
        end_ts = time.mktime(time.strptime(ended, "%Y-%m-%dT%H:%M:%S"))
    except ValueError:
        return None
    return max(round(end_ts - start_ts, 1), 0.0)


def build_trace(
    engine: Any,
    run_id: str,
    *,
    case_id: str = "",
    mode: str = "",
    reproduce: dict[str, Any] | None = None,
    fixture_hashes: dict[str, str] | None = None,
) -> dict[str, Any]:
    """从 Store 里重建一次运行的 Skill Trace（不依赖内存状态）。"""
    store = engine.store
    run = store.get_run(run_id)
    steps = store.get_steps(run_id)
    by_run = [rev for rev in _all_revisions(store) if rev.get("produced_by_run") == run_id]
    produced: dict[str, list[dict[str, Any]]] = {}
    for rev in by_run:
        produced.setdefault(str(rev.get("produced_by") or ""), []).append(
            {"artifact_id": rev["artifact_id"], "revision_id": rev["revision_id"], "content_hash": rev["content_hash"]}
        )

    route = store.accepted_content("router_result") or {}
    plan = store.accepted_content("build_plan_dynamic") or {}
    skills: list[dict[str, Any]] = []
    snapshot = _run_inputs(run).get("skill_snapshot")
    node_by_skill: dict[str, dict[str, Any]] = {}
    for node in plan.get("nodes", []):
        node_by_skill.setdefault(str(node.get("skill")), node)
    for step in steps:
        if snapshot is not None:
            skill_name = step["step_id"] if step["step_id"] in snapshot["identities"] else snapshot["step_skills"].get(step["step_id"], "")
        else:
            skill_name = _skill_for_step(step["step_id"])
        resolved = bool(skill_name)
        identity = _skill_identity(skill_name) if resolved else {
            "skill": f"step:{step['step_id']}",
            "version": "",
            "provider": "",
            "runtime": "",
            "agent": "",
            "upstream_sha": "",
            "package_sha256": "",
            "patch": "",
            "pinned": False,
        }
        if snapshot is not None and resolved:
            identity = snapshot["identities"][skill_name]
        # §39：优先用执行器记录的 input_revs/output_revs（精确到 revision，含失败节点）；
        # 旧数据没有这些列，回退到按 produced_by 反查（只到 artifact_id，且需去重）。
        node = node_by_skill.get(step["step_id"]) or {}
        stored_inputs = _parse_rev_list(step.get("input_revs"))
        stored_outputs = _parse_rev_list(step.get("output_revs"))
        if stored_inputs or stored_outputs:
            inputs = sorted({_artifact_of(rev) for rev in stored_inputs if _artifact_of(rev)})
            outputs = list(dict.fromkeys(_artifact_of(rev) for rev in stored_outputs if _artifact_of(rev)))
        else:
            inputs = []
            outputs = list(
                dict.fromkeys(rev["artifact_id"] for rev in produced.get(step["step_id"], []))
            )
        skills.append(
            {
                **identity,
                "identity_source": "run_snapshot" if snapshot is not None else "current_registry",
                "step_id": step["step_id"],
                "status": step["status"],
                "attempts": step.get("attempts", 0),
                "duration": _step_duration(step),
                "model_calls": int(step.get("model_calls") or 0),
                "schema_repairs": _schema_repairs(str(step.get("note") or "")),
                "started_at": step.get("started_at"),
                "ended_at": step.get("ended_at"),
                "note": step.get("note") or "",
                "error": step.get("error") or "",
                "input_artifacts": inputs,
                "output_artifacts": outputs,
                "output_revisions": stored_outputs,
                "parallel_group": node.get("parallel_group"),
                "reused": bool(node.get("reused")),
                "gates_before": node.get("gate_before", []),
                "gates_after": node.get("gate_after", []),
                "reason": node.get("reason", ""),
            }
        )

    gate_results = []
    for artifact in store.list_artifacts():
        if artifact["artifact_type"] != "gate_result" or not artifact.get("accepted_rev"):
            continue
        content = store.accepted_content(artifact["artifact_id"]) or {}
        gate_results.append(
            {
                "gate": content.get("gate_id"),
                "target": artifact["artifact_id"],
                "status": content.get("status"),
                "version": content.get("check_version"),
            }
        )

    human_review: list[dict[str, Any]] = []
    for artifact in store.list_artifacts():
        if artifact["artifact_type"] != "review_record" or not artifact.get("accepted_rev"):
            continue
        content = store.accepted_content(artifact["artifact_id"]) or {}
        human_review.append(
            {
                "changeset_id": content.get("changeset_id"),
                "reviewer": content.get("reviewer"),
                "basis": content.get("basis"),
                "created_at": content.get("created_at"),
            }
        )

    return {
        "run_id": run_id,
        "case_id": case_id,
        "mode": mode or str(_run_inputs(run).get("planner", "static")),
        "run_status": run["status"],
        "request": run.get("request", ""),
        "route": {
            "task_intent": route.get("task_intent"),
            "knowledge_types": route.get("knowledge_types"),
            "requested_outputs": route.get("requested_outputs"),
            "research_need": route.get("research_need"),
            "media_need": route.get("media_need"),
            "source": route.get("source"),
        },
        "plan": {
            "plan_id": plan.get("plan_id"),
            "node_count": len(plan.get("nodes", [])),
            "terminal_outputs": plan.get("terminal_outputs", []),
            "reused_artifacts": plan.get("reused_artifacts", []),
            "degraded": plan.get("degraded", False),
            # §63/§64：Trace 必须带上"为什么选它 / 为什么拒绝其他候选"，
            # 否则 Evaluation Tab 的高级模式永远没有可展示的解释。
            "selection_trace": plan.get("selection_trace", []),
        },
        "skills": skills,
        "gates": gate_results,
        "human_review": human_review,
        # §41：不传 reproduce 时也要带上 provider SHA / patch，否则历史数据升级后失效
        "reproducibility": reproduce or reproducibility(fixture_hashes=fixture_hashes, skills=skills),
    }

```

## pebs/server.py
```python
diff --git a/pebs/server.py b/pebs/server.py
index bc2d9e0..a03334c 100644
--- a/pebs/server.py
+++ b/pebs/server.py
@@ -121,9 +121,11 @@ class ConversationIn(BaseModel):
 class HumanEvalIn(BaseModel):
     reviewer: str
     role: str = "teacher"
+    evaluation_kind: str = "human"
+    target: dict[str, Any] = Field(default_factory=dict)
     run_id: str = ""
     mode: str = ""
-    scores: dict[str, float] = Field(default_factory=dict)
+    scores: dict[str, float | None] = Field(default_factory=dict)
     comment: str = ""
     must_fix: list[str] = Field(default_factory=list)
     nice_to_have: list[str] = Field(default_factory=list)
@@ -397,13 +399,18 @@ def get_trace(project_id: str, run_id: str | None = None) -> dict[str, Any]:
 
 
 @app.get("/api/projects/{project_id}/evaluation")
-def get_evaluation(project_id: str) -> dict[str, Any]:
+def get_evaluation(project_id: str, run_id: str = "") -> dict[str, Any]:
     """§62：Evaluation Tab 数据（Run/Skills/Human Scores/Edit Ratio/Issues/Comparison）。"""
     from .benchmark import evaluation as evaluation_mod
     from .benchmark import report as report_mod
 
     engine = get_engine(project_id)
-    run = engine.store.latest_run()
+    from .store import StoreError
+
+    try:
+        run = engine.store.get_run(run_id) if run_id else engine.store.latest_run()
+    except StoreError as exc:
+        raise HTTPException(status_code=404, detail="受评运行不存在") from exc
     trace = {}
     if run:
         from .benchmark import trace as trace_mod
@@ -423,7 +430,8 @@ def get_evaluation(project_id: str) -> dict[str, Any]:
     return {
         "run": {"run_id": run["run_id"], "status": run["status"]} if run else None,
         "trace": trace,
-        "human_eval": evaluation_mod.latest(engine),
+        "human_eval": evaluation_mod.for_run(engine.store, run["run_id"]) if run else None,
+        "evaluation_target": evaluation_mod.target_for_run(engine.store, run["run_id"]) if run else None,
         "performance": benchmark_performance(),
         "comparison": comparison,
         "benchmark_run": {
@@ -445,7 +453,9 @@ def record_evaluation(project_id: str, payload: HumanEvalIn) -> dict[str, Any]:
 
     engine = get_engine(project_id)
     try:
-        content = evaluation_mod.record(engine, payload.model_dump())
+        content = evaluation_mod.record(
+            engine, payload.model_dump(), run_id=payload.run_id, mode=payload.mode
+        )
     except ValueError as exc:
         return JSONResponse(status_code=409, content={"ok": False, "reason": str(exc)})
     return content
@@ -460,7 +470,10 @@ def benchmark_reports_dir() -> str:
 def benchmark_performance() -> dict[str, Any]:
     from .benchmark import performance as performance_mod
 
-    return performance_mod.load_performance().get("skills", {})
+    try:
+        return performance_mod.load_performance().get("skills", {})
+    except (OSError, ValueError):
+        return {}
 
 
 @app.get("/api/projects/{project_id}/artifacts")

```

## pebs/cli.py
```python
diff --git a/pebs/cli.py b/pebs/cli.py
index 05fe1f2..d682e3c 100644
--- a/pebs/cli.py
+++ b/pebs/cli.py
@@ -281,16 +281,19 @@ def cmd_benchmark(args: argparse.Namespace) -> int:
             print("error: --submit-eval 需要 --project", file=sys.stderr)
             return 1
         engine = Engine(args.project)
-        payload = report_mod.load_worksheet(Path(args.submit_eval))
         try:
+            payload = report_mod.load_worksheet(Path(args.submit_eval))
             content = evaluation_mod.record(engine, payload, run_id=payload.get("run_id", ""), mode=payload.get("mode", ""))
-        except ValueError as exc:
+        except (ValueError, OSError) as exc:
             print(f"error: {exc}", file=sys.stderr)
             return 1
         print(
             json.dumps(
                 {
                     "reviewer": content["reviewer"],
+                    "run_id": content["run_id"],
+                    "evaluation_id": content["evaluation_id"],
+                    "binding": content["binding"],
                     "overall": content["overall"],
                     "edit_ratio": content["edit_ratio"],
                     "evidence_errors": content["evidence_errors"],
@@ -300,7 +303,7 @@ def cmd_benchmark(args: argparse.Namespace) -> int:
                 indent=2,
             )
         )
-        return 0
+        return 0 if content["binding"]["status"] == "BOUND" else 1
     if args.plan_only:
         from .benchmark import report as report_mod
 

```

## pebs/store.py
```python
diff --git a/pebs/store.py b/pebs/store.py
index ed3892f..e4fdbac 100644
--- a/pebs/store.py
+++ b/pebs/store.py
@@ -556,6 +556,10 @@ class Store:
         inputs: dict[str, Any] | None = None,
     ) -> str:
         budgets = budgets or {}
+        from .benchmark.trace import skill_snapshot
+
+        # Whitelisted identities only; never copy provider credentials into runs.
+        inputs = {**(inputs or {}), "skill_snapshot": skill_snapshot()}
         run_id = "run_" + uuid.uuid4().hex[:12]
         rules = {**{"model_calls": 40, "research_requests": 20, "run_seconds": 1800}}
         self._exec(

```

## tests/test_evaluation_integrity.py
```python
"""Public evaluation boundaries: provenance, frozen kits and human-only metrics."""
from __future__ import annotations

import pytest

from conftest import FakeLLM, FakeResearch, REQUEST_1, run_dynamic_build
from test_benchmark_evaluation import _valid_payload, client  # noqa: F401

pytestmark = pytest.mark.benchmark_smoke


@pytest.fixture(autouse=True)
def isolated_performance_registry(registry_env):
    """Every submission, including failed repros, stays outside the real registry."""


def _prepared_project(client, name, *, artifact_type="lesson_plan"):
    """A completed local run, without network/model/renderer dependencies."""
    from pebs import server

    client.post("/api/projects", json={"project_id": name})
    engine = server.get_engine(name)
    run_id = engine.store.create_run(environment="test_fixture", inputs={"planner": "dynamic"})
    revision = engine.store.add_revision(
        artifact_id=f"{artifact_type}:sec1", artifact_type=artifact_type,
        content={"section_id": "sec1", "title": "Frozen lesson", "units": []},
        produced_by="lesson-designer", run_id=run_id, fixture=True,
    )
    engine.store.set_accepted(f"{artifact_type}:sec1", revision["revision_id"])
    engine.store.set_run_status(run_id, "succeeded")
    return engine, run_id


def test_api_preserves_the_evaluated_run_and_mode(client, registry_env):
    from pebs import server

    client.post("/api/projects", json={"project_id": "bound-evaluation"})
    engine = server.get_engine("bound-evaluation")
    engine.llm = FakeLLM()
    engine.research = FakeResearch()
    start, status = run_dynamic_build(engine, REQUEST_1)
    assert status["run"]["status"] == "succeeded"
    engine.accept(start["changeset_id"])
    payload = _valid_payload(run_id=start["run_id"], mode="dynamic",
        target=client.get("/api/projects/bound-evaluation/evaluation").json()["evaluation_target"])
    payload["scores"]["spoken_naturalness"] = 4
    response = client.post(
        "/api/projects/bound-evaluation/evaluation",
        json=payload,
    )
    assert response.status_code == 200, response.text
    assert response.json()["run_id"] == start["run_id"]
    assert response.json()["mode"] == "dynamic"
    saved = client.get("/api/projects/bound-evaluation/evaluation").json()["human_eval"]
    assert saved["run_id"] == start["run_id"]


@pytest.mark.parametrize("source", [{"role": "ai"}, {"evaluation_kind": "ai"}])
def test_ai_review_cannot_be_submitted_as_a_teacher_score(client, source):
    client.post("/api/projects", json={"project_id": "human-only"})
    response = client.post(
        "/api/projects/human-only/evaluation", json=_valid_payload(**source)
    )
    assert response.status_code == 409
    assert client.get("/api/projects/human-only/evaluation").json()["human_eval"] is None


def test_incomplete_scores_cannot_enter_the_human_report(client):
    client.post("/api/projects", json={"project_id": "complete-rubric"})
    response = client.post(
        "/api/projects/complete-rubric/evaluation",
        json=_valid_payload(scores={"goal_clarity": 5}),
    )
    assert response.status_code == 409
    assert "subject_accuracy" in response.json()["reason"]


def test_report_reloads_teacher_evidence_instead_of_trusting_embedded_scores(client):
    from pebs.benchmark import report

    _, run_id = _prepared_project(client, "report-source")
    run = {"project_id": "report-source", "run_id": run_id, "case_id": "A",
           "mode": "dynamic", "run_status": "succeeded",
           "human_eval": _valid_payload(role="ai", edit_ratio=0.0)}
    row = report.summarize([run])["rows"][0]
    assert row["human_score"] is None
    assert row["edit_ratio"] is None


def test_non_script_optional_score_is_nullable_and_does_not_change_core_average(client):
    _, run_id = _prepared_project(client, "optional-score")
    payload = _valid_payload(run_id=run_id, mode="dynamic",
        target=client.get("/api/projects/optional-score/evaluation").json()["evaluation_target"])
    payload["scores"]["spoken_naturalness"] = None
    response = client.post("/api/projects/optional-score/evaluation", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["overall"] == 3.857
    payload["scores"]["spoken_naturalness"] = 1
    response = client.post("/api/projects/optional-score/evaluation", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["overall"] == 3.857


@pytest.mark.parametrize("run_id", ["", "run_from_another_project"])
def test_api_rejects_scores_without_a_run_in_this_project(client, run_id):
    _prepared_project(client, "bound-only")
    response = client.post(
        "/api/projects/bound-only/evaluation", json=_valid_payload(run_id=run_id)
    )
    assert response.status_code == 409, response.text


def test_scores_become_stale_when_the_reviewed_content_changes(client, registry_env):
    from pebs.benchmark import report

    engine, run_id = _prepared_project(client, "revision-bound")
    target = client.get("/api/projects/revision-bound/evaluation").json()["evaluation_target"]
    assert target["artifacts"]["lesson_plan:sec1"]["revision_id"] == "lesson_plan:sec1@r1"
    payload = _valid_payload(run_id=run_id, mode="dynamic", target=target)
    response = client.post("/api/projects/revision-bound/evaluation", json=payload)
    assert response.status_code == 200, response.text
    changed = engine.store.add_revision(
        artifact_id="lesson_plan:sec1", artifact_type="lesson_plan",
        content={"title": "Changed after evaluation"}, produced_by="lesson-designer",
        run_id=run_id, fixture=True,
    )
    engine.store.set_accepted("lesson_plan:sec1", changed["revision_id"])
    saved = client.get("/api/projects/revision-bound/evaluation").json()["human_eval"]
    assert saved["stale"] is True
    summary = report.summarize([{
        "case_id": "A", "project_id": engine.project_id, "run_id": run_id,
        "mode": "dynamic", "run_status": "succeeded",
    }])
    assert summary["rows"][0]["human_score"] is None
    assert summary["rows"][0]["human_eval_stale"] is True
    assert client.post("/api/projects/revision-bound/evaluation", json=payload).status_code == 409


def test_kit_regeneration_preserves_the_entire_filled_run_package(client, tmp_path):
    import json
    from pathlib import Path
    import yaml
    from pebs.benchmark import evaluation

    engine, first_run = _prepared_project(client, "frozen-kit")
    def run(rid):
        return {"case_id": "A", "mode": "dynamic", "project_id": engine.project_id,
                "run_id": rid, "run_status": "succeeded", "artifact_hashes": {"lesson_plan:sec1":
                    engine.store.accepted_revision("lesson_plan:sec1")["content_hash"]}}
    first_record = run(first_run)
    first = evaluation.export_kit([first_record], directory=tmp_path / "kit")[0]
    worksheet = Path(first["worksheet"])
    contents = yaml.safe_load(worksheet.read_text(encoding="utf-8"))
    contents["reviewer"] = "Teacher already working"
    worksheet.write_text(yaml.safe_dump(contents), encoding="utf-8")
    original = {p.name: p.read_bytes() for p in Path(first["dir"]).iterdir() if p.is_file()}
    second_run = engine.store.create_run(environment="test_fixture", inputs={"planner": "dynamic"})
    changed = engine.store.add_revision(
        artifact_id="lesson_plan:sec1", artifact_type="lesson_plan", content={"title": "New lesson"},
        produced_by="lesson-designer", run_id=second_run, fixture=True,
    )
    engine.store.set_accepted("lesson_plan:sec1", changed["revision_id"])
    engine.store.set_run_status(second_run, "succeeded")
    second = evaluation.export_kit([run(second_run)], directory=tmp_path / "kit")[0]
    assert first["dir"] != second["dir"]
    assert json.loads((Path(second["dir"]) / "run.json").read_text(encoding="utf-8"))["run_id"] == second_run
    evaluation.export_kit([first_record], directory=tmp_path / "kit")
    assert {p.name: p.read_bytes() for p in Path(first["dir"]).iterdir() if p.is_file()} == original


def test_binding_failure_is_visible_and_resubmission_is_idempotent(client, registry_env):
    from pebs import config

    engine, run_id = _prepared_project(client, "binding-failure")
    # An invalid filesystem destination exercises the real persistence failure.
    path = config.REGISTRY_DIR / "performance.json"
    if path.exists():
        path.unlink()
    path.mkdir()
    payload = _valid_payload(run_id=run_id, mode="dynamic",
        target=client.get("/api/projects/binding-failure/evaluation").json()["evaluation_target"])
    response = client.post("/api/projects/binding-failure/evaluation", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["binding"]["status"] == "FAILED"
    assert client.get("/api/projects/binding-failure/evaluation").json()["human_eval"]["binding"]["status"] == "FAILED"
    path.rmdir()
    retried = client.post("/api/projects/binding-failure/evaluation", json=payload)
    assert retried.status_code == 200, retried.text
    assert retried.json()["binding"]["status"] == "BOUND"
    saved = path.read_bytes()
    again = client.post("/api/projects/binding-failure/evaluation", json=payload)
    assert again.json()["evaluation_id"] == retried.json()["evaluation_id"]
    assert path.read_bytes() == saved


def test_teacher_must_submit_the_snapshot_they_reviewed(client):
    _, run_id = _prepared_project(client, "explicit-snapshot")
    response = client.post("/api/projects/explicit-snapshot/evaluation",
                           json=_valid_payload(run_id=run_id, mode="dynamic"))
    assert response.status_code == 409
    assert "target" in response.json()["reason"]


def test_script_evaluation_requires_spoken_naturalness(client):
    _, run_id = _prepared_project(client, "script-rubric", artifact_type="script")
    target = client.get("/api/projects/script-rubric/evaluation").json()["evaluation_target"]
    payload = _valid_payload(run_id=run_id, mode="dynamic", target=target)
    payload["scores"].pop("spoken_naturalness")
    response = client.post("/api/projects/script-rubric/evaluation", json=payload)
    assert response.status_code == 409
    assert "spoken_naturalness" in response.json()["reason"]


def test_cli_submission_reports_binding_failure_and_can_retry(client, tmp_path, capsys):
    from pathlib import Path
    import json
    import yaml
    from pebs import cli, config
    from pebs.benchmark import evaluation

    engine, run_id = _prepared_project(client, "cli-evaluation")
    artifact = engine.store.accepted_revision("lesson_plan:sec1")
    run = {"project_id": engine.project_id, "run_id": run_id, "case_id": "A", "mode": "dynamic",
           "run_status": "succeeded", "artifact_hashes": {"lesson_plan:sec1": artifact["content_hash"]}}
    package = evaluation.export_kit([run], directory=tmp_path / "kit")[0]
    sheet = Path(package["worksheet"])
    data = yaml.safe_load(sheet.read_text(encoding="utf-8"))
    data.update(_valid_payload())
    sheet.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    path = config.REGISTRY_DIR / "performance.json"
    if path.exists():
        path.unlink()
    path.mkdir()
    args = ["benchmark", "--submit-eval", str(sheet), "--project", engine.project_id]
    assert cli.main(args) != 0
    assert json.loads(capsys.readouterr().out)["binding"]["status"] == "FAILED"
    path.rmdir()
    assert cli.main(args) == 0
    saved = json.loads(capsys.readouterr().out)
    assert saved["run_id"] == run_id
    assert saved["binding"]["status"] == "BOUND"


def test_direct_baseline_kit_has_complete_content_and_a_submittable_identity(client, tmp_path, capsys):
    from pathlib import Path
    import yaml
    from pebs import cli
    from pebs.benchmark import evaluation, report

    run_dir = tmp_path / "direct"
    run_dir.mkdir()
    original = "Direct baseline lesson\n" * 1200 + "END OF ORIGINAL"
    (run_dir / "direct_output.md").write_text(original, encoding="utf-8")
    run = {"project_id": "direct-evaluation", "run_id": "", "run_dir": str(run_dir),
           "case_id": "A", "mode": "direct_codex", "run_status": "succeeded", "artifact_hashes": {}}
    exported = evaluation.export_kit([run], directory=tmp_path / "kit")[0]
    assert original in (Path(exported["dir"]) / "course.md").read_text(encoding="utf-8")
    path = Path(exported["worksheet"])
    sheet = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert sheet["run"]["run_id"]
    sheet.update(_valid_payload())
    path.write_text(yaml.safe_dump(sheet, allow_unicode=True), encoding="utf-8")
    assert cli.main(["benchmark", "--submit-eval", str(path), "--project", run["project_id"]]) == 0
    row = report.summarize([run])["rows"][0]
    assert row["human_score"] == 3.857
    assert not row["human_eval_stale"]


def test_teacher_binding_keeps_build_time_skill_version_after_registry_upgrade(client):
    import json
    from pebs import config
    from pebs.benchmark import performance

    engine, run_id = _prepared_project(client, "skill-provenance")
    engine.store.add_step(run_id, "script-writer", "Script", status="SUCCEEDED")
    before = client.get("/api/projects/skill-provenance/evaluation").json()
    version = before["trace"]["skills"][0]["version"]
    path = config.REGISTRY_DIR / "skills.json"
    registry = json.loads(path.read_text(encoding="utf-8"))
    registry["script-writer"]["version"] = "999.0-upgraded"
    registry["script-writer"]["pinned_version"] = "999.0-upgraded"
    path.write_text(json.dumps(registry), encoding="utf-8")
    response = client.post("/api/projects/skill-provenance/evaluation", json=_valid_payload(
        target=before["evaluation_target"], run_id=run_id, mode="dynamic"))
    assert response.status_code == 200, response.text
    assert response.json()["binding"]["status"] == "BOUND"
    stored = performance.load_performance()["human_evaluations"][response.json()["evaluation_id"]]
    assert stored["skills"][0]["version"] == version


def test_evaluation_api_can_retrieve_an_older_run_without_using_the_latest_score(client):
    engine, first_run = _prepared_project(client, "history-evaluation")
    target = client.get("/api/projects/history-evaluation/evaluation").json()["evaluation_target"]
    response = client.post("/api/projects/history-evaluation/evaluation", json=_valid_payload(
        run_id=first_run, mode="dynamic", target=target))
    assert response.status_code == 200
    second_run = engine.store.create_run(inputs={"planner": "dynamic"})
    engine.store.set_run_status(second_run, "succeeded")
    assert client.get("/api/projects/history-evaluation/evaluation").json()["human_eval"] is None
    historical = client.get("/api/projects/history-evaluation/evaluation", params={"run_id": first_run})
    assert historical.status_code == 200
    assert historical.json()["run"]["run_id"] == first_run
    assert historical.json()["human_eval"]["run_id"] == first_run
    assert not historical.json()["human_eval"]["stale"]


def test_cli_rejects_a_material_package_changed_after_export(client, tmp_path, capsys):
    from pathlib import Path
    import yaml
    from pebs import cli
    from pebs.benchmark import evaluation

    engine, run_id = _prepared_project(client, "changed-package")
    artifact = engine.store.accepted_revision("lesson_plan:sec1")
    run = {"project_id": engine.project_id, "run_id": run_id, "case_id": "A", "mode": "dynamic",
           "run_status": "succeeded", "artifact_hashes": {"lesson_plan:sec1": artifact["content_hash"]}}
    package = evaluation.export_kit([run], directory=tmp_path / "kit")[0]
    sheet = Path(package["worksheet"])
    data = yaml.safe_load(sheet.read_text(encoding="utf-8"))
    data.update(_valid_payload())
    sheet.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    (Path(package["dir"]) / "course.md").write_text("Replaced after export", encoding="utf-8")
    assert cli.main(["benchmark", "--submit-eval", str(sheet), "--project", engine.project_id]) != 0
    assert client.get("/api/projects/changed-package/evaluation").json()["human_eval"] is None

```
