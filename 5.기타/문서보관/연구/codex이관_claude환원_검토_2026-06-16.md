# Codex 이관 역할 → Claude 환원 검토 (2026-06-16)

> 근거 문서: `sync/_meta/CODEX_BOOTSTRAP_REPORT.md` (로스쿨 학습 자동화 설계서)
> 운영 환경: 사용자는 GPT Pro/Codex를 사용하지 않고 **Claude Web** 기준으로 운영한다(2026-06-16 사용자 지정). 이 문서에서 'Claude'는 Claude Web을 가리킨다.
> 결론: **이관 무방. 단, 보고서를 글자 그대로 구축하지 않고 핵심 개념만 기존 시스템에 이식한다.**

## 1. 사실관계

- 보고서가 설계한 시스템(SQLite 원장 `progress.sqlite` + `law-study/` 별도 레포 + Anki batch CSV)은 **구축된 적 없음**. (sqlite·law-study 디렉토리 부재 확인)
- 실제 Codex로 넘어간 역할 = **카드 v37·쟁점 위키 파이프라인** (`.agent/workflows/card-wiki-pipeline.md` + `sync/_meta/이식용_핸드오프_프롬프트_2026-06-15.md`).
- 위임 사유 = "Claude Code 구독 비활성화 → 서브에이전트 인증 실패"라는 **일시적 접근 문제** (능력 문제 아님). 본 세션에서 해소(워크스페이스 접근·korean-law-mcp 정상).

## 2. 이관 판정: 무방 (Claude가 더 적합)

보고서 설계의 약 80%가 이미 Claude측 워크스페이스에 존재 — Codex로 재구축은 이중화.

| 보고서 설계 | 기존 자산 |
|---|---|
| `progress.sqlite` 진도·약점 원장 | `.agent/state/progress.json`·`learning.json` + progress-tracker 스킬 |
| review_queue (D+1/D+2…) | `srs_log.json` + spaced-repetition 스킬(SM-2) |
| problem/issue catalog | `problem_index.json`(v2.0)·`issue_frequency.json` + problem-index 스킬 |
| 답안 채점 워크플로우 | case-answer-review 스킬 + `case_answer_packet.json` |
| Anki batch CSV | v37 genanki **apkg 16개·19,629장** + `build_v37_apkg.py` |

추가 근거: 채점·검증의 근거 규칙(AGENTS #5 원문·#16 인용·#38 판례문구)은 **korean-law-mcp(Claude측 MCP)** 에 의존 — Codex 네이티브 미지원.

## 3. 채택 / 기각

### 채택(기존 스킬에 이식) — 보고서에 있고 현재 공백
1. **Anki 카드 생명주기 + note_key 안정성 + 중복방지** (보고서 §11~13·20·23).
   - 현 빌더는 genanki guid를 **내용 기반**(`guid_for(src, blk[:30], 정규화텍스트)`)으로 생성 → 카드 텍스트 수정 시 guid 변동 → **복습이력 분실**. 안정 note_key→guid 전환 필요.
2. **답안 채점 루브릭 가중치** (쟁점0.25/키워드0.20/구조0.20/결론0.15/포섭0.20) + 감점 시 source 의무 (보고서 §17).
   - 현 case-answer-review는 "초벌 평가"라 고정 루브릭 없음.
3. **약점→복습→카드 자동연동** (1회 누락=복습큐, 2회=카드후보, 결론오류=즉시) (보고서 §18~19).
   - 현재 case-answer-review·spaced-repetition·learning.json이 분리 운영(채점이 srs를 자동 갱신 안 함).

### 기각(기존 시스템 포크 위험)
- SQLite 원장 — 워크스페이스는 JSON 상태. 마이그레이션 이익 없음·불안정화.
- 별도 `law-study/` 레포 + `materials_structured/` 중복 — 교재는 이미 `outputs/01_ocr_llamaparse/`·`sync/wiki/`.
- CSV batch — v37 genanki apkg가 더 발전됨.

## 4. 실행한 업그레이드 (2026-06-16)

| 파일 | 변경 |
|---|---|
| `.agent/workflows/card-wiki-pipeline.md` | 운영주체 Claude 환원 명시 + §8 카드 생명주기·note_key·중복방지 신설 |
| `.agent/skills/case-answer-review/SKILL.md` | 채점 루브릭·감점 source 의무·약점 연동 규칙 신설 |
| `.agent/skills/spaced-repetition/SKILL.md` | 오류유형별 복습간격 연동표 신설 |
| `AGENTS.md` | #19 워크플로우 목록에 card-wiki-pipeline 추가 |

## 5. 후속

- [완료 2026-06-16] `build_v37_apkg.py`의 guid를 **안정 note_key**(`{파일stem}::{basic|cloze}::{seq:04d}`)에서 파생하도록 전환 → 카드 수정 시 guid 유지·복습이력 보존. key=출처(파일 고유 stem), card_type=빌더 실제 모델(basic/cloze), seq=(파일,종류)별 등장순 누적번호. 내용기반 dedup은 별도 유지해 총장수 보존(19,629 동일). 검증: `_apkg_report.md` 한자0·번호없는cloze0·덱별분포 동일, 일회성 테스트로 "내용 수정해도 guid 동일" 확인. **사용자 고지·승인('전환만 진행', 마이그레이션 맵 미생성)** — 이 전환 직후 첫 임포트 1회는 v37 전량이 새 노트로 인식되어 복습이력이 초기화됨(구 노트는 남아 중복). 향후 카드 텍스트 수정은 동일 노트 업데이트로 이력 보존.
- 채택 개념 #2·#3을 render_case_answer_review.py / srs_scheduler.py에 코드 반영(현재는 규칙·스펙만 문서화). — 미실행
