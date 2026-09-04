---
description: 사례답안 채점, 범위 기출/교재 자료 수집, 약점 분석을 현재 소크라틱/RAG 체계와 연결하는 워크플로우
---

# 사례답안 채점 통합 워크플로우

> 목표: 교재 전체 인식 -> 관련 쟁점 파악 -> 사례답안 초벌 채점 -> 모범답안/해설지/교재 일치 검토 -> 객관식 O/X 드릴화 -> 약점 분석 -> 소크라틱 후속 학습

---

## 1. 확인된 사실

1. 현재 문제 인덱스에는 과목별 `textbook_files`, `topics`, `problems.dt`, `problems.case`가 저장되어 있다.
   - 근거 발췌: `"textbook_files"`, `"topics"`, `"problems"`
   - 근거 위치: `《.agent/state/problem_index.json》 subject schema`
   - 근거 발췌: `"해당 회차에 대응하는 쟁점의 문제 목록 출력"`
   - 근거 위치: `《.agent/skills/problem-index/SKILL.md》 "1. 진도 기반 문제 조회"`

2. 현재 채점 규칙은 필수 요건/키워드 누락 시 부분정답 또는 오답으로 처리하는 엄격 채점 구조다.
   - 근거 발췌: `"필수 요건/키워드가 누락되면 '부분 정답' 또는 '오답'"`
   - 근거 위치: `《.agent/skills/socratic-core/docs/grading.md》 "채점표 (Strict Grading)"`
   - 근거 발췌: `"3가지 요건 중 2가지만 말함 -> 부분 정답 (△)"`
   - 근거 위치: `《.agent/skills/socratic-core/docs/grading.md》 "Completeness Check"`

3. 현재 약점은 `.agent/state/learning.json`의 `weak_points`에 저장된다.
   - 근거 발췌: `"저장: .agent/state/learning.json -> weak_points"`
   - 근거 위치: `《.agent/skills/socratic-core/docs/grading.md》 "약점 저장/재출제"`
   - 근거 발췌: `"weak_points"`
   - 근거 위치: `《.agent/state/learning.json》 top-level field`

4. 현재 RAG는 qmd 컬렉션(law-notes)으로 정리노트·교재원문 통합 검색을 수행하며, 교재 원문 청크는 `sync/_교재원문/` 하위 파일로 저장돼 있다 (2026-04-10 LanceDB → qmd 전환).
   - 근거 위치: `《.agent/lib/qmd_search.py》` · `《sync/_교재원문/》` · `《.mcp.json》 qmd 설정`

---

## 2. 운영 판단

사용자 요구는 계약 검토가 아니라 학습용 사례답안 채점이다. 따라서 중심축은 아래와 같이 잡는다.

1. `problem_index.json`
   - 해당 범위 문제 찾기
   - 기출/자료 문제 연결

2. `alignment.json` + `curriculum.json`
   - 교재 페이지 범위 연결

3. `learning.json`
   - 기존 약점과 중첩 분석

4. `qmd_search` helper (law-notes)
   - 관련 설명 청크와 인용 페이지 확보 (정리노트 + sync/_교재원문/ 통합)

---

## 3. 권장 파이프라인

```text
[답안 + 질문지 + 모범답안 + 해설지]
          |
          v
[case-answer-review]
          |
          +--> problem_index.json -> 관련 쟁점/기출/사례/선택형
          +--> case_material_index.json -> 질문지/해설지/채점평 묶음
          +--> problem_index.json -> 관련 기출/사례/선택형
          +--> alignment.json -> 교재 페이지
          +--> learning.json -> 기존 약점
          +--> qmd_search (law-notes) -> 설명 청크 (정리노트 + 교재원문)
          |
          v
[case_answer_packet.json]
          |
          +--> 관련 쟁점 파악
          +--> 초벌 채점
          +--> 모답/해설/교재 일치 검토
          +--> 객관식 O/X 변환
          +--> 대비자료
          +--> 약점 후보
          |
          v
[소크라틱 후속 문답 / 복습]
```

---

## 4. 출력에 반드시 포함할 요소

1. 인식된 교재/자료 코퍼스
2. 관련 쟁점
3. 해당 범위 기출 문제와 자료 문제
4. 관련 조문
5. 관련 판례
6. 설명용 RAG 청크
7. 기존 약점과 신규 약점 후보
8. 모범답안/해설지/교재 일치 검토
9. 객관식 O/X 변환 결과
10. 추가 필요사항 조사

---

## 5. 현재 구현 경로

```powershell
python .agent/skills/case-answer-review/scripts/render_case_answer_review.py --subject 민법 --topic 행위능력 --text "답안 본문" --output "H:\내 드라이브\tmp\case_answer_review.md"
```

```powershell
python .agent/skills/case-answer-review/scripts/render_case_answer_review.py --subject 민법 --topic 행위능력 --text "답안 본문" --question-text "사례문" --model-answer-text "모범답안" --explanation-text "해설지" --output "H:\내 드라이브\tmp\case_answer_review.md"
```

산출물:

- `H:\내 드라이브\tmp\case_answer_review.md`
- `H:\내 드라이브\.agent\state\case_answer_packet.json`

---

## 6. 현재 추가된 검토 단계

1. 질문지/모범답안/해설지 입력을 받아 `답안 vs 모답 vs 해설 vs 교재RAG`를 함께 본다.
2. 직접 O/X 문제는 즉시 드릴화하고, 숫자선지는 `choices` 저장 여부에 따라 선지별 O/X로 변환한다.
3. `problem_index + alignment`로 관련 쟁점을 먼저 추려서 교재 범위를 넓게 본다.
4. `case_material_index.json`으로 lecture 기준 사례형 묶음을 자동 매칭한다.
5. 보고서에 코퍼스 한계와 정밀 채점 보류 사유를 함께 적어 둔다.

---

## 7. 진행로그

1. DT 재인덱싱 로그: `.agent/state/dt_reindex_log.json`
2. 사례형 묶음 인덱스: `.agent/state/case_material_index.json`
3. 사례형 묶음 로그: `.agent/state/case_material_index_log.json`

---

## 8. 남은 확장 포인트

1. 배점표 기반 O/△/X를 issue 단위로 세분화
2. `weak_points` 자동 반영 옵션 추가
3. `srs_log.json` 자동 등록 옵션 추가
4. 기존 선택형 PDF를 재인덱싱해 `question_text`와 `choices`를 채우기
