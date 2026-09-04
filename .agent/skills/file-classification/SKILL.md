---
name: file-classification
description: 파일 분류 및 정리(백스톱·레거시 inbox 청소용). 미분류 파일 검색, 분류 규칙 적용, 파일명 변경. "파일 정리", "분류", "미분류 파일", "새 파일 정리" 요청 시 사용. 신규 생성물의 분류는 생성 시점에 resolve_output_path.py가 담당(#42) — 본 스킬은 이미 쌓인 미분류 정리용.
---

# 파일 분류 Skill

<!-- @rule: CLAUDE.md#15 Verify-Before-Act -->

## Quick Start

기본 실행(법학 도메인, DRY-RUN):

```powershell
python .agent/skills/file-classification/scripts/classification_v3.py --domain legal
```

`5.기타/_inbox`는 기본적으로 임시 처리 영역이며(특히 전사 파이프라인), 임시파일은 기본 스킵됩니다.

입시 도메인 분리 실행(DRY-RUN):

```powershell
python .agent/skills/file-classification/scripts/classification_v3.py --domain admission
```

실제 변경 실행:

```powershell
python .agent/skills/file-classification/scripts/classification_v3.py --domain legal --execute
```

잠금(검토 완료) 등록:

```powershell
python .agent/skills/file-classification/scripts/classification_v3.py --domain legal --mark-complete "1.민사/송영곤_기본민법/교재/파일.pdf" --execute
```

잠금 해제(명시 요청 파일만):

```powershell
python .agent/skills/file-classification/scripts/classification_v3.py --domain legal --unlock-file "1.민사/송영곤_기본민법/교재/파일.pdf" --execute
```

---

## 주요 기능

### 1. 도메인 분리 실행

```powershell
python scripts/classification_v3.py --domain legal|admission [--root <경로>] [--execute]
```

- `legal`: `1.민사/2.형사/3.공법/4.선택법` 대상
- 기타 분류 불가 파일은 `5.기타/보관/`을 표준으로 사용하고, 레거시 `기타/보관/`은 fallback 으로만 취급
- `admission`: `9.로스쿨입시` 전용
- 기본값은 DRY-RUN
- 기본 대상은 `5.기타/_inbox`의 비임시 파일이며, 임시 전사 파일은 `SKIP_INBOX_TEMP`
- 임시 파일까지 포함하려면 `--include-inbox-temp` 사용
- 현재 자동화는 `5.기타/_inbox` 기준 1차 라우팅만 수행하며, 예외 자동 라우팅은 `서보학_형법1/형법2`, `이진_헌법1`까지만 지원

### 2. 보호 루트 자동 제외

```powershell
python scripts/classification_v3.py --domain legal
```

- 자동 제외: `공유드라이브`, `.agent`, `5.기타/_trash`, `5.기타/_RAG_데이터`, `_원본보관`  (구 `스터디 답안지`는 2026-06-15 해체)

### 3. 완료 잠금(재작업 방지)

```powershell
python scripts/classification_v3.py --domain legal --mark-complete <상대경로> --execute
```

- 키: `relative_path + mtime`
- 잠금 일치 시 `SKIP_LOCKED`
- 파일 수정으로 mtime 변경 시 `REVIEW_REQUIRED(mtime_changed)`로 자동 재검토

### 4. 명시 해제(파일 단위)

```powershell
python scripts/classification_v3.py --domain legal --unlock-file <상대경로> --execute
```

---

## 분류 규칙

권위 규칙: [../../workflows/classification-rules_v2.md](../../workflows/classification-rules_v2.md)

### sync 폴더 정비 전용 룰 (§1-1 핵심 원칙 14·15 — 2026-04-27 추가)

- **0바이트 선처리**: sync 폴더 정비 시 0바이트 `.md`/`.canvas`/`.base` 파일은 **무조건 `_trash/{YYYY-MM-DD}/sync_root/`로 이동**합니다. (글로벌 inbox 처리에는 미적용 — 다른 폴더의 0바이트는 OCR 추출 실패 마커일 수 있음)
- **신설 폴더**: `sync/_inbox/`(임시 격리), `sync/_발제/`(자유형 긴 제목), `9.작업중/클로드/`(운영 메모), `sync/_답안지/{과목}/`(사례형 답안 통합 — 8과목).
- **LLM 콘텐츠 분류**: 의미불명 파일명(`1.md`, `무제 X.md` 등)에 콘텐츠가 있으면 Gemini Flash로 첫 1KB 분석 → 신뢰도 ≥0.85면 자동 라우팅, 미만이면 `_inbox/` 격리.
- **`.hwp` 자동 처리** (§1-1 핵심원칙 16): sync 내 `.hwp`/`.hwpx` 발견 시 `hwp5txt`로 텍스트 추출 → frontmatter 포함 `.md`로 sync에 저장 + `.hwp` 원본은 `_원본보관/hwp_전체/`로 이동(핵심원칙4와 일원화. 구 `9.스터디 답안지/`는 2026-06-15 해체)(공백·이중공백 → `_`, 날짜 ISO화). 한자(甲乙丙丁) 등 자필 답안 원문은 보존(#37 예외).
- 자세한 트리·예시는 권위 규칙 §1-1 참조.

### 파일명 형식

> 상세 규칙: [naming-rules.md](resources/naming-rules.md)

- 고유명사(브랜드명·조어): `책이름_분야_연도` (예: `민법의맥_물권_25`)
- 일반명사(과목명 유사): `강사명_세부과목_연도` (예: `서보학_형법총론_25`)
- 동일 책이름 다수 저자: `강사명_책이름_분야_연도` (예: `강혜림_민법강의_민총_26`)

- 연도: **필수** (강의 연도 2자리)
- 유형은 **폴더 구조**로 관리 (`교재/`, `정리/`, `사례/`, `선택형/`, `기록형/`, `모의답안/`, `전사문/`, `개념/`, `기타/`)
- 폴더명은 `교수명_과목명/` 형식 유지

---

## 스크립트 목록 (v3 우선)

### Python 스크립트

| 파일 | 기능 |
|------|------|
| `classification_v3.py` | 도메인 분리 + 보호루트 가드 + 잠금/해제 + dry-run/execute |
| `find_untyped.py` | 미분류 파일 검색 |
| `reclassify.py` | 분류 규칙 적용 |
| `rename_files.py` | 파일명 변경 |
| `internal_classify.py` | 내부 분류 로직 |
| `apply_types.py` | 유형 라벨 적용 |
| `assign_types.py` | 유형 지정 |
| `check_originals.py` | 원본 파일 확인 |
| `organize_files_reorg.py` | 파일 재정리 |
| `rename_copies.py` | 사본 파일 정리 |

### PowerShell 스크립트

| 파일 | 기능 |
|------|------|
| `classify_inbox.ps1` | 인박스 파일 분류 |
| `rename_files.ps1` | 파일명 일괄 변경 |

> 레거시 스크립트(`reclassify.py`, `rename_files.py`, `classify_inbox.ps1`, `rename_files.ps1` 등)는 과거 규칙/경로를 포함할 수 있으므로 신규 작업에는 `classification_v3.py`만 사용하세요.

---

## 관련 파일

- 분류 규칙: `resources/classification-rules.md`
- 잠금 레지스트리: `../../state/classification_lock.json`
- 기존 로그: `../../state/rename_violations_log.json`, `../../state/naming_issues.json`

