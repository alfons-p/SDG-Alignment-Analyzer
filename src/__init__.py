"""SDG Alignment Analyzer package.

A Python-based data analytics project that uses Natural Language Processing (NLP)
to assess how well city council annual reports align with the 17 UN Sustainable
Development Goals (SDGs).
"""

__version__ = "0.1.0"
__author__ = "SDG Analyzer Team"

from src.config import SDG_DEFINITIONS, Config
from src.pdf_extractor import PDFExtractor
from src.text_processor import TextProcessor
from src.sdg_reference import SDGReference
from src.activity_extractor import ActivityExtractor
from src.alignment_engine import AlignmentEngine
from src.reports import Reporter
from src.embedding_cache import EmbeddingCache

__all__ = [
    "SDG_DEFINITIONS",
    "Config",
    "PDFExtractor",
    "TextProcessor",
    "SDGReference",
    "ActivityExtractor",
    "AlignmentEngine",
    "Reporter",
    "EmbeddingCache",
]
