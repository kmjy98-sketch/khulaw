# gemini_ops — Antígravity 작업 감시 인프라

## 디렉터리 구조

```
.auto-memory/gemini_ops/
├── _README.md              ← 이 파일 (운영 규약)
├── _LOG_TEMPLATE.md         ← Antígravity가 따라야 할 로그 양식
├── _watcher.log             ← watcher 자체 로그
├── _watcher_state.json      ← watcher 내부 상태 (mtime 추적)
├── flag.json                ← 검증 결과 (Claude가 읽음)
└── logs/                    ← Antígravity가 작성하는 로그 파일들
    └── YYYY-MM-DD_HHMMSS_{slug}.md
```

## 데이터 흐름

```
[Antígravity]
   ↓ (로그 작성)
logs/YYYY-MM-DD_xxx.md
   ↓ (3초 폴링 감지)
[_gemini_watcher.py]
   ↓ (frontmatter + 본문 파싱)
[_verify_rules.py] → severity 산출
   ↓
flag.json 갱신
   ↓ (다음 Claude Code 세션 시작 시)
[SessionStart hook] → context에 요약 노출
   ↓
[사용자/Claude] → 필요 시 정밀 검토
```

## flag.json 스키마

```json
{
  "updated_at": "2026-05-23T14:35:00",
  "summary": {
    "red": 0,
    "yellow": 1,
    "green": 5,
    "total": 6
  },
  "entries": [
    {
      "log_path": ".auto-memory/gemini_ops/logs/2026-05-23_143000_precedent.md",
      "log_name": "2026-05-23_143000_precedent.md",
      "checked_at": "2026-05-23T14:35:00",
      "severity": "yellow",
      "verify_status": "pending",
      "spec_source": "[[task_precedent_pipeline_2026-05-22]]",
      "violations": [
        {
          "rule": "rule_claim_without_evidence",
          "severity": "yellow",
          "message": "claim_without_evidence: 추측·미검증 단정 표현 → ['확인됨']"
        }
      ]
    }
  ]
}
```

## 검증 룰 요약 (`_verify_rules.py`)

| 룰 | severity | 트리거 |
|----|----------|--------|
| `rule_silent_drop` | red | 로그가 생성·수정했다는 파일이 실재하지 않음 |
| `rule_path_fabrication` | red | 본문 인용 경로(`...`)가 실재하지 않음 |
| `rule_deletion_attempt` | red | 삭제 명령 흔적 (rm, del, Remove-Item 등) |
| `rule_claim_without_evidence` | yellow | "확인됨/검증됨/~인 것 같다" 등 근거 없는 단정 |
| `rule_excessive_modification` | yellow | 변경 파일 수 > 10 |

## 태그 표준 (frontmatter)

| 태그 키 | 값 예시 | 의미 |
|---------|---------|------|
| `gemini-log` | (고정) | Antígravity 작업 로그 표식 |
| `YYYY-MM-DD` | `2026-05-23` | 작업일자 (날짜별 필터링) |
| `verify-status/X` | `pending`, `green`, `yellow`, `red` | 검증 상태 |
| `scope/X` | `판례색인`, `OCR`, `노트정비` | 작업 범위 분류 |

## 백링크 표준 (본문)

본문 "참조" 섹션에서 영향 범위를 명시:

- 지시서 백링크: `[[task_xxx_YYYY-MM-DD]]`
- 대상 파일 백링크: 파일명 stem 사용 `[[_gen_precedent_ox]]`
- 사용자 의도 백링크: 메모리 노트가 있으면 `[[memory/judgment_xxx]]`

검증 실패 시 watcher가 백링크를 따라 영향 범위를 산출합니다.

## 운영 명령

### Watcher 등록 (최초 1회)

```powershell
& "H:\내 드라이브\.agent\scripts\_register_watcher_task.ps1"
```

### 즉시 시작 (등록 후 첫 실행)

```powershell
Start-ScheduledTask -TaskName GeminiOpsWatcher
```

### 상태 확인

```powershell
& "H:\내 드라이브\.agent\scripts\_register_watcher_task.ps1" -Status
```

### 해제

```powershell
& "H:\내 드라이브\.agent\scripts\_register_watcher_task.ps1" -Uninstall
```

### 수동 검증 (watcher 없이 1회 실행)

```bash
python "H:/내 드라이브/.agent/scripts/_gemini_watcher.py"
# Ctrl+C로 중지
```

## SessionStart Hook 동작

Claude Code 세션 시작 시:
1. `flag.json` 읽음
2. `summary.red > 0` 또는 `summary.yellow > 0` 이면 context에 요약 prepend
3. 사용자가 `/감시` 입력 시 정밀 검토 트리거 가능 (별도 설정)

## 주의사항

- `_watcher.log`는 무한 누적되므로 주기적으로 archive로 이동 권장 (월 1회)
- `flag.json`의 entry는 같은 `log_path` 재처리 시 덮어쓰기됨 (이력 추적 X)
- 이력이 필요하면 `logs/` 폴더 자체가 보존되므로 거기서 확인
- 룰 추가/변경: `_verify_rules.py`의 `RULES` 리스트에 함수 추가
