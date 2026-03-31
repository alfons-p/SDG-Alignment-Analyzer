"""PDF text extraction module using PyMuPDF.

Provides reliable PDF text extraction with layout preservation.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import fitz  # PyMuPDF

from src.exceptions import PDFExtractionError


class PDFExtractor:
    """Extract text and metadata from PDF files using PyMuPDF."""

    def __init__(self):
        """Initialize the PDF extractor."""
        self.metadata: Dict[str, Any] = {}

    def extract_text_from_pdf(
        self,
        pdf_path: Path,
        preserve_layout: bool = True,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Extract text from a PDF file with page numbers and metadata.

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
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        result = {
            "source": str(pdf_path),
            "text": "",
            "pages": [],
            "metadata": {},
            "sections": []
        }

        try:
            with fitz.open(pdf_path) as doc:
                # Extract metadata
                if include_metadata:
                    result["metadata"] = self._extract_metadata(doc)

                # Extract text from each page
                full_text_parts = []
                for page_num, page in enumerate(doc, start=1):
                    page_text = self._extract_page_text(page, preserve_layout)
                    if page_text.strip():
                        # Skip TOC pages
                        if self._is_toc_page(page_text):
                            continue

                        # Filter structural content
                        page_text = self._filter_page_content(page_text)

                        if page_text.strip():  # Check again after filtering
                            result["pages"].append({
                                "page_number": page_num,
                                "text": page_text,
                                "word_count": len(page_text.split())
                            })
                            full_text_parts.append(page_text)

                result["text"] = "\n\n".join(full_text_parts)

                # Try to identify sections
                result["sections"] = self._identify_sections(result["text"])

        except Exception as e:
            raise PDFExtractionError(f"Error extracting text from {pdf_path}: {e}") from e

        return result

    def _extract_metadata(self, doc: fitz.Document) -> Dict[str, Any]:
        """Extract metadata from PDF document."""
        metadata = doc.metadata
        return {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "creator": metadata.get("creator", ""),
            "producer": metadata.get("producer", ""),
            "creation_date": metadata.get("creationDate", ""),
            "modification_date": metadata.get("modDate", ""),
            "page_count": len(doc),
            "file_size": doc.name if hasattr(doc, 'name') else "unknown"
        }

    def _extract_page_text(self, page: fitz.Page, preserve_layout: bool) -> str:
        """Extract text from a single page."""
        if preserve_layout:
            # Use block extraction for better layout handling
            # This helps with multi-column layouts
            blocks = page.get_text("blocks")
            # Sort blocks by vertical position, then horizontal
            blocks.sort(key=lambda b: (b[1], b[0]))  # Sort by y, then x
            text_parts = []
            for block in blocks:
                block_text = block[4].strip()
                if block_text:
                    text_parts.append(block_text)
            text = "\n".join(text_parts)
        else:
            # Simple text extraction
            text = page.get_text()

        # Clean up common PDF extraction artifacts
        text = self._clean_text(text)
        return text

    def _is_toc_page(self, text: str) -> bool:
        """
        Check if a page appears to be a table of contents page.

        Returns:
            True if the page is likely a TOC page
        """
        text_lower = text.lower()

        # Check for explicit TOC markers
        toc_headers = ['contents', 'table of contents', 'index']
        if any(header in text_lower[:500] for header in toc_headers):
            return True

        # Check for TOC pattern: multiple lines with text followed by page numbers
        lines = text.split('\n')
        toc_line_count = 0
        total_lines = 0

        for line in lines:
            line_stripped = line.strip()
            if len(line_stripped) > 5:  # Skip very short lines
                total_lines += 1
                # Pattern: text followed by number at end (page number)
                if re.search(r'\w+.*?\d+\s*$', line_stripped):
                    toc_line_count += 1

        # If more than 40% of lines look like TOC entries
        if total_lines > 5 and toc_line_count / total_lines > 0.4:
            return True

        # Check for high density of page number patterns
        page_number_patterns = re.findall(r'\b\d{1,3}\s*$', text, re.MULTILINE)
        if len(page_number_patterns) >= 5:
            return True

        return False

    def _filter_page_content(self, text: str) -> str:
        """
        Filter out structural content from a page.

        Removes headers, footers, and other non-content elements.
        """
        lines = text.split('\n')
        filtered_lines = []

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # Skip TOC-style lines (text ending with page number)
            if re.search(r'\w+.*?\d+\s*$', line_stripped) and len(line_stripped) < 100:
                # Check if it looks like a TOC entry
                words_before_number = re.sub(r'\d+\s*$', '', line_stripped).strip()
                if words_before_number and len(words_before_number.split()) < 10:
                    continue

            # Skip header with embedded numbers like "Financial summary 2022-2023 42"
            if re.search(r'\w+.*?20\d{2}[-–]?\d{0,2}\s+\d+\s*$', line_stripped):
                continue

            # Skip standalone page numbers
            if re.match(r'^\d+$', line_stripped):
                continue

            # Skip "Page X" patterns
            if re.match(r'^page\s+\d+$', line_stripped, re.IGNORECASE):
                continue

            # Skip "X of Y" patterns
            if re.match(r'^\d+\s+of\s+\d+$', line_stripped, re.IGNORECASE):
                continue

            filtered_lines.append(line)

        return '\n'.join(filtered_lines)

    def _clean_text(self, text: str) -> str:
        """Clean extracted text by removing common artifacts."""
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        # Replace multiple newlines with double newline (paragraph break)
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        # Remove non-breaking spaces
        text = text.replace('\xa0', ' ')
        # Remove zero-width spaces
        text = text.replace('\u200b', '')
        # Remove form feed characters
        text = text.replace('\x0c', '')
        # Strip leading/trailing whitespace
        return text.strip()

    def _identify_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        Attempt to identify document sections using heading patterns.

        Looks for common section headers in annual reports.
        """
        sections = []

        # Common section patterns in annual reports
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

            # Check if this line looks like a heading
            is_heading = False
            for pattern in section_patterns:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    is_heading = True
                    break

            # Additional heuristics for headings
            if not is_heading and line_stripped:
                # All caps, reasonable length, not a table row
                if (line_stripped.isupper() and
                    10 < len(line_stripped) < 80 and
                    '|' not in line_stripped and
                    not line_stripped.replace('.', '').replace(',', '').isdigit()):
                    is_heading = True

            if is_heading:
                # Save previous section
                if current_section["content"]:
                    current_section["content"] = '\n'.join(current_section["content"])
                    current_section["end_line"] = i
                    sections.append(current_section)

                # Start new section
                current_section = {
                    "title": line_stripped,
                    "content": [],
                    "start_line": i
                }
            else:
                current_section["content"].append(line)

        # Save last section
        if current_section["content"]:
            current_section["content"] = '\n'.join(current_section["content"])
            sections.append(current_section)

        return sections

    def extract_tables(self, pdf_path: Path, page_number: Optional[int] = None) -> List[Dict]:
        """
        Extract tables from PDF.

        Args:
            pdf_path: Path to the PDF file
            page_number: Specific page to extract (None for all pages)

        Returns:
            List of tables with their data
        """
        pdf_path = Path(pdf_path)
        tables = []

        try:
            with fitz.open(pdf_path) as doc:
                pages_to_process = [page_number - 1] if page_number else range(len(doc))

                for idx in pages_to_process:
                    if idx < 0 or idx >= len(doc):
                        continue

                    page = doc[idx]
                    # Get tables using PyMuPDF's table finder
                    tabs = page.find_tables()

                    for tab in tabs.tables:
                        tables.append({
                            "page": idx + 1,
                            "data": tab.extract()
                        })

        except Exception as e:
            print(f"Error extracting tables from {pdf_path}: {e}")

        return tables

    def get_page_count(self, pdf_path: Path) -> int:
        """Get the number of pages in a PDF."""
        try:
            with fitz.open(pdf_path) as doc:
                return len(doc)
        except Exception as e:
            raise PDFExtractionError(f"Error reading PDF {pdf_path}: {e}") from e

    def is_annual_report(self, pdf_path: Path) -> Tuple[bool, float]:
        """
        Check if a PDF appears to be an annual report.

        Returns:
            Tuple of (is_report, confidence_score)
        """
        try:
            result = self.extract_text_from_pdf(pdf_path, include_metadata=True)
            text_lower = result["text"].lower()

            # Keywords that suggest an annual report
            report_keywords = [
                "annual report", "annual review", "year in review",
                "council", "local government", "municipal",
                "performance", "achievements", "activities",
                "financial statements", "governance", "mayor",
                "chief executive", "director", "infrastructure",
                "community services", "strategic plan"
            ]

            # Count keyword matches
            matches = sum(1 for kw in report_keywords if kw in text_lower)
            confidence = matches / len(report_keywords)

            # Additional checks
            if result["metadata"].get("title", "").lower().count("annual") > 0:
                confidence += 0.2

            # Check for year patterns (2022-23, 2023, etc.)
            if re.search(r'20\d{2}\s*[-–]\s*(?:20)?\d{2}', result["text"]):
                confidence += 0.1

            return confidence > 0.3, min(confidence, 1.0)

        except Exception as e:
            return False, 0.0
