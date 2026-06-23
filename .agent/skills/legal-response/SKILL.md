---
name: legal-response
description: [직무전용·미사용 — #48 자동발동 제외, 명시 요청 시에만] 플레이북과 검토 결과를 바탕으로 상대방 또는 내부 요청자에게 보낼 회신 초안을 만들 때 사용하는 스킬. `legal-review` 보고서나 원문 문서를 받아 pushback, clarify, accept posture의 문안을 생성한다. "법무 회신", "수정 요청 메일", "legal response" 요청 시 사용.
---

# Legal Response

이 스킬은 플레이북 기준 문구를 바탕으로 대외/내부 회신 초안을 만든다. 기본 흐름은 `legal-review` 결과를 입력으로 받아 `pushback`, `clarify`, `accept` 중 하나의 posture로 문안을 생성하는 것이다.

## Quick Start

검토 보고서에서 수정 요청 회신을 만들 때:

```powershell
python .agent/skills/legal-response/scripts/render_legal_response.py --review-path "E:\법학볼트\tmp\contract_review.md" --posture pushback --recipient "상대방 법무" --output "E:\법학볼트\tmp\legal_response.md"
```

원문 문서를 바로 기준 문안으로 바꿀 때:

```powershell
python .agent/skills/legal-response/scripts/render_legal_response.py "C:\path\nda.docx" --posture clarify --recipient "사업팀" --output "E:\법학볼트\tmp\legal_response.md"
```

## Postures

- `pushback`: 수정 또는 제한 요청
- `clarify`: 사실관계/문구 확인 요청
- `accept`: 현재 기준상 큰 충돌이 없는 문안

## Inputs

- `legal-review` 보고서 또는 원문 문서
- 플레이북: `.agent/state/legal_playbook.md`
- 템플릿: `.agent/state/legal_templates.md`

## Output

- 대외 회신 초안
- 참조한 이슈 표
- 내부 메모

## Related Skills

- `legal-review`: 조항별 상태와 근거 수집
- `legal-briefing`: 회의 메모 작성
- `legal-compliance`: 점검표 작성
