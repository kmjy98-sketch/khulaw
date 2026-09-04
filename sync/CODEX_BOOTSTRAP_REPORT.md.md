
OpenAI Codex 문서에는 Codex의 CLI, IDE Extension, Web, configuration, rules, hooks, `AGENTS.md`, non-interactive mode, SDK, GitHub Action 등 저장소 기반 자동화에 필요한 항목들이 공식 문서 구조로 제공되어 있으므로, 이 설계는 “Codex가 저장소 안의 파일·DB·스크립트·규칙을 관리하는 프로젝트”로 두는 전제에 맞습니다. ([OpenAI Developers](https://developers.openai.com/codex/?utm_source=chatgpt.com "Codex | OpenAI Developers"))

---
# Law Study Automation System — Codex 작업용 전체 보고서

## 0. 이 문서의 목적

이 문서는 로스쿨 사례형 답안 훈련, Markdown 교재 정리, 진도관리, 약점 분석, 복습 큐, Anki 장기복습 카드풀을 통합하는 개인 학습 자동화 시스템을 Codex가 바로 구현할 수 있도록 정리한 작업 지시서이다.

Codex는 이 문서를 기준으로 다음을 수행해야 한다.

1. 저장소 폴더 구조 생성
2. `AGENTS.md`, `PROJECT_CONTEXT.md`, `DECISIONS.md` 작성
3. `config/*.yml` 작성
4. `data/*.csv` 기본 스키마 작성
5. `progress.sqlite` 초기화 스크립트 작성
6. 진도·복습·약점·Anki 카드 후보 관리 스크립트 작성
7. 사례형 답안 평가 결과를 Markdown/JSON/SQLite로 누적하는 구조 작성
8. Anki 전체 보관용 카드풀을 만들되, 실제 Anki export는 진도와 약점에 따라 제한하는 batch CSV 생성 구조 작성

---

# 1. 프로젝트 배경

사용자는 로스쿨생이다.

목표는 단순 암기가 아니라 **사례형 답안 훈련**이다.  
현재 법학 교재, 정리 자료, 판례, 노트는 Markdown으로 정리되어 있거나 정리될 예정이다.

사용자는 다음 기능을 원한다.

- 법학 교재 Markdown 구조화
- 쟁점 단위 정리
- 사례형 문제 풀이
- 답안 파일 자동 평가
- 쟁점 발견 여부 평가
- 핵심 키워드 일치도 평가
- 법리 구조 일치도 평가
- 결론 일치 여부 평가
- 포섭 누락 여부 평가
- 반복적으로 틀리는 쟁점 누적
- 복습 필요 항목 자동 생성
- 진도표 자동 갱신
- 약점표 자동 갱신
- Anki 후보 카드 생성
- 주기적 Anki batch CSV 생성
- 주간 리포트 생성

---

# 2. 최종 시스템 방향

## 2.1 핵심 결론

이 시스템은 다음 구조로 운영한다.

```text
Codex + SQLite + Markdown
  = 진도관리, 약점분석, 사례형 채점, 단기 복습, 카드 업데이트 판단

Anki
  = 전체 보관용 지식 저장소 + 장기복습 엔진

CSV
  = Anki import/export 중간 형식

Markdown
  = 사람이 읽는 교재, 리뷰, 현황판

SQLite
  = 실제 누적 원장
```

## 2.2 역할 분담

| 영역 | 담당 |
|---|---|
| 사례형 답안 평가 | Codex |
| 쟁점·키워드·결론·포섭 분석 | Codex |
| 진도관리 | SQLite + Codex |
| 약점 분석 | SQLite + Codex |
| 단기 복습 큐 | SQLite + Markdown |
| 장기복습 | Anki |
| 전체 카드 보관 | Anki |
| 카드 후보 관리 | SQLite |
| 카드 batch 생성 | Codex |
| Anki import | 사용자가 Anki Desktop에서 수행 |
| AnkiWeb 직접 수정 | 금지 |

---

# 3. 비목표와 금지사항

## 3.1 이 시스템이 하지 않는 것

이 시스템은 다음을 하지 않는다.

```text
- 외부 법학 지식으로 답안을 새로 채점하지 않는다.
- 교재에 없는 법리를 만들어내지 않는다.
- Anki를 진도관리 DB로 쓰지 않는다.
- 사례형 모범답안 전체를 Anki 카드로 만들지 않는다.
- 매일 Anki 덱을 직접 수정하지 않는다.
- Codex가 AnkiWeb에 직접 로그인해서 수정하지 않는다.
```

## 3.2 반드시 지켜야 할 원칙

```text
1. 모든 법학 판단은 materials_structured/에 근거한다.
2. 자료에 없는 법리는 “자료 부족—보류”로 처리한다.
3. 감점, 누락, 카드 생성에는 source.file과 source.location을 남긴다.
4. Anki는 전체 보관용 지식 저장소로 쓰되, export는 진도·약점 기준으로 통제한다.
5. 세부 쟁점은 Anki 덱이 아니라 issue_id와 tag로 관리한다.
6. Anki 덱은 과목/대분류 단위로 둔다.
7. note_key는 절대 변경하지 않는다.
8. 반복 오답은 기존 카드를 업데이트하거나 후보를 보강한다.
9. 중복 카드는 생성하지 않는다.
10. SQLite를 원장으로 두고, Markdown은 현황판으로 둔다.
```

---

# 4. 전체 폴더 구조

Codex는 다음 구조를 생성한다.

```text
law-study/
  CODEX_BOOTSTRAP_REPORT.md
  AGENTS.md
  PROJECT_CONTEXT.md
  DECISIONS.md
  README.md

  config/
    categories.yml
    review_rules.yml
    scoring_rules.yml
    anki_rules.yml
    notification_rules.yml

  data/
    category_catalog.csv
    issue_catalog.csv
    problem_catalog.csv
    syllabus.csv

  materials_raw/
    .gitkeep

  materials_structured/
    공법/
      헌법_기본권/
      헌법_통치구조/
      헌법소송/
      행정법_행정작용/
      행정법_행정절차/
      행정법_행정쟁송/
      행정법_국가배상손실보상/
    민사/
      민법_민총/
      민법_물권/
      민법_채권총론/
      민법_채권각론/
      민법_가족법/
      민소법_소송요건/
      민소법_심리증거/
      민소법_판결상소재심/
      상법_회사/
      상법_기타/
    형사/
      형법_총론/
      형법_개인적법익/
      형법_사회적법익/
      형법_국가적법익/
      형소법_수사/
      형소법_공판/
      형소법_증거/
      형소법_상소재심/

  problems/
    .gitkeep

  answers/
    .gitkeep

  reviews/
    .gitkeep

  progress/
    progress.sqlite
    today_plan.md
    progress_dashboard.md
    review_queue.md
    weak_points.md
    anki_update_notice.md
    weekly_report.md

  cards_pending/
    pending_all.csv

  cards_batches/
    .gitkeep

  cards_exported/
    .gitkeep

  exports/
    today_plan.csv
    review_queue.csv
    weak_points.csv

  scripts/
    init_db.py
    import_catalogs.py
    plan_today.py
    review_answer.py
    update_progress.py
    update_review_queue.py
    analyze_weak_points.py
    check_anki_update_needed.py
    generate_anki_batch.py
    mark_anki_exported.py
    generate_dashboard.py
    generate_weekly_report.py
```

---

# 5. 저장소에 생성할 핵심 문서

## 5.1 `PROJECT_CONTEXT.md`

Codex는 다음 내용으로 `PROJECT_CONTEXT.md`를 생성한다.

```markdown
# Project Context

## 목적

이 저장소는 로스쿨 사례형 답안 훈련, Markdown 교재 정리, 진도관리, 약점 분석, 복습 큐, Anki 장기복습을 통합하기 위한 개인 학습 시스템이다.

## 기본 방향

- Anki는 전체 보관용 지식 저장소이자 장기복습 도구로 사용한다.
- Codex/SQLite는 진도, 약점, 단기복습, 사례형 답안 평가, Anki 카드 업데이트 판단을 담당한다.
- 사례형 답안 훈련의 중심은 Anki가 아니라 Codex 기반 평가와 오답 누적이다.
- Anki는 요건, 판례, 조문 구조, 목차, 반복오답, 핵심 키워드 암기에 사용한다.

## 과목 범위

- 공법: 헌법, 행정법
- 민사: 민법, 민소법, 상법
- 형사: 형법, 형소법

## 핵심 원칙

1. 외부 법학 지식 사용 금지.
2. 판단은 `materials_structured/`에 있는 자료 기준으로만 한다.
3. 자료에 없는 법리는 `자료 부족—보류`로 처리한다.
4. 감점 또는 카드 생성에는 source file과 source location을 남긴다.
5. Anki 카드는 전체 보관용으로 생성하되, 실제 업데이트/export는 진도와 약점을 고려해 제한한다.
6. 세부 쟁점은 Anki 덱이 아니라 `issue_id`와 태그로 관리한다.
7. Anki 덱은 과목/대분류 단위로 유지한다.
```

---

## 5.2 `DECISIONS.md`

Codex는 다음 내용으로 `DECISIONS.md`를 생성한다.

```markdown
# Design Decisions

## 1. Anki의 역할

Anki는 진도관리 메인 시스템이 아니다.
Anki는 전체 보관용 지식 저장소이자 장기복습 도구로 사용한다.

## 2. Codex의 역할

Codex는 다음을 담당한다.

- 매일 진도 확인
- 오늘 할 일 추천
- 단기 복습 큐 생성
- 사례형 답안 평가
- 약점 분석
- Anki 후보 카드 생성
- Anki 카드 업데이트 필요 여부 판단
- 주기적 batch CSV 생성
- Anki import 필요 고지

## 3. 카드 관리 원칙

Anki 카드는 전체 보관용으로 만들 수 있다.
다만 Anki에 매일 무제한 import하지 않는다.

카드 상태는 다음 생명주기를 따른다.

- draft
- pending
- approved
- batched
- exported
- updated
- suspended
- rejected

## 4. Anki 덱 구조

쟁점별 덱을 만들지 않는다.
덱은 과목/대분류 단위로 둔다.

예:

- Law::공법::헌법_기본권
- Law::공법::행정법_행정쟁송
- Law::민사::민법_채권총론
- Law::형사::형법_총론
- Law::반복오답::공법
- Law::사례형목차::민사

세부 쟁점은 태그와 issue_id로 관리한다.

## 5. 사례형 전체 Anki화 금지

사례형 모범답안 전체를 Anki 카드로 만들지 않는다.
대신 목차, 키워드, 판례문구, 반복오답, 포섭 체크포인트만 카드화한다.

## 6. AnkiWeb 직접 갱신 금지

Codex가 AnkiWeb에 직접 로그인하거나 웹으로 수정하지 않는다.
권장 흐름은 다음과 같다.

Codex → CSV batch 생성 → Anki Desktop import → Anki sync

## 7. SQLite 원장 원칙

진도, 약점, 시도, 복습 큐, Anki 후보 상태는 SQLite에 저장한다.
Markdown 파일은 사람이 읽는 현황판이다.
CSV는 Anki export/import용 중간 산출물이다.
```

---

# 6. `AGENTS.md`

Codex는 다음 내용으로 `AGENTS.md`를 생성한다.

```markdown
# AGENTS.md

## Role

You are maintaining a Korean law school study automation repository.

This system manages:

- Markdown legal materials
- structured issue notes
- law school exam-style answer review
- progress tracking
- weakness analysis
- short-term review queue
- Anki card storage and batch export

## Non-Negotiable Principles

1. Do not use external legal knowledge unless explicitly instructed.
2. Evaluate answers only against `materials_structured/`.
3. If a rule, issue, conclusion, or keyword is not found in the source materials, mark it as `자료 부족—보류`.
4. Every negative evaluation must include:
   - issue_id
   - source file
   - source location
   - reason
5. Do not invent legal doctrines, cases, or statutory requirements.
6. Do not silently overwrite user-written files.
7. Do not import directly into Anki unless explicitly instructed.
8. Do not attempt to update AnkiWeb directly.
9. Do not create issue-level Anki decks.
10. Do not create duplicate cards.

## Source of Truth

The source of truth is:

1. `progress/progress.sqlite`
2. `data/*.csv`
3. `materials_structured/`
4. `reviews/*.json`

Markdown files under `progress/` are human-readable dashboards.
CSV files under `cards_pending/` and `cards_batches/` are export artifacts.

## System Roles

### Codex / SQLite

Codex manages:

- daily progress
- short-term review
- weakness analysis
- answer evaluation
- Anki card candidate generation
- Anki card update decisions
- batch export generation
- update notices

### Anki

Anki is used for:

- long-term memory
- issue outline recall
- rule/requirement recall
- case-law phrase recall
- statutory structure recall
- repeated mistake cards

Anki is not the primary progress manager.
Anki is not the main case-answer training system.

## Anki Card Policy

Anki cards are created as a full knowledge storage system.
However, not every card is immediately exported.

Cards must be managed through this lifecycle:

1. draft
2. pending
3. approved
4. batched
5. exported
6. updated
7. suspended
8. rejected

Valid card types:

- requirement
- case_law
- statute_structure
- issue_outline
- keyword_recall
- conclusion_pattern
- application_checkpoint
- repeated_mistake

Do not create cards for:

- full model answers
- one-time minor mistakes
- unsupported legal rules
- unclear source material
- overly long passages
- duplicate notes

## Note Key Rule

Every Anki card must have a stable `note_key`.

Format:

`{issue_id}::{card_type}::{sequence}`

Examples:

- `헌법_집회의자유_금지통고_001::keyword_recall::001`
- `민법_채권자대위권_001::requirement::001`
- `형법_공동정범_001::case_law::001`

Never change an existing `note_key`.

If the card content must be improved, update the card with the same `note_key`.

## Deck Policy

Do not create issue-level decks.

Use category-level decks only.

Examples:

- `Law::공법::헌법_기본권`
- `Law::공법::행정법_행정쟁송`
- `Law::민사::민법_채권총론`
- `Law::민사::민소법_심리증거`
- `Law::형사::형법_총론`
- `Law::형사::형소법_증거`
- `Law::사례형목차::공법`
- `Law::반복오답::민사`

Detailed classification must be stored in tags:

- `subject::헌법`
- `category::헌법_기본권`
- `topic::집회의자유`
- `issue::헌법_집회의자유_금지통고_001`
- `type::keyword_recall`

## Daily Workflow

When asked to generate the daily plan:

1. Read `progress/progress.sqlite`.
2. Read `data/category_catalog.csv`.
3. Read `data/issue_catalog.csv`.
4. Read `data/problem_catalog.csv`.
5. Check overdue review items.
6. Check weak issues.
7. Check current progress by category.
8. Recommend today’s tasks.
9. Update:
   - `progress/today_plan.md`
   - `progress/progress_dashboard.md`
   - `progress/review_queue.md`
   - `progress/weak_points.md`
   - `progress/anki_update_notice.md`

## Answer Review Workflow

When reviewing an answer:

1. Read the problem file.
2. Read the answer file.
3. Identify expected issue_ids.
4. Read relevant files under `materials_structured/`.
5. Evaluate only against structured materials.
6. Score:
   - issue spotting
   - keyword match
   - structure match
   - conclusion match
   - application quality
7. Generate:
   - `reviews/{attempt_id}_review.md`
   - `reviews/{attempt_id}_review.json`
8. Update:
   - attempts
   - issue_results
   - keyword_results
   - conclusion_results
   - review_queue
   - weak_points
   - anki_candidates

## Weakness-Based Card Update Rule

If a user repeatedly misses the same issue, keyword, conclusion, or application checkpoint, update or create an Anki candidate.

Rules:

- First minor miss: add to review_queue only.
- Second miss: create or update an Anki candidate.
- Wrong conclusion: create candidate immediately.
- Missed issue: create issue_outline or keyword_recall candidate after repetition.
- Application weakness: create application_checkpoint card only if source checkpoint exists.
- Unsupported rule: do not create card; mark `자료 부족—보류`.

## Card Update Priority

Card export priority should be calculated using:

- current category progress
- issue importance
- weakness severity
- repeat error count
- recency
- whether the card has source location
- whether the card is already exported
- whether the card is a duplicate

Suggested formula:

priority =
  importance * 10
  + repeat_error_count * 15
  + weakness_severity * 12
  + current_category_bonus
  + due_soon_bonus
  - duplicate_penalty
  - no_source_penalty

## Batch Export Rule

Do not export cards every day unless explicitly requested.

Generate a batch when one of the following is true:

- pending cards in category >= 50
- last export was more than 7 days ago
- category progress milestone reached
- repeated mistake cards >= 10
- user explicitly requests export

Batch rules:

1. Use category-level deck from `category_catalog.csv`.
2. Include only cards with valid source.
3. Exclude `자료 부족—보류`.
4. Exclude duplicates.
5. Keep `note_key` stable.
6. Limit repeated mistake cards.
7. Generate CSV under `cards_batches/`.
8. Record batch in `anki_batches`.
9. Update `progress/anki_update_notice.md`.

## CSV Format

Use this format for Anki CSV exports:

```csv
#separator:Comma
#html:true
#notetype:LawBasic
#deck column:2
#tags column:7
#columns:note_key,deck,front,back,extra,source,tags
```

Fields:

1. note_key
2. deck
3. front
4. back
5. extra
6. source
7. tags

## Duplicate Prevention

Before creating a card:

1. Check same `note_key`.
2. Check same `issue_id + card_type + normalized_front`.
3. If exported, update existing candidate instead of creating a new one.
4. If pending, merge with existing pending card.
5. If rejected, do not recreate unless user explicitly allows.

## Import Completion Workflow

When the user says a batch was imported into Anki:

1. Set `anki_batches.status = imported`.
2. Set `anki_batches.imported_at`.
3. Set included `anki_candidates.status = exported`.
4. Move CSV from `cards_batches/` to `cards_exported/`.
5. Update `progress/progress_dashboard.md`.
6. Update `progress/anki_update_notice.md`.

## Important Constraint

Codex manages the card pool.
Anki schedules memory reviews.

Do not make Anki the progress database.
Do not make Anki the weakness analysis system.
```

---

# 7. Config 파일

## 7.1 `config/categories.yml`

다음은 예시값이다.  
실제 과목 편성에 맞게 수정 가능하다.

```yaml
categories:
  헌법_기본권:
    subject_group: 공법
    subject: 헌법
    category_name: 기본권
    deck: "Law::공법::헌법_기본권"
    weekly_export_limit: 80
    daily_new_limit_hint: 25
    status: active

  헌법_통치구조:
    subject_group: 공법
    subject: 헌법
    category_name: 통치구조
    deck: "Law::공법::헌법_통치구조"
    weekly_export_limit: 50
    daily_new_limit_hint: 15
    status: active

  행정법_행정작용:
    subject_group: 공법
    subject: 행정법
    category_name: 행정작용
    deck: "Law::공법::행정법_행정작용"
    weekly_export_limit: 70
    daily_new_limit_hint: 20
    status: active

  행정법_행정쟁송:
    subject_group: 공법
    subject: 행정법
    category_name: 행정쟁송
    deck: "Law::공법::행정법_행정쟁송"
    weekly_export_limit: 80
    daily_new_limit_hint: 25
    status: active

  민법_민총:
    subject_group: 민사
    subject: 민법
    category_name: 민총
    deck: "Law::민사::민법_민총"
    weekly_export_limit: 80
    daily_new_limit_hint: 25
    status: active

  민법_물권:
    subject_group: 민사
    subject: 민법
    category_name: 물권
    deck: "Law::민사::민법_물권"
    weekly_export_limit: 80
    daily_new_limit_hint: 25
    status: active

  민법_채권총론:
    subject_group: 민사
    subject: 민법
    category_name: 채권총론
    deck: "Law::민사::민법_채권총론"
    weekly_export_limit: 100
    daily_new_limit_hint: 30
    status: active

  민법_채권각론:
    subject_group: 민사
    subject: 민법
    category_name: 채권각론
    deck: "Law::민사::민법_채권각론"
    weekly_export_limit: 100
    daily_new_limit_hint: 30
    status: active

  민소법_심리증거:
    subject_group: 민사
    subject: 민소법
    category_name: 심리증거
    deck: "Law::민사::민소법_심리증거"
    weekly_export_limit: 70
    daily_new_limit_hint: 20
    status: active

  형법_총론:
    subject_group: 형사
    subject: 형법
    category_name: 총론
    deck: "Law::형사::형법_총론"
    weekly_export_limit: 80
    daily_new_limit_hint: 25
    status: active

  형법_개인적법익:
    subject_group: 형사
    subject: 형법
    category_name: 개인적법익
    deck: "Law::형사::형법_개인적법익"
    weekly_export_limit: 80
    daily_new_limit_hint: 25
    status: active

  형소법_수사:
    subject_group: 형사
    subject: 형소법
    category_name: 수사
    deck: "Law::형사::형소법_수사"
    weekly_export_limit: 80
    daily_new_limit_hint: 25
    status: active

  형소법_증거:
    subject_group: 형사
    subject: 형소법
    category_name: 증거
    deck: "Law::형사::형소법_증거"
    weekly_export_limit: 80
    daily_new_limit_hint: 25
    status: active
```

---

## 7.2 `config/anki_rules.yml`

```yaml
anki:
  export_mode: batch_csv
  direct_ankiweb_update: false
  direct_ankiconnect_update: false

  note_type: LawBasic
  csv_columns:
    - note_key
    - deck
    - front
    - back
    - extra
    - source
    - tags

  note_key_format: "{issue_id}::{card_type}::{sequence}"

  allowed_card_types:
    - requirement
    - case_law
    - statute_structure
    - issue_outline
    - keyword_recall
    - conclusion_pattern
    - application_checkpoint
    - repeated_mistake

  excluded_card_types:
    - full_model_answer
    - unsupported_rule
    - one_time_minor_error

  batch_triggers:
    pending_cards_min: 50
    days_since_last_export: 7
    repeated_error_cards_min: 10
    category_progress_milestone: true

  limits:
    default_batch_limit: 80
    repeated_mistake_limit: 15
    max_new_cards_per_category_per_week: 100
    max_cards_without_manual_review: 0

  duplicate_check:
    use_note_key: true
    use_issue_cardtype_front_hash: true
    update_existing_if_exported: true
    merge_if_pending: true
    do_not_recreate_rejected: true

  export_statuses:
    - draft
    - pending
    - approved
    - batched
    - exported
    - updated
    - suspended
    - rejected

  priority_weights:
    importance: 10
    repeat_error_count: 15
    weakness_severity: 12
    current_category_bonus: 20
    due_soon_bonus: 10
    no_source_penalty: 100
    duplicate_penalty: 1000
```

---

## 7.3 `config/review_rules.yml`

```yaml
review:
  intervals:
    missed_issue: 1
    wrong_conclusion: 1
    keyword_score_below_50: 2
    structure_score_below_70: 3
    application_score_below_60: 2
    stable_pass: 7

  weakness_thresholds:
    repeated_error_count: 2
    severe_keyword_score: 0.5
    severe_structure_score: 0.7
    severe_application_score: 0.6

  card_creation:
    first_minor_error: review_queue_only
    second_error: create_or_update_anki_candidate
    wrong_conclusion: create_immediately
    missed_issue: create_after_repetition
    application_weakness: create_only_if_checkpoint_exists
```

---

## 7.4 `config/scoring_rules.yml`

```yaml
scoring:
  total_score:
    issue_spotting: 0.25
    keyword_match: 0.20
    structure_match: 0.20
    conclusion_match: 0.15
    application: 0.20

  issue_spotting:
    detected: 1.0
    partially_detected: 0.5
    missed: 0.0

  conclusion:
    match: 1.0
    partially_match: 0.5
    mismatch: 0.0
    insufficient_source: null

  application:
    requires_fact_to_rule_link: true
    pure_rule_statement_without_facts_max_score: 0.5
    missing_core_fact_max_score: 0.6
    unsupported_application: null

  source_policy:
    unsupported_rule: "자료 부족—보류"
    missing_source_location: "보류"
```

---

## 7.5 `config/notification_rules.yml`

```yaml
notifications:
  anki_update_notice:
    enabled: true
    triggers:
      pending_cards_min: 50
      days_since_last_export: 7
      repeated_error_cards_min: 10
      category_progress_milestone: true

  dashboard_warnings:
    weak_issue_count_min: 5
    overdue_review_count_min: 5
    application_score_warning_below: 0.6
    conclusion_error_count_warning: 2
```

---

# 8. Data CSV 스키마

## 8.1 `data/category_catalog.csv`

```csv
category_id,subject_group,subject,category_name,anki_deck,weekly_export_limit,daily_new_limit_hint,status
헌법_기본권,공법,헌법,기본권,Law::공법::헌법_기본권,80,25,active
행정법_행정쟁송,공법,행정법,행정쟁송,Law::공법::행정법_행정쟁송,80,25,active
민법_채권총론,민사,민법,채권총론,Law::민사::민법_채권총론,100,30,active
형법_총론,형사,형법,총론,Law::형사::형법_총론,80,25,active
```

위 내용은 예시다.  
실제 category는 사용자가 교재 분류에 맞게 수정한다.

---

## 8.2 `data/issue_catalog.csv`

```csv
issue_id,subject_group,subject,category_id,area,topic,title,source_file,source_location,difficulty,importance,status
헌법_집회의자유_금지통고_001,공법,헌법,헌법_기본권,기본권,집회의 자유,집회금지통고,materials_structured/공법/헌법_기본권/집회의자유_금지통고.md,집회의 자유 > 금지통고,4,5,active
민법_채권자대위권_001,민사,민법,민법_채권총론,채권총론,채권자대위권,채권자대위권 요건,materials_structured/민사/민법_채권총론/채권자대위권.md,채권자대위권 > 요건,4,5,active
```

위 내용은 예시다.

---

## 8.3 `data/problem_catalog.csv`

```csv
problem_id,subject_group,subject,category_id,area,topic,problem_file,issue_ids,estimated_minutes,difficulty,status,planned_date
헌법_사례_001,공법,헌법,헌법_기본권,기본권,집회의 자유,problems/헌법_사례_001.md,"헌법_집회의자유_금지통고_001",30,4,not_started,
민법_사례_001,민사,민법,민법_채권총론,채권총론,채권자대위권,problems/민법_사례_001.md,"민법_채권자대위권_001",40,4,not_started,
```

위 내용은 예시다.

---

# 9. Markdown 구조화 스키마

각 쟁점 정리 Markdown은 다음 구조를 따른다.

예시:

```markdown
---
issue_id: 헌법_집회의자유_금지통고_001
subject_group: 공법
subject: 헌법
category_id: 헌법_기본권
area: 기본권
topic: 집회의 자유
title: 집회금지통고
issue_tags:
  - 집회의자유
  - 금지통고
  - 사전허가금지
  - 과잉금지원칙
required_keywords:
  - 집회의 자유
  - 금지통고
  - 구체적 위험
  - 직접·명백한 위험
  - 교통소통
aliases:
  구체적 위험:
    - 직접·명백한 위험
    - 추상적 위험만으로는 부족
    - 막연한 우려만으로는 부족
conclusion_patterns:
  - 금지통고 위헌 가능성 높음
  - 단순 교통불편만으로는 금지통고 곤란
answer_structure:
  - 보호범위
  - 제한 여부
  - 법률유보
  - 사전허가금지
  - 과잉금지원칙
  - 구체적 위험성 포섭
application_checkpoints:
  - 단순 교통불편과 구체적 위험을 구별할 것
  - 막연한 우려만으로 금지할 수 없음을 사안 사실에 연결할 것
source:
  file: 헌법교재.md
  location: 집회의 자유 > 집회금지통고
---

# 법리

# 답안용 문구

# 포섭 체크포인트

# 판례 키워드

# 주의할 오답

# Anki 후보

## requirement

## case_law

## issue_outline

## keyword_recall

## application_checkpoint
```

주의:

- 위 내용은 예시다.
- 실제 법리와 키워드는 사용자의 Markdown 교재에서만 추출한다.
- source가 불명확하면 카드 생성 및 감점 판단에 사용하지 않는다.

---

# 10. SQLite 스키마

Codex는 `scripts/init_db.py`에서 다음 테이블을 생성해야 한다.

```sql
CREATE TABLE IF NOT EXISTS categories (
  category_id TEXT PRIMARY KEY,
  subject_group TEXT NOT NULL,
  subject TEXT NOT NULL,
  category_name TEXT NOT NULL,
  anki_deck TEXT NOT NULL,
  weekly_export_limit INTEGER DEFAULT 80,
  daily_new_limit_hint INTEGER DEFAULT 25,
  status TEXT DEFAULT 'active',
  planned_start_date TEXT,
  planned_end_date TEXT,
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS issues (
  issue_id TEXT PRIMARY KEY,
  subject_group TEXT NOT NULL,
  subject TEXT NOT NULL,
  category_id TEXT NOT NULL,
  area TEXT,
  topic TEXT,
  title TEXT NOT NULL,
  source_file TEXT,
  source_location TEXT,
  difficulty INTEGER,
  importance INTEGER,
  status TEXT DEFAULT 'not_started',
  anki_export_status TEXT DEFAULT 'not_exported',
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS problems (
  problem_id TEXT PRIMARY KEY,
  subject_group TEXT NOT NULL,
  subject TEXT NOT NULL,
  category_id TEXT,
  area TEXT,
  topic TEXT,
  problem_file TEXT NOT NULL,
  estimated_minutes INTEGER,
  difficulty INTEGER,
  status TEXT DEFAULT 'not_started',
  planned_date TEXT,
  completed_at TEXT,
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS problem_issues (
  problem_id TEXT NOT NULL,
  issue_id TEXT NOT NULL,
  expected_weight REAL DEFAULT 1.0,
  PRIMARY KEY (problem_id, issue_id)
);

CREATE TABLE IF NOT EXISTS study_sessions (
  session_id TEXT PRIMARY KEY,
  session_date TEXT NOT NULL,
  subject_group TEXT,
  subject TEXT,
  category_id TEXT,
  study_range TEXT,
  minutes INTEGER,
  session_type TEXT,
  notes TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS attempts (
  attempt_id TEXT PRIMARY KEY,
  problem_id TEXT NOT NULL,
  answer_file TEXT NOT NULL,
  review_md TEXT,
  review_json TEXT,
  attempt_date TEXT NOT NULL,
  subject_group TEXT,
  subject TEXT,
  category_id TEXT,
  total_score REAL,
  issue_spotting_score REAL,
  keyword_score REAL,
  structure_score REAL,
  conclusion_score REAL,
  application_score REAL,
  time_spent_minutes INTEGER,
  notes TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS issue_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  attempt_id TEXT NOT NULL,
  problem_id TEXT NOT NULL,
  issue_id TEXT NOT NULL,
  category_id TEXT,
  detected INTEGER,
  keyword_match REAL,
  structure_match REAL,
  conclusion_match INTEGER,
  application_score REAL,
  missing_keywords TEXT,
  missing_structure TEXT,
  application_feedback TEXT,
  source_file TEXT,
  source_location TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS keyword_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  attempt_id TEXT NOT NULL,
  issue_id TEXT NOT NULL,
  keyword TEXT NOT NULL,
  matched INTEGER,
  matched_alias TEXT,
  source_file TEXT,
  source_location TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS conclusion_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  attempt_id TEXT NOT NULL,
  issue_id TEXT NOT NULL,
  expected_pattern TEXT,
  user_conclusion TEXT,
  match_status TEXT,
  source_file TEXT,
  source_location TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS review_queue (
  queue_id TEXT PRIMARY KEY,
  issue_id TEXT NOT NULL,
  problem_id TEXT,
  category_id TEXT,
  due_date TEXT NOT NULL,
  review_type TEXT NOT NULL,
  reason TEXT,
  priority INTEGER DEFAULT 50,
  status TEXT DEFAULT 'scheduled',
  created_from_attempt_id TEXT,
  completed_at TEXT,
  result_score REAL,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS weak_points (
  issue_id TEXT PRIMARY KEY,
  subject_group TEXT,
  subject TEXT,
  category_id TEXT,
  topic TEXT,
  error_count INTEGER DEFAULT 0,
  repeat_error_count INTEGER DEFAULT 0,
  last_error_date TEXT,
  avg_keyword_score REAL,
  avg_structure_score REAL,
  avg_application_score REAL,
  main_weakness TEXT,
  next_action TEXT,
  severity INTEGER,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS anki_candidates (
  card_id TEXT PRIMARY KEY,
  note_key TEXT UNIQUE NOT NULL,
  issue_id TEXT NOT NULL,
  category_id TEXT,
  source_attempt_id TEXT,
  card_type TEXT NOT NULL,
  deck TEXT NOT NULL,
  front TEXT NOT NULL,
  back TEXT NOT NULL,
  extra TEXT,
  tags TEXT,
  source_file TEXT,
  source_location TEXT,
  status TEXT DEFAULT 'pending',
  export_priority INTEGER DEFAULT 50,
  front_hash TEXT,
  batch_id TEXT,
  exported_at TEXT,
  updated_at TEXT,
  anki_guid TEXT
);

CREATE TABLE IF NOT EXISTS anki_batches (
  batch_id TEXT PRIMARY KEY,
  category_id TEXT NOT NULL,
  subject_group TEXT,
  deck_name TEXT NOT NULL,
  file_path TEXT NOT NULL,
  card_count INTEGER DEFAULT 0,
  new_card_count INTEGER DEFAULT 0,
  update_card_count INTEGER DEFAULT 0,
  repeated_error_card_count INTEGER DEFAULT 0,
  generated_at TEXT NOT NULL,
  imported_at TEXT,
  status TEXT DEFAULT 'generated',
  notes TEXT
);

CREATE TABLE IF NOT EXISTS weekly_stats (
  week_id TEXT PRIMARY KEY,
  start_date TEXT NOT NULL,
  end_date TEXT NOT NULL,
  subject_group TEXT,
  subject TEXT,
  category_id TEXT,
  problems_attempted INTEGER DEFAULT 0,
  avg_total_score REAL,
  avg_issue_spotting_score REAL,
  avg_keyword_score REAL,
  avg_structure_score REAL,
  avg_conclusion_score REAL,
  avg_application_score REAL,
  weak_issue_count INTEGER DEFAULT 0,
  anki_candidates_created INTEGER DEFAULT 0,
  anki_cards_exported INTEGER DEFAULT 0,
  created_at TEXT
);
```

---

# 11. 카드 생명주기

Anki 카드는 전체 보관용으로 만든다.  
그러나 모든 카드가 즉시 Anki로 들어가는 것은 아니다.

```text
draft
  아직 검토 전 초안

pending
  카드 후보로 생성됨

approved
  export 가능 상태

batched
  batch CSV에 포함됨

exported
  Anki Desktop에 import 완료됨

updated
  기존 exported 카드의 내용이 보강됨

suspended
  당분간 export하지 않음

rejected
  카드화하지 않기로 결정
```

## 11.1 상태 전환 규칙

```text
draft → pending
  source가 있고 front/back이 생성된 경우

pending → approved
  중복이 아니고 카드화 가치가 있는 경우

approved → batched
  batch 생성 시 포함된 경우

batched → exported
  사용자가 Anki import 완료를 보고한 경우

exported → updated
  같은 note_key에 대해 내용 보강이 필요한 경우

pending/rejected
  source 부족, 중복, 과도하게 긴 카드, 일회성 실수인 경우 rejected
```

---

# 12. Anki 카드 타입

허용 카드 타입은 다음이다.

| card_type | 용도 |
|---|---|
| requirement | 요건 암기 |
| case_law | 판례 문구·판례 키워드 |
| statute_structure | 조문 구조 |
| issue_outline | 사례형 목차 |
| keyword_recall | 핵심 키워드 써내기 |
| conclusion_pattern | 결론 패턴 |
| application_checkpoint | 포섭 체크포인트 |
| repeated_mistake | 반복 오답 |

생성 금지:

```text
full_model_answer
unsupported_rule
one_time_minor_error
unclear_source
duplicate_note
```

---

# 13. note_key 전략

모든 카드는 고정 `note_key`를 갖는다.

```text
{issue_id}::{card_type}::{sequence}
```

예:

```text
헌법_집회의자유_금지통고_001::keyword_recall::001
헌법_집회의자유_금지통고_001::issue_outline::001
민법_채권자대위권_001::requirement::001
형법_공동정범_001::case_law::001
```

절대 금지:

```text
- 기존 note_key 변경
- 같은 내용에 새 note_key 부여
- 날짜를 note_key에 넣기
```

이유:

```text
note_key가 안정되어야 Anki import 시 같은 노트 업데이트가 가능하다.
```

---

# 14. Anki 덱 구조

쟁점별 덱은 만들지 않는다.  
큰 분류 단위 덱만 사용한다.

## 14.1 권장 덱

```text
Law::공법::헌법_기본권
Law::공법::헌법_통치구조
Law::공법::헌법소송
Law::공법::행정법_행정작용
Law::공법::행정법_행정절차
Law::공법::행정법_행정쟁송
Law::공법::행정법_국가배상손실보상

Law::민사::민법_민총
Law::민사::민법_물권
Law::민사::민법_채권총론
Law::민사::민법_채권각론
Law::민사::민법_가족법
Law::민사::민소법_소송요건
Law::민사::민소법_심리증거
Law::민사::민소법_판결상소재심
Law::민사::상법_회사
Law::민사::상법_기타

Law::형사::형법_총론
Law::형사::형법_개인적법익
Law::형사::형법_사회적법익
Law::형사::형법_국가적법익
Law::형사::형소법_수사
Law::형사::형소법_공판
Law::형사::형소법_증거
Law::형사::형소법_상소재심

Law::사례형목차::공법
Law::사례형목차::민사
Law::사례형목차::형사

Law::반복오답::공법
Law::반복오답::민사
Law::반복오답::형사
```

## 14.2 태그 구조

세부 분류는 태그로 관리한다.

```text
subject_group::공법
subject::헌법
category::헌법_기본권
topic::집회의자유
issue::헌법_집회의자유_금지통고_001
type::keyword_recall
source::헌법교재
```

---

# 15. Anki CSV export 형식

Codex는 batch 생성 시 다음 형식으로 CSV를 만든다.

```csv
#separator:Comma
#html:true
#notetype:LawBasic
#deck column:2
#tags column:7
#columns:note_key,deck,front,back,extra,source,tags
헌법_집회의자유_금지통고_001::keyword_recall::001,Law::공법::헌법_기본권,"집회금지통고 사안에서 금지통고의 핵심 판단 기준은?","단순한 교통불편이나 막연한 우려만으로는 부족하고, 구체적·직접적 위험을 중심으로 판단한다.","반복오답: 포섭 누락 2회","materials_structured/공법/헌법_기본권/집회의자유_금지통고.md > 금지통고","subject_group::공법 subject::헌법 category::헌법_기본권 topic::집회의자유 issue::헌법_집회의자유_금지통고_001 type::keyword_recall"
```

주의:

- 위 행은 예시다.
- 실제 법리 문구는 사용자의 자료에서만 가져온다.
- source 없는 카드는 export하지 않는다.
- `자료 부족—보류` 카드는 export하지 않는다.

---

# 16. 매일 운영 흐름

Codex는 매일 다음 작업을 수행한다.

```text
1. progress.sqlite 읽기
2. category별 진도율 계산
3. 오늘 예정 진도 확인
4. overdue 복습 큐 확인
5. 반복 약점 확인
6. 오늘 할 일 추천
7. Anki pending 카드 수 확인
8. Anki 업데이트 필요 여부 확인
9. today_plan.md 갱신
10. progress_dashboard.md 갱신
11. review_queue.md 갱신
12. weak_points.md 갱신
13. anki_update_notice.md 갱신
```

## 16.1 오늘 계획 예시

```markdown
# 2026-06-16 오늘 공부 계획

## 1. 진도 현황

| 대분류 | 완료율 | 진행중 | 약점 | Anki 대기 |
|---|---:|---:|---:|---:|
| 헌법_기본권 | 42% | 6 | 4 | 76 |
| 행정법_행정쟁송 | 35% | 5 | 6 | 41 |
| 민법_채권총론 | 58% | 3 | 5 | 92 |
| 형법_총론 | 47% | 4 | 3 | 38 |

## 2. 오늘 신규 진도

1. 행정법_행정쟁송: 처분성 사례 1문제
2. 민법_채권총론: 채권자대위권 사례 1문제

## 3. 오늘 복습

1. 헌법_집회의자유_금지통고_001
   - 유형: 포섭 5줄 쓰기
   - 이유: 직접·명백한 위험 포섭 2회 누락

2. 민법_채권자대위권_001
   - 유형: 키워드 써내기
   - 이유: 피보전채권 요건 누락

## 4. 약점 경고

- 공법 포섭 점수 평균 60점 미만
- 민법 채권총론 Anki pending 90장 초과

## 5. Anki 업데이트 상태

- 업데이트 필요 category: 민법_채권총론
- 사유: pending 92장, 마지막 export 후 8일 경과
- 권장 batch: 50장 이하
```

---

# 17. 답안 평가 흐름

사용자가 답안을 제출하면 Codex는 다음을 수행한다.

```text
1. 문제 파일 읽기
2. 답안 파일 읽기
3. problem_catalog에서 예상 issue_id 확인
4. materials_structured에서 해당 issue_id 파일 읽기
5. required_keywords, aliases, answer_structure, conclusion_patterns, application_checkpoints 기준 평가
6. review.md 생성
7. review.json 생성
8. progress.sqlite 업데이트
9. weak_points 업데이트
10. review_queue 업데이트
11. 필요 시 anki_candidates 생성 또는 업데이트
```

## 17.1 평가 기준

```text
쟁점 발견:
  expected issue_id가 답안에 드러나는지

키워드:
  required_keywords와 aliases 기준

구조:
  answer_structure 순서와 주요 항목 포함 여부

결론:
  conclusion_patterns와 실질적으로 일치하는지

포섭:
  application_checkpoints의 사실-법리 연결 여부
```

## 17.2 평가 JSON 예시

```json
{
  "attempt_id": "헌법_사례_001_2026-06-16",
  "problem_id": "헌법_사례_001",
  "subject_group": "공법",
  "subject": "헌법",
  "category_id": "헌법_기본권",
  "scores": {
    "total": 72,
    "issue_spotting": 80,
    "keyword_match": 70,
    "structure_match": 75,
    "conclusion_match": 80,
    "application": 55
  },
  "issue_results": [
    {
      "issue_id": "헌법_집회의자유_금지통고_001",
      "detected": true,
      "missing_keywords": [
        "직접·명백한 위험",
        "단순 교통불편"
      ],
      "structure_missing": [
        "사전허가금지",
        "구체적 위험성 포섭"
      ],
      "conclusion_match": true,
      "application_score": 50,
      "application_feedback": "법리는 제시했으나 교통불편 사실과 직접·명백한 위험 기준의 연결이 부족함.",
      "source": {
        "file": "materials_structured/공법/헌법_기본권/집회의자유_금지통고.md",
        "location": "집회의 자유 > 금지통고"
      }
    }
  ],
  "review_queue_additions": [
    {
      "issue_id": "헌법_집회의자유_금지통고_001",
      "review_type": "mini_application",
      "due_date": "2026-06-18",
      "reason": "직접·명백한 위험 포섭 부족"
    }
  ],
  "anki_candidate_updates": [
    {
      "note_key": "헌법_집회의자유_금지통고_001::keyword_recall::001",
      "action": "create_or_update",
      "reason": "핵심 키워드 반복 누락"
    }
  ]
}
```

위 내용은 형식 예시다.  
실제 문구와 점수는 자료와 답안에 따라 생성한다.

---

# 18. 약점 분석 규칙

## 18.1 약점 유형

```text
missed_issue
missing_keyword
wrong_structure
wrong_conclusion
weak_application
insufficient_source_reference
time_management
```

## 18.2 약점 심각도

```text
severity 1:
  1회성 경미한 누락

severity 2:
  같은 유형 2회 반복

severity 3:
  결론 오류 또는 핵심 쟁점 누락

severity 4:
  같은 쟁점에서 3회 이상 반복

severity 5:
  시험상 고중요도 쟁점에서 반복 결론 오류
```

## 18.3 약점별 조치

| 약점 | 조치 |
|---|---|
| missed_issue | issue_outline 복습 |
| missing_keyword | keyword_recall 카드 후보 |
| wrong_structure | issue_outline 카드 후보 |
| wrong_conclusion | conclusion_pattern 카드 후보 즉시 생성 |
| weak_application | application_checkpoint 단기 복습 |
| 반복 포섭 부족 | repeated_mistake 카드 후보 |
| 일회성 표현 차이 | 카드 생성 금지 |

---

# 19. 복습 큐 규칙

`review_queue`는 Anki 이전의 단기 복습 시스템이다.

## 19.1 review_type

```text
issue_spotting
outline_recall
keyword_recall
mini_application
conclusion_drill
full_rewrite
anki_candidate_review
```

## 19.2 복습 간격

```text
쟁점 자체를 못 찾음: D+1
결론 반대: D+1
키워드 50% 미만: D+2
목차 구조 누락: D+3
포섭 60점 미만: D+2
안정적 통과: D+7
2회 연속 양호: completed 후보
```

---

# 20. 카드 생성 및 업데이트 규칙

## 20.1 기본 원칙

```text
Anki 카드는 전체 보관용으로 생성 가능하다.
하지만 export는 진도와 약점에 따라 제한한다.
```

## 20.2 카드 생성 조건

카드 생성 가능:

```text
- 요건 암기 가치 있음
- 판례 문구 암기 가치 있음
- 조문 구조 암기 가치 있음
- 사례형 목차 암기 가치 있음
- 핵심 키워드 반복 누락
- 결론 패턴 오류
- 포섭 체크포인트 반복 누락
- source.file과 source.location이 명확함
```

카드 생성 금지:

```text
- 자료 부족—보류
- source 없음
- 너무 긴 모범답안 전체
- 단순 표현 차이
- 1회성 사소한 실수
- 이미 같은 note_key 존재
- 기존 rejected 카드
```

## 20.3 반복 오답 카드 업데이트

반복 오답이 발생하면 새 카드를 무조건 만들지 않는다.

우선순위:

```text
1. 같은 note_key 카드가 있으면 back/extra를 보강한다.
2. 같은 issue_id + card_type + normalized_front가 있으면 병합한다.
3. 없으면 새 candidate 생성.
4. 이미 exported된 카드라면 status를 updated로 바꾸고 다음 batch에 업데이트 카드로 포함한다.
```

---

# 21. 카드 우선순위 알고리즘

Codex는 batch 생성 시 다음 점수로 우선순위를 계산한다.

```text
priority =
  importance * 10
  + repeat_error_count * 15
  + weakness_severity * 12
  + current_category_bonus
  + due_soon_bonus
  + conclusion_error_bonus
  + application_weakness_bonus
  - duplicate_penalty
  - no_source_penalty
```

## 21.1 보너스/패널티

```text
current_category_bonus:
  현재 진도 category면 +20

due_soon_bonus:
  복습 예정일이 지났으면 +10

conclusion_error_bonus:
  결론 오류 카드면 +20

application_weakness_bonus:
  포섭 약점 카드면 +10

duplicate_penalty:
  중복이면 -1000

no_source_penalty:
  source 없으면 -100
```

---

# 22. Anki 업데이트 필요 고지 규칙

Codex는 매일 `check_anki_update_needed.py`를 실행한다.

업데이트 필요 조건:

```text
1. category별 pending 카드가 50장 이상
2. 마지막 export 후 7일 이상 경과
3. 반복오답 카드가 10장 이상
4. category 진도 milestone 도달
5. 사용자가 명시적으로 요청
```

## 22.1 `anki_update_notice.md` 예시

```markdown
# Anki 업데이트 필요

## 우선순위: 높음

### 대상
- category_id: 민법_채권총론
- deck: Law::민사::민법_채권총론

### 사유
- 마지막 export 후 8일 경과
- pending 카드 92장
- 반복오답 카드 11장
- 완료된 쟁점 9개

### 권장 batch
- 총 카드: 50장 이하
- 반복오답 카드: 10장 이하
- 업데이트 카드: 제한 없음
- 신규 카드: 40장 이하

### 실행 명령
```bash
python scripts/generate_anki_batch.py --category 민법_채권총론 --limit 50
```

### import 후 입력할 문구
`cards_batches/[파일명].csv Anki import 완료`
```

---

# 23. Batch 생성 규칙

Codex는 `generate_anki_batch.py`를 구현한다.

## 23.1 입력

```text
- progress/progress.sqlite
- data/category_catalog.csv
- config/anki_rules.yml
- cards_pending/
```

## 23.2 처리

```text
1. category_id 기준 후보 카드 조회
2. status pending/approved/updated만 조회
3. source 없는 카드 제외
4. 자료 부족—보류 카드 제외
5. 중복 note_key 제거
6. priority 계산
7. limit만큼 선택
8. repeated_mistake_limit 적용
9. CSV 생성
10. anki_batches 테이블 기록
11. anki_candidates.status = batched
12. progress/anki_update_notice.md 갱신
```

## 23.3 출력

```text
cards_batches/YYYY-WW_{category_id}_batch.csv
```

예:

```text
cards_batches/2026-W25_민법_채권총론_batch.csv
```

---

# 24. Anki import 완료 처리

사용자가 다음처럼 말하면:

```text
cards_batches/2026-W25_민법_채권총론_batch.csv Anki import 완료
```

Codex는 다음을 수행한다.

```text
1. anki_batches.status = imported
2. anki_batches.imported_at = 오늘 날짜
3. 해당 batch_id의 anki_candidates.status = exported
4. 해당 CSV 파일을 cards_exported/로 이동
5. progress_dashboard.md 갱신
6. anki_update_notice.md 갱신
```

---

# 25. 주간 리포트

Codex는 매주 `generate_weekly_report.py`를 실행할 수 있어야 한다.

## 25.1 포함 내용

```text
1. 과목별 푼 문제 수
2. category별 진도율
3. 평균 점수
4. 쟁점 발견 점수 추이
5. 키워드 점수 추이
6. 구조 점수 추이
7. 결론 오류 횟수
8. 포섭 점수 낮은 쟁점
9. 반복 오답 TOP 10
10. Anki 후보 생성 수
11. Anki batch 생성 수
12. Anki import 완료 수
13. 다음 주 우선순위
```

## 25.2 출력

```text
progress/weekly_report.md
```

---

# 26. 스크립트 명세

## 26.1 `scripts/init_db.py`

역할:

```text
- progress/progress.sqlite 생성
- 모든 테이블 생성
- 필요한 index 생성
```

## 26.2 `scripts/import_catalogs.py`

역할:

```text
- data/category_catalog.csv를 categories 테이블로 import
- data/issue_catalog.csv를 issues 테이블로 import
- data/problem_catalog.csv를 problems 및 problem_issues로 import
```

## 26.3 `scripts/plan_today.py`

역할:

```text
- 오늘 공부 계획 생성
- overdue 복습 조회
- 약점 조회
- 신규 진도 추천
- today_plan.md 생성
```

## 26.4 `scripts/review_answer.py`

역할:

```text
- 문제 파일과 답안 파일 읽기
- materials_structured 기준 평가
- review.md 생성
- review.json 생성
- attempts, issue_results, keyword_results, conclusion_results 업데이트
```

## 26.5 `scripts/update_review_queue.py`

역할:

```text
- review.json 기준으로 복습 큐 생성
- due_date 계산
- review_type 결정
```

## 26.6 `scripts/analyze_weak_points.py`

역할:

```text
- issue_results 누적 분석
- weak_points 테이블 업데이트
- progress/weak_points.md 생성
```

## 26.7 `scripts/check_anki_update_needed.py`

역할:

```text
- category별 pending 카드 수 확인
- 마지막 export 이후 경과일 확인
- 반복오답 카드 수 확인
- 업데이트 필요 category 판단
- anki_update_notice.md 생성
```

## 26.8 `scripts/generate_anki_batch.py`

역할:

```text
- category별 Anki batch CSV 생성
- priority 계산
- limit 적용
- 중복 제거
- anki_batches 기록
```

## 26.9 `scripts/mark_anki_exported.py`

역할:

```text
- 사용자가 import 완료한 batch를 exported 처리
- CSV를 cards_exported/로 이동
- dashboard 갱신
```

## 26.10 `scripts/generate_dashboard.py`

역할:

```text
- progress_dashboard.md 갱신
- category별 진도율
- 약점
- 복습 due
- Anki pending 현황 출력
```

## 26.11 `scripts/generate_weekly_report.py`

역할:

```text
- weekly_report.md 생성
- weekly_stats 테이블 업데이트
```

---

# 27. Codex에게 최초로 입력할 프롬프트

다음 프롬프트를 Codex에 입력한다.

```text
이 저장소는 로스쿨 사례형 답안 훈련, 진도관리, 약점 분석, Anki 장기복습 카드풀 관리를 위한 프로젝트다.

CODEX_BOOTSTRAP_REPORT.md를 읽고 그 지시를 기준으로 초기 구현을 진행하라.

작업:
1. 보고서의 폴더 구조를 생성하라.
2. AGENTS.md, PROJECT_CONTEXT.md, DECISIONS.md를 생성하라.
3. config/*.yml 파일을 생성하라.
4. data/*.csv 기본 스키마와 예시 행을 생성하라.
5. scripts/init_db.py를 작성하라.
6. progress/progress.sqlite를 초기화하라.
7. scripts/import_catalogs.py를 작성하라.
8. scripts/generate_dashboard.py의 최소 버전을 작성하라.
9. scripts/check_anki_update_needed.py의 최소 버전을 작성하라.
10. scripts/generate_anki_batch.py의 최소 버전을 작성하라.

제약:
- 외부 법학 지식은 사용하지 말 것.
- 법리 예시는 보고서에 있는 예시 외에는 만들지 말 것.
- 사용자의 실제 자료가 없는 경우 .gitkeep 또는 placeholder만 생성할 것.
- 모든 자동화의 원장은 progress/progress.sqlite로 둘 것.
- AnkiWeb 직접 업데이트 기능은 만들지 말 것.
```

---

# 28. 매일 시작 프롬프트

```text
AGENTS.md와 PROJECT_CONTEXT.md 기준으로 오늘 공부 계획을 생성하라.

입력:
- progress/progress.sqlite
- data/category_catalog.csv
- data/issue_catalog.csv
- data/problem_catalog.csv
- progress/review_queue.md
- progress/weak_points.md

작업:
1. 과목/대분류별 진도율을 계산하라.
2. overdue 복습 항목을 찾으라.
3. 반복 약점 issue_id를 우선순위화하라.
4. 오늘 할 신규 진도와 복습을 추천하라.
5. Anki pending 카드 수를 category별로 계산하라.
6. Anki batch 생성이 필요한 category를 표시하라.
7. progress/today_plan.md를 갱신하라.
8. progress/progress_dashboard.md를 갱신하라.
9. progress/anki_update_notice.md를 필요 시 생성하라.

제약:
- Anki에 직접 import하지 말 것.
- 카드 후보는 생성하되, batch export는 업데이트 필요 조건을 만족할 때만 제안할 것.
- 사례형 포섭 약점은 Anki로 넘겼더라도 Codex review_queue에 남길 것.
```

---

# 29. 답안 평가 프롬프트

```text
AGENTS.md 기준으로 다음 답안을 평가하고 진도 DB를 업데이트하라.

문제:
problems/[problem_id].md

답안:
answers/[answer_file].md

기준 자료:
materials_structured/[subject_group]/[category_id]/

규칙:
1. 외부 법학 지식 사용 금지.
2. materials_structured에 없는 법리는 "자료 부족—보류"로 처리.
3. issue_id 기준으로 평가.
4. required_keywords와 aliases를 기준으로 키워드 일치도를 계산.
5. answer_structure 기준으로 목차 구조를 평가.
6. conclusion_patterns 기준으로 결론 일치 여부를 평가.
7. application_checkpoints 기준으로 포섭을 평가.
8. 모든 감점에는 source.file과 source.location을 남겨라.
9. review.md와 review.json을 생성하라.
10. progress.sqlite의 attempts, issue_results, keyword_results, conclusion_results, weak_points, review_queue를 업데이트하라.
11. 반복 오답 또는 중대한 오류만 anki_candidates에 생성 또는 업데이트하라.
```

---

# 30. Anki batch 생성 프롬프트

```text
AGENTS.md와 config/anki_rules.yml 기준으로 다음 category의 Anki 업데이트용 batch CSV를 생성하라.

대상 category:
[예: 민법_채권총론]

입력:
- progress/progress.sqlite
- data/category_catalog.csv
- config/anki_rules.yml
- cards_pending/

조건:
1. status가 pending, approved, updated인 카드만 포함하라.
2. source_file과 source_location이 없는 카드는 제외하라.
3. "자료 부족—보류" 카드는 제외하라.
4. 동일 note_key가 이미 exported 상태이면 update 대상인지 확인하라.
5. 같은 note_key가 pending에 중복되어 있으면 최신 back/extra만 반영하라.
6. 최대 [N]장으로 제한하라.
7. repeated_mistake 카드는 최대 [M]장으로 제한하라.
8. deck은 category_catalog.csv의 anki_deck을 사용하라.
9. tags에는 subject_group, subject, category, issue_id, card_type을 포함하라.

출력:
- cards_batches/[YYYY-WW]_[category_id]_batch.csv
- anki_batches 테이블 기록
- anki_candidates.status를 batched로 업데이트
- progress/anki_update_notice.md 갱신
```

---

# 31. Anki import 완료 프롬프트

```text
다음 Anki batch를 Anki Desktop에 import 완료했다.

파일:
cards_batches/[파일명].csv

작업:
1. anki_batches.status를 imported로 변경하라.
2. imported_at을 오늘 날짜로 기록하라.
3. 해당 batch에 포함된 anki_candidates.status를 exported로 변경하라.
4. cards_batches/의 파일을 cards_exported/로 이동하라.
5. progress/anki_update_notice.md를 갱신하라.
6. progress_dashboard.md의 Anki pending 수를 갱신하라.
```

---

# 32. 주간 리포트 프롬프트

```text
AGENTS.md 기준으로 이번 주 공부 리포트를 생성하라.

기간:
[YYYY-MM-DD] ~ [YYYY-MM-DD]

입력:
- progress/progress.sqlite
- reviews/*.json
- progress/review_queue.md
- progress/weak_points.md
- cards_pending/
- cards_batches/
- cards_exported/

출력:
- progress/weekly_report.md

포함할 것:
1. 과목별 푼 문제 수
2. category별 진도율
3. 평균 점수
4. 쟁점 발견 점수 추이
5. 키워드 일치도 추이
6. 구조 점수 추이
7. 결론 오류 횟수
8. 포섭 점수 낮은 쟁점
9. 반복 오답 TOP 10
10. Anki 후보 생성 수
11. Anki batch 생성 수
12. Anki import 완료 수
13. 다음 주 우선 복습 쟁점
14. Anki 카드 과잉 여부 경고
```

---

# 33. MVP 구현 우선순위

Codex는 한 번에 모든 기능을 완성하려 하지 말고 다음 순서로 구현한다.

## 1단계

```text
- 폴더 구조
- AGENTS.md
- PROJECT_CONTEXT.md
- DECISIONS.md
- config/*.yml
- data/*.csv
```

## 2단계

```text
- init_db.py
- import_catalogs.py
- progress.sqlite 초기화
```

## 3단계

```text
- generate_dashboard.py
- plan_today.py
- check_anki_update_needed.py
```

## 4단계

```text
- generate_anki_batch.py
- mark_anki_exported.py
```

## 5단계

```text
- review_answer.py
- update_review_queue.py
- analyze_weak_points.py
```

## 6단계

```text
- generate_weekly_report.py
```

---

# 34. 구현 시 주의사항

## 34.1 법학 판단 오류 방지

```text
- 외부 법학 지식 사용 금지
- issue_id 기준 평가
- source 없는 감점 금지
- 자료 부족 시 보류
```

## 34.2 카드 폭증 방지

```text
- batch limit 적용
- repeated_mistake_limit 적용
- 1회성 실수 카드화 금지
- 중복 note_key 금지
```

## 34.3 Anki와 Codex 불일치 방지

```text
- Anki import 후 반드시 mark_anki_exported.py 실행
- cards_batches → cards_exported 이동
- anki_batches.status 갱신
- anki_candidates.status 갱신
```

## 34.4 Markdown과 SQLite 불일치 방지

```text
- SQLite를 원장으로 한다.
- Markdown dashboard는 SQLite에서 재생성한다.
- 사람이 Markdown dashboard만 수정하지 않는다.
```

---

# 35. 최종 운영 원칙

이 시스템의 최종 운영 원칙은 다음 한 문장이다.

```text
Anki는 전체 보관용 지식 저장소와 장기복습 엔진으로 두고,
Codex/SQLite가 진도·약점·단기복습·사례형 평가·카드 업데이트 판단을 담당한다.
```

Codex는 세부 issue_id를 추적하고, Anki는 큰 category 덱에서 복습하게 한다.

---

# 36. Codex 최종 작업 지시

Codex는 이 보고서를 읽고 다음 산출물이 생성되면 1차 작업 완료로 본다.

```text
AGENTS.md
PROJECT_CONTEXT.md
DECISIONS.md

config/categories.yml
config/anki_rules.yml
config/review_rules.yml
config/scoring_rules.yml
config/notification_rules.yml

data/category_catalog.csv
data/issue_catalog.csv
data/problem_catalog.csv
data/syllabus.csv

scripts/init_db.py
scripts/import_catalogs.py
scripts/generate_dashboard.py
scripts/check_anki_update_needed.py
scripts/generate_anki_batch.py
scripts/mark_anki_exported.py

progress/progress.sqlite
progress/progress_dashboard.md
progress/anki_update_notice.md
```

1차 작업에서는 실제 법학 내용 생성은 하지 않는다.  
실제 법학 내용은 사용자의 `materials_raw/`와 `materials_structured/` 자료가 들어온 뒤 별도 작업으로 수행한다.
````

---

이 보고서에서 **예시**라고 표시한 부분은 나중에 교재 분류와 실제 자료 기준으로 바꾸면 됩니다. 나머지는 그대로 프로젝트 운영 규칙으로 써도 됩니다.