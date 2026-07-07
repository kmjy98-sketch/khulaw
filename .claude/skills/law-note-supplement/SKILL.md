---
name: law-note-supplement
description: 기존 법학 노트(민법/형법/헌법)를 보완·검토·재구조화할 때 사용. 새 노트 생성이 아니라 기존 노트에 빠진 판례문구, 조문, 요건, 서브개념, 모답형, 중요도, 도표를 추가하거나 오류를 검토하는 작업. 트리거: "노트 보완", "판례 추가해줘", "요건 빠진 거 채워줘", "노트 검토", "노트 구조 바꿔줘", "단권화 동기화", "법학노트보완", "note supplement", "augment notes"
---

`E:\법학볼트\.agent\skills\law-note-supplement\SKILL.md` 를 읽고 지침을 따른다.

참조 파일:
- `references/source-priority.md` — 소스 우선순위 및 충돌 규칙
- `references/note-structures.md` — 과목별 노트 블록 템플릿

모드: **augment** (내용 추가) / **review** (오류·갭 검토) / **restructure** (구조 개선)
새 노트를 처음부터 만들 때는 `study-notes` 스킬을 사용한다.

law_api.py(verify-text/verify-article, 법제처 직접 API) 자동 호출:
- augment: 조문 번호만 있고 원문 없으면 자동 조회 → 요건 변환 소스로 사용
- review: 조문 내용 불일치 의심 시 원문 대조
- restructure: 조회 불요
