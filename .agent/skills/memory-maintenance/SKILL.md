---
name: memory-maintenance
description: 메모리·정합성 정기 정비 단일 진입점. "메모리 정비", "lint", "메모리 컴파일", "메모리 점검", "memory maintenance" 요청 시 사용. lint.py 전수 정합점검(활성) + consolidate-memory(하버스 메모리 정비) + 포인터 무결성 점검을 묶는다. flush/compile은 동결.
---

# memory-maintenance — 메모리·정합성 정비 래퍼

> CLAUDE.md #41 진입점. 산재하던 lint/flush/compile/consolidate를 하나로 묶는다.

## 무엇을 하나
1. **전수 정합점검(활성)**: `.agent/scripts/lint.py` 실행 — 깨진 백링크·고아·stale·판례모순·빈 아티클·중복주제·인덱스 동기·백링크형식·한자잔재·표구조 + (확장 시) 진입점 없는 자산·죽은 경로참조. 결과 `.auto-memory/lint_report.json`.
2. **하버스 메모리 정비**: consolidate-memory 스킬 호출 — MEMORY.md 중복 병합·stale 정정·인덱스 정리.
3. **포인터 무결성**: MEMORY.md의 `[[링크]]`·9.작업중/클로드·위키 경로가 실재하는지 점검(교정루프 C1·C6 연동). 불일치 → `.agent/state/consistency_log.jsonl` 기록 + 보고.

## 메모리 모델 (필독)
- **인간뷰 정본 = 쟁점 위키 `sync/위키/{과목}/`**(#50-B, 논점 단위). **원문 전문 = `outputs/`(비동기, sync 밖)**. 구 `sync/위키/원문`은 폐기·이관됨(#50). `MEMORY.md` = **클로드뷰 자동로드 마스터 색인**(행동룰·프로젝트 상태·사용자 선호 + 위키 단방향 포인터). 링크는 MEMORY→위키 단방향, 위키 원문 역주입 금지(#40).
- `flush.py`·`compile.py`(세션로그→daily→sync/wiki)는 **동결**. 부활 전엔 호출하지 않는다.

## 안전
- 삭제 금지(#16) — 오래된 아티클은 `_trash` 이동 '제안'만, 실제 이동은 사용자 승인 + `log_file_op.py`(#16-C).
- 자동 수정·이동 금지: 점검 결과는 보고. 적용은 사용자 확인 후(#45-C 검증자 권한과 동일).
