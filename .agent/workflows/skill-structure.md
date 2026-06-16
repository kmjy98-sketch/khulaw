# Skill Structure

> **갱신 (2026-04-21)**: Ingest/Prep 그룹에 `pdf-export`(md→PDF 출력) 추가, `pdf-ingest`에 OCR 경로(`ocr_extract.py`) 문서화 완료. Local Skill Map의 G1 하위 노드 S17 추가.
>
> **갱신 (2026-04-10)**: LanceDB → qmd 이전 반영 완료. `lancedb-rag` 노드 제거, `qmd (law-notes)` 로 통합. 관련 helper: `.agent/lib/qmd_search.py`.

## 0. Detailed Legal Suite Flow

```mermaid
flowchart LR
    DOC["contract / nda / inline text"] --> RUN["run_legal_suite.py"]
    PLAY["legal_playbook.md"] --> RUN
    TPL["legal_templates.md"] --> RUN
    RUN --> R1["legal_review.md"]
    RUN --> R2["legal_compliance.md"]
    RUN --> R3["legal_briefing.md"]
    RUN --> R4["legal_response.md"]
    RUN --> R5["legal_socratic_packet.json"]
    RUN --> LOG["legal_suite_dry_run_log.json"]
```

기준:
- `H:\내 드라이브\AGENTS.md`
- `H:\내 드라이브\.agent\skills\*`
- `H:\내 드라이브\.agent\workflows\socratic.md`
- `H:\내 드라이브\.agent\workflows\case-answer-rag.md`
- `H:\내 드라이브\.agent\workflows\legal-socratic-rag.md`
- `H:\내 드라이브\.agent\skills\textbook-problem-intake\SKILL.md`
- `H:\내 드라이브\.agent\skills\case-answer-review\SKILL.md`

메모:
- 아래 묶음은 현재 폴더와 문서 기준의 도식용 그룹이다.
- 연결선은 위 기준 문서에서 확인된 흐름만 표시한다.

## 1. Local Skill Map

```mermaid
flowchart LR
    AG["AGENTS.md"] --> WF["Workflow Docs"]
    AG --> SG["Local Skill Groups"]

    WF --> W1["classification-rules_v2.md"]
    WF --> W2["socratic.md"]
    WF --> W3["case-answer-rag.md"]
    WF --> W4["lecture-notes.md"]
    WF --> W5["legal-socratic-rag.md"]
    WF --> W6["leet-solve.md"]
    WF --> W7["colab-pipeline.md"]
    WF --> W8["skill-structure.md"]

    SG --> G1["Ingest / Prep"]
    SG --> G2["Index / State"]
    SG --> G3["Retrieval / Learning"]
    SG --> G4["Review / Domain"]

    G1 --> S11["file-classification"]
    G1 --> S12["whisper-transcribe"]
    G1 --> S13["transcript-tools"]
    G1 --> S14["transcript-correction"]
    G1 --> S15["pdf-ingest"]
    G1 --> S16["textbook-reflow"]
    G1 --> S17["pdf-export"]

    G2 --> S21["auto-index"]
    G2 --> S22["problem-index"]
    G2 --> S23["textbook-problem-intake"]
    G2 --> S24["progress-tracker"]
    G2 --> S25["spaced-repetition"]

    G3 --> S31["qmd (law-notes)"]
    G3 --> S32["socratic-loader"]
    G3 --> S33["socratic-core"]
    G3 --> S34["study-notes"]

    G4 --> S41["case-answer-review"]
    G4 --> S42["legal-review"]
    G4 --> S43["legal-compliance"]
    G4 --> S44["legal-briefing"]
    G4 --> S45["legal-response"]
    G4 --> S46["korean-law-mcp (MCP 서버)"]
    G4 --> S47["law-note-supplement"]
```

## 2. Verified Flow Links

```mermaid
flowchart TD
    PDFI["pdf-ingest"] --> EXTRACTS[".agent/data/pdf_extracts"]
    TPI["textbook-problem-intake"] --> SCAN["scan_textbook_embedded_problems.py"]
    TPI --> PIPE["run_textbook_intake.py"]
    TPI --> REG["register_textbook_problem_candidates.py"]

    EXTRACTS --> PIPE
    PIPE --> SCAN
    PIPE --> REG
    SCAN --> CAND["textbook_problem_candidates.json"]
    SCAN --> SCANLOG["textbook_problem_scan_log.json"]
    REG --> REGLOG["textbook_problem_register_log.json"]
    PIPE --> PIPELOG["textbook_problem_pipeline_log.json"]
    REG --> PINDEX["problem_index.json"]

    PINDEX --> PI["problem-index"]
    PINDEX --> EXISS["extract_issues.py"]
    EXISS --> ISSFREQ["issue_frequency.json"]
    ISSFREQ --> SNOTES["study-notes (collect.py)"]
    ISSFREQ --> LNOTE
    PINDEX --> CAR["case-answer-review"]
    CAND --> CAR

    PTRACK["progress-tracker"] --> PROGRESS["progress.json"]
    SRS["spaced-repetition"] --> SRSLOG["srs_log.json"]
    WTRANS["whisper-transcribe"] --> TTOOLS["transcript-tools"]
    TTOOLS --> TCORR["transcript-correction"]
    TCORR --> PTRACK
    TCORR --> PI
    TCORR --> PDFI

    PROGRESS --> SLOAD["socratic-loader"]
    LEARN["learning.json"] --> SLOAD
    SRSLOG --> SLOAD
    SLOAD --> QMD["qmd (law-notes)"]
    SLOAD --> PI

    CAR --> LEARN
    CAR --> QMD

    LREV["legal-review"] --> QMD
    LPLAY["legal_playbook.md"] --> LREV
    LPLAY --> LCOMP["legal-compliance"]
    LPLAY --> LRESP["legal-response"]
    LTPL["legal_templates.md"] --> LCOMP
    LTPL --> LBRIEF["legal-briefing"]
    LTPL --> LRESP
    LREV --> LBRIEF
    LREV --> LRESP
    LREV --> KLMCP["korean-law-mcp"]
    QMD --> KLMCP
    KLMCP --> LAWRAW["조문 원문 / 판례 전문"]

    SC["socratic-core"] -.->|정답 공개 시| KLMCP
    LNOTE["law-note-supplement"] -.->|augment/review 시| KLMCP
    CAR --> KLMCP
```

## 3. Current Reading Guide

- 조악한 교재/기출문제 파싱본을 최적의 렌더링으로 일관화할 때: `textbook-reflow`
- 정리노트 `.md`를 시험용 A4 PDF로 일괄 출력할 때: `pdf-export` (출력 경로 `5.기타/정리노트PDF/{YYYY-MM-DD}/`)
- 교재 내부 문제 후보를 잡을 때: `textbook-problem-intake` -> `problem-index`
- 전사문 교정과 완료 반영을 할 때: `transcript-correction`
- 사례답안 채점과 대비자료를 만들 때: `case-answer-review`
- 소크라틱 학습 세션을 열 때: `socratic.md` -> `socratic-loader` -> `socratic-core`
- 리걸 검토 결과를 학습/RAG와 분리 연계할 때: `legal-socratic-rag.md`
- 조문 원문·판례 전문이 필요할 때: `korean-law-mcp` (API 키 설정 후 MCP 도구 직접 호출)
- 기존 법학 노트 보완·오류검토·재구조화할 때: `law-note-supplement` (augment/review/restructure 모드)
- 기출/사례 쟁점 빈도를 추출할 때: `problem-index` → `extract_issues.py` → `issue_frequency.json`
- 노트 목차를 쟁점 중심으로 재배치할 때: `law-note-supplement` restructure(issue-priority) 서브모드

## 4. Detailed Intake Flow

```mermaid
flowchart LR
    A["New textbook PDFs"] --> B["pdf-ingest extract-only"]
    B --> C[".agent/data/pdf_extracts/chunks_index.json"]
    C --> D["textbook-problem-intake run_textbook_intake.py"]
    D --> E["scan_textbook_embedded_problems.py"]
    E --> F["textbook_problem_candidates.json"]
    E --> G["textbook_problem_scan_log.json"]
    D --> H["register_textbook_problem_candidates.py (dry-run/apply)"]
    H --> I["textbook_problem_register_log.json"]
    D --> J["textbook_problem_pipeline_log.json"]
    H --> K["problem_index.json > problems.textbook"]
    F --> L["case-answer-review"]
    K --> L
```

## 5. Detailed Socratic Flow

```mermaid
flowchart LR
    P["progress.json"] --> SL["socratic-loader"]
    LRN["learning.json"] --> SL
    SRS["srs_log.json"] --> SL
    PI2["problem_index.json"] --> SL
    QMD2["qmd (law-notes)"] --> SL
    SL --> SESSION["session bootstrap output"]
    SESSION --> SC["socratic-core"]
    SC --> LRN
    SC --> P
    SC --> SRS
```
