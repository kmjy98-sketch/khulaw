---
name: file_ops_log
description: 파일·폴더 이동·이름변경·복사·trash 이동 시 경로·해시·사유를 master.{csv,jsonl,md} 에 자동 기록. 트리거 "이동", "이름변경", "rename", "move", "옮겨", "trash로", "파일 정리"
triggers: ["이동", "이름변경", "이름 변경", "rename", "move", "옮겨", "옮기", "trash", "휴지통", "파일 정리"]
---

# file_ops_log — 파일 이동·이름변경 자동 로그

CLAUDE.md **#16-C** 의무 로그 시스템. 워크스페이스 내 모든 파일/폴더 이동·이름변경·복사·trash 이동을
`.agent/file_ops_log/master.{csv,jsonl,md}` 에 1작업=1행으로 기록한다.

## 언제 발동하나

다음 작업을 수행할 때 **반드시** 발동:
- 파일/폴더 이동 (move)
- 파일/폴더 이름변경 (rename)
- 파일/폴더 복사 (copy)
- `_trash/{YYYY-MM-DD}/` 로 이동 (delete-to-trash, #16 삭제 대체)

## 표준 필드

| 필드 | 의미 |
|---|---|
| `timestamp` | ISO 8601 (로컬, 초 단위) |
| `operation` | move / rename / copy / delete-to-trash |
| `source_path` | 원본 절대경로 |
| `dest_path` | 대상 경로 또는 신규 이름 |
| `size_bytes` | 파일 크기 |
| `sha256` | 무결성 해시(이동 후 기준) |
| `task_id` | 세션 ID 또는 메모 |
| `reason` | 이동 사유 1줄 |
| `verified` | 전후 sha256 일치 여부 |

## 워크플로우

### 방법 A — 헬퍼가 이동까지 실행 (권장, 자동 검증)

`--execute` 를 주면 사전 sha256 → 이동 → 사후 sha256 대조 → 3개 형식 로그를 한 번에 처리.

```bash
python .agent/scripts/log_file_op.py \
  --op move --src "원본경로" --dst "대상경로" \
  --reason "사유 1줄" --task-id "세션메모" --execute
```

```powershell
.\.agent\scripts\log_file_op.ps1 `
  -Op move -Src "원본경로" -Dst "대상경로" `
  -Reason "사유 1줄" -TaskId "세션메모" -Execute
```

### 방법 B — 도구(Bash mv / Move-Item)로 이동 후 기록만

이미 이동을 끝냈거나 다른 도구로 옮긴 경우, `--execute` 없이 로그만 남긴다.
(대상이 존재하면 자동으로 무결성 확인)

1. **사전 해시**(선택): `sha256sum 원본` 으로 기록해 둠
2. **이동 실행**: `mv` / `Move-Item`
3. **로그 추가**: `python .agent/scripts/log_file_op.py --op move --src ... --dst ... --reason ...`
4. **검증 확인**: 출력의 `검증OK` 확인, master.md 마지막 행 점검

## 절대 규칙

- **공유드라이브(`0.공유드라이브/`) 는 절대 이동·이름변경·복사 금지** (#16-B). 헬퍼도 해당 경로를 차단한다.
- **삭제 금지**: 삭제 대신 항상 `_trash/{YYYY-MM-DD}/` 로 이동(operation=delete-to-trash) (#16).
- **로그 누락 = 작업 무효**: 이동·이름변경 후 로그를 남기지 않으면 작업을 되돌리거나 즉시 보충 기록.
- 로그 파일(master.*)은 손으로 편집하지 않는다(헬퍼만 append).

## 관련 파일

- 헬퍼: `.agent/scripts/log_file_op.py`, `.agent/scripts/log_file_op.ps1`
- 로그: `.agent/file_ops_log/master.{csv,jsonl,md}`
- 레거시 통합본: `.agent/file_ops_log/_legacy_consolidated.csv` (과거 87건)
- 룰: CLAUDE.md #16-C
