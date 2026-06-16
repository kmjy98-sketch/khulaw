# khulaw Codex Rules

이 저장소는 Codex Web/Pro 세션에서 한국 법학 학습 작업 기준을 재현하기 위한 얇은 운영 repo다.

GitHub에는 룰, 스킬, 워크플로우, 스크립트, 설정 템플릿, 운영 문서만 둔다. 교재 원문, OCR 원문, 카드 산출물, apkg, RAG 인덱스, 개인 학습 상태, API 키는 Google Drive 또는 로컬 환경에 남기고 Git에 올리지 않는다.

저장소 visibility는 private 운영을 전제로 한다. private repo라도 실제 API 키와 개인 인증 토큰은 커밋하지 않고, 대용량 자료는 사용자가 대상 파일을 명시한 경우에만 별도 branch 또는 Git LFS로 선별 포함한다.

## 세션 시작 순서

1. `AGENTS.md`
2. `.agent/workflows/card-wiki-pipeline.md`
3. `.agent/skills/anki-card-generation/SKILL.md`
4. `docs/drive-sync/DRIVE_SYNC_POLICY.md`
5. `docs/git/GIT_POLICY.md`
6. `docs/codex/CODEX_WEB_PRO_RUNBOOK.md`

## 핵심 정책

- 법리, 조문, 판례 단정은 사용자 제공 소스 또는 허용된 공적 원문으로 확인된 경우만 쓴다.
- 로컬 `H:\내 드라이브` 경로는 Web/Pro에서 직접 접근되지 않을 수 있다.
- Drive 파일을 읽지 못하면 추측하지 말고 접근 실패로 기록한다.
- 실제 설정 파일과 비밀값은 예시 파일로만 문서화한다.

## 주요 문서

- Git 정책: `docs/git/GIT_POLICY.md`
- Drive/Git 분리 정책: `docs/drive-sync/DRIVE_SYNC_POLICY.md`
- Codex Web/Pro 실행 가이드: `docs/codex/CODEX_WEB_PRO_RUNBOOK.md`
- 룰/스킬 인벤토리: `docs/reports/rule_skill_inventory.md`
