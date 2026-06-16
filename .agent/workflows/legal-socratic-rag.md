---
description: 리걸 리뷰 결과를 소크라틱 문답과 RAG 검색으로 연결하는 통합 워크플로우
---

# 리걸 리뷰 통합 워크플로우

> 계약/NDA 검토 결과를 현재 `legal-review`, `socratic`, `qmd` RAG 체계와 연결할 때의 운영 규칙 (2026-04-10 LanceDB → qmd 전환)

---

## 1. 확인된 사실

1. 현재 소크라틱 세션 로더는 `progress.json`, `learning.json`, `srs_log.json`을 먼저 확인하고 qmd law-notes 컬렉션 검색을 수행한다 (helper: `.agent/lib/qmd_search.py`).
   - 근거 위치: `《.agent/skills/socratic-loader/scripts/socratic_loader.py》 search_rag()`

2. 현재 소크라틱 코어는 최종 답변에서만 근거를 제공하고, 채점은 reverse-RAG를 전제로 한다.
   - 근거 발췌: `"최종 답변(정답 공개) 시에만: 근거 제공"`
   - 근거 위치: `《.agent/skills/socratic-core/SKILL.md》 "근거 제공 예외"`
   - 근거 발췌: `"Reverse-RAG 채점"`
   - 근거 위치: `《.agent/skills/socratic-core/SKILL.md》 "RAG 2.0 통합"`

3. 현재 RAG 스택은 qmd law-notes 컬렉션(정리노트 + `sync/_교재원문/` 통합)이며, `qmd_search()` helper는 BM25/벡터/리랭크 결과를 반환한다.
   - 근거 위치: `《.agent/lib/qmd_search.py》` · `《.mcp.json》 qmd 설정`

4. 현재 진도·커리큘럼 상태 파일은 민법 강의/교재 중심으로 채워져 있다.
   - 근거 발췌: `"(1-01)민법_송영곤_기본민강_권리주체(26).pdf"`
   - 근거 위치: `《.agent/state/progress.json》 current_scope.textbook`
   - 근거 발췌: `"primary_book": "기본민강_26"`
   - 근거 위치: `《.agent/state/curriculum.json》 primary_book`

5. `legal-review`는 계약/NDA를 플레이북 기준으로 검토하고, 근거 스니펫과 상태값을 마크다운 보고서로 만든다.
   - 근거 발췌: `"조항별 상태를 GREEN/YELLOW/RED로 정리"`
   - 근거 위치: `《.agent/skills/legal-review/SKILL.md》 description`
   - 근거 발췌: `"문서 내 근거 문구와 스니펫을 포함"`
   - 근거 위치: `《.agent/skills/legal-review/SKILL.md》 "핵심 원칙"`

6. `korean-law-mcp`는 국가법령정보센터 Open API를 통해 법령·판례·행정규칙 원문을 실시간 반환한다. qmd law-notes 정적 코퍼스를 보완하는 실시간 조회 레이어다.
   - 근거 발췌: `"국가법령정보센터 Open API를 활용한 고성능 MCP 서버"`
   - 근거 위치: `《.agent/skills/korean-law-mcp/SKILL.md》 description`
   - 근거 발췌: `"#5 Original-Text Priority 준수: 조문 원문은 이 도구 반환값을 우선 인용"`
   - 근거 위치: `《.agent/skills/korean-law-mcp/SKILL.md》 "운영 규칙"`

---

## 2. 통합 판단

직접 통합은 가능하지만, **현재 학습 상태 파일에 바로 합치는 방식은 비권장**이다.

이유:

- 현재 `progress.json`, `curriculum.json`, `alignment.json`은 민법 강의 진도와 개념 맵을 전제로 설계되어 있다.
- 계약 검토 조항(`Limitation of Liability`, `Indemnification`, `NDA Carveouts`)은 현재 `concept_ids` 체계와 직접 매핑되지 않는다.
- 따라서 법무 검토 세션을 같은 진도 파일에 쓰면 학습 추적과 계약 검토 추적이 서로 오염된다.

권장 구조는 `별도 legal packet/state`를 두고, **소크라틱 질문/후속 RAG 검색만 현재 체계에 연결**하는 방식이다.

---

## 3. 권장 아키텍처

```text
[contract / nda]
        |
        v
[legal-review/render_review.py]
        |
        v
[review markdown]
        |
        +--> 참조 조문/판례 식별
        |           |
        |           v
        |    [korean-law-mcp]  ← 실시간 조문 원문 / 판례 전문 (API 키 필요)
        |
        v
[build_socratic_packet.py]
        |
        +--> .agent/state/legal_socratic_packet.json
        |
        +--> retrieval_queries
                 |
                 v
         [qmd_search (law-notes)]  ← 정리노트 + sync/_교재원문/ 통합 검색
                 |
                 v
        [근거 청크 / 페이지]
                 |
                 v
       [socratic 질문 / 최종 근거 답변]
```

---

## 4. 운영 규칙

### 4-1. 소크라틱 연결

1. 먼저 `render_review.py`로 계약 검토 또는 NDA triage 보고서를 만든다.
2. 그 보고서를 `build_socratic_packet.py`로 변환한다.
3. 소크라틱 문답은 `legal_socratic_packet.json`의 `focus_clauses`, `questions`, `evidence`를 우선 소스로 쓴다.
4. 최종 정답 공개나 교정 단계에서만 근거를 붙인다. 이 규칙은 현재 `socratic-core`와 동일하다.

### 4-2. RAG 연결 (qmd law-notes — 정리노트 + 교재원문 통합)

1. 표준계약서, 과거 redline, DPA, NDA 샘플, 내부 정책을 PDF/Markdown으로 정리한다.
2. `pdf-ingest`로 마크다운 추출 후 `sync/_교재원문/` 또는 법무 전용 서브볼트에 저장한다.
3. `qmd update && qmd embed`로 law-notes 컬렉션을 갱신 → `qmd_search(clause명/trigger)` 로 검색한다.
4. 검색 결과는 `legal_socratic_packet.json`의 `retrieval_queries`를 기본 입력으로 쓴다.

### 4-3. 실시간 조문 조회 (korean-law-mcp — API 키 필요)

1. `legal-review` 보고서에서 참조 조문(민법 제○조, 근로기준법 제○조 등)이 식별된 경우 → `search_law_tool` 또는 `get_law_detail`로 원문 확인.
2. 판례 번호 또는 키워드가 식별된 경우 → `search_precedent_tool` / `get_precedent_detail`로 판결요지 확인.
3. qmd 청크에 조문 원문이 없거나 불완전한 경우 → `korean-law-mcp`로 보완. #5 Original-Text Priority 준수.
4. API 키 미설정 상태에서는 이 단계를 건너뛰고 qmd 검색만 사용한다.

### 4-4. 상태 파일 분리

다음 파일은 **법무 검토 세션과 분리 유지**한다.

- `.agent/state/progress.json`
- `.agent/state/learning.json`
- `.agent/state/curriculum.json`
- `.agent/state/alignment.json`

다음 파일은 **법무 검토용 별도 상태**로 사용한다.

- `.agent/state/legal_playbook.md`
- `.agent/state/legal_socratic_packet.json`

추가 확장 시 제안 파일:

- `.agent/state/legal_sessions.json`
- `.agent/state/legal_alignment.json`

---

## 5. 실행 순서

### 5-1. 계약 검토 -> 소크라틱

```powershell
python .agent/skills/legal-review/scripts/render_review.py "C:\path\contract.pdf" --mode contract-review --output "H:\내 드라이브\tmp\contract_review.md"
python .agent/skills/legal-review/scripts/build_socratic_packet.py "H:\내 드라이브\tmp\contract_review.md"
```

### 5-2. NDA triage -> 소크라틱

```powershell
python .agent/skills/legal-review/scripts/render_review.py "C:\path\nda.docx" --mode nda-triage --output "H:\내 드라이브\tmp\nda_triage.md"
python .agent/skills/legal-review/scripts/build_socratic_packet.py "H:\내 드라이브\tmp\nda_triage.md"
```

### 5-3. 후속 RAG 검색 (qmd law-notes)

```powershell
python -c "import sys; sys.path.insert(0, '.agent/lib'); from qmd_search import qmd_search; [print(h['title'], h['score'], h['path']) for h in qmd_search('Limitation of Liability unlimited liability', k=5)]"
python -c "import sys; sys.path.insert(0, '.agent/lib'); from qmd_search import qmd_search; [print(h['title'], h['score'], h['path']) for h in qmd_search('NDA Carveouts no carveouts', k=5)]"
```

### 5-4. 조문 원문 실시간 조회 (korean-law-mcp, API 키 설정 후)

MCP 도구로 직접 호출:
- `search_law_tool(query="민법 손해배상")` → 관련 법령 목록
- `get_law_detail(law_id="민법")` → 민법 전문
- `search_precedent_tool(query="불법행위 손해배상", court="대법원")` → 판례 목록
- `get_precedent_detail(precedent_id="...")` → 판결요지 + 판시사항 + 전문

---

## 6. 제안

1. **단기**: 현재 구조에서는 `legal-review -> packet -> socratic/RAG`의 느슨한 결합이 최선이다.
2. **중기**: 법무 문서용 별도 코퍼스와 alignment 파일을 만든다. `korean-law-mcp` API 키 발급 후 조문 조회 레이어 활성화.
3. **장기**: `socratic-loader`에 `legal_socratic_packet.json` 읽기 분기를 추가해, 학습 세션과 계약 검토 세션을 모드 수준에서 분리한다. `korean-law-mcp` 검색 결과를 packet의 `evidence` 필드에 자동 삽입하는 파이프라인 추가 검토.
