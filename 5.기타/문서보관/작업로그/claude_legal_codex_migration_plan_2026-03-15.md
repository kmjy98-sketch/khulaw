# Claude Legal -> Codex 이식 계획

작성일: 2026-03-15

## 1. 조사 요약

### 1-1. 확인된 사실

1. 이 PC의 Claude 환경에는 `legal@knowledge-work-plugins`가 2026-03-12에 원격 설치된 기록이 있다.
   - 근거 발췌: `"installPlugin: attempting remote API install for plugin legal@knowledge-work-plugins"`
   - 근거 위치: `C:\Users\111\AppData\Roaming\Claude\logs\main.log:8576`
   - 근거 발췌: `"Installed plugin: legal"`
   - 근거 위치: `C:\Users\111\AppData\Roaming\Claude\logs\main.log:8577`

2. Anthropic의 `legal` 플러그인은 사내 법무팀용 생산성 플러그인으로, 계약 검토·NDA 분류·컴플라이언스 워크플로우·브리핑·정형 응답을 다룬다.
   - 근거 발췌: `"An AI-powered productivity plugin for in-house legal teams"`
   - 근거 위치: `https://raw.githubusercontent.com/anthropics/knowledge-work-plugins/main/legal/README.md:3`
   - 근거 발췌: `"contract review, NDA triage, and compliance workflows"`
   - 근거 위치: `https://raw.githubusercontent.com/anthropics/knowledge-work-plugins/main/legal/.claude-plugin/plugin.json:4`

3. 플러그인은 조직별 협상 기준을 `legal.local.md`에 두고, 그 playbook을 기준으로 검토 흐름을 수행하도록 설계되어 있다.
   - 근거 발췌: `"Create a local settings file"`
   - 근거 위치: `https://raw.githubusercontent.com/anthropics/knowledge-work-plugins/main/legal/README.md:30`
   - 근거 발췌: `"create a legal.local.md file"`
   - 근거 위치: `https://raw.githubusercontent.com/anthropics/knowledge-work-plugins/main/legal/README.md:32`

4. 대표 스킬인 `review-contract`는 계약 파일/URL/붙여넣기 텍스트를 받아 조항별 분석, redline 제안, business impact 분석을 수행하도록 정의되어 있다.
   - 근거 발췌: `"flag deviations, generate redlines, provide business impact analysis"`
   - 근거 위치: `https://raw.githubusercontent.com/anthropics/knowledge-work-plugins/main/legal/skills/review-contract/SKILL.md:3`
   - 근거 발췌: `"Analyze each clause, flag deviations, generate redline suggestions"`
   - 근거 위치: `https://raw.githubusercontent.com/anthropics/knowledge-work-plugins/main/legal/skills/review-contract/SKILL.md:11`

5. 플러그인은 MCP 기반 외부 도구 연결을 전제로 하며, 기본 서버 목록에는 Slack, Box, Egnyte, Atlassian, Microsoft 365, DocuSign, Google Calendar, Gmail이 포함된다.
   - 근거 발췌: `"Pre-configured servers include Slack, Box, Egnyte, Atlassian, and Microsoft 365"`
   - 근거 위치: `https://raw.githubusercontent.com/anthropics/knowledge-work-plugins/main/legal/README.md:80`
   - 근거 발췌: `"slack"`, `"box"`, `"egnyte"`, `"atlassian"`, `"ms365"`, `"docusign"`, `"google-calendar"`, `"gmail"`
   - 근거 위치: `https://raw.githubusercontent.com/anthropics/knowledge-work-plugins/main/legal/.mcp.json:2-34`

6. 현재 워크스페이스의 Codex 자산에는 법무 전용 스킬은 없지만, PDF 추출, RAG 검색, 노트 생성, 태그 인덱싱, 진도 추적 자산이 이미 있다.
   - 근거 발췌: `"PDF → 마크다운 추출 → LanceDB 인덱싱 통합 파이프라인."`
   - 근거 위치: `H:\내 드라이브\.agent\skills\pdf-ingest\SKILL.md:11`
   - 근거 발췌: `"49개 교재 파일을 벡터 인덱싱하여 정밀한 페이지 인용 검색 제공"`
   - 근거 위치: `H:\내 드라이브\.agent\skills\lancedb-rag\SKILL.md:11`
   - 근거 발췌: `"전사문·교재·기출문제를 RAG로 교차 참조하여 구조화된 학습 노트를 자동 생성합니다."`
   - 근거 위치: `H:\내 드라이브\.agent\skills\study-notes\SKILL.md:8`
   - 근거 발췌: `"태그 인덱스 자동 업데이트"`
   - 근거 위치: `H:\내 드라이브\.agent\skills\auto-index\SKILL.md:3`

7. 현재 워크스페이스에는 `contract`, `nda`, `compliance`, `legal` 명칭의 `.agent` 스킬 파일이 확인되지 않았다.
   - 근거 발췌: `.agent` 하위 파일명 검색 결과 없음
   - 근거 위치: 로컬 검색 결과(2026-03-15 실행)
   - 근거 발췌: 현재 `.agent/skills` 목록은 `file-classification`, `whisper-transcribe`, `transcript-tools`, `problem-index`, `socratic-loader`, `spaced-repetition`, `lancedb-rag`, `socratic-core`, `auto-index`, `progress-tracker`, `pdf-ingest`, `study-notes`
   - 근거 위치: 로컬 디렉터리 조회 결과(2026-03-15 실행)

### 1-2. 확인되지 않은 점

- 현재 사용자별 `legal.local.md` 또는 이에 준하는 조직 playbook 파일은 로컬 탐색 범위(`%USERPROFILE%\\.claude`, `%APPDATA%\\Claude`)에서 확인되지 않았다.
  - 근거 발췌: 검색 결과 없음
  - 근거 위치: 로컬 검색 결과(2026-03-15 실행)
- Codex 쪽에서 Claude Legal과 동급의 MCP connector 묶음을 이미 제공하는지 여부는 소스에서 확인할 수 없습니다.

## 2. 해석

이식의 핵심은 `Claude Legal plugin 자체`를 옮기는 것이 아니라, 아래 3개 층을 Codex 워크스페이스 구조로 재구성하는 것이다.

1. `playbook 층`
   - 조직별 협상 기준, 허용 범위, escalation trigger, 표준 응답문을 로컬 파일로 관리

2. `workflow 층`
   - 계약 검토
   - NDA 분류
   - 법무 브리핑
   - 컴플라이언스 체크
   - 정형 응답 생성

3. `knowledge 층`
   - 계약서/사례/정책/내규/이전 검토결과를 PDF 추출 -> 청크화 -> RAG 검색 -> 인라인 근거 인용으로 연결

## 3. Codex 대응표

| Claude Legal 기능 | 확인 근거 | Codex 쪽 활용 자산 | 이식 판단 |
| --- | --- | --- | --- |
| 계약 검토(`review-contract`) | `review-contract` 스킬 원문 | `pdf-ingest` + `lancedb-rag` + 신규 법무 스킬 | 1순위 |
| NDA 분류(`triage-nda`) | README의 NDA triage 언급 | 신규 법무 스킬 + playbook 파일 | 1순위 |
| 컴플라이언스 체크 | README / plugin.json | 신규 법무 스킬 + 외부 조사 + RAG | 2순위 |
| 법무 브리핑/brief | README의 legal briefings 언급 | `study-notes` 구조 재사용 + 신규 템플릿 | 2순위 |
| 정형 응답(`legal-response`) | README의 templated responses 언급 | 신규 템플릿 + playbook | 2순위 |
| 기관 지식 관리 | plugin.json의 institutional knowledge 언급 | `pdf-ingest` + `lancedb-rag` + `auto-index` | 1순위 |
| Slack/Box/Atlassian/M365/DocuSign 연동 | `CONNECTORS.md`, `.mcp.json` | 자료 부족—별도 설계 필요 | 3순위 |

## 4. 권장 이식 구조

### Phase 0. 기준 파일 확보

목표: Claude의 `legal.local.md` 역할을 Codex 워크스페이스 안의 관리 가능한 파일로 옮긴다.

권장 산출물:

- `H:\내 드라이브\.agent\state\legal_playbook.md`
- `H:\내 드라이브\.agent\state\legal_templates.md`

포함 항목:

- 책임제한(LoL)
- indemnity
- IP ownership
- data protection
- term/termination
- governing law / dispute resolution
- NDA 기본 조건
- escalation trigger
- 표준 응답 템플릿

이 단계가 선행되지 않으면 이후 계약 검토 결과는 조직 기준이 아니라 일반 기준에 머문다.

### Phase 1. 핵심 스킬 1개로 MVP 구축

목표: `review-contract`와 `triage-nda`를 우선 Codex형 단일 스킬로 합친다.

권장 스킬명:

- `H:\내 드라이브\.agent\skills\legal-review\`

구성:

- `SKILL.md`
- `templates\contract_review.md`
- `templates\nda_triage.md`
- `scripts\extract_contract_context.py`
- `scripts\render_review.py`

동작:

1. 입력 파일(PDF/DOCX/TXT) 확인
2. PDF면 `pdf-ingest` 또는 단일 추출 경로 사용
3. `legal_playbook.md` 로드
4. 조항별 체크리스트 적용
5. 결과를 Markdown 보고서로 출력
6. 필요 시 `auto-index`로 태그화

### Phase 2. 지식베이스 연결

목표: 과거 계약서, 표준조항, 사내 기준서, 정책 PDF를 근거 검색 가능한 형태로 만든다.

활용 자산:

- `pdf-ingest`: PDF -> Markdown -> 인덱싱
- `lancedb-rag`: 관련 청크 및 페이지 검색
- `auto-index`: 키워드/조문/판례/쟁점 링크 보강

권장 입력 소스:

- 표준계약서
- NDA 샘플
- DPA / 개인정보처리 부속합의서
- 내부 승인 기준 문서
- 과거 redline 결과

### Phase 3. 문서 유형별 파생 스킬 분리

MVP 안정화 후 아래를 분리한다.

1. `legal-review`
   - 계약 검토
   - NDA 분류

2. `legal-briefing`
   - 회의 브리핑
   - 사건/쟁점 브리프
   - 협상 포인트 요약

3. `legal-response`
   - 정형 회신 초안
   - 정책 문의 응답
   - 내부 검토 요청 회신

4. `legal-compliance`
   - 체크리스트형 규정 검토
   - 데이터 처리 / 보안 / 보존 조항 검토

### Phase 4. 외부 도구 연동

현재 확인된 Claude Legal의 강점은 MCP connector 묶음이다. 다만 Codex 쪽 동일 자산은 소스에서 확인할 수 없습니다. 따라서 외부 도구 연동은 별도 트랙으로 뺀다.

권장 방식:

1. 먼저 `파일 기반 운영`으로 MVP 완성
2. 그 다음 실제 사용 빈도가 높은 도구 1개만 우선 연결
3. 연동 우선순위는 `문서 저장소 -> 메신저 -> 전자서명` 순

권장 우선순위:

1. cloud storage 대체
   - Google Drive / SharePoint / Box 중 실제 사용하는 저장소 1개
2. chat 대체
   - Slack 또는 Teams
3. e-signature 대체
   - DocuSign 등

## 5. 실행 순서

1. `legal_playbook.md` 초안 작성
2. `legal-review` 스킬 골격 생성
3. 샘플 계약서 2~3건으로 계약 검토 출력 포맷 고정
4. `pdf-ingest` + `lancedb-rag`로 표준문서 인덱싱
5. NDA 전용 템플릿 분기 추가
6. `study-notes` 구조를 재사용해 briefing/output 템플릿 확장
7. 외부 connector 필요성 재평가

## 6. 바로 실행 가능한 최소 계획

이번 이식은 아래 범위로 자르는 것이 가장 안전하다.

- 범위 포함
  - playbook 파일
  - 계약 검토
  - NDA 분류
  - 근거 인용형 Markdown 출력
  - 표준문서 RAG 검색

- 범위 제외
  - Slack/Box/Atlassian/M365/DocuSign 실연동
  - 조직별 승인 플로우 자동화
  - 다중 이해관계자 협업 UI

## 7. 권고

현재 상태에서는 `Claude Legal의 기능 전체 복제`보다 `Codex용 로컬 법무 워크벤치`를 만드는 접근이 맞다. 이유는 다음과 같다.

1. 로컬 워크스페이스에는 이미 `PDF 추출 -> RAG -> 노트/태그화` 자산이 있다.
2. 반면 법무 전용 playbook/skill/connector 계층은 비어 있다.
3. 따라서 이식 비용 대비 효과가 가장 큰 구간은 `playbook + review skill + knowledge base` 3개를 먼저 붙이는 것이다.

## 8. 참고 소스

- [Anthropic Legal plugin page](https://claude.com/plugins/legal)
- [knowledge-work-plugins/legal README](https://raw.githubusercontent.com/anthropics/knowledge-work-plugins/main/legal/README.md)
- [knowledge-work-plugins/legal CONNECTORS](https://raw.githubusercontent.com/anthropics/knowledge-work-plugins/main/legal/CONNECTORS.md)
- [knowledge-work-plugins/legal plugin.json](https://raw.githubusercontent.com/anthropics/knowledge-work-plugins/main/legal/.claude-plugin/plugin.json)
- [knowledge-work-plugins/legal review-contract skill](https://raw.githubusercontent.com/anthropics/knowledge-work-plugins/main/legal/skills/review-contract/SKILL.md)
- [lecture-notes workflow](H:\내 드라이브\.agent\workflows\lecture-notes.md)
- [pdf-ingest skill](H:\내 드라이브\.agent\skills\pdf-ingest\SKILL.md)
- [lancedb-rag skill](H:\내 드라이브\.agent\skills\lancedb-rag\SKILL.md)
- [study-notes skill](H:\내 드라이브\.agent\skills\study-notes\SKILL.md)
- [auto-index skill](H:\내 드라이브\.agent\skills\auto-index\SKILL.md)
- [Claude install log](C:\Users\111\AppData\Roaming\Claude\logs\main.log)
