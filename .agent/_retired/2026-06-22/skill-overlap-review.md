# Skill Overlap Review

> **갱신 (2026-04-10)**: LanceDB → qmd 이전 반영 완료. 아래 본문의 `lancedb-rag` 언급은 현재 qmd `law-notes` 컬렉션(helper `.agent/lib/qmd_search.py`)으로 통합됨.

기준 소스:
- `H:\내 드라이브\.agent\workflows\socratic.md`
- `H:\내 드라이브\.agent\skills\socratic-loader\SKILL.md`
- `H:\내 드라이브\.agent\skills\socratic-core\SKILL.md`
- `H:\내 드라이브\.agent\skills\pdf-ingest\SKILL.md`
- `H:\내 드라이브\.agent\skills\problem-index\SKILL.md`
- `H:\내 드라이브\.agent\skills\textbook-problem-intake\SKILL.md`
- `H:\내 드라이브\.agent\skills\case-answer-review\SKILL.md`

## 1. `socratic-loader` vs `socratic-core`

### `socratic-loader`

- 역할: 세션 시작 전 상태 확인, 자료 로드, qmd RAG 검색, 세션 시작 출력
- 근거 발췌: `"socratic-loader [MUST FIRST] ... 상태 파일 확인 ... qmd RAG 검색 (law-notes) ... 전사문 → 교재 페이지 추출 ... 세션 시작 출력"`
- 근거 위치: `《.agent/workflows/socratic.md》 "스킬 호출 순서"`
- 근거 발췌: `"Phase 0: 세션 초기화"` / `"progress.json"`, `"learning.json"`, `"SRS 복습 조회"`, `"problem_index.json -> 관련 문제 검색"`
- 근거 위치: `《.agent/skills/socratic-loader/SKILL.md》 "Phase 0"`, `"Step 0-1"`, `"Step 0-3"`

### `socratic-core`

- 역할: 실제 문답, 문제 생성, 채점, 상태 갱신
- 근거 발췌: `"socratic-core ... 대화 모드: 분석지도 + 질문 / 생성 모드: 문제 생성 / 채점 모드: 채점표 + SRS / Problem Drill: 문제 풀이"`
- 근거 위치: `《.agent/workflows/socratic.md》 "스킬 호출 순서"`
- 근거 발췌: `"실제 학습 로직 실행 (대화, 문제 생성, 채점)"` / `"learning.json" - 취약점`, `"progress.json" - 교재/전사문 진도`, `"srs_log.json" - 복습 간격`
- 근거 위치: `《.agent/skills/socratic-core/SKILL.md》 본문, "자동 상태 커밋"`

정리:
- `loader`는 세션 부팅기다.
- `core`는 학습 엔진이다.
- 현행 분리는 유지하는 편이 맞다. 문서상 `MUST FIRST` 순서가 이미 명시되어 있어 역할 충돌보다 순서 통제가 핵심이다.

## 2. 현재 중복 기능과 효율화 판단

### A. `socratic-loader`와 `pdf-ingest`

- 중복 지점: 둘 다 교재 PDF 텍스트를 다룬다.
- 근거 발췌: `"교재 PDF 텍스트 추출 + 캐싱"`
- 근거 위치: `《.agent/skills/socratic-loader/SKILL.md》 "2. 교재 PDF 텍스트 추출 + 캐싱"`
- 근거 발췌: `"PDF → 마크다운 청크 추출 전용. 인덱싱은 sync/_교재원문/ 하위에 파일 배치 후 qmd update && qmd embed가 자동 처리한다."`
- 근거 위치: `《.agent/skills/pdf-ingest/SKILL.md》 본문 (2026-04-10 LanceDB 제거 이후)`

판단:
- 기능이 겹치지만 목적이 다르다.
- `socratic-loader`는 현재 세션 범위만 빠르게 가져오는 단건 추출이다.
- `pdf-ingest`는 전체 코퍼스 추출 전용(인덱싱은 qmd 자동 처리).
- 더 효율적인 방식은 둘을 합치는 게 아니라, `신규 교재 투입 시 pdf-ingest → sync/_교재원문/ 배치 → qmd update/embed`, `세션 시작 시 socratic-loader`로 분리하는 것이다.

### B. `problem-index`와 `textbook-problem-intake`

- 중복 지점: 둘 다 교재 문제를 `problem_index.json`으로 연결한다.
- 근거 발췌: `"교재 내 문제 후보 스캔"` / `"problem_index.json > problems.textbook"`
- 근거 위치: `《.agent/skills/problem-index/SKILL.md》 "4. 교재 내 문제 후보 스캔", "5. 교재 문제 후보 등록 준비"`
- 근거 발췌: `"교재 extract에서 숨어 있는 문제를 찾아 ... problem_index.json > problems.textbook으로 올릴 수 있게 정리"`
- 근거 위치: `《.agent/skills/textbook-problem-intake/SKILL.md》 본문`

판단:
- `problem-index`는 등록소/조회기 역할이다.
- `textbook-problem-intake`는 교재 문제 intake wrapper다.
- 둘을 합치기보다는, `intake -> register -> query` 순으로 역할을 나누는 게 더 명확하다.

### C. `socratic-loader`와 `case-answer-review`

- 중복 지점: 둘 다 `progress.json`, `learning.json`, `problem_index.json`, qmd law-notes 검색 결과를 읽는다.
- 근거 발췌: `"progress.json"`, `"learning.json"`, `"problem_index.json -> 관련 문제 검색"`
- 근거 위치: `《.agent/skills/socratic-loader/SKILL.md》 "Step 0-1", "Step 0-3"`
- 근거 발췌: `"problem_index, alignment, weak_points, RAG 검색 결과를 묶어 사례형 답안의 초벌 평가와 후속 학습 자료를 만든다."`
- 근거 위치: `《.agent/skills/case-answer-review/SKILL.md》 frontmatter description`

판단:
- 읽는 소스는 겹치지만 출력이 다르다.
- `socratic-loader`는 세션 시작용.
- `case-answer-review`는 채점 보고서와 패킷 생성용.
- 이 둘은 병합보다 `packet` 인터페이스로 느슨하게 연결하는 쪽이 효율적이다.

### D. `law-note-supplement`와 `study-notes`

- 중복 지점: 둘 다 법학 노트를 다룬다.
- 근거 발췌: `"새 노트 생성이 아니라 기존 노트에 빠진 내용을 추가하거나 오류를 수정하거나 구조를 개선하는 용도"`
- 근거 위치: `《.agent/skills/law-note-supplement/SKILL.md》 Overview`
- 근거 발췌: `"전사문/교재/기출 기반 학습 노트 자동 생성·정리"`
- 근거 위치: `《.claude/skills/study-notes/SKILL.md》 description`

판단:
- `study-notes`는 소스에서 처음부터 노트를 생성한다.
- `law-note-supplement`는 기존 노트에 내용을 추가·수정·재구조화한다.
- 입력 상태가 다르다: `study-notes`는 소스 → 새 파일, `law-note-supplement`는 기존 파일 → 수정 파일.
- 병합 불가. CLAUDE.md §7 규칙 9에 분기 기준이 명시되어 있다. (2026-04-21 §7 재번호: 기존 7 → 9)

## 3. 현행 기준에서 추천하는 운영 규칙

1. 새 교재가 들어오면 `pdf-ingest`를 직접 치지 말고 `textbook-problem-intake` 파이프라인을 먼저 쓴다.
2. 소크라틱 세션은 항상 `socratic-loader -> socratic-core` 순서를 유지한다.
3. 사례답안 채점은 `case-answer-review`로 분리하고, 학습 세션에 바로 섞지 않는다.
4. `problem-index`는 조회와 최종 등록 상태 확인에 집중한다.

## 4. 이번 적용 사항

- `textbook-problem-intake/scripts/run_textbook_intake.py`를 추가해 `extract -> scan -> register dry-run/apply -> pipeline log`를 한 번에 실행하게 했다.
- `skill-structure.md`에 `Detailed Intake Flow`, `Detailed Socratic Flow`를 추가해 상태파일 기준 흐름을 분리해 표시했다.
