# 정합성 드리프트 로그 (사람용 요약)

> CLAUDE.md #45-C 자기정합 교정루프 산출. 기계기록은 `.agent/state/consistency_log.jsonl`.
> 1행 = 1불일치. status: open/accepted/dismissed/false_positive. recurring 3 누적 시 룰 영구개정 상신.

## 2026-06-22 (룰·스킬 정비 세션 — 교정루프 첫 가동)

| check | 위치 | 불일치 | 처리 | status |
|-------|------|--------|------|--------|
| C4 룰↔코드 | CLAUDE.md #46/#38 | 감사·설계 워크플로가 낡은 스냅샷 참조(실제 룰은 이미 v37·위키정본 반영) | 계획 무효화, 실측 우선 | false_positive |
| C1 경로정본 | sync/wiki/쟁점/_index.md | 계획이 참조한 파일 부재(쟁점 36→89 허수) | 보류 | dismissed |
| C3 트리거/레지스트리 | .agent/workflows | 계획 레거시 12 주장 vs 실제 10(활성 2개 오분류) | 활성 2개 제외, 10개 격리 | accepted |

**교훈(recurring 후보)**: 설계·감사 워크플로의 서브에이전트가 **세션 중 변경된 파일의 낡은 스냅샷**을 보고 계획을 세우는 드리프트가 반복됨(C4). → 모든 편집은 직전 실측(verify-before-act #45)을 강제. recurring 누적 시 "워크플로 산출은 항상 메인 실측으로 재검증" 룰화 검토.
