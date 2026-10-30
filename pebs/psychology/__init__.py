"""Versioned psychology teaching content, independent of media production."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import hashlib
from .. import schemas

CONTENT_PATH = Path(__file__).resolve().parents[2] / "curriculum" / "psychology" / "classical-conditioning.json"
SOURCE_DIRECTORY = CONTENT_PATH.parent / 'sources'
UNIT_SOURCES = {
    'classical-conditioning': 'openstax-6-2-ccby4',
    'operant-conditioning': 'openstax-6-3-ccby4',
    'research-methods': 'openstax-2-3-ccby4',
}
UNIT_TITLES = {'classical-conditioning': '经典条件作用',
               'operant-conditioning': '操作性条件作用', 'research-methods': '心理学研究方法'}
EXTRA_UNIT_SOURCES = {
    'research-methods': {'kim-thoemmes-2026-mediation': 'kim-thoemmes-2026-mediation-ccby4'},
}


def source_snapshot(unit_id: str = 'classical-conditioning') -> tuple[dict, str]:
    slug = UNIT_SOURCES[unit_id]
    metadata = json.loads((SOURCE_DIRECTORY / f'{slug}.metadata.json').read_text(encoding='utf-8'))
    text = (SOURCE_DIRECTORY / f'{slug}.txt').read_text(encoding='utf-8')
    if hashlib.sha256(text.encode('utf-8')).hexdigest() != metadata['sha256']:
        raise ValueError('source snapshot hash mismatch')
    return metadata, text


def extra_source_snapshots(unit_id: str) -> dict:
    """Read explicitly catalogued additional snapshots with their own hashes."""
    result = {}
    for source_id, slug in EXTRA_UNIT_SOURCES.get(unit_id, {}).items():
        metadata = json.loads((SOURCE_DIRECTORY / f'{slug}.metadata.json').read_text(encoding='utf-8'))
        text = (SOURCE_DIRECTORY / f'{slug}.txt').read_text(encoding='utf-8')
        if hashlib.sha256(text.encode('utf-8')).hexdigest() != metadata['sha256']:
            raise ValueError('additional source snapshot hash mismatch')
        result[source_id] = {'metadata': metadata, 'text': text}
    return result


def published_rules(store, unit_revision: dict) -> list[dict]:
    """Select project-local teaching recommendations for this exact input."""
    from .. import pii

    selected = []
    for artifact in store.list_artifacts():
        if artifact['artifact_type'] != 'psychology_rule':
            continue
        revisions = store.revisions_of(artifact['artifact_id'])
        if not revisions:
            continue
        revision = store.get_revision(revisions[-1])
        content = revision['content']
        if content['status'] != 'PUBLISHED' or content['target']['content_hash'] != unit_revision['content_hash']:
            continue
        verification = content.get('verification') or {}
        cases = verification.get('cases') or []
        concepts = {c['concept_id'] for c in unit_revision['content']['concepts']}
        if (content.get('verification_status') != 'PASS'
                or verification.get('role') != 'teacher'
                or {case.get('kind') for case in cases} != {'positive', 'counterexample'}
                or not all(case.get('passed') is True and str(case.get('rationale', '')).strip() for case in cases)
                or not content.get('concept_refs') or not set(content['concept_refs']) <= concepts):
            raise ValueError('published rule lacks valid case verification or concept scope')
        if pii.scan(content['recommendation']):
            raise ValueError('published teaching rule contains identifiable data; redaction required')
        selected.append({'artifact_id': artifact['artifact_id'], 'revision_id': revision['revision_id'],
                         'content_hash': revision['content_hash'], 'concept_refs': content['concept_refs'],
                         'recommendation': content['recommendation']})
    return sorted(selected, key=lambda item: item['artifact_id'])


def classical_conditioning() -> dict:
    """Load an independent snapshot and reject broken content references."""
    unit = json.loads(CONTENT_PATH.read_text(encoding="utf-8"))
    if unit.get('unit_id') != 'classical-conditioning':
        raise ValueError('unit identity does not match catalog entry')
    metadata, snapshot = source_snapshot()
    return validate_unit(unit, metadata, snapshot)


def load_unit(unit_id: str) -> dict:
    """Load only explicitly catalogued units and their pinned source."""
    if unit_id not in UNIT_SOURCES:
        raise KeyError(unit_id)
    if unit_id == 'classical-conditioning':
        return classical_conditioning()
    unit = json.loads((CONTENT_PATH.parent / f'{unit_id}.json').read_text(encoding='utf-8'))
    if unit.get('unit_id') != unit_id:
        raise ValueError('unit identity does not match catalog entry')
    metadata, snapshot = source_snapshot(unit_id)
    extras = extra_source_snapshots(unit_id) if len(unit.get('sources', [])) > 1 else {}
    return validate_unit(unit, metadata, snapshot, extras)


def validate_unit(unit: dict, metadata: dict, snapshot: str, extra_sources: dict | None = None) -> dict:
    """Validate catalog or frozen content against the supplied source snapshot."""
    if hashlib.sha256(snapshot.encode('utf-8')).hexdigest() != metadata['sha256']:
        raise ValueError('source snapshot hash mismatch')
    try:
        schemas.validate(unit, "psychology_unit")
    except schemas.SchemaError as exc:
        raise ValueError(str(exc)) from exc
    if unit.get("unit_id") not in UNIT_SOURCES or not unit.get("version"):
        raise ValueError("invalid unit identity or version")
    sources = {s["source_id"] for s in unit["sources"]}
    if len(sources) != len(unit['sources']):
        raise ValueError('duplicate source identifier')
    if unit['teacher_review']['status'] != 'PENDING':
        raise ValueError('embedded teacher approval is not a project review record')
    if unit['sources'][0].get('snapshot_sha256') != metadata['sha256']:
        raise ValueError('unit source snapshot hash mismatch')
    primary = unit['sources'][0]
    if len(unit['sources']) > 1 and (not primary.get('version_url') or not primary.get('title')):
        raise ValueError('multi-source unit requires primary source identity')
    if ((primary.get('version_url') and primary['version_url'] != metadata.get('url'))
            or (primary.get('title') and primary['title'] != metadata.get('title'))):
        raise ValueError('primary source identity mismatch')
    pinned_source_id = unit['sources'][0]['source_id']
    source_texts = {pinned_source_id: snapshot}
    extra_sources = extra_sources or {}
    if set(extra_sources) != sources - {pinned_source_id}:
        raise ValueError('additional source snapshot set mismatch')
    for source in unit['sources'][1:]:
        source_id = source['source_id']
        frozen = extra_sources.get(source_id)
        if not frozen:
            raise ValueError('additional source snapshot unavailable')
        source_metadata, source_text = frozen['metadata'], frozen['text']
        digest = hashlib.sha256(source_text.encode('utf-8')).hexdigest()
        if digest != source_metadata['sha256'] or digest != source.get('snapshot_sha256'):
            raise ValueError('additional source snapshot hash mismatch')
        if (source_metadata.get('url') != source.get('url')
                or source_metadata.get('title') != source.get('title')):
            raise ValueError('additional source identity mismatch')
        source_texts[source_id] = source_text
    concepts = {c["concept_id"] for c in unit["concepts"]}
    questions = {q["assessment_id"] for q in unit["assessments"]}
    prerequisites = {c['concept_id']: c.get('prerequisites', []) for c in unit['concepts']}
    visited, active = set(), set()

    def visit(concept_id: str) -> None:
        if concept_id not in concepts:
            raise ValueError('unknown prerequisite concept')
        if concept_id in active:
            raise ValueError('prerequisite cycle')
        if concept_id in visited:
            return
        active.add(concept_id)
        for prerequisite in prerequisites[concept_id]:
            visit(prerequisite)
        active.remove(concept_id)
        visited.add(concept_id)

    for concept_id in concepts:
        visit(concept_id)
    if len(concepts) != len(unit["concepts"]) or len(questions) != len(unit["assessments"]):
        raise ValueError("duplicate concept or assessment identifier")
    for concept in unit["concepts"]:
        for source in concept["source_refs"]:
            if source not in sources:
                raise ValueError(f"unknown source reference: {source}")
        anchor = concept.get('evidence_anchor', {})
        if anchor.get('source_ref') not in concept['source_refs'] or anchor.get('source_ref') not in source_texts:
            raise ValueError('concept anchor source reference mismatch')
        anchor_snapshot = source_texts[anchor['source_ref']]
        start, end = anchor.get('start_char', -1), anchor.get('end_char', -1)
        if not (0 <= start < end <= len(anchor_snapshot)) or anchor_snapshot[start:end] != anchor.get('text'):
            raise ValueError('concept source anchor is not locatable')
    terminology = unit.get('terminology', [])
    if len({entry['term_id'] for entry in terminology}) != len(terminology):
        raise ValueError('duplicate terminology identifier')
    for entry in terminology:
        if not set(entry['source_refs']).issubset(sources):
            raise ValueError('unknown terminology source reference')
        anchor = entry['evidence_anchor']
        anchor_snapshot = source_texts.get(anchor['source_ref'], '')
        start, end = anchor['start_char'], anchor['end_char']
        if (anchor['source_ref'] not in entry['source_refs'] or anchor['source_ref'] not in source_texts
                or not (0 <= start < end <= len(anchor_snapshot))
                or anchor_snapshot[start:end] != anchor['text']
                or anchor['verification_status'] != 'LOCATED_ONLY'):
            raise ValueError('terminology source anchor is not locatable')
        for language in ('zh-CN', 'en', 'ja', 'ko'):
            localized = entry['terms'][language]
            if not isinstance(localized, dict) or not isinstance(localized.get('full'), str) or not localized['full'].strip():
                raise ValueError('localized terminology must use a full term')
    for question in unit["assessments"]:
        if question["concept_ref"] not in concepts:
            raise ValueError("unknown concept reference")
        if question.get("followup_ref") and question["followup_ref"] not in questions:
            raise ValueError("unknown followup reference")
        if question['kind'] == 'diagnostic':
            if not isinstance(question.get('followup_ref'), str) or question['followup_ref'] not in questions:
                raise ValueError('diagnostic followup reference is missing or unknown')
            followup = next(q for q in unit['assessments'] if q['assessment_id'] == question['followup_ref'])
            if followup['kind'] != 'retest' or followup['concept_ref'] != question['concept_ref']:
                raise ValueError('followup must be a retest for the same concept')
            concept = next(c for c in unit['concepts'] if c['concept_id'] == question['concept_ref'])
            misconceptions = {m['misconception_id'] for m in concept['misconceptions']}
            if question['misconception_ref'] not in misconceptions:
                raise ValueError('unknown diagnostic misconception reference')
            options = question.get('option_details', [])
            if len(options) != len(question['options']) or len({o['option_id'] for o in options}) != len(options):
                raise ValueError('invalid diagnostic option identifiers')
            if [o['text'] for o in options] != question['options']:
                raise ValueError('option text mismatch')
            if sum(o['text'] == question['answer'] for o in options) != 1:
                raise ValueError('diagnostic needs exactly one correct answer')
            for option in options:
                if option['text'] == question['answer'] and option.get('misconception_ref') is not None:
                    raise ValueError('correct option cannot diagnose a misconception')
                if option['text'] != question['answer'] and option.get('misconception_ref') not in misconceptions:
                    raise ValueError('unknown option misconception reference')
    return unit


def unit_terms(unit: dict) -> list[dict]:
    """Use concept terminology where a unit has no separate glossary."""
    return unit.get('terminology') or [
        {'term_id': c['concept_id'], 'definition': c['definition'], 'terms': c['terms'],
         'auxiliary_abbreviations': []} for c in unit.get('concepts', [])
    ]


def teaching_materials(unit: dict, audience: str) -> dict:
    """Explicit student projection prevents future teacher fields leaking out."""
    if audience not in {"student", "teacher"}:
        raise ValueError("unknown material audience")
    result = {
        "unit_id": unit["unit_id"], "version": unit["version"],
        "status": "draft", "label": "草稿—未通过 QA", "audience": audience,
        'terminology': [
            {'term_id': entry['term_id'], 'definition': entry['definition'],
             'terms': {language: {'full': localized['full']} for language, localized in entry['terms'].items()},
             'auxiliary_abbreviations': list(entry.get('auxiliary_abbreviations', []))}
            for entry in unit_terms(unit)
        ],
        "questions": [
            {key: value for key, value in question.items()
             if key in {"assessment_id", "question", "options", "kind"}}
            for question in unit["assessments"]
        ],
    }
    for projected, question in zip(result['questions'], unit['assessments']):
        if question['kind'] == 'diagnostic':
            projected['option_details'] = [
                {'option_id': option['option_id'], 'text': option['text']}
                for option in question['option_details']
            ]
    if audience == "teacher":
        result.update({"teacher_review": deepcopy(unit["teacher_review"]),
                       "terminology": deepcopy(unit_terms(unit)),
                       "concepts": deepcopy(unit["concepts"]),
                       "sources": deepcopy(unit["sources"]),
                       "questions": deepcopy(unit["assessments"])})
    return result


def diagnose(unit: dict, assessment_id: str, option_id: str) -> dict:
    """Return a followup suggestion, without recording a student diagnosis."""
    question = next((q for q in unit['assessments']
                     if q['assessment_id'] == assessment_id and q['kind'] == 'diagnostic'), None)
    if question is None:
        raise ValueError('unknown diagnostic assessment')
    option = next((o for o in question.get('option_details', []) if o['option_id'] == option_id), None)
    if option is None:
        raise ValueError('unknown option')
    correct = option['text'] == question['answer']
    result = {'correct': correct, 'interpretation': 'needs_followup' if not correct else 'correct_on_this_item',
              'unit_version': unit['version']}
    if not correct:
        concept = next(c for c in unit['concepts'] if c['concept_id'] == question['concept_ref'])
        misconception = next(m for m in concept['misconceptions']
                             if m['misconception_id'] == option['misconception_ref'])
        retest = next(q for q in unit['assessments'] if q['assessment_id'] == question['followup_ref'])
        result.update({'misconception_ref': misconception['misconception_id'],
                       'remediation': misconception['remediation'],
                       'retest_goal': misconception['retest_goal'],
                       'retest': {key: retest[key] for key in ('assessment_id', 'question', 'kind', 'options') if key in retest}})
    return result


def materials_markdown(materials: dict) -> str:
    """Render already-projected material, preserving its frozen target."""
    target = materials['target']
    lines = [f"# {UNIT_TITLES[materials['unit_id']]}学习材料", '', materials['label'], '',
             f"版本：{materials['version']}", f"修订：{target['revision_id']}",
             f"内容哈希：{target['content_hash']}", '',
             '情境为教学假设；来源核验和课堂适用性需按项目记录确认。', '']
    teacher = materials['audience'] == 'teacher'
    if materials.get('terminology'):
        lines.extend(['## 核心术语', ''])
        for entry in materials['terminology']:
            lines.extend(['### ' + entry['terms']['zh-CN']['full'], '', entry['definition'],
                          '辅助缩写：' + '、'.join(entry.get('auxiliary_abbreviations', [])), ''])
    if teacher:
        review = materials['teacher_review']
        if review['status'] == 'PENDING':
            lines.extend(['待真人教师审核；此文件不代表教师签署。', ''])
        else:
            lines.extend([f"内容审核：{review['status']}",
                          f"审核人：{review['reviewer']}", f"审核依据：{review['basis']}",
                          '内容审核不代替项目正式签署及证据核验。', ''])
    for question in materials['questions']:
        lines.extend([f"## {question['assessment_id']}", '', question['question'], ''])
        for option in question.get('option_details', []):
            lines.append(f"- {option['option_id']}：{option['text']}")
        if not question.get('option_details'):
            lines.extend(f'- {option}' for option in question.get('options', []))
        if teacher:
            lines.extend(['', '评分依据：' + question.get('rationale', question.get('scoring_guidance', '待补充'))])
            if question.get('answer'):
                lines.append('参考答案：' + question['answer'])
            if question.get('misconception_ref'):
                lines.append('误解关联：' + question['misconception_ref'])
        lines.append('')
    if teacher:
        lines.extend(['## 概念与教学边界', ''])
        for concept in materials['concepts']:
            lines.extend([f"### {concept['terms']['zh-CN']['full']}", '',
                          concept['definition'], '边界：' + concept.get('boundary', '待补充'),
                          '先修：' + '、'.join(concept.get('prerequisites', []))])
            for label, example in concept.get('examples', {}).items():
                kind = '正例' if label == 'positive' else '反例'
                lines.append(f"{kind}（虚构教学情境）：{example['text']}")
            anchor = concept.get('evidence_anchor') or {}
            lines.extend([f"来源定位状态：{anchor.get('verification_status', 'PENDING')}", ''])
        lines.extend(['## 来源记录', ''])
        for source in materials['sources']:
            lines.extend([source.get('title', source['source_id']), source['url'],
                          '固定版本：' + source.get('version_url', source['url']),
                          '来源许可：' + source.get('license', '待核对'),
                          source.get('attribution', ''),
                          '来源核验状态：' + source['verification_status'],
                          '快照哈希：' + source.get('snapshot_sha256', '未提供'), ''])
        lines.extend(['## 补救与复测目标', ''])
        for concept in materials['concepts']:
            for misconception in concept['misconceptions']:
                lines.extend([f"- {misconception['misconception_id']}：{misconception['remediation']}",
                              f"  复测目标：{misconception['retest_goal']}；依据类型：{misconception['basis']}"])
    return '\n'.join(lines) + '\n'
