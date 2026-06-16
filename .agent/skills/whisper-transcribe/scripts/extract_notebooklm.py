"""
NotebookLM HTML 전사문 추출기
===============================
NotebookLM에서 저장한 HTML 파일에서 전사문 텍스트를 추출합니다.

사용법:
    # 단일 파일
    python extract_notebooklm.py "파일명.html"
    
    # output/ 폴더 전체 (기본)
    python extract_notebooklm.py
    
    # 특정 폴더
    python extract_notebooklm.py --dir "경로"
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

DRIVE_ROOT = Path(r"h:\내 드라이브")
DEFAULT_OUTPUT_DIR = DRIVE_ROOT / "5.기타" / "_inbox" / "녹음" / "output"

# 최소 글자수 — 이보다 짧은 텍스트 블록은 전사문이 아님
MIN_TRANSCRIPT_LENGTH = 500


def extract_transcript_from_html(html_path: Path) -> str | None:
    """HTML 파일에서 가장 긴 한국어 텍스트 블록(=전사문)을 추출합니다."""
    content = html_path.read_text(encoding="utf-8")
    
    # script/style 태그 제거
    clean = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL)
    clean = re.sub(r"<style[^>]*>.*?</style>", "", clean, flags=re.DOTALL)
    
    # HTML 태그 제거 → 순수 텍스트
    text_only = re.sub(r"<[^>]+>", "\n", clean)
    
    # 한국어가 포함된 텍스트 블록만 필터링
    lines = [
        l.strip()
        for l in text_only.split("\n")
        if l.strip() and re.search("[가-힣]", l) and len(l.strip()) > 20
    ]
    
    if not lines:
        return None
    
    # 가장 긴 블록 = 전사문 본문
    lines.sort(key=len, reverse=True)
    transcript = lines[0]
    
    if len(transcript) < MIN_TRANSCRIPT_LENGTH:
        return None
    
    return transcript


def format_transcript(transcript: str, source_name: str) -> str:
    """전사문에 헤더를 붙이고 줄바꿈을 추가합니다."""
    # 문장 끝에서 줄바꿈
    formatted = transcript.replace(". ", ".\n")
    
    header = f"# 전사문: {source_name}\n\n"
    header += f"- **소스**: NotebookLM\n"
    header += f"- **추출일**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    header += f"- **글자수**: {len(transcript):,}\n\n---\n\n"
    
    return header + formatted


def process_html_file(html_path: Path, dry_run: bool = False) -> bool:
    """단일 HTML 파일을 처리합니다."""
    # NotebookLM 보조 파일 건너뛰기 (_files/ 하위 파일)
    if "_files" in str(html_path):
        return False
    
    # 출력 파일명: 원본에서 " - NotebookLM" 제거 + "_transcript.txt"
    stem = html_path.stem.replace(" - NotebookLM", "")
    out_path = html_path.parent / f"{stem}_transcript.txt"
    
    # 이미 추출된 파일 건너뛰기
    if out_path.exists():
        print(f"  ⏭ 이미 추출됨: {out_path.name}")
        return False
    
    print(f"  📄 처리 중: {html_path.name}")
    
    transcript = extract_transcript_from_html(html_path)
    if transcript is None:
        print(f"  ⚠ 전사문을 찾을 수 없음")
        return False
    
    formatted = format_transcript(transcript, stem)
    
    if dry_run:
        print(f"  ✅ [DRY-RUN] {len(transcript):,}자 추출 가능 → {out_path.name}")
    else:
        out_path.write_text(formatted, encoding="utf-8")
        print(f"  ✅ {len(transcript):,}자 추출 → {out_path.name}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="NotebookLM HTML 전사문 추출기")
    parser.add_argument("file", nargs="?", help="처리할 HTML 파일 (없으면 폴더 전체)")
    parser.add_argument("--dir", default=str(DEFAULT_OUTPUT_DIR), help="HTML 파일이 있는 폴더")
    parser.add_argument("--dry-run", action="store_true", help="실제 저장 없이 미리보기")
    args = parser.parse_args()
    
    print("=" * 50)
    print("NotebookLM HTML 전사문 추출기")
    print("=" * 50)
    
    if args.file:
        # 단일 파일 처리
        html_path = Path(args.file)
        if not html_path.exists():
            print(f"❌ 파일을 찾을 수 없음: {html_path}")
            sys.exit(1)
        process_html_file(html_path, args.dry_run)
    else:
        # 폴더 전체 처리
        target_dir = Path(args.dir)
        if not target_dir.exists():
            print(f"❌ 폴더를 찾을 수 없음: {target_dir}")
            sys.exit(1)
        
        html_files = list(target_dir.glob("*.html"))
        # _files 하위 파일 제외
        html_files = [f for f in html_files if "_files" not in str(f)]
        
        if not html_files:
            print(f"  📭 HTML 파일 없음: {target_dir}")
            sys.exit(0)
        
        print(f"\n📂 대상 폴더: {target_dir}")
        print(f"📎 HTML 파일: {len(html_files)}개\n")
        
        success = 0
        for html_file in sorted(html_files):
            if process_html_file(html_file, args.dry_run):
                success += 1
        
        print(f"\n{'=' * 50}")
        print(f"완료: {success}/{len(html_files)}개 추출")
        if args.dry_run:
            print("(DRY-RUN 모드 — 실제 저장되지 않음)")
    
    print()


if __name__ == "__main__":
    main()
