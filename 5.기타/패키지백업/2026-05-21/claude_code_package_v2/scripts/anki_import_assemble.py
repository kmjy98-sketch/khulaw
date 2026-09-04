"""
Anki Import 조립.
outputs/02_cards/ 또는 outputs/06_cases/ 의 TSV 출력 파일들을
Anki Import 가능한 단일 .txt 파일로 조립.

사용법:
    python scripts/anki_import_assemble.py [옵션]

옵션:
    --source 02_cards|06_cases|all  (default: all)
    --note-type rule|case_law|case_problem_card  (Anki에 등록된 Note Type 이름)
    --deck-prefix "변시"  (default 변시)

출력:
    outputs/anki_import/[timestamp]_[note_type].txt

Anki Import 절차:
    1. Anki Desktop → File → Import
    2. 위 .txt 파일 선택
    3. Note Type 매칭, Deck 선택, Fields separated by Tab 확인
    4. Import
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _utils import setup_logger, PACKAGE_ROOT, save_output


def extract_tsv_blocks(content: str) -> list[str]:
    """파일 안에서 ```tsv``` 코드블록 추출"""
    return re.findall(r"```tsv\n(.+?)```", content, re.DOTALL)


def collect_tsv_files(source: str) -> list[Path]:
    """outputs/ 하위에서 TSV 파일 수집"""
    subdirs = []
    if source == "all":
        subdirs = ["02_cards", "06_cases"]
    else:
        subdirs = [source]
    
    files = []
    for subdir in subdirs:
        files.extend((PACKAGE_ROOT / "outputs" / subdir).glob("*_TSV.txt"))
    return sorted(files)


def main():
    parser = argparse.ArgumentParser(description="Anki Import 조립")
    parser.add_argument("--source", default="all",
                        choices=["02_cards", "06_cases", "all"])
    parser.add_argument("--note-type", default=None,
                        help="필터링할 Note Type (TSV header로 추정)")
    parser.add_argument("--deck-prefix", default="변시")
    args = parser.parse_args()
    
    logger = setup_logger("anki_assemble")
    logger.info(f"=== Anki Import 조립 시작 ===")
    
    files = collect_tsv_files(args.source)
    if not files:
        logger.warning(f"TSV 파일 없음: outputs/{args.source}/")
        return
    
    logger.info(f"발견 파일: {len(files)}개")
    
    # 모든 TSV 블록 수집 (header 통일 가정)
    all_rows = []
    header = None
    
    for f in files:
        content = f.read_text(encoding="utf-8")
        blocks = extract_tsv_blocks(content)
        for block in blocks:
            lines = [l for l in block.strip().split("\n") if l.strip()]
            if not lines:
                continue
            file_header = lines[0]
            
            if header is None:
                header = file_header
            elif file_header != header:
                logger.warning(
                    f"{f.name}: header 불일치, 별도 처리 권장\n"
                    f"  기준: {header[:80]}\n  현재: {file_header[:80]}"
                )
                continue
            
            all_rows.extend(lines[1:])
    
    if not header:
        logger.error("TSV header 미발견")
        return
    
    # 출력
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = header + "\n" + "\n".join(all_rows)
    
    out_dir = PACKAGE_ROOT / "outputs" / "anki_import"
    out_dir.mkdir(exist_ok=True)
    out_filename = f"{timestamp}_{args.source}_{len(all_rows)}cards.txt"
    out_path = out_dir / out_filename
    out_path.write_text(output, encoding="utf-8")
    
    logger.info(f"완료: {out_path.relative_to(PACKAGE_ROOT)}")
    logger.info(f"총 카드: {len(all_rows)}장")
    logger.info(f"\n=== Anki Import 절차 ===")
    logger.info(f"1. Anki Desktop → File → Import")
    logger.info(f"2. {out_path.name} 선택")
    logger.info(f"3. Note Type 매칭, Deck 선택, Fields separated by Tab 확인")
    logger.info(f"4. Import")


if __name__ == "__main__":
    main()
