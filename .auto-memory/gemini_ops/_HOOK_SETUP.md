# SessionStart Hook 설정 — 수동 적용 가이드

자동 적용은 안전 정책상 차단되었으므로, 아래 내용을 직접 `.claude/settings.local.json`에 머지하세요.

## 추가할 내용

`.claude/settings.local.json` 파일의 **최상위에 `hooks` 키를 추가**합니다.

### 현재 구조 (예시)

```json
{
  "permissions": {
    "allow": [
      ...
    ]
  }
}
```

### 변경 후 구조

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"H:/내 드라이브/.agent/scripts/_gemini_flag_hook.py\""
          }
        ]
      }
    ]
  },
  "permissions": {
    "allow": [
      ...
    ]
  }
}
```

## 동작 확인

1. `.claude/settings.local.json`에 위 `hooks` 키 추가
2. Claude Code 재시작
3. 세션 시작 직후 stdout이 자동 로드됨

테스트용 더미 flag.json 생성:

```bash
cat > "H:/내 드라이브/.auto-memory/gemini_ops/flag.json" <<EOF
{
  "updated_at": "2026-05-23T15:00:00",
  "summary": {"red": 0, "yellow": 1, "green": 0, "total": 1},
  "entries": [
    {
      "log_path": "test.md",
      "log_name": "test.md",
      "checked_at": "2026-05-23T15:00:00",
      "severity": "yellow",
      "verify_status": "pending",
      "spec_source": "test",
      "violations": [
        {"rule": "rule_test", "severity": "yellow", "message": "테스트 메시지"}
      ]
    }
  ]
}
EOF
```

Claude Code 새 세션 시작 시 알림 메시지가 출력되면 정상입니다.

## 토큰 비용

- flag.json에 red/yellow 0건 → **출력 0바이트**, 토큰 추가 없음
- 1건 발견 → 약 100~200 토큰
- 10건 발견 → 약 500 토큰

## 비활성화

`hooks` 키 자체를 삭제하면 됩니다.
