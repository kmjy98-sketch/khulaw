# Drive Sync Policy

## 목적

Google Drive는 대용량 원본, 산출물, 개인 학습 자료의 source of truth로 유지한다.
GitHub는 Codex Web/Pro가 읽을 수 있는 룰, 스킬, 워크플로우, 스크립트, 설정 템플릿만 보관한다.

## Drive에 남길 것

- 교재 PDF
- OCR 원문
- 카드 전체 산출물
- Anki apkg
- 개인 학습 상태
- RAG 인덱스
- 대용량 미디어
- 저작권 위험이 있는 원문 및 가공본

## Git에 올릴 것

- `AGENTS.md`
- `.agent/skills`
- `.agent/workflows`
- `.agent/scripts`
- 설정 템플릿
- 운영 문서
- `sync/_meta` 중 이식 및 운영 문서
- 안키 카드 작성 규칙의 모델 중립 버전

## Private repo 운영

이 repo는 private 운영을 전제로 한다.

private repo에서도 기본 정책은 얇은 운영 repo다. 다만 사용자가 특정 대용량 자료를 Git에 포함하라고 명시하면 다음 조건으로 선별 포함할 수 있다.

1. 대상 파일 경로와 목적이 명확할 것
2. 저작권 또는 공유 위험을 사용자가 감수한다고 명시할 것
3. 가능하면 일반 Git 커밋보다 Git LFS 또는 별도 자료 branch를 사용할 것
4. 포함 사실을 `docs/reports/`에 기록할 것

실제 API 키, 인증 토큰, private key는 private repo라도 커밋하지 않는다. 필요한 값은 `.env.example`과 `.mcp.example.json`에 변수명만 둔다.

## 경로 충돌 처리

다음 폴더가 중복될 수 있다.

- `sync`
- `_sync`
- `sync_root`
- `sync이관_2026-06-11`
- `sync_파생본`
- `.codex`
- `.agent`
- `.agents`

동일 파일명이 여러 위치에 있으면 다음 우선순위로 판단한다.

1. 파일 내부에 명시된 갱신일 및 운영 메모
2. Git 추적 여부
3. modified time
4. 사용자 확인

불명확하면 병합하지 말고 보고한다.

## Codex Web/Pro 주의

Codex Web/Pro는 로컬 `H:\내 드라이브`를 직접 읽지 못할 수 있다.
따라서 repo 안에는 실행 기준이 되는 문서를 반드시 포함한다.
원문 자료가 필요한 경우 Drive 경로만 명시하고, 접근 실패 시 사용자에게 요청한다.
