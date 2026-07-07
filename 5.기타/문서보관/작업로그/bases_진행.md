# Bases·닫힌루프 빌드 진행 (2026-06-28)

핸드오프: `sync/_meta/핸드오프_옵시디언Bases_닫힌루프_2026-06-27.md`

## 완료
- [x] 695 논점노트 frontmatter 진도속성 배선(회독·선택·사례·기록·약점·진도·최근복습). 멱등 스크립트 `.agent/scripts/_bases_진도속성.py`. 파일럿3→전체692+3.
- [x] `sync/위키/진도보드.base` (filter type=="쟁점", 4뷰: 진도표(과목 groupBy)/약점/미착수/회독진행). 문법은 옛 `_쟁점보드.base` 호환.
- [x] 약점 시드: learning.json weak_points 8개 중 6개 → 논점 5개 `약점:true`(대상청구권·부동산이중매매·제한능력자 재산적 법률행위 방식·채권자대위권·채권자취소권 소송요건).

## 보류/미완
- [ ] 회독 시드: 진도_state(백업) 회독 데이터=민소 8단원뿐 + 단원단위(논점보다 거침)이라 자동 시드 생략. 논점 회독은 0 시작, Obsidian에서 갱신.
- [ ] 약점 2개(권리남용 요건·강행법규 위반 무효) — 대응 논점명 불명확으로 미시드.
- [~] drill→frontmatter 역기록: **약점 역기록 헬퍼 `mark_progress.py` 추가 + SKILL.md Phase3 절차 반영(2026-06-28)** — 드릴 에이전트가 다룬 논점 명시→frontmatter(약점·회독·최근복습) 기록. 단원↔논점 회독 자동통합은 미정(단원 board 정본 + 논점층 병행).
- [ ] SRS: learning.json srs 8항목(민법) → 논점키 정합 미배선. drill_log.jsonl=0B(빈).
- [ ] board_server 은퇴(#49): Obsidian에서 .base 정상 렌더 확인 후 진행(그 전까진 유지).

## 스키마 통일·보드 재작성 (2026-06-28, 재연구 후속)
- 재연구(`sync/_meta/연구종합_카드+진도보드_2026-06-28.md`) 결론: 보드 '쟁점 누락'의 진짜 원인 = 노트 결손 0이지만 **frontmatter 스키마 불일치**(type 쟁점/논점노트 혼재로 263개 필터탈락 + 논점필드 제각각 + 계층속성 0).
- [x] **스키마 통일** `.agent/scripts/_schema_unify.py` — 목차 권위로 전 695노트 `type:쟁점` + `논점:<목차KEY>` + `대분류`/`중분류` + `스키마:통일`. 695/695 매칭(미매칭 0). type=쟁점 695/695, 대분류 695/695(32섹션).
- [x] **`진도보드.base` 재작성** — 5뷰: 목차순(과목·대분류 groupBy)·대분류별·약점·미착수·회독진행. Claude-readable frontmatter=단일정본(나+다 기반).

## 검증 필요(사용자)
- Obsidian에서 `sync/위키/진도보드.base` 렌더 확인 — 이제 695 전부 + 대분류 그룹 표시되어야. '약점'(==true)·'회독진행'(>0) bool/숫자 필터, 다단계 정렬 렌더 확인. 안 되면 문법 조정.
- 입력(풀고 체크) 방식: Bases 인라인 편집 데스크톱 충분한지 / 부족하면 frontmatter 쓰는 경량보드(다) 추가 결정.

## v2 보드 구축 (2026-06-28, 사용자 결정: UX=B느낌·1:1 논점·대분류 섹션·방학/내신/SRS 연동, 정본=frontmatter)
- [x] 보드 데이터 파손 수정: YAML오류 428건(카드감사 마커 값내 콜론) `_fm_sanitize.py`로 인용처리 → 0 / 과목없음 42 보강 / 대분류·중분류 편·장 접두사 제거 404.
- [x] `6.진도관리/board_server_v2.py` — **정본=논점 frontmatter**. 기존 `진도_board.html` UX 재사용(BOARD만 frontmatter→{과목>대분류>논점}로 치환). 키=과목|대분류|논점, 클릭→해당 논점 frontmatter(회독·선택·사례·기록) 기록. 약점/SRS/시험=learning.json 재사용. 방학/내신 목표=`백업/진도보드_목표.json`. selftest 통과(과목7·대분류32·논점695, 쓰기왕복 OK).
- [x] `진도보드.base`(Bases)도 같은 frontmatter — 나(Bases 열람)+다(HTML 입력)가 단일 정본 공유. Claude도 직접 read/write(mark_progress.py).
- [ ] 사용자 확인 후: autostart를 board_server.py→board_server_v2.py로 전환, v1(단원) `_retired`. HTML help 문구 '단원'→'논점' 정리(선택).
