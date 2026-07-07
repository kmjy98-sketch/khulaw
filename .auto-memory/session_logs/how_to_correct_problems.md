# 판례 문제 오류 교정 절차서

> 작성: 2026-05-23  
> 적용 대상: `precedent_problems_ox_*.json` / `precedent_problems_blank_*.json`  
> 관련 스크립트: `.agent/scripts/_gen_precedent_ox.py`, `_gen_precedent_blank.py`

---

## 개요

각 문제 데이터에는 `references` 필드가 포함되어 있습니다.  
이 필드를 이용해 오류의 원천 파일까지 역추적하고, 수정 후 문제를 재빌드합니다.

```json
"references": {
  "case_stub_link": "[[2000다22850]]",
  "sources": [
    {
      "book_name": "계약해제_근저당권실행_김준호_민법강의",
      "context_path": "민법/강혜림_민법1/계약해제_근저당권실행_김준호_민법강의.md",
      "page": "p.61"
    }
  ]
}
```

---

## Step 1: 오류 문제 식별

JSON 파일에서 오류 문항의 `id`를 기록합니다.

```
id: "prec-ox-2000다22850-2"
```

---

## Step 2: 판례 스텁 파일 열기

`references.case_stub_link` 값의 `[[사건번호]]` 위키링크를 사용합니다.

- **Obsidian**: `[[2000다22850]]` 링크를 클릭하거나 Quick Switcher로 검색
- **직접 경로**:
  ```
  sync/_백업/교재원문_문서_백업_2026-05-22/_판례색인/민법/2000다22850.md
  ```
- **과목 판별**: `분야` 필드 (`civil` → 민법, `criminal` → 형법, `constitutional` → 헌법)

스텁 파일에서 확인할 사항:
- `판시사항` 블록: OX 문제의 원문 (`문제_원문` 필드와 대조)
- `판결요지` / `결정요지` 블록: 블랭크 문제의 원문 (`원문` 필드와 대조)
- 선고일·사건번호·법원 정보 (Frontmatter)

---

## Step 3: 원천 교재 파일 확인 (선택)

스텁의 판시사항·판결요지만으로 오류 원인이 불분명하면 교재 원문을 확인합니다.

`references.sources` 목록의 각 항목에서:

| 필드 | 의미 |
|------|------|
| `context_path` | 교재 원문 청크 파일 (상대 경로) |
| `page` | 해당 판례가 등장하는 추정 페이지 (있는 경우) |

**파일 전체 경로**:
```
sync/_백업/교재원문_문서_백업_2026-05-22/_교재원문/{context_path}
```

예시:
```
sync/_백업/교재원문_문서_백업_2026-05-22/_교재원문/민법/강혜림_민법1/계약해제_근저당권실행_김준호_민법강의.md
```

파일 내에서 판례번호 (`2000다22850`)로 검색하면 관련 본문을 찾을 수 있습니다.  
`page` 정보가 있으면 frontmatter의 `포함_페이지` 범위와 대조해 물리적 교재 페이지를 확인합니다.

---

## Step 4: 오류 수정

오류 유형에 따라 수정 위치가 다릅니다.

### A. 판례 스텁의 내용 오류 (판시사항·판결요지 잘못 기재)

1. 스텁 파일을 직접 수정합니다.
2. `korean-law-mcp`로 원문 재확인:
   ```
   /korean-law-mcp → search_precedent_tool "2000다22850"
   ```
3. 수정 후 저장

### B. 판례 스텁의 Frontmatter 오류 (사건번호·선고일 오기)

1. `korean-law-mcp`로 정확한 메타데이터 확인
2. Frontmatter (`사건번호`, `선고일`, `사건명`) 수정

### C. 교재 원문 파일의 OCR 오류

1. 원본 PDF를 찾아 해당 페이지(`page` 정보 활용) 확인
2. `sync/_백업/교재원문_문서_백업_2026-05-22/_교재원문/{context_path}` 파일 수정
3. OCR 교정 원칙 적용: 원본을 HTML 주석으로 보존
   ```markdown
   <!-- original: 오류 원문 -->
   수정된 본문
   ```

---

## Step 5: 문제 재빌드

수정된 스텁 파일 기준으로 JSON을 재생성합니다.

```bash
cd "H:/내 드라이브"
python3 .agent/scripts/_gen_precedent_ox.py
python3 .agent/scripts/_gen_precedent_blank.py
```

출력 파일:
- `.agent/state/precedent_problems_ox_2026-04-18.json`
- `.agent/state/precedent_problems_blank_2026-04-18.json`

---

## Step 6: 재빌드 결과 검증

```python
import json
with open('.agent/state/precedent_problems_ox_2026-04-18.json', encoding='utf-8') as f:
    data = json.load(f)

# 수정된 문항 확인
target_id = 'prec-ox-2000다22850-2'
item = next((p for p in data['problems'] if p['id'] == target_id), None)
print(item['문제'], item['정답'])
```

---

## 빠른 참조: 파일·경로 요약

| 항목 | 경로 |
|------|------|
| 판례 스텁 (민법) | `sync/_백업/.../판례색인/민법/{사건번호}.md` |
| 판례 스텁 (형법) | `sync/_백업/.../판례색인/형법/{사건번호}.md` |
| 판례 스텁 (헌법) | `sync/_백업/.../판례색인/헌법/{사건번호}.md` |
| 교재 원문 청크 | `sync/_백업/.../_교재원문/{context_path}` |
| OX 문제 JSON | `.agent/state/precedent_problems_ox_2026-04-18.json` |
| 블랭크 문제 JSON | `.agent/state/precedent_problems_blank_2026-04-18.json` |
| 판례 종합 표 | `.auto-memory/wiki/판례종합표_{민사|형사|헌법}.md` |
| 빈도 데이터 | `.agent/state/references_all_2026-04-18_v2.json` |

---

## 주의사항

- 교재 파일 수정 시 **원본 삭제 금지** — `_trash/YYYY-MM-DD/`로 이동 또는 HTML 주석 보존
- `page` 정보는 추정값입니다. 판례번호 주변 200자 범위에서 정규식으로 탐색한 결과이므로, 실제 물리적 페이지와 다를 수 있습니다.
- 스텁 파일 수정 후 반드시 `_gen_precedent_ox.py` / `_gen_precedent_blank.py`를 재실행해야 JSON에 반영됩니다.
