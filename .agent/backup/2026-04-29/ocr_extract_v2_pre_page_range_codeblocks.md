# ocr_extract_v2.ipynb — page_range 수정 직전 코드 스냅샷

생성: 2026-04-29
대상 파일: `H:\내 드라이브\ocr_extract_v2.ipynb`
미러: `H:\내 드라이브\.agent\notebooks\ocr_extract_v2.py`

> **참고**: 원본 .ipynb 파일은 단일 라인 minified JSON으로 토큰 한계(34355)를 초과하여
> Read 툴로 전체 복제가 불가능했습니다. Drive 버전 기록 + 본 코드 스냅샷으로 롤백 안전장치를 마련합니다.
> Edit 툴은 정확한 문자열 매칭으로 동작하므로 다른 셀에는 영향이 없습니다.

---

## (A) `_build_converter()` — .py mirror line 711~716

```python
def _build_converter():
    """marker-pdf PdfConverter 를 한 번만 만들고 재사용."""
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    artifact_dict = create_model_dict()
    return PdfConverter(artifact_dict=artifact_dict)
```

## (B) `_convert_chunk()` — .py mirror line 795~809

```python
def _convert_chunk(converter, pdf_abs: str, start: int, end: int) -> str:
    """단일 청크 변환. md_text 반환. 실패 시 예외 전파."""
    try:
        page_range = list(range(start - 1, end))
        rendered = converter(pdf_abs, page_range=page_range)
    except TypeError:
        # 일부 marker-pdf 버전은 page_range 미지원 → 전체 호출 폴백
        print(f"  [info] page_range 시그니처 미지원 → 전체 호출 폴백.")
        rendered = converter(pdf_abs)
    md_text = getattr(rendered, "markdown", None)
    if md_text is None and hasattr(rendered, "text_content"):
        md_text = rendered.text_content
    if md_text is None:
        md_text = str(rendered)
    return md_text
```

## (C) `_convert_chunk` 호출부 — .py mirror line 864, 871

```python
            md_text = _convert_chunk(converter_holder[0], pdf_abs, start, end)
```

```python
                    md_text = _convert_chunk(converter_holder[0], pdf_abs, start, end)
```

---

## 롤백 방법

1. Google Drive 웹 → 파일 우클릭 → "버전 기록" → 2026-04-29 이전 버전 복원
2. 또는 위 코드 블록을 해당 셀에 수동 복원
