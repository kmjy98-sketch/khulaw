# Claude Code 첫 사용 가이드 (v3.6 Phase 1)

> Codex 운영 메모(2026-06-15): 이 문서는 Claude Code 첫 사용용 레거시 가이드다. Codex에서는 `.agent/workflows/card-wiki-pipeline.md`와 `sync/_meta/이식용_핸드오프_프롬프트_2026-06-15.md`를 먼저 읽고, 이 파일의 Claude 설치·로그인 절차는 실행하지 않는다.

## 0. 사전 준비

- Claude Code 설치 (https://docs.claude.com)
- Python 3.10+ 설치
- 이 패키지 폴더를 적당한 위치에 복사 (예: ~/Documents/law_card_pipeline_v2/)

## 1. 첫 명령 (한 번만)

```bash
cd ~/Documents/law_card_pipeline_v2
claude
```

Claude Code 열리면 첫 메시지로:

```
SKILL.md 읽고 v3.6 Phase 1 패키지 구조 파악해.
환경 설정 안 됐으면 .env.example 보고 안내해줘.
의존성 설치 안 됐으면 requirements.txt 보고 설치 명령 알려줘.
```

Claude Code가 자동으로:
- SKILL.md 읽고 4단계 파이프라인·태그 2축·마크다운 충돌 회피 규칙 이해
- `.env` 존재 여부 확인 → 없으면 `.env.example` 복사 + API key 입력 안내
- `pip list`로 의존성 확인 → 부족하면 `pip install -r requirements.txt`
- inputs/ outputs/ 폴더 존재 확인

## 2. 시범 운영 (첫 책 처리 전)

API key 설정 후 다음 명령으로 단계별 테스트:

### 2.1 01번 단독
```
01번 OCR 단독 테스트.
inputs/raw_pdf/에 단권화 책 1권 넣어줄 테니, 첫 100p만 Mode B로 OCR 돌려서
결과 검토 후 02-wiki 진행 여부 결정할게.
```

검토 후:
- 결과 만족 → "다음 단계 02-wiki로 진행"
- 마킹·구조 인식 미흡 → "01번 v3.6 프롬프트 확인. media_resolution: high 적용됐는지"

### 2.2 02-wiki 단독 ⭐ v3.6 신규
```
01번 출력 첫 청크를 02-wiki로 위키화해줘.
book_type_hint: 단권화
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

### 2.3 Obsidian vault 동기화 검증 (선택)
```
outputs/02_wiki/책이름_chunk_001_wiki.md를 임시로 Obsidian vault에 복사해서
callout이 박스로, backlink가 활성 link로 정확히 렌더링되는지 확인해줘.
경로: ~/Documents/Obsidian_vault/시범/
```

### 2.4 02-card 단독
```
outputs/02_wiki/책이름_chunk_001_wiki.md를 02-card로 변환.
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
| 선행 단서 카드 추가 | `02-card 호출할 때 generate_precursor_cards: true 켜줘` |
| 사후 검증 | `검증필요::AI추출 카드 grounding 페이지 정리해줘` |
| 비용 확인 | `이번 달 API 사용 비용 정리해줘` |

## 4. 자주 막히는 케이스

### "API key 없어요"
```
.env 파일 만들고 ANTHROPIC_API_KEY랑 GOOGLE_API_KEY 입력해줘.
.env.example 참고.
```

### "Gemini API 오류"
```
logs/ 확인하고 어떤 에러인지 알려줘.
- 401: API key 잘못됨
- 429: rate limit, 잠시 대기
- 500: Google 서버 일시 장애, 재시도
```

### "02-wiki 출력이 이상해요"
```
outputs/02_wiki/[해당파일] 보여줘. 어떤 부분이 이상한지 확인할게.
특히 책 유형 추정·callout 변환·속성 라벨 부착 점검.
프롬프트 수정 필요하면 prompts/에서 수정하고 알려줘.
```

### "비용이 너무 많이 나와요"
```
이번 달 누적 비용 확인하고, 어떤 작업이 가장 비쌌는지 알려줘.
v3.6 비용 증가 원인: 02-wiki 단계 추가 (책 1권당 약 1.8배).
필요하면 Claude Opus 4.7 → Sonnet 4.6 다운그레이드 옵션 검토.
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

- **API key는 .env에만**. git commit 시 `.gitignore` 확인.
- **outputs/ 폴더는 자동 백업 안 됨**. 중요 결과는 따로 보관.
- **사용자가 명시 안 한 자동화 금지** (자동 Anki Import, 자동 git push, 자동 Obsidian 동기화).
- **v3.6 Phase 1 시범 운영 중**: 첫 책 처리 후 다음 책 자동 진행 금지. 사용자 확인 필수.

## 7. v3.5.2 → v3.6 마이그레이션 옵션

A. **점진 (권장)**: 기존 v3.5.2 카드 유지 + 새 자료부터 v3.6
B. **즉시 통합**: Anki Browse에서 태그 일괄 치환 (위험, 백업 필수)
C. **별개 운영**: 변시::v35·변시::v36 별개 덱 (안전, 카드 중복 가능)

## 8. 막힐 때 vs Claude.ai 채팅으로 돌아가기

Claude Code가 잘 안 작동하면:
1. 결과를 outputs/에 저장하라고 명령
2. 그 파일을 Claude.ai에 첨부해서 디버깅
3. 프롬프트 수정 필요 시 Claude.ai에서 검토 후 prompts/에 반영

기존 수동 워크플로우(Gem·Claude Project)는 항상 사용 가능. Claude Code는 자동화 layer.
