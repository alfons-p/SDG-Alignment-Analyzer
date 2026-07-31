# Financial Statements Inventory Report

**Generated:** 2026-03-22
**Purpose:** Identify which council annual reports contain financial statements sections

---

## Overview

This inventory identifies which PDF documents in `data/LGAcleannames/` contain financial statements sections. When processing reports with `--nofinancial`, the text after the first detected financial statement heading is excluded from analysis.

---

## Summary Statistics

| Metric | Count | Percentage |
|--------|-------|------------|
| **Total PDFs scanned** | 1,542 | 100% |
| **Contains financial statements** | 1,296 | 84.0% |
| **No financial statements detected** | 246 | 16.0% |

---

## By State

| State | Total | With Financial | Without Financial | % With Financial |
|-------|-------|----------------|-------------------|-------------------|
| VIC | 231 | 219 | 12 | 94.8% |
| SA | 203 | 191 | 12 | 94.1% |
| TAS | 85 | 79 | 6 | 92.9% |
| NT | 48 | 44 | 4 | 91.7% |
| QLD | 213 | 193 | 20 | 90.6% |
| WA | 391 | 308 | 83 | 78.8% |
| NSW | 371 | 262 | 109 | 70.6% |

**Observation:** NSW and WA have the highest proportion of reports without financial statements, likely because some councils publish separate financial reports.

---

## By Year

| Year | Total | With Financial | Without Financial | % With Financial |
|------|-------|----------------|-------------------|-------------------|
| 2023 | 522 | 444 | 78 | 85.1% |
| 2024 | 520 | 429 | 91 | 82.5% |
| 2025 | 500 | 423 | 77 | 84.6% |

---

## Financial Statement Headings Detected

The following headings are used to detect the start of financial statements sections:

| Heading | Frequency |
|---------|-----------|
| financial statements | 578 |
| statement of comprehensive income | 308 |
| general purpose financial statements | 115 |
| audited financial statements | 113 |
| statement of financial position | 63 |
| statement of changes in equity | 50 |
| financial statement | 24 |
| statement of cash flows | 19 |
| notes to the financial statements | 19 |
| notes to financial statements | 4 |
| notes to and forming part of the financial statements | 2 |
| certified financial statements | 1 |

---

## Detection Method

The `filter_financial_statements()` function in `src/activity_extractor.py` searches for these headings (case-insensitive) with various formatting patterns:

- Heading on its own line: `\n{heading}\n`
- Heading with colon: `\n{heading}:`
- Heading followed by space: `\n{heading} `
- Uppercase variants of all above

When a heading is found, all text **after** that position is excluded from activity extraction.

---

## Using the `--nofinancial` Option

### When to Use

Use `--nofinancial` when:
1. You want to focus on narrative sections (community updates, project descriptions)
2. Financial statements contain standardized accounting data not relevant to SDG analysis
3. Processing smaller reports that may not have separate financial sections

### Command

```bash
python scripts/run_analysis.py --input data/LGAcleannames/ --nofinancial
```

### Output Location

When `--nofinancial` is enabled, results are saved to:
```
results/nofinancial/
├── by_council/
├── by_state/
├── trends/
├── sdg_keywords/
└── sdg_mentions/
```

---

## Reports Without Financial Statements

The following 246 reports do not contain detectable financial statement sections:

### By State

**NSW (109 reports):** NSW_Brewarrina_Rural_2023, NSW_Burwood_Urban_2023, NSW_Byron_Urban_2023, NSW_Cessnock_Urban_2023, NSW_Cobar_Rural_2023, NSW_Coffs Harbour_Urban_2023, NSW_Dubbo_Urban_2023, NSW_Dungog_Rural_2023, NSW_Edward River_Rural_2023, NSW_Forbes_Rural_2023, NSW_Hilltops_Rural_2023, NSW_Hunters Hill_Urban_2023, NSW_Junee_Rural_2023, NSW_Kyogle_Rural_2023, NSW_Lake Macquarie_Urban_2023, NSW_Liverpool Plains_Rural_2023, NSW_Lockhart_Rural_2023, NSW_Maitland_Urban_2023, NSW_Moree Plains_Rural_2023, NSW_Nambucca_Urban_2023, NSW_Penrith_Urban_2023, NSW_Port Macquarie Hastings_Urban_2023, NSW_Queanbeyan Palerang_Urban_2023, NSW_Randwick_Urban_2023, NSW_Richmond Valley_Urban_2023, NSW_Singleton_Urban_2023, NSW_Sydney_Urban_2023, NSW_Upper Hunter_Rural_2023, NSW_Wagga Wagga_Urban_2023, NSW_Walgett_Rural_2023, NSW_Warrumbungle_Rural_2023, NSW_Waverley_Urban_2023, NSW_Wingecarribee_Urban_2023, NSW_Woollahra_Urban_2023, NSW_Armidale_Urban_2024, NSW_Brewarrina_Rural_2024, NSW_Burwood_Urban_2024, NSW_Byron_Urban_2024, NSW_Central Coast_Urban_2024, NSW_Cessnock_Urban_2024, NSW_Cootamundra Gundagai_Rural_2024, NSW_Dubbo_Urban_2024, NSW_Dungog_Rural_2024, NSW_Edward River_Rural_2024, NSW_Forbes_Rural_2024, NSW_Georges River_Urban_2024, NSW_Hilltops_Rural_2024, NSW_Inner West_Urban_2024, NSW_Inverell_Rural_2024, NSW_Kyogle_Rural_2024, NSW_Lithgow_Urban_2024, NSW_Lockhart_Rural_2024, NSW_Maitland_Urban_2024, NSW_Nambucca_Urban_2024, NSW_Newcastle_Urban_2024, NSW_Orange_Urban_2024, NSW_Parramatta_Urban_2024, NSW_Port Macquarie Hastings_Urban_2024, NSW_Port Stephens_Urban_2024, NSW_Queanbeyan Palerang_Urban_2024, NSW_Randwick_Urban_2024, NSW_Richmond Valley_Urban_2024, NSW_Shellharbour_Urban_2024, NSW_Shoalhaven_Urban_2024, NSW_Sydney_Urban_2024, NSW_Temora_Rural_2024, NSW_Upper Hunter_Rural_2024, NSW_Waverley_Urban_2024, NSW_Wollongong_Urban_2024, NSW_Yass Valley_Rural_2024, NSW_Armidale_Urban_2025, NSW_Balranald_Rural_2025, NSW_Berrigan_Rural_2025, NSW_Burwood_Urban_2025, NSW_Byron_Urban_2025, NSW_Central Darling_Rural_2025, NSW_Cessnock_Urban_2025, NSW_Cobar_Rural_2025, NSW_Coffs Harbour_Urban_2025, NSW_Cootamundra Gundagai_Rural_2025, NSW_Cumberland_Urban_2025, NSW_Dubbo_Urban_2025, NSW_Dungog_Rural_2025, NSW_Forbes_Rural_2025, NSW_Hilltops_Rural_2025, NSW_Hornsby_Urban_2025, NSW_Inverell_Rural_2025, NSW_Kempsey_Urban_2025, NSW_Kyogle_Rural_2025, NSW_Lake Macquarie_Urban_2025, NSW_Leeton_Rural_2025, NSW_Lismore_Urban_2025, NSW_Lockhart_Rural_2025, NSW_Maitland_Urban_2025, NSW_Muswellbrook_Rural_2025, NSW_Orange_Urban_2025, NSW_Parramatta_Urban_2025, NSW_Penrith_Urban_2025, NSW_Port Macquarie Hastings_Urban_2025, NSW_Port Stephens_Urban_2025, NSW_Sydney_Urban_2025, NSW_Tamworth_Urban_2025, NSW_Upper Hunter_Rural_2025, NSW_Uralla_Rural_2025, NSW_Waverley_Urban_2025, NSW_Willoughby_Urban_2025, NSW_Wollongong_Urban_2025, NSW_Woollahra_Urban_2025, NSW_Yass Valley_Rural_2025

**WA (83 reports):** WA_Augusta Margaret River_Rural_2023, WA_Bunbury_Urban_2023, WA_Carnamah_Rural_2023, WA_Cockburn_Urban_2023, WA_Dalwallinu_Rural_2023, WA_Dandaragan_Rural_2023, WA_Denmark_Rural_2023, WA_Dundas_Rural_2023, WA_Halls Creek_Rural_2023, WA_Kalgoorlie Boulder_Urban_2023, WA_Kellerberrin_Rural_2023, WA_Kent_Rural_2023, WA_Kojonup_Rural_2023, WA_Kondinin_Urban_2023, WA_Kwinana_Urban_2023, WA_Laverton_Rural_2023, WA_Mandurah_Urban_2023, WA_Manjimup_Rural_2023, WA_Melville_Urban_2023, WA_Moora_Rural_2023, WA_Sandstone_Rural_2023, WA_Serpentine Jarrahdale_Urban_2023, WA_Shark Bay_Rural_2023, WA_Subiaco_Urban_2023, WA_Tammin_Rural_2023, WA_Vincent_Urban_2023, WA_Williams_Rural_2023, WA_Boyup Brooke_Rural_2024, WA_Bunbury_Urban_2024, WA_Carnamah_Rural_2024, WA_Chittering_Rural_2024, WA_Cockburn_Urban_2024, WA_Dandaragan_Rural_2024, WA_Derby West Kimberley_Rural_2024, WA_Dowerin_Rural_2024, WA_Fremantle_Urban_2024, WA_Joondalup_Urban_2024, WA_Kalgoorlie Boulder_Urban_2024, WA_Kellerberrin_Rural_2024, WA_Kojonup_Rural_2024, WA_Kondinin_Urban_2024, WA_Kulin_Rural_2024, WA_Kwinana_Urban_2024, WA_Mandurah_Urban_2024, WA_Melville_Urban_2024, WA_Morawa_Rural_2024, WA_Mosman Park_Urban_2024, WA_Mount Magnet_Rural_2024, WA_Mundaring_Rural_2024, WA_Narembeen_Rural_2024, WA_Ngaanyatjarraku_Rural_2024, WA_Northampton_Rural_2024, WA_Quairading_Rural_2024, WA_Sandstone_Rural_2024, WA_Subiaco_Urban_2024, WA_Tammin_Rural_2024, WA_Toodyay_Rural_2024, WA_Wagin_Rural_2024, WA_Wongan Ballidu_Rural_2024, WA_Albany_Urban_2025, WA_Carnamah_Rural_2025, WA_Cockburn_Urban_2025, WA_Collie_Rural_2025, WA_Cranbrook_Rural_2025, WA_Cunderdin_Rural_2025, WA_Dumbleyung_Rural_2025, WA_Dundas_Rural_2025, WA_Fremantle_Urban_2025, WA_Irwin_Rural_2025, WA_Joondalup_Urban_2025, WA_Karratha_Urban_2025, WA_Kellerberrin_Rural_2025, WA_Kondinin_Urban_2025, WA_Kulin_Rural_2025, WA_Kwinana_Urban_2025, WA_Mandurah_Urban_2025, WA_Manjimup_Rural_2025, WA_Menzies_Rural_2025, WA_Northampton_Rural_2025, WA_Nungarin_Rural_2025, WA_Tammin_Rural_2025, WA_Three Springs_Rural_2025, WA_Wongan Ballidu_Rural_2025

**QLD (20 reports):** QLD_Blackall Tambo_Rural_2023, QLD_Cherbourg_Rural_2023, QLD_Mapoon_Rural_2023, QLD_Mckinlay_Rural_2023, QLD_Mount Isa_Rural_2023, QLD_Cherbourg_Rural_2024, QLD_Flinders_Rural_2024, QLD_Hope Vale_Rural_2024, QLD_Mapoon_Rural_2024, QLD_Mount Isa_Rural_2024, QLD_Napranum_Rural_2024, QLD_Palm Island_Urban_2024, QLD_Somerset_Urban_2024, QLD_Western Downs_Urban_2024, QLD_Winton_Rural_2024, QLD_Bulloo_Rural_2025, QLD_Cherbourg_Rural_2025, QLD_Isaac_Urban_2025, QLD_South Burnett_Urban_2025, QLD_Yarrabah_Rural_2025

**SA (12 reports):** SA_Anangu_Rural_2023, SA_Franklin Harbour_Rural_2023, SA_The Barossa_Rural_2023, SA_Wuddina_Rural_2023, SA_Elliston_Rural_2024, SA_Franklin Harbour_Rural_2024, SA_The Barossa_Rural_2024, SA_Franklin Harbour_Rural_2025, SA_Gawler_Urban_2025, SA_Mount Barker_Urban_2025, SA_Playford_Urban_2025, SA_The Barossa_Rural_2025

**VIC (12 reports):** VIC_Bass Coast_Urban_2023, VIC_Glenelg_Urban_2023, VIC_Hepburn_Rural_2023, VIC_Loddon_Rural_2023, VIC_Wyndham_Urban_2023, VIC_Glenelg_Urban_2024, VIC_Hobsons Bay_Urban_2024, VIC_Loddon_Rural_2024, VIC_Yarra Ranges_Urban_2024, VIC_Hobsons Bay_Urban_2025, VIC_Wyndham_Urban_2025, VIC_Yarra Ranges_Urban_2025

**TAS (6 reports):** TAS_Central Highlands_Rural_2023, TAS_West Coast_Rural_2023, TAS_Burnie_Urban_2024, TAS_Devonport_Urban_2024, TAS_Huon Valley_Rural_2024, TAS_Huon Valley_Rural_2025

**NT (4 reports):** NT_Katherine_Rural_2023, NT_Tiwi Islands_Rural_2024, NT_Victoria Daly_Rural_2024, NT_Wagait_Urban_2024

---

## Data File

Full inventory data is available at: `data/financial_statements_inventory.csv`

### CSV Columns

| Column | Description |
|--------|-------------|
| filename | PDF filename |
| path | Relative path from data/LGAcleannames/ |
| state | State abbreviation (NSW, VIC, QLD, etc.) |
| council | Council name extracted from filename |
| year | Year extracted from filename |
| has_financial_statements | True/False - whether financial statements were detected |
| financial_heading | The heading that was found (or None) |
| financial_page | Page number where financial statements begin |
| total_pages | Total number of pages in the PDF |
| total_chars | Total characters in the document |

---

## Related Code

- **Detection function:** `src/activity_extractor.py` - `filter_financial_statements()`
- **CLI option:** `scripts/run_analysis.py` - `--nofinancial` flag
- **Headings list:** `FINANCIAL_STATEMENT_HEADINGS` in both files

---

## Notes

1. Some reports may have financial statements but with different heading formats not captured by the current detection patterns. These would be classified as "no financial statements" even though they contain financial data.

2. Reports without financial statements typically:
   - Are shorter documents (community updates, highlights reports)
   - Have separate financial reports published elsewhere
   - Use alternative heading formats for financial sections

3. The detection is based on text matching and may miss:
   - Financial statements with non-standard headings
   - Financial content embedded in other sections
   - Scanned PDFs with OCR issues