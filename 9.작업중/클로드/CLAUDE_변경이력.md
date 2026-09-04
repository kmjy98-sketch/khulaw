# CLAUDE.md 변경이력 (CHANGELOG)

> 룰 파일에서 분리한 경위·이력 기록(2026-07-02 슬림화, 사용자 승인). 현행 규범은 CLAUDE.md가 유일 정본.

## 도구·파이프라인 전환 경위
- **OCR 파이프라인**(2026-06-21 갱신): Colab 폐기 → LlamaParse 로컬 전환. 구 Colab 노트북 2종(`.agent/notebooks/ocr_extract_v2.ipynb`·`ocr_compare_v2.ipynb`)은 레거시(연동 끊김, 신규작업 미사용; 이동·이름변경 금지 주석만 유지). 교정 검증도구는 korean-law-mcp → law_api.py(#49, 2026-07-01 완전 은퇴).
- **운영 모드**(2026-06-21): 안티그래비티(Gemini)·Colab·Gemini Gems 폐기 — 01 OCR·02-wiki·02-card 모두 Claude 단일 생태계로 통합. 구 Phase 2 2모델 분담·Phase 1.2 legacy는 이력(legacy 스크립트·.env 보존만).
- **korean-law-mcp**(2026-07-01): 풀클론 `.agent/_retired/2026-07-01/` 은퇴, 소비자 전부 law_api.py 재배선, API키 `.agent/lib/.env`.
- **v1 진도보드**(2026-07-01): board_server.py·_ingest_jindo.py·진도_현황.json/md 은퇴 → board_server_v2 + 진도보드.base(#19-B).

## 위키 경로 변천 (#38·#40·#50)
- 구: 위키 원문 정본 `sync/위키/원문`(+생성기 wiki_원문분할.py), 쟁점 `sync/wiki/쟁점`(영문 병존).
- 2026-06-26 #50 재편: 쟁점=`sync/위키/{과목}/`(sync), 원문 전문=`outputs/01_ocr_llamaparse/`(비동기, sync 1GB 제외). 구 경로·생성기 폐기, 잔존분 과목 폴더 이관(#16-C 로그).

## #18 파일 존재 확인 이력 (구 체크리스트)
- 2026-04-24 확인 / 2026-05-21 v3.6 Phase 1.2 갱신 / 2026-06-01 v3.6 Phase 2 갱신 / 2026-06-16 재확인:
  socratic.md·lecture-notes.md·leet-solve.md·file-classification·daily-drill(2026-06-18 신설, build_session.py·log_result.py)·claude_code_package_v2/SKILL.md(운영 주체 Claude Web 환원 2026-06-16)·prompts 16종(claude 5·gemini 5·공용 6)·패키지백업(2026-05-21) — 전부 존재 확인 완료.

## AGENTS.md 은퇴·부활
- Antigravity(Gemini) 아키텍처 섹션: [RETIRED 2026-06-26] — 도구 폐기로 번호 회수. 대체 지침 #45-B/C·#50.
- AGENTS.md 본체: 2026-06-26 부활·정합(비클로드 에이전트용 운영 기준, 정본은 CLAUDE.md).

## 주요 룰 신설 연혁
- #50 위키 닫힌루프·2층분리(2026-06-26) / #51 카드 3역할·사례층(2026-06-28) / #45-D 대량 fan-out 금지(2026-07-01) / #52 모델티어링·채점관·복습3루프(2026-07-01~02) / #42 문서보관층·읽기레이어, #52-A 라우팅표(2026-07-02).
- #52 출제 단위 규칙(2026-07-04): 요건·효과=세트 출제 필수(파편 OX·단일 빈칸 금지 — 열거형·멀티클로즈·침입선다·미니사례 포섭형, 소스 무열거 시 생략 폴백) / 판례=개별 OX 유지 / 논점당 8문(증량 10)·세트 서브키 부분점수. 근거 9.작업중/클로드/드릴_요건묶음출제_검토_2026-07-04.md §0. 반영: 커널 #52, 채점복습.md (B-0), daily-drill SKILL Phase 1.
- #52 세션 구조 3스텝(2026-07-06): 혼동 클러스터 선정→논점 블록(개념→응용)→혼합 라운드(논점 무표기 셔플). 근거 조사보고_드릴출제구조_2026-07-06.md(메타분석 g=0.42·변별대비 조건·expertise reversal). L0 필수복습 3원천(수업·드릴·보드체크, /api/bump 복원+최근체크 스탬프), SRS 사례형 미니 필수·복습 사례 2건, SRS 과목별 가중(retention_factors 버그수정·활성화).
- #52 검증·보완 조사(2026-07-07): 조사보고 미검증 5건 전부 원출처 confirmed(words g=-0.39 Table2 p=.005 / van Gog 예제선행 / Kalyuga '효과크기 차이' 보정 / Pan 2024 문법 인터리빙 / Nemeth 2025 블록 학습착각). 설계 보정 4건 — 혼합 라운드 필수조건 3(피드백 라벨·성취 게이트·효과 체감 표시), 전문성 역전은 선택형 개념 세트 한정(사례형 모범답안 유지 — Nievelstein 2013 법학 직접근거), 사례비교 과제 신설(2-A++, analogical encoding 2~3배 전이), SRS 졸업 수치화(간격 세션 3회 성공→FSRS, 동일일 1세션 계산, 재제시 상한 2). 반영: SKILL 3-B·2-A++, 채점복습.md #20, 조사보고 §5~6.
- 시스템 공백 감사·수리(2026-07-07): 4렌즈 감사(룰정합·데이터흐름·커버리지·운영) → P0 수리: SRS 결선(log_result --srs-scores→SM-2 실가동, 같은날 1세션 dedup, 3세션 졸업 자동화+graduated_queue, --add 중복병합, srs_events.jsonl 신설) / 문항단위 로그 drill_items.jsonl(--items) / 루틴 4종 배터리 조건 해제(3일 침묵스킵 원인) / _daily_handoff 이중버그 수정 / Anki 컬렉션 주간 오프사이트 백업(routine_weekly) / 보드서버 자동시작 단일화(HKCU 제거→autostart.py) / build_session 위키폴더 부재 경고. 잔여 P0(콘텐츠): 형소·상법·선택법 위키 부재, 행정법 사례·포섭사전 전무 — 사용자 결정 대기. 상세 감사결과: 사건 tasks/w7lpus1i4.
