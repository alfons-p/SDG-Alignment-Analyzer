"""SDG mention finder for scanning PDFs for explicit SDG references.

This module searches for explicit mentions of "SDG" and "sustainable development goal"
in PDF documents, which helps identify whether councils explicitly reference the
SDG framework in their annual reports.
"""

import re
from pathlib import Path
from typing import Dict, Any


def _extract_metadata_from_filename(filename: str) -> Dict[str, str]:
    """Extract metadata from filename (local copy to avoid circular imports)."""
    metadata = {
        'year': '',
        'state': '',
        'council_name': '',
        'urban_rural': '',
        'source': filename
    }

    # Try to extract year (4 digits)
    year_match = re.search(r'20\d{2}', filename)
    if year_match:
        metadata['year'] = year_match.group(0)

    # Try to extract state (common abbreviations)
    state_patterns = ['VIC', 'NSW', 'QLD', 'WA', 'SA', 'TAS', 'ACT', 'NT']
    for state in state_patterns:
        if state in filename.upper():
            metadata['state'] = state
            break

    # Extract urban/rural from filename
    filename_lower = filename.lower()
    if 'urban' in filename_lower:
        metadata['urban_rural'] = 'Urban'
    elif 'rural' in filename_lower:
        metadata['urban_rural'] = 'Rural'

    # Try to extract council name from standardized format
    standardized_match = re.match(
        r'([A-Z]{2,3})_([^_]+)_(Urban|Rural|nan)_([0-9]{4})',
        filename,
        re.IGNORECASE
    )
    if standardized_match:
        metadata['state'] = standardized_match.group(1).upper()
        metadata['council_name'] = standardized_match.group(2).replace('_', ' ')
        metadata['urban_rural'] = standardized_match.group(3)
        metadata['year'] = standardized_match.group(4)

    return metadata


def scan_pdf_for_sdg_mentions(pdf_path: Path, original_filename: str = None) -> Dict[str, Any]:
    """Scan a PDF file for SDG mentions.

    Searches for:
    - "SDG" (uppercase acronym)
    - "sustainable development goal" (full phrase)

    Args:
        pdf_path: Path to the PDF file to scan
        original_filename: Optional original filename (if pdf_path is a temp file)

    Returns:
        Dictionary with scan results including:
        - sdg: 1 if "SDG" found, 0 otherwise
        - sdgtext: The text containing "SDG" if found
        - susdevgoal: 1 if "sustainable development goal" found, 0 otherwise
        - sdgfulltext: The text containing the full phrase if found
        - metadata: Extracted from filename
    """
    try:
        # Import here to avoid circular imports
        import pypdfium2 as pdfium

        # Extract text from PDF
        text = ""
        pdf = pdfium.PdfDocument(pdf_path)
        for page in pdf:
            page_text = page.get_textpage().get_text_bounded()
            if page_text:
                text += page_text + "\n"
        pdf.close()

        # Search for "SDG" (uppercase)
        sdg_match = re.search(r'SDG[^.!?]*[.!?]', text, re.IGNORECASE)
        sdg_found = sdg_match is not None
        sdg_text = sdg_match.group(0) if sdg_match else ""

        # Search for "sustainable development goal" (full phrase)
        susdev_match = re.search(r'sustainable\s+development\s+goal[^.!?]*[.!?]', text, re.IGNORECASE)
        susdev_found = susdev_match is not None
        susdev_text = susdev_match.group(0) if susdev_match else ""

        # Use original filename if provided, otherwise use pdf_path.name
        filename_for_metadata = original_filename if original_filename else pdf_path.name

        # Extract metadata from filename
        metadata = _extract_metadata_from_filename(filename_for_metadata)

        return {
            "sdg": 1 if sdg_found else 0,
            "sdgtext": sdg_text,
            "susdevgoal": 1 if susdev_found else 0,
            "sdgfulltext": susdev_text,
            "council_name": metadata.get("source", filename_for_metadata),
            "state": metadata.get("state", ""),
            "year": metadata.get("year", ""),
            "urban_rural": metadata.get("urban_rural", ""),
        }

    except Exception as e:
        filename_for_error = original_filename if original_filename else pdf_path.name
        return {
            "error": str(e),
            "sdg": 0,
            "susdevgoal": 0,
            "council_name": filename_for_error,
        }


def scan_directory_for_sdg_mentions(input_path: Path, output_dir: Path = None, recursive: bool = True, verbose: bool = False) -> Dict[str, Dict[str, Any]]:
    """Scan PDFs for SDG mentions (supports single file or directory).

    Args:
        input_path: File or directory to scan
        output_dir: Optional directory to save results (if None, returns dict only)
        recursive: If True, scan subdirectories recursively
        verbose: If True, print progress

    Returns:
        Dictionary mapping filename to scan results
    """
    results = {}

    # Handle single file vs directory
    if input_path.is_file():
        pdf_files = [input_path]
    elif input_path.is_dir():
        if recursive:
            pdf_files = list(input_path.rglob("*.pdf"))
        else:
            pdf_files = list(input_path.glob("*.pdf"))
    else:
        if verbose:
            print(f"  Warning: Input path does not exist: {input_path}")
        return results

    if verbose:
        print(f"  Found {len(pdf_files)} PDF files to scan")

    for pdf_path in pdf_files:
        if verbose:
            print(f"  Scanning: {pdf_path.name}")
        result = scan_pdf_for_sdg_mentions(pdf_path)
        results[pdf_path.name] = result

    # Save results if output_dir specified
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        import json
        output_path = output_dir / "sdg_mentions.json"
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        if verbose:
            print(f"  Results saved to: {output_path}")

    return results
