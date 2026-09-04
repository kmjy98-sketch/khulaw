#!/usr/bin/env python3
"""
sanitize_helper.py — 옵시디언 문법, 가독성, OCR 훼손 정제 자동화 헬퍼.

주요 기능:
1. 단락 중간 개행 제거 및 문장 복원 (구조적 마크다운 라인 제외)
2. OCR 한자 및 오인식 알파벳 한글화 치환 (fix_ocr_hanja.py 규칙 포함)
3. 원본 보존 주석 추가 (변경 라인의 전본을 <!-- original: ... --> 으로 백업)
4. 표 레이아웃 정리 및 2열 표 일관성 포맷팅
"""

import os
import re
import sys
import glob
import shutil
import argparse
from datetime import date
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import VAULT_ROOT, vp  # noqa: E402

# 당사자 및 오인식 한자 규칙 (fix_ocr_hanja.py 참고 및 법률 범용 한자 딕셔너리 확장)
HANJA_MAP = {
    "甲": "갑", "乙": "을", "丙": "병", "丁": "정", "戊": "무",
    "己": "기", "庚": "경", "辛": "신", "壬": "임", "癸": "계",
    "契": "계", "約": "약", "債": "채", "權": "권", "法": "법",
    "物": "물", "人": "인", "事": "사", "件": "건", "判": "판",
    "例": "례", "案": "안", "訴": "소", "訟": "송", "原": "원",
    "告": "고", "被": "피", "申": "신", "請": "청", "答": "답",
    "辯": "변", "證": "증", "明": "명", "理": "리", "解": "해",
    "釋": "석", "規": "규", "定": "정", "則": "칙", "條": "조",
    "項": "항", "號": "호", "芮": "병", "雨": "병", "因": "병",
    "成": "무", "日": "을", "江": "을", "石": "을", "仁": "병",
    "西": "무", "內": "병",
}

# 당사자 맥락 감지
PARTY_CONTEXT = re.compile(r"[갑을병정무]|[甲乙丙丁戊己庚辛壬癸]|\bZ\b")

# Z 및 특수 OCR 오류 치환 규칙
OCR_RULES = [
    (re.compile(r"\bZ(?=[이은는을를의에와과도만]|에게|에서)"), "을"),
    (re.compile(r"\bZ[r]\b"), "을"),
]


def convert_hanja_and_ocr(text: str) -> tuple[str, int]:
    """한자 및 OCR 오인식 문자 치환"""
    count = 0
    new_text = text
    
    # 1. OCR_RULES (Z -> 을 등) 적용
    has_party = bool(PARTY_CONTEXT.search(new_text))
    for pattern, repl in OCR_RULES:
        if has_party:
            new_val, n = pattern.subn(repl, new_text)
            if n > 0:
                new_text = new_val
                count += n
                
    # 2. 일반 법률 한자 딕셔너리 치환
    def _replace_hanja(m):
        char = m.group(0)
        # 괄호로 묶인 경우 (예: "성(成)") 또는 원본 인용 목적 괄호는 보존
        start = m.start()
        end = m.end()
        if start > 0 and new_text[start-1] == '(' and end < len(new_text) and new_text[end] == ')':
            return char
        return HANJA_MAP.get(char, char)
        
    hanja_pattern = re.compile(r"[" + "".join(HANJA_MAP.keys()) + "]")
    new_val, n = hanja_pattern.subn(_replace_hanja, new_text)
    if n > 0:
        new_text = new_val
        count += n
        
    return new_text, count


def is_structural_line(line: str) -> bool:
    """헤더, 리스트, 표, 수식 등 구조적 개행 유지가 필요한 마크다운 라인인지 판단"""
    line_stripped = line.strip()
    if not line_stripped:
        return True
    # 헤더 (#)
    if line_stripped.startswith("#"):
        return True
    # 리스트 (-, *, +, 번호)
    if line_stripped.startswith("-") or line_stripped.startswith("*") or line_stripped.startswith("+"):
        return True
    if re.match(r"^\d+\.\s+", line_stripped):
        return True
    # 표 (|)
    if line_stripped.startswith("|"):
        return True
    # 인용구 (>)
    if line_stripped.startswith(">"):
        return True
    # 코드블록 (```)
    if line_stripped.startswith("```"):
        return True
    # 옵시디언 프런트매터 (---)
    if line_stripped == "---":
        return True
    return False


def reconstruct_paragraphs(content: str) -> tuple[str, int]:
    """단락 중간의 비정상적인 줄바꿈을 제거하여 문장 연결"""
    lines = content.splitlines()
    new_lines = []
    i = 0
    changes = 0
    
    while i < len(lines):
        line = lines[i]
        
        # 구조적 라인이거나 빈 줄이면 개행 유지
        if is_structural_line(line) or (i + 1 < len(lines) and is_structural_line(lines[i+1])):
            new_lines.append(line)
            i += 1
            continue
            
        # 현재 라인의 끝부분과 다음 라인의 시작부분을 확인
        # 문장 종결 기호(. ? !)나 마크다운 기호 등으로 끝나지 않은 경우 합침
        line_stripped = line.rstrip()
        if not line_stripped:
            new_lines.append(line)
            i += 1
            continue
            
        last_char = line_stripped[-1]
        
        # 합쳐야 할 조건: 
        # 1. 마침표, 물음표, 느낌표로 끝나지 않음
        # 2. 한글 자모 또는 숫자로 끝남
        if last_char not in [".", "?", "!", ":", ";", ")", "]", ">", "}"]:
            if i + 1 < len(lines):
                next_line = lines[i+1].lstrip()
                # 다음 라인이 한글이나 특수 조사로 시작하면 병합
                if next_line and not is_structural_line(lines[i+1]):
                    # 병합 전 인라인 백업 주석 생성
                    backup_comment = f"<!-- original: {line} -->"
                    new_lines.append(backup_comment)
                    
                    # 라인을 합치고 한 줄로 취급
                    merged_line = line_stripped + " " + next_line
                    lines[i+1] = merged_line
                    changes += 1
                    i += 1
                    continue
                
        new_lines.append(line)
        i += 1
        
    return "\n".join(new_lines), changes


def sanitize_table(line: str) -> tuple[str, int]:
    """표 레이아웃 다듬기 및 2열 표 형식 맞춤"""
    # 원고-피고 2열 표 규칙
    if "원고" in line and "피고" in line and "|" in line:
        # 헤더 포맷 통일: | **원고 (甲)** | **피고 (乙)** |
        if "원고 (甲)" not in line or "피고 (乙)" not in line:
            return "| **원고 (甲)** | **피고 (乙)** |", 1
            
    # 표 내의 불필요한 연속 공백 정리
    if line.startswith("|") and line.endswith("|"):
        parts = [p.strip() for p in line.split("|")]
        # 구분선인지 확인
        if all(re.match(r"^:?\-+:?$", p) for p in parts[1:-1]):
            return "|---|---|", 0
        cleaned_line = " | ".join(parts).strip()
        if cleaned_line != line:
            return cleaned_line, 1
            
    return line, 0


def process_content(content: str) -> tuple[str, int]:
    """텍스트 내용 전체 정제 프로세스 실행"""
    total_fixes = 0
    
    # 1. 단락 개행 복원
    content, paragraph_fixes = reconstruct_paragraphs(content)
    total_fixes += paragraph_fixes
    
    # 2. 라인별 한자/OCR 및 표 정제
    lines = content.splitlines()
    new_lines = []
    
    for line in lines:
        if line.strip().startswith("<!-- original:"):
            new_lines.append(line)
            continue
            
        # OCR/한자 치환
        cleaned_line, ocr_fixes = convert_hanja_and_ocr(line)
        
        # 표 정제
        if cleaned_line.strip().startswith("|"):
            cleaned_line, table_fixes = sanitize_table(cleaned_line)
            ocr_fixes += table_fixes
            
        if ocr_fixes > 0 and cleaned_line != line:
            new_lines.append(f"<!-- original: {line} -->")
            total_fixes += ocr_fixes
            
        new_lines.append(cleaned_line)
        
    return "\n".join(new_lines), total_fixes


def process_file(file_path: Path, dry_run: bool = False) -> int:
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[ERROR] 파일 읽기 실패 {file_path}: {e}")
        return 0
        
    new_content, fixes = process_content(content)
    if fixes == 0 or new_content == content:
        return 0
        
    if dry_run:
        print(f"[DRY-RUN] {file_path.name} -> {fixes}개 항목 수정 예정")
        return fixes
        
    # 백업 수행 (5.기타/교재원문_백업/...)
    workspace_root = Path(VAULT_ROOT)
    try:
        rel = file_path.relative_to(workspace_root)
        backup_path = workspace_root / "5.기타" / "교재원문_백업" / date.today().isoformat() / "sanitize" / rel
    except ValueError:
        backup_path = workspace_root / "5.기타" / "교재원문_백업" / date.today().isoformat() / "sanitize" / file_path.name
        
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    if not backup_path.exists():
        shutil.copy2(file_path, backup_path)
        
    file_path.write_text(new_content, encoding="utf-8")
    print(f"[FIXED] {file_path.name} -> {fixes}개 항목 정제 및 백업 완료")
    return fixes


def main():
    parser = argparse.ArgumentParser(description="옵시디언 문법 및 OCR 훼손 정제 헬퍼")
    parser.add_argument("path", nargs="?", help="대상 파일 또는 폴더 경로 (기본: WIKI_DIR)")
    parser.add_argument("--dry-run", action="store_true", help="수정 예정 사항 미리보기")
    args = parser.parse_args()
    
    wiki_dir = os.environ.get("WIKI_DIR", vp("sync", "wiki"))
    target_path = Path(args.path) if args.path else Path(wiki_dir)
    
    if target_path.is_file():
        files = [target_path]
    else:
        files = sorted(target_path.rglob("*.md"))
        
    total_files = 0
    total_fixes = 0
    
    for f in files:
        if any(p.startswith("_backup") or p.startswith("_trash") or p.startswith(".") for p in f.parts):
            continue
        if f.name.endswith(".tmp.md"):
            continue
            
        fixes = process_file(f, dry_run=args.dry_run)
        if fixes > 0:
            total_files += 1
            total_fixes += fixes
            
    print(f"\n[정제 요약] 파일: {total_files}개, 수정 건수: {total_fixes}건")


if __name__ == "__main__":
    main()
