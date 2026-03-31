"""PDF activity extraction and SDG mention scanning for the dashboard."""

import tempfile
import traceback
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import streamlit as st

from src.dashboard.utils import get_extractor, extract_metadata_from_filename
from src.exceptions import SDGAnalyzerError
from src.sdg_mention_finder import scan_pdf_for_sdg_mentions

logger = logging.getLogger(__name__)


@st.cache_data(show_spinner=False)
def extract_activities_from_pdf_cached(
    uploaded_file_bytes: bytes,
    filename: str,
    min_words: int,
    max_words: int,
    top_activities: Optional[int]
) -> Dict[str, Any]:
    """Extract activities from PDF - cached to avoid re-extraction when only threshold changes.

    This is cached based on file content (bytes) and extraction parameters.

    Args:
        uploaded_file_bytes: Raw bytes of the uploaded PDF file
        filename: Original filename for metadata extraction
        min_words: Minimum word count for activities
        max_words: Maximum word count for activities
        top_activities: Limit to top N activities (None for all)

    Returns:
        Dictionary with extracted activities and metadata
    """
    # Save uploaded file temporarily
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file_bytes)
            tmp_path = tmp_file.name

        logger.debug(f"Processing PDF: {filename} ({len(uploaded_file_bytes)} bytes)")

        # Extract metadata from filename (using the ORIGINAL filename)
        metadata = extract_metadata_from_filename(filename)

        # Extract activities with word count filtering
        extractor = get_extractor(min_words=min_words, max_words=max_words)
        activities_data = extractor.extract_from_pdf(tmp_path)

        # OVERRIDE the source with the original filename (not the temp path)
        activities_data['source'] = filename

        # Add/override metadata
        activities_data['metadata']['year'] = metadata['year']
        activities_data['metadata']['state'] = metadata['state']
        activities_data['metadata']['urban_rural'] = metadata['urban_rural']
        activities_data['metadata']['source'] = filename

        # Filter to top activities if specified
        if top_activities and top_activities > 0:
            activities_data['activities'] = activities_data['activities'][:top_activities]

        logger.debug(f"Extracted {len(activities_data.get('activities', []))} activities from {filename}")

        return activities_data

    except SDGAnalyzerError as e:
        logger.error(f"Extraction failed for {filename}: {e}", exc_info=True)
        return {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()}
    except Exception as e:
        logger.error(f"Unexpected extraction error for {filename}: {e}", exc_info=True)
        return {"error": str(e), "error_type": "UnexpectedError", "traceback": traceback.format_exc()}
    finally:
        # Clean up temp file
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
                logger.debug(f"Cleaned up temp file: {tmp_path}")
            except OSError as e:
                logger.warning(f"Failed to clean up temp file {tmp_path}: {e}")


@st.cache_data(show_spinner=False)
def scan_sdg_mentions_cached(uploaded_file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Scan PDF for SDG mentions - cached to avoid re-scanning.

    Args:
        uploaded_file_bytes: Raw bytes of the uploaded PDF file
        filename: Original filename for metadata extraction

    Returns:
        Dictionary with SDG mention scan results
    """
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file_bytes)
            tmp_path = tmp_file.name

        logger.debug(f"Scanning PDF for SDG mentions: {filename}")

        # Scan for SDG mentions
        result = scan_pdf_for_sdg_mentions(Path(tmp_path))
        result['source'] = filename

        logger.debug(f"SDG mention scan complete for {filename}")

        return result

    except Exception as e:
        logger.error(f"SDG mention scan failed for {filename}: {e}", exc_info=True)
        return {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()}
    finally:
        # Clean up temp file
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
                logger.debug(f"Cleaned up temp file: {tmp_path}")
            except OSError as e:
                logger.warning(f"Failed to clean up temp file {tmp_path}: {e}")