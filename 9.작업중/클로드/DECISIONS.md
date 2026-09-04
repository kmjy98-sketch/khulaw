# Design Decisions

## 1. 구조 이식 방식

공유 보고서의 `law-study/` 새 루트 구조는 현재 워크스페이스와 중복되므로 생성하지 않는다. 보고서의 개념만 기존 `H:\내 드라이브` 운영 위치로 흡수한다.

## 2. AGENTS.md의 역할

루트 `AGENTS.md`는 이미 상세한 출처, 파일 작업, 노트 형식, 학습 운영 규칙을 포함한다. 따라서 보고서의 축약 `AGENTS.md`는 새로 만들지 않고, 본 결정 문서와 `.agent/workflows/law-study-automation.md`에서 보완한다.

## 3. SQLite 원장

진도, 약점, 복습 큐, 사례형 시도, Anki 후보 및 batch 상태는 `.agent/state/progress.sqlite`에 누적한다. 기존 `.agent/state/progress.json`, `learning.json`, `srs_log.json`은 바로 폐기하지 않고 병행 유지한다.

## 4. Anki의 역할

Anki는 진도관리 DB가 아니다. Anki는 전체 보관용 지식 저장소와 장기복습 엔진으로 쓰고, Codex가 batch CSV를 생성한 뒤 사용자가 Anki Desktop에서 import한다.

## 5. 카드 관리 원칙

카드 생명주기는 `draft -> pending -> batched -> exported`를 기본으로 한다. 반복 오답으로 기존 카드 보강이 필요하면 `updated` 상태를 사용한다. `rejected` 카드는 자동 batch 대상에서 제외한다.

## 6. 덱 구조

쟁점별 덱을 만들지 않는다. 덱은 과목/대분류 단위로 둔다.

예:

- `Law::공법::헌법_기본권`
- `Law::공법::행정법_행정쟁송`
- `Law::민사::민법_채권총론`
- `Law::형사::형법_총론`

세부 쟁점은 `issue_id`와 태그로 관리한다.

## 7. 사례형 전체 Anki화 금지

사례형 모범답안 전체를 Anki 카드로 만들지 않는다. 목차, 키워드, 판례문구, 반복오답, 포섭 체크포인트만 후보로 만든다.

## 8. AnkiWeb 직접 갱신 금지

Codex는 AnkiWeb에 직접 로그인하거나 덱을 직접 수정하지 않는다. CSV export와 import 완료 처리만 담당한다.

## 9. 실행 단계

이번 이식은 보고서의 MVP 1-4단계에 해당한다.

1. 문서, config, data 기본 스키마
2. SQLite 초기화
3. 일일 현황 및 Anki 업데이트 필요 고지
4. Anki batch 생성 및 import 완료 처리

답안 자동 채점 엔진은 기존 `.agent/workflows/case-answer-rag.md` 흐름과 충돌하지 않도록 별도 단계에서 확장한다.
