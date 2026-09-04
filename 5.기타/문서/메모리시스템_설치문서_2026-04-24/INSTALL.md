# 설치 가이드 — PC에서 실행

## 전제조건
- Google Drive (H:\내 드라이브) 연결됨
- Python 3.8+ 설치됨
- Claude Code 또는 Cowork 사용 가능

## 설치 순서 (5분)

### Step 1: 스크립트 복사 (1분)

outputs/karpathy_memory_system/scripts/ 폴더의 파일 3개를
H:\내 드라이브\.agent\scripts\ 에 복사:

```
flush.py   → H:\내 드라이브\.agent\scripts\flush.py
compile.py → H:\내 드라이브\.agent\scripts\compile.py
lint.py    → H:\내 드라이브\.agent\scripts\lint.py
```

### Step 2: 폴더 생성 (30초)

```powershell
mkdir "H:\내 드라이브\.auto-memory\session_logs"
mkdir "H:\내 드라이브\.auto-memory\daily"
mkdir "H:\내 드라이브\.auto-memory\wiki"
```

### Step 3: CLAUDE.md 규칙 추가 (1분)

`CLAUDE_MD_추가규칙.md` 파일의 내용을
H:\내 드라이브\CLAUDE.md 끝에 붙여넣기.

또는 Cowork/Claude Code에서:
```
CLAUDE.md에 #42~#45 규칙을 추가해줘.
파일: outputs/karpathy_memory_system/CLAUDE_MD_추가규칙.md 내용 참조.
```

### Step 4: 워크플로우 수정 (2분)

Cowork/Claude Code에서:
```
워크플로우_수정사항.md를 읽고 해당 내용을
lecture-notes.md, socratic.md, consolidate-memory/SKILL.md,
CLAUDE.md의 Auto-Load 테이블에 각각 반영해줘.
```

### Step 5: 동작 확인 (30초)

```powershell
cd "H:\내 드라이브"
python .agent/scripts/lint.py --report-only
```

에러 없이 "메모리 시스템 건강 체크" 출력되면 설치 완료.

## 사용법

### 일상 사용 (자동)
- 세션 시작 → Claude가 wiki/_index.md 자동 참조 (#42)
- 세션 종료 → Claude가 세션 로그 자동 기록 (#43)

### 주기적 정비 (수동, 주 1회 권장)
1. "메모리 컴파일해줘" → flush + compile 실행
2. "메모리 정비해줘" 또는 "lint 돌려줘" → lint 실행

### 직접 실행 (터미널)
```powershell
# 세션 로그 → daily log
python .agent/scripts/flush.py

# daily log → wiki 아티클
python .agent/scripts/compile.py

# 건강 체크
python .agent/scripts/lint.py

# 전체 재구축
python .agent/scripts/compile.py --rebuild
```
