---
name: textbook-problem-intake
description: 교재 추출본 안에 포함된 사례형·객관식 문제를 스캔해 후보 manifest와 진행로그를 만들고, 이후 `problem_index.json` 등록 준비나 실제 등록까지 이어지는 로컬 스킬. "교재 안 문제 인식", "교재 문제 후보 추출", "교재 문제 DB 등록", "embedded problem scan", "textbook problem intake" 요청 시 사용.
---

# Textbook Problem Intake

교재 extract에서 숨어 있는 문제를 찾아 별도 후보 manifest로 모으고, 나중에 `problem_index.json > problems.textbook`으로 올릴 수 있게 정리한다. 실제 등록 전에도 `case-answer-review`가 이 후보 manifest를 직접 읽으므로, 먼저 스캔하고 나중에 DB 반영하는 순서로 운영한다.

## Quick Start

기존 extract를 그대로 쓸 때:

```powershell
python .agent/skills/textbook-problem-intake/scripts/run_textbook_intake.py --subject 민법 --skip-extract
```

새 교재 PDF를 넣고 한 번에 처리할 때:

```powershell
python .agent/skills/textbook-problem-intake/scripts/run_textbook_intake.py --subject 민법 --pdf-dir "H:\내 드라이브\민사\민법\교재"
```

실제 DB 반영까지 할 때:

```powershell
python .agent/skills/textbook-problem-intake/scripts/run_textbook_intake.py --subject 민법 --skip-extract --apply
```

## Workflow

### 1. 입력 상태를 확인한다

- `.agent/data/pdf_extracts/chunks_index.json`이 있는지 확인한다.
- `.agent/state/problem_index.json`과 `.agent/state/alignment.json`을 읽어 subject/topic 매핑 가능 여부를 확인한다.
- 교재 문제가 이미 `problem_index.json > problems.textbook`에 들어가 있는지 먼저 확인한다.

### 2. 교재 문제 후보를 스캔한다

기본 호출은 `scripts/run_textbook_intake.py`로 하고, 내부에서 `../problem-index/scripts/scan_textbook_embedded_problems.py`를 호출한다.

```powershell
python .agent/skills/textbook-problem-intake/scripts/run_textbook_intake.py --subject 민법 --skip-extract
```

생성 파일:
- `.agent/state/textbook_problem_candidates.json`
- `.agent/state/textbook_problem_scan_log.json`

운영 원칙:
- 사례형/객관식 신호가 있는 chunk만 후보로 올린다.
- topic 매핑이 안 되면 추정 등록하지 말고 `pending_topic_mapping`으로 남긴다.
- `source_pdf`, `page_span_hint`, `question_preview`를 유지한다.

### 3. 등록 전 dry-run으로 검토한다

기본은 `scripts/run_textbook_intake.py`가 `../problem-index/scripts/register_textbook_problem_candidates.py`를 dry-run으로 실행한다.

```powershell
python .agent/skills/textbook-problem-intake/scripts/run_textbook_intake.py --subject 민법 --skip-extract
```

확인 파일:
- `.agent/state/textbook_problem_register_log.json`
- `.agent/state/textbook_problem_pipeline_log.json`

검토 포인트:
- 등록 대상 수
- topic 미매핑 수
- 중복 여부
- `question_text`와 `choices` 보존 여부

### 4. 필요할 때만 DB에 반영한다

사용자가 실제 등록을 원할 때만 `--apply`를 붙인다.

```powershell
python .agent/skills/textbook-problem-intake/scripts/run_textbook_intake.py --subject 민법 --skip-extract --apply
```

반영 위치:
- `.agent/state/problem_index.json`
- `subjects.{subject}.topics.{topic}.problems.textbook`

### 5. 다운스트림 검토에 연결한다

- `../case-answer-review/SKILL.md`는 등록 전 후보 manifest를 직접 읽는다.
- DB 반영 전에도 사례답안 채점 보고서에서 `교재 내 문제 후보`를 보여줄 수 있다.
- 구조도와 연결 관계는 `../../workflows/skill-structure.md`를 기준으로 확인한다.
- 새 교재를 넣을 때는 `pdf-ingest -> scan -> register dry-run`을 이 스킬 하나로 묶어 호출한다.

## Detailed Checks

```powershell
python .agent/skills/problem-index/scripts/query_problems.py --subject 민법 --topic 행위능력
```

```powershell
python .agent/skills/case-answer-review/scripts/render_case_answer_review.py --subject 민법 --topic 행위능력 --text "답안 본문..." --skip-rag
```

## Output Contract

- 스캔만 수행하면 candidate manifest와 scan log를 만든다.
- dry-run 등록은 register log만 갱신한다.
- `--apply` 등록은 `problem_index.json`의 `problems.textbook`만 확장한다.
- 전체 파이프라인 호출은 `.agent/state/textbook_problem_pipeline_log.json`에 단계별 실행 로그를 남긴다.
- 자료가 부족하면 추정 등록하지 말고 `자료 부족—보류`로 남긴다.
