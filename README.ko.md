# PEBS · 심리학 교육 자료 제작 시스템

**근거를 추적하고, 수정 범위를 관리하며, 교사가 검토할 수 있는 수업 자료를 만듭니다.**

[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

[![Code CI](https://github.com/Beritwu/psychology-education-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/Beritwu/psychology-education-skills/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)

[**수업과 애니메이션 체험 →**](https://beritwu.github.io/psychology-education-skills/)
 · [사용 설명서 — 영어](docs/usage.md)
 · [사용 설명서 — 중국어](docs/usage.zh-CN.md)

![고전적 조건형성의 세 단계](examples/classical-conditioning/preview.png)

## PEBS란?

심리학 교사, 교원 연수 담당자, 교육과정 개발팀을 위한 로컬 Python 애플리케이션입니다.
요구사항, 학습 설계, 심리학적 주장, 근거 자료, 수업 자료, 미디어, 품질 검사와 내보내기를
버전 관리가 가능한 하나의 작업 흐름으로 연결합니다. 웹 작업 화면, CLI, REST API를 제공합니다.

현재 목록에는 **내장 스킬 22개와 선택적으로 설치하는 외부 교육 스킬 14개**가 있습니다.
SKILL.md 파일만 복사해서 전체 기능을 사용할 수는 없습니다. 새 컴퓨터에서는 의존성과
스킬 실행 파일을 별도로 설치해야 합니다.

## 주요 기능

| 작업 | 기능 |
|---|---|
| 수업 설계 | 학습 목표, 평가 과제, 교수 순서, 사례와 활동지 |
| 근거 확인 | 학술 검색, 저장된 출처, 위치를 확인할 수 있는 인용과 검토 상태 |
| 자료 제작 | 지도안, 강의 원고, 학습자·교사용 자료, SVG, 편집 가능한 PPTX |
| 부분 수정 | 지정 부분 수정, 유지할 부분 보호, 연관 자료의 갱신 필요성 추적 |
| 결과물 관리 | 현재 버전에 해당하는 품질 검사, 정식 조건 미충족 시 초안 표시 |
| 평가 | 벤치마크, 스킬 버전 기록, 버전을 고정한 교사 평가 패키지 |

## 빠른 시작

Python 3.11 이상이 필요하며, 처음에는 Python 3.12를 권장합니다.

```bash
git clone https://github.com/Beritwu/psychology-education-skills.git
cd psychology-education-skills
python -m venv .venv
```

Windows PowerShell: `.venv\Scripts\Activate.ps1`.
macOS/Linux: `source .venv/bin/activate`.

```bash
python -m pip install -r requirements.txt
python -m pebs.cli serve --port 8710
```

**http://127.0.0.1:8710**에 접속합니다. 화면과 정적 예제는 모델 없이 살펴볼 수 있습니다.
실제 자료 생성에는 모델 서비스가 필요합니다. 기본 설정은 로컬에 설치하고 로그인한 Codex CLI이며,
`openai_compatible`도 지원합니다. 비밀 키는 환경 변수로 설정합니다.

```bash
python -m pebs.cli build --project first_course --planner dynamic --max-model-calls 20 --max-research 8 --max-seconds 900 --request "Create one introductory psychology lesson with a fictional case and a formative question. No PPT and no animation."
```

모델 사용량이 발생합니다. 생성 후 변경 사항을 검토한 다음 승인하거나 거절합니다.
승인만으로 정식 내보내기 조건이 충족되는 것은 아닙니다. 자세한 절차는 [사용 설명서](docs/usage.md)에 있습니다.

## 외부 교육 스킬 설치

[Gareth Manning의 Education Agent Skills](https://github.com/GarethManning/education-agent-skills)에서
14개를 선택하고 `6bbbce41…` 버전으로 고정했습니다. 그중 3개에는 PEBS 정책 패치가 적용됩니다.
새로 복제한 저장소에는 실행 캐시가 없으므로 다음을 실행합니다.

```bash
python -c "from pebs.provider_edu import install; install()"
python -c "from pebs.provider_edu import verify; r=verify(); print(r); raise SystemExit(0 if r['ok'] else 1)"
```

고정된 아카이브를 내려받고 명세에 기록된 검토 정책과 패치를 적용합니다. 상위 프로젝트의
스크립트는 실행하지 않습니다. 도입 전 명세를 검토하세요. 기본 선택은 내장 스킬이며,
재설치와 사용자 정의 스킬은 사용 설명서를 참고합니다.

## 예제 수업과 애니메이션

[고전적 조건형성 예제](examples/classical-conditioning/README.md)는 20분 수업 지도안, 활동지,
교사용 정답, 스킬 적용 기록, 스토리보드, 네 언어를 지원하는 애니메이션을 포함합니다.
`examples/classical-conditioning/index.html`을 브라우저로 열면 오프라인에서도 실행됩니다.
역방향 설계, 이해를 진단하는 질문, 이중 부호화 스킬을 적용했습니다.

스킬 적용 기록과 출처를 함께 제공합니다. 애니메이션은 재생, 일시 정지, 단계별 보기를 지원하며
정적 그림과 함께 수업에 활용할 수 있습니다.

## 문서와 기여

[사용 방법](docs/usage.md) · [스킬 목록](docs/skills.md) · [구조](documentation/architecture.md)
 · [교사 평가](docs/evaluation-workflow.md) · [로드맵](docs/roadmap.md)
 · [기여 안내](CONTRIBUTING.md) · [보안](SECURITY.md) · [변경 기록](CHANGELOG.md)

```bash
python -m compileall -q pebs
python -m pytest tests -q -m "not integration and not live_research"
```

자동 테스트는 소프트웨어 동작을 확인하며 교육 효과를 입증하지 않습니다.
한국어 소개와 데모를 제공하지만, 애플리케이션 UI는 주로 중국어입니다.

## 라이선스

독자 코드와 문서는 [MIT](LICENSE), 외부 교육 스킬 수정본과 예제의 교육 내용은
**CC BY-SA 4.0**입니다. [제3자 저작물 안내](THIRD_PARTY_NOTICES.md)를 확인하세요.
