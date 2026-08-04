"""Tests for the OCR fallback extractor.

The integration test runs real Tesseract on a known image-only council PDF
(WA Carnamah 2023 — 64 pages, no text layer) and is skipped when the tesseract
binary or the sample PDF is absent, so the suite stays green on machines without
OCR installed.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.ocr_extractor import OCRExtractor

# Known image-only sample (0 chars in its text layer -> OCR must recover text).
SAMPLE_PDF = Path("data/raw/2023/WA/WA_Carnamah_Rural_2023.pdf")

_ocr = OCRExtractor()
_needs_ocr = pytest.mark.skipif(
    not _ocr.available(), reason="tesseract binary not installed"
)
_needs_sample = pytest.mark.skipif(
    not SAMPLE_PDF.exists(), reason=f"sample PDF missing: {SAMPLE_PDF}"
)


def test_available_returns_bool():
    assert isinstance(OCRExtractor().available(), bool)


def test_cache_path_is_content_addressed():
    ocr = OCRExtractor(dpi=300, lang="eng")
    a = ocr._cache_path(b"hello")
    b = ocr._cache_path(b"world")
    assert a != b
    assert a.name.startswith("ocr_") and a.name.endswith("_300_eng_30.txt")
    # Same bytes -> same key (deterministic).
    assert ocr._cache_path(b"hello") == a


def test_result_shape_matches_extractor_contract():
    ocr = OCRExtractor()
    r = ocr._result(Path("x.pdf"), "some text", [{"page_number": 1, "text": "t"}], 3, 3, False)
    assert set(r) >= {"source", "text", "pages", "metadata", "sections"}
    assert r["source_engine"] == "ocr"
    assert r["metadata"]["ocr"] is True
    assert r["metadata"]["page_count"] == 3


@_needs_ocr
@_needs_sample
def test_ocr_recovers_text_from_image_only_pdf(tmp_path):
    ocr = OCRExtractor(dpi=300, max_pages=8, cache_dir=tmp_path)  # 8 pages: fast but enough
    result = ocr.extract_text_from_pdf(SAMPLE_PDF)

    assert result["source_engine"] == "ocr"
    assert result["metadata"]["ocr"] is True
    # A scanned annual report yields plenty of recognised text.
    assert len(result["text"]) > 2000, f"OCR text too short: {len(result['text'])}"

    # Cache file written for the content+dpi+lang+min_page_chars key.
    cache_files = list(Path(tmp_path).glob("ocr_*_300_eng_*.txt"))
    assert len(cache_files) == 1


@_needs_ocr
@_needs_sample
def test_second_call_hits_cache_and_skips_tesseract(tmp_path):
    ocr = OCRExtractor(dpi=300, max_pages=4, cache_dir=tmp_path)
    ocr.extract_text_from_pdf(SAMPLE_PDF)  # populate cache

    import pytesseract
    with patch.object(pytesseract, "image_to_string") as m:
        result = ocr.extract_text_from_pdf(SAMPLE_PDF)
        m.assert_not_called()  # cache hit -> no OCR
    assert len(result["text"]) > 2000
