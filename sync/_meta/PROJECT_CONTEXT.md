# Project Context

## 목적

이 워크스페이스는 로스쿨 사례형 답안 훈련, Markdown 교재 정리, 진도관리, 약점 분석, 복습 큐, Anki 장기복습 카드풀을 통합하기 위한 개인 학습 시스템이다.

## 현재 적용 방식

공유 보고서의 새 `law-study/` 저장소 구조는 그대로 만들지 않는다. 현재 루트 `AGENTS.md`와 기존 `.agent/`, `sync/`, `outputs/anki/` 구조가 우선한다.

| 보고서 개념 | 현행 위치 |
|---|---|
| `CODEX_BOOTSTRAP_REPORT.md` | `sync/_meta/CODEX_BOOTSTRAP_REPORT.md` |
| `PROJECT_CONTEXT.md`, `DECISIONS.md` | `sync/_meta/` |
| `config/*.yml` | `.agent/config/` |
| `data/*.csv` | `.agent/data/` |
| `progress.sqlite` | `.agent/state/progress.sqlite` |
| daily dashboard Markdown | `.agent/state/law_study_*.md` |
| Anki batch CSV | `outputs/anki/law_study_batches/` |
| Anki imported archive | `outputs/anki/law_study_exported/` |

## 기본 방향

- Anki는 전체 보관용 지식 저장소이자 장기복습 도구로 사용한다.
- Codex는 진도, 약점, 단기복습, 사례형 답안 평가 결과 누적, Anki 카드 업데이트 판단을 담당한다.
- 사례형 답안 훈련의 중심은 Anki가 아니라 Codex 기반 평가와 오답 누적이다.
- Anki는 요건, 판례, 조문 구조, 목차, 반복오답, 핵심 키워드 암기에 사용한다.

## 과목 범위

- 공법: 헌법, 행정법
- 민사: 민법, 민소법, 상법
- 형사: 형법, 형소법

## 핵심 원칙

1. 외부 법학 지식 사용 금지.
2. 법학 판단은 사용자 제공 자료와 허용된 공적 API 소스 기준으로만 한다.
3. 자료에 없는 법리는 `자료 부족—보류`로 처리한다.
4. 감점 또는 카드 생성에는 `source_file`과 `source_location`을 남긴다.
5. Anki 카드는 전체 보관용으로 생성하되, 실제 batch export는 진도와 약점을 고려해 제한한다.
6. 세부 쟁점은 Anki 덱이 아니라 `issue_id`와 태그로 관리한다.
7. Anki 덱은 과목/대분류 단위로 유지한다.
