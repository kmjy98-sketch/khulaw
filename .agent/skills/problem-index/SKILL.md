---
name: problem-index
description: 문제 인덱스 관리. 진도 기반 문제 조회, 인덱스 보정, 교재 문제 후보 스캔/등록.
---

# problem-index Skill

<!-- @rule: AGENTS.md#2 Not-in-Source -->
<!-- @rule: GEMINI.md#2 Not-in-Source -->

## Quick Start

진도 기반 문제 조회:

```powershell
python .agent/skills/problem-index/scripts/query_problems.py --lecture 10
```

인덱스 보정 dry-run:

```powershell
python .agent/skills/problem-index/scripts/repair_problem_index.py --dry-run
```

기존 `dt`와 겹치는 레거시 `case` 정리:

```powershell
python .agent/skills/problem-index/scripts/repair_problem_index.py --prune-candidate-overlaps --dry-run
```

## 주요 기능

### 1. 진도 기반 문제 조회

```powershell
python scripts/query_problems.py --lecture 10 [--subject 민법] [--json]
```

- 지정 회차 기준으로 `problem_index.json`에서 문제를 조회합니다.
- `--json`을 주면 후속 파이프라인에서 바로 쓸 수 있는 JSON으로 출력합니다.

### 2. 문제 파일 스캔 및 인덱스 등록

```powershell
python scripts/scan_problems.py [--dir <경로>] [--dry-run]
```

- 문제 파일명과 메타데이터를 읽어 인덱스 후보를 만듭니다.
- `--dry-run`은 파일 변경 없이 결과만 확인합니다.

### 3. 인덱스 정합성 보정

```powershell
python scripts/repair_problem_index.py [--dry-run]
python scripts/repair_problem_index.py --prune-candidate-overlaps [--dry-run]
```

- 과거 `file`/`answer_source` 경로를 현재 워크스페이스 기준으로 재매핑합니다.
- `.agent/state/problem_index_unresolved.json`에 미해결 경로와 후보 경로를 기록합니다.
- `--prune-candidate-overlaps`는 이미 같은 토픽의 `dt`에 존재하는 레거시 `case`만 제거합니다.

### 4. 교재 내 문제 후보 스캔

```powershell
python scripts/scan_textbook_embedded_problems.py [--subject 민법]
```

- 교재 추출물에서 문제 후보를 모아 `.agent/state/textbook_problem_candidates.json`을 생성합니다.
- 스캔 로그는 `.agent/state/textbook_problem_scan_log.json`에 기록합니다.

### 5. 교재 문제 후보 등록

```powershell
python scripts/register_textbook_problem_candidates.py [--subject 민법] [--apply]
```

- 기본은 dry-run이며 `--apply`를 줘야 `problem_index.json`에 반영합니다.
- 등록 로그는 `.agent/state/textbook_problem_register_log.json`에 남깁니다.

### 6. 개별 DT PDF 추출

```powershell
python scripts/extract_problems.py <pdf_path> [--dry-run] [--update-index]
```

- 단일 DT PDF에서 문제/정답을 추출해 JSON으로 확인하거나 바로 인덱스에 반영할 수 있습니다.
- 대량 재처리용 기본 명령은 아니고, 개별 PDF 보정이나 점검이 필요할 때만 사용합니다.

## 내부 유지보수

```powershell
python scripts/migrate_index_v2.py --dry-run
python scripts/reindex_minsa_dt.py --dry-run
```

- `migrate_index_v2.py`는 `problem_index.json`이 v1.0일 때만 쓰는 일회성 마이그레이션 도구입니다.
- 현재 워크스페이스 인덱스 버전은 이미 `2.0`이므로 상시 명령으로 취급하지 않습니다.
- `reindex_minsa_dt.py`는 민법 DT 벌크 재인덱싱용 로컬 유지보수 스크립트입니다.

### 7. 쟁점 빈도 추출

```powershell
python scripts/extract_issues.py [--subject 민법] [--top 15] [--dry-run]
```

- 전체 `problem_index.json`의 `question_text`를 스캔하여 쟁점별 출현 빈도를 집계합니다.
- 결과를 `.agent/state/issue_frequency.json`에 저장합니다.
- `--dry-run`은 저장 없이 콘솔에만 출력합니다.
- 과목별 패턴(민법/형법/헌법)이 분리되어 교차 오염이 없습니다.
- study-notes, law-note-supplement 등 다른 스킬이 이 파일을 참조하여 쟁점 중심 노트 구조를 생성합니다.

## 상태 파일

| 파일 | 위치 |
|------|------|
| 문제 인덱스 | `.agent/state/problem_index.json` |
| 미해결 경로 목록 | `.agent/state/problem_index_unresolved.json` |
| 교재 문제 후보 | `.agent/state/textbook_problem_candidates.json` |
| 교재 문제 스캔 로그 | `.agent/state/textbook_problem_scan_log.json` |
| 교재 문제 등록 로그 | `.agent/state/textbook_problem_register_log.json` |
| 쟁점 빈도 인덱스 | `.agent/state/issue_frequency.json` |

## 데이터 메모

- `problems.dt`는 객체 배열(v2.0) 기준으로 유지합니다.
- DT에서 `verified: true`를 쓰려면 `answer`와 `answer_source`가 함께 있어야 합니다.
- `repair_problem_index.py`는 경로 정리와 중복 정리용이며, 없는 스크립트를 대신 호출하지 않습니다.
