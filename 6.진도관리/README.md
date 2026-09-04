# 6.진도관리 — 학습 진도 시스템 (v2, 2026-06-30)

> 진도 추적 도구·소스·백업을 한곳에 묶은 전용 폴더(2026-06-18 분리; 2026-06-30 v2 정합).

---

## 진도 정본 (#19-B)

**논점 frontmatter** = `sync/위키/{과목}/{쟁점}.md`의 회독·선택·사례·약점·진도 필드가 정본.

인터페이스 2종 병존(둘 다 같은 frontmatter를 읽고 씀):
- `board_server_v2.py` → `http://localhost:8770/` (HTML, 데스크톱 클릭 입력)
- `sync/위키/진도보드.base` (옵시디언 Bases 열람)

역기록(드릴→보드 닫힌루프): `.agent/skills/daily-drill/scripts/mark_progress.py`

> **구 v1 자산(아래 `board_server.py` 항목 참조)은 deprecated.** `progress.json`·`진도_현황.json`·`진도_state.json`·`진도_현황.md`는 보조 snapshot/구 v1이며 정본이 아님 — 참조 금지(#19-B).

---

## 구성

```
6.진도관리/
  board_server_v2.py      ← 정본 서버(논점 frontmatter 읽고 씀)
  board_server.py         ← [DEPRECATED — v1. board_server_v2.py가 후속.]
                             Bases 렌더 확인 후 .agent/_retired/로 이관 예정(#49).
  진도보드_서버켜기.bat       ← board_server_v2.py 실행(검은 창, 로그 표시)
  진도보드_백그라운드실행.bat  ← board_server_v2.py 백그라운드 실행(권장)
  진도보드_서버끄기.bat
  진도_board.html         ← v1 인터페이스(deprecated — v2 HTML 또는 Bases 사용)
  data/                   ← 소스 데이터
    진도_소단원_master.csv
    진도_tracker.xlsx
    행정법강해_목차_제14판.md
  백업/                   ← 진도 데이터 백업(JSON)
  사례답안/               ← 사례형 답안 인박스
  오늘_드릴.md            ← daily-drill 세션 브리프
  README.md
```

---

## 서버 모드 (권장)

`.bat`을 실행하면 `board_server_v2.py`가 기동되어 `http://localhost:8770/`이 자동 열린다.

- **`진도보드_백그라운드실행.bat`** — 창 없이 백그라운드. 끄려면 `진도보드_서버끄기.bat`.
- **`진도보드_서버켜기.bat`** — 검은 창으로 실행(로그 보고 싶을 때). 창 닫으면 서버 꺼짐.

보드 상단 "● 서버 연결"(초록)이면 정상. "file://"(회색)이면 `.bat`이 아닌 html을 직접 연 것.

### board_server_v2.py 동작 원리

`build_board` 함수가 `sync/위키/{과목}/` 하위 각 쟁점 `.md`의 **frontmatter**(과목·대분류·논점·회독·선택·사례·약점·진도)를 읽어 보드를 구성한다. 키 표준: `과목|대분류|논점` (#50-A).

클릭마다 자동 저장:
- 논점 frontmatter 갱신(`mark_progress.py` — 역기록 닫힌루프)
- `백업/진도_log.jsonl` — 이벤트 로그
- `백업/진도_state.json` — 전체 스냅샷

---

## 역기록 (드릴→보드 닫힌루프)

드릴에서 다룬 논점·약점을 논점노트 frontmatter에 기록한다:

```powershell
python .agent/skills/daily-drill/scripts/mark_progress.py \
  --notes "민법/채권자대위권,민법/대상청구권" --weak --review
# --weak 약점:true / --clear-weak 약점:false / --read 회독+1 / --review 최근복습=오늘
```

---

## [DEPRECATED] v1 자산 안내

| 자산 | 상태 | 후속 |
|------|------|------|
| `board_server.py` | deprecated | `board_server_v2.py` |
| `진도_board.html` | deprecated | `http://localhost:8770/` 또는 `sync/위키/진도보드.base` |
| `progress.json`, `진도_현황.json`, `진도_state.json` | 보조 snapshot(정본 아님) | 논점 frontmatter |
| `_ingest_jindo.py` | deprecated | `mark_progress.py`(역기록 자동) |

**파일 자체는 이동·삭제하지 않음**(#16). Bases 렌더 확인 후 `board_server.py`만 `_retired` 이관 예정(#49).

---

## Claude에 진도 반영

진도 정본은 논점 frontmatter이므로 Claude는 `sync/위키/{과목}/` 쟁점 파일을 직접 읽어 진도를 파악한다. 별도 export/import 불필요.

---

## 과목 풀네임 (#50-B, #51)

경로·필드에 과목 약칭 사용 금지. 정확한 폴더명:
`민법` · `민사소송법` · `민사집행법` · `형법총론` · `형법각론` · `형사소송법` · `행정법` · `헌법`
