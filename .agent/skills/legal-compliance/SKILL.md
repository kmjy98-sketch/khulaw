---
name: legal-compliance
description: 계약서, 정책서, DPA, NDA를 플레이북 기준의 컴플라이언스 점검표로 정리할 때 사용하는 법무 스킬. `legal-review` 결과나 원문 문서를 받아 privacy, data retention, governing law, dispute resolution 중심의 체크리스트와 필수 조치를 만든다. "컴플라이언스 체크", "데이터보호 점검", "법무 체크리스트", "legal compliance" 요청 시 사용.
---

# Legal Compliance

`legal-review`가 조항별 리스크를 보는 MVP라면, 이 스킬은 그중 컴플라이언스 관점의 체크리스트와 필수 조치를 분리해 보여준다. 현재 기본 범위는 `Data Protection`, `Term and Termination`, `Governing Law`, `Dispute Resolution`, `NDA Mutuality`, `NDA Term`, `NDA Carveouts`다.

## Quick Start

원문 문서를 바로 점검할 때:

```powershell
python .agent/skills/legal-compliance/scripts/render_compliance_review.py "C:\path\contract.pdf" --owner "법무" --system "SaaS 계약" --output "H:\내 드라이브\tmp\legal_compliance.md"
```

기존 `legal-review` 보고서에서 이어갈 때:

```powershell
python .agent/skills/legal-compliance/scripts/render_compliance_review.py --review-path "H:\내 드라이브\tmp\contract_review.md" --output "H:\내 드라이브\tmp\legal_compliance.md"
```

## Inputs

- 원문 입력: `pdf`, `docx`, `txt`, `md`
- 또는 기존 `legal-review` 마크다운 보고서
- 플레이북: `.agent/state/legal_playbook.md`
- 템플릿: `.agent/state/legal_templates.md`

## Workflow

1. 원문 또는 기존 검토 보고서를 읽는다.
2. `legal_playbook.md`에서 컴플라이언스 관련 조항 기준을 가져온다.
3. `legal_templates.md`의 조치 규칙을 반영해 체크리스트와 필수 조치를 만든다.
4. RED/YELLOW 항목을 우선 검토 대상으로 올린다.

## Output

- 마크다운 보고서
- 주요 섹션:
  - 요약
  - 상태 집계
  - 체크리스트
  - 필수 조치
  - 근거 스니펫

## Related Skills

- `legal-review`: 계약/NDA 기본 검토
- `legal-briefing`: 회의용 브리핑 메모
- `legal-response`: 상대방/내부 회신 초안
