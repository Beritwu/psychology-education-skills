"""The approved three-unit question-bank scope through the public API."""

import pytest
from fastapi.testclient import TestClient

from pebs.server import app


@pytest.mark.parametrize('unit_id', [
    'classical-conditioning', 'operant-conditioning', 'research-methods',
])
def test_question_bank_supports_six_main_questions_and_four_followups(unit_id):
    with TestClient(app) as client:
        response = client.get(f'/api/psychology/units/{unit_id}')
        assert response.status_code == 200, response.text
        items = response.json()['assessments']
        diagnostics = [item for item in items if item['kind'] == 'diagnostic']
        retests = {item['assessment_id']: item for item in items if item['kind'] == 'retest'}
        assert len(diagnostics) >= 6
        assert len(retests) >= 4
        for item in diagnostics:
            assert item['answer'] in item['options']
            assert retests[item['followup_ref']]['concept_ref'] == item['concept_ref']
        for item in (item for item in diagnostics if '-application-' in item['assessment_id']):
            for option in item['option_details']:
                result = client.post(f'/api/psychology/units/{unit_id}/diagnose', json={
                    'assessment_id': item['assessment_id'], 'option_id': option['option_id'],
                })
                assert result.status_code == 200, result.text
                outcome = result.json()
                assert outcome['correct'] == (option['text'] == item['answer'])
                if not outcome['correct']:
                    assert outcome['misconception_ref'] == option['misconception_ref']
                    assert outcome['remediation'] and 'answer' not in outcome['retest']
        student = client.get(f'/api/psychology/units/{unit_id}/materials?audience=student')
        assert student.status_code == 200, student.text
        assert len(student.json()['questions']) >= 10
        assert all('answer' not in item and 'rationale' not in item
                   for item in student.json()['questions'])
