"""Custom exceptions for SDG Alignment Analyzer."""


class SDGAnalyzerError(Exception):
    """Base exception for all SDG Analyzer errors."""
    pass


class PDFExtractionError(SDGAnalyzerError):
    """Raised when PDF extraction fails."""
    pass


class ModelLoadError(SDGAnalyzerError):
    """Raised when a model fails to load."""
    pass


class EmbeddingError(SDGAnalyzerError):
    """Raised when embedding generation fails."""
    pass


class ActivityExtractionError(SDGAnalyzerError):
    """Raised when activity extraction fails."""
    pass


class AlignmentError(SDGAnalyzerError):
    """Raised when SDG alignment fails."""
    pass


class ValidationError(SDGAnalyzerError):
    """Raised when input validation fails."""
    pass


class DependencyError(SDGAnalyzerError):
    """Raised when an optional dependency is missing."""
    pass