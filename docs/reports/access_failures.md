# Access Failures

| 시각 | 대상 | 시도 방법 | 결과 | 추정 원인 | 후속 필요 |
|---|---|---|---|---|---|
| 2026-06-16 13:20 | 작업 지시문/위키/메모리 동시 읽기 | 샌드박스 PowerShell | 실패 | 샌드박스 초기화 오류 | 승인 경로로 재시도하여 해결 |
| 2026-06-16 13:24 | `git status`, `git remote -v`, `git branch --show-current` 묶음 실행 | PowerShell | 시간 제한 | Drive 루트 Git 상태 조회 지연 가능성 | `.git/HEAD`, `.git/config`, `git ls-files`로 우회 확인 |
| 2026-06-16 13:31 | `H:\내 드라이브\_sync` | `Test-Path` | 미존재 | 후보 경로 없음 또는 미동기화 가능성 | 필요 시 사용자 확인 |
| 2026-06-16 13:31 | `H:\내 드라이브\sync_root` | `Test-Path` | 미존재 | 후보 경로 없음 또는 미동기화 가능성 | 필요 시 사용자 확인 |
| 2026-06-16 13:31 | `H:\내 드라이브\sync이관_2026-06-11` | `Test-Path` | 미존재 | 후보 경로 없음 또는 미동기화 가능성 | 필요 시 사용자 확인 |
| 2026-06-16 13:31 | `H:\내 드라이브\sync_파생본` | `Test-Path` | 미존재 | 후보 경로 없음 또는 미동기화 가능성 | 필요 시 사용자 확인 |
| 2026-06-16 13:31 | push 권한 | 미시도 | 미검증 | 네트워크/인증 확인 전 | 사용자가 push 요청 시 별도 확인 |
| 2026-06-16 13:45 | `kmjy98-sketch/khulaw` GitHub repo | GitHub connector `_get_repo` | 404 Not Found | private repo 권한 범위 또는 repo 접근 불가 가능성 | GitHub 권한 확인 필요 |
| 2026-06-16 13:46 | GitHub visibility 변경 | `gh --version`, `gh auth status` | 실패 | 당시 로컬 GitHub CLI 미설치 | 2026-06-16 14:48 `gh` 2.94.0 설치 완료 |
| 2026-06-16 14:49 | GitHub CLI 인증 | `gh auth login --web --scopes repo` | 시간 제한 | 비대화형 세션에서 웹 로그인 완료 불가 | 사용자가 PowerShell에서 `gh auth login` 직접 실행 필요 |
