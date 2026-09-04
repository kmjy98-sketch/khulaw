---
type: 연구
주제: claude-for-legal/law-student [클러스터 A3_계획구조] 4스킬 정독·대조
대상스킬: exam-forecast / study-plan / outline-builder / session
작성: 2026-06-28
근거원칙: CLAUDE.md #1(소스근거)·#2(미확인 보류)·#7(추론비노출)
상태: 초안(읽기전용 조사 결과)
---

# 연구 — A3 계획구조 클러스터 (시험예측·학습계획·아웃라인·세션)

> 목적: claude-for-legal `law-student` 플러그인의 계획·구조 스킬 4종을 정독해 우리 시스템(법학볼트 SRS/시험D-day/MOC/닫힌루프)과 대조하고, (1)각 스킬 핵심기법 (2)우리보다 나은 점 (3)IRAC+한국 요건사실론 통합 시사 (4)사례형 전수 카드화 시사를 추출한다.
> 방법: 4개 SKILL.md 전문 정독 + 우리 시스템 6파일(연구_카드구조.md, cardaudit_집계.md, daily-drill/SKILL.md, 연구종합_2026-06-28.md, case-answer-review/SKILL.md, CLAUDE.md #50) 대조. 모든 주장에 파일·인용 근거(#1). 미확인은 '미확인' 표기.

---

## 0. 4스킬 한눈 대조표

| 스킬 | 한 줄 정의 | 우리 대응물 | 핵심 차이 |
|---|---|---|---|
| exam-forecast | 동일 교수 과거시험 N개 분석 → 과목가중·함정유형·출제스타일 예측("예측 아닌 가중 휴리스틱") | (없음) — 우리 daily-drill·weekly-review에 시험예측 모듈 부재 | **출제경향 역분석 자체가 우리에 없음** |
| study-plan | 시험역산 장기계획(학습/드릴/복습 3단계, 약점가중, study-plan.yaml에 session_history 누적·적응) | progress.json(수동)+srs_log+daily-drill+weekly-review로 분산 | **단일 plan 파일에 phase+일별스케줄+session_history 통합·적응**이 우리엔 분산 |
| outline-builder | 목차(아웃라인) 스캐폴드만 생성, 내용은 학생이 채움("내가 안 써준다" 하드룰) | MOC/_목차.md + 위키 논점노트(원문보존) | **"안 써주는" 학습모드 + GAP 마커 + provenance 단서** |
| session | N문항 고정 세션(MBE/essay/flashcard) → 채점 → study-plan에 결과 기록 | daily-drill 2트랙(진도 객관식 / 복습 사례+SRS) | **메서드 라우팅 단순·plan 연동 일원** vs 우리 2트랙·회독연동 정교 |

---

## 1. 각 스킬의 핵심 기법·구조

### 1.1 exam-forecast (시험 예측)
- **단계(SKILL line 14-20)**: ①CLAUDE.md(과목·교수·시험형식·실라버스) 로드 → ②과거시험 intake(PDF/붙여넣기/경로, 표본크기 확인) → ③시험별 분석(형식·과목커버·문제스타일·사실밀도·반복함정) → ④교차 패턴분석(stable/variable/absent) → ⑤실라버스 결합 예측 → ⑥파일 작성(versioned).
- **3분류 패턴분석(line 74-86)**: **stable**(거의 모든 시험 출현=과목가중·문제스타일·교수 hobby horse), **variable**(일부만=정책에세이·오픈북차이), **absent**(수업엔 있으나 출제無 / 출제됐으나 현 실라버스에 없음).
- **confidence discipline(line 30-35)**: 패턴분석=확신, **상위 예측=`[UNCERTAIN]` 기본**. 표본 1~2개면 "noise"로 명시. 신임교수(표본0)면 예측불가→실라버스 fallback.
- **데이터 흐름(Integration, line 148-153)**: forecast 가중치 → outline-builder 깊이결정 / flashcards 생성량 / irac-practice 주제선정으로 **하방 전파**.
- **출력 구조(line 109-141)**: 과목가중표(과거가중·현실라버스여부·예측가중) + 문제스타일 예측 + hobby horses + "출제뜸한 주제" + 학습강조(Heavy 40-50%·Moderate 30-40%·Sanity 10-20%).
- **방어선**: 헤더 `STUDY NOTES — NOT LEGAL ADVICE` 강제(line 90, 출력의 정체성), "예측 아닌 가중" 반복 프레이밍, "전부 공부 대체 아님"(line 163).

### 1.2 study-plan (학습 계획)
- **라우팅 4모드(line 16-20)**: `--build`(신규)/`--update`(session_history 재독→우선순위·시간 조정)/`--status`(오늘·이번주·점수추세·뒤처짐)/`--cram`(80/20 고수율+일일 MBE볼륨+마지막 2-3일 taper).
- **입력 게이트(Step2, line 66-87) — 한 번에 하나씩, 대기**: 시험일·과목·강/약과목·주당가능시간·**생활맥락 강제확인**(직업·가족·통근…→실현가능성 sanity check)·학습방법 multi-select·주당 휴식일.
- **생활맥락 sanity check(line 74-84)**: 학생이 시간 말하면 "그 외 주간 일정 뭐냐"를 강제로 묻고 "현실적/빠듯/지속불가" 판정. 낮춘 수치를 쓰고 `confidence_flags`에 기록. **"못 따르는 계획은 가벼운 계획보다 나쁘다"**.
- **prep-course 보충 vs 대체(Step2.5, line 88-108)**: Barbri/Themis/Kaplan 사용자면 "두 커리큘럼 병행 금지" — **supplement(약점 드릴만 얹기) / replace(전면 재구축)** 택1을 강제(`prep_course_mode` yaml 기록).
- **3단계 phase(line 113-120)**: learning(60%, 아웃라인+플래시+신규MBE) → drilling(30%, MBE볼륨+에세이+시뮬) → review(10%, 약점서브토픽+풀모의). **약점과목 ~2배 시간**.
- **cram(<4주, line 121-126)**: 80/20 — 빈출 MBE과목(Civ Pro·Evidence·Con Law·Contracts)에 집중, 좁은과목 최소커버, **마지막 2-3일 taper**("밤샘 크램은 점수 더 떨어진다 — real").
- **데이터 흐름·적응(line 210-228)**: 각 하위스킬(session/flashcards/drill/irac)이 끝나면 `session_history`에 append(date·subject·type·score·weak_subtopics). `--update` 시 저점수 과목 priority·weekly_hours 승격, 약점서브토픽 다음세션 플래그, 뒤처지면 압축/고지, 앞서면 약점심화 개방.
- **yaml 스키마(line 131-187)**: plan_type/exam_date/weeks_to_exam/hours_per_week/mode/phases[]/subjects{priority,weekly_hours,methods}/schedule[](date·sessions[])/session_history[]. **단일 파일에 계획+일별스케줄+이력 통합.**

### 1.3 outline-builder (아웃라인=목차 빌더)
- **하드룰 "내가 안 써준다"(line 24-50)**: 학습모드 스킬. **스캐폴드(주제트리·서브헤딩·case slot·예외 placeholder)만 생성**, 룰/판시/분석은 학생이 채움. "이 섹션 그냥 써줘" 요청에 **거부 + 이유설명 + scaffold/source-extract 2옵션 제시**(line 42-50).
  - 예외 1: **확장(extending)** 시 학생이 붙인 판례·노트 텍스트에서 추출(=내가 쓰는 게 아니라 학생이 준 것 포맷팅).
  - 예외 2(narrow carve-out, line 61-70): 학생이 말한 룰이 **학생 자신의 업로드 자료와 모순**되면, 정답 채우지 말고 **"네가 [위치]에 쓴 것과 다르다, 인용=[원문] 어느 게 맞냐"**고 충돌만 표면화.
- **confidence·provenance(line 52-70)**: "아웃라인=룰 라이브러리. 틀린 룰이 빠진 룰보다 나쁘다(재확인 없이 공부하므로)." 룰마다 provenance 단서 — 학생노트/업로드교재/내지식확신(무마커) / 내지식불확실(`[VERIFY]`·`[UNCERTAIN]`). **기본은 GAP**(`[GAP — fill from class notes]`).
- **3포맷 매칭(line 105-131)**: traditional(I/A/1/a 계층) / rules-only(bar prep식 `- 룰. 판례.`) / flowchart-adjacent(`→ Is element met? YES→…`). 기존 아웃라인 있으면 **구조 정확히 매칭**.
- **GAP 마커(line 134-138)**: `[NEEDS CASES]`·`[CHECK CLASS NOTES]`·`[EXCEPTION UNCLEAR]`.
- **citation check(line 140-142)**: AI생성 인용은 미검증 — 공부 전 Westlaw/CourtListener 등으로 룩업하라("AI 인용은 조작·오인용 가능").
- **drill-me 통합(line 144-146)**: 섹션 빌드 후 "아웃라인 덮고, 이 hypo 풀어봐" — 종이에만 들어갔는지 머리에 들어갔는지 시험.

### 1.4 session (고정 세션)
- **단계(line 13-27)**: ①`$ARGUMENTS` 파싱(과목·N) → ②CLAUDE.md 로드 → ③study-plan.yaml의 `session_history` 읽어 **약점 서브토픽 가중** → ④메서드 라우팅(`--mbe` 기본/`--essay`/`--flashcards`) → ⑤N문항 1개씩, 직후 정오 설명+관할분기 표기 → ⑥결과기록(plan 있으면 session_history, 없으면 session-history.yaml) → ⑦리포트(점수·오답+서브토픽태그·이번주약점·과거대비추세·plan추천).
- **데이터 흐름**: study-plan을 읽고(약점가중) study-plan에 쓴다(결과기록). **session ↔ study-plan 양방향 닫힘.**
- 채점은 **MBE=객관식 정오, essay=루브릭**(별 skill 위임 bar-prep-questions).

---

## 2. 우리보다 나은 점 (구체)

### N1. **시험경향 역분석(exam-forecast)이 우리에 통째로 없다** [최대 격차]
- 우리: daily-drill·weekly-review·SRS는 "오늘 뭘 풀고 약점 어디냐"는 있으나, **"이 시험(내신/변시)이 무엇을 어떤 비중·어떤 함정으로 내왔나"**의 역분석 모듈이 부재. CLAUDE.md #19~#20·#50 닫힌루프에 '약점→목차'는 있으나 **출제경향→목차 가중**은 없다.
- 그쪽 우월점: ①**stable/variable/absent 3분류**로 과거시험을 정량화(과목가중표) ②교수 hobby horse·반복함정을 명시 추출 ③**가중치를 outline 깊이·카드 생성량·드릴 주제로 하방 전파**(Integration). ④"예측 아닌 가중" + `[UNCERTAIN]` 규율로 과신 차단.
- 우리 적용가치: 우리는 기출/빈출 라벨을 #22로 엄격제한(소스표지 있을때만)하는데, exam-forecast는 **"내가 가진 N개 과거시험"이라는 명시 소스**에서만 패턴을 뽑아 #1·#22와 충돌 없이 경향분석을 할 길을 보여준다. 변시·내신 역산(srs_scheduler `--add-exam` 다중타깃, daily-drill line 155)에 **출제가중 입력**을 더하면 D-day 페이싱이 "남은 시간 분배"에서 "기대출제 가중 분배"로 격상.

### N2. **단일 plan 파일에 계획+일별스케줄+session_history 통합·적응(study-plan)**
- 우리: 계획·진도·약점·이력이 **분산** — progress.json(수동, #19-B), srs_log.json, drill_log.jsonl, learning.json weak_points, 진도_현황.json, 보드 localStorage. daily-drill가 매일 build_session으로 조합하지만 **"시험까지 N주, 어느 phase, 오늘 어느 과목"의 장기 계획 레이어가 없다**(daily-drill는 '오늘'만).
- 그쪽 우월점: ①**weeks_to_exam 역산 → learning/drilling/review 3 phase 자동 분할** ②약점 2배 가중을 weekly_hours로 명시 ③session 결과가 session_history에 누적되면 `--update`가 **저점수 과목 priority 자동 승격**(우리 SRS는 항목단위 간격조정은 하나 '과목 우선순위·주당시간 재배분'은 없음).
- 우리 적용가치: 우리 **시험D-day(다중타깃 srs_scheduler)** 위에 **phase 레이어**를 얹으면(예: 시험 8주전=learning, 3주전=drilling, 1주전=review) daily-drill의 2트랙 비중을 phase가 자동 조절(learning기엔 진도트랙 우세, review기엔 복습·약점트랙 우세). 현재 daily-drill는 회독수(0 vs ≥1)로만 트랙을 가르는데, **phase × 회독** 2축으로 정밀화 가능.

### N3. **생활맥락 강제 sanity check + prep-course 보충/대체 게이트(study-plan)**
- 우리: 계획 현실성·과부하 방지 장치가 약함. weekly-review가 페이싱을 보나, "주당 N시간 말했는데 직업·가족 감안하면 지속가능한가"를 **강제로 되묻는 게이트**가 없다.
- 그쪽 우월점: ①시간 입력 후 **생활부하를 한 문항씩 강제 질의** → 낮춘 수치를 채택하고 `confidence_flags` 기록 ②"못 따르는 계획은 더 나쁘다" 원칙 ③prep-course 사용자에게 **"두 커리큘럼 병행 금지, 보충 or 대체 택1"**. 우리 학생도 학원 강의(강성민·송영곤 등) + 자체 카드/위키 **이중 부담**이 있어 동일 함정 — supplement/replace 게이트는 우리에 바로 이식 가능.

### N4. **"내가 안 써준다" 학습모드 하드룰 + GAP/provenance(outline-builder)**
- 우리: study-notes·law-note-supplement는 **노트를 채워주는** 방향(원문보존·판례추가·요건채움). socratic만 "안 알려주고 질문"인데, **아웃라인(목차) 빌드 단계에서 'AI가 룰을 채우면 학습실패'라는 거부 하드룰**은 우리에 명문화 안 됨.
- 그쪽 우월점: ①**scaffold만 생성, 룰은 학생이** + 거부 시 2옵션(scaffold/source-extract) ②모든 룰에 provenance 단서(학생노트/업로드/AI확신/`[VERIFY]`) ③**narrow carve-out**: 학생의 룰이 학생 자신의 자료와 모순될 때만 충돌 표면화(정답은 안 줌) ④`[GAP — fill from class notes]` = 빈칸이 올바른 답. "틀린 룰이 빠진 룰보다 나쁘다."
- 우리 적용가치: 우리 #1·#2·#13(소스근거·미확인보류·생성후검증)·#21(소크라틱)과 **사상 동일**이나, outline-builder는 이를 **"GAP 마커를 산출물에 박는다"**는 구체 메커니즘으로 구현. 우리 카드/위키에 **`[GAP]`·provenance 단서**(학생노트 vs AI추정)를 명시 필드로 넣으면 #2 보류가 산출물에 가시화된다(현재 우리는 '검증' frontmatter는 있으나 본문 라인단위 provenance는 약함).

### N5. **versioned 산출물 + 하방 전파 명시(exam-forecast Integration)**
- 그쪽: forecast를 `forecast-[YYYY-MM-DD].md`로 버전관리하고 새 과거시험 입수 시 재실행·append. 그리고 forecast→outline→flashcards→irac로 **가중치가 흐르는 의존선을 SKILL에 명시**.
- 우리: 닫힌루프(#50)는 있으나 '시험경향 가중'이라는 흐름 키가 없다. forecast 같은 **가중치 산출물을 닫힌루프의 한 노드로** 추가하면 "목차→쟁점→카드→드릴→보드→약점→목차"에 **"기출경향→목차 가중"** 진입점이 생긴다.

### (역으로) 우리가 그쪽보다 나은 점 — 균형 기록
- **전수 카드화·누락0 게이트**: 우리 cardaudit(1867건 전수감사, 집계표)·atom 인벤토리 추적은 그쪽에 전혀 없다(그쪽 flashcards는 forecast-heavy 주제만 생성, 의도적 선별).
- **2트랙 회독연동 드릴 + 사례 패널채점**: daily-drill 진도/복습 2트랙 + case-answer-review 독립채점관 N명 다수결·약점합집합은 session(단순 N문항 채점)보다 정교.
- **소스근거 강제·법령 자동검증**: law_api.py verify-text 일괄대조(#13·#45-C)는 그쪽 "citation check(사람이 직접 룩업하라)" 수동 권고보다 강제력이 높다.
- **원문보존 위키(#50-B)**: 695논점 원문 전체보존+백링크는 그쪽 outline(요약 스캐폴드)과 지향이 다름 — 우리는 라이브러리, 그쪽은 학습용 빈 골격.

---

## 3. IRAC + 한국 요건사실론 통합에 주는 시사

> 이 4스킬은 미국 bar/law-school용이라 **IRAC·MBE·MEE 전제**다. 한국 요건사실론(요건사실·주장증명책임·청구원인/항변)은 직접 다루지 않으나, **구조 설계 사상**에서 시사가 있다.

### S1. study-plan의 phase·약점가중 사상을 **쟁점유형(청구원인/항변)별 가중**으로 번역
- 그쪽은 과목(Evidence·Contracts)·서브토픽 단위로 약점가중. 우리 요건사실론은 **청구원인 요건사실 / 항변 요건사실 / 재항변**이 학습·채점 단위(case-answer-review '과목별 구조 기준' 민법 다툼형 = #32 원고|피고 2열 + IRAC #24).
- 시사: session/study-plan의 `weak_subtopics`를 우리는 **`weak_요건사실`**(예: "동시이행항변권 항변요건", "사해행위 객관적요건")로 잡아야 한다. daily-drill 약점 태깅(`주제::`)을 **요건사실 슬롯 단위**로 세분하면 SRS 재순환이 "권리남용 요건"이 아니라 "권리남용 **주관적 요건(가해의사)**"까지 내려간다.

### S2. outline-builder flowchart 포맷 → **요건사실 충족 트리**로 채택
- 그쪽 flowchart-adjacent(`Is element met? YES→…`)는 요건사실론과 궁합이 좋다. 우리 위키/카드에 **청구원인 요건 → (충족?) → 항변 → (성립?) → 재항변** 트리를 outline 포맷으로 도입하면, IRAC의 R(룰)을 **요건사실 체크리스트**로 구조화 가능.
- 단, 우리 #37(외국어 금지)·#34(판례 원문표현)·#35(백링크) 준수: 트리 노드는 한국어 요건명 + 근거조문 백링크.

### S3. **주장증명책임**을 provenance·confidence 축으로 흡수
- outline-builder의 provenance 단서(학생노트/AI확신/`[VERIFY]`)는 "이 룰의 출처가 무엇이냐"를 라인단위로 박는다. 요건사실론에선 이와 별개로 **"이 요건사실의 증명책임이 누구에게 있냐(원고/피고)"**가 핵심 메타데이터. → 우리 카드 SCHEMA(연구_카드구조.md §5)에 **`증명책임:: 원고/피고`** 필드를 추가하면, 요건세트 카드가 "요건 N개"뿐 아니라 "각 요건의 증명책임 귀속"까지 인출 대상으로 만든다. (침해부당이득 요건사실표가 이미 4열에 증명책임 판례를 담음 — 연구_카드구조.md line 54.)

### S4. exam-forecast의 함정유형(trap) 추출 → **요건사실 함정 카탈로그**
- 그쪽은 "교수가 깨끗한 사실관계에 관할쟁점을 숨긴다"식 함정을 stable 패턴으로 추출. 한국 사례형의 대응물 = **숨은 항변·간과하기 쉬운 요건사실·반대 결론 함정**(case-answer-review 결론캡, line 147). exam-forecast 사상으로 **기출에서 반복되는 요건사실 함정**(예: "동시이행 항변을 빠뜨리게 만드는 사실배치")을 카탈로그화하면, 포섭 진단(case-answer-review 포섭 4슬롯·E1~E3)과 결합해 **약점→함정유형→재출제** 루프가 닫힌다.

### S5. case-answer-review와의 정합 — 이미 우리가 더 정교
- 우리 case-answer-review는 IRAC #24 + #32 2열 + **과목별 구조 기준**(민법 다툼형/검토형, 형법 구성요건→위법성→책임·죄수, 헌법 적법요건→본안)을 이미 가짐 — 그쪽 session/study-plan보다 한국법 구조 반영이 앞선다. 4스킬에서 **가져올 것은 채점구조가 아니라 '계획·예측·아웃라인' 레이어**다.

---

## 4. 사례형(CASE)을 전부 카드화해야 하는가 — 시사

### 이 레포는 사례를 어떻게 다루나 (정독 결과)
- **사례를 '카드'로 만들지 않는다.** 사례는 **session의 essay 메서드**(line 18-19 `--essay`)와 **irac-practice**(별 스킬, exam-forecast Integration line 154)로 **그때그때 출제·채점**되고, study-plan에는 **결과(score·weak_subtopics)만 session_history에 기록**된다(study-plan line 213-221). 즉 **사례 본문은 영속 카드가 아니라 일회성 세션 산출물 + 약점 메타데이터**로 환원.
- flashcards는 **forecast-heavy 주제만 의도적 생성**(exam-forecast line 152) — 전수 카드화 사상 자체가 없다.
- outline-builder의 drill-me(line 144)도 hypo를 즉석 출제할 뿐 **카드로 적립하지 않는다**.
- → **이 레포의 입장: 사례=훈련 이벤트, 카드=룰/요건/판례 같은 atomic 지식. 사례를 카드로 박제하지 않고, 사례에서 나온 '약점(요건·쟁점)'만 영속화한다.**

### 우리 시스템 대조
- 우리 02-card 프롬프트는 사례형을 **`사례형_schema`로 원문보존(비분해)** 하되 far-transfer 위해 **종합/IRAC 카드 1장 병행 권장**(연구_카드구조.md line 66-67·172). cardaudit는 사례형도 atom으로 잡아 누락 감사.
- 즉 우리는 "사례도 카드(원문보존형) + 종합카드"인데, **이 레포는 "사례는 카드 아님, 약점만 적립"**.

### 시사 (전수 카드화 정책에 주는 함의)
- **S6. 사례형은 '전수 카드화'의 대상이 아닐 수 있다 — 약점추출형이 더 효율적.**
  - 그쪽 모델의 강점: 사례는 매번 새 사실관계로 와도 **테스트 항목은 동일 요건/쟁점**이므로, **사례 본문 1882건을 카드로 박제하는 것보다 사례→약점요건 추출→그 요건의 룰/포섭 카드만 영속화**가 retention·far-transfer에 유리(case-answer-review 포섭 페이딩 Lv1~4, line 183과 동일 사상 — 사례는 페이딩 훈련 재료이지 암기 대상이 아니다).
  - 우리 현황과의 긴장: 우리 cardaudit은 **사례형 누락도 '누락'으로 집계**(전수 카드화 압박). 그러나 위 사상대로면 **사례형 atom은 "카드화 필수"가 아니라 "약점연동 필수"**로 정책을 분기해야 한다. → 연구_카드구조.md §5의 `사례형` card_type을 **"원문보존 + 종합카드"는 유지하되, '사례 본문 자체의 빈칸/룰 카드 전수화'는 면제**하고, 대신 **사례→요건사실 약점 매핑(case-answer-review 연동)을 게이트**로 두는 것이 정합적.
- **S7. 사례 카드화 정책 2분기 제안(소스 사상 기반)**:
  1. **룰/요건/판례/조문/표** = 전수 카드화 대상(누락0 게이트 유지 — 연구_카드구조.md R1~R4).
  2. **사례형(CASE)** = 전수 카드화 **비대상**. 대신 ①원문보존(위키·교재) ②종합/IRAC 카드 1장(far-transfer 닻) ③**사례→약점 요건사실 추출 → 그 요건 카드의 SRS 가중**(daily-drill 복습트랙·case-answer-review 약점연동). 사례 본문의 모든 문장을 카드로 쪼개지 않는다.
- **주의(미확인)**: 이 레포는 한국식 '사례집(문제+모범답안)' 대량 보유 전제가 아니라 '교수 hypo 즉석출제' 전제다. 우리는 사례집 책(case_problem_answer_index.json)이 실재하므로, **사례집 문제↔모범답안 링크(우리 강점)는 유지**하되 그것을 카드가 아닌 **드릴 출제 인덱스**로 두는 현 daily-drill 설계(line 108·180)가 이 레포 사상과 이미 정합한다. 즉 **우리는 이미 부분적으로 "사례=출제재료, 카드아님"을 하고 있다** — 다만 cardaudit의 사례 누락 집계가 정책과 어긋나므로 그 부분만 교정 대상.

---

## 5. 종합 권고 (우선순위)

1. **exam-forecast 도입(최우선 격차 N1)**: 우리에 없는 모듈. 내신/변시 기출(소스 보유분만, #22 준수)을 stable/variable/absent로 분석하는 스킬을 신설하고, 산출 가중치를 **#50 닫힌루프의 진입점("기출경향→목차 가중")**으로 연결. `[UNCERTAIN]`·"예측아님" 규율 그대로 채택.
2. **study-plan phase 레이어 + 생활맥락 게이트(N2·N3)**: 우리 다중타깃 D-day(srs_scheduler `--add-exam`) 위에 learning/drilling/review phase를 얹어 daily-drill 2트랙 비중을 phase가 조절. 생활맥락 강제확인 + 학원/자체 이중부담 supplement/replace 게이트 이식.
3. **provenance·GAP 마커 명문화(N4)**: 카드/위키 본문에 라인단위 provenance 단서(`[GAP]`·학생노트 vs AI추정)를 #2 보류의 가시화로 도입.
4. **요건사실론 흡수(S1~S4)**: weak 태깅을 요건사실 슬롯 단위로 세분 + 카드 SCHEMA에 `증명책임::` 필드 + outline flowchart를 요건충족 트리로.
5. **사례형 카드화 정책 분기(S6·S7)**: 사례형을 전수 카드화 비대상으로 명시, '약점요건 추출 연동'을 게이트로. cardaudit의 사례 누락 집계를 이 정책에 맞춰 교정(검증자 권한·보고만, 자동수정 금지 #45-C).

---

## 6. 미확인 / 한계
- 4스킬이 참조하는 하위스킬(**flashcards·bar-prep-questions·irac-practice·socratic-drill**)의 SKILL.md는 본 클러스터(A3) 범위 밖 — 정독 안 함. 사례 카드화 사상(§4)은 exam-forecast/session의 **참조 서술**(flashcards가 forecast-heavy만 생성, session essay 결과만 기록)에 근거한 추론이며, flashcards 스킬 본문 미확인.
- 이 레포의 CLAUDE.md(`~/.claude/plugins/config/claude-for-legal/law-student/CLAUDE.md`)·`## Outputs`·`next-steps decision tree` 본문 미정독(4 SKILL이 참조만 함) — 헤더/출력규약의 전모는 미확인.
- study-plan.yaml·forecast.md의 실제 산출 샘플 부재(스킬 명세만 존재) — 실동작 미검증.
- 한국 요건사실론 통합(§3)은 우리 case-answer-review·#24·#32 기존 구조와 4스킬 사상의 **접합 제안**이며, 실제 카드/드릴에 반영된 바 없는 설계안.

## 7. 인용 출처
- 대상스킬(정독): `claude-for-legal/law-student/skills/exam-forecast/SKILL.md`, `study-plan/SKILL.md`, `outline-builder/SKILL.md`, `session/SKILL.md` (scratchpad 경로)
- 우리 대조: `.agent/state/연구_카드구조.md`, `.agent/state/cardaudit_집계.md`, `.agent/skills/daily-drill/SKILL.md`, `sync/_meta/연구종합_카드+진도보드_2026-06-28.md`, `.agent/skills/case-answer-review/SKILL.md`, `E:\법학볼트\CLAUDE.md`(#19·#20·#22·#24·#32·#45-C·#50)
