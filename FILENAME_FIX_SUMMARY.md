# Fix Summary: Council-Level Alignment Files Naming Issue

## Problem
Council annual reports with parsing issues (e.g., missing council name or "nan" placeholder) were all being saved to the same file: `{STATE}_Unknown_{TYPE}_{YEAR}_alignment.csv`, losing the true council identity.

### Example:
- **Input**: `NSW_Ballina_Urban_2025.pdf`
- **Old Output**: `NSW_Unknown__2025_alignment.csv` (all councils with parsing issues merged!)
- **New Output**: `NSW_Ballina_Urban_2025_alignment.csv` ✓

## Root Cause
The filename generation logic in `src/reports/base.py` relied on metadata fields (`council_name`, `urban_rural`) that were often:
1. Missing (empty string)
2. Placeholder values ("nan")
3. Not properly extracted from the PDF filename

When these metadata fields were missing/invalid, the code used "Unknown" as a fallback, causing all affected councils to be merged into the same file.

## Solution
Modified three methods in `src/reports/base.py`:
1. `generate_csv_report()`
2. `generate_json_report()`
3. `generate_summary_report()`

### Key Changes:
1. **Created helper method** `_extract_filename_from_source()`:
   - Extracts filename from the source PDF path
   - Parses state, council, urban_rural, and year from the filename
   - If urban_rural is "nan", searches for the actual PDF file in data directories
   - Uses the actual filename to get the correct urban_rural value (Urban/Rural)

2. **Updated all three report generators**:
   - Now use the source filename as the primary source for naming
   - Falls back to file search if "nan" placeholder is detected
   - Much more reliable than depending on metadata extraction

### How It Works:
```
Source: data/raw/2025/NSW/NSW_Ballina_nan_2025.pdf
         ↓ Parse filename
State: NSW, Council: Ballina, Type: nan, Year: 2025
         ↓ Type is "nan" - search for actual file
Find: data/LGAcleannames/2025/NSW/NSW_Ballina_Urban_2025.pdf
         ↓ Extract type from actual file
Type: Urban
         ↓ Generate output filename
NSW_Ballina_Urban_2025_alignment.csv
```

## Results

### Before Fix:
- ❌ `NSW_Unknown__2025_alignment.csv` (council name missing)
- ❌ All problematic councils merged into "Unknown"
- ❌ No individual council-level data

### After Fix:
- ✅ `NSW_Ballina_Urban_2025_alignment.csv` (correct name!)
- ✅ Each council gets its own file
- ✅ True council-level alignment data preserved

## Files Changed
- `src/reports/base.py`:
  - Added `_extract_filename_from_source()` helper method (lines 130-180)
  - Updated `generate_csv_report()` (lines 186-190)
  - Updated `generate_json_report()` (lines 212-216)
  - Updated `generate_summary_report()` (lines 239-243)

## Testing
- All 40 existing tests pass ✓
- Manual testing confirmed correct filename generation for Ballina 2025
- Search logic correctly finds actual PDF files and extracts urban_rural type

## Impact
This fix ensures that:
1. Each council's annual report produces its own alignment files
2. Council names are correctly preserved even when metadata extraction fails
3. The "nan" placeholder in filenames is resolved to the actual Urban/Rural type
4. Data integrity is maintained at the council level for accurate analysis