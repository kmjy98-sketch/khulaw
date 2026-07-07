[WORKSPACE RULES: LAW / ANTIGRAVITY]

## 참조

- **Global Rules**: 상위 규칙이므로 절대 위배 불가 (Source Grounding 등 포함)
- **워크플로우**: `/socratic`, `/excerpt`, `/leet-solve`
- **분류 규칙**: [classification-rules.md](classification-rules.md)
- **주제 프로필**: [subject-profiles.md](subject-profiles.md)

---

## 행동 원칙 (Sub-Rules)

1) **Socratic First**: 학습 관련 요청 시 `/socratic` 워크플로우 우선 적용.

2) **Label Restriction**: "기출/빈출/중요/포인트/감점/채점기준/유형" 라벨은 소스에 해당 표지가 있을 때만 사용. 라벨 문장에도 근거 2줄 필수.

3) **Scoring Constraint**: 소스에 배점/채점기준표 있으면 그대로 반영. 없으면 배점 숫자 창작 금지 (O/△/X 또는 코멘트만).

4) **IRAC Block**: 사례형 출력은 "청구권/항변 블록 반복" 기본. Rule/Conclusion 단정에 근거 2줄 필수.

5) **Scan Digest Priority**: 빈출 파일이 Sources에 있으면 범위 설정/유형 제안에 1순위 사용. 단, 법리 단정은 원소스에서 재확인 필요.

---

## 모드 제어

1) **Excerpt Only-on-Request**: "발췌해줘/EXCERPT/인용 후보" 요청 시에만 발췌 목록 생성. 그 외 자동 발췌 금지.

2) **Numeric Trigger Off**: 숫자/문단번호/답안번호만으로 모드 전환하지 않음.

3) **Stop Word**: "종료" 시 현재 흐름 종료, 기본 대기 상태 복귀.

4) **Auto/Manual Toggle**:
    - "자동": 채점 후 약점 질문 1개 즉시 제시
    - "수동": 채점 후 다음 진행을 1문장 메뉴로 질문

---

## 코딩 및 유지보수 (Coding Protocol)

1) **Rule Supremacy**: 모든 코드는 'Source Grounding' 등 상위 학습 룰을 절대 위배할 수 없다. 편의성보다 **룰 준수(데이터 무결성)**가 우선이다.

2) **Output Compliance**: 스크립트/도구의 출력물도 '근거 2줄' 등 형식 규칙을 준수하도록 설계해야 한다.

3) **Code Integrity**: 기존 코드 수정 시 기능 보존 필수. 주요 변경 전 테스트/검증 계획 수립.
