"""Activity Extraction Module.

Identifies and extracts meaningful activities from council reports.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union

from src.pdf_extractor import PDFExtractor
from src.text_processor import TextProcessor
from src.llm_activity_labeler import LLMActivityLabeler
from src.enhanced_pdf_extractor import PDFPlumberExtractor, SentenceReconstructor


# Financial statement section headings to detect and exclude
FINANCIAL_STATEMENT_HEADINGS = [
    "financial statements",
    "financial statement",
    "statement of financial position",
    "statement of comprehensive income",
    "statement of financial performance",
    "statement of cash flows",
    "statement of changes in equity",
    "notes to the financial statements",
    "notes to financial statements",
    "notes to and forming part of the financial statements",
    "financial report",
    "certified financial statements",
    "audited financial statements",
    "general purpose financial statements",
    "special purpose financial statements",
]


def filter_financial_statements(text: str) -> str:
    """
    Remove financial statements section from text.

    Detects financial statement headings and removes all text after that point.
    This is useful for focusing analysis on narrative sections rather than
    standardized financial reporting.

    Args:
        text: The full text extracted from a PDF

    Returns:
        Text with financial statements section removed
    """
    if not text:
        return text

    text_lower = text.lower()

    # Find the earliest occurrence of any financial statement heading
    earliest_pos = len(text)
    found_heading = None

    for heading in FINANCIAL_STATEMENT_HEADINGS:
        # Look for heading with various formatting patterns
        patterns = [
            f"\n{heading}\n",           # Heading on its own line
            f"\n{heading}:",            # Heading with colon
            f"\n{heading} ",            # Heading followed by space
            f"\n{heading.upper()}\n",   # Uppercase version
            f"\n{heading.upper()}:",    # Uppercase with colon
            f"\n{heading.upper()} ",    # Uppercase with space
        ]

        for pattern in patterns:
            pos = text_lower.find(pattern)
            if pos != -1 and pos < earliest_pos:
                earliest_pos = pos
                found_heading = heading

    if earliest_pos < len(text):
        # Found financial statement section - remove it
        filtered_text = text[:earliest_pos]
        return filtered_text

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

    # Pre-compiled regex patterns for scoring (cached at class level)
    _OUTCOME_PATTERNS = [
        re.compile(r'\d+\s*(?:percent|%|people|households|residents|jobs|tonnes|units)', re.IGNORECASE),
        re.compile(r'\$[\d,]+(?:\.\d{2})?', re.IGNORECASE),
        re.compile(r'(?:increased|decreased|reduced|improved)\s+by\s+\d+', re.IGNORECASE),
    ]

    # SDG-relevant keywords (cached at class level)
    _SDG_RELEVANT_TERMS = [
        "sustainable", "climate", "environment", "community", "health",
        "education", "infrastructure", "economic", "social", "partnership",
        "innovation", "biodiversity", "renewable", "waste", "recycling",
        "wellbeing", "inclusion", "diversity", "accessibility", "conservation"
    ]

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
        nofinancial: bool = False
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
        """
        self.pdf_extractor = PDFExtractor()
        self.use_sentence_reconstruction = use_sentence_reconstruction
        self.spacy_model_name = spacy_model
        self.nofinancial = nofinancial

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
        if use_llm_labeling:
            self.llm_labeler = LLMActivityLabeler(
                model=llm_model,
                ollama_hosts=llm_ollama_hosts
            )
        else:
            self.llm_labeler = None

    def extract_from_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract activities from a PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with activities and metadata
        """
        # Extract text from PDF
        extraction_result = self.pdf_extractor.extract_text_from_pdf(pdf_path)

        # Store raw text for debugging reference
        raw_text = extraction_result["text"]

        # Filter out financial statements if requested
        if self.nofinancial:
            raw_text = filter_financial_statements(raw_text)

        # Apply sentence reconstruction if enabled
        if self.use_sentence_reconstruction and self.sentence_reconstructor:
            reconstructed_text = self.sentence_reconstructor.reconstruct(raw_text)
        else:
            reconstructed_text = raw_text

        # Extract activities from the text
        activities = self.extract_from_text(reconstructed_text)

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

    def extract_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract activities from plain text.

        Args:
            text: Input text

        Returns:
            List of activity dictionaries
        """
        # Clean text first
        cleaned_text = self.text_processor.clean_text(text)

        # Extract activities using text processor
        activities = self.text_processor.extract_activities(
            cleaned_text,
            use_heuristics=True
        )

        # Filter and score activities with stricter criteria
        filtered_activities = []
        for activity in activities:
            scored_activity = self._score_activity(activity)
            # Stricter threshold: only activities with confidence > 0.6
            if scored_activity["relevance_score"] > 0.6:
                filtered_activities.append(scored_activity)

        # Debug: show activity extraction stats
        print(f"  Extracted {len(activities)} activities, {len(filtered_activities)} passed relevance threshold (>0.6)")
        if len(activities) > 0 and len(filtered_activities) == 0:
            # Show top relevance scores for debugging
            top_scores = sorted([a.get("relevance_score", 0) for a in activities], reverse=True)[:5]
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
        Score an activity based on strict validation criteria.

        Args:
            activity: Activity dictionary from text processor

        Returns:
            Activity with added relevance score
        """
        text = activity["text"]
        base_confidence = activity.get("confidence", 0.5)

        score = base_confidence

        # Bonus for SDG-relevant keywords (use cached class attribute)
        text_lower = text.lower()
        sdg_matches = sum(1 for term in self._SDG_RELEVANT_TERMS if term in text_lower)
        score += min(sdg_matches * 0.05, 0.15)  # Reduced from 0.1/0.3 to be stricter

        # Bonus for quantitative outcomes (use pre-compiled patterns)
        for pattern in self._OUTCOME_PATTERNS:
            if pattern.search(text):
                score += 0.05  # Reduced from 0.1
                break

        # Bonus for specificity indicators
        specificity_markers = [
            'for', 'in', 'at', 'with', 'to',
            'community', 'residents', 'people', 'families',
            'area', 'region', 'town', 'city'
        ]
        specificity_count = sum(1 for marker in specificity_markers if marker in text_lower)
        score += min(specificity_count * 0.02, 0.1)

        # Penalty for too many numbers (likely a table)
        words = text.split()
        if words:
            number_ratio = sum(1 for w in words if any(c.isdigit() for c in w)) / len(words)
            if number_ratio > 0.3:
                score *= 0.5

        # Detect section type
        section_type = self.text_processor.detect_section_type(text)

        # Store section type and relevance score
        activity["section_type"] = section_type
        activity["relevance_score"] = min(score, 1.0)

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
