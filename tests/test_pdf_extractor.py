"""Tests for PDF extraction module."""

import pytest
from pathlib import Path

from src.pdf_extractor import PDFExtractor


class TestPDFExtractor:
    """Test cases for PDFExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create PDF extractor fixture."""
        return PDFExtractor()

    def test_init(self, extractor):
        """Test extractor initialization."""
        assert extractor is not None
        assert isinstance(extractor.metadata, dict)

    def test_clean_text(self, extractor):
        """Test text cleaning."""
        dirty_text = "  Hello   world  \n\n\n  Test  \x0c  "
        cleaned = extractor._clean_text(dirty_text)
        assert "  " not in cleaned
        assert "\x0c" not in cleaned
        assert cleaned.strip() == cleaned

    def test_filter_page_content(self, extractor):
        """Test that header/footer content is filtered from pages."""
        # Test that page numbers are filtered
        text_with_page_num = "Some content\n1\nMore content"
        filtered = extractor._filter_page_content(text_with_page_num)
        assert "Some content" in filtered
        assert "More content" in filtered

        # Test "Page X" patterns are filtered
        text_with_page = "Content here\nPage 3\nMore content"
        filtered = extractor._filter_page_content(text_with_page)
        assert "Page 3" not in filtered

        # Test "X of Y" patterns are filtered
        text_with_pagination = "Content\n1 of 5\nMore content"
        filtered = extractor._filter_page_content(text_with_pagination)
        assert "1 of 5" not in filtered

    def test_file_not_found(self, extractor):
        """Test handling of non-existent file."""
        with pytest.raises(FileNotFoundError):
            extractor.extract_text_from_pdf(Path("/nonexistent/path.pdf"))

    def test_identify_sections(self, extractor):
        """Test section identification."""
        text = """
INTRODUCTION

This is the introduction section.

1. GOVERNANCE

This is about governance.

2. COMMUNITY SERVICES

This covers community services.
"""
        sections = extractor._identify_sections(text)
        assert len(sections) > 0
        assert any("GOVERNANCE" in s.get("title", "") for s in sections)

    def test_is_annual_report(self, extractor, tmp_path):
        """Test annual report detection."""
        # Create a test PDF
        import fitz

        pdf_path = tmp_path / "test.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text(
            (50, 50),
            "Annual Report 2023\n\nCouncil activities and achievements"
        )
        doc.save(str(pdf_path))
        doc.close()

        is_report, confidence = extractor.is_annual_report(pdf_path)
        assert isinstance(is_report, bool)
        assert 0 <= confidence <= 1


class TestPDFExtractorEdgeCases:
    """Test edge cases for PDF extraction."""

    @pytest.fixture
    def extractor(self):
        return PDFExtractor()

    def test_empty_text(self, extractor):
        """Test handling of empty text."""
        cleaned = extractor._clean_text("")
        assert cleaned == ""

    def test_unicode_text(self, extractor):
        """Test handling of unicode characters."""
        text = "Test \u200b with \xa0 non-breaking spaces"
        cleaned = extractor._clean_text(text)
        assert "\u200b" not in cleaned
        assert "\xa0" not in cleaned

    def test_multiple_spaces(self, extractor):
        """Test handling of multiple spaces."""
        text = "Word1    Word2     Word3"
        cleaned = extractor._clean_text(text)
        assert "    " not in cleaned

    def test_table_detection(self, extractor):
        """Test table-like content."""
        text = """Col1 | Col2 | Col3
        Val1 | Val2 | Val3"""
        sections = extractor._identify_sections(text)
        # Should handle without error
        assert isinstance(sections, list)
