"""Gemini Op 로그 검증 룰.

각 룰은 (severity, message) 또는 None 반환.
severity: 'red' | 'yellow' | 'green'

red: 사실 위반 (silent drop, 경로 위조)
yellow: 의심 (단정 근거 없음, 과도 변경)
green: 통과 (룰 위반 없음)
"""
import re
from pathlib import Path

BASE = Path('H:/내 드라이브')


def _extract_paths_from_section(log_text: str) -> list:
    """`### 생성/작성/수정 파일` 섹션 안의 백틱 경로 추출."""
    claimed = []
    in_section = False
    section_pat = re.compile(r'^\s*#{2,4}\s+(?:생성|작성|수정)\s*파일')
    header_pat = re.compile(r'^\s*#{2,4}\s+')
    for line in log_text.split('\n'):
        if section_pat.match(line):
            in_section = True
            continue
        if in_section and header_pat.match(line):
            in_section = False
            continue
        if in_section:
            # 백틱 내 경로 (공백·한글·콜론 포함 가능)
            for p in re.findall(r'`([^`]+\.(?:md|py|json|txt|yaml|yml|ps1|ipynb))`', line):
                claimed.append(p.strip())
    return claimed


def _resolve_path(p: str) -> Path:
    """다양한 표기 → Path 해석."""
    raw = Path(p)
    if raw.is_absolute() and raw.exists():
        return raw
    # workspace 기준 상대
    rel = BASE / p
    if rel.exists():
        return rel
    # 'H:/...' 같은 절대인데 못 찾으면 BASE 기준 폴백
    return raw


def rule_silent_drop(log_text: str, frontmatter: dict) -> tuple:
    """로그가 생성·수정했다고 주장한 파일이 실제 존재하는지 확인.

    검사 대상: '### 생성/작성/수정 파일' 섹션 내 백틱 경로만.
    (자유 문장 내 경로는 false positive 위험으로 제외)
    """
    claimed_files = _extract_paths_from_section(log_text)
    missing = []
    for f in claimed_files:
        resolved = _resolve_path(f)
        if not resolved.exists():
            missing.append(f)
    if missing:
        return ('red', f'silent_drop: 주장된 파일이 존재하지 않음 → {missing[:3]}')
    return None


def rule_path_fabrication(log_text: str, frontmatter: dict) -> tuple:
    """로그 본문 내 백틱 경로 중 실재하지 않는 것 탐지 (생성/수정 섹션 제외).

    생성·수정 섹션은 rule_silent_drop이 별도 처리하므로 중복 방지.
    """
    # 섹션 추출 결과는 silent_drop에서 처리하므로 여기서는 제외
    section_paths = set(_extract_paths_from_section(log_text))

    fake_paths = []
    for p in re.findall(r'`([^`]+\.(?:md|py|json|txt|yaml|yml|ps1|ipynb))`', log_text):
        if p in section_paths:
            continue
        # 명백히 경로처럼 보이는 것만 (디렉터리 구분자 포함)
        if '/' not in p and '\\' not in p:
            continue
        resolved = _resolve_path(p)
        if not resolved.exists():
            fake_paths.append(p)
    if fake_paths:
        return ('red', f'path_fabrication: 존재하지 않는 경로 인용 → {fake_paths[:3]}')
    return None


def rule_claim_without_evidence(log_text: str, frontmatter: dict) -> tuple:
    """'확인됨', '검증됨', '~인 것 같다' 등 근거 없는 단정."""
    suspect_phrases = [
        r'확인됨', r'검증됨', r'~인 것 같다', r'~으로 보인다',
        r'추정됨', r'~일 것이다',
    ]
    hits = []
    for phrase in suspect_phrases:
        m = re.search(phrase, log_text)
        if m:
            hits.append(phrase.strip('~'))
    if hits:
        return ('yellow', f'claim_without_evidence: 추측·미검증 단정 표현 → {hits}')
    return None


def rule_excessive_modification(log_text: str, frontmatter: dict) -> tuple:
    """과도한 파일 변경 (안전장치). 10개 초과면 yellow."""
    fc = frontmatter.get('files_created', 0)
    fm = frontmatter.get('files_modified', 0)
    try:
        total = int(fc) + int(fm)
    except (ValueError, TypeError):
        total = 0
    if total > 10:
        return ('yellow', f'excessive_modification: 변경 파일 수 {total} > 10')
    return None


def rule_deletion_attempt(log_text: str, frontmatter: dict) -> tuple:
    """삭제 관련 키워드 탐지 (CLAUDE.md #16 위반 가능성)."""
    if re.search(r'(?:Remove-Item|\brm\s|\bdel\s|rmdir|unlink\(|os\.remove)', log_text):
        return ('red', 'deletion_attempt: 삭제 명령 흔적 발견 (#16 위반)')
    return None


# 룰 레지스트리 (순서 = 평가 순서)
RULES = [
    rule_silent_drop,
    rule_path_fabrication,
    rule_deletion_attempt,
    rule_claim_without_evidence,
    rule_excessive_modification,
]


def evaluate(log_text: str, frontmatter: dict) -> dict:
    """모든 룰 실행 → 최악 severity + 위반 리스트 반환."""
    violations = []
    severity_order = {'green': 0, 'yellow': 1, 'red': 2}
    worst = 'green'

    for rule in RULES:
        try:
            result = rule(log_text, frontmatter)
        except Exception as e:
            violations.append({
                'rule': rule.__name__,
                'severity': 'yellow',
                'message': f'rule_error: {e}',
            })
            continue
        if result is None:
            continue
        sev, msg = result
        violations.append({
            'rule': rule.__name__,
            'severity': sev,
            'message': msg,
        })
        if severity_order[sev] > severity_order[worst]:
            worst = sev

    return {
        'severity': worst,
        'violations': violations,
    }
