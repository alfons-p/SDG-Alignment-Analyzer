"""Council identity parsed from the V1 filename convention
`{state}_{council}_{region}_{year}` — the API does not carry council identity
natively yet (data-contract Part C #2), so we recover it from the filename.
Mirrors frontend/src/lib/results.ts parseReportName."""

import re
from typing import Optional

_STATES = {"NSW", "VIC", "QLD", "WA", "SA", "TAS", "NT", "ACT"}
_REGION_WORDS = {"urban", "rural", "metro", "regional", "city", "shire"}


def parse_report_identity(filename: str) -> dict[str, Optional[str]]:
    """Return {council_name, state, year} recovered from a report filename."""
    stem = re.sub(r"\.[^.]+$", "", filename)
    stem = re.sub(r"_alignment$", "", stem, flags=re.IGNORECASE)
    parts = [p for p in stem.split("_") if p]

    year: Optional[int] = None
    year_idx = -1
    for i, p in enumerate(parts):
        if re.fullmatch(r"\d{4}", p):
            year = int(p)
            year_idx = i
            break

    state = parts[0].upper() if parts and parts[0].upper() in _STATES else None

    start = 1 if state else 0
    end = year_idx if year_idx >= 0 else len(parts)
    middle = parts[start:end]
    if len(middle) > 1 and middle[-1].lower() in _REGION_WORDS:
        middle = middle[:-1]
    council = " ".join(middle).strip() or stem

    return {"council_name": council, "state": state, "year": year}
