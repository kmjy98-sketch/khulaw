# build_session.py v2 변경 요약 (2026-06-30)

## 교체 내용

### 제거된 v1 의존성
| 제거 항목 | 이유 |
|---|---|
| `HTML` (진도_board.html) + `load_board()` | v1 보드 HTML 내장 JSON — #19-B 구 v1, 정본 아님 |
| `MASTER` (진도_소단원_master.csv) + 관련 매칭 함수 전체 | 소단원 마스터 — 폐기, frontmatter 대체 |
| `WIKI` (sync/위키/원문) | #50-B 폐기 경로 — 원문은 outputs/ |
| `HYUN` (진도_현황.json) | 구 v1 snapshot — 정본 아님 |
| `PROG` (progress.json) | 구 v1 — 정본 아님 |
| `find_export()` + `--export` 인수 | board export 파일 — v1 의존 전부 제거 |
| 소단원 매칭 로직 전체 (`_master_row_matches`, `_strip_lead`, `_core_norm`, `_board_tokens`, `_master_segments`, `BOARD_UNIT_ALIASES`, `_card_parse_index`, `unit_cards`, `title_unit_cards`) | master.csv 기반 — 불필요 |
| `wiki_unit()` (sync/위키/원문 기반) | 폐기 경로 |
| `csv` import | master.csv 불필요 |
| SRC 딕셔너리 (원문 폴더 매핑) | 원문 폴더 참조 폐기 |

### 새 데이터소스
- **`build_pool_from_wiki()`**: `sync/위키/{과목}/*.md` frontmatter 스캔
  - `type: 쟁점` 파일만 선택 (board_server_v2.build_board() 참조)
  - 키 = `과목|대분류|논점(파일명)` (#50-A 표준)
  - 추출 필드: 회독·선택·사례·약점·진도·대분류·원문·책

### 보존된 동작
- 2트랙 로직 (회독0=진도트랙 / 회독≥1=복습트랙) — 논점 단위로 그대로 유지
- 약점 주입 (learning.json weak_points)
- 방학목표 주입 (진도보드_목표.json)
- 드릴 로그 최근드릴 주입 (drill_log.jsonl)
- SRS due 연동
- 사례 인박스 스캔
- 사례 인덱스 조인 (case_for_unit)
- 카드 파일 매칭 (CARD_KEYWORDS + frontmatter 과목 폴백)
- 출력 파일: drill_session.json + 오늘_드릴.md

### 카드 매칭 변경
- v1: master.csv 출처책+페이지 범위 → 카드 glob
- v2: `원문` frontmatter 경로 → `outputs/02_cards_v37/{책}_p{범위}*_v37.md` glob (논점단위)
  - 실패 시 과목단위 폴백 유지

### 키 정본 통일
- 구: `과목|중분류|소단원` (v1 표기)
- 신: `과목|대분류|논점` (#50-A, board_server_v2 실구현 동일)
- 하위호환: `소단원` 필드에 논점 제목을 그대로 노출 (외부 리더용)
- `대상단원` 키 유지 (하위호환)

## dry 실행 결과 (2026-06-30)
```
세션 구성: 진도 3논점 · 복습 3논점 · 사례대기 0건 · 총논점 695
  [진도] 민법>물권·담보물권>가등기담보법에 의한 규율 (회독0 방학)
  [진도] 민법>민법총칙>강박에 의한 의사표시를 다투는 방법 (회독0 방학)
  [진도] 민법>채권법>경개 (회독0 방학)
  [복습] 민사소송법>소송종료·판결>당사자 기일해태의 효과 (회독1)
  [복습] 민사소송법>당사자·소송능력>당사자 확정 (회독1)
  [복습] 민사소송법>당사자·소송능력>당사자능력 (회독1)
```
오류 없음. drill_session.json + 오늘_드릴.md 정상 생성 확인.

## 이슈

1. **카드범위 "과목단위" 주 발생**: frontmatter `원문` 경로에서 책명을 파싱해 카드 glob 시도하나,
   `쟁점노트_재산법_llamaparse_p481-510.md` → `쟁점노트_재산법_llamaparse_p481-510` 패턴이
   02_cards_v37의 실제 파일명(`논점민법재산법_p001-030_기본서_v37.md`)과 책명이 달라 과목단위 폴백.
   → 근본 원인: 원문 파일명의 책코드(쟁점노트_재산법)와 카드 파일명의 책코드(논점민법재산법)가 불일치.
   → 해결책(별도 작업): 카드-원문 책명 매핑 테이블 추가 또는 카드 frontmatter에 `원문:` 역참조 추가.
   현재는 과목단위 폴백이 동작 중이므로 세션 구성 자체는 문제 없음.

2. **형사소송법·상법·선택법 위키 폴더 미존재**: 해당 과목 논점 0개 — 위키화 전이므로 정상.
