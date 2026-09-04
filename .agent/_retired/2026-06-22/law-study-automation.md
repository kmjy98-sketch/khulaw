---
description: 공유 CODEX_BOOTSTRAP_REPORT를 현행 H:\내 드라이브 학습 자동화 구조에 맞춰 운영하는 워크플로우
---

# Law Study Automation Workflow

## 1. 우선순위

1. 루트 `AGENTS.md`와 과목별 `AGENTS.md`
2. `sync/_meta/PROJECT_CONTEXT.md`
3. `sync/_meta/DECISIONS.md`
4. 본 문서
5. `sync/_meta/CODEX_BOOTSTRAP_REPORT.md`

보고서가 새 저장소 루트 구조를 요구하더라도, 현행 워크스페이스에서는 `.agent/`, `sync/`, `outputs/anki/`로 매핑한다.

## 2. 운영 파일

| 용도 | 경로 |
|---|---|
| SQLite 원장 | `.agent/state/progress.sqlite` |
| 설정 | `.agent/config/*.yml` |
| 기본 카탈로그 | `.agent/data/category_catalog.csv`, `.agent/data/issue_catalog.csv`, `.agent/data/problem_catalog.csv` |
| 일일 계획 | `.agent/state/law_study_today_plan.md` |
| 대시보드 | `.agent/state/law_study_progress_dashboard.md` |
| 복습 큐 | `.agent/state/law_study_review_queue.md` |
| 약점표 | `.agent/state/law_study_weak_points.md` |
| Anki 업데이트 고지 | `.agent/state/law_study_anki_update_notice.md` |
| Anki batch CSV | `outputs/anki/law_study_batches/` |
| import 완료 CSV | `outputs/anki/law_study_exported/` |

## 3. 초기화

```powershell
python .agent/scripts/init_law_study_db.py
```

동작:

- `.agent/state/progress.sqlite`가 없으면 생성한다.
- 테이블과 인덱스를 `CREATE TABLE IF NOT EXISTS` 방식으로 보강한다.
- `.agent/data/category_catalog.csv`, `issue_catalog.csv`, `problem_catalog.csv`를 import한다.
- 기존 JSON 상태 파일은 수정하지 않는다.

## 4. 매일 시작

```powershell
python .agent/scripts/law_study_daily.py
```

동작:

- category별 쟁점, 문제, 약점, Anki pending 수를 집계한다.
- overdue 복습 큐를 표시한다.
- Anki 업데이트 필요 여부를 고지한다.
- 생성된 Markdown은 `.agent/state/law_study_*.md`에 둔다.

## 5. 사례형 답안 평가

현재 답안 평가의 기준 워크플로우는 `.agent/workflows/case-answer-rag.md`이다. 자동 채점 결과를 SQLite에 누적할 때만 다음 테이블을 사용한다.

- `attempts`
- `issue_results`
- `keyword_results`
- `conclusion_results`
- `review_queue`
- `weak_points`
- `anki_candidates`

법학 판단은 반드시 사용자 제공 자료 또는 허용된 공적 API 소스에 근거해야 한다. 자료가 부족하면 `자료 부족—보류`로 남긴다.

## 6. Anki batch 생성

```powershell
python .agent/scripts/generate_anki_batch.py --category 민법_채권총론 --limit 50
```

조건:

- `status`가 `pending` 또는 `updated`인 후보만 대상이다.
- `source_file`과 `source_location`이 없으면 export하지 않는다.
- `자료 부족—보류`가 포함된 카드는 export하지 않는다.
- batch 생성 후 후보 상태는 `batched`가 된다.

## 7. Anki import 완료 처리

```powershell
python .agent/scripts/mark_anki_imported.py --batch-id anki_YYYYMMDD_HHMMSS
```

동작:

- `anki_batches.status`를 `imported`로 바꾼다.
- 포함 후보의 `status`를 `exported`로 바꾼다.
- CSV 파일을 `outputs/anki/law_study_exported/`로 이동하고 `.agent/file_ops_log/`에 기록한다.

## 8. 금지

- AnkiWeb 직접 로그인 또는 직접 수정 금지.
- source 없는 카드 export 금지.
- 모범답안 전체 카드화 금지.
- 기존 `outputs/anki/v37` apkg 산출물 자동 변경 금지.
