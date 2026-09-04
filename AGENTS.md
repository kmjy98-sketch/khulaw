# AGENTS.md

> **[ACTIVE 2026-06-26 부활 및 정합]** 본 문서는 에이전트 호환 및 룰 로드를 위한 규칙 미러 파일입니다. **권위본은 `CLAUDE.md`**이며, 상세한 모든 룰은 `CLAUDE.md`를 기준으로 적용됩니다. 내용이 충돌할 경우 `CLAUDE.md`를 우선하되, 본 문서도 최신 상태로 정합 갱신을 병행합니다.

## 적용 범위
- 이 문서는 `E:\법학볼트` 워크스페이스의 운영 기준입니다(구 `H:\내 드라이브` — 2026-06-26 E: 정정. 운영 주체: Claude Web/Code). 본 문서는 Codex 등 외부 AI 호환 미러이며, 충돌 시 권위본 `CLAUDE.md`를 우선합니다. 실행 주체를 특정 모델로 고정하지 않되 기본 운영주체는 Claude Web으로 한다.
- 하위 `.agent/workflows`, `.agent/skills`, `.agent/state`에 동일하게 적용합니다.
- 사용자-facing 답변은 한국어를 기본으로 합니다. 코드·명령·원문 인용·전문용어는 필요한 경우 원어를 병기할 수 있습니다.
- 과목별 하위 폴더에 `AGENTS.md`가 있으면 루트 규칙과 함께 적용하고, 과목별 자료 위치·우선순위는 해당 하위 문서를 우선합니다.

## 소스 및 근거 규정 (#1-9)
1. Source Grounding: 모든 단정은 사용자 제공 소스(파일/전사/문서) 근거만 사용.
2. Not-in-Source: 소스 미확인 단정은 출력 금지. 반드시 "소스에서 확인할 수 없습니다" 또는 "자료 부족—보류"로 처리.
3. Evidence Mandatory: 법리/사실 단정 시 근거 2줄 표기.
   - 근거 발췌: "……"
   - 근거 위치: 《파일명》 p.X / 절 / 소제목 / 타임스탬프 / chunk_id
   - 근거 각주 변형(허용): 근거 발췌 인라인 + 근거 위치를 `[^id]` 각주 정의로 분리 가능.
     예: `근거 발췌: "……"[^민3-18]` → `[^민3-18]: 《교재명》 p.XX`
     상세: `law-note-supplement/references/note-structures.md` "각주(Footnote) 규칙"
4. No Fabricated Location: 위치 추정 금지. 식별자 부족 시 "(확인 불가—위치 식별자 부족)".
5. Original-Text Priority: 조문/판례 원문 우선. 미포함 시 "(원문 미포함)". korean-law-mcp API 반환값은 공적 법령 원문으로서 #1 소스 제한의 예외로 허용한다.
6. Integrity: 조문번호/판례명/선고일 정확성 우선. 불명확 시 `[불명확: 후보1/후보2]`.
7. COT Non-Disclosure: 내부 추론은 사용자에게 직접 노출 금지. 요청 시 1~2문장 요약 + 근거만.
8. Output Minimalism: 요청 형식 우선, 불필요 장문 금지.
9. PDF Handling: Read 도구(작은 PDF, 1MB 미만) → Claude 네이티브 PDF 지원을 우선한다(필요 시 #46 폴백 체인). 로컬 pypdf 전처리는 RAG 청킹/인덱싱 용도로만 사용.

## 성능 최적화 (#10-12)
1. Structured Thinking: 내부 단계 추론은 수행하되 출력은 결과 중심.
2. XML Structure(선택): 복잡 입력은 `<context>`, `<task>` 등 구조화 태그 사용 가능.
3. Uncertainty Acknowledgment: 불확실 시 추정 금지, #2 규칙 적용.

## RAG 2.0 운영 (#13-15)
1. Multi-Step Retrieval: Query Expansion(Step-back/HyDE) → Hybrid Search(Semantic+Keyword) → Re-ranking(상위 3~5).
2. Reverse-RAG: Claim 추출 → 소스 매칭 → [Supported/Contradicted/Not Found] 판정.
3. Not Found/Contradicted 단정은 출력에서 삭제. 추측 표현("~인 것 같다") 금지.

## Prompt-Based Citation (#16)
- 법학/LEET 응답은 인라인 인용 기본 적용.
- 인용 형식: `[《문서명》 p.X | "정확한 발췌"]`.
- API 소스(korean-law-mcp) 인용 형식: `[《국가법령정보센터》 제○조 | "조문 원문"]` 또는 `[《국가법령정보센터》 사건번호 | "판결요지"]`.
- 인용 불가 단정은 삭제(#2).

## 파일 작업 원칙 (#17-18)
1. Verify-Before-Act: 이동/이름변경 전 파일 내용 또는 메타데이터 확인.
2. State Check: 폴더 구조 작업 전 현재 상태 조회, JSON 수정 전 기존 내용 읽기.
3. 삭제 금지(최우선): `Remove-Item`, `del`, `rm`, `rmdir` 등 삭제 명령 금지(빈 폴더 포함).
4. 삭제 대체: 워크스페이스 루트 `_trash/{YYYY-MM-DD}/` 하위로 이동 (2026-06-11 단일화. 구 `5.기타/_trash/`는 레거시 보관 동결).
   - 예: `민사\민법\참고\파일.pdf` → `_trash\2026-06-11\민사_민법_참고\파일.pdf`
5. 운영 폴더: `_inbox/`, `_RAG_데이터/`는 `5.기타/` 하위에서 관리한다. `_trash/`는 루트에서 관리한다.
   - 표준 경로: `5.기타/_inbox/`, `5.기타/_RAG_데이터/`, 루트 `_trash/`
6. 파일 생성 위치: 새 파일은 루트가 아닌 유형별 표준 위치에 생성한다 — 스크립트 `.agent/scripts/`, 상태·데이터 `.agent/state/`, 운영 메모 `sync/_meta/`, 비노트 문서 `5.기타/문서/`, 백업 `5.기타/` 하위.
7. 구글 포인터 파일(`.gdoc`/`.gsheet`/`.gslides`/`.gscript`)은 로컬 직접 읽기 불가 — Drive MCP로 열람한다. 루트 적치분은 `5.기타/구글문서/`로 집결한다(밀메뉴 관련 제외; Gemini Gems·Colab Notebooks·Opal 폐기 — 2026-06-21). 공유드라이브 내 포인터는 이동 제외(#16-B).
8. 공유드라이브 쓰기·이동 금지: `0.공유드라이브/` 및 Google 공유 드라이브 경로의 파일·폴더는 이동·이름변경·삭제·쓰기 금지. 읽기·복사만 허용하며, 사용자 명시 승인 없이는 `_trash` 이동도 하지 않는다.
9. 파일 이동·이름변경·복사 로그: 워크스페이스 내 파일/폴더를 이동·이름변경·복사·`_trash` 이동할 때마다 `.agent/file_ops_log/master.{csv,jsonl,md}`에 1작업=1행으로 기록한다. 원칙적으로 `.agent/scripts/log_file_op.py` 헬퍼를 사용한다.
10. 빈 파일 정리: 0바이트 또는 공백뿐인 텍스트 파일은 `_trash/{YYYY-MM-DD}/` 이동을 권고한다. 작업 중 새로 만든 임시 파일만 자동 이동할 수 있고, 기존 파일·설정 파일·구글 포인터 파일은 사용자 확인 전 이동하지 않는다.
11. PDF 분할 및 목차·색인 분리 원칙: 대용량 PDF 교재를 단원별로 분할할 때 목차(`_00_목차`)와 색인(`_99_색인`)은 본문과 분리하여 각각 단독 분할하고, 실제 물리 페이지를 정교하게 검증하여 분할 기준을 정한다. 상세 명명 및 폴더 배치 기준은 `CLAUDE.md`의 `#16-D` 규칙을 참조한다.

## 워크플로우 자동 참조 (#19-20)
- 파일 분류/이름 변경: `.agent/workflows/classification-rules_v2.md`
- 학습/문제/채점: `.agent/workflows/socratic.md`
- 사례답안 채점/대비자료: `.agent/workflows/case-answer-rag.md`
- 교재 내 문제 인식/DB 등록 준비: `.agent/skills/textbook-problem-intake/SKILL.md`
- 스킬 경계/중복 검토: `.agent/workflows/skill-overlap-review.md`
- 리걸 스킬 묶음 운영: `.agent/workflows/legal-suite.md`
- 노트 정리/수업 정리: `.agent/workflows/lecture-notes.md`
- 리걸 리뷰 + 소크라틱/RAG 통합: `.agent/workflows/legal-socratic-rag.md`
- LEET 풀이: `.agent/workflows/leet-solve.md`
- 전사 파이프라인: `.agent/workflows/colab-pipeline.md`, `.agent/skills/whisper-transcribe/SKILL.md`, `.agent/skills/transcript-correction/SKILL.md`
- 현재 스킬 구조도: `.agent/workflows/skill-structure.md`
- 기존 노트 보완·검토·재구조화: `.agent/skills/law-note-supplement/SKILL.md`
- 카드 v37·쟁점 위키 운영: `.agent/workflows/card-wiki-pipeline.md` (카드 생명주기·note_key·중복방지 §8 포함). 운영 주체는 Claude Web으로 환원(2026-06-16).
- 세션 시작·이전 작업 참고: 쟁점 위키 `sync/위키/{과목}/`(#50 정본)에서 관련 아티클만 읽는다. 원문 전문은 `outputs/`(비동기).
- 메모리 정비/lint/컴파일: `memory-maintenance`(Skill) 진입점(#41). flush.py·compile.py는 **은퇴 검토(동결)** — 직접 호출 안 함.
- OCR 교정(2026-06-21 — Colab 폐기): 신규 추출=LlamaParse 로컬(→ `outputs/01_ocr_llamaparse/`), 교정=`.agent/scripts/haiku_ocr_correct.py`·`sonnet_review.py`·`apply_corrections.py`. 구 Colab 노트북 2종(`.agent/notebooks/`)은 레거시(신규작업 미사용).
- 파일 이동·이름변경·복사 로그: `.agent/skills/file_ops_log/SKILL.md`, `.agent/scripts/log_file_op.py`
- `claude_code_package_v2`(`5.기타/프롬프트 등 개선/claude_code_package_v2/`)는 **파일 존재 확인됨**(2026-06-16). 카드·위키 운영 기준은 `card-wiki-pipeline.md`를 우선하고, 패키지 prompts는 그 보조로만 사용한다. 실행 주체를 특정 모델로 고정하지 않는다.

## 진도 추적 (#21-22)
1. TOC-Based Progress: `{편}>{장}>{절}>{항목}` 형식. 진도 정본=`.agent/state/progress.json`(수동 갱신 — 전사문 자동추적 폐기·재구축 금지). `진도_현황.json`은 대시보드 snapshot.
2. Weak Problem Storage: `.agent/state/learning.json`의 `weak_points` 사용.
3. Spaced Repetition: `.agent/state/srs_log.json` — SM-2(Claude 중단기) → FSRS(안키 장기) 핸드오프(전면전환 아님; 시험임박은 deadline-aware desired-retention).

## 학습 행동 원칙 (#23-27)
1. Socratic First: 학습 요청은 `/socratic` 우선.
2. Label Restriction: "기출/빈출" 라벨은 소스 표지 + 근거 2줄 있을 때만.
3. Scoring Constraint: 배점표가 있으면 반영, 없으면 O/△/X.
4. IRAC Block: 사례형은 청구권/항변 블록 + 근거 2줄.
5. Source Priority: 사례형 교재 > 사례형 자료 > 선택형 자료 > 정리 자료.

## 모드 제어 (#28-30)
1. Stop Word: "종료" 입력 시 현재 흐름 종료.
2. Auto/Manual Toggle: "자동"=약점 즉시 제시, "수동"=메뉴 질문.
3. Only-on-Request: 전사/발췌는 명시 요청 시에만 수행.

## 코딩 규정 (#31-34)
1. Rule Supremacy: 코드/스크립트는 #1-18 위배 금지.
2. Output Compliance: 스크립트 출력도 근거 규칙 준수.
3. Code Integrity: 기존 기능 보존, 주요 변경 전 테스트.
4. Whisper Priority: 음성 전사는 `.agent/skills/whisper-transcribe/scripts/transcribe.bat` 로컬 경로 우선 사용.

## Checklist Mandatory (#35)
파일 생성/수정/이동이 2개 이상이면 반드시:
1. 변경 대상 파일 목록 작성
2. 각 파일별 변경 1줄 요약
3. 변경 순서 명시
- 예외: 단일 파일 수정, 오타/포맷팅만 변경

## 노트 정리 형식 규칙 (#36-41)
적용 범위: 민법·형법·헌법 등 모든 과목의 사례형 노트 및 압축본.

1. **#36 청구-항변 구조 형식**: 사례형 답안의 청구-항변 구조는 2열 표(원고|피고) 형식으로 정리한다. 3열 표·볼드 블록·줄글형은 이 구조에 사용하지 않는다. 형식: `| **원고 (갑)** | **피고 (을)** |` + 행 단위로 청구→항변→재항변, 빈 셀은 `—`.
2. **#37 모답형/보강포인트 배치**: 사례형 답안 연습(모답형)·보강 포인트·교차검증 결과는 해당 쟁점 섹션 안에 배치한다. 암기 문장·시험 직전 접근순서·판례 총정리표는 별도 섹션으로 유지한다.
3. **#38 판례 문구 원칙**: 판례의 태도·입장은 교재나 판례 원문에 확인된 표현만 사용한다. 전사본·요약에서 온 비공식 표현은 교재 원문 표현으로 대체한다. 판례 사건번호는 함께 표기한다.
4. **#39 백링크 규칙**: 노트 본문 내 판례·조문·핵심 개념에 옵시디언 위키링크(`[[...]]`)를 사용한다.
   - 판례: `[[대판 YYYY.M.DD, YYdaXXXX]]` 또는 `[[헌재 YYYY.M.DD, YYYYhunmaXXXX]]`. 선고일 미확인 시 `[[YYdaXXXX]]`만 둔다.
   - 조문: `[[§XXX]]`(§10 이상만 — §1~§9는 섹션번호 오탐 방지로 제외) 또는 `[[민법 제XXX조]]`. 같은 노트 내 하나의 형식으로 통일한다.
   - 핵심 개념: `[[선의취득]]`, `[[물권적청구권]]`처럼 명사구 단위로 고정한다.
   - 교차참조: 같은 판례·조문·개념이 여러 과목 노트에 등장하면 동일한 백링크명을 쓴다.
   - 제외 범위: 표 셀 내부·각주 정의 내부·코드블록 내부에는 백링크를 걸지 않는다.
5. **#40 교수님 고유 표현 태그**: 각 교수님만의 독특한 표현·용어는 `[전경운]`·`[서보학]`·`[강혜림]`·`[이진]` 등 태그로 별도 표시한다. 인라인 볼드(`**[전경운]**`) 또는 블록 단위 제목 모두 허용한다. 태그된 문구는 해당 교수님 소스에서 직접 확인된 표현만 쓴다(#38과 연동).
6. **#41 외국어 표현 금지**: 노트 본문에는 라틴어·독일어·한자 등 외국어 표기를 사용하지 않고 한국어로 기재한다. 예: 甲→갑, 乙→을, actio libera in causa→원인에 있어서 자유로운 행위. 교재 원문 인용도 한국어로 번역하되, 원어 확인이 필요한 경우에만 괄호 보조를 허용한다. `§`·`①~⑳`·`★` 등 기호는 외국어로 보지 않는다.

## Wiki 메모리 시스템 (#42-45)
1. 세션 시작 시 쟁점 위키 `sync/위키/{과목}/`(#50 정본)에서 관련 아티클만 읽고, 전체 wiki를 무조건 로드하지 않는다.
2. wiki는 이전 작업 기록이므로 참고 자료로만 취급한다. 법학·LEET 단정은 교재·전사·문서 등 사용자 제공 원소스 또는 허용된 API 소스로 재확인한다.
3. 노트 수정·보강 결과, 새로 확인된 판례·학설·교수님 입장, 사용자가 지적한 오류, 작업 중 발견한 운영 교훈은 필요 시 `.auto-memory/session_logs/session_{YYYY-MM-DD}_{HHMM}.md`에 기록한다.
4. (2026-06-26 #50 정합) **쟁점 위키=`sync/위키/{과목}/`**(sync), **원문 전문=`outputs/`**(비동기, sync밖). 구 `sync/위키/원문`·`sync/wiki/쟁점`은 폐기→이관. 오래된 아티클도 삭제 없이 `_trash/{YYYY-MM-DD}/`로 이동한다.

## 도구 가용성·충돌 방지 (#46-49)
1. PDF 텍스트가 필요하면 새 추출 전 기존 마크다운을 먼저 찾는다. 우선 위치: `outputs/01_ocr_llamaparse/`, `outputs/02_cards_v37/`, `sync/위키/{과목}/`(쟁점), `5.기타/_백업/`, `.agent/temp_toc/`.
2. (2026-06-26 #16-D 정합) 없을 때만 추출. **PDF 분할·페이지·텍스트에 파이썬(pypdf/pdfplumber/pdftotext) 금지** — 추출=LlamaParse, 분할·열람=PDF 플러그인/`pdf` 스킬.
3. 다른 도구와 같은 파일을 동시에 편집할 가능성이 있으면, 편집 전 파일 크기·첫 줄·최근 수정시간을 확인한다. 충돌 위험이 있으면 별도 파일명(`_v2`, `_claude`, `_정리`)을 사용한다.
4. 주요 산출 노트 작성 후 관련 wiki 진입점이 존재하면 링크 추가를 검토하고, 세션 기록은 Wiki 메모리 시스템 규칙과 통합한다.
5. **에이전트 오케스트레이션(병렬·검증, CLAUDE.md #45-B/C 미러)**: 작업 기본형은 '판단=에이전트, 결정적·무결성=코드, 검증=산출 직후 적대검증 패스'다. ①독립 작업은 같은 턴 병렬, 독립 단위 2개+면 포그라운드 병렬 서브에이전트 fan-out(백그라운드 장시간 금지, dispatch §3), 생성·대량 재작성은 1청크 파일럿(#17·dispatch §5) 통과 후 확대. ②'판단'은 일회성 파이썬보다 에이전트 위임 우선(#45-B), 단 sha256·apkg·정규식 배치·JSON 상태·파일이동 로그(#16-C `log_file_op.py`)는 결정적 코드로 유지. ③법리·판례·조문 단정 산출물은 생성 직후 검증 패스(Workflow verify/refute 서브에이전트)로 #1·#6(korean-law-mcp)·#13·#16-C를 대조하고, 위반 탐지 시 보류·보고·중단 권고(자동 수정·이동·삭제 금지; 실시간 상시 watcher·포그라운드 강제중단은 미지원). ④동시쓰기는 별도 파일명(#45)·공유파일 직렬강제로 격리(worktree는 git 추적 한정). ⑤'읽기·탐색·생성·검증' 비파괴 파이프라인에 한해 Workflow 상시 opt-in, 이동·삭제·push·외부전송은 글로벌 §5·#16계열 개별 승인. 모든 서브에이전트·검증자는 #16/#16-B/#16-C·#1/#6/#13을 동일 상속. 권위본은 CLAUDE.md #45-B/C.

## [RETIRED] Antigravity(Gemini) 아키텍처 — 폐기·번호 회수. 대체 = CLAUDE.md #45-B/C·#50 (경위 → sync/_meta/CLAUDE_변경이력.md)

## 문서 이관 메모
- 운영주체는 **Claude(Web/Code) 단일**이다(2026-06-26 정정). 안티그래비티(Gemini)는 폐기 — 권한 부여 회수. 에이전트 오케스트레이션·다중채점은 CLAUDE.md #45-B/C·#50으로 수행.
- `_archive` 문서는 참고용 보관본이며, 운영 기준은 본 문서와 `.agent/workflows`의 현행 파일을 우선합니다.
- 운영 규칙의 단일 권위본(single source of truth)은 루트·과목별 `CLAUDE.md`이며, 본 `AGENTS.md`는 Codex 등 외부 AI 호환을 위한 미러 사본이다(2026-06-16 Claude Web 기준 운영 확정). 두 문서가 충돌하면 `CLAUDE.md`를 우선하되, **CLAUDE.md 미규정 영역(예: RAG 2.0 운영 #13-15)은 본 문서가 보충 적용**한다. stale 경로·미존재 명령은 실행 경로로 취급하지 않는다.
