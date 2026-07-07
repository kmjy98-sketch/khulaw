# 변경요약 — spaced-repetition SKILL.md 보완 (2026-06-30)

## 대상 파일
`E:\법학볼트\.agent\skills\spaced-repetition\SKILL.md`

## 변경 내용

### 1. 약점 저장소 단일화 명시
- **기존**: "데이터 파일 = `.agent/state/srs_log.json`에 저장" (한 줄, srs_log.json 단독 기술)
- **변경**: `learning.json`이 약점 원천(단일 정본)임을 명시. `srs_log.json`은 리뷰 이벤트 로그(이력)이며 약점 원천이 아님을 분리 기술.
- **근거**: CLAUDE.md #20 "Weak Problem Storage: .agent/state/learning.json → weak_points 저장", `board_server_v2.py read_weak()`가 `learning.json`을 읽음.

### 2. `learning.json` 구조 설명 추가
- `weak_points` 배열 = 약점 원천. board_server_v2 진도보드 약점 패널이 이 값을 표시.
- `srs.items` 배열 = SM-2 간격 관리. `weak_points`에서 유래(`source: "weak_points"`).
- `srs_log.json` = 리뷰 이벤트 타임스탬프·점수 이력. 간격 계산 이력 기록, 약점 원천 아님.

### 3. 보드 약점 frontmatter 연동 섹션 신설
- 논점노트 frontmatter `약점: true/false` ↔ `learning.json weak_points` ↔ board_server_v2 닫힌루프 흐름 기술.
- `mark_progress.py --weak` / `--clear-weak` 플래그 사용법 명시(근거: mark_progress.py 실구현).
- CLAUDE.md #19-B "인터페이스 병존" (board_server_v2 HTML + 진도보드.base) 연동 기술.

### 4. 과목 풀네임 강제 (약칭 금지)
- `--add` 예시를 "민법" → "민사소송법" 으로 교체, 약칭 금지 주석 추가 (CLAUDE.md #51·#50-B 근거).

### 5. 룰 주석 갱신
- `<!-- @rule: CLAUDE.md#19 -->` → `<!-- @rule: CLAUDE.md#19-B·#20 -->` (정본 룰 반영).

## 보존 동작
- SM-2 알고리즘 설명 유지.
- 최신연구(SM-2·FSRS·deadline-aware, 2026-06-21) 절 유지.
- 답안 채점 연동 간격 표 유지.
- 기존 Quick Start / 주요 기능 / 점수 기준 유지.

## 이슈
- `srs_scheduler.py` 자체 코드는 아직 `srs_log.json`을 사용할 수 있음 — 스크립트 코드 확인 및 `learning.json` 경유 통합은 후속 과제.
- `--weak` / `--clear-weak` 시 `learning.json weak_points` 배열도 동기화되어야 닫힌루프가 완전해짐 — mark_progress.py 현재 구현은 frontmatter만 씀, learning.json 동기화 추가 검토 필요.
