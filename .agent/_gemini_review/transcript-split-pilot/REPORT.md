# Gemini 파일럿 보고: transcript-tools 분할

- 작성일: 2026-04-27
- 대상: 강의 전사문 5등분 분할 작업
- 비교 대상: Claude 측 (`split_transcript.py` 결정론적 Python 스크립트) vs Gemini Flash 2.5 (gemini CLI v0.39.1, headless)

---

## 1. 파일럿 대상

| 항목 | 값 |
|------|-----|
| 원본 | `H:\내 드라이브\1.민사\30.송영곤_기본민법\전사문\civ_song_basic_3-2.2\civ_song_basic_3-2.2_transcript.txt` |
| 크기 | 16,437 bytes / 8,009 chars / 199 lines |
| 타임스탬프 | 187개 (`[HH:MM:SS]` 형식) |
| 메타헤더 | `# 전사문: ...` + `**원본**:` 등 9줄 + `---` |
| 선정 사유 | mtime 1주일 내 .md는 전무 → 합쳐진 단일 5–50KB 후보 중 가장 최근(2026-03-21경) 전사 원본. 명확한 타임스탬프 보유로 보존율 측정 가능 |

원본 사본: `_gemini_review/transcript-split-pilot/source/civ_song_basic_3-2.2_transcript.md`

## 2. 결과물 위치

| 도구 | 경로 | 파일 수 |
|------|------|--------|
| Claude (`split_transcript.py --parts 5`) | `_gemini_review/transcript-split-pilot/claude/` | 5 |
| Gemini Flash 2.5 (3차 시도, stdin pipe) | `_gemini_review/transcript-split-pilot/gemini/` | 5 |
| 비교 스크립트 | `_gemini_review/transcript-split-pilot/compare.py` | — |
| Gemini raw stdout | `_gemini_review/transcript-split-pilot/gemini_output_v3.md` | — |

## 3. 비교 표 (5항목)

| 항목 | Claude (Python) | Gemini Flash 2.5 | 차이 |
|------|---------|------------------|------|
| **파트 크기 균일도 (CV%)** | 20.9% | 7.5% | Gemini 우세 (균등 분할) |
| **타임스탬프 보존율** | 187/187 (100%) | 187/187 (100%) | 동률 |
| **원문 무훼손** (정규화 비교) | True (완전 일치) | False (메타헤더 9줄 + `---` 1줄 = 233 chars / 2.9% 손실) | Claude 우세 |
| **처리 시간** | < 1초 (로컬 Python) | 31초 (네트워크 호출) | Claude 30배 이상 빠름 |
| **비용** | 0원 (로컬) | 무료 OAuth quota 차감 (~6K 입력 + ~8K 출력 토큰 ≈ API 환산 $0.022). 일일 무료 쿼터(2.5 Flash 1,500req/day) 내 | 정량적 차이는 미미하나 Claude가 0 |

## 4. 추가 발견 (질적 차이)

### Gemini Flash 헤드리스 모드의 불안정성
- **1차 시도**: `@filename` 참조 + 도구 호출 시도 → `write_file`/`run_shell_command` 도구 부재로 plan만 출력, 본문 누락 (실패)
- **2차 시도**: `--approval-mode plan`으로 도구 차단 → Part 1, 2만 본문 출력하고 Part 3–5는 프롬프트 placeholder 텍스트("[원본 3/5 내용 그대로]")를 그대로 echo하고 종료 (부분 실패)
- **3차 시도** (성공): 원문을 stdin으로 직접 주입하고 도구 호출 명시 금지 → 5분할 완료. 단, **출력 첫 줄에 `MCP issues detected. Run /mcp list for status.` 노이즈가 본문에 붙어 출력**되어 후처리 필요

### 메타헤더 손실 (Claude 우세 핵심 근거)
Gemini Flash가 본문(타임스탬프 라인)은 1글자도 빠짐없이 보존하지만, 다음 10줄을 **무성 누락**함:
```
# 전사문: 송영곤_기본민법_3-2.2
- **원본**: 송영곤_기본민법_3-2.2.mp3
- **강사**: 송영곤
- **강의**: 기본민법
- **회차**: 3회
- **길이**: 11.9분
- **모델**: faster-whisper large-v3
- **전사일**: 2026-02-21 08:18
- **소요시간**: 129.9초
---
```
원문 보존 명령("한 글자도 변경/요약/생략 금지")에도 불구하고 **메타데이터를 본문이 아닌 것으로 분류해 자체 판단으로 제거**한 것으로 추정.

## 5. 결론: **부적합 — 정식 채택 보류**

### 사유
1. **결정적**: Gemini Flash가 헤드리스 모드에서 메타헤더를 무성 누락. 이는 #2(Not-in-Source) 및 #15(Verify-Before-Act) 위반 가능성. 사용자가 이후 OCR 교정·인덱싱 단계에서 메타데이터에 의존하는 워크플로우가 있을 경우 silent data loss 발생.
2. **운영 리스크**: 동일 프롬프트로 3번 호출했을 때 1차·2차는 실패, 3차만 성공. CLI agent 프레임워크의 도구 의존성·MCP 경고 텍스트 누설 등 비결정성이 크다.
3. **수익 부재**: 파트 크기 균일도(CV 20.9% → 7.5%)는 분할 작업의 핵심 KPI가 아님. 후속 transcript-correction 단계는 part 단위 LLM 호출이라 균등도가 비용 절감으로 직결되지도 않는다.
4. **속도 손실**: 31초 vs <1초 — 로컬 Python 스크립트가 모든 면에서 우월.

### 채택 가능성 있는 변형 (참고)
- **의미 단위 분할**(목차 변경 지점, 화제 전환점 등 *semantic boundary*)이 필요한 경우 Gemini Flash가 유리할 수 있음. 단 그 경우는 "분할" 워크플로우가 아니라 "구조화" 워크플로우로 별도 정의해야 함.
- 본 파일럿 범위는 단순 N등분이므로 Gemini로 대체할 이유가 없음.

### 정식 채택 시 필요했을 변경 사항 (보류)
- `transcript-tools.md` 워크플로우에 Gemini wrapper 스크립트 추가
- 3번의 시행착오 끝에 검증된 프롬프트 ("stdin 주입 + 도구 호출 금지 + END_OF_TRANSCRIPT 마커") 고정
- "MCP issues detected" 노이즈 후처리 로직
- 메타헤더 보존 검증 + 누락 시 fallback (Claude로 자동 재실행)

→ 현 단계에서는 **추가 변경 불필요**. transcript-tools는 기존 Python 스크립트 유지.

---

## 6. 메모 (다음 Gemini 파일럿 후보 시 참고)

- gemini CLI는 본질적으로 **에이전트 프레임워크**이지 **순수 LLM 호출 도구가 아님**. 다음 파일럿에서는 (a) Gemini API direct call (Python `google-generativeai` SDK) 또는 (b) `--approval-mode plan` + stdin 주입을 default로 사용 권장.
- "한 글자도 변경 금지" 같은 강한 보존 명령도 Gemini 2.5 Flash는 메타데이터·헤더는 자체 판단으로 정리하는 경향. **검증 필수**.
- 본 파일럿의 31초는 OAuth 인증된 무료 쿼터 사용. 동일 quota는 일일 1,500 req(2.5 Flash) 내에서 무비용. 지속적 운영 시 quota 소진 모니터링 필요.
