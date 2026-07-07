# Claude Code 첫 사용 가이드 (v3.6 Phase 1.2 — Claude Code 운영 모드)

## 0. 사전 준비

- Claude Code 설치 (https://docs.claude.com)
- **API key 불필요** — Claude Code 구독으로 처리
- 이 패키지 폴더 위치: `H:\내 드라이브\프롬프트 등 개선\claude_code_package_v2\`

## 1. 첫 명령 (한 번만)

Claude Code 열고 첫 메시지로:

```
SKILL.md 읽고 v3.6 Phase 1.2 Claude Code 운영 모드 파악해.
prompts/ 폴더 구조와 적용 방법 확인 후 시범 명령 가능 여부 알려줘.
```

Claude Code가 자동으로:
- SKILL.md 읽고 4단계 파이프라인·태그 2축·마크다운 충돌 회피 규칙 이해
- prompts/ 폴더에 12개 프롬프트 확인 (Claude 6 + Gemini legacy 6)
- inputs/ outputs/ 폴더 존재 확인
- 시범 명령 안내

## 2. 시범 운영 (첫 책 처리 전)

### 2.1 01번 단독
```
01번 OCR 단독 테스트.
inputs/raw_pdf/시범_50p.pdf 첨부했어. 
prompts/01_claude_마킹_구조_조문_추출_v3.6.md 적용해서 Mode B로 OCR 돌려.
결과 outputs/01_ocr/에 저장하고, 마킹·구조 인식 보고해줘.
```

검토 후:
- 결과 만족 → "다음 단계 02-wiki로 진행"
- 마킹·구조 인식 미흡 → "01번 prompts/01_claude_*.md 확인. 어떤 부분 누락됐는지"

### 2.2 02-wiki 단독 ⭐ v3.6 신규
```
01번 출력 첫 청크를 02-wiki로 위키화해줘.
book_type_hint: 단권화
prompts/02-wiki_claude_위키화_v3.6.xml 적용.
결과 outputs/02_wiki/에 저장하고, 책 유형 추정 신뢰도·속성 라벨 개수·
Obsidian callout 변환·{불명} 변환 확인해줘.
```

검토 항목:
- **책 유형 추정 신뢰도 90%+** (낮으면 hint 명시 필요)
- 속성 라벨 부착 누락 5% 이하
- `[논점정리]` → `> [!summary] 논점정리` callout 변환 확인
- `[개념]`·`[사안]` → `**[개념]**` 인라인 굵게 변환 확인
- `[불명]` → `{불명}` 변환 확인
- backlink `[[쟁점명]]` 보수적 부착 (남발 X)
- **한자 병기 없음** (CLAUDE.md #37)

### 2.3 Obsidian vault 동기화 검증 (선택)
```
outputs/02_wiki/책이름_chunk_001_wiki.md를 임시로 Obsidian vault에 복사해서
callout이 박스로, backlink가 활성 link로 정확히 렌더링되는지 확인해줘.
경로: 사용자가 알려줘야 함
```

### 2.4 02-card 단독
```
outputs/02_wiki/책이름_chunk_001_wiki.md를 02-card로 변환.
prompts/02-card_claude_Anki카드화_v3.6.xml 적용.
note_type: auto (속성 자동 분기), difficulty: A
결과: 속성 자동 분기 정확도·태그 2축 부착·표 분해 확인.
```

검토 항목:
- 속성 자동 분기: 정의/요건/효과/조문 → rule, 판례 → case_law, 객관식정지문 → mcq
- 태그 2축: 모든 카드에 `과목::`+`속성::`+`주제::`+`난이도::`+`출처::`
- 표 분해: 위키 메모 준수
- {불명} 비율 15% 이하

### 2.5 06b 단독
```
inputs/cases/사례집_샘플.pdf 06b로 카드화.
prompts/06b_claude_사례집문제_extract_v3.6.xml 적용.
풀이 영역 자동 식별 성공 여부·grounding 정확도·검증필요::AI추출 태그 부착 확인.
```

## 3. 일상 사용 명령

| 상황 | 입력 |
|---|---|
| 단권화 책 전체 자동 | `inputs/raw_pdf/형법총론.pdf 처리. 단권화` |
| 위키화만 (Obsidian) | `inputs/raw_pdf/송영곤논점민법강의.pdf 위키화만` |
| 위키 → 카드만 | `outputs/02_wiki/송영곤_chunk_001_wiki.md 02-card로 변환` |
| 사례집 풀이 포함 | `inputs/cases/김춘환민법사례연습.pdf 06b로 카드화` |
| 사례집 1문제 정밀 | `cases/문제5.md 06a로 카드화` |
| 선행 단서 카드 추가 | `02-card 적용할 때 generate_precursor_cards: true 켜줘` |
| 사후 검증 | `검증필요::AI추출 카드 grounding 페이지 정리해줘` |

## 4. 자주 막히는 케이스

### "PDF가 너무 커요"
```
Claude API PDF 한계는 32MB / 100p.
큰 책은 100p 단위로 미리 분할 후 청크 단위로 첨부해줘.
사용자가 PDF 분할 도구 사용 (pdfsplit 등) 또는 Adobe Acrobat 등.
```

### "출력이 이상해요"
```
outputs/[해당파일] 보여주면 어떤 부분이 이상한지 확인할게.
특히 책 유형 추정·callout 변환·속성 라벨 부착 점검.
프롬프트 수정 필요하면 prompts/에서 수정하고 알려줘.
(주의: 프롬프트 수정 전 5.기타/패키지백업/에 백업 확인)
```

### "한자가 출력에 섞여 있어요"
```
CLAUDE.md #37 위반. 동음이의는 한국어 풀이로만 구별.
해당 부분 한국어 대역으로 수정 요청해줘.
prompts/에 한자 병기 금지 규정 있는지 재확인 (모든 prompts/ v3.6.xml·md).
```

### "v3.5.2 카드와 v3.6 카드 섞이는데?"
```
v3.5.2 카드는 유형::·쟁점:: 태그, v3.6 카드는 속성::·주제:: 태그.
당분간 별개 덱(변시::v35 / 변시::v36)으로 운영 권장.
점진적 통합은 Anki Browse에서 일괄 태그 치환:
  Find: tag:유형::조문    Replace: tag:속성::조문
```

## 5. Obsidian 단권화 vault 동기화 (선택)

별도 명령:
```
outputs/02_wiki/송영곤논점민법강의_chunk_*.md를 Obsidian vault의 
민법/송영곤논점민법강의/ 폴더에 복사해줘.
원본은 유지하고 vault에 사본만.
```

Obsidian vault 경로는 사용자가 알려줘야 함.

## 6. 안전 수칙

- **API key 불필요** — Claude Code 구독으로 처리
- **outputs/ 폴더는 자동 백업 안 됨**. 중요 결과는 따로 보관
- **사용자가 명시 안 한 자동화 금지** (자동 Anki Import, 자동 git push, 자동 Obsidian 동기화)
- **v3.6 Phase 1.2 시범 운영 중**: 첫 책 처리 후 다음 책 자동 진행 금지. 사용자 확인 필수
- **한자 병기 금지** (CLAUDE.md #37): 동음이의는 한국어 풀이로만 구별
- **외국어 표현 금지** (CLAUDE.md #37): 한국어 대역만

## 7. v3.5.2 → v3.6 마이그레이션 옵션

A. **점진 (권장)**: 기존 v3.5.2 카드 유지 + 새 자료부터 v3.6
B. **즉시 통합**: Anki Browse에서 태그 일괄 치환 (위험, 백업 필수)
C. **별개 운영**: 변시::v35·변시::v36 별개 덱 (안전, 카드 중복 가능)

## 8. legacy 보존 안내

다음은 v3.6 Phase 1.2에서 사용 안 함 (추후 API key 발급 시 사용 가능):
- `scripts/*.py` — Anthropic API 자동화
- `.env`, `.env.example` — API key 설정
- `requirements.txt` — Python 의존성
- `logs/` — scripts 실행 로그

원본 백업: `5.기타/패키지백업/2026-05-21/claude_code_package_v2/`

## 9. 막힐 때 vs Claude.ai 채팅으로 돌아가기

Claude Code 안에서 잘 안 되면:
1. 결과를 outputs/에 저장하라고 명령
2. 그 파일을 Claude.ai에 첨부해서 디버깅
3. 프롬프트 수정 필요 시 Claude.ai에서 검토 후 prompts/에 반영

기존 수동 워크플로우(Gem·Claude Project)는 항상 사용 가능. Claude Code는 자동 layer.
