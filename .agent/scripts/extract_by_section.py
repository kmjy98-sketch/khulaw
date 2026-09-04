"""
쟁점별 TOC 기반 마크다운 추출 — 형법 COMPACT OX + 민법 선택형연습1
출력: sync/_교재원문/{과목}/{교재}/{쟁점명}_{교재약칭}.md
"""
import os
import sys
from pathlib import Path
from pypdf import PdfReader

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(VAULT_ROOT)
SYNC = ROOT / "sync" / "_교재원문"


# ─────────────────────────────────────────────────────────────────────────────
# 공통 유틸
# ─────────────────────────────────────────────────────────────────────────────

def merge_same_pages(toc_raw: list) -> list:
    """연속 동일 시작 페이지 항목을 하나의 섹션으로 합침."""
    merged = []
    i = 0
    while i < len(toc_raw):
        name, page = toc_raw[i]
        j = i + 1
        while j < len(toc_raw) and toc_raw[j][1] == page:
            # 이름에서 파트 접두어(part1_01_) 제거 후 병합
            tail = toc_raw[j][0]
            # 숫자_숫자_ 접두어 제거
            parts = tail.split("_", 3)
            if len(parts) >= 3 and parts[1].isdigit():
                tail = "_".join(parts[2:])
            elif len(parts) >= 2 and parts[0].startswith("part"):
                tail = "_".join(parts[2:]) if len(parts) > 2 else parts[-1]
            name = name + "_" + tail
            j += 1
        merged.append((name, page))
        i = j
    return merged


def extract_section(reader: PdfReader, pdf_start: int, pdf_end: int) -> str:
    """pdf_start~pdf_end (1-based inclusive) 페이지 텍스트 추출."""
    lines = []
    total = len(reader.pages)
    for p in range(max(1, pdf_start), min(total, pdf_end) + 1):
        text = reader.pages[p - 1].extract_text() or ""
        lines.append(f"--- Page {p} ---")
        lines.append(text.strip())
        lines.append("")
    return "\n".join(lines)


def build_chunks(toc_merged: list, offset: int, total_pdf: int) -> list:
    """TOC → [(이름, pdf_start, pdf_end)] 변환."""
    chunks = []
    for idx, (name, book_page) in enumerate(toc_merged):
        pdf_start = book_page + offset
        if idx + 1 < len(toc_merged):
            pdf_end = toc_merged[idx + 1][1] + offset - 1
        else:
            pdf_end = total_pdf
        if pdf_start > total_pdf:
            continue
        pdf_end = min(pdf_end, total_pdf)
        chunks.append((name, pdf_start, pdf_end))
    return chunks


def run_book(src_pdf: Path, out_dir: Path, suffix: str, toc_raw: list,
             offset: int, total_pdf: int, book_title: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(str(src_pdf))
    toc = merge_same_pages(toc_raw)
    chunks = build_chunks(toc, offset, total_pdf)

    print(f"\n[{book_title}] {len(chunks)}개 섹션 → {out_dir.name}/")
    ok = 0
    for name, ps, pe in chunks:
        fname = f"{name}{suffix}.md"
        # Windows 파일명 길이 제한 대비
        if len(fname) > 200:
            fname = fname[:195] + suffix[-10:] + ".md"
        out_path = out_dir / fname
        # frontmatter
        book_page_start = ps - offset
        book_page_end = pe - offset
        header = (
            f"---\n"
            f"source: {book_title}\n"
            f"section: {name.replace('_', ' ')}\n"
            f"교재_pages: pp.{book_page_start}–{book_page_end}\n"
            f"pdf_pages: pp.{ps}–{pe}\n"
            f"---\n\n"
        )
        body = extract_section(reader, ps, pe)
        out_path.write_text(header + body, encoding="utf-8")
        char_count = len(body.replace("\n", "").replace("--- Page", ""))
        print(f"  [{'OK' if char_count > 10 else 'EMPTY?'}] {fname[:80]}  "
              f"(교재 pp.{book_page_start}–{book_page_end}, {pe-ps+1}p, {char_count}자)")
        if char_count > 10:
            ok += 1
    print(f"  → {ok}/{len(chunks)} 정상 추출")
    return ok, len(chunks)


# ─────────────────────────────────────────────────────────────────────────────
# 형법 COMPACT OX 제3판
# ─────────────────────────────────────────────────────────────────────────────
FORM_TOC = [
    # (쟁점명, 교재 시작 페이지)
    # 제1편. 형법 일반이론
    ("1편_1장_죄형법정주의", 2),
    ("1편_2장_시간적적용범위", 14),
    ("1편_2장_장소적적용범위", 20),
    # 제2편. 범죄론 — 제2장 구성요건
    ("2편_2장_인과관계_객관적귀속", 32),
    ("2편_2장_고의범", 42),
    ("2편_2장_과실범", 51),
    ("2편_2장_결과적가중범", 62),
    ("2편_2장_부작위범", 70),
    # 제3장 위법성
    ("2편_3장_주관적정당화요소", 82),
    ("2편_3장_정당방위", 84),
    ("2편_3장_긴급피난", 89),
    ("2편_3장_자구행위", 91),
    ("2편_3장_피해자의승낙", 93),
    ("2편_3장_정당행위", 96),
    # 제4장 책임
    ("2편_4장_책임이론", 106),
    ("2편_4장_책임능력", 108),
    ("2편_4장_원인에있어서자유로운행위", 113),
    ("2편_4장_위법성인식", 117),
    ("2편_4장_위법성조각사유전제사실착오", 124),
    ("2편_4장_기대가능성", 128),
    # 제5장 미수론
    ("2편_5장_미수범일반이론", 130),
    ("2편_5장_중지미수", 133),
    ("2편_5장_불능미수", 138),
    ("2편_5장_예비음모", 145),
    # 제6장 공범론
    ("2편_6장_공범이론일반", 150),
    ("2편_6장_공동정범", 152),
    ("2편_6장_합동범과공동범", 160),
    ("2편_6장_필요적공범", 164),
    ("2편_6장_간접정범", 168),
    ("2편_6장_교사범", 172),
    ("2편_6장_방조범", 176),
    ("2편_6장_공범의착오", 181),
    ("2편_6장_공범과신분", 185),
    # 제7장 죄수론
    ("2편_7장_일죄", 194),
    ("2편_7장_수죄", 197),
    # 제3편. 형벌론
    ("3편_1장_형벌일반이론", 208),
    ("3편_2장_몰수", 210),
    ("3편_2장_추징", 215),
    ("3편_3장_형의가중감경면제", 222),
    ("3편_3장_누범", 228),
    ("3편_4장_집행유예", 232),
    ("3편_4장_선고유예가석방", 237),
]

# ─────────────────────────────────────────────────────────────────────────────
# 민법 신민사법선택형연습 1 (5판)
# ─────────────────────────────────────────────────────────────────────────────
CIVIL_TOC = [
    # Part 1 — 민법총칙
    ("part1_01_법원신의칙", 3),
    ("part1_02_권리주체_자연인", 8),
    ("part1_03_권리주체_비영리법인비법인사단", 22),
    ("part1_04_대리", 39),
    ("part1_05_법률행위목적해석", 54),
    ("part1_06_의사표시", 69),
    ("part1_07_법률행위부관", 91),
    ("part1_08_법률행위무효취소", 96),
    ("part1_09_기간", 102),
    ("part1_10_소멸시효1_대상기간기산점효과", 103),
    ("part1_11_소멸시효2_중단포기", 121),
    ("part1_12_제척기간", 141),
    ("part1_13_권리의실효", 143),
    # Part 2 — 채권법(1)
    ("part2_01_채권일반유형", 147),
    ("part2_02_계약성립", 156),
    ("part2_03_계약체결상과실책임", 158),
    ("part2_04_동시이행항변권", 159),
    ("part2_05_위험부담", 169),
    ("part2_06_제3자를위한계약", 169),   # 동일 페이지 → 자동 병합
    ("part2_07_매매계약", 174),
    ("part2_08_임대차계약", 201),
    ("part2_09_도급계약", 230),
    ("part2_10_조합계약", 239),
    ("part2_11_기타전형계약", 249),
    ("part2_12_사무관리", 260),
    ("part2_13_부당이득", 264),
    ("part2_14_불법행위", 277),
    # Part 3 — 채권법(2)
    ("part3_01_변제", 309),
    ("part3_02_상계", 331),
    ("part3_03_공탁경개면제혼동", 346),
    ("part3_04_채무불이행1_유형", 351),
    ("part3_05_채무불이행2_손해배상대상청구권", 363),
    ("part3_06_채무불이행3_과실상계손익상계", 368),
    ("part3_07_채무불이행4_손해배상액예정", 372),
    ("part3_08_계약해제", 377),
    ("part3_09_계약해지", 392),
    ("part3_10_채권자지체", 392),        # 동일 → 병합
    ("part3_11_제3자채권침해", 394),
    ("part3_12_채권자대위권", 395),
    ("part3_13_채권자취소권1_소송요건", 412),
    ("part3_14_채권자취소권2_본안요건", 416),
    ("part3_15_채권자취소권3_효과", 436),
    ("part3_16_지명채권양도", 442),
    ("part3_17_채무인수이행인수계약인수", 457),
    # Part 4 — 담보법(1) 인적담보
    ("part4_01_분할채권불가분채권", 469),
    ("part4_02_연대채무부진정연대채무", 472),
    ("part4_03_보증채무", 481),
    # Part 5 — 담보법(2) 물적담보
    ("part5_01_물상대위권", 501),
    ("part5_02_저당권", 506),
    ("part5_03_유치권", 535),
    ("part5_04_질권", 551),
    ("part5_05_비전형담보", 562),
    ("part5_06_동산채권담보법", 576),
    # Part 6 — 물권법
    ("part6_01_물권총설", 581),
    ("part6_02_부동산물권변동_부동산등기", 585),
    ("part6_03_동산물권변동", 607),
    ("part6_04_법률규정에의한물권변동", 613),
    ("part6_05_물권소멸", 614),
    ("part6_06_취득시효", 616),
    ("part6_07_선점습득발견첨부", 640),
    ("part6_08_소유권범위", 643),
    ("part6_09_소유권에기한물권적청구권", 648),
    ("part6_10_공동소유1_공유", 657),    # 스캔 검증값
    ("part6_11_공동소유2_합유총유", 672),
    ("part6_12_명의신탁", 674),
    ("part6_13_점유권", 691),
    ("part6_14_지상권", 696),
    ("part6_15_지역권", 710),
    ("part6_16_전세권", 711),
    # Part 7 — 가족법
    ("part7_01_가족법총론", 725),
    ("part7_02_혼인", 726),
    ("part7_03_이혼", 736),
    ("part7_04_사실혼", 761),
    ("part7_05_부모와자", 762),
    ("part7_06_친권", 782),
    ("part7_07_후견", 791),
    ("part7_08_친족관계와가족", 800),
    ("part7_09_부양", 801),
    ("part7_10_상속일반", 807),
    ("part7_11_상속인", 807),            # 동일 → 병합
    ("part7_12_상속효력1_포괄승계", 812),
    ("part7_13_상속효력2_공유", 814),
    ("part7_14_상속효력3_상속분", 814),  # 동일 → 병합
    ("part7_15_상속효력4_분할", 820),
    ("part7_16_상속효력5_회복청구권", 828),
    ("part7_17_상속승인포기", 833),
    ("part7_18_상속재산분리", 844),
    ("part7_19_상속인부존재", 844),      # 동일 → 병합
    ("part7_20_유언", 844),              # 동일 → 병합
    ("part7_21_유류분", 855),
]


# ─────────────────────────────────────────────────────────────────────────────
# 실행
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    total_ok = 0
    total_sec = 0

    ok, n = run_book(
        src_pdf=ROOT / "2.형사/94.교재/2026 COMPACT 형법 총론 OX - 제3판_3c_r6_2d.pdf",
        out_dir=SYNC / "형법/김기용_COMPACT형법OX_2026",
        suffix="_김기용_COMPACT형법OX",
        toc_raw=FORM_TOC,
        offset=9,
        total_pdf=251,
        book_title="2026 COMPACT 형법총론 OX 제3판",
    )
    total_ok += ok
    total_sec += n

    ok, n = run_book(
        src_pdf=ROOT / "1.민사/94.교재/2026 신민사법 선택형연습 1 - 변호사 시험 & 각종 국가고시 대비,_3c_r6_2d.pdf",
        out_dir=SYNC / "민법/송영곤_선택형연습1_2026",
        suffix="_송영곤_선택형연습1",
        toc_raw=CIVIL_TOC,
        offset=11,
        total_pdf=879,
        book_title="2026 신민사법 선택형연습 1 (5판)",
    )
    total_ok += ok
    total_sec += n

    print(f"\n=== 전체 {total_ok}/{total_sec} 섹션 추출 완료 ===")
