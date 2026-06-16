---
description: 클라우드 routine(데이터 브리프) ↔ 로컬 socratic 스킬(학습 엔진) 핸드오프. 트리거 - "오늘 진도 진행", "/socratic", "오늘 숙제 풀자", "morning brief 처리"
---

# Routine ↔ Socratic 학습 루프

> **routine = 머신 파싱 가능 데이터 브리프** (YAML frontmatter + 표). **socratic-core = 학습 엔진** (질문·채점·갱신). 두 환경 분리, Drive 동기화로 연결.

---

## 환경 구분

| 환경 | 역할 | 도구 | 출력 |
|------|------|------|------|
| **Anthropic 클라우드** (routine) | 데이터 브리프 자동 생성 | Drive MCP만 | `.agent/daily-brief/*.md` (YAML+표) |
| **로컬 PC** (Cowork·Code) | 소크라틱 학습 진행 | socratic-loader, socratic-core, spaced-repetition, korean-law-mcp, qmd_search, python | state JSON 갱신 |

→ 두 환경은 **공유 데이터(Drive `.agent/state/`)** 로만 연결. 직접 호출 X.

---

## morning.md 형식 (머신 파싱 우선)

```
---
date: 2026-04-28
day_of_week: 화
srs_due_count: 4
weak_points_count: 4
ad_hoc_count: 1
prep_subjects: ["민법"]
final_dday: 35
review_mode_dday: 25
review_mode_start: 2026-05-22
intl_dday: 41
ethics_dday: 43
final_status: "개념 복습중"
generated_at: 2026-04-28T09:08:00+09:00
sources: [".agent/state/learning.json", ".agent/state/srs_log.json", ".agent/state/goals.json"]
---

# 진도 브리프 2026-04-28

## srs_due
| id | topic | scope | next_review | overdue_days | repetitions | ef |
|---|---|---|---|---:|---:|---:|
| 1 | 권리남용 요건 (주관+객관) | 권리주체_행위능력 | 2026-04-04 | 24 | 0 | 2.5 |
...

## weak_points
| topic | wrong_count | last_attempt | priority |
| 권리남용 요건 (주관+객관) | — | — | — |
...

## ad_hoc
| date | subject | task | done | added |
| 2026-04-28 | 형법 | 형법 미수범 기출 25-1번 풀기 | false | 2026-04-27 |

## prep
- subject: 민법
- reason: 수요일 민법 스터디 prep

## final_exam
- d_day: 35
- review_mode_start: 2026-05-22 (D-25)
- status: "개념 복습중"
- progress: ...
- daily_quota_remaining: ...

## related_exams
- intl_law: D-41
- legal_ethics: D-43

[OK]
```

핵심: 소크라틱 톤·접힌 답·"왜?"·재회상 X. 그건 socratic-core가 함.

---

## evening.md 형식

morning과 동일 frontmatter 패턴 + `_await_user_` 마커:

```
---
date: 2026-04-28
day_of_week: 화
srs_due_count: 4
ad_hoc_count: 1
morning_brief_found: true
final_dday: 35
...
---

## srs_due_recall
| id | topic | quality_score | notes |
| 1 | 권리남용 요건 (주관+객관) | _await_user_ | _await_user_ |
...

## ad_hoc_status
| date | task | progress |
| 2026-04-28 | 형법 미수범 기출 25-1번 풀기 | _await_user_ |

## final_progress_request
- requested_inputs:
  - ox_done_today: "민법1=N·민법3=N·형법1=N·헌법1=N"
  - case_done_today: "민법1=K·민법3=K·형법1=K·헌법1=K"

[OK]
```

→ `_await_user_` 마커는 socratic-core가 row 단위로 사용자 답장을 받아 채점·갱신할 위치.

---

## 일일 루프 (Mon~Sat)

### 09:00 KST · main morning routine 자동 발화
- ID: `trig_01NSqSzMazfoL8KAweSPodFG`
- Drive에서 state JSON 읽기 → YAML+표 브리프 → `.agent/daily-brief/YYYY-MM-DD-morning.md`
- Gmail 발송 X

### 10:00 KST · morning watchdog 자동 발화
- ID: `trig_01BUFpiZCFQCnJMTtipm3EcV`
- 검사: 오늘 morning.md 존재 + size > 100B + 마지막 줄 `[OK]`
  - 정상 → `.agent/daily-brief/YYYY-MM-DD-watchdog-morning.md` OK 마커
  - 실패 → ALERT 마커 + 사용자 수동 [지금 실행] 안내 (sandbox에서 RemoteTrigger 미지원으로 자동 재발화 불가)

### 사용자 학습 시간 (자유)
1. PC에서 morning.md 확인 (Drive 동기화 후 폴더)
2. **로컬 Cowork·Code 세션**에 다음 중 하나 입력:
   - `오늘 진도 진행` (자연어)
   - `/socratic` (슬래시)
   - `공부 시작`
3. **socratic-loader 자동 진입** (CLAUDE.md #17 트리거):
   - morning.md 읽고 frontmatter 파싱: `srs_due_count`, `weak_points_count`, `ad_hoc_count`, `prep_subjects` 추출
   - 표 row 단위로 처리 (id 매칭으로 srs_log.json 직접 갱신 가능)
   - qmd 검색 + spaced-repetition 결합
4. **socratic-core 진행**:
   - srs_due 표의 row 순차 처리 → 유도 질문 → 사용자 답변 → Reverse-RAG 채점 → quality_score 결정
   - 조문·판례 등장 시 korean-law-mcp 자동 호출
   - learning.json (weak_points wrong_count++) + srs_log.json (SM-2 next_review 재계산) 즉시 갱신 (id 매칭)
5. ad_hoc·prep 항목도 row 단위로 처리
6. 종료 시 사용자가 "종료" 또는 자연 종료

### 22:00 KST · main evening routine 자동 발화
- ID: `trig_01LiHwfs3WxYaxMmihyzpVTF`
- 갱신된 state JSON + 오늘 morning.md 읽기 → evening.md (`_await_user_` 마커 포함)
- 사용자가 PC에서 답장 처리 → final_exam.progress 등 갱신

### 일요일
- 모든 routine SKIP. 사용자 자유 학습.

---

## 데이터 흐름

```
                    [09:00 KST]
Drive(.agent/state/) ─read─→ main morning ─write─→ Drive(daily-brief/morning.md, YAML+표)
                                                          │
                          [10:00 KST: watchdog 검증]      │
                                                          │
                                  ↓ Drive 동기화          │
                              사용자 PC                   │
                                  ↓ /socratic              ↑
                          socratic-loader (frontmatter 파싱)
                                  ↓
                          socratic-core (row 단위 질문·채점)
                                  ↓
                      learning.json·srs_log.json 갱신 (id 매칭)
                                  ↓ Drive 자동 동기화
Drive(.agent/state/) ───────────┘
                                  
                    [22:00 KST]
Drive(.agent/state/) ─read─→ main evening ─write─→ Drive(daily-brief/evening.md, _await_user_)
```

---

## socratic-core ↔ frontmatter 파싱 가이드

socratic-loader가 morning.md를 처리할 때:

```python
# 의사코드 (실제는 socratic-loader/scripts/)
import yaml
with open("daily-brief/2026-04-28-morning.md") as f:
    text = f.read()
front, body = text.split("---\n", 2)[1:]
meta = yaml.safe_load(front)

# frontmatter에서 즉시:
srs_due_count = meta["srs_due_count"]  # 4
prep_subjects = meta["prep_subjects"]   # ["민법"]
final_dday = meta["final_dday"]         # 35

# 표 파싱 (## srs_due 섹션):
# id 컬럼이 srs_log.json items[i].id와 직접 매칭 → row 단위 처리
for row in parse_table(body, section="srs_due"):
    item_id = row["id"]
    topic = row["topic"]  # content 필드 그대로
    # 사용자한테 질문 → 답변 → quality_score 매기기
    # → srs_log.json items[id-1] 직접 갱신
```

→ frontmatter 카운트로 빈 섹션 빨리 건너뛰기, 표 row id로 정확히 매칭. 자유 텍스트 파싱 X.

---

## 핵심 룰

- routine은 **read-only state + write to Drive** (frontmatter+표 형식)
- 소크라틱 톤·접힌 답·"왜?" elaboration **routine에서 절대 생성 X** (socratic-core가 담당)
- `_await_user_` 마커: socratic-core가 채워야 할 빈 자리
- id 필드: srs_log.json·learning.json과 1:1 매칭 → 정확한 갱신 보장
- Drive 동기화 지연 ~30초. 즉시 반영 필요 시 routine [지금 실행]

---

## 트리거 매핑 (CLAUDE.md #17 보강)

| 사용자 입력 | 자동 진입 |
|---|---|
| `오늘 진도 진행`, `/socratic`, `공부 시작` | socratic-loader → morning.md frontmatter 파싱 → socratic-core |
| `오늘 morning brief`, `오늘 숙제 봐줘` | Drive에서 morning.md 읽고 표시 |
| `evening 점검`, `오늘 진행 어때?` | Drive에서 evening.md 읽고 `_await_user_` 마커 단위로 답장 받기 |
| `진도 갱신`, `OX·사례 결과 입력` | spaced-repetition + goals.json final_exam.progress 갱신 |

---

## 실패 모드 대처

| 증상 | 원인 | 조치 |
|------|------|------|
| morning.md 없음 (10:00 후) | main 09:00 발화 실패 | watchdog ALERT 마커 확인 → routine 페이지 [지금 실행] |
| evening.md 없음 (23:00 후) | evening 22:00 발화 실패 | routine 페이지 [지금 실행] |
| frontmatter 깨짐 | base64 디코딩 실패·agent 오류 | 마커 `[데이터 읽기 실패]` 본문에 들어감 → 사용자 확인, 재발화 |
| state 갱신 안 됨 | 로컬 socratic 세션이 write 못 함 | Drive 동기화·권한 확인 |
| Drive (1) suffix 누적 | 같은 날짜 여러 번 실행 | 정상. 가장 최근 파일 참조. 정리는 `_trash`로 (삭제 X) |

---

## 룰 준수

- CLAUDE.md #21 (Socratic First): 학습 질문은 socratic-core로
- CLAUDE.md #2/3 (소스 근거): routine은 source JSON 그대로 인용 (변형 X)
- CLAUDE.md #16 (삭제 금지): daily-brief 누적은 `_trash`로
- CLAUDE.md #34 (판례 원문): socratic-core가 처리
- CLAUDE.md #35 (백링크): routine 본문에서는 X (표 안에는 표시 X)

---

생성: 2026-04-28 (machine-parsable format으로 갱신)
