"""Enhanced PDF text extraction with better sentence reconstruction.

Provides multiple extraction backends (PyMuPDF, pdfplumber) and smart
sentence reconstruction to handle line breaks in PDF extraction.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from src.exceptions import PDFExtractionError


@dataclass
class ExtractedPage:
    """Represents extracted text from a single page."""
    page_number: int
    text: str
    word_count: int
    blocks: List[Dict] = None  # Text blocks with position info


class SentenceReconstructor:
    """Reconstruct proper sentences from PDF-extracted text with line breaks."""

    # Words that indicate continuation (not sentence boundaries)
    # NOTE: Articles ('the', 'a', 'an') were REMOVED - they typically end sentences,
    # not indicate mid-sentence continuation. This was causing all lines to be joined.
    CONTINUATION_WORDS = {
        'to', 'of', 'with', 'and', 'in', 'on', 'for', 'at', 'by', 'from',
        'as', 'that', 'which', 'who', 'whom', 'whose', 'where', 'when',
        'this', 'these', 'those', 'some', 'any', 'each',
        'every', 'both', 'few', 'many', 'most', 'other', 'another',
    }

    # Words that start new sentences (sentence starters)
    SENTENCE_STARTERS = {
        'the', 'a', 'an', 'this', 'that', 'these', 'those', 'it', 'he', 'she',
        'they', 'we', 'you', 'i', 'there', 'here', 'now', 'then', 'when',
        'after', 'before', 'while', 'during', 'although', 'because', 'since',
        'however', 'therefore', 'moreover', 'furthermore', 'additionally',
        'first', 'second', 'third', 'finally', 'in', 'on', 'at', 'by',
    }

    # Common abbreviations that shouldn't end sentences
    ABBREVIATIONS = {
        'dr', 'mr', 'mrs', 'ms', 'prof', 'sr', 'jr', 'st', 'ave',
        'blvd', 'rd', 'inc', 'ltd', 'corp', 'llc', 'eg', 'ie',
        'etc', 'vol', 'vols', 'pg', 'pp', 'ed', 'eds', 'no', 'nos',
        'fig', 'figs', 'et', 'al', 'cf', 'vs', 'dept', 'govt', 'council',
    }

    def __init__(self, nlp=None):
        """
        Initialize sentence reconstructor.

        Args:
            nlp: Optional spaCy language model for advanced processing
        """
        self.nlp = nlp

    def reconstruct(self, text: str) -> str:
        """
        Reconstruct sentences from text with arbitrary line breaks.

        This method PRESERVES the original paragraph boundaries (\n\n).
        It joins lines that were broken during PDF extraction WITHIN each
        paragraph, then uses spaCy for sentence boundary refinement.

        Args:
            text: Text with potential line breaks in middle of sentences

        Returns:
            Text with proper paragraph structure preserved, broken lines joined,
            and spaCy sentence boundary refinement
        """
        if not text:
            return ""

        # Split on \n\n to preserve paragraph boundaries
        raw_paragraphs = text.split('\n\n')

        reconstructed_paragraphs = []

        for para in raw_paragraphs:
            if not para.strip():
                reconstructed_paragraphs.append("")
                continue

            # Split into lines and join broken lines
            lines = para.split('\n')
            joined_lines = self._join_mid_sentence_lines(lines)

            # Use spaCy for sentence boundary refinement if available
            if self.nlp:
                joined_lines = self._refine_with_spacy(joined_lines)

            # Rejoin lines into a single paragraph
            reconstructed_paragraphs.append(' '.join(joined_lines))

        return '\n\n'.join(reconstructed_paragraphs)

    def _join_mid_sentence_lines(self, lines: List[str]) -> List[str]:
        """Join lines that are mid-sentence based on heuristics."""
        if not lines:
            return []

        result = []
        current = ""

        for line in lines:
            line = line.strip()
            if not line:
                if current:
                    result.append(current)
                    current = ""
                result.append("")
                continue

            # Check if current line should continue previous
            should_continue = self._should_continue_previous(current, line)

            # Check if current line should start new sentence
            should_start_new = self._should_start_new_sentence(current, line)

            if should_continue and current:
                current = current + " " + line
            elif should_start_new and current:
                result.append(current)
                current = line
            elif current:
                # Default: check if current ends with sentence-ending punctuation
                if self._ends_sentence(current):
                    result.append(current)
                    current = line
                else:
                    current = current + " " + line
            else:
                current = line

        if current:
            result.append(current)

        return result

    def _should_continue_previous(self, previous: str, current: str) -> bool:
        """Check if current line should continue the previous line."""
        if not previous:
            return False

        previous_lower = previous.lower().strip()
        current_lower = current.lower().strip()

        # Previous line ends with continuation word
        prev_words = previous_lower.split()
        if prev_words and prev_words[-1] in self.CONTINUATION_WORDS:
            return True

        # Current line starts with lowercase
        if current and current[0].islower():
            return True

        # Current line starts with continuation word
        curr_words = current_lower.split()
        if curr_words and curr_words[0] in self.CONTINUATION_WORDS:
            # But not if it starts with 'the', 'a', etc. at start of document
            if curr_words[0] not in {'the', 'a', 'an'}:
                return True

        return False

    def _should_start_new_sentence(self, previous: str, current: str) -> bool:
        """Check if current line should start a new sentence."""
        if not previous:
            return True

        # Previous line ends with sentence-ending punctuation
        if self._ends_sentence(previous):
            return True

        # Current line is a title/heading (short, starts with capital, no verb)
        current_words = current.split()
        if (len(current_words) < 10 and
            current[0].isupper() and
            not any(word.lower() in {'and', 'or', 'but', 'the', 'a', 'of', 'in', 'to'}
                    for word in current_words[1:3] if len(current_words) > 1)):
            # Likely a heading
            return True

        return False

    def _ends_sentence(self, text: str) -> bool:
        """Check if text ends a sentence."""
        if not text:
            return False

        text = text.rstrip()

        # Ends with sentence-ending punctuation
        if text[-1] in '.!?':
            # Check it's not an abbreviation
            words = text.split()
            if words:
                last_word = words[-1].rstrip('.!?').lower()
                if last_word in self.ABBREVIATIONS:
                    return False
            return True

        return False

    def _refine_with_spacy(self, lines: List[str]) -> List[str]:
        """Use spaCy to refine sentence boundaries."""
        if not self.nlp:
            return lines

        result = []
        for line in lines:
            if not line.strip():
                result.append(line)
                continue

            # Process with spaCy
            doc = self.nlp(line)

            # Extract proper sentences
            for sent in doc.sents:
                sent_text = sent.text.strip()
                if sent_text:
                    result.append(sent_text)

        return result

    def _form_paragraphs(self, lines: List[str]) -> List[str]:
        """Group lines into paragraphs based on content flow.

        Uses both blank lines AND sentence-ending punctuation followed by
        new topic indicators (capitalized lines) to determine paragraph breaks.
        """
        paragraphs = []
        current_para = []

        for i, line in enumerate(lines):
            if not line.strip():
                # Blank line always ends paragraph
                if current_para:
                    paragraphs.append(' '.join(current_para))
                    current_para = []
            else:
                # Check if this looks like a new paragraph
                # A new paragraph starts with a capital letter after sentence end
                is_new_paragraph = False
                if current_para:
                    prev_line = current_para[-1]
                    # If previous line ends with sentence punctuation and current starts
                    # with capital letter (and has substantial content), it's likely a new topic
                    if (prev_line.rstrip().endswith(('.', '!', '?')) and
                        line and line[0].isupper() and len(line) > 20):
                        is_new_paragraph = True

                if is_new_paragraph:
                    paragraphs.append(' '.join(current_para))
                    current_para = [line]
                else:
                    current_para.append(line)

        if current_para:
            paragraphs.append(' '.join(current_para))

        return paragraphs


class ParagraphReconstructor:
    """Reconstruct proper paragraphs from PDF-extracted text with line breaks.

    Paragraph boundaries are PRESERVED from the original text (double newlines).
    This class only joins lines that were broken during PDF extraction within
    each existing paragraph.

    Primary signal for line joining: lines that end without sentence-ending
    punctuation followed by lines that start with lowercase or continuation words.
    """

    def __init__(self, avg_lines_per_paragraph: int = 8, overlap_lines: int = 2):
        """
        Initialize paragraph reconstructor.

        Args:
            avg_lines_per_paragraph: Expected average lines per paragraph.
                                    Used only for heuristic segmentation when
                                    explicit boundaries are absent.
            overlap_lines: Number of lines to overlap between paragraphs
                          when using heuristic segmentation (not used in
                          normal operation since we preserve boundaries).
        """
        self.avg_lines_per_paragraph = avg_lines_per_paragraph
        self.overlap_lines = overlap_lines

    def reconstruct(self, text: str) -> str:
        """
        Reconstruct paragraphs by preserving existing boundaries and joining
        broken lines within each paragraph.

        Args:
            text: Text with potential line breaks within paragraphs

        Returns:
            Text with proper paragraph structure (line breaks joined within
            paragraphs, \n\n boundaries preserved)
        """
        if not text:
            return ""

        # Split on double newlines to get existing paragraphs
        raw_paragraphs = text.split('\n\n')

        reconstructed_paragraphs = []

        for para in raw_paragraphs:
            # Skip empty paragraphs
            if not para.strip():
                reconstructed_paragraphs.append("")
                continue

            # Join broken lines within this paragraph
            joined_lines = self._join_broken_lines(para)
            reconstructed_paragraphs.append(joined_lines)

        return '\n\n'.join(reconstructed_paragraphs)

    def _join_broken_lines(self, paragraph: str) -> str:
        """
        Join lines that were broken mid-sentence within a paragraph.

        Uses simple heuristics:
        - If line ends with 'to', 'of', 'the', etc. (continuation words), join
        - If next line starts with lowercase, join
        - If line ends without sentence-ending punctuation, join

        Args:
            paragraph: Text of a single paragraph (no \n\n inside)

        Returns:
            Paragraph with joined lines
        """
        lines = paragraph.split('\n')
        if len(lines) <= 1:
            return paragraph

        result_lines = []
        current = lines[0].strip()

        for next_line in lines[1:]:
            next_line = next_line.strip()
            if not next_line:
                continue

            # Check if we should join this line with current
            should_join = self._should_join(current, next_line)

            if should_join:
                # Join with space, preserving ending punctuation intent
                if current.endswith('-'):
                    # Hard hyphen means join without space
                    current = current[:-1] + next_line
                else:
                    current = current + " " + next_line
            else:
                result_lines.append(current)
                current = next_line

        if current:
            result_lines.append(current)

        return ' '.join(result_lines)

    def _should_join(self, previous: str, current: str) -> bool:
        """
        Check if current line should be joined with previous line.

        Args:
            previous: The preceding text
            current: The following text

        Returns:
            True if lines should be joined, False otherwise
        """
        if not previous or not current:
            return False

        prev_stripped = previous.rstrip()
        curr_stripped = current.lstrip()

        # If previous ends with sentence-ending punctuation, don't join
        # (unless it's an abbreviation)
        if prev_stripped.endswith(('.', '!', '?')):
            # Check for abbreviations
            words = prev_stripped.split()
            if words:
                last_word = words[-1].rstrip('.!?').lower()
                abbreviations = {'dr', 'mr', 'mrs', 'ms', 'prof', 'etc', 'eg', 'ie', 'vs'}
                if last_word not in abbreviations:
                    return False

        # If previous ends with a colon, dash, or ellipsis, join
        if prev_stripped.endswith((':', '-', '–', '—')):
            return True

        # If current starts with lowercase, likely continuation
        if curr_stripped and curr_stripped[0].islower():
            return True

        # If current starts with a continuation word, likely continuation
        continuation_starters = {
            'to', 'of', 'with', 'and', 'in', 'on', 'for', 'at', 'by', 'from',
            'the', 'a', 'an', 'that', 'which', 'who', 'whom', 'whose',
        }
        first_word = curr_stripped.lower().split()[0] if curr_stripped.split() else ''
        if first_word in continuation_starters:
            return True

        # If previous ends with a common connector word, join
        connector_words = {
            'to', 'of', 'with', 'and', 'in', 'on', 'for', 'at', 'by', 'from',
            'as', 'that', 'which', 'who', 'where', 'when',
        }
        prev_words = prev_stripped.lower().split()
        if prev_words and prev_words[-1] in connector_words:
            return True

        # Default: don't join (likely a new sentence)
        return False


class PDFPlumberExtractor:
    """Extract text from PDFs using pdfplumber for better layout preservation."""

    def __init__(self, use_sentence_reconstruction: bool = True, nlp=None):
        """
        Initialize pdfplumber extractor.

        Args:
            use_sentence_reconstruction: Whether to apply sentence reconstruction
            nlp: Optional spaCy model for sentence boundary detection
        """
        self.use_sentence_reconstruction = use_sentence_reconstruction
        self.sentence_reconstructor = SentenceReconstructor(nlp) if nlp else None
        self.nlp = nlp

    def extract_text_from_pdf(
        self,
        pdf_path: Path,
        preserve_layout: bool = True,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Extract text from a PDF file using pdfplumber.

        Args:
            pdf_path: Path to the PDF file
            preserve_layout: Whether to preserve document layout
            include_metadata: Whether to extract PDF metadata

        Returns:
            Dictionary containing:
                - text: Full extracted text
                - pages: List of page texts with page numbers
                - metadata: PDF metadata (if requested)
                - sections: Identified sections (if possible)
        """
        import pdfplumber

        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        result = {
            "source": str(pdf_path),
            "text": "",
            "pages": [],
            "metadata": {},
            "sections": [],
            "extraction_method": "pdfplumber"
        }

        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Extract metadata
                if include_metadata:
                    result["metadata"] = self._extract_metadata(pdf)

                # Extract text from each page
                full_text_parts = []
                for page_num, page in enumerate(pdf.pages, start=1):
                    page_text = self._extract_page_text(page, preserve_layout)
                    if page_text.strip():
                        # Skip TOC pages
                        if self._is_toc_page(page_text):
                            continue

                        # Filter structural content
                        page_text = self._filter_page_content(page_text)

                        if page_text.strip():
                            result["pages"].append({
                                "page_number": page_num,
                                "text": page_text,
                                "word_count": len(page_text.split())
                            })
                            full_text_parts.append(page_text)

                raw_text = "\n\n".join(full_text_parts)

                # Apply sentence reconstruction if enabled
                if self.use_sentence_reconstruction and self.sentence_reconstructor:
                    result["text"] = self.sentence_reconstructor.reconstruct(raw_text)
                else:
                    result["text"] = raw_text

                # Try to identify sections
                result["sections"] = self._identify_sections(result["text"])

        except Exception as e:
            raise PDFExtractionError(f"Error extracting text from {pdf_path}: {e}") from e

        return result

    def _extract_metadata(self, pdf) -> Dict[str, Any]:
        """Extract metadata from PDF document."""
        metadata = pdf.metadata or {}
        return {
            "title": metadata.get("Title", ""),
            "author": metadata.get("Author", ""),
            "subject": metadata.get("Subject", ""),
            "creator": metadata.get("Creator", ""),
            "producer": metadata.get("Producer", ""),
            "creation_date": metadata.get("CreationDate", ""),
            "modification_date": metadata.get("ModDate", ""),
            "page_count": len(pdf.pages),
        }

    def _extract_page_text(self, page, preserve_layout: bool) -> str:
        """Extract text from a single page using pdfplumber."""
        if preserve_layout:
            # Use layout-preserving extraction
            text = page.extract_text(layout=True)
        else:
            text = page.extract_text()

        if not text:
            return ""

        # Clean up common artifacts
        text = self._clean_text(text)
        return text

    def _clean_text(self, text: str) -> str:
        """Clean extracted text by removing common artifacts."""
        # Replace multiple spaces with single space (but preserve newlines)
        text = re.sub(r'[ \t]+', ' ', text)
        # Replace multiple newlines with double newline
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        # Remove non-breaking spaces
        text = text.replace('\xa0', ' ')
        # Remove zero-width spaces
        text = text.replace('\u200b', '')
        # Remove form feed characters
        text = text.replace('\x0c', '')
        return text.strip()

    def _is_toc_page(self, text: str) -> bool:
        """Check if a page appears to be a table of contents page."""
        text_lower = text.lower()

        # Check for explicit TOC markers
        toc_headers = ['contents', 'table of contents', 'index']
        first_200_chars = text_lower[:200]

        for header in toc_headers:
            if first_200_chars.startswith(header) or first_200_chars.strip().startswith(header):
                lines = text.split('\n')
                toc_entry_count = sum(1 for line in lines[:15]
                                     if re.search(r'.+\d+\s*$', line.strip()) and len(line.strip()) > 10)
                if toc_entry_count >= 3:
                    return True

        # Check for activity tables (should NOT be treated as TOC)
        activity_table_markers = ['delivery program action', 'operational plan activity', 'code']
        if any(marker in text_lower for marker in activity_table_markers):
            return False

        return False

    def _filter_page_content(self, text: str) -> str:
        """Filter out structural content from a page."""
        lines = text.split('\n')
        filtered_lines = []

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # Skip TOC-style lines
            if re.search(r'\w+.*?\d+\s*$', line_stripped) and len(line_stripped) < 100:
                words_before_number = re.sub(r'\d+\s*$', '', line_stripped).strip()
                if words_before_number and len(words_before_number.split()) < 10:
                    continue

            # Skip standalone page numbers
            if re.match(r'^\d+$', line_stripped):
                continue

            if re.match(r'^page\s+\d+$', line_stripped, re.IGNORECASE):
                continue

            filtered_lines.append(line)

        return '\n'.join(filtered_lines)

    def _identify_sections(self, text: str) -> List[Dict[str, Any]]:
        """Attempt to identify document sections using heading patterns."""
        sections = []

        section_patterns = [
            r'^\s*(?:CHAPTER\s+)?(\d+[.:]?)\s+([A-Z][A-Z\s\-]+)',
            r'^\s*([A-Z][A-Z\s\-]{3,50})\s*$',
            r'^\s*(?:Section\s+)?(\d+)\.?\s+([A-Z][A-Za-z\s\-]+)',
            r'^\s*(About\s+This\s+Report|Annual\s+Report|Chief\s+Executive|Mayoral|Director|Financial|Performance|Governance|Community|Sustainability|Environment|Planning|Infrastructure|Corporate)',
        ]

        lines = text.split('\n')
        current_section = {"title": "Introduction", "content": [], "start_line": 0}

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            is_heading = False
            for pattern in section_patterns:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    is_heading = True
                    break

            if not is_heading and line_stripped:
                if (line_stripped.isupper() and
                    10 < len(line_stripped) < 80 and
                    '|' not in line_stripped and
                    not line_stripped.replace('.', '').replace(',', '').isdigit()):
                    is_heading = True

            if is_heading:
                if current_section["content"]:
                    current_section["content"] = '\n'.join(current_section["content"])
                    current_section["end_line"] = i
                    sections.append(current_section)

                current_section = {
                    "title": line_stripped,
                    "content": [],
                    "start_line": i
                }
            else:
                current_section["content"].append(line)

        if current_section["content"]:
            current_section["content"] = '\n'.join(current_section["content"])
            sections.append(current_section)

        return sections


class HybridPDFExtractor:
    """
    Extract text using both PyMuPDF and pdfplumber, selecting the best result.

    This class attempts extraction with both methods and uses heuristics
    to determine which produces better results.
    """

    def __init__(self, prefer_plumber: bool = True, nlp=None):
        """
        Initialize hybrid extractor.

        Args:
            prefer_plumber: Whether to prefer pdfplumber results
            nlp: Optional spaCy model for sentence reconstruction
        """
        self.prefer_plumber = prefer_plumber
        self.plumber_extractor = PDFPlumberExtractor(use_sentence_reconstruction=True, nlp=nlp)

        # Import PyMuPDF extractor
        from src.pdf_extractor import PDFExtractor
        self.pymupdf_extractor = PDFExtractor()

    def extract_text_from_pdf(
        self,
        pdf_path: Path,
        preserve_layout: bool = True,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Extract text using the best available method.

        Args:
            pdf_path: Path to the PDF file
            preserve_layout: Whether to preserve document layout
            include_metadata: Whether to extract PDF metadata

        Returns:
            Dictionary with extracted text and metadata
        """
        results = {}
        errors = []

        # Try pdfplumber first (if preferred)
        if self.prefer_plumber:
            try:
                results['pdfplumber'] = self.plumber_extractor.extract_text_from_pdf(
                    pdf_path, preserve_layout, include_metadata
                )
            except Exception as e:
                errors.append(f"pdfplumber error: {e}")

        # Try PyMuPDF
        try:
            results['pymupdf'] = self.pymupdf_extractor.extract_text_from_pdf(
                pdf_path, preserve_layout, include_metadata
            )
        except Exception as e:
            errors.append(f"PyMuPDF error: {e}")

        # If pdfplumber was not preferred, try it now
        if not self.prefer_plumber and 'pdfplumber' not in results:
            try:
                results['pdfplumber'] = self.plumber_extractor.extract_text_from_pdf(
                    pdf_path, preserve_layout, include_metadata
                )
            except Exception as e:
                errors.append(f"pdfplumber error: {e}")

        # Select the best result
        if 'pdfplumber' in results and self.prefer_plumber:
            result = results['pdfplumber']
            result['extraction_method'] = 'pdfplumber'
        elif 'pymupdf' in results:
            result = results['pymupdf']
            result['extraction_method'] = 'pymupdf'
        elif 'pdfplumber' in results:
            result = results['pdfplumber']
            result['extraction_method'] = 'pdfplumber'
        else:
            raise PDFExtractionError(f"All extraction methods failed: {'; '.join(errors)}")

        return result

    def compare_extractions(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Compare extraction results from both methods.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary with comparison results
        """
        results = {}

        try:
            results['pdfplumber'] = self.plumber_extractor.extract_text_from_pdf(pdf_path)
        except Exception as e:
            results['pdfplumber'] = {"error": str(e)}

        try:
            results['pymupdf'] = self.pymupdf_extractor.extract_text_from_pdf(pdf_path)
        except Exception as e:
            results['pymupdf'] = {"error": str(e)}

        # Compare word counts
        comparison = {
            "pdfplumber_words": len(results.get('pdfplumber', {}).get('text', '').split()),
            "pymupdf_words": len(results.get('pymupdf', {}).get('text', '').split()),
            "pdfplumber_pages": len(results.get('pdfplumber', {}).get('pages', [])),
            "pymupdf_pages": len(results.get('pymupdf', {}).get('pages', [])),
        }

        return {
            "results": results,
            "comparison": comparison
        }