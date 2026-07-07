# Codex Web/Pro Runbook

## 세션 시작 시 읽을 파일

Codex Web/Pro 세션에서는 다음 순서로 읽는다.

1. `AGENTS.md`
2. `.agent/workflows/card-wiki-pipeline.md`
3. `.agent/skills/anki-card-generation/SKILL.md`
4. `docs/drive-sync/DRIVE_SYNC_POLICY.md`
5. `docs/git/GIT_POLICY.md`
6. 필요한 경우 `docs/anki/*.md`
7. 필요한 경우 `docs/legacy/*.md`

## 기본 원칙

- repo에 없는 원문이나 산출물은 Drive에 있다고 가정하지 말고 접근 가능성을 확인한다.
- Drive 파일을 읽지 못하면 즉시 보고한다.
- Google Drive 포인터 파일은 로컬에서 직접 읽지 않는다.
- 법리, 조문, 판례는 사용자 제공 소스 또는 공적 원문으로 확인되지 않으면 단정하지 않는다.
- 카드 생성 시 근거 없는 법리 창작 금지.
- 조문번호, 판례 사건번호, 선고일 추측 금지.
- apkg 빌드는 사용자가 명시 요청하거나 카드 파일을 변경한 경우에만 수행한다.

## Web/Pro에서 가능한 작업

- 룰 및 스킬 문서 수정
- Git diff 검토
- 스크립트 정리
- 템플릿 작성
- 안키 카드 생성 규칙 정리
- Drive 경로 매핑 문서화

## Web/Pro에서 제한되는 작업

- 로컬 `H:\내 드라이브` 직접 접근 보장
- Drive 동기화 상태 직접 보장
- 대용량 PDF 전체 처리
- Anki 앱 직접 조작
- 실제 API key 확인
- 실제 `mcp.json` 공개 저장

## Drive 자료가 필요한 경우

다음 형식으로 사용자에게 요청한다.

```text
다음 파일을 읽어야 하는데 현재 세션에서 접근되지 않습니다.

필요 파일:
- 경로:
- 목적:
- 대체 가능 여부:
- 필요한 조치: Drive connector 권한 부여 / 파일 업로드 / Git repo 반영
```
