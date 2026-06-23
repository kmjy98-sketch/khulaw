---
name: legal-briefing
description: [직무전용·미사용 — #48 자동발동 제외, 명시 요청 시에만] 계약 검토 결과나 원문 문서를 회의용 법무 브리핑 메모로 재구성할 때 사용하는 스킬. `legal-review` 보고서 또는 원문을 받아 executive summary, decision points, 질문 목록을 만든다. "법무 브리핑", "회의 메모", "legal briefing" 요청 시 사용.
---

# Legal Briefing

이 스킬은 계약 검토 결과를 바로 회의 메모로 압축한다. 원문을 직접 넣어도 되지만, 기본 흐름은 `legal-review` 보고서를 먼저 만들고 그 결과를 브리핑 메모로 바꾸는 것이다.

## Quick Start

기존 검토 보고서에서 브리핑 메모를 만들 때:

```powershell
python .agent/skills/legal-briefing/scripts/render_legal_briefing.py --review-path "E:\법학볼트\tmp\contract_review.md" --meeting "내부 협상 회의" --output "E:\법학볼트\tmp\legal_briefing.md"
```

원문 문서를 바로 브리핑할 때:

```powershell
python .agent/skills/legal-briefing/scripts/render_legal_briefing.py "C:\path\contract.pdf" --audience "사업팀" --objective "협상 포인트 정리" --output "E:\법학볼트\tmp\legal_briefing.md"
```

## Inputs

- `legal-review` 보고서 또는 원문 문서
- 플레이북: `.agent/state/legal_playbook.md`
- 템플릿: `.agent/state/legal_templates.md`

## Output

- Executive Summary
- Risk Snapshot
- Decision Points
- Clause Notes
- Questions

## Recommended Order

1. `legal-review`로 계약/NDA 검토를 먼저 만든다.
2. `legal-briefing`으로 회의용 메모를 뽑는다.
3. 필요하면 `legal-response`로 회신 초안을 만든다.
