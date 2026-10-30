from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from . import gates
from .gates import COLUMN_KIND_MAP
from .store import current_signoffs, file_hash, now_iso

LABEL_FORMAL = "正式"
LABEL_DRAFT = "草稿—未通过 QA"


def _set_cjk_font(document: Any) -> None:
    from docx.oxml.ns import qn

    style = document.styles["Normal"]
    style.font.name = "Microsoft YaHei"
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    rfonts.set(qn("w:eastAsia"), "Microsoft YaHei")


def _column_text(units: list[dict[str, Any]], column_name: str) -> str:
    for kind, words in COLUMN_KIND_MAP.items():
        if any(word in column_name for word in words):
            matched = [u for u in units if u.get("kind") == kind]
            if kind == "visual":
                return "\n".join(f"{u.get('text', '')}（{u.get('visual_function', '')}）" for u in matched)
            return "\n".join(u.get("text", "") for u in matched)
    return ""


def _units_markdown(script: dict[str, Any]) -> str:
    lines: list[str] = []
    for unit in script.get("units", []):
        kind = unit.get("kind")
        text = unit.get("text", "")
        if kind == "title":
            lines.append(f"### {text}")
        elif kind == "visual":
            lines.append(f"> [画面] {text}（{unit.get('visual_function', '')}）")
        elif kind == "note":
            lines.append(f"> {text}")
        elif kind == "case":
            lines.append(f"**案例**：{text}")
        elif kind == "interaction":
            lines.append(f"**互动**：{text}")
        else:
            lines.append(text)
        lines.append("")
    return "\n".join(lines)


def _section_markdown(course: str, script: dict[str, Any], label: str | None, blocking: list[str]) -> str:
    parts = [f"# {course} — {script.get('title', '')}"]
    if label:
        parts.append(f"> **{label}**")
    parts.append("")
    wc = script.get("word_count", {})
    if wc:
        parts.append(
            f"*正文字数：{wc.get('count', 0)}（要求 {wc.get('min', 0)}–{wc.get('max', 0)}；口径：{wc.get('scope_note', '')}）*"
        )
        parts.append("")
    parts.append(_units_markdown(script))
    if blocking:
        parts.append("## 未通过 QA 的问题（草稿）")
        for item in blocking:
            parts.append(f"- {item}")
    return "\n".join(parts)


def _write_docx(path: Path, course: str, script: dict[str, Any], columns: list[str], label: str | None, blocking: list[str]) -> None:
    import docx

    document = docx.Document()
    _set_cjk_font(document)
    if label:
        document.add_paragraph(label)
    document.add_heading(f"{course} — {script.get('title', '')}", level=1)
    wc = script.get("word_count", {})
    if wc:
        document.add_paragraph(
            f"正文字数：{wc.get('count', 0)}（要求 {wc.get('min', 0)}–{wc.get('max', 0)}）"
        )
    units = script.get("units", [])
    if columns:
        table = document.add_table(rows=1, cols=len(columns))
        table.style = "Table Grid"
        for idx, name in enumerate(columns):
            table.rows[0].cells[idx].text = name
        row = table.add_row()
        for idx, name in enumerate(columns):
            row.cells[idx].text = _column_text(units, name)
    else:
        for unit in units:
            kind = unit.get("kind")
            text = unit.get("text", "")
            if kind == "title":
                document.add_heading(text, level=2)
            elif kind == "visual":
                paragraph = document.add_paragraph()
                run = paragraph.add_run(f"【画面】{text}（{unit.get('visual_function', '')}）")
                run.italic = True
            elif kind == "case":
                document.add_paragraph(f"【案例】{text}")
            elif kind == "interaction":
                document.add_paragraph(f"【互动】{text}")
            elif kind == "note":
                document.add_paragraph(text)
            else:
                document.add_paragraph(text)
    if blocking:
        document.add_heading("未通过 QA 的问题（草稿）", level=2)
        for item in blocking:
            document.add_paragraph(item, style="List Bullet")
    document.save(str(path))


def _output_dir(ctx: Any, mode: str) -> Path:
    base = Path(ctx.store.base_dir) / "outputs"
    if mode == "formal":
        return base / "staging" / str(ctx.changeset_id)
    return base / "draft" / str(ctx.changeset_id)


def _lesson_markdown(course: str, lesson: dict[str, Any], label: str | None) -> str:
    lines = [f"# {course} — {lesson.get('title', '')}（教案）"]
    if label:
        lines.append(f"> **{label}**")
    lines.append("")
    lines.append("## 教学目标")
    for objective in lesson.get("objectives", []):
        lines.append(f"- （{objective.get('goal_ref', '')}）{objective.get('text', '')}")
    if lesson.get("key_points"):
        lines.append("")
        lines.append("## 教学重点")
        for item in lesson["key_points"]:
            lines.append(f"- {item}")
    if lesson.get("difficult_points"):
        lines.append("")
        lines.append("## 教学难点")
        for item in lesson["difficult_points"]:
            lines.append(f"- {item}")
    if lesson.get("preparation"):
        lines.append("")
        lines.append("## 教学准备")
        for item in lesson["preparation"]:
            lines.append(f"- {item}")
    lines.append("")
    lines.append("## 教学过程")
    lines.append("")
    lines.append("| 环节 | 时间 | 教师活动 | 学生活动 | 教学意图 |")
    lines.append("|---|---|---|---|---|")
    for stage in lesson.get("process", []):
        lines.append(
            f"| {stage.get('stage', '')} | {stage.get('minutes', '')} 分钟 | {stage.get('teacher_activity', '')} "
            f"| {stage.get('student_activity', '')} | {stage.get('intent', '')} |"
        )
    if lesson.get("board_design"):
        lines.append("")
        lines.append("## 板书 / 画面设计")
        lines.append(lesson["board_design"])
    if lesson.get("homework"):
        lines.append("")
        lines.append("## 课后任务")
        for item in lesson["homework"]:
            lines.append(f"- {item}")
    return "\n".join(lines)


def _assessment_labels(worksheet: dict[str, Any]) -> dict[str, str]:
    question_labels: dict[str, str] = {}
    for task in worksheet.get('tasks', []):
        for question in task.get('canonical_questions', []):
            identifier = question['assessment_id']
            if identifier not in question_labels:
                question_labels[identifier] = f'主评价 {len(question_labels) + 1}'
    return question_labels


def _render_question_references(value: str, question_labels: dict[str, str]) -> str:
    # Short identifiers such as "1" or "A" may be dates or answer options.
    identifiers = [identifier for identifier in question_labels if len(identifier) >= 5 and '_' in identifier]
    if not identifiers:
        return value
    pattern = '|'.join(re.escape(identifier) for identifier in sorted(identifiers, key=len, reverse=True))
    return re.sub(r'(?<![A-Za-z0-9_/-])(?:' + pattern + r')(?![A-Za-z0-9_/-])',
                  lambda match: question_labels[match.group()], value)


def _worksheet_markdown(course: str, worksheet: dict[str, Any], *, include_answers: bool, label: str | None) -> str:
    question_labels = _assessment_labels(worksheet)
    def question_label(value: str) -> str:
        return question_labels.get(value, value)

    def task_prompt(value: str) -> str:
        value = value.replace('系统插入的', '')
        return _render_question_references(value, question_labels)
    suffix = "（教师版）" if include_answers else "（学生版）"
    lines = [f"# {course} — {worksheet.get('title', '')} 学习单{suffix}"]
    if label:
        lines.append(f"> **{label}**")
    lines.append("")
    lines.append(worksheet.get("instructions", ""))
    case = worksheet.get('source_case') or {}
    if case.get('text'):
        heading = '## 本课案例（教学虚构）' if case.get('kind') == 'fictional' else '## 本课案例'
        lines.extend(['', heading, '', case['text']])
    if include_answers and worksheet.get('teacher_guidance'):
        guidance = worksheet['teacher_guidance']
        lines.extend(['', '## 评价使用说明', ''])
        if isinstance(guidance, str):
            lines.append(guidance)
        else:
            lines.append(guidance['administration'])
            for rule in guidance.get('decision_rules', []):
                lines.append(f"- {question_label(rule['assessment_ref'])}：{rule['trigger']} → {rule['action']}")
            if guidance.get('interpretation_boundary'):
                lines.append(guidance['interpretation_boundary'])
    if worksheet.get('reference_terms'):
        lines.extend(['', '## 术语参照', ''])
        for entry in worksheet['reference_terms']:
            lines.extend(['### ' + entry['term'], entry['definition']])
            abbreviations = entry.get('auxiliary_abbreviations') or []
            if abbreviations:
                lines.append('辅助缩写：' + '、'.join(abbreviations))
            lines.append('')
    for index, task in enumerate(worksheet.get("tasks", []), start=1):
        lines.append("")
        lines.append(f"## 任务 {index}：{task_prompt(task.get('prompt', ''))}")
        for question in task.get('canonical_questions', []):
            lines.extend(['', f"### {question_label(question['assessment_id'])}", question['question'], ''])
            lines.extend(question.get('options') or [])
            lines.append('')
            if include_answers:
                lines.append('**答案：** ' + question['answer'])
                lines.append('**解析：** ' + question.get('rationale', ''))
                verification = question.get('answer_verification')
                if isinstance(verification, str) and verification.strip():
                    lines.append('**评分与核验：** ' + verification)
                scoring = question.get('scoring')
                if isinstance(scoring, dict):
                    total = scoring.get('total_points', question.get('max_score'))
                    heading = f'**评分细则（满分 {total} 分）：**' if isinstance(total, (int, float)) else '**评分细则：**'
                    criteria = scoring.get('criteria')
                    if isinstance(criteria, list):
                        lines.append(heading)
                        for criterion in criteria:
                            if not isinstance(criterion, dict) or not isinstance(criterion.get('criterion'), str):
                                continue
                            points = criterion.get('points')
                            label = f"（{points} 分）" if isinstance(points, (int, float)) else ''
                            partial = criterion.get('partial_credit')
                            suffix = f'；部分得分：{partial}' if isinstance(partial, str) and partial else ''
                            lines.append(f"- {criterion['criterion']}{label}{suffix}")
                if question.get('remediation'):
                    remediation = question['remediation']
                    if isinstance(remediation, dict):
                        lines.append('**补救：**')
                        lines.extend(f'- {key}：{value}' for key, value in remediation.items())
                    else:
                        lines.append('**补救：** ' + str(remediation))
                retest = question.get('retest_question')
                if isinstance(retest, dict):
                    lines.append('**复测：** ' + str(retest.get('question', '')))
                    lines.extend(retest.get('options') or [])
                    lines.append('**复测答案：** ' + str(retest.get('answer', '')))
                    if retest.get('rationale'):
                        lines.append('**复测解析：** ' + retest['rationale'])
            else:
                if task.get('kind') == 'record_table' and not task.get('fields'):
                    # Canonical assessment tasks may have their generated
                    # answer-bearing table removed; preserve blank space when
                    # the prompt still asks the learner to use a record table.
                    lines.extend(['| 作答要点 | 记录 |', '|---|---|'])
                    lines.extend('|  |  |' for _ in range(6))
                else:
                    lines.append('作答：________________')
        fields = list(task.get('fields') or [])
        answer = task.get('answer')
        if task.get('row_labels') and fields and isinstance(answer, (dict, list)):
            answer_rows = list(answer.values()) if isinstance(answer, dict) else answer
            answer_columns = {key for row in answer_rows if isinstance(row, dict) for key in row if key != 'row_label'}
            # Some generators supply only data columns and omit the row-label heading.
            if fields[0] in answer_columns:
                fields.insert(0, '条目')
        if fields:
            lines.append("| " + " | ".join(fields) + " |")
            lines.append("|" + "---|" * len(fields))
            if task.get('row_labels'):
                for row_label in task['row_labels']:
                    lines.append('| ' + question_label(row_label) + ' |' + '  |' * (len(fields) - 1))
            else:
                # Answer rows can establish how much writing space is needed,
                # without exposing their labels or values to the student.
                answer_rows = list(answer.values()) if isinstance(answer, dict) else answer
                blank_rows = len(answer_rows) if isinstance(answer_rows, list) and all(isinstance(row, dict) for row in answer_rows) else 1
                lines.extend("|" + "  |" * len(fields) for _ in range(max(1, blank_rows)))
        if include_answers and task.get("answer"):
            answer = task['answer']
            if isinstance(answer, dict) and all(isinstance(value, str) for value in answer.values()):
                lines.append('**答案：**')
                lines.extend(f'- {question_label(key)}：{value}' for key, value in answer.items())
            elif isinstance(answer, (dict, list)):
                rows = list(answer.items()) if isinstance(answer, dict) else [
                    (row['row_label'], {key: value for key, value in row.items() if key != 'row_label'})
                    for row in answer
                ]
                answer_columns = [column for _, row in rows for column in row]
                has_data_first = bool(fields and fields[0] in answer_columns)
                columns = list(dict.fromkeys((fields if has_data_first else fields[1:]) + answer_columns))
                def cell(value: str) -> str:
                    return value.replace('|', '\\|').replace('\n', '<br>')
                row_heading = '条目' if has_data_first else (fields[0] if fields else '条目')
                lines.extend(['**答案：**', '', '| ' + cell(row_heading) + ' | ' + ' | '.join(map(cell, columns)) + ' |',
                              '|' + '---|' * (len(columns) + 1)])
                for stage, row in rows:
                    lines.append('| ' + cell(question_label(stage)) + ' | ' + ' | '.join(cell(row.get(column, '')) for column in columns) + ' |')
            else:
                lines.append(f"**答案：** {answer}")
            if task.get("answer_notes"):
                lines.append(f"**解析：** {task['answer_notes']}")
    if worksheet.get("reflection_questions"):
        lines.append("")
        lines.append("## 反思问题")
        for question in worksheet["reflection_questions"]:
            lines.append(f"- {question}")
    if not include_answers:
        lines.append("")
        lines.append(f"*{worksheet.get('student_version_note', '学生版不含答案')}*")
    return "\n".join(lines)


def _write_text_docx(path: Path, title: str, lines: list[str]) -> None:
    import docx
    from docx.enum.table import WD_ROW_HEIGHT_RULE
    from docx.shared import Cm

    document = docx.Document()
    _set_cjk_font(document)
    document.add_heading(title, level=1)
    index = 0
    while index < len(lines):
        text = lines[index].strip()
        if text.startswith('|') and text.endswith('|'):
            rows: list[list[str]] = []
            while index < len(lines):
                row = lines[index].strip()
                if not (row.startswith('|') and row.endswith('|')):
                    break
                cells = [cell.strip() for cell in row[1:-1].split('|')]
                if not all(re.fullmatch(r':?-{3,}:?', cell) for cell in cells):
                    rows.append(cells)
                index += 1
            if rows:
                width = max(len(row) for row in rows)
                table = document.add_table(rows=len(rows), cols=width)
                table.style = 'Table Grid'
                for row_index, cells in enumerate(rows):
                    for column_index, cell in enumerate(cells):
                        table.cell(row_index, column_index).text = cell
                    if row_index and not any(cells[1:]):
                        table.rows[row_index].height = Cm(0.7)
                        table.rows[row_index].height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
            continue
        index += 1
        if not text:
            continue
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text.removeprefix('> ').strip())
        if text.startswith("#"):
            level = min(len(text) - len(text.lstrip("#")), 3)
            document.add_heading(text.lstrip("# ").strip(), level=level)
            continue
        document.add_paragraph(text)
    document.save(str(path))


def write_exports(ctx: Any, *, mode: str, gate_ctx: gates.GateContext, note: str = "") -> dict[str, Any]:
    requirements = ctx.content("requirements") or {}
    course = requirements.get("course", "课程")
    readiness = gates.export_readiness_with_overrides(gate_ctx)
    blocking = list(readiness.get("blocking", []))
    if note:
        blocking.insert(0, note)
    label = LABEL_FORMAL if mode == "formal" else LABEL_DRAFT
    output_dir = _output_dir(ctx, mode)
    output_dir.mkdir(parents=True, exist_ok=True)
    spec = ctx.content("template_spec") or {}
    columns = [c["name"] for c in spec.get("columns", [])]
    files: list[dict[str, Any]] = []
    sections = (requirements.get("sections") or [])
    for section in sections:
        artifact_id = f"script:{section['section_id']}"
        script = ctx.content(artifact_id) or {}
        worksheet = ctx.content(f"worksheet:{section['section_id']}") or {}
        question_labels = _assessment_labels(worksheet)
        # Keep the stored revision intact; neutralize long question references
        # only in the learner-facing text used for the two script exports.
        script = {**script, 'units': [
            {**unit, 'text': _render_question_references(unit.get('text', ''), question_labels)}
            for unit in script.get('units', [])
        ]}
        rev_id = ctx.rev(artifact_id) or "r0"
        version = rev_id.split("@")[-1] if "@" in rev_id else rev_id
        stem = f"{_safe(course)}_{section['section_id']}.{version}"
        md_path = output_dir / f"{stem}.md"
        md_path.write_text(
            _section_markdown(course, script, LABEL_DRAFT if mode == "draft" else None, blocking if mode == "draft" else []),
            encoding="utf-8",
        )
        files.append(
            {
                "path": str(md_path),
                "kind": "markdown",
                "sha256": file_hash(md_path),
                "label": label,
                "role": "lesson_script",
            }
        )
        docx_path = output_dir / f"{stem}.docx"
        _write_docx(
            docx_path,
            course,
            script,
            columns,
            LABEL_DRAFT if mode == "draft" else None,
            blocking if mode == "draft" else [],
        )
        files.append(
            {
                "path": str(docx_path),
                "kind": "docx",
                "sha256": file_hash(docx_path),
                "label": label,
                "role": "lesson_script",
            }
        )

        def _add_media(source_path: str, kind: str, role: str, expected_hash: str | None = None) -> None:
            source = Path(source_path)
            raw = None
            if kind == 'svg':
                from . import media

                diagram_root = (Path(ctx.store.base_dir) / 'media' / 'diagrams').resolve()
                if not source.resolve().is_relative_to(diagram_root) or not expected_hash:
                    raise ValueError('图示路径或修订哈希无效，无法导出')
                try:
                    with source.open('rb') as stream:
                        raw = stream.read(media.MAX_SVG_BYTES + 1)
                    svg = raw.decode('utf-8')
                except (OSError, UnicodeError) as exc:
                    raise ValueError('无法读取图示修订文件，无法导出') from exc
                if len(raw) > media.MAX_SVG_BYTES:
                    raise ValueError('图示文件过大，无法导出')
                normalized = svg.replace('\r\n', '\n').replace('\r', '\n')
                if (media.svg_sha256(svg) != expected_hash and media.svg_sha256(normalized) != expected_hash) or media.validate_svg(svg):
                    raise ValueError('图示内容与修订哈希不一致或 SVG 无效，无法导出')
            if not source.exists():
                return
            target = output_dir / f"{_safe(course)}_{section['section_id']}_{source.name}"
            if raw is not None:
                target.write_bytes(raw)
            else:
                shutil.copyfile(source, target)
            files.append(
                {"path": str(target), "kind": kind, "sha256": file_hash(target), "label": label, "role": role}
            )

        diagrams_doc = ctx.content(f"diagrams:{section['section_id']}") or {}
        for diagram in diagrams_doc.get("diagrams", []):
            _add_media(str(diagram.get("svg_path", "")), "svg", "diagram", diagram.get('svg_sha256'))
        storyboard_doc = ctx.content(f"storyboard:{section['section_id']}") or {}
        if storyboard_doc.get("shots"):
            media_base = Path(ctx.store.base_dir) / "media"
            _add_media(str(media_base / "storyboard" / f"{section['section_id']}.json"), "json", "storyboard")
            _add_media(str(media_base / "storyboard" / f"{section['section_id']}.md"), "markdown", "storyboard")
            _add_media(str(media_base / "prompts" / f"{section['section_id']}.txt"), "txt", "prompt")

        draft_label = LABEL_DRAFT if mode == "draft" else None
        lesson = ctx.content(f"lesson_plan:{section['section_id']}") or {}
        if lesson:
            lesson_path = output_dir / f"{stem}.lesson.md"
            lesson_path.write_text(_lesson_markdown(course, lesson, draft_label), encoding="utf-8")
            files.append(
                {"path": str(lesson_path), "kind": "markdown", "sha256": file_hash(lesson_path), "label": label, "role": "lesson_plan"}
            )
            lesson_docx = output_dir / f"{stem}.lesson.docx"
            _write_text_docx(
                lesson_docx,
                f"{course} — {lesson.get('title', '')}（教案）",
                _lesson_markdown(course, lesson, draft_label).splitlines(),
            )
            files.append(
                {"path": str(lesson_docx), "kind": "docx", "sha256": file_hash(lesson_docx), "label": label, "role": "lesson_plan"}
            )
        if worksheet:
            student_path = output_dir / f"{stem}.worksheet.student.md"
            student_path.write_text(
                _worksheet_markdown(course, worksheet, include_answers=False, label=draft_label), encoding="utf-8"
            )
            files.append(
                {"path": str(student_path), "kind": "markdown", "sha256": file_hash(student_path), "label": label, "role": "worksheet"}
            )
            student_docx = output_dir / f"{stem}.worksheet.student.docx"
            _write_text_docx(
                student_docx,
                f"{course} — {worksheet.get('title', '')} 学习单（学生版）",
                _worksheet_markdown(course, worksheet, include_answers=False, label=draft_label).splitlines(),
            )
            files.append(
                {"path": str(student_docx), "kind": "docx", "sha256": file_hash(student_docx), "label": label, "role": "worksheet"}
            )
            teacher_path = output_dir / f"{stem}.worksheet.teacher.md"
            teacher_path.write_text(
                _worksheet_markdown(course, worksheet, include_answers=True, label=draft_label), encoding="utf-8"
            )
            files.append(
                {"path": str(teacher_path), "kind": "markdown", "sha256": file_hash(teacher_path), "label": label, "role": "worksheet_teacher"}
            )


    deck = ctx.content("pptx_deck") or {}
    deck_path = Path(str(deck.get("path", ""))) if deck.get("path") else None
    if deck_path is not None and deck_path.is_file():
        target = output_dir / f"{_safe(course)}_slides.pptx"
        shutil.copyfile(deck_path, target)
        files.append(
            {"path": str(target), "kind": "pptx", "sha256": file_hash(target), "label": label, "role": "presentation"}
        )

    manifest: dict[str, Any] = {
        "project_id": ctx.project_id,
        "mode": mode,
        "draft_label": LABEL_DRAFT if mode == "draft" else None,
        "files": files,
        "gate_summary": readiness.get("summary", []),
        "renderer": _renderer_info(),
        "signoffs": current_signoffs(ctx.store),
        "created_at": now_iso(),
    }
    return manifest


def _renderer_info() -> dict[str, Any]:
    try:
        from importlib.metadata import version as _pkg_version

        docx_version = _pkg_version("python-docx")
    except Exception:  # noqa: BLE001 - informational metadata only
        docx_version = "unknown"
    return {"docx": f"python-docx {docx_version}", "fonts": ["Microsoft YaHei"], "qa": "python-docx 打开/解析检查"}


def _safe(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_()" or "\u4e00" <= ch <= "\u9fff" else "_" for ch in text)[:40]
