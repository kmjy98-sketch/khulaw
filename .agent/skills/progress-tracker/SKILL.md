---
name: progress-tracker
description: 학습 진도 보조 조회(수동입력). progress.json(보조 snapshot)의 과목별 상태·진행률·회독·종료여부·로드맵 조회/갱신. "진도 확인", "진도 갱신", "방학/학기 목표" 요청 시 사용.
---

# Progress Tracker Skill (수동입력판)

> **진도 정본 = 논점 frontmatter**(`sync/위키/{과목}/{쟁점}.md`의 회독·선택·사례·약점·진도, #19-B 2026-06-30). 본 스킬이 다루는 `.agent/state/progress.json`은 **보조 snapshot(정본 아님)** — 과목 > 大단원 단위의 거친 조회·로드맵 메모용으로만 쓴다. 정밀 진도(회독·약점 등)는 논점 frontmatter를 확인한다.
> 전사문 자동추적은 폐기됨(2026-06-18 — 토큰 과소모·미열람). 진도는 사용자가 직접 갱신하고 Claude는 조회·간단갱신만 한다.

---

## Quick Start

```powershell
# 진도 조회
python .agent/skills/progress-tracker/scripts/progress.py --status

# 단원 갱신 (과목 > 大단원). --unit 필수
python .agent/skills/progress-tracker/scripts/progress.py --set 민법 --unit 물권법 --state 진행중 --rounds 2
python .agent/skills/progress-tracker/scripts/progress.py --set 형법 --unit 형법총론 --done   # 종료 처리

# 로드맵 목표 설정
python .agent/skills/progress-tracker/scripts/progress.py --goal 방학 "민법·형법 3회독 완료"
```

또는 `progress.json`을 직접 편집해도 된다(수동입력이 기본).

---

## 데이터 구조 (`.agent/state/progress.json`)

```json
{
  "최종수정": "2026-06-18",
  "로드맵": { "전체목표": "...", "이번방학목표": "...", "다음학기목표": "..." },
  "과목": {
    "민법": {
      "물권법": { "상태": "진행중", "회독": 2, "세부": ["물권총칙·물권변동", "점유권", "소유권(취득시효·공유)", "용익물권"] }
    }
  }
}
```

- 추적 단위 = **과목 > 大단원**(목차 기준). `세부`는 교재 목차 장/절(참고용, 필요시 개별 추적)
- `상태` = 예정 | 진행중 | 종료 (종료 단원이 Anki 회독·약점 포착 대상, 루프 ④⑤)
- `회독` = 정수 (변시 핵심 지표)
- 단원 근거: 민법=논점민법재산법 / 민소=논점민소 / 헌법=헌법핵심정리300 목차, 그 외(상법·행정법·형소·선택)=OCR 없어 표준체계

---

## 워크플로우 연계

| 워크플로우 | 트리거 | 동작 |
|---|---|---|
| `/socratic` | 세션 시작 | `--status` (현 진도 참고) |
| 진도 갱신 | "민법 3회독 끝" 등 | `--set 민법 --rounds 3` |
| 목표 설정 | "방학 목표 …" | `--goal 방학 "…"` |

진도 시각화(과목 진행률·회독 히트맵)는 이 데이터를 소스로 한다(대시보드 목업 참조).

---

## 폐기 사항 (2026-06-18)
- 전사문 기반 추적(`current_scope.transcript`·`transcript_parts`·`lecture_notes`·`--complete partXX`·`--next`·`--set-scope`) 전부 제거.
- 구 진도(과거 작업 로그 포함)는 `5.기타/_백업/progress_전사문구_2026-06-18.json`에 보존.
