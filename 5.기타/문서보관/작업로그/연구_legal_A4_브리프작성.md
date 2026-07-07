---
type: 연구
주제: claude-for-legal/law-student 스킬 4종(case-brief·legal-writing·cold-start-interview·customize) 정독·대조
클러스터: A4_브리프작성
작성: 2026-06-28
근거원칙: CLAUDE.md #1(소스근거)·#2(미확인 보류)·#7(COT 비노출)
상태: 초안(읽기전용 조사 결과)
대조대상: E:\법학볼트 (카드구조 연구·카드감사·daily-drill·case-answer-review·연구종합 보드)
---

# 연구 — claude-for-legal 4스킬 대조 (브리프·법문서작성·초기인터뷰·개인화)

> 목적: 외부 레포(claude-for-legal/law-student)의 4개 스킬을 정독하고, 우리 법학볼트 시스템(판례 백링크·사례채점·개인화)과 대조해 (1)핵심기법 (2)우리보다 나은 점 (3)IRAC+한국 요건사실론 통합 시사 (4)사례형 전수카드화 시사를 추출.
> 모든 인용은 SKILL.md 라인 근거. 추측 금지(#2).

---

## 0. 정독한 4스킬 출처

- `…/claude-for-legal/law-student/skills/case-brief/SKILL.md` (109줄)
- `…/legal-writing/SKILL.md` (168줄)
- `…/cold-start-interview/SKILL.md` (309줄)
- `…/customize/SKILL.md` (89줄)

---

## 1. 각 스킬의 핵심 기법·구조

### 1.1 case-brief (판례 브리프)

**구조(단계)**: ①config(`CLAUDE.md`) 로드 → 학생 브리프 선호 형식 파악 → ②워크플로 적용 → ③학생 형식으로 브리프(드릴모드면 holding 먼저 말하게)(line 12-14).

**핵심 기법**:
- **Confidence discipline(신뢰등급)**(line 22-30): 입력에 따라 신뢰도 차등. ①판례 원문 붙여넣음=원문에서 추출, 확신 / ②사건명만 줌=지식기반 브리프, 가치 낮음, 불확실한 줄마다 `[UNCERTAIN: 구체사유]` 플래그 + 실제 판례 대조 강권 / ③유명하나 다툼있는 해석=다수설+`[VERIFY]`. "내 추측 + 학생 선의로 만든 브리프는 브리프 없느니만 못하다"(line 30).
- **"don't brief it for me" 하드룰**(line 36-51): **모든 모드의 기본값은 학생의 브리프 작성을 '스캐폴딩'하는 것이지 대신 써주는 것이 아니다.** 읽은 내용(사실·쟁점·holding)을 학생에게 먼저 물음 → 선호형식 빈 템플릿 제공 → 빈약한 섹션에 핵심질문 → 학생이 원문 붙이면 법원 표현 verbatim 추출(이건 대신쓰기 아님). 거부: 사건명만으로 풀 브리프 작성 / "요약해줘". 예외 1개: 학생이 "3번 읽었고 holding 표현만 막혔다, 시작문장만" 명시 override 시 `[VERIFY]` 단 최소 시작문장 + 재작성 유도.
- **Mode fork**(line 54-62): **drill-me**=holding 한 문장 먼저 말하게, 못하면 다시 읽으라; **explain-to-me**=같은 스캐폴드 + 부드러운 톤, "좋은 holding은 yes/no + rule 한 문장" 같은 구조 힌트, 그래도 내용은 학생이 쓴다. ("explain-to-me ≠ 대신 써줘".)
- **데이터 흐름**: config(format/depth/learning style) → 브리프 템플릿 → (모드별) 스캐폴드 질문. 출력 끝에 **Citation check** 고정문(AI 생성 cite는 미검증, Westlaw/CourtListener 등에서 확인)(line 95).
- **Depth calibration**(line 98-102): 1L=풀 브리프, 3L/bar=rule-only. config 기반.

**브리프 템플릿 슬롯**(line 70-96): Case Name/cite · Court · Facts(holding에 영향준 사실만) · Procedural posture · Issue(yes/no 질문) · Holding(1문장 yes/no+rule) · Reasoning(법원 논리=법이 있는 곳) · Rule(아웃라인에 넣을 portable takeaway) · Notes(반대의견·구별·교수 강조).

### 1.2 legal-writing (법문서작성 피드백)

**구조(단계)**(line 12-19): config 로드 → 프레임워크 적용 → 초안 통독(top-to-bottom, 짧으면 2회) → 구조유형 식별(memo/brief/paper/essay) → 구조화 피드백(구조 먼저 → 분석깊이 → 명료성 → top3 fix) → 불확실 substantive call에 `[VERIFY]` → 재작성 요청은 우아하게 거부 → tracker.md에 append(패턴 검출용).

**핵심 기법**:
- **하드룰: 절대 재작성 안 함(no rewriting ever)**(line 26-34). 구조 피드백이 산출물. 예시 표현(labeled example phrasing)은 세션당 1~2개만, "write yours—don't copy" 라벨 필수, 학생의 실제 substantive 주제가 아닌 일반형으로만(line 164: 자동차 사고 과실 쓰는 학생에겐 "피고의 breach" 예시도 너무 가까움 → placeholder로 "rule-application mapping"만 보여줌).
- **Confidence discipline 3분**(line 36-39): 구조 피드백(조직·IRAC/CRAC·topic sentence·전환·간결·능동태)=확신 / 내용 피드백(rule 정확성·case 적용성)=`[VERIFY]` / cite form(Bluebook·ALWD)=흔한 형식은 알되 edge case `[VERIFY]`.
- **구조유형 식별**(line 54-60): office memo(QP/BA/Facts/Discussion/Conclusion) · brief(TOA/Intro/SoF/Argument/Conclusion, 옹호) · paper · exam essay. 유형 명시("memo처럼 읽히는 brief는 나쁜 brief").
- **Top-down 피드백 순서**(line 62-119): 구조(망가졌으면 먼저) → 분석깊이(rule statement·application·counterargument·구체적 gap) → 명료성(결론선행 문장·수동태 남용·장황·cite form) → top3 fix(우선순위) → 예시 1개(do not copy).
- **재작성 요청 거부 스크립트**(line 127-129) + 대안 3종(타깃 구조피드백 / labeled 예시 / socratic-drill 라우팅).
- **패턴 추적(학습)**(line 137-149): `writing-feedback/[student]/tracker.md`에 세션 요약 append → 3세션+ 후 패턴 표면화("thesis를 계속 묻는다", "counterargument 분석이 약하다").

### 1.3 cold-start-interview (초기 인터뷰·자료 인테이크)

**구조(단계)**(line 14-19): config 체크(populated면 --redo 없이는 덮어쓰기 확인) → 인터뷰 워크플로 → Part0(누가/뭐 연결)·Part1(어디)·Part2(어떻게 학습:drill-me vs explain-to-me)·Part3(강/약/회피)·Part4(자료 인테이크 10~20개 목표) → 재독(모순·드리프트·gap) → config 작성(`## Who's using this`·`## Available integrations`, 10개 미만이면 `LIMITED DATA` 플래그) → 확인.

**핵심 기법**:
- **개인화의 본질**: "다른 cold-start는 조직을 배우지만 이건 너를 배운다 — 어떻게 공부하고, 뭘 피하고, 밀어붙여지길 원하는지 vs 스캐폴딩되길 원하는지"(line 28-30).
- **drill-me vs explain-to-me 디폴트**(line 181-191): 이 한 질문이 socratic-drill·irac-practice·cold-call-prep의 동작을 가른다. drill-me=묻고 밀어붙임·답 안 줌 / explain-to-me=먼저 명확히 설명 후 이해확인. 세션별 override 가능, 디폴트가 중요.
- **Pause/Resume + 부분저장**(line 96): "pause/stop" 시 `<!-- SETUP PAUSED AT: [section] -->` 주석 + `[PENDING]` 마커로 부분 config 저장, 재실행 시 이어받음. **silent gap 금지**(line 95: 모든 placeholder는 학생이 의도적으로 건너뛴 것이어야).
- **Templates-first 인테이크**(line 107): 기존 아웃라인 업로드하면 읽고 형식 매칭(설명 요구 대신). "이미 써둔 걸 다시 타이핑시키는 인터뷰어는 인터뷰어의 첫 직무에 실패"(line 88).
- **Connector 정직성(✓는 실제 호출 성공 시만)**(line 23, 150-163): `.mcp.json` 선언만으론 ✓ 금지. 테스트성공=✓ / 못함=⚪("configured but not verified") / 없음=✗ + 연결법 + manual fallback.
- **LIMITED DATA 플래그**(line 248): 10개 미만 자료면 상단 경고 — "outline builder가 네 형식을 모름, exam forecast 시그널 얇음, IRAC grader가 네 작문패턴 모름". 3개 이하=강한 caveat.
- **사용자 검증(verify user-stated legal facts)**(line 99): 인터뷰 답변에 rule cite·조문번호·사건명·deadline·threshold·jurisdiction 나오면 **config에 쓰기 전에 sanity-check** → 충돌 시 표면화("threshold X라 했는데 내 이해는 Y, `[premise flagged—verify]`"). "틀린 사실이 CLAUDE.md에 쓰이면 모든 미래 출력에 전파 — 여기서 잡는 게 최고 레버리지"(line 99).
- **재독(re-read before writing)**(line 236-242): 모순·드리프트된 specifics·이름붙일 gap 검출.
- **공유 company-profile 재사용**(line 42-48): 다른 legal 플러그인과 공유하는 profile 있으면 재질문 안 함.
- **Role-gated 가드레일**(line 121-144): 학생/grad면 honor-code·AI정책 확인 + "실제 의뢰인 사실 붙여넣지 마라" 경고. **real-client-matter check**: 실제 사안(실명·실일자·실제 노출)이면 일시정지·리디렉트, 가상 hypothetical 확인 전엔 분석 안 함.
- **After-write 가치제안 제시**(line 252-269): "내가 잘하는 것" 구체 리스트 + 첫 작업 제안(cold-start 문제·value-prop 문제 동시 해결).

### 1.4 customize (개인화 조정)

**구조(단계)**(line 22-71): config 읽기(없거나 `[PLACEHOLDER]`면 cold-start로 안내) → **customizable map** 그룹별 현재값 1줄요약 표시 → 뭘 바꿀지 질문 → 변경(현재값→새값→다운스트림 영향 설명→확인→쓰기) → 닫기.

**핵심 기법**:
- **다운스트림 영향 명시**(line 56-69): 변경이 어떤 스킬 동작을 바꾸는지 설명. 예) class 추가→outline-builder 새 아웃라인·flashcards 새 버킷·cold-call-prep 동작 / "summary-first"→socratic-drill이 먼저 답 안 묻고 rule+예시 제시 후 application 퀴즈.
- **가드레일**(line 73-88): ①**섹션 삭제 금지**(드롭은 `[Archived—retain seed materials]` 마킹) ②**내부 모순 플래그**("summary-first" + "maximum pushback" 충돌) ③**가드레일 degradation 플래그**: legal-writing·irac-practice의 "no rewriting" 룰은 load-bearing — 끄려 하면 "플러그인이 네 작업을 대신 안 써줄 것" 이해 확인 ④한 번에 한 변경(전체 인터뷰 재질문 금지).
- **전체 cold-start 없이 한 항목만 조정** = 핵심 가치(YAML 수기편집 회피)(line 16-18).

### 1.5 공통 설계 사상 (4스킬 관통)

1. **학습보존(anti-ghostwriting) 하드룰**: case-brief "don't brief it for me", legal-writing "no rewriting", customize의 가드레일까지 — **"대신 해주면 학생은 못 배운다"가 일관된 제1원리.** (case-brief line 38, legal-writing line 31, customize line 80-86)
2. **Confidence/Verify discipline**: 모든 substantive 단정에 `[UNCERTAIN]`/`[VERIFY]` + 외부 검색도구 대조 권고. AI cite는 fabricate될 수 있음 명시.
3. **단일 config(CLAUDE.md) 중심 개인화**: 인터뷰가 쓰고, 모든 스킬이 읽고, customize가 한 항목씩 고침. "한 달 쓰면 네가 직접 쓴 것처럼 읽히는 config"(cold-start line 308).
4. **drill-me vs explain-to-me 토글**이 학습강도를 가르는 마스터 스위치.
5. **패턴 추적 학습**: legal-writing tracker.md → N세션 후 약점 패턴 표면화.

---

## 2. 우리보다 나은 점 (우리에 없거나 약한 것)

### 2.1 [최대 격차] 학습자 개인화 레이어 자체가 없음

- **저쪽**: cold-start-interview가 학습자 프로필(학년·과목·약점·**학습스타일 drill-me/explain-to-me**·과거자료)을 단일 config에 영속화하고, 모든 스킬이 이를 읽어 출력을 개인화. customize가 한 항목씩 무중단 조정.
- **우리**: daily-drill·case-answer-review·카드생성 어디에도 **'이 사용자가 누구이고 어떻게 배우는가'를 영속화한 학습자 프로필이 없다.** CLAUDE.md(#1~#50)는 *시스템 운영규칙*이지 *학습자 개인 프로필*이 아니다. drill 난이도·사례 채점 강도·복습강도가 사용자 학습성향(밀어붙이기 vs 스캐폴딩)에 따라 분기하지 않는다.
- **구체 격차**: 우리 MEMORY.md의 메모리(law-vault-target-architecture 등)는 *시스템 사양*이지 *학습성향*이 아님. 저쪽의 `## Who's using this`·learning-style 디폴트·LIMITED DATA 플래그 같은 **학습자 메타데이터 슬롯이 부재**.

### 2.2 신뢰등급(Confidence discipline) — 입력 신뢰도에 따른 차등 산출

- **저쪽**: case-brief가 "원문 붙임=확신 / 사건명만=`[UNCERTAIN]` 플래그 + 외부대조 강권"으로 **입력 출처에 따라 산출 신뢰등급을 명시 차등**(line 22-30). legal-writing은 구조피드백=확신 / 내용=`[VERIFY]` / cite=edge case `[VERIFY]`로 **피드백 종류별 신뢰등급**(line 36-39).
- **우리**: #1·#2(소스근거·미확인 보류)·#13(생성후검증)이 있으나, 이는 *이진*(소스에 있다/없다)에 가깝다. **"소스 있지만 내 해석은 다수설이라 다툼있음"·"구조판단은 확신, 내용판단은 불확실" 같은 다단 신뢰등급 어휘(`[UNCERTAIN]`/`[VERIFY]`/다수설+verify)가 카드·드릴·채점 산출에 체계적으로 박혀 있지 않다.** 카드의 `검증` 필드(완료/anchor확인/원문확인필요…)는 *anchor 검증 상태*에 한정되고, *해석 신뢰등급*(다수설/소수설/다툼)은 다루지 않는다.

### 2.3 anti-ghostwriting을 '거부 스크립트 + 대안 제시'로 구현

- **저쪽**: legal-writing은 재작성 요청을 **우아한 거부 스크립트**(line 127-129) + **대안 3종**(타깃 피드백 / labeled 예시 / socratic 라우팅)으로 처리. case-brief는 "요약해줘" 거부 + **단 1개의 명시적 override 경로**(3번 읽었다고 하면 시작문장만)(line 51).
- **우리**: #21(Socratic First)이 "학습질문은 소크라틱 우선"이라고 선언하지만, **case-answer-review·daily-drill에 "답안 대신 써줘"류 요청을 거부하고 대안을 제시하는 명시적 스크립트가 없다.** 우리는 채점은 하되, "사례답안을 대신 작성"하는 요청에 대한 가드가 SKILL에 명문화돼 있지 않다(daily-drill은 출제·채점 모드, 작성대행 거부 룰 부재).

### 2.4 자료 인테이크의 '점진/일시정지/Templates-first' 설계

- **저쪽**: cold-start가 (a)**Templates-first**(아웃라인 업로드 시 형식 자동매칭, 설명요구 안 함, line 107) (b)**pause/resume + 부분저장**(`PAUSED AT` 주석·`[PENDING]` 마커, line 96) (c)**silent gap 금지**(모든 placeholder는 의도적 선택, line 95)을 명문화.
- **우리**: pdf-ingest·textbook-problem-intake가 있으나, **장시간 인테이크 인터뷰를 일시정지/재개**하는 설계나 **silent gap 금지(빠진 항목을 사용자에게 확인)** 원칙이 약하다. (우리 강점인 #45-C 재개가능 검증 fan-out은 *대량 산출 작업* 재개이지, *사용자 대화형 인테이크* 재개가 아님 — 결이 다름.)

### 2.5 customize의 '다운스트림 영향 설명 + 가드레일 degradation 경고'

- **저쪽**: 설정 변경 시 **어떤 스킬 동작이 바뀌는지 설명**하고, load-bearing 가드레일(no-rewriting)을 끄려 하면 경고(line 80-86).
- **우리**: 설정 변경(예: 학습성향·드릴강도)을 한 항목씩 안전하게 바꾸는 **사용자향 customize 진입점이 없다.** CLAUDE.md 룰 변경은 우리 #45-C 자기정합 교정루프가 *룰 내부 정합*을 보지만, *사용자가 자기 학습설정을 바꿀 때 다운스트림 영향을 설명*하는 레이어는 없다.

### 2.6 출력 끝 'Citation check' 고정 면책 + 외부 검색도구 안내

- **저쪽**: case-brief 출력 끝에 **고정 Citation check 블록**(AI cite는 미검증·fabricate 가능, Westlaw/Fastcase/CourtListener/학교도구에서 확인)(line 95). cold-start는 첫 citation-heavy 세션 전 research connector 연결 권고(line 283).
- **우리**: law_api.py verify-text로 **실제 자동검증**한다는 점에서 오히려 우리가 강하다(저쪽은 면책+권고에 그침). 단, **카드/드릴/채점 산출 끝에 "이 cite는 미검증, 직접 확인하라"는 사용자향 고정 면책 블록 습관은 약하다** — 우리는 검증을 *하지만*, 검증 안 된 항목을 사용자에게 *표시*하는 UX 문구(드릴의 "검증보류"는 있음)가 산출유형 전반에 일관되진 않다.

> 주의: 저쪽 4스킬은 **판례 백링크·사례 IRAC 자동채점·SRS·전수 카드감사가 전혀 없다.** 이 영역은 우리가 압도적으로 앞선다(아래 §3·§4). "나은 점"은 위 6개(개인화·신뢰등급·anti-ghostwriting 스크립트·인테이크 UX·customize·면책 UX)에 한정된다.

---

## 3. IRAC + 한국 요건사실론 통합에 주는 시사

### 3.1 저쪽의 IRAC 처리 방식 (관찰)

- **IRAC를 전담 스킬로 분리**: legal-writing이 "IRAC-specific exam essay는 `/irac-practice`가 더 타깃"이라고 라우팅(line 153). case-brief의 Issue/Holding/Reasoning/Rule 슬롯이 IRAC의 골격.
- **brief는 IRAC가 아니라 '판례 구조' 슬롯**: Facts/Issue/Holding/Reasoning/Rule + Procedural posture. **Issue를 yes/no 질문으로, Holding을 "yes/no + rule 1문장"으로** 강제(line 81-83) — 이는 한국 답안의 *결론先·요건충족 판단*과 결이 통한다.
- **구조유형별 차등**: memo(중립분석)·brief(옹호)를 구분(line 54-60). 우리 #32(원고|피고 2열) 사상과 연결됨.

### 3.2 우리 시스템의 현 상태

- 우리는 이미 **과목·유형별 구조**를 case-answer-review에 명문화: 민법 다툼형=#32 원고|피고 2열+IRAC(청구→항변→재항변), 민법 검토형=설문별 IRAC(쟁점→요건→포섭→결론), 형법=구성요건→위법성→책임·학설·죄수, 헌법=적법요건→본안(SKILL line 150-162). **이는 저쪽 IRAC보다 한국 시험구조에 이미 깊게 맞춰져 있다.**
- **포섭(사실↔법리)을 독립 채점 단계**로 분리(0.20 가중 + 4슬롯 작법: [요건적시]→[사안의 경우+구체사실]→[법적평가]→[소결], because 필수, 사실0개=포섭0점캡)(line 164-185).

### 3.3 통합 시사 (요건사실론 반영)

1. **신뢰등급 어휘를 요건사실 단정에 도입**: 저쪽의 `[UNCERTAIN]`/`[VERIFY]`/"다수설+verify"를 차용하여, 우리 사례채점·카드에서 **요건사실의 주장·증명책임 귀속이 다툼있는 경우(통설/판례/소수설 갈림)를 다단 신뢰등급으로 표시**. 현재 우리는 "소스에 있다/없다" 이진 → "있지만 주장증명책임 분배가 다툼/판례입장과 학설 갈림"을 명시할 어휘가 없다.

2. **case-brief의 "Issue=yes/no 질문, Holding=결론+rule 1문장" 강제를 한국식으로 변환**: 한국 요건사실론에서는 **청구원인(요건사실 충족) → 항변(반대규범 요건사실) → 재항변** 구조. 저쪽 brief의 Rule("아웃라인에 넣을 portable takeaway")처럼, 우리 카드/노트의 판례 holding을 **"어느 요건사실에 대한 어느 당사자의 주장·증명책임을 정한 명제인가"**로 portable하게 추출하면 IRAC와 요건사실론이 한 카드에서 만난다. (현 case_law 카드는 사건명·쟁점·판시·결론이지 *요건사실 귀속*을 명시 슬롯으로 갖지 않음 — 연구_카드구조 §5.2.)

3. **memo(중립) vs brief(옹호) 구분 → 검토형 vs 다툼형 강화**: 저쪽이 문서유형으로 분석톤을 가르듯, 우리도 이미 다툼형(2열)/검토형(설문IRAC)을 가른다. 추가 시사: **다툼형 답안에서 "청구원인 요건사실 / 항변 요건사실"을 2열의 행 레이블로 명시**하면(현 #32는 청구→항변 주고받기지만 *요건사실 단위* 행 분해는 미강제), 요건사실론이 IRAC 2열표에 결정적으로 녹는다.

4. **포섭 4슬롯을 요건사실 단위로**: 우리 4슬롯([요건적시]→[사안의 경우+사실]→[법적평가]→[소결])은 이미 요건사실론과 정합. 시사는 **[요건적시]를 "요건사실 + 그 주장·증명책임 주체"로 확장**하면 단순 IRAC를 넘어 요건사실론 답안이 된다.

---

## 4. 사례형(CASE)을 전부 카드로 만들어야 하는가 — 시사

### 4.1 이 레포는 사례를 어떻게 다루나 (핵심 관찰)

- **저쪽은 사례형을 '카드'로 만들지 않는다.** case-brief는 *판례*를 브리프하지 사례문제를 카드화하지 않으며, irac-practice(별도 스킬)는 **사례형 에세이를 채점·피드백하되 학생이 직접 쓰게** 한다. legal-writing도 **재작성 없음** — 즉 **사례형은 "학생이 푸는 것 + 구조 피드백"이지 "암기카드"가 아니다.**
- 핵심 철학: **anti-ghostwriting**. 사례 답안은 *생산물*이 아니라 *학습 행위* — 대신 만들어주면(카드로 박제하면) far-transfer(응용) 학습이 죽는다는 입장. case-brief가 "요약해줘"를 거부하는 것과 같은 논리.
- 개인화 학습(flashcards 스킬)은 *룰·cite·개념* 단위 플래시카드를 만들되, **사례 자체를 통째 카드화하진 않는다.**

### 4.2 우리 시스템의 현 입장

- 우리 02-card 프롬프트는 **사례형을 분해하지 말고 원문 보존**(`사례형_schema`, 연구_카드구조 line 67) — 별도 schema. 단 far-transfer 위해 **종합/IRAC 카드 1장 병행 권장**(line 67, anki SKILL line 29).
- daily-drill 2트랙: **진도 트랙=선택형(객관식) 즉시채점**(retention) / **복습·심화 트랙=사례형 IRAC 채점(포섭검토)+SRS**(응용·포섭)(SKILL line 11-12). **사례는 "푸는 것 + 채점"이지 통째 카드화 대상이 아니다** — 이 점에서 우리와 저쪽 철학이 사실상 일치.

### 4.3 시사 (사례형 카드화 여부)

1. **"사례형 전부를 카드로" = 안티패턴 (양쪽 모두 부정).** 저쪽의 anti-ghostwriting + far-transfer 논리와 우리 daily-drill 2트랙(사례=풀기/채점, 객관식=카드/retention)이 **동일 결론**: 사례 답안을 통째 암기카드로 만들면 *인출연습·포섭연습*이라는 학습가치가 소멸한다. **사례는 카드가 아니라 '풀이+채점+약점역류'의 대상.**

2. **단, 사례에서 '추출되는 명제'는 카드화 대상.** 우리 연구_카드구조의 결론(§5.2)대로: 사례형 원문은 비분해 보존하되, 그 사례가 가르치는 **(a)판례 holding (b)요건세트 (c)학설 대립**은 *별도 atom으로* 카드화. 즉 **"사례 → 카드" 변환의 단위는 '사례 전체'가 아니라 '사례가 인용·전제하는 법명제'.** (연구_카드구조 line 67·172: 사례형은 원문보존 + 종합/IRAC 카드 1장.)

3. **far-transfer 카드 1장은 유지·권장**: 저쪽이 사례를 카드화 안 하는 대신 *룰/개념* 카드 + *직접 풀기*로 응용을 기른다면, 우리는 **사례형마다 'IRAC 골격 종합카드 1장'(쟁점추출→적용)을 병행**하는 현 권장이 적절. 이는 "통째 박제"가 아니라 "구조 회상 단서"이므로 anti-ghostwriting과 충돌 안 함.

4. **결론**: **사례형 전수 카드화는 하지 않는다(NO).** 대신 ①사례 원문 비분해 보존 ②사례가 전제하는 법명제(판례·요건·학설)는 전수 atom 카드화(연구_카드구조의 누락0 게이트 적용) ③사례당 IRAC 종합카드 1장(far-transfer) ④사례 자체는 daily-drill 복습트랙에서 *풀고 채점*. — 이것이 저쪽 anti-ghostwriting 철학 + 우리 2트랙·전수 atom 카드화의 정합 지점.

---

## 5. 미확인 / 한계

- 저쪽의 `irac-practice`·`flashcards`·`socratic-drill`·`outline-builder` SKILL.md 본문은 본 조사 범위 밖(case-brief·legal-writing이 *참조*만 함). "사례를 어떻게 다루나"는 4스킬 내 언급 + integration 라우팅 근거의 추론이며, irac-practice 원문 미정독 — 사례형 직접 처리 방식은 *부분 미확인*.
- 저쪽 config 템플릿(`${CLAUDE_PLUGIN_ROOT}/CLAUDE.md`) 실파일 미열람 — 학습자 프로필 슬롯 구조는 cold-start SKILL 서술 기반.
- 우리 case-answer-review의 패널채점 Workflow(`.claude/workflows/case-answer-panel-grade.js`) 실코드 미열람(SKILL 서술만).

---

## 6. 인용 출처

- 외부: `…/claude-for-legal/law-student/skills/{case-brief,legal-writing,cold-start-interview,customize}/SKILL.md`
- 우리: `.agent/state/연구_카드구조.md`, `.agent/state/cardaudit_집계.md`, `.agent/skills/daily-drill/SKILL.md`, `.agent/skills/case-answer-review/SKILL.md`, `sync/_meta/연구종합_카드+진도보드_2026-06-28.md`, `E:\법학볼트\CLAUDE.md`(#1·#2·#21·#24·#32·#35·#50)
