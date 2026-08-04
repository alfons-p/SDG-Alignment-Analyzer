"""OCR fallback text extraction for image-only PDFs.

Third rung of the extraction ladder in ``ActivityExtractor.extract_from_pdf``:
tried only after PyMuPDF (fitz) and pdfplumber both return a thin text layer,
i.e. the PDF is scanned images with no embedded text. Rasterises each page with
PyMuPDF and runs Tesseract via ``pytesseract``.

Design notes:
- Mirrors ``PDFExtractor.extract_text_from_pdf`` return shape so the ladder can
  swap sources uniformly.
- OCR is expensive (~1-3 s/page), so results are cached content-addressed
  (SHA256 of the PDF bytes + dpi + lang). A re-run — e.g. Admin ``--replace`` —
  reads the cached text and does zero OCR.
- Degrades gracefully: if the ``tesseract`` binary is missing, ``available()``
  is False and the caller skips OCR rather than crashing the pipeline.
"""

import hashlib
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import fitz  # PyMuPDF


class OCRExtractor:
    """Extract text from scanned/image-only PDFs using Tesseract OCR."""

    def __init__(
        self,
        dpi: int = 300,
        lang: str = "eng",
        max_pages: int = 150,
        min_page_chars: int = 30,
        cache_dir: Optional[Path] = None,
    ):
        self.dpi = dpi
        self.lang = lang
        self.max_pages = max_pages
        # A page with fewer than this many embedded chars is treated as image-only
        # and OCR'd; pages above it keep their (higher-quality) embedded text.
        self.min_page_chars = min_page_chars
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / ".cache" / "ocr"
        self.cache_dir = Path(cache_dir)
        self._checked_available: Optional[bool] = None

    # ── availability ────────────────────────────────────────────────────────

    def available(self) -> bool:
        """True when the Tesseract binary is on PATH and pytesseract imports.
        Cached after the first check so the pipeline probes tesseract once."""
        if self._checked_available is not None:
            return self._checked_available
        ok = shutil.which("tesseract") is not None
        if ok:
            try:
                import pytesseract  # noqa: F401
            except Exception:  # noqa: BLE001
                ok = False
        self._checked_available = ok
        return ok

    # ── cache ───────────────────────────────────────────────────────────────

    def _cache_path(self, content: bytes) -> Path:
        key = hashlib.sha256(content).hexdigest()[:32]
        # min_page_chars is in the key because it changes which pages get OCR'd.
        return self.cache_dir / f"ocr_{key}_{self.dpi}_{self.lang}_{self.min_page_chars}.txt"

    # ── extraction ──────────────────────────────────────────────────────────

    def extract_text_from_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Per-page merge of embedded text and OCR into the standard result dict.

        For each page: keep the embedded text layer when it carries real content
        (>= ``min_page_chars``); OCR the page only when it's image-only. This
        recovers scanned pages in a mixed document while preserving the sharper
        embedded text on the pages that have it.

        Returns a dict with the same keys as ``PDFExtractor`` (``text``,
        ``pages``, ``metadata``, ``sections``) plus ``source_engine="ocr"`` and
        OCR flags in ``metadata`` (``ocr``, ``ocr_pages``, ``ocr_truncated``).
        """
        import pytesseract
        from PIL import Image

        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        content = pdf_path.read_bytes()
        cache_file = self._cache_path(content)

        with fitz.open(pdf_path) as doc:
            page_count = len(doc)
            n = min(page_count, self.max_pages) if self.max_pages else page_count
            truncated = bool(self.max_pages and page_count > self.max_pages)

            # Cache hit: reuse merged text, skip the expensive render+recognise.
            cached = self._read_cache(cache_file)
            if cached is not None:
                pages = [{"page_number": i + 1, "text": ""} for i in range(n)]
                return self._result(pdf_path, cached, pages, page_count, n, truncated)

            page_texts = []
            ocr_pages = 0
            for i in range(n):
                embedded = doc[i].get_text()
                if len(embedded.strip()) >= self.min_page_chars:
                    page_texts.append(embedded)  # keep sharper embedded text
                    continue
                try:
                    pix = doc[i].get_pixmap(dpi=self.dpi)
                    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    page_texts.append(pytesseract.image_to_string(img, lang=self.lang))
                    ocr_pages += 1
                except Exception as e:  # noqa: BLE001 — one bad page must not lose the rest
                    print(f"  OCR page {i + 1} failed: {type(e).__name__}: {e}")
                    page_texts.append(embedded)

        text = "\n".join(page_texts)
        self._write_cache(cache_file, text)
        pages = [{"page_number": i + 1, "text": page_texts[i]} for i in range(len(page_texts))]
        return self._result(pdf_path, text, pages, page_count, ocr_pages, truncated)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _result(self, pdf_path, text, pages, page_count, ocr_pages, truncated) -> Dict[str, Any]:
        return {
            "source": str(pdf_path),
            "text": text,
            "pages": pages,
            "metadata": {
                "page_count": page_count,
                "ocr": True,
                "ocr_pages": ocr_pages,
                "ocr_truncated": bool(truncated),
            },
            "sections": [],
            "source_engine": "ocr",
        }

    @staticmethod
    def _read_cache(path: Path) -> Optional[str]:
        try:
            if path.exists():
                return path.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
        return None

    def _write_cache(self, path: Path, text: str) -> None:
        """Atomic write (tmp + rename) so a crash mid-write leaves no partial file."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, path)
        except Exception as e:  # noqa: BLE001 — cache failure must not fail extraction
            print(f"  OCR cache write failed: {type(e).__name__}: {e}")
