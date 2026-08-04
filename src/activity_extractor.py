"""Activity Extraction Module.

Identifies and extracts meaningful activities from council reports.
Uses BERT activity classifier (DeBERTa-v3-small) by default.
Falls back to spaCy heuristics if the model is unavailable or --no-bert-classifier is set.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union

from src.pdf_extractor import PDFExtractor
from src.text_processor import TextProcessor
from src.llm_activity_labeler import LLMActivityLabeler
from src.enhanced_pdf_extractor import PDFPlumberExtractor, SentenceReconstructor
from src.activity_classifier import ActivityClassifier


# Strong signals that a page is part of the actual financial statements section
# (not just a TOC entry or narrative mention)
_FINANCIAL_SECTION_TITLE_MARKERS = [
    "annual financial report",
    "certification of the financial statements",
    "independent audit report",
    "independent auditor's report",
    "auditor's independence declaration",
    "statement of comprehensive income",
    "statement of financial position",
    "statement of cash flows",
    "statement of changes in equity",
    "notes to the financial statements",
    "notes to and forming part of the financial statements",
    "consolidated financial report",
]

# Weak signals — contribute confidence but don't alone trigger financial section start
_FINANCIAL_PAGE_CONTENT_MARKERS = [
    "general purpose financial statements",
    "special purpose financial statements",
    "certified financial statements",
    "audited financial statements",
    "income statement",
    "balance sheet",
]


def _is_financial_section_page(page_text: str) -> bool:
    """Check if a single page is part of the financial statements section."""
    text_lower = page_text.lower()
    for marker in _FINANCIAL_SECTION_TITLE_MARKERS:
        if marker in text_lower:
            return True
    return False


def _find_financial_section_start(pages: list[dict]) -> int:
    """
    Find the index of the first page in the financial statements section.

    Uses page-level detection to find where the ACTUAL financial report begins,
    avoiding false positives from TOC entries and narrative mentions.

    Returns the page index, or len(pages) if no financial section found.
    """
    # Pass 1: Look for strong standalone section markers (page titles/headers)
    for i, page in enumerate(pages):
        text = page["text"].strip()
        text_lower = text.lower()
        first_line = text_lower.split("\n")[0].strip() if text else ""

        # Strong signal: page opens with financial report title
        for marker in _FINANCIAL_SECTION_TITLE_MARKERS:
            if first_line == marker or first_line.startswith(marker):
                return i
            # Also check if the marker appears as a heading within first 3 lines
            first_3_lines = "\n".join(text_lower.split("\n")[:3])
            if f"\n{marker}\n" in f"\n{first_3_lines}\n":
                return i

    # Pass 2: "Certification of the Financial Statements" is the strongest
    # unambiguous signal — it never appears in TOC or narrative
    for i, page in enumerate(pages):
        text_lower = page["text"].lower()
        if "certification of the financial statements" in text_lower:
            # Look nearby for audit/accounting language to confirm
            context = text_lower
            audit_signals = ["opinion", "audit", "compliance", "accounting standard",
                           "true and fair", "internal control"]
            hits = sum(1 for s in audit_signals if s in context)
            if hits >= 1:
                return i

    # Pass 3: Combination of financial content markers on same page
    for i, page in enumerate(pages):
        text_lower = page["text"].lower()
        hits = sum(1 for m in _FINANCIAL_PAGE_CONTENT_MARKERS if m in text_lower)
        strong_hits = sum(1 for m in _FINANCIAL_SECTION_TITLE_MARKERS if m in text_lower)
        if strong_hits >= 2 or (strong_hits >= 1 and hits >= 2):
            return i

    # No financial section found
    return len(pages)


def filter_financial_pages(pages: list[dict]) -> tuple[list[dict], int]:
    """
    Remove financial statement pages from page-structured extraction.

    Detects the start of the actual financial statements section (not TOC entries
    or narrative mentions) and excludes all pages from that point.

    Args:
        pages: List of page dicts with 'page_number' and 'text' keys

    Returns:
        Tuple of (filtered_pages, dropped_count)
    """
    if not pages:
        return pages, 0

    start_idx = _find_financial_section_start(pages)

    if start_idx >= len(pages):
        return pages, 0

    # Drop everything from the financial section start
    dropped = len(pages) - start_idx
    return pages[:start_idx], dropped


def filter_financial_statements(text: str) -> str:
    """
    Legacy wrapper — operates on raw text using page-level detection.
    Extracts pages via PDFPlumberExtractor, filters, and reassembles text.

    Prefer filter_financial_pages() when pages are already extracted.
    """
    if not text:
        return text

    # For standalone raw text, fall back to basic heading detection
    # with TOC guard: require heading to appear after 25% of document
    text_lower = text.lower()

    earliest_pos = len(text)
    for heading in _FINANCIAL_SECTION_TITLE_MARKERS:
        patterns = [
            f"\n{heading}\n",
            f"\n{heading.upper()}\n",
        ]
        for pattern in patterns:
            pos = text_lower.find(pattern)
            pct = pos / len(text) if pos != -1 else 0
            if pos != -1 and pct > 0.20 and pos < earliest_pos:
                earliest_pos = pos

    if earliest_pos < len(text):
        return text[:earliest_pos]

    return text


class ActivityExtractor:
    """Extract activities from council annual reports."""

    # Section headers commonly found in annual reports
    SECTION_PATTERNS = {
        "environment": [
            "environment", "sustainability", "climate", "carbon", "green",
            "conservation", "biodiversity", "ecosystem", "waste", "recycling"
        ],
        "community": [
            "community", "social", "health", "wellbeing", "education",
            "culture", "recreation", "sport", "youth", "seniors",
            "disability", "indigenous", "aboriginal", "diversity"
        ],
        "economic": [
            "economic", "business", "employment", "jobs", "tourism",
            "investment", "development", "growth", "enterprise", "commerce"
        ],
        "infrastructure": [
            "infrastructure", "roads", "buildings", "facilities",
            "transport", "utilities", "maintenance", "construction",
            "engineering", "public works"
        ],
        "planning": [
            "planning", "urban design", "zoning", "land use", "housing",
            "development applications", "building permits", "strategic planning"
        ],
        "governance": [
            "governance", "council", "meeting", "policy", "strategy",
            "performance", "audit", "compliance", "risk", "transparency"
        ],
        "finance": [
            "financial", "budget", "revenue", "expenditure", "audit",
            "accounting", "funding", "grants", "rates", "fees"
        ],
    }

    def __init__(
        self,
        min_activity_length: int = 20,
        max_activity_length: int = 500,
        use_llm_labeling: bool = False,
        llm_model: str = "kimi-k2.5:cloud",
        llm_max_workers: int = 4,
        llm_ollama_hosts: Optional[List[str]] = None,
        use_sentence_reconstruction: bool = True,
        spacy_model: str = "en_core_web_sm",
        nlp=None,
        nofinancial: bool = False,
        use_bert_classifier: bool = False,
        bert_classifier_model: Optional[str] = None,
        min_confidence: float = 0.7,
        require_action_verb: bool = False,
        use_ocr: bool = True,
        ocr_dpi: int = 300,
        ocr_lang: str = "eng",
        ocr_max_pages: int = 150,
    ):
        """
        Initialize activity extractor.

        Args:
            min_activity_length: Minimum words for an activity
            max_activity_length: Maximum words for an activity
            use_llm_labeling: Whether to use LLM for intuitive activity labeling
            llm_model: Ollama model name for LLM labeling
            llm_max_workers: Number of parallel threads for LLM labeling (default: 4)
            llm_ollama_hosts: List of Ollama server URLs for multi-server mode.
                            Example: ["http://localhost:11434", "http://localhost:11435"]
                            If None, uses single server mode.
            use_sentence_reconstruction: Whether to apply smart sentence reconstruction
                                         to handle line breaks in PDF extraction
            spacy_model: spaCy model name for TextProcessor. Options:
                        'en_core_web_sm' (default), 'en_core_web_md', 'en_core_web_lg',
                        'en_core_web_trf' (transformer model, requires spacy-transformers)
            nlp: Optional spaCy language model for advanced sentence reconstruction.
                 If None and use_sentence_reconstruction is True, uses the model from TextProcessor.
            nofinancial: Whether to exclude financial statements section from extraction.
            use_bert_classifier: Whether to use BERT activity classifier for sentence filtering.
            bert_classifier_model: Path to BERT classifier model (Hub repo ID or local path.
                                 default: voyager205/sdg-activity-classifier)
            min_confidence: Minimum classifier confidence to keep an ACTION sentence (default: 0.7)
            require_action_verb: Whether to require at least one action verb (priority or standard)
                                in BERT-classified ACTION sentences (default: False)
        """
        self.pdf_extractor = PDFExtractor()
        self.use_sentence_reconstruction = use_sentence_reconstruction
        self.spacy_model_name = spacy_model
        self.nofinancial = nofinancial

        # OCR fallback (rung 3): built lazily on first image-only PDF, reused
        # thereafter (matches the model-caching pattern). Env overrides let the
        # feature be disabled or tuned without code changes.
        self.use_ocr = use_ocr and os.getenv("OCR_ENABLED", "1") not in ("0", "false", "False")
        self.ocr_dpi = int(os.getenv("OCR_DPI", str(ocr_dpi)))
        self.ocr_lang = os.getenv("OCR_LANG", ocr_lang)
        self.ocr_max_pages = int(os.getenv("OCR_MAX_PAGES", str(ocr_max_pages)))
        self.ocr_min_cpp = int(os.getenv("OCR_MIN_CPP", "50"))
        self._ocr_extractor = None

        # Initialize TextProcessor with specified spaCy model
        self.text_processor = TextProcessor(
            min_activity_length,
            max_activity_length,
            spacy_model=spacy_model
        )

        # Use provided nlp model, or get from text_processor if available
        if use_sentence_reconstruction:
            if nlp is not None:
                self.nlp = nlp
            elif self.text_processor.is_model_loaded():
                self.nlp = self.text_processor.nlp
            else:
                self.nlp = None
        else:
            self.nlp = None

        # Initialize sentence reconstructor if we have an nlp model
        self.sentence_reconstructor = SentenceReconstructor(self.nlp) if use_sentence_reconstruction and self.nlp else None

        self.min_activity_length = min_activity_length
        self.max_activity_length = max_activity_length
        self.use_llm_labeling = use_llm_labeling
        self.llm_max_workers = llm_max_workers
        self.min_confidence = min_confidence
        self.require_action_verb = require_action_verb

        # Initialize BERT activity classifier if enabled
        self.use_bert_classifier = use_bert_classifier
        self.bert_classifier = None
        if use_bert_classifier:
            try:
                self.bert_classifier = ActivityClassifier(model_path=bert_classifier_model)
            except Exception as e:
                print(f"Warning: Failed to load BERT classifier: {e}")
                print("Falling back to spaCy-based extraction.")
                self.use_bert_classifier = False

        if use_llm_labeling:
            self.llm_labeler = LLMActivityLabeler(
                model=llm_model,
                ollama_hosts=llm_ollama_hosts
            )
        else:
            self.llm_labeler = None

    def _get_ocr_extractor(self):
        """Lazily build the OCR extractor once and reuse it."""
        if self._ocr_extractor is None:
            from src.ocr_extractor import OCRExtractor
            self._ocr_extractor = OCRExtractor(
                dpi=self.ocr_dpi, lang=self.ocr_lang, max_pages=self.ocr_max_pages
            )
        return self._ocr_extractor

    @staticmethod
    def _pdf_is_image_heavy(pdf_path: Path) -> bool:
        """True when the PDF averages >=1 embedded image per page — the signal
        that a thin text layer means scanned pages, not a genuinely empty doc."""
        try:
            import fitz
            with fitz.open(pdf_path) as doc:
                pages = len(doc)
                if pages == 0:
                    return False
                imgs = sum(len(doc[i].get_images()) for i in range(pages))
                return imgs / pages >= 1
        except Exception:  # noqa: BLE001
            return False

    def _maybe_ocr(self, pdf_path: Path, raw_text: str, extraction_result: dict):
        """Run OCR when the extracted text is too thin for the page count and the
        PDF looks scanned. Returns possibly-updated (raw_text, extraction_result);
        a no-op when OCR is disabled, the binary is missing, or the gates fail."""
        if not self.use_ocr:
            return raw_text, extraction_result
        pages = extraction_result.get("metadata", {}).get("page_count", 0) or 0
        if pages <= 0:
            return raw_text, extraction_result
        if len(raw_text) / pages >= self.ocr_min_cpp:
            return raw_text, extraction_result
        if not self._pdf_is_image_heavy(pdf_path):
            return raw_text, extraction_result
        ocr = self._get_ocr_extractor()
        if not ocr.available():
            print("  OCR skipped: tesseract not installed")
            return raw_text, extraction_result
        try:
            result = ocr.extract_text_from_pdf(pdf_path)
            if len(result.get("text", "")) > len(raw_text) * 1.5:
                print(f"  image-only ({len(raw_text)}c) → OCR ({len(result['text'])}c)")
                return result["text"], result
        except Exception as e:  # noqa: BLE001
            print(f"  OCR failed: {type(e).__name__}: {e}")
        return raw_text, extraction_result

    def extract_from_pdf(self, pdf_path: Path, progress_callback: callable = None) -> Dict[str, Any]:
        """
        Extract activities from a PDF file.

        Args:
            pdf_path: Path to PDF file
            progress_callback: Optional callable(percent, step_text) for progress reporting

        Returns:
            Dictionary with activities and metadata
        """
        cb = progress_callback or (lambda p, s: None)
        pdf_path = Path(pdf_path)

        # Extract text from PDF
        cb(6.0, "Reading PDF text...")

        if self.nofinancial:
            from src.enhanced_pdf_extractor import PDFPlumberExtractor
            plumber = PDFPlumberExtractor()
            extraction_result = plumber.extract_text_from_pdf(pdf_path)
            pages = extraction_result.get("pages", [])

            # Filter financial pages before assembling text
            filtered_pages, dropped = filter_financial_pages(pages)
            if dropped > 0:
                print(f"  Excluded {dropped} financial statement pages (pages {filtered_pages[-1]['page_number']+1 if filtered_pages else '?'}+ dropped)")

            # Reassemble text from filtered pages
            raw_text = "\n".join(p["text"] for p in filtered_pages)
            # Update extraction result to reflect filtered text
            extraction_result["text"] = raw_text
            extraction_result["pages"] = filtered_pages
            extraction_result["financial_pages_dropped"] = dropped
        else:
            extraction_result = self.pdf_extractor.extract_text_from_pdf(pdf_path)
            raw_text = extraction_result["text"]

            # Fallback: the default extractor (PyMuPDF/fitz) under-reads some
            # PDFs — it can return a small fraction of the real text (e.g.
            # 11k chars where pdfplumber reads 689k). When the result is
            # suspiciously thin (< ~200 chars/page), retry with pdfplumber and
            # keep whichever is richer. Only triggers on thin results, so the
            # common case (fitz works well) is unchanged.
            _pages = extraction_result.get("metadata", {}).get("page_count", 0) or 1
            if len(raw_text) < 200 * _pages:
                try:
                    from src.enhanced_pdf_extractor import PDFPlumberExtractor
                    alt = PDFPlumberExtractor().extract_text_from_pdf(pdf_path)
                    if len(alt.get("text", "")) > len(raw_text) * 1.5:
                        print(f"  fitz thin ({len(raw_text)}c) → pdfplumber ({len(alt['text'])}c)")
                        extraction_result = alt
                        raw_text = alt["text"]
                except Exception as _e:  # noqa: BLE001
                    pass

        # Rung 3: still image-only after fitz + pdfplumber -> OCR. Gated so it
        # only fires on genuinely scanned PDFs: real pages (skips 0-page broken
        # files), thin text (skips text-layer PDFs), image-heavy (confirms scan).
        raw_text, extraction_result = self._maybe_ocr(pdf_path, raw_text, extraction_result)

        # Apply sentence reconstruction if enabled
        if self.use_sentence_reconstruction and self.sentence_reconstructor:
            reconstructed_text = self.sentence_reconstructor.reconstruct(raw_text)
        else:
            reconstructed_text = raw_text

        # Extract activities from the text
        cb(8.0, "Cleaning and segmenting text into sentences...")
        activities = self.extract_from_text(reconstructed_text, progress_callback=progress_callback)

        # Add section context and source tracking if available
        if extraction_result.get("sections"):
            activities = self._add_section_context(
                activities, extraction_result["sections"]
            )

        # Add source reference to each activity for debugging
        for activity in activities:
            activity["source_file"] = str(pdf_path)
            # Store first 200 chars of surrounding context for debugging
            activity_text = activity.get("text", "")
            if activity_text and raw_text:
                # Try to find the activity in the raw text
                idx = raw_text.find(activity_text[:50])  # Use first 50 chars as anchor
                if idx != -1:
                    start = max(0, idx - 100)
                    end = min(len(raw_text), idx + len(activity_text) + 100)
                    activity["source_context"] = raw_text[start:end]
                else:
                    activity["source_context"] = None

        # Note: LLM labeling is already applied in extract_from_text()
        # to avoid double-labeling, we don't repeat it here

        return {
            "source": str(pdf_path),
            "metadata": extraction_result.get("metadata", {}),
            "total_activities": len(activities),
            "activities": activities,
            "llm_labeling_enabled": self.use_llm_labeling,
            "sentence_reconstruction_enabled": self.use_sentence_reconstruction,
            "spacy_model": self.text_processor.get_model_info(),
            "raw_text_sample": raw_text[:2000] if raw_text else None  # First 2000 chars for debugging
        }

    def extract_from_text(self, text: str, progress_callback: callable = None) -> List[Dict[str, Any]]:
        """
        Extract activities from plain text.

        Args:
            text: Input text
            progress_callback: Optional callable(percent, step_text) for progress reporting

        Returns:
            List of activity dictionaries
        """
        cb = progress_callback or (lambda p, s: None)

        # Clean text first
        cleaned_text = self.text_processor.clean_text(text)

        if self.use_bert_classifier and self.bert_classifier:
            # Phase 1: Get candidate sentences (segmentation + cleaning only)
            candidates = self.text_processor.extract_candidate_sentences(cleaned_text)

            # Phase 2: Classify with BERT + quick structure guard
            if candidates:
                cb(12.0, f"Classifying {len(candidates)} sentences with BERT...")
                results = self.bert_classifier.classify_batch(candidates)
                raw_activities = []
                for candidate, result in zip(candidates, results):
                    if result["is_activity"] and result["confidence"] >= self.min_confidence:
                        if self.require_action_verb and not self.text_processor.has_action_verb_quick(candidate):
                            continue
                        raw_activities.append({
                            "text": candidate,
                            "confidence": result["confidence"],
                            "classification_method": "bert",
                        })
            else:
                raw_activities = []

            print(f"  BERT classified {len(candidates)} candidates, {len(raw_activities)} ACTION")
        else:
            # spaCy-based pipeline: segmentation + structure validation
            raw_activities = self.text_processor.extract_activities(
                cleaned_text,
                use_heuristics=True
            )

            print(f"  Extracted {len(raw_activities)} activities via spaCy")

        # Shared post-processing: score relevance, add section type, filter
        filtered_activities = []
        for activity in raw_activities:
            scored = self._score_activity(activity)
            if scored["relevance_score"] >= 0.5:
                filtered_activities.append(scored)

        if len(raw_activities) > 0 and len(filtered_activities) == 0:
            top_scores = sorted(
                [self._score_activity(a)["relevance_score"] for a in raw_activities],
                reverse=True
            )[:5]
            print(f"  Top relevance scores: {top_scores}")

        # Sort by relevance score
        filtered_activities.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Apply LLM labeling if enabled (using parallel processing)
        if self.use_llm_labeling and self.llm_labeler:
            filtered_activities = self.llm_labeler.label_activities_parallel(
                filtered_activities,
                max_workers=self.llm_max_workers
            )

        return filtered_activities

    def _score_activity(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score an activity combining model confidence with text-based relevance.

        Uses shared TextProcessor.score_relevance() for text features.
        Final score = 0.6 * confidence + 0.4 * text_relevance.
        """
        text = activity["text"]
        base_confidence = activity.get("confidence", 0.5)
        text_score = self.text_processor.score_relevance(text)

        activity["relevance_score"] = round(0.6 * base_confidence + 0.4 * text_score, 4)
        activity["word_count"] = len(text.split())
        activity["section_type"] = self.text_processor.detect_section_type(text)

        return activity

    def _add_section_context(
        self,
        activities: List[Dict[str, Any]],
        sections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Add section context to activities."""
        for activity in activities:
            # Find which section this activity belongs to
            # Note: This is a simplified approach
            activity_text = activity["text"].lower()

            # Check section headers for context
            for section in sections:
                section_title = section.get("title", "").lower()
                for section_type, keywords in self.SECTION_PATTERNS.items():
                    if any(kw in section_title for kw in keywords):
                        activity["section_category"] = section_type
                        break

        return activities

    def extract_by_section(
        self,
        text: str,
        target_sections: Optional[List[str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract activities organized by section type.

        Args:
            text: Input text
            target_sections: List of section types to extract (None for all)

        Returns:
            Dictionary mapping section types to activities
        """
        activities = self.extract_from_text(text)

        # Group by section type
        by_section = {}
        for activity in activities:
            section = activity.get("section_type", "general")
            if target_sections and section not in target_sections:
                continue
            if section not in by_section:
                by_section[section] = []
            by_section[section].append(activity)

        return by_section

    def extract_top_activities(
        self,
        text: str,
        n: int = 50,
        min_score: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Extract top N activities by relevance score.

        Args:
            text: Input text
            n: Number of activities to return
            min_score: Minimum relevance score

        Returns:
            List of top activities
        """
        activities = self.extract_from_text(text)
        filtered = [a for a in activities if a["relevance_score"] >= min_score]
        return filtered[:n]

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the spaCy model being used.

        Returns:
            Dictionary with model name, type, accuracy level, and loaded status
        """
        return self.text_processor.get_model_info()

    def get_activity_summary(self, activities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary statistics for extracted activities."""
        if not activities:
            return {
                "total": 0,
                "avg_word_count": 0,
                "avg_relevance": 0,
                "by_section": {}
            }

        total = len(activities)
        avg_word_count = sum(a["word_count"] for a in activities) / total
        avg_relevance = sum(a["relevance_score"] for a in activities) / total

        # Count by section
        by_section = {}
        for activity in activities:
            section = activity.get("section_type", "general")
            by_section[section] = by_section.get(section, 0) + 1

        return {
            "total": total,
            "avg_word_count": round(avg_word_count, 2),
            "avg_relevance": round(avg_relevance, 2),
            "by_section": by_section
        }

    def filter_activities(
        self,
        activities: List[Dict[str, Any]],
        min_words: Optional[int] = None,
        max_words: Optional[int] = None,
        min_score: Optional[float] = None,
        section_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter activities by various criteria.

        Args:
            activities: List of activities
            min_words: Minimum word count
            max_words: Maximum word count
            min_score: Minimum relevance score
            section_type: Filter by section type

        Returns:
            Filtered list of activities
        """
        filtered = activities

        if min_words:
            filtered = [a for a in filtered if a["word_count"] >= min_words]

        if max_words:
            filtered = [a for a in filtered if a["word_count"] <= max_words]

        if min_score:
            filtered = [a for a in filtered if a["relevance_score"] >= min_score]

        if section_type:
            filtered = [a for a in filtered if a.get("section_type") == section_type]

        return filtered

    def cleanup(self):
        """Release MPS resources from BERT classifier."""
        if hasattr(self, 'bert_classifier') and self.bert_classifier is not None:
            self.bert_classifier.cleanup()

    def __del__(self):
        try:
            self.cleanup()
        except Exception:
            pass
