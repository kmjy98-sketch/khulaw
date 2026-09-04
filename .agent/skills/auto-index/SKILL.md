---
name: auto-index
description: 태그 인덱스 자동 업데이트. 조문/판례/키워드 추출 및 tag_index.json 관리. "인덱스 업데이트", "태그 추출", "인덱싱" 요청 시 사용.
---

# Auto-Index Skill

<!-- @rule: CLAUDE.md#15 State Check -->

> 마크다운 파일에서 조문/판례/키워드를 자동 추출하여 `tag_index.json` 업데이트

---

## Quick Start

```powershell
# 단일 파일 인덱싱
python .agent/skills/auto-index/scripts/update_index.py <markdown_file>

# 폴더 전체 인덱싱
python .agent/skills/auto-index/scripts/update_index.py --dir <folder_path>
```

---

## 주요 기능

### 1. 자동 태그 추출

파일에서 다음 패턴을 자동 추출:

| 유형 | 패턴 | 예시 |
|------|------|------|
| **조문** | `제XXX조` | 제126조, 제748조 |
| **판례** | `대법원 YYYY.M.D` / `XX다XXXX` | 대법원 97.5.23, 2018다40231 |
| **키워드** | `**볼드**` 법률용어 | **표현대리**, **현존이익** |
| **헤더 쟁점** | `## N. 제목` | 부재자관재인, 실종선고 |

### 2. 인덱스 업데이트

```powershell
# 단일 파일
python scripts/update_index.py "part12.md"

# 폴더 전체
python scripts/update_index.py --dir "전사문/"

# 미리보기 (실제 저장 안함)
python scripts/update_index.py "part12.md" --dry-run
```

### 3. 인덱스 조회

```powershell
# 특정 조문 검색
python scripts/query_index.py --article "126조"

# 특정 키워드 검색
python scripts/query_index.py --keyword "표현대리"

# 특정 파트 내용 조회
python scripts/query_index.py --source "part12"
```

---

## 인덱스 구조

```json
{
  "version": "2.0",
  "last_updated": "YYYY-MM-DD",
  "sources": {
    "part12": {
      "articles": ["35조", "59조"],
      "keywords": ["법인", "대표권제한"],
      "cases": ["대법원 2007.5.17."]
    }
  },
  "articles": {
    "126조": ["part09", "part18"]
  },
  "keywords": {
    "표현대리": ["part09", "part24"]
  }
}
```

---

## 데이터 파일

| 파일 | 위치 |
|------|------|
| 인덱스 | `.agent/state/tag_index.json` |

---

## 워크플로우 연계

- `/transcribe` 교정 완료 시 → 자동 호출
- `/lecture-notes` 정리 완료 시 → 자동 호출
- `task.md`에 [x] 완료 체크 시 → 트리거

**트리거 명령:**

```powershell
python .agent/skills/auto-index/scripts/update_index.py <완료된 파일>
```

---

## 4. 링크 작성 표준 (Link Standards)

> **원칙**: 노트 간 연결성을 극대화하여 지식 그래프 구축. 유지보수 및 일괄 수정을 위해 아래 규칙을 준수합니다.

### 작성 규칙

| 유형 | 형식 | 설명 |
|------|------|------|
| **핵심 개념** | `[[개념명]]` | 주요 법적 개념은 위키 링크로 연결 (파일명 = 개념명) |
| **조문 링크** | `[[민법 제XXX조]]` | 조문은 가능한 전체 명칭 사용 |
| **강의 참조** | `[[partXX]]` | 해당 전사문 파일로 연결 |
| **강의 시점** | `[00:00:00]` | 전사문 내 해당 시점 (Timestamp) |

---

## 5. 노트 위키화 (Wiki-fying)

> **목적**: 작성된 노트의 텍스트를 분석하여 자동으로 링크를 생성하고 태그를 보강합니다.

### 사용법

```powershell
python .agent/skills/auto-index/scripts/enrich_note.py <target_file>
```

### 작동 방식

1. **키워드 매칭**: `tag_index.json`에 등록된 키워드/조문/판례를 본문에서 검색
2. **링크 변환**:
   - 텍스트 "표현대리" → `[[표현대리]]` (이미 링크된 경우 스킵)
   - 조문/판례 패턴 감지 및 링크화
3. **메타데이터 보강**:
   - `tags: [...]` 필드에 감지된 키워드 자동 추가
   - 하단 `## Related Notes` 섹션에 연관 노트 목록 추가 (선택적)

### 활용 시점

- `/lecture-notes` 정리 직후
- 기존 노트의 일괄 업데이트 시

---

## 6. 각주 감사 (Footnote Audit)

> 볼트 내 모든 노트의 각주 무결성을 검사한다.

### 사용법

```powershell
python .agent/skills/auto-index/scripts/audit_footnotes.py
```

### 기능

1. **고아 참조 탐지**: 인라인 `[^id]` 참조가 있으나 대응 정의(`[^id]: ...`)가 없는 경우
2. **고아 정의 탐지**: 정의는 있으나 본문에서 참조하지 않는 경우
3. **정의 후보 제안**: 고아 참조 인접의 `<!-- 📖 교재별 페이지 -->` 마커에서 교재명+페이지 추출
4. 출력: `.agent/state/footnote_audit.json`

### 출력 형식

```json
{
  "orphan_refs": [{"file": "민법3_..._정리노트.md", "line": 45, "ref_id": "민3-18", "suggested_def": "《전경운_민법》 p.153"}],
  "orphan_defs": [{"file": "...", "line": 200, "def_id": "형1-old"}],
  "summary": {"total_refs": 61, "total_defs": 3, "orphan_refs": 58, "orphan_defs": 0}
}
```

---

## 7. 백링크 제안 (Backlink Suggestions)

> 과목 내 노트 간 교차참조 가능한 쟁점을 탐지하고 백링크를 제안한다.

### 사용법

```powershell
python .agent/skills/auto-index/scripts/suggest_backlinks.py
```

### 기능

1. 양 볼트(`_4과목_도표추가본_통합본_모음/`, `_기말_도표추가본_통합본_모음/`)의 `.md` 파일 스캔
2. `##` 헤딩, 조문(`§`, `제X조`), 판례번호(`대판`, `XX다XXXX`) 추출
3. **과목 내** 교차참조 맵 생성 (민법끼리, 형법끼리, 헌법끼리)
4. 중간↔기말 연결 우선
5. 출력: `.agent/state/backlink_suggestions.json`

### 출력 형식

```json
{
  "suggestions": [
    {"source_file": "민법1_..._중간.md", "source_section": "§7-2 표현대리", "target_file": "민법1_..._기말.md", "target_section": "표현대리", "reason": "§126 공유", "priority": "high"}
  ],
  "broken_links": [
    {"file": "...", "line": 47, "link": "[[민법3#물권변동]]", "issue": "target heading not found"}
  ]
}
```

