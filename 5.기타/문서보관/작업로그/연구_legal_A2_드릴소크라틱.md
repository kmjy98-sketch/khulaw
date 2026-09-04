---
type: 연구
주제: 클러스터 A2 — 드릴·소크라틱·콜드콜·변시문제 생성/채점 (claude-for-legal/law-student 대조)
작성: 2026-06-28
근거원칙: CLAUDE.md #1(소스근거)·#2(미확인 보류) — 읽기전용 조사
대상레포: claude-for-legal/law-student/skills/{socratic-drill, cold-call-prep, bar-prep-questions}/SKILL.md
대조시스템: E:\법학볼트 (2트랙 daily-drill + case-answer-review + 카드 v37 + 진도보드 닫힌루프)
---

# 연구 A2 — 드릴·소크라틱·콜드콜·변시문제

> 목적: claude-for-legal 학생용 3스킬(소크라틱 드릴 / 콜드콜 대비 / 변시(bar) 문제 생성·채점)의 출제·소크라틱·채점 기법을 정독하고, 우리 2트랙 드릴(daily-drill)·사례채점(case-answer-review)·카드구조와 대조한다. 모든 단정에 파일·줄 인용. 못 본 것은 '미확인'.

---

## 0. 세 스킬 한눈 요약 (근거: 각 SKILL.md)

| 스킬 | 한 줄 정체 | 핵심 동작 | 우리 대응물 |
|---|---|---|---|
| socratic-drill | "묻고 답하게 하고 반박한다. 답을 먼저 주지 않는다." | 룰진술형 질문→답→반박/좁히기, 정답 비공개(socratic-drill `SKILL.md` line 14-16, 39-79) | socratic.md(개념이해) / daily-drill은 정답키 선공개형 |
| cold-call-prep | 교수 콜드콜 예상문항 6-10개를 카테고리별로 예측→소크라틱 드릴 | 자료식별→문항예측(Facts/Holding/Reasoning/Application/Policy)→드릴→사후요약(강/약/누락)(cold-call-prep `SKILL.md` line 13-18, 57-120) | 우리에 직접 대응물 없음(콜드콜·발제대비 부재) |
| bar-prep-questions | 변시(MBE/essay)를 약점·관할별로 출제·채점, 미스 패턴 추적 | 시험유형 게이트→관할분기→출제(약점가중)→채점(왜 오답/오답함정)→세션이력 적재(bar-prep-questions `SKILL.md` line 12-21, 144-183) | daily-drill 선택형 + case-answer-review essay채점 |

세 스킬 공통 골격(3개 모두 동일):
1. **컨텍스트 로드** = `~/.claude/plugins/config/claude-for-legal/law-student/CLAUDE.md`(학습스타일·약점·수업·교수·관할·시험유형) + `study-plan.yaml`(있으면).
2. **real-matter check**(실제 사건 차단): 실명·실주소·실금액·실마감이 보이면 출제 중단하고 "법률조언 불가" 안내(socratic-drill line 20-26, cold-call line 23-28, bar-prep line 26-31). — **우리에 없는 안전레일**.
3. **confidence discipline**: 불확실한 룰은 `[UNCERTAIN]`/`[VERIFY]` 인라인 태그 + "prep course로 검증하라". 발명 금지(bar-prep line 128-136, cold-call line 37-40).

---

## 1. 각 스킬의 핵심 기법·구조 (단계·IRAC/요건·데이터흐름)

### 1.1 socratic-drill — '답 안 주기'를 메커니즘화

**단계(line 40-79):**
- Step1 토픽 선정: 사용자 지정 or `CLAUDE.md` 약점에서. **"피하는 과목이 곧 드릴 대상"**(line 42).
- Step2 출제: **룰진술형(rule-statement) 질문 + 항상 hypo 우선**("A가 B에게 금연하면 100불 약속…유효한가?"). "consideration에 대해 말해봐" 같은 추상질문 금지(line 44-48).
- Step3 듣고 반박(이 스킬의 본체): 답의 5가지 상태별 분기 —
  - 맞고 추론 좋음 → 간단 인정 후 **난도 상향**("A가 죽으면? B가 그래도 금연하면 유산에서 받나?")(line 54).
  - 맞지만 추론 허술 → **봐주지 않음**. "'consideration이 있으니까'는 결론이지 이유가 아니다. 무엇이 consideration인가?"(line 56).
  - 틀림 → **고쳐주지 않고** 문제를 드러내는 질문으로(line 58).
  - 추측 → "그건 추측 같다. 룰부터 진술하라"(line 60).
  - 막힘 → 답 주지 말고 **질문을 좁힌다**("계약의 요건부터 나열하라")(line 62).
- **좁은 예외 1개 — 학생 자기자료 모순(line 64-73):** 학생이 진술한 룰이 학생 본인 업로드 노트/아웃라인/케이스브리프와 **모순**될 때만, 답을 채우지 않고 충돌을 들이민다: "그건 당신 노트 [위치]와 안 맞는다 — 당신은 [정확 인용]이라 썼다. 뭐가 맞나?" 내 지식으로 교정 금지, 케이스북 인용 금지, **학생 자기자료만 역인용**.
- Step4 정답 확정: 답 + 추론 둘 다 맞을 때만 짧게 확인(line 76). 여러 라운드 좁혀도 룰을 못 내놓으면 **룰도 적용도 주지 않고** "케이스북/아웃라인 가서 black-letter 보고 와라"로 종료(line 79) — 테이크홈/채점과제에서 답 주기 = 선을 넘음.

**IRAC/요건 처리:** 명시적 IRAC 프레임은 없음. 대신 **"룰 진술 → 적용"의 분리를 강제**(결론을 이유로 착각하는 것을 매번 교정). 요건은 "요건 나열부터"로 환원(line 62).
**데이터흐름:** 입력=CLAUDE.md 약점/자료, 처리=Q&A 루프, 출력=미스 패턴 running note("X와 Y를 계속 혼동 → 그것만 드릴")(line 89-91). **세션 외부 영속 파일 없음**(running note는 대화 내).

### 1.2 cold-call-prep — 예상문항을 카테고리·교수별로 예측

**단계(line 49-120):**
- Step1 자료+교수 식별: 사건명/인용, 교수(CLAUDE.md 수업목록 — 교수별 톤·초점 상이), 과목, 신택터스 내 위치(첫 케이스/좁히는 케이스/반례?)(line 49-54).
- Step2 문항 예측(핵심): 5카테고리로 — **Facts(워밍업) / Holding·rule / Reasoning / Application·hypos / Policy·theory**(line 60-82). + **교수 성향 가중**(hypo형 교수면 Application 가중, policy형이면 Policy 가중, Paper Chase형이면 Facts+Holding)(line 84-87). 6-10문항, **먼저 물을 가능성 순 랭크**(Facts 먼저)(line 89).
- Step3 드릴: socratic-drill 패턴 재사용(line 92-100). 명시적으로 "use the `socratic-drill` pattern"이라고 **스킬 합성**.
- Step4 사후요약(line 102-120): markdown 리포트 — **Strong / Shaky / Missed** 3분류 + "수업 전 다시 볼 것" + "수업에서 나올 법한 top 3".

**confidence discipline(line 37-40):** 케이스 텍스트 주면 confident, 사건명만 주면 케이스 디테일 의존 문항에 `[UNCERTAIN]` 플래그, 케이스 모르면 "신뢰할 read 없다, 텍스트 붙여라" 자백.
**통합(line 122-126):** case-brief(안 했으면 먼저 권유) ↔ socratic-drill(과목 약점이면 넘김) ↔ flashcards(암기할 룰이면 덱 추가 제안). — **스킬 간 라우팅이 명시적**.
**IRAC 처리:** Holding/Reasoning/Application을 분리한 카테고리 자체가 IRAC의 변형(R=Holding·rule, A=Application·hypos). **데이터흐름:** 입력=케이스+교수프로필, 출력=드릴 리포트(파일 영속은 미명시, markdown 블록 제시).

### 1.3 bar-prep-questions — 시험유형·관할 분기가 본체

**단계(line 12-21):**
1. CLAUDE.md(관할·시험포맷·약점·prep course) + study-plan.yaml 로드.
2. **시험유형 게이트(스킵 금지, line 16, 38-60):** NextGen vs 전통 UBE vs 주별 시험을 **반드시 먼저 물음**. NextGen은 신탁·가족법·국제사법·담보거래를 단독과목에서 제외 → "틀린 과목리스트 공부 = 회복불가 실수"라며 NCBE 공식페이지로 검증 요구. 약점과목이 학생 시험에 없으면 플래그하고 (a)스킵 (b)통합문항 속 개념만 (c)그래도 드릴 선택지 제시(line 57-60).
3. **관할 분기(line 61-127):** ① 시험구조(순수UBE/UBE+주별/비UBE주별/NextGen) ② 룰내용(형법 common law vs MPC vs 주법전, 증거 FRE vs CA Evidence Code, 민소 FRCP vs CA, 부부공동재산 주, PR ABA vs CA). **divergence 태그는 과목단위 아닌 룰단위**(line 90-100): 안 갈리는 룰엔 "[CA does not diverge on UCC §2-207]", 갈리는 룰엔 `**Your jurisdiction (X) diverges:**` 블록. 과목 전체에 같은 태그 도배 금지(노이즈).
4. **출제(MBE/essay/mixed, line 186-244):** 약점가중(약점과목 60%), 난도=bar수준(로스쿨 issue-spotter보다 낮게, black-letter 깔끔히 적용)(line 196). 각 문항을 룰바디(`[UBE/majority]`/`[CA-specific]`)로 라벨.
5. **채점:**
   - MBE: 정답 + **왜 각 오답이 틀린지**(왜 A/B/D 아닌지 each) + "기억할 룰" + **citation check 면책문**("AI생성·미검증, prep course와 대조하라")(line 200-216).
   - essay: **이슈스포팅(놓친 것=테이블에 남긴 점수) / 룰진술 정확·완전 / 분석(룰을 사실에 적용했나, 둘 다 나열만 했나) / 조직(IRAC/CRAC)**(line 236-258). **"bar 채점은 brilliance 아닌 competence — 완전·조직·정확하면 합격, brilliant하지만 불완전하면 불합격"**(line 244).
6. **세션이력 적재(line 144-183):** `--session <n>` → study-plan.yaml `session_history`에 date·subject·type·n·score·**weak_subtopics**·jurisdiction_mode를 YAML로 append. 다음 세션이 이 이력으로 약점 서브토픽 가중. **"hearsay 최근 4회 중 3회 미스 = stuck → socratic-drill로 라우팅"**(line 165) — 정량 패턴→스킬 라우팅.

**IRAC/요건 처리:** essay 채점축이 곧 IRAC(Issue스포팅/Rule진술/Analysis=적용/조직). 요건사실론은 없음(미국법). **데이터흐름:** CLAUDE.md+study-plan.yaml → 출제 → 채점 → study-plan.yaml session_history 갱신 → 다음세션 가중. **닫힌 루프가 YAML 1파일로 단순하게 구현됨.**

---

## 2. 우리보다 나은 점 (우리에 없거나 약한 것 — 구체)

### 2.1 [socratic-drill] '정답 비공개 + 5상태 분기 + 자기자료 모순 역인용'
- 우리 daily-drill은 **정답키 선확정→진리값 대조**(SKILL line 55, 66-87)로 **속도 최우선·정답 선공개형**. 인출 후 즉시 정오. 반면 socratic-drill은 **답을 안 주고 좁히는 질문으로 학생이 스스로 도달**하게 한다. 우리는 #21 Socratic First(개념이해)에서 socratic.md로 넘기지만, **드릴 안에서 답을 참는 메커니즘(맞지만 허술→봐주지 않음, 추측→호명, 막힘→좁히기)의 5상태 분기 디테일은 우리 어디에도 명문화돼 있지 않다.**
- **결정적으로 나은 1점 — 자기자료 모순 역인용(line 64-73):** 학생이 말한 룰이 학생 본인 노트와 충돌하면 그 충돌만 들이밀고 답은 안 준다. 우리는 백링크 연결사슬(#35 S4: 백링크→쟁점→카드→약점보드)은 있으나, **'학생 답안 ↔ 학생 자기노트 모순을 출제·드릴 중에 탐지해 들이미는' 동작은 없다.** 우리 695논점 위키 + v37카드를 가지고 있으므로 이 역인용을 **우리가 더 강하게 구현 가능**(자기노트 = 위키 원문/카드).

### 2.2 [cold-call-prep] '문항 카테고리 예측 + 강/약/누락 사후 리포트'
- **5카테고리(Facts/Holding/Reasoning/Application/Policy) × 교수성향 가중**으로 한 케이스에서 출제 스펙트럼을 체계적으로 생성. 우리 daily-drill은 카드유형(rule/cloze/case_law)→문항형(OX/4지/빈칸)으로 변환(SKILL line 60-65)하지만 **'한 논점/판례에서 어떤 인지층위(사실확인 vs 논거 vs 응용 vs 정책)를 물을지' 카테고리 설계가 없다.** 우리 출제는 카드 단위라 인지층위가 카드 종류에 종속됨.
- **사후 리포트 3분류(Strong/Shaky/Missed)**: 우리는 틀린 문항 주제태그를 약점후보로 모으지만(daily-drill line 89-91), **"shaky(맞췄으나 hedge/추측)"를 따로 잡는 층위가 없다** — 우리는 O/X 이진. shaky 포착은 retention 판정에 유용(맞췄어도 불안정한 항목 = 다음 우선).
- **발제·콜드콜 대비라는 용도 자체가 우리에 부재.** 로스쿨 발제/구두 대비 스킬이 없다.

### 2.3 [bar-prep-questions] '시험유형·관할 게이트 + 룰단위 divergence 태그 + 세션이력 자동가중 + citation 면책'
- **(a) 시험유형 게이트(line 38-60):** "틀린 과목리스트 공부 = 회복불가"를 first-class로 막는다. 우리는 **변시/내신 다중타깃**을 SRS 노브로 담지만(daily-drill line 155 `--add-exam`), **'이 시험에 이 과목이 출제되는가(시험범위 게이트)'를 출제 전에 검증하는 단계가 없다.** 변시 선택과목·연차별 범위 차이를 출제 전 게이트로 거르면 우리도 회복불가 실수 방지.
- **(b) 룰단위 divergence 태그(line 90-100):** 같은 쟁점도 **룰마다** "여기선 안 갈림 / 여기선 갈림" 태그. 한국법 대응 = **판례 다수설 vs 소수설 vs 학설대립, 또는 대법원 입장 변경 전후**. 우리 카드는 학설 cloze는 있으나(연구_카드구조 line 169), **"이 룰은 다툼 없음 / 이 룰은 견해대립"을 문항 안 룰단위로 표지하는 규약이 없다.** 도배 방지(과목단위 태그 금지)도 우리에 시사.
- **(c) 세션이력→자동가중→스킬 라우팅(line 144-183):** YAML session_history에 weak_subtopics 적재 → 다음세션 가중 + **"N회 중 M회 미스 = stuck → socratic으로"** 정량 라우팅. 우리는 drill_log.jsonl(line 147)·learning.json·srs_log로 분산 보유하나, **"같은 서브토픽 반복 미스율"을 임계로 스킬을 자동 전환하는 룰이 약하다**(daily-drill은 "2회+ 반복 오답 → SRS 등록"까지, socratic 라우팅 자동화는 없음).
- **(d) citation check 면책문(line 215-216) + confidence 태그(line 128-136):** 모든 MBE 해설에 "AI생성·미검증, prep course 대조" 면책 + 불확실 룰 `[UNCERTAIN]`/`[VERIFY]`. 우리는 law_api.py로 **조문·사건번호를 실제 검증**(daily-drill line 170)하므로 사실검증은 더 강하지만, **"검증 안 된 룰 진술에 인라인 불확실 태그를 붙이는 습관"은 약하다**(우리는 검증 실패 시 '검증보류·출제제외'로 빼버림 — 태그하고 출제하는 중간 옵션 부재).
- **(e) essay 채점 철학 "competence > brilliance"(line 244):** 변시 채점관 관점("완전·조직·정확이면 합격")을 명문화. 우리 case-answer-review는 정교한 가중루브릭(쟁점0.25/키워드0.20/구조0.20/결론0.15/포섭0.20)이 있어 **세밀함은 우리가 앞서나**, "합격선 = competence"라는 **채점 철학·캘리브레이션 한 줄이 우리에 없다**(우리는 점수 중심).

### 2.4 [공통] real-matter check (실제 사건 차단)
- 3스킬 모두 **실명·실금액·실마감 감지 시 출제 중단 + 법률조언 불가 안내.** 우리는 #1 소스근거로 외부지식 출제는 막지만, **"사용자가 실제 자기 사건을 학습질문으로 위장해 가져올 때 차단하는 레일이 없다."** 로스쿨생 사용자 특성상 도입 가치 있음(윤리·안전).

---

## 3. IRAC 기본 + 한국 요건사실론 반영에의 시사

> 세 스킬은 미국법(IRAC/CRAC, MBE/essay)이라 **요건사실·주장증명책임·청구원인/항변 구조는 전무**. 따라서 시사는 "그들의 IRAC 골격에 우리 요건사실론을 어떻게 얹을까"의 형태로만 도출.

### 3.1 essay 채점축(I/R/A/조직)을 요건사실 4슬롯에 매핑
- bar-prep essay 채점은 **Issue스포팅 / Rule진술 정확·완전 / Analysis=룰을 사실에 적용(나열만 하면 감점) / 조직**(line 236-258). 우리 case-answer-review의 **포섭 4슬롯**([요건적시]→[사안의 경우+구체사실]→[법적평가]→[소결], `case-answer-review` SKILL line 182)이 바로 이 "Analysis=적용"을 한국식으로 정밀화한 것. **둘은 같은 골격** → IRAC의 A를 우리 요건사실 포섭 4슬롯으로 치환하면 IRAC↔요건사실론 통합의 표준형이 된다.
- **시사: "Rule진술"을 한국에선 '요건(구성요건/성립요건) 진술'로, "Analysis"를 '요건별 사실대입(주요사실 포섭)'으로 1:1 대응**시키는 명시 매핑표를 만들면, 미국식 IRAC 채점축을 그대로 요건사실 채점에 재사용 가능.

### 3.2 청구원인/항변 = bar에 없는 우리 고유축 → 별도 강제
- bar-prep·socratic·cold-call 어디에도 **주장증명책임 분배, 청구원인-항변-재항변 구조**가 없다(미국 pleading은 다름). 우리 #32 원고|피고 2열 + #24 IRAC은 **그들에 없는 우리 강점**. 따라서 IRAC을 빌리되 **"민법 다툼형엔 IRAC 위에 청구-항변 2열을 덮는다"**(case-answer-review 과목별 구조표 line 154-159)는 현 설계가 옳음 — 외부 스킬에서 차용할 게 아니라 **유지·강화** 대상.
- **시사: 요건사실 = '누가 무엇을 주장·증명해야 하나(증명책임)'를 카드/채점에 first-class 필드로.** 우리 침해부당이득 요건사실표(증명책임 판례, 연구_카드구조 line 54)처럼 **증명책임 귀속을 요건카드의 필수 필드**로 올리면, IRAC의 R을 "요건 + 그 요건의 증명책임자"로 확장 — bar엔 없는 한국 고유 정밀화.

### 3.3 socratic의 '룰진술→적용 분리 강제'를 요건사실 진술 훈련에 차용
- socratic-drill의 핵심 교정("'consideration 있으니까'는 결론이지 이유 아님 — 무엇이 consideration인가", line 56)은 **한국 요건사실 훈련에 그대로**: "'기망행위가 있으니까'(결론) → 어떤 사실이 기망행위 요건을 충족하나(요건+사실)". **요건→사실대입을 못 하고 결론 직행(case-answer-review E2, line 181)을 소크라틱 좁히기로 교정**하는 드릴 모드를 우리 복습트랙에 추가할 근거.

---

## 4. 사례형(CASE)을 전부 카드로 만들어야 하나 — 이 레포의 사례 취급 + 우리 시사

### 4.1 이 레포는 사례(hypo)를 '카드'로 만들지 않는다
- **socratic-drill: hypo는 출제 도구이지 저장물이 아니다.** "A가 B에게 금연하면 100불…"식 hypo를 **즉석 생성·구두 소비**하고 카드로 적재하지 않는다(line 46-54). 미스 패턴만 running note(line 89-91).
- **cold-call-prep: 예측 6-10문항도 카드 아님** — 케이스별 1회성 드릴 + 사후 리포트(line 102-120). 단 **"케이스 룰이 암기대상이면 flashcards 덱에 추가 제안"**(line 126) — 즉 **사례 자체가 아니라 사례에서 추출된 '룰'만 카드화**.
- **bar-prep: MBE 문항·essay 프롬프트도 카드 아님** — 세션 단위 출제·소비, study-plan.yaml에 남는 건 **점수·약점 서브토픽(메타데이터)뿐**(line 170-181). 문항 텍스트를 적재하지 않는다.
- **결론: 세 스킬 모두 "사례/문항 = 일회성 인출 이벤트, 카드 = 사례에서 추출된 룰/약점"으로 분리.** 사례를 카드로 보존하지 않는다.

### 4.2 우리 시사 — "사례형 전부 카드화"는 과잉, '사례→룰/약점 추출 + 사례형 원문보존(비분해)'이 맞다
- 우리 현 설계는 이미 부분적으로 이 방향: 02-card는 **사례형을 분해하지 말고 원문보존**(연구_카드구조 line 66-67, `사례형_schema`) + far-transfer용 종합/IRAC 카드 1장 병행(line 172). daily-drill 복습트랙도 **사례 문제는 책 원문 span을 연결(case_problem_answer_index)하고 카드화하지 않음**(daily-drill line 108).
- **외부 3스킬과 정합 = 우리 방향이 옳다는 방증:** 사례형 문항 전부를 낱장 카드로 쪼개는 것은 (a)far-transfer 손실(연구_카드구조 line 67) (b)일회성 이벤트를 영속 카드로 만드는 비용. **대신 사례에서 ①추출된 룰/판례holding은 카드(전수 카드화 대상) ②약점은 SRS ③사례 원문은 비분해 보존+링크**의 3분리가 외부 베스트프랙티스와 일치.
- **단, 우리만의 보강:** 외부는 약점을 메타데이터(weak_subtopics)로만 남기지만, 우리는 **약점을 쟁점노트 frontmatter에 역기록(daily-drill mark_progress, line 149-154)하고 백링크 연결사슬로 쟁점·카드에 잇는다**(#35 S4). 즉 **"사례형은 카드화 안 하되, 사례에서 나온 약점은 카드/쟁점과 연결"** — 외부보다 한 단계 더 닫힌 루프. 이걸 유지·강화하는 게 맞다.
- **카드화해야 하는 사례의 예외:** cold-call의 "룰이 암기대상이면 덱 추가"(line 126)와 동일하게, **사례에서 도출된 '규범명제(holding·요건·예외)'는 카드, 사례 사실관계·문항 자체는 비카드.** 우리 02-card '사실관계 구체적일 때만 포섭카드'(연구_카드구조 line 166) 규칙이 이미 이 경계를 가짐 → 유지.

---

## 5. 종합 권고 (우리 시스템에 반영할 7가지)

1. **socratic 5상태 분기 + 정답 비공개 모드를 daily-drill 복습트랙(또는 socratic.md)에 명문화** — 현 정답키 선공개형은 진도트랙 속도용으로 유지하되, 복습·약점 항목엔 '답 안 주고 좁히기' 모드 옵션 추가.
2. **자기자료 모순 역인용 도입(우리가 더 강하게 가능)** — 학생 답안 ↔ 우리 695위키/v37카드 충돌을 채점·드릴 중 탐지해 들이밀기(답은 비공개). 백링크 연결사슬(S4) 자산 활용.
3. **출제 인지층위 카테고리(사실확인/논거/응용/정책) 도입** — 카드유형 종속 출제를 보완. 한 논점에서 층위별 출제 스펙트럼 생성.
4. **사후 리포트에 'shaky(맞췄으나 불안정)' 층위 추가** — 현 O/X 이진 → 강/약/누락 3분류로. retention 판정 정밀화.
5. **시험범위 게이트 도입** — 변시 선택과목·연차별 범위를 출제 전 검증(약점과목이 시험범위 밖이면 플래그). SRS 다중타깃과 결합.
6. **룰단위 견해대립 태그 규약** — 카드/문항에 "다툼없음 / 견해대립(다수·소수·판례변경)"을 룰단위로 표지(과목단위 도배 금지). 한국법 학설대립 정밀화.
7. **IRAC R↔요건진술, A↔요건별 사실대입(포섭4슬롯) 1:1 매핑표 + 증명책임을 요건카드 필수필드로** — IRAC 골격에 요건사실론을 얹는 표준형. + competence>brilliance 채점 캘리브레이션 한 줄 추가.

추가로 검토할 안전레일: **real-matter check(실제 사건 차단)** — 로스쿨생 사용자 윤리·안전 레일로 도입 가치.

---

## 6. 미확인 / 한계
- 외부 레포의 `CLAUDE.md`(학습프로필)·`study-plan.yaml`·`case-brief`/`flashcards`/`study-plan` 스킬 본문은 미정독(이 3개 SKILL.md만 정독 지시). 데이터흐름 일부는 SKILL.md 인용 기반 추정.
- 우리 socratic.md 본문 미정독(이번 범위 밖) — daily-drill·case-answer-review와의 정확한 경계는 SKILL 인용 기준.
- 외부 스킬이 실제로 파일 영속(리포트 저장)을 하는지는 SKILL.md에 markdown 블록만 제시 — 저장 경로 명시 없음(cold-call은 미명시, bar-prep만 study-plan.yaml 명시).
- 요건사실론 통합·증명책임 필드화는 설계 제안이며 현 빌더(build_v37_apkg.py)·카드 schema 미지원 — 도입 시 보강 필요(연구_카드구조 line 198 동일 한계).

## 7. 인용 출처
- 외부: `claude-for-legal/law-student/skills/socratic-drill/SKILL.md`, `.../cold-call-prep/SKILL.md`, `.../bar-prep-questions/SKILL.md`
- 우리: `.agent/skills/daily-drill/SKILL.md`, `.agent/skills/case-answer-review/SKILL.md`, `.agent/state/연구_카드구조.md`, `.agent/state/cardaudit_집계.md`, `sync/_meta/연구종합_카드+진도보드_2026-06-28.md`, `CLAUDE.md`(#21·#24·#32·#35 S4·#50)
