# Karpathy 메모리 시스템 — 법학 학습 커스텀 구현

## 개요
Andrej Karpathy의 LLM Wiki 패턴을 법학 학습 환경에 맞게 구현한 시스템.
기존 .auto-memory/ + CLAUDE.md 체계와 완전 호환.

## 구성 요소

| 파일 | 역할 | 실행 시점 |
|------|------|----------|
| `flush.py` | 세션 로그에서 핵심 결정/교훈/패턴 추출 → daily log | 세션 종료 후 (hooks) |
| `compile.py` | daily log들을 주제별 wiki 아티클로 컴파일 | 수동 또는 주 1회 |
| `lint.py` | 메모리 건강 체크 7종 | 수동 또는 주 1회 |
| `index.py` | wiki 아티클 인덱스 생성/갱신 | compile 후 자동 |

## 디렉토리 구조

```
H:\내 드라이브\
├── .auto-memory/           ← 기존 유지
│   ├── MEMORY.md           ← 기존 인덱스 (유지)
│   ├── user_profile.md     ← 기존 유지
│   ├── feedback_*.md       ← 기존 유지
│   ├── session_logs/       ← 신규: 세션별 자동 캡처 로그
│   │   ├── 2026-04-24_1430.md
│   │   └── 2026-04-24_1830.md
│   ├── daily/              ← 신규: flush된 일별 요약
│   │   ├── 2026-04-24.md
│   │   └── 2026-04-25.md
│   └── wiki/               ← 신규: 컴파일된 주제별 아티클
│       ├── _index.md       ← wiki 인덱스 (검색용)
│       ├── 점유취득시효.md
│       ├── 공모관계이탈.md
│       ├── 사정변경원칙.md
│       └── ...
├── .claude/
│   ├── CLAUDE.md           ← #42~#45 규칙 추가
│   └── hooks/              ← 신규: 세션 종료 hook
│       └── post_session.py
└── .agent/
    └── scripts/
        ├── flush.py        ← 신규
        ├── compile.py      ← 신규
        ├── lint.py         ← 신규
        └── index.py        ← 신규
```

## 기존 시스템과의 호환

| 기존 구성 | 신규 구성 | 관계 |
|----------|----------|------|
| .auto-memory/MEMORY.md | 유지 | wiki/_index.md가 보완 |
| consolidate-memory 스킬 | 유지 | lint.py가 보완 |
| CLAUDE.md #1~#41 | #42~#45 추가 | 충돌 없음 |
| 옵시디언 백링크 (#39) | wiki 아티클에도 적용 | 통합 |
| #17-A 삭제 금지 | lint.py도 _trash 이동만 | 준수 |

## 설치 방법
→ INSTALL.md 참조
