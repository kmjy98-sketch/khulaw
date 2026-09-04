# Git Policy

## 목적

이 repo는 Codex Web/Pro에서 룰, 스킬, 워크플로우를 재현하기 위한 얇은 운영 repo다.
대용량 원본이나 산출물 repo가 아니다.

## Branch

- Visibility: private repo 운영을 기본으로 한다.
- `main`: 안정 버전
- `dev/codex-rules-cleanup`: 룰 및 스킬 정리
- `dev/anki-gpt55pro-skill`: GPT-5.5 Pro용 안키 카드 스킬 정리
- `archive/legacy-claude-package`: 레거시 Claude 패키지 보관

작업은 가능하면 `main`에서 직접 하지 않는다.

## Commit 단위

권장 커밋:

1. `chore: initialize codex rule repository`
2. `docs: add AGENTS hierarchy and workflow map`
3. `feat: add gpt55pro anki card generation skill`
4. `chore: add gitignore and config templates`
5. `docs: archive legacy claude card pipeline references`

## 금지

- API 키 커밋 금지
- `.env` 커밋 금지
- 실제 `mcp.json` 또는 `.mcp.json` 커밋 금지
- 교재 원문 커밋 금지
- OCR 전체 결과 커밋 금지
- Anki apkg 커밋 금지
- 개인 학습 상태 커밋 금지
- RAG 인덱스 커밋 금지

사용자가 private repo에 특정 대용량 자료를 넣으라고 명시한 경우에는 위 대용량 금지를 선별 완화할 수 있다. 이 경우 `git add -f`는 대상 파일을 하나씩 지정해서만 사용하고, 가능한 경우 Git LFS 또는 별도 자료 branch를 사용한다. 실제 비밀값은 private repo라도 커밋하지 않는다.

## 커밋 전 점검

```powershell
git status --short
git diff --stat
git diff --cached --stat
git check-ignore -v outputs/anki/test.apkg
git check-ignore -v .env
git check-ignore -v .mcp.json
git check-ignore -v outputs/02_cards_v37/test.md
```

민감정보 검색:

```powershell
Select-String -Path (Get-ChildItem -Recurse -File -Exclude .git | Select-Object -ExpandProperty FullName) `
  -Pattern 'api[_-]?key|secret|token|password|BEGIN PRIVATE KEY|sk-' `
  -CaseSensitive:$false
```

대용량 파일 점검:

```powershell
Get-ChildItem -Recurse -File | Where-Object {
  $_.FullName -notmatch '\\.git\\' -and $_.Length -gt 10MB
} | Select-Object FullName,Length
```
