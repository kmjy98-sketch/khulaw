"""
ocr_extract_v2.ipynb — page_range ConfigParser 주입 패치 적용 스크립트

실행:
    cd "H:\\내 드라이브"
    python ".agent\\backup\\2026-04-29\\apply_page_range_fix.py"

동작:
    1. 원본 백업 → .agent/backup/2026-04-29/ocr_extract_v2_pre_page_range.ipynb
    2. 두 셀(_build_converter, _convert_chunk + 호출부)을 새 코드로 교체
    3. JSON 파싱 검증
    4. 검증 실패 시 자동 롤백

근거: marker-pdf v1.x는 PdfConverter() 시그니처에서 page_range를 직접 받지 않으며,
      ConfigParser로 config={"page_range": "0-49"} 형태로 주입해야 함.
"""

from __future__ import annotations
import json
import shutil
import sys
from pathlib import Path

# === 경로 ===
ROOT = Path(r"H:\내 드라이브")
TARGET = ROOT / "ocr_extract_v2.ipynb"
BACKUP_DIR = ROOT / ".agent" / "backup" / "2026-04-29"
BACKUP = BACKUP_DIR / "ocr_extract_v2_pre_page_range.ipynb"

# === 교체 대상 코드 ===

OLD_BUILD_CONVERTER = """def _build_converter():
    \"\"\"marker-pdf PdfConverter 를 한 번만 만들고 재사용.\"\"\"
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    artifact_dict = create_model_dict()
    return PdfConverter(artifact_dict=artifact_dict)"""

NEW_BUILD_CONVERTER = """def _build_converter(page_range_str=None):
    \"\"\"marker-pdf PdfConverter — page_range는 ConfigParser로 주입.\"\"\"
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.config.parser import ConfigParser

    # artifact_dict는 한 번만 생성해서 함수 속성으로 캐시 (모델 재사용)
    if not hasattr(_build_converter, \"_artifact_dict\"):
        _build_converter._artifact_dict = create_model_dict()

    config_dict = {}
    if page_range_str:
        config_dict[\"page_range\"] = page_range_str

    config_parser = ConfigParser(config_dict)
    return PdfConverter(
        config=config_parser.generate_config_dict(),
        artifact_dict=_build_converter._artifact_dict,
        processor_list=config_parser.get_processors(),
        renderer=config_parser.get_renderer(),
    )"""

OLD_CONVERT_CHUNK = """def _convert_chunk(converter, pdf_abs: str, start: int, end: int) -> str:
    \"\"\"단일 청크 변환. md_text 반환. 실패 시 예외 전파.\"\"\"
    try:
        page_range = list(range(start - 1, end))
        rendered = converter(pdf_abs, page_range=page_range)
    except TypeError:
        # 일부 marker-pdf 버전은 page_range 미지원 → 전체 호출 폴백
        print(f\"  [info] page_range 시그니처 미지원 → 전체 호출 폴백.\")
        rendered = converter(pdf_abs)
    md_text = getattr(rendered, \"markdown\", None)
    if md_text is None and hasattr(rendered, \"text_content\"):
        md_text = rendered.text_content
    if md_text is None:
        md_text = str(rendered)
    return md_text"""

NEW_CONVERT_CHUNK = """def _convert_chunk(pdf_abs: str, start: int, end: int) -> str:
    \"\"\"단일 청크 변환. 청크별 PdfConverter 새로 만들고 page_range는 ConfigParser로 주입.
    filepath만 전달 (page_range 키워드 인자 폐기). md_text 반환. 실패 시 예외 전파.
    \"\"\"
    page_range_str = f\"{start - 1}-{end - 1}\"  # 0-based, 양 끝 포함
    converter = _build_converter(page_range_str=page_range_str)
    rendered = converter(pdf_abs)
    md_text = getattr(rendered, \"markdown\", None)
    if md_text is None and hasattr(rendered, \"text_content\"):
        md_text = rendered.text_content
    if md_text is None:
        md_text = str(rendered)
    return md_text"""

OLD_CALL_BLOCK = """            md_text = _convert_chunk(converter_holder[0], pdf_abs, start, end)
        except Exception as e:
            if _is_oom_error(e):
                print(f\"  [OOM] {book_name} p{start}-{end}: {type(e).__name__}: {e}\")
                print(f\"  [OOM] converter 재생성 후 1회 재시도 ...\")
                try:
                    converter_holder[0] = _recycle_converter(converter_holder[0])
                    md_text = _convert_chunk(converter_holder[0], pdf_abs, start, end)"""

NEW_CALL_BLOCK = """            md_text = _convert_chunk(pdf_abs, start, end)
        except Exception as e:
            if _is_oom_error(e):
                print(f\"  [OOM] {book_name} p{start}-{end}: {type(e).__name__}: {e}\")
                print(f\"  [OOM] artifact_dict 캐시 비우고 재시도 ...\")
                try:
                    if hasattr(_build_converter, \"_artifact_dict\"):
                        del _build_converter._artifact_dict
                    _free_memory(verbose=True)
                    md_text = _convert_chunk(pdf_abs, start, end)"""


def cell_source_text(cell: dict) -> str:
    src = cell.get("source", "")
    if isinstance(src, list):
        return "".join(src)
    return src


def set_cell_source(cell: dict, new_text: str) -> None:
    # 원본이 리스트였으면 리스트 형식 유지 (각 줄 끝에 \n, 마지막 줄은 \n 없이)
    src = cell.get("source", "")
    if isinstance(src, list):
        lines = new_text.split("\n")
        out = []
        for i, line in enumerate(lines):
            if i < len(lines) - 1:
                out.append(line + "\n")
            else:
                if line:
                    out.append(line)
        cell["source"] = out
    else:
        cell["source"] = new_text


def apply_replacement(cells: list, old: str, new: str, label: str) -> bool:
    for cell in cells:
        if cell.get("cell_type") != "code":
            continue
        text = cell_source_text(cell)
        if old in text:
            new_text = text.replace(old, new, 1)
            set_cell_source(cell, new_text)
            print(f"  [OK] {label}: 교체 완료")
            return True
    print(f"  [ERR] {label}: old 패턴을 찾지 못함")
    return False


def main() -> int:
    if not TARGET.exists():
        print(f"[ERR] 대상 파일 없음: {TARGET}", file=sys.stderr)
        return 2

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # 1) 백업
    print(f"[1/4] 백업 → {BACKUP}")
    shutil.copy2(TARGET, BACKUP)

    # 2) 로드
    print(f"[2/4] 로드 → {TARGET}")
    with open(TARGET, "r", encoding="utf-8") as f:
        nb = json.load(f)
    cells = nb.get("cells", [])
    print(f"     셀 수: {len(cells)}")

    # 3) 교체
    print("[3/4] 교체")
    ok1 = apply_replacement(cells, OLD_BUILD_CONVERTER, NEW_BUILD_CONVERTER, "_build_converter")
    ok2 = apply_replacement(cells, OLD_CONVERT_CHUNK, NEW_CONVERT_CHUNK, "_convert_chunk")
    ok3 = apply_replacement(cells, OLD_CALL_BLOCK, NEW_CALL_BLOCK, "_convert_chunk 호출부")

    if not (ok1 and ok2 and ok3):
        print("[ERR] 일부 패턴 매칭 실패 — 변경 사항 저장하지 않음. 원본 그대로.", file=sys.stderr)
        return 3

    # 4) 저장 + 검증
    print("[4/4] 저장 + 검증")
    tmp = TARGET.with_suffix(".ipynb.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False)
    # 재파싱 검증
    try:
        with open(tmp, "r", encoding="utf-8") as f:
            json.load(f)
    except Exception as e:
        tmp.unlink(missing_ok=True)
        print(f"[ERR] 검증 실패: {e}", file=sys.stderr)
        return 4
    tmp.replace(TARGET)
    print(f"     완료. 백업: {BACKUP}")
    print()
    print("=== 다음 단계 ===")
    print("  Colab 에서 ocr_extract_v2.ipynb 새로 열기 → 처음부터 실행")
    print("  marker-pdf 가 ConfigParser 시그니처를 받아 page_range를 정상 인식해야 함")
    return 0


if __name__ == "__main__":
    sys.exit(main())
