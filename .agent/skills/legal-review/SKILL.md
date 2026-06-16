---
name: legal-review
description: 계약, NDA, 법무 검토 요청을 플레이북 기준으로 구조화해 검토할 때 사용한다. PDF/DOCX/TXT/MD 문서를 읽고 조항별 상태를 GREEN/YELLOW/RED로 정리하며, redline 제안, fallback 포지션, business impact를 함께 제시한다.
---

# Legal Review Skill

법무 문서 검토용 로컬 스킬이다. 현재 범위는 `계약 검토`와 `NDA triage`다.

## 핵심 출력

- 조항별 상태 분류: `GREEN / YELLOW / RED`
- 플레이북 기준 포지션, 허용 범위, 에스컬레이션 트리거
- `Suggested Redlines`
- `Fallback Position`
- `Business Impact`

## 기본 경로

- 플레이북: `H:\내 드라이브\.agent\state\legal_playbook.md`
- 스크립트: `H:\내 드라이브\.agent\skills\legal-review\scripts\render_review.py`
- 계약 검토 템플릿: `H:\내 드라이브\.agent\skills\legal-review\templates\contract_review.md`
- NDA triage 템플릿: `H:\내 드라이브\.agent\skills\legal-review\templates\nda_triage.md`

## 빠른 실행

```powershell
python .agent/skills/legal-review/scripts/render_review.py "C:\path\contract.pdf" --mode contract-review --output "H:\내 드라이브\tmp\contract_review.md"
```

```powershell
python .agent/skills/legal-review/scripts/render_review.py "C:\path\nda.docx" --mode nda-triage --output "H:\내 드라이브\tmp\nda_triage.md"
```

직접 텍스트로도 실행 가능하다.

```powershell
python .agent/skills/legal-review/scripts/render_review.py --mode contract-review --text "The parties agree..." --output "H:\내 드라이브\tmp\quick_review.md"
```

## Dry Run Runner

전체 로컬 legal suite를 드라이런으로 검증하려면 아래 러너를 사용한다.

```powershell
python .agent/skills/legal-review/scripts/run_legal_suite.py --preset vendor-saas --text "Vendor may transfer personal data without safeguards. All disputes shall be resolved by mandatory arbitration in California. Confidential obligations apply only to Customer and last for 10 years with no carve-outs."
```

Artifacts are written under `H:\내 드라이브\tmp\legal_suite_dry_run\{timestamp}\`.
The latest pipeline log is written to `H:\내 드라이브\.agent\state\legal_suite_dry_run_log.json`.

## 실행 순서

1. 입력 문서를 확인한다. 지원 형식은 `pdf`, `docx`, `txt`, `md`다.
2. `legal_playbook.md`를 읽어 조항별 기준, fallback, redline, business impact를 로드한다.
3. `render_review.py`로 보고서를 생성한다.
4. RED/YELLOW 조항의 트리거, redline, fallback을 우선 검토한다.
5. 필요 시 `legal-compliance`, `legal-briefing`, `legal-response`로 후속 산출물을 만든다.
6. 학습/RAG 연계가 필요하면 `build_socratic_packet.py`로 `legal_socratic_packet.json`을 만든다.

## 다른 스킬과의 관계

- 문서 추출이 필요하면 `pdf-ingest`
- 선례/정책 검색이 필요하면 qmd law-notes (`.agent/lib/qmd_search.py`)
- 컴플라이언스 체크리스트는 `legal-compliance`
- 회의 메모는 `legal-briefing`
- 회신 초안은 `legal-response`
- 통합 드라이런은 `run_legal_suite.py`

## 한계

- 현재 버전은 플레이북 + 키워드/트리거 기반 로컬 검토기다.
- 자동 redline 생성은 제안 수준이며 DOCX 비교편집 같은 문서 레벨 redline은 아니다.
- 외부 CLM/MCP connector, 규제 최신성 검증, 자동 redline 문서 패치 생성은 후속 단계다.
