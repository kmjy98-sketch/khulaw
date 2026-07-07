# _retired 2026-07-01 (#49 은퇴 대장)

| 자산 | 원위치 | 사유 | 후속(대체) |
|------|--------|------|-----------|
| korean-law-mcp/ (풀 클론+runtime+.git) | `.agent/skills/korean-law-mcp/` | #49 은퇴. MCP 서버 폐기, law_api.py(법제처 직접 API)로 완전 대체. 코드 소비자 전부 재배선 완료(build_law_evidence·law_api·anchor_verify_batch → `.agent/lib/.env`). | `.agent/lib/law_api.py` (search_law·get_law_detail·search_precedent·verify_*) |
| board_server.py | `6.진도관리/board_server.py` | v1 진도보드 서버. 정본=논점 frontmatter(#19-B), board_server_v2.py로 대체. log_result.py 폴백 제거·끄기.bat 패턴 v2화 후 은퇴. | `6.진도관리/board_server_v2.py` + `sync/위키/진도보드.base` |
| _ingest_jindo.py | `.agent/scripts/_ingest_jindo.py` | v1 진도 ingest(단원 모델). 논점 frontmatter 정본화로 폐지. 호출자 board_server.py도 은퇴. | 논점 frontmatter + mark_progress.py |
| 진도_현황.json | `.agent/state/진도_현황.json` | v1 단원별 집계 snapshot. 정본 아님(#19-B). | 논점 frontmatter |
| 진도_현황.md | `6.진도관리/진도_현황.md` | v1 사람용 진도표(자동생성). | 진도보드.base(Bases) / board_server_v2 |

## 비고
- API 키(.env)는 은퇴 전 `.agent/lib/.env`로 복사됨(#16-C copy 로그). law_api·anchor_verify_batch는 `_ENV_PATHS`=[lib우선, 구클론 폴백]으로 읽어 클론 없어도 동작.
- 복원: 이 폴더의 korean-law-mcp/를 `.agent/skills/`로 move(log_file_op) 하면 됨. 삭제 아님(가역).
- .claude/skills/korean-law-mcp 라우팅 스텁은 2026-06-30 `_trash/2026-06-30/`로 별도 이동됨(스킬목록 노출 제거).
