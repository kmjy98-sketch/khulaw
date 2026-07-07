# Rule / Skill Inventory

작성일: 2026-06-16

| 구분 | 경로 | 파일명 | 역할 | 상태 | Git 포함 | 비고 |
|---|---|---|---|---|---|---|
| root-rule | `AGENTS.md` | `AGENTS.md` | Codex 전체 작업 기준 | active | yes | 최우선 |
| subject-rule | `1.민사/AGENTS.md` | `AGENTS.md` | 민사 과목별 기준 | active | yes | 존재 확인 |
| subject-rule | `2.형사/AGENTS.md` | `AGENTS.md` | 형사 과목별 기준 | active | yes | 존재 확인 |
| subject-rule | `3.공법/AGENTS.md` | `AGENTS.md` | 공법 과목별 기준 | active | yes | 존재 확인 |
| subject-rule | `4.선택법/AGENTS.md` | `AGENTS.md` | 선택법 과목별 기준 | active | yes | 존재 확인 |
| workflow | `.agent/workflows/card-wiki-pipeline.md` | `card-wiki-pipeline.md` | 카드 v37 및 쟁점 위키 주경로 | active | yes | 2026-06-15 갱신 확인 |
| workflow | `.agent/workflows/skill-structure.md` | `skill-structure.md` | 스킬 구조도 | active | yes | 존재 확인 |
| workflow | `.agent/workflows/skill-overlap-review.md` | `skill-overlap-review.md` | 스킬 중복 검토 | active | yes | 존재 확인 |
| workflow | `.agent/workflows/lecture-notes.md` | `lecture-notes.md` | 노트 정리 | active | yes | 존재 확인 |
| workflow | `.agent/workflows/socratic.md` | `socratic.md` | 학습 및 문답 | active | yes | 존재 확인 |
| skill | `.agent/skills/anki-card-generation/SKILL.md` | `SKILL.md` | Codex Web/Pro 안키 카드화 | active | yes | 신규 |
| skill | `.agent/skills/korean-law-mcp` | `SKILL.md` | 법령 및 판례 공적 원문 확인 | active | yes | 폴더 존재 확인 |
| skill | `.agent/skills/file_ops_log` | `SKILL.md` | 파일 이동/복사/이름변경 로그 | active | yes | 폴더 존재 확인 |
| script | `.agent/scripts/build_v37_apkg.py` | `build_v37_apkg.py` | v37 apkg 빌드 | reference | yes | 실행은 명시 요청 시 |
| script | `.agent/scripts/anchor_verify_batch.py` | `anchor_verify_batch.py` | 판례/조문 anchor 검증 | reference | yes | 공적 원문 확인 보조 |
| script | `.agent/scripts/log_file_op.py` | `log_file_op.py` | 파일 작업 로그 | active | yes | 이동/복사/이름변경 시 사용 |
| state-template | `.agent/state/README.md` | `README.md` | state 포함/제외 기준 | active | yes | 신규 |
| state-private | `.agent/state/learning.json` | `learning.json` | 개인 학습 상태 | active | no | Git 제외 |
| state-private | `.agent/state/srs_log.json` | `srs_log.json` | 간격 반복 상태 | active | no | Git 제외 |
| bulk-output | `outputs/02_cards_v37/` | `*.md` | 카드 readable 산출물 | reference | no | Drive/로컬 보관 |
| bulk-output | `outputs/anki/v37/apkg/` | `*.apkg` | Anki 산출물 | reference | no | Drive/로컬 보관 |
| wiki-index | `sync/wiki/_index.md` | `_index.md` | 위키 진입점 | reference | selected | 선별 포함 후보 |
| legacy | `5.기타/프롬프트 등 개선/claude_code_package_v2/` | `...` | 과거 Claude 패키지 | legacy | no | 실행 경로 아님 |

상태값: `active`, `reference`, `legacy`, `deprecated`, `unknown`, `unreadable`, `duplicate`.
