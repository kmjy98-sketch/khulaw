---
name: study-notes
description: "교재·기출문제 기반으로 주요 내용 노트(핵심정리/개념정리/수업정리)를 자동 생성하는 스킬 (보조 소스: 기존 전사문 코퍼스 — 전사 생성 STT는 #45-C/P2에서 은퇴, 코퍼스는 보존)"
---

## 산출 frontmatter 계약 (issue_id 역색인 · #45-C C5, 2026-06-22)
생성 노트 상단 frontmatter에 포함: `issue_id`(.agent/state/issue_frequency.json 슬러그 기준, 불명확 시 생략), `과목`, `source_anchor`(교재·페이지·사건번호 등 근거 위치). 교재↔노트↔카드↔위키 교차참조의 1순위 키. 미상이면 채우지 말고 비운다(#2). ※ 전면 적용은 1책 1세트 파일럿 후.

# `study-notes` 스킬 지침

이 스킬은 사용자가 "노트 정리", "핵심정리", "수업정리", "개념정리", "요약해줘" 등을 요청할 때 트리거됩니다. 전사문·교재·기출문제를 RAG로 교차 참조하여 구조화된 학습 노트를 자동 생성합니다.

## 시스템 자원

- **scripts/collect.py**: 입력 파일 주변의 문서 및 교차 참조를 위한 Source Context를 수집
- **scripts/generate.py**: 수집된 Context를 바탕으로 LLM을 호출하여 노트를 생성
- **templates/**: 노트 생성을 위한 마크다운 템플릿 (`concept.md`, `case.md`, `exam.md`)

## 실행 프로세스

1. **사용자 요청 파악 (모드 결정)**
   - **개념정리/수업정리**: 전사문 또는 교재를 기반으로 개념 중심의 노트를 작성합니다. (`concept.md` 템플릿 사용)
   - **사례정리/모의답안정리**: 기출문제, 모의답안, 사례형 문제의 논점을 정리합니다. (`case.md` 템플릿 사용)
   - **기출핵심/출제포인트**: 기출문제의 선택형 지문, 관련 판례를 정리합니다. (`exam.md` 템플릿 사용)

2. **소스 수집 (collect.py 실행)**
   사용자가 현재 보고 있는 파일이나 언급한 문서를 대상으로 Python 스크립트를 실행합니다.

   ```bash
   python "h:\내 드라이브\.agent\skills\study-notes\scripts\collect.py" --target "{목표 파일 경로}" --mode "{모드}"
   ```

   *이 스크립트는 필요시 qmd law-notes 검색(`.agent/lib/qmd_search.py`)을 활용하여, 전사문의 경우 연관 교재 내용을, 교재의 경우 연관 전사문/기출문제를 교차 수집합니다.* 수집된 컨텍스트는 `.agent/state/study-notes-context.json`에 저장됩니다.

3. **노트 생성 (generate.py 실행)**
   수집된 컨텍스트를 바탕으로 템플릿 양식에 맞는 최종 마크다운 노트를 생성합니다.

   ```bash
   python "h:\내 드라이브\.agent\skills\study-notes\scripts\generate.py" --mode "{모드}" --out "{저장할 폴더의 경로/파일명.md}"
   ```

4. **사용자 검토 요청 (notify_user)**
   생성된 마크다운 노트 파일(`{저장할 폴더의 경로/파일명.md}`)의 경로를 `PathsToReview`로 전달하며, 작업 완료를 알립니다.

## 법령 자동검증 (law_api.py)

노트 생성 중 다음 상황이면 `.agent/lib/law_api.py`(법제처 직접 API)를 **자동 호출**한다:

1. **조문 원문 삽입**: 교재/전사문에서 조문 번호(민법 제○조 등)가 언급되었으나 원문이 없으면 `law_api.py law-detail`로 원문 조회 → 요건 블록에 삽입
2. **판례 요지 보강**: 판례명/사건번호가 등장하되 판결요지가 없으면 `law_api.py search-prec` → `prec-detail`로 판결요지 한 줄 확인
3. **qmd 우선**: law-notes 검색 결과에 이미 조문 원문/판결요지가 포함되어 있으면 중복 조회하지 않는다

인용 형식: `[《국가법령정보센터》 제○조 | "조문 원문"]`

## 챕터별 페이지 마커 삽입

노트 생성 시 모든 `##` 수준 섹션에 **페이지 마커 주석**을 자동 삽입한다.

1. `sync/_교재원문/` 챕터 파일의 frontmatter(`교재`·`챕터번호`·`페이지`)와 qmd 검색 결과 활용
2. 형식: `<!-- 📖 교재별 페이지\n  - 송영곤_논점민법_본책 ch.01 p.13-42 → [[송영곤_논점민법_본책_ch01_p013-042]]\n  - ... -->`
3. `##` 헤딩 바로 아래에 HTML 주석으로 삽입
4. 상세 규칙: `law-note-supplement/references/note-structures.md`의 "챕터별 페이지 마커 규칙" 참조

## 각주 형식 적용

노트 생성 시 `근거 위치`를 `[^id]` 각주로 분리한다.

1. **인라인**: `근거 발췌: "……"[^민1-XX]`
2. **각주 정의**: 해당 `##` 섹션 말미에 `[^민1-XX]: 《교재명》 p.XX` 배치
3. ID 네이밍: `[^{과목약칭}-{섹션번호}]` (예: `[^민1-3-1]`, `[^형1-r5]`)
4. 상세 규칙: `law-note-supplement/references/note-structures.md`의 "각주(Footnote) 규칙" 참조

## 백링크 삽입

같은 과목 내 기존 노트가 있으면 관련 쟁점 간 `[[파일명#섹션명]]` 백링크를 삽입한다.

1. **과목 내 한정**: 과목 간 교차 링크 금지
2. **`> 관련:` 블록** 또는 자연스러운 인라인 배치
3. `##` 섹션당 최대 3개
4. 상세 규칙: `law-note-supplement/references/note-structures.md`의 "백링크(Backlink) 규칙" 참조

---

## law-note-supplement 연계

`study-notes`로 **새 노트를 생성**한 후, 보완·검토·재구조화가 필요하면 `law-note-supplement` 스킬로 전환한다.

흐름: `study-notes`(신규 생성) → `law-note-supplement`(augment/review/restructure)

---

## 파일 저장 위치 원칙

생성된 노트는 자동 분류 규칙(`classification-rules_v2.md`)에 따라 저장되어야 합니다.

- 주 강사 진행중: `{과목}/{강사명}/정리/`
- 기타 강사/내신: `{과목}/보관/{강사명}/정리/`
- 공통 개념 단권화: `{과목}/개념/`
