"""Skill Performance Registry（M6 §19, §40, §68, §69）。

记录必须绑定 Skill 版本（provider SHA / package hash / patch），否则升级后历史数据失效。
"""

from __future__ import annotations

import json
import os
import tempfile
import time
import sqlite3
from functools import wraps
from threading import RLock
from pathlib import Path
from typing import Any

from .. import config

MODES = ("direct_codex", "builtin", "dynamic", "mixed")
_EVALUATION_LOCK = RLock()


def _serialized_update(function):
    """Serialize JSON read/modify/replace across threads and CLI/server processes."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        with _EVALUATION_LOCK:
            directory = Path(config.REGISTRY_DIR)
            directory.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(directory / "performance.lock.sqlite3", timeout=30)
            try:
                connection.execute("BEGIN IMMEDIATE")
                return function(*args, **kwargs)
            finally:
                connection.rollback()
                connection.close()
    return wrapped

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


@_serialized_update
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


@_serialized_update
def record_run(
    *,
    skill: str,
    version: str = "",
    provider_sha: str | None = None,
    package_sha256: str | None = None,
    patch: str | None = None,
    domain: str = "",
    success: bool,
    schema_failure: bool = False,
    schema_repair: bool = False,
    model_calls: int = 0,
    latency: float = 0.0,
    failure_mode: str = "",
    human_score: float | None = None,
    edit_ratio: float | None = None,
    run_key: str = "",
) -> dict[str, Any]:
    data = load_performance()
    observation = {"success": bool(success), "schema_failure": bool(schema_failure),
                   "schema_repair": bool(schema_repair), "model_calls": max(int(model_calls), 0),
                   "latency": max(float(latency), 0.0), "failure_mode": failure_mode}
    previous_build = data.get("build_records", {}).get(run_key, {}) if run_key else {}
    previous_observation = previous_build.get("observation", {})
    if previous_observation == observation:
        return previous_build["result"]
    record = data["skills"].get(skill) or _empty_record(skill, version)
    identity = {"version": version or record.get("version", "")}
    for key, value in (("provider_sha", provider_sha), ("package_sha256", package_sha256), ("patch", patch)):
        identity[key] = (record.get(key, "") if identity["version"] == record.get("version") else "") if value is None else value
    history_index = None
    if version and any(record.get(key, "") != value for key, value in identity.items()):
        if previous_observation:
            history_index = next((i for i, item in reversed(list(enumerate(data.get("skill_history", []))))
                if item.get("skill") == skill and all(item.get(k, "") == v for k, v in identity.items())), None)
            record = dict(data["skill_history"][history_index]) if history_index is not None else dict(previous_build["result"])
            if history_index is None:
                history_index = len(data.setdefault("skill_history", []))
                data["skill_history"].append(record)
        else:
            data.setdefault("skill_history", []).append(dict(record))
            record = {**_empty_record(skill, version), **identity}
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
    previous_runs = int(record.get("runs", 0))
    runs = previous_runs + (0 if previous_observation else 1)
    successes = round(float(record.get("success_rate", 0.0)) * previous_runs) - int(previous_observation.get("success", 0)) + int(success)
    schema_failures = round(float(record.get("schema_failure_rate", 0.0)) * previous_runs) - int(previous_observation.get("schema_failure", 0)) + int(schema_failure)
    schema_repairs = round(float(record.get("schema_repair_rate", 0.0)) * previous_runs) - int(previous_observation.get("schema_repair", 0)) + int(schema_repair)
    model_total = float(record.get("average_model_calls", 0.0)) * previous_runs - previous_observation.get("model_calls", 0) + observation["model_calls"]
    latency_total = float(record.get("average_latency", 0.0)) * previous_runs - previous_observation.get("latency", 0.0) + observation["latency"]
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
    if history_index is None:
        data["skills"][skill] = record
    else:
        data["skill_history"][history_index] = record
    if run_key:
        data.setdefault("build_records", {})[run_key] = {"observation": observation, "result": dict(record)}
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
    grouped: dict[tuple[str, ...], dict[str, Any]] = {}
    for skill in trace.get("skills", []):
        identity = tuple(str(skill.get(key) or "") for key in ("skill", "version", "upstream_sha", "package_sha256", "patch"))
        if identity not in grouped:
            grouped[identity] = dict(skill)
        else:
            merged = grouped[identity]
            merged["schema_repairs"] = int(merged.get("schema_repairs") or 0) + int(skill.get("schema_repairs") or 0)
            if skill.get("status") != "SUCCEEDED":
                merged["status"] = skill.get("status")
                merged["error"] = skill.get("error")
    for identity, skill in grouped.items():
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
                run_key=json.dumps([trace["run_id"], *identity]) if trace.get("run_id") else "",
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
