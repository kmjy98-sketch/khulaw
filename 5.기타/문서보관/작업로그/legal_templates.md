# Legal Templates

## briefing_defaults
- executive_summary_prefix: 아래 메모는 플레이북과 검토 결과를 회의용으로 압축한 초안이다.
- decision_request_red: RED 항목은 대외 회신 전 담당 법무 승인 여부를 먼저 정리한다.
- decision_request_yellow: YELLOW 항목은 원문 확인 또는 상대방 설명 요청 여부를 먼저 정리한다.
- impact_red: 플레이북 기준 일탈 가능성이 있어 승인 또는 수정안 결정이 필요하다.
- impact_yellow: 문구 불명확 또는 근거 부족으로 사실관계 확인이 필요하다.
- impact_green: 현재 확인 범위에서는 플레이북과의 직접 충돌이 크지 않다.
- question_prefix: 확인 질문

## response_defaults
- external_disclaimer: 아래 문안은 검토 초안이며 내부 승인 후 사용한다.

### pushback
- opener: 검토 결과 아래 조항은 현재 기준상 수정 또는 제한이 필요합니다.
- clause_line: {clause} 조항은 현재 {status}로 검토되었고, 당사 기준은 "{standard_position}" 입니다.
- action_line: 가능하면 해당 문구를 조정하거나 대안을 제시해 주시기 바랍니다.
- close: 수정안 또는 설명을 주시면 재검토 후 회신드리겠습니다.

### clarify
- opener: 검토 과정에서 아래 조항은 문구 확인 또는 추가 설명이 필요했습니다.
- clause_line: {clause} 조항은 현재 {status}로 검토되었으며, 확인된 근거는 "{evidence}" 입니다.
- action_line: 해당 문구의 의도나 적용 범위를 확인할 수 있도록 설명 부탁드립니다.
- close: 설명을 받는 대로 내부 검토를 이어가겠습니다.

### accept
- opener: 현재 확인 범위에서는 아래 조항들이 기준과 큰 충돌 없이 검토되었습니다.
- clause_line: {clause} 조항은 현재 {status}로 정리되었고, 기준상 "{standard_position}" 방향과 대체로 부합합니다.
- action_line: 특별한 추가 수정 요청은 없으나 최종본 기준으로 한 번 더 확인하겠습니다.
- close: 최종본 공유 시 동일 기준으로 마무리 검토하겠습니다.

## compliance_defaults
- required_action_red: 즉시 에스컬레이션 또는 내부 승인 필요
- required_action_yellow: 원문 보강 또는 상대방 확인 필요
- required_action_green: 현 기준상 추가 조치 필요성 낮음
- escalation_note: RED 항목은 예외 승인 가능 여부와 대체 문구 유무를 함께 확인한다.
