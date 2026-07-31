# References

## UN Sustainable Development Goals Official Sources

- United Nations. (2015). *Transforming our world: the 2030 Agenda for Sustainable Development*. A/RES/70/1. https://www.un.org/ga/search/view_doc.asp?symbol=A/RES/70/1&Lang=E

- United Nations Department of Economic and Social Affairs (DESA). (2025). *Goal 17: Strengthen the means of implementation and revitalize the Global Partnership for Sustainable Development*. https://sdgs.un.org/goals/goal17

- United Nations Statistics Division. (2025). *SDG Indicators Metadata Repository*. https://unstats.un.org/sdgs/metadata/

- United Nations Statistics Division. (2025). *Sustainable Development Goals Extended Report 2025 - Goal 17*. https://unstats.un.org/sdgs/report/2025/extended-report/Extended-Report-2025_Goal-17.pdf

- UNESCAP. (2024). *Means of Implementation | SDG Help Desk*. https://sdghelpdesk.unescap.org/knowledge-hub/thematic-area/means-implementation

## SDG Text Classification Research

- P. Arora, M. K. H. Aung, & J. W. N. Cheong. (2025). *Polarity Detection of Sustainable Development Goals in News Text*. arXiv preprint. https://arxiv.org/abs/2509.19833

- G. Siudem, M. Bautista, & D. S. S. Sousa. (2022). *SDG-Meter: A Deep Learning Based Tool for Automatic Text Classification of the Sustainable Development Goals*. In: ACIIDS 2022. Lecture Notes in Computer Science, vol 13295. Springer. https://doi.org/10.1007/978-3-031-21743-2_21

- D. N. P. W. Tissera, R. Tang, H. Xu, & A. Arenas. (2024). *Using novel data and ensemble models to improve automated labeling of Sustainable Development Goals*. Sustainability Science. https://doi.org/10.1007/s11625-024-01516-3

- F. D. Russo, M. Grimaldi, & A. Colabianchi. (2025). *Capturing research literature attitude towards sustainable development goals: an LLM-based topic modeling approach*. Journal of Big Data, 12(1). https://doi.org/10.1186/s40537-025-01189-4

- F. Biancardi, F. C. Calderoni, G. F. G. Zollo, M. S. Teodoro, & R. Savino. (2021). *Natural language processing and network analysis provide novel insights on policy and scientific discourse around Sustainable Development Goals*. Scientific Reports, 11, Article 23860. https://doi.org/10.1038/s41598-021-01801-6

## Policy & Implementation

- C. Scartascini, M. L. Criscuolo, D. R. Diaz-Rojas, L. González, F. Rojas, & J. C. Benítez. (2023). *Automatic SDG budget tagging: Building public financial management capacity through natural language processing*. Data & Policy, 5, e25. https://doi.org/10.1017/dap.2023.25

- UNDP. (2021). *SDG Alignment and Budget Taxonomy: Colombia Case Study*. https://www.undp.org/

## Tools & Resources

- OSDG.ai. (2024). *Open Source SDG Classification Tool*. https://www.osdg.ai/
  - GitHub Repository: https://github.com/osdg-ai/osdg-data
  - Research Paper: Siudem et al. (2023). *OSDG 2.0: A multilingual tool for classifying text data by UN Sustainable Development Goals (SDGs)*. arXiv:2211.11252.

- text2sdg R Package. (2024). *Comparing SDG Classification Systems*. https://CRAN.R-project.org/package=text2sdg

- TETYS Dashboard. (2025). *SDG Topic Evolution Analysis*. http://gmql.eu/tetys/

## Related Projects

- Aurora SDG Dashboard. (2024). *Mapping Research Output to SDGs*. https://aurora-sdg.ph-hosting.net/

- Elsevier SDG Mapping. (2023). *SDG Classification of Research Publications*.

- SIRIS Academic SDG Classifier. (2023). https://www.sirisacademic.com/

- SDSN Australia/Pacific SDG Mapper. (2022).

## OSDG Community Dataset

**File**: `data/external/osdg-community-data-v2024-04-01.csv` (29 MB)

**Source**: [OSDG.ai](https://www.osdg.ai/) / [Zenodo](https://zenodo.org/records/11441197)

**Citation**:
```bibtex
@dataset{osdg_community_dataset,
  title={OSDG Community Dataset (OSDG-CD)},
  author={Siudem, Grzegorz and Bautista, Nuria and Sousa, Daniel},
  year={2024},
  publisher={Zenodo},
  doi={10.5281/zenodo.5550237},
  url={https://doi.org/10.5281/zenodo.5550237}
}
```

**Download**:
```bash
curl -L -o data/external/osdg-community-data-v2024-04-01.csv \
  "https://zenodo.org/records/11441197/files/osdg-community-data-v2024-04-01.csv?download=1"
```

**Dataset Description**:

The OSDG Community Dataset (OSDG-CD) is a **crowd-sourced collection of ~43,000 text excerpts** labeled with SDG classifications. It contains validated annotations from citizen scientists via the OSDG Community Platform.

**Columns**:
- `doi`: Document identifier
- `text_id`: Unique text excerpt identifier
- `text`: The text excerpt/paragraph
- `sdg`: Assigned SDG (1-17)
- `labels_negative`: Number of negative votes
- `labels_positive`: Number of positive votes
- `agreement`: Inter-annotator agreement score (0-1)

**Use Cases**:
- Fine-tuning sentence transformer models
- Validation and benchmarking
- Threshold calibration
- Keyword extraction
- Model evaluation

See `data/external/README.md` for detailed documentation.

## Citation

If you use this project in academic work, please cite:

```bibtex
@software{sdg_alignment_analyzer,
  title = {SDG Alignment Analyzer: NLP-based Assessment of Council Reports},
  author = {SDG Analyzer Team},
  year = {2025},
  url = {https://github.com/your-org/sdg-alignment-analyzer}
}
```

## SDG Keyword Taxonomies

The keyword taxonomies used in this project are informed by:

1. **UN Official SDG Indicators** - Official target and indicator definitions
2. **OSDG.ai Community Dataset** - Crowd-sourced validated text annotations
3. **SDG-Meter Taxonomy** - BERT-based classification keywords
4. **Academic consensus** - From systematic reviews of SDG text classification literature

### SDG-Specific Notes

**SDG 11 (Sustainable Cities and Communities):**
Based on UN Habitat and UN-Habitat III New Urban Agenda keywords.
Focus areas: urban planning, affordable housing, public transport, urban resilience.

**SDG 17 (Partnerships for the Goals):**
Comprehensive scope covering both domestic (resource mobilization, capacity building, policy coherence) and international (technology transfer, multi-stakeholder partnerships) elements.
Not limited to international collaboration as commonly misunderstood.

## Model Improvements (v0.2.0)

### Enhanced SDG Definitions (2026-02-26)

The model improvements implemented in February 2026 draw from the following sources:

#### SDG Descriptions and Indicators

1. **United Nations. (2015).** *Transforming our world: the 2030 Agenda for Sustainable Development*. A/RES/70/1.
   - Complete SDG descriptions with targets and implementation guidance
   - Source: https://www.un.org/ga/search/view_doc.asp?symbol=A/RES/70/1&Lang=E

2. **United Nations Statistics Division.** (2025). *SDG Indicators Database*.
   - Official list of 231 SDG indicators
   - Source: https://unstats.un.org/sdgs/UNSDAPI/v1/sdg/Series/Data

3. **United Nations.** (2024). *SDG Indicators: Global indicator framework*.
   - Tier classification and metadata
   - Source: https://unstats.un.org/sdgs/indicators/Global%20Indicator%20Framework%20after%202024%20refinement.English.pdf

#### Local Government Keywords

4. **Australian Local Government Association (ALGA).** (2024). *National Local Government Report*.
   - Common council service areas and responsibilities
   - https://www.alga.asn.au/

5. **Municipal Association of Victoria (MAV).** (2024). *Local Government Functions and Services*.
   - Victorian council service classifications
   - https://www.mav.asn.au/

6. **Local Government NSW (LGNSW).** (2024). *Council Services Directory*.
   - NSW council service categories and terminology
   - https://www.lgnsw.org.au/

7. **Australian Bureau of Statistics.** (2024). *Local Government Finance Statistics, Australia*.
   - ABS Catalogue No. 5504.0
   - Standardized expenditure categories for local government
   - https://www.abs.gov.au/statistics/people/people-and-communities/local-government-finance-statistics

8. **Analysis of Council Annual Reports (2023-2025).**
   - NSW: Alpine, Armidale, Ballina, Bathurst, Bayside, Blacktown, Blue Mountains, Byron, Camden
   - VIC: Alpine, Ararat, Banyule, Bayside, Boroondara, Casey, Geelong, Melbourne
   - Common terminology extraction and pattern analysis

#### Embedding Enhancement Strategy

9. **Sentence Transformers Documentation.** (2024). *Multi-task learning and ensemble embeddings*.
   - https://www.sbert.net/
   - Multiple text encoding and weighted combination approach

### Multi-Text Embedding Methodology

The enhanced embedding generation strategy (Improvement D) uses a weighted combination approach inspired by:

- **Reimers, N., & Gurevych, I.** (2019). *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks*. EMNLP/IJCNLP.
  - Base sentence transformer methodology
  - https://doi.org/10.18653/v1/D19-1410

- **Muennighoff, N.** (2022). *SGPT: GPT Sentence Embeddings for Semantic Search*. arXiv:2202.08904.
  - Multi-text representation strategies
  - https://arxiv.org/abs/2202.08904

### Keyword Compilation Method

Local government keywords compiled through:
1. **Systematic review** of council annual report terminology (n=60+ reports)
2. **Category mapping** to UN SDG targets and indicators
3. **Peer validation** against Australian local government service frameworks
4. **Coverage analysis** ensuring alignment with common council activities

See `docs/model_improvements.md` for detailed documentation of the enhancement implementation.

## Version History

- v0.2.0 (2026-02-26): Enhanced SDG definitions with expanded descriptions, local government keywords, and UN indicators. Multi-text embedding generation strategy.
- v0.1.0 (2025-02-24): Initial release with refined SDG 11 and SDG 17 keyword definitions based on UN official sources and academic research.

---

*Last updated: 2026-02-26*
