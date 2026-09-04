# OCR 정리 파이프라인 인수인계 (2026-04-21)

> 새 대화 시작 시 이 파일만 Read 하면 컨텍스트 복원 완료. 이어서 실행하려면 "handoff_ocr_cleanup_2026-04-21.md 보고 이어서 진행" 지시.

---

## 1. 목표

`sync/_교재원문/**/*.md` 전체(약 3,000 파일, ~240만 행)의 OCR 오인식·띄어쓰기·줄바꿈 오류를 Sonnet으로 검토·수정. 기존 규칙 기반 스크립트는 맥락 오류를 놓침(사용자 확인). LLM 검토로 보강 필요.

---

## 2. 현재 상태

### 완료된 자동 처리 (규칙 기반, 2026-04-20~21)

| 스크립트 | 경로 | 결과 |
|----------|------|------|
| 페이지 마커 정규화 | `.agent/scripts/cleanup_page_markers.py` | 122 파일 / 1,449 라인 (`NNN ¦ 민법재산법` → `<!-- p.NNN -->`) |
| 한자 당사자명 치환 | `.agent/scripts/fix_ocr_hanja.py` | 413 파일 / 16,785건 (`芮/雨/因→병`, `Z→을`, `成/戊→무`) |
| 한글 띄어쓰기 복원 | `.agent/scripts/fix_ocr_spacing.py` | 1,148 파일 / 142,511건 |
| 줄바꿈·인용 분할 결합 | `.agent/scripts/fix_ocr_line_breaks.py` | 1,002 파일 / 2,019+ 결합 |
| MBA 재생성 (10개) | `.agent/scripts/mba_reocr_step1_map.py` + `step2_regenerate.py` | 원본 추출에서 본문 교체 |

**모든 스크립트에 적용된 폴더 제외 규칙**: `_backup_*`, `_trash`, `.*`, `_재추출`, `_재추출본`, `_raw`, `_src`, `_orig`

### 알려진 미해결 문제 (사용자 지적)

- 규칙 기반으로 처리 완료 표시된 파일에도 맥락 오류 잔존
- 예: "실효조항부 손해배상약정" 같은 고유명사 띄어쓰기, 판례번호 연속 라인 내부, 문맥 의존 조사 오인식
- 정규식이 못 잡는 의미·문맥 단위 수정은 LLM 필요

### 백업 위치

`5.기타/_trash/2026-04-21/{hanja_fix,spacing_fix,linebreak_fix,pagemarker_cleanup,mba_reocr}/`
+ `2026-04-20/{linebreak_fix,pagemarker_cleanup,민법_송영곤_쟁점노트}/`
→ 전체 상대 경로 구조 보존됨.

---

## 3. 다음 작업: Sonnet 기반 전과목 파이프라인

### 설계 — 교재 파일 분할 기반 파이프라인

```
[1] 인덱싱           — sync/_교재원문/**/*.md 전체 목록 + 행수 + OCR 잔존 스코어
                       → .agent/state/all_files_index.json

[2] 파일 분할        — 각 .md 파일을 400행 청크로 split
                       · 첫 청크: frontmatter + 본문 시작부 포함
                       · 이후 청크: 본문만 (페이지 마커 기준 자연 경계 우선)
                       · 청크별 고유 ID: {filename}__chunk_{NNN}
                       → .agent/data/ocr_chunks/{교과}/{교재}/{파일명}__chunk_{NNN}.md
                       총 약 6,000 청크

[3] 규칙 정리 (멱등) — 기존 스크립트 재실행 (청크 단위)
                       · cleanup_page_markers.py
                       · fix_ocr_hanja.py
                       · fix_ocr_spacing.py
                       · fix_ocr_line_breaks.py

[4] Sonnet 검토      — **Claude Code 내부 Agent 도구** (API 미사용)
                       · Agent 도구로 sub-agent 병렬 spawn
                       · sub-agent당 청크 20~50개 처리 후 파일 저장
                       · 동시 실행: 4~8 agent (시스템 부하 감안)
                       · 입력: .agent/data/ocr_chunks/...
                       · 출력: .agent/data/ocr_chunks_reviewed/...
                       · 각 agent는 완료 시 JSON 상태 파일 기록

[5] diff 검증 (청크별) — validate_chunk_diff.py
                       · 라인 수 편차 ≤ 5%
                       · 삭제된 라인 = 0
                       · 페이지 마커 보존
                       · 판례 인용(대판 YYYY.M.D.)·조문(**제N조**) 원문 동일성
                       · 실패 청크는 reject → 원본 청크로 대체

[6] 재병합·교체       — merge_and_apply.py
                       · 청크 순서대로 concatenate
                       · 원본 .md 파일 백업 후 교체
                       · 청크 임시 폴더 정리
```

### 모델 결정

**Sonnet 4.5** (또는 4.6) 사용 확정. Claude Code 내부 Agent 도구로 spawn — **API·Batches 사용 안 함**. 사용자 플랜 내 Agent 호출만 사용.

Opus 는 3~5배 비용·시간 대비 이득 없음. 단, 파일럿에서 문제 청크 발견 시 해당 청크만 Opus로 재처리 옵션 유지.

### 프롬프트 원칙 (청크 검토용)

```
역할: OCR 오인식 수정만 수행. 원문 절대 보존.
허용: OCR 글자 오식, 띄어쓰기 복원, 줄바꿈 결합(문장 경계), 페이지 마커 유지
금지: 요약, 주해, 판례/조문 원문 수정, 문장 재작성, 의미 변경
출력: 원본과 동일 행 수 기준 ±5%, 삭제 라인 0
```

### 안전장치

1. 파이프라인 시작 시 전체 `sync/_교재원문/` 스냅샷 → `5.기타/_trash/{date}/full_snapshot/`
2. 청크당 diff 검증 — 라인 편차 > 20% 자동 reject
3. 판례 인용(`대판 YYYY.M.D.`), 조문(`**제N조**`)은 프롬프트에서 "touch X" 강제
4. 파일럿 먼저(20개 파일) → 품질 확인 후 전면

### 비용·시간 추산 (Claude Code Agent 도구, API 미사용)

- 사용자 플랜 내 Agent 호출 → 별도 API 비용 없음
- 제약: Claude Code 세션의 Agent 동시 실행 수 (보통 4~8개 병렬 권장)
- 청크 6,000개 × 평균 처리 20초 / 병렬 6 agent ≈ **6~8시간 소요**
- 청크당 sub-agent가 20~50 청크 묶어 처리하면 agent 호출 수 120~300회 수준
- 파일럿: 20 파일 ≈ 40 청크 → 1 agent 단일 호출로 처리 가능, 약 **5~10분**

---

## 4. 시작 명령 옵션

| 지시 | 동작 |
|------|------|
| "파일럿" | 20개 샘플 파일로 Sonnet 검토 → 결과 diff 리뷰 |
| "전면" | 6,000 청크 전체 Batches API 실행 |
| "수정" | 파이프라인 세부 조정 (프롬프트/청크 크기/제외 규칙 등) |

---

## 5. 핵심 상태 파일

- 재-OCR 후보: `.agent/state/reocr_targets.json` (1,126건 식별됨, 대부분 `_재추출` 소스 제외 후 축소)
- MBA 매핑: `.agent/state/mba_reocr_mapping.json`, `mba_reocr_result.json`, `mba_full_scan.json`
- 이 문서: `.agent/state/handoff_ocr_cleanup_2026-04-21.md`

---

## 6. 즉시 실행 가능한 구현 체크리스트

**구현 스크립트 (신규 작성)**
1. `index_all_files.py` — 전체 .md 인덱싱, OCR 잔존 스코어 계산 → `all_files_index.json`
2. `split_to_chunks.py` — 400행 단위 분할, frontmatter·페이지 마커 경계 보존
3. **(스크립트 없음)** Sonnet 검토는 Agent 도구로 직접 spawn — 아래 "Agent 프롬프트 템플릿" 사용
4. `validate_chunk_diff.py` — 청크별 입출력 diff 검증 + reject 로직
5. `merge_and_apply.py` — 청크 재병합 + 원본 백업 + 교체
6. `run_pipeline.py` — 오케스트레이터 (1, 2, 4, 5 순차 실행; 3은 수동 Agent 호출)

**Agent 프롬프트 템플릿 (Sonnet sub-agent용)**
```
역할: OCR 추출 마크다운 청크의 오인식·띄어쓰기·줄바꿈만 수정. 원문 절대 보존.

입력 경로: {chunk_dir}의 청크 파일 N개 (경로 목록 명시)
출력 경로: {reviewed_dir}에 같은 파일명으로 저장

허용 수정:
- OCR 글자 오식 정정 (예: 기→갑, C^→다, 저I→제)
- 한글 띄어쓰기 복원 (이행불능이된 → 이행불능이 된)
- 줄바꿈 결합 (문장 중간 분할된 라인)
- 페이지 마커 유지 (<!-- p.NNN -->)

금지:
- 문장 삭제/추가
- 요약·주해·번역
- 판례 인용(대판 YYYY.M.D. NNNN다NNNN) 원문 수정
- 조문(**제N조**, **제N조 제M항**) 원문 수정
- frontmatter 변경

검증 규칙: 출력은 입력과 행 수 ±5%, 삭제 라인 0.
```

**파일럿 플로우**
1. 파일 선정: 4과목 × 5개 = 20 파일 (OCR 잔존 스코어 상위)
2. `split_to_chunks.py` 실행 → ~40 청크 생성 (입력 폴더로 복사)
3. Agent 1개 spawn — 40 청크 전부 처리 지시 (subagent_type: general-purpose, model: sonnet)
4. `validate_chunk_diff.py` 실행 → 이상 청크 flag
5. 사용자 샘플 리뷰 → 프롬프트 튜닝
6. 반복 후 전면 실행 승인 받기

**전면 플로우 (파일럿 승인 후)**
1. 전체 인덱스 → 약 3,000 파일
2. 분할 → 약 6,000 청크 (폴더 구조 보존)
3. 청크를 N개 버킷으로 분할 (예: 6 agent × 1,000 청크)
4. Agent 여러 개 동시 spawn (run_in_background=true) — 각 agent가 자기 버킷 처리
5. 모든 agent 완료 대기 후 검증·병합
6. 실패 청크는 별도 agent로 재처리
7. 완료 보고

---

_사용자 환경: Windows 11, bash, 한국어 응답. 민감 규칙은 `C:\Users\111\.claude\CLAUDE.md`와 `H:\내 드라이브\CLAUDE.md` 참조._
