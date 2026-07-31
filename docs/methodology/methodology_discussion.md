# Empirical Approach for Assessing SDG Alignment in Local Government Annual Reports: A Text Analytics Framework

## Abstract

This paper presents a text analytics framework for systematically evaluating how local government activities, as disclosed in annual reports, align with the United Nations Sustainable Development Goals (SDGs). Drawing on advances in natural language processing and machine learning, we develop a methodology that combines semantic similarity assessment with topic modeling to enable large-scale comparative analysis across jurisdictions and time periods. The approach addresses fundamental challenges in public sector sustainability reporting research: the need to classify disclosures that may not explicitly reference SDG frameworks, and the requirement for systematic identification of thematic content within sustainability-oriented activities.

---

## 1. Introduction

The United Nations Sustainable Development Goals (SDGs) have emerged as a dominant framework for conceptualizing and reporting on organizational contributions to sustainable development (Awuah et al., 2023; Erin et al., 2024). For local governments, whose activities span infrastructure, community services, environmental management, and economic development, the SDGs provide a comprehensive taxonomy against which to assess the breadth and depth of sustainability engagement. However, the absence of standardized reporting frameworks for SDG alignment in the public sector presents methodological challenges for researchers seeking to conduct comparative analyses (Kaur et al., 2025).

This paper develops and applies an empirical framework that leverages recent advances in text mining and natural language processing to systematically assess SDG alignment in local government annual reports. Our approach addresses two interconnected challenges: first, the classification of activity-level disclosures according to their alignment with specific SDGs; and second, the identification of thematic content within SDG-aligned activities to enable comparison across jurisdictions, regions, and time periods.

We contribute to the emerging literature on public sector sustainability accounting by providing a replicable methodology that can be applied across diverse institutional contexts. The approach is particularly relevant for researchers investigating questions related to sustainability disclosure quality, the substance versus symbolism of organizational engagement with global goals, and the comparative analysis of sustainability priorities across jurisdictions (Du Toit, 2024).

---

## 2. Research Design and Data Collection

### 2.1. Data Source and Sample

The study draws on annual reports from local government entities across multiple Australian states, covering a three-year period (2023–2025). Annual reports serve as the primary mechanism through which public sector entities communicate their activities, achievements, and resource allocations to stakeholders, making them an appropriate source for assessing substantive engagement with sustainability objectives (Coy & Pratt, 1998; Steccolini, 2019).

The sample comprises council annual reports that vary in size, geographic location (urban versus rural), and jurisdictional context. This variation enables comparative analysis across institutional settings while maintaining a consistent analytical framework. Annual reports were systematically retrieved from council websites and subjected to text extraction procedures to isolate activity-level disclosures.¹

### 2.2. Unit of Analysis

Each activity statement extracted from annual reports constitutes a unit of analysis. Activity statements represent discrete descriptions of programs, services, projects, or initiatives undertaken by councils. This granular approach enables fine-grained classification of sustainability-oriented activities rather than treating reports as monolithic documents.²

---

## 3. Text Preprocessing and Normalization

### 3.1. Preprocessing Pipeline

Prior to analysis, textual data undergoes a standardized preprocessing pipeline designed to normalize linguistic variation while preserving semantic content. The pipeline consists of several stages:

**Tokenization and Lemmatization.** Text is segmented into individual tokens (words and punctuation), and inflected word forms are reduced to their base representations through lemmatization.³ For example, "communities" is transformed to "community," and "funded" to "fund," enabling consistent comparison across documents regardless of grammatical variation in the original text.

**Stopword Filtering.** A domain-specific stopword list was developed to exclude terms that, while appearing frequently in council communications, carry limited discriminative value for topic identification. This list includes council names, geographic identifiers (states, regions), and administrative terminology common across all jurisdictions.⁴ The development of a domain-specific stopword list addresses concerns about construct validity in text-based measures raised by Loughran and McDonald (2011) in their critique of generic dictionaries in financial text analysis.

**N-gram Generation.** Sequences of adjacent terms up to length three are incorporated to capture multi-word concepts that single terms cannot represent—such as "waste management," "energy efficiency," or "housing affordability." This approach aligns with recommendations from Senave et al. (2023) for accounting-related text mining applications.

### 3.2. Validity Considerations

Text preprocessing necessarily involves trade-offs between information preservation and noise reduction. We address validity concerns through multiple approaches: retaining the full distribution of SDG alignment scores rather than only top classifications; employing both traditional term-frequency methods and semantic embedding methods to enable cross-validation; and documenting all preprocessing decisions to support replication.

---

## 4. SDG Alignment Methodology

### 4.1. Semantic Similarity Approach

The core analytical task involves determining the degree to which each activity statement aligns with specific SDGs. We employ a semantic similarity approach using transformer-based language models, which capture contextual meaning more effectively than traditional keyword-based methods (Reimers & Gurevych, 2019; Devlin et al., 2019).

The alignment process proceeds as follows. First, standardized SDG descriptions are constructed for each of the 17 goals, drawing on official UN documentation and supplementary guidance from sustainability reporting frameworks. These descriptions serve as reference texts against which activity disclosures are compared. Second, each activity text is encoded into a dense vector representation using a pre-trained sentence transformer model.⁵ Third, cosine similarity is computed between each activity embedding and each SDG description embedding, yielding a distribution of alignment probabilities across all 17 SDGs.⁶

The highest-scoring SDG for each activity is designated as the "top SDG," though the full distribution of scores is retained for analyses requiring nuanced interpretation of multi-dimensional alignment. This approach addresses a fundamental challenge in sustainability reporting research: the need to systematically classify disclosures that may not explicitly reference SDG frameworks but nevertheless reflect sustainability-oriented activities (Székely & vom Brocke, 2017).

### 4.2. Theoretical Rationale

The semantic similarity approach rests on the assumption that activities contributing to a particular SDG will share conceptual content with the official SDG description, even when employing different terminology. This assumption is supported by research demonstrating the effectiveness of contextual language models in capturing domain-specific semantics (Bochkay et al., 2023). The use of pre-trained models also provides transfer learning benefits, enabling meaningful comparison without the need for large labeled training datasets specific to the public sector context.

Importantly, the methodology does not impose a deterministic classification but rather produces probability distributions that can be interpreted according to research questions. Activities with diffuse similarity patterns across multiple SDGs may reflect genuinely multi-dimensional activities, or may indicate insufficient specificity in the disclosure itself—both possibilities that warrant analytical attention.

---

## 5. Keyword Extraction and Thematic Characterization

### 5.1. TF-IDF Analysis

To characterize the substantive content of activities within each SDG category, we employ Term Frequency-Inverse Document Frequency (TF-IDF) analysis (Loughran & McDonald, 2011). This technique identifies terms that are distinctive to each SDG category relative to the broader corpus, surfacing themes that differentiate, for instance, SDG 11 (Sustainable Cities and Communities) activities from SDG 13 (Climate Action) activities.

The TF-IDF weighting naturally downweights terms that appear across all SDG categories while highlighting terms with concentrated usage in particular categories. The mathematical formulation assigns weight to term *t* in document *d* as:

TF-IDF(t, d) = TF(t, d) × IDF(t) = (count of t in d / total terms in d) × log(total documents / documents containing t)

### 5.2. Multi-Level Aggregation

Keyword extraction is performed at multiple aggregation levels: council-level, state-level, regional-level (urban versus rural), and temporal comparisons across years. This multi-level approach enables identification of themes that are common across all jurisdictions as well as themes that emerge specifically in particular geographic or temporal contexts. For example, keywords distinctive to SDG 11 activities in urban councils might include "public transport" and "housing density," while rural council keywords might include "road infrastructure" and "telecommunications access."

---

## 6. Topic Modeling

### 6.1. Dual Methodological Approach

To identify underlying thematic structures within SDG-specific activity disclosures, we employ two complementary topic modeling approaches: Latent Dirichlet Allocation (LDA) and BERTopic. This dual approach serves both validation and exploratory purposes, recognizing that different topic modeling techniques may reveal complementary aspects of the textual data (Žnidaršič et al., 2024).

**Latent Dirichlet Allocation (LDA).** LDA is a generative probabilistic model that discovers latent topics as distributions over words, with each document represented as a mixture of topics (Blei et al., 2003). Applied within each SDG category, LDA identifies coherent themes that characterize the diversity of activities. For instance, within SDG 11, LDA might distinguish topics related to housing, transportation, and urban planning—each representing a distinct dimension of "sustainable cities and communities" as operationalized by councils.

**BERTopic.** BERTopic extends topic modeling by incorporating semantic embeddings from transformer models (Grootendorst, 2022). Unlike LDA, which operates on word frequencies alone, BERTopic clusters documents based on their semantic similarity in a learned vector space.⁷ This enables identification of topics that may share vocabulary but differ in meaning, or conversely, topics expressed through different terminology but conveying related concepts.

### 6.2. Aggregation Strategy

Both topic modeling approaches are applied at multiple aggregation levels: globally (all councils combined), by state, by region (urban versus rural), and by year. For the BERTopic analysis specifically, aggregation precedes topic modeling—the corpus for, say, SDG 11 in Victoria comprises all SDG 11 activities from Victorian councils combined. This approach ensures sufficient document volume for stable topic estimation while enabling comparison of how thematic content varies across jurisdictions.

Topic consistency across aggregation levels provides evidence of robust thematic structures, while divergence may indicate meaningful heterogeneity in how SDGs are operationalized. For instance, if SDG 13 topics differ systematically between urban and rural councils, this may reflect genuinely different approaches to climate action appropriate to distinct community contexts.

### 6.3. Methodological Advantages of the Dual Approach

The combination of LDA and BERTopic offers complementary strengths. LDA provides interpretable, well-established topic structures that facilitate comparison with prior literature. BERTopic captures semantic relationships that word-frequency methods may miss, particularly when similar concepts are expressed through different terminology. The comparison of results across methods serves as a form of robustness checking—if both methods identify similar thematic structures, confidence in the findings increases.

---

## 7. Comparative Analysis Framework

### 7.1. Cross-Sectional Comparisons

The analytical framework supports cross-sectional comparisons across multiple dimensions:

**Jurisdictional Variation.** By aggregating data at the state level, the methodology enables comparison of how similar SDG themes are articulated differently across institutional contexts. State-level variation may reflect differences in regulatory environments, political priorities, or resource allocations that influence sustainability reporting practices.

**Urban-Rural Distinction.** The regional aggregation (urban versus rural) addresses a gap identified in the SDG reporting literature, which has predominantly focused on large urban entities and listed corporations (Low et al., 2023). Rural councils face distinct sustainability challenges and may operationalize SDGs in ways that differ from their urban counterparts.

**Temporal Dynamics.** Year-over-year comparison enables assessment of whether sustainability themes evolve in response to external events, policy changes, or shifting community priorities. The three-year time window captures a period of significant environmental and social disruption, including post-pandemic recovery and increasing attention to climate resilience.

### 7.2. Validity Considerations

Several validity considerations inform our approach. First, the use of pre-trained language models for SDG alignment introduces potential bias if the models' training data differs substantially from council report discourse. However, transformer models have demonstrated strong transfer learning capabilities across domains, and the SDG descriptions provide explicit semantic anchors for alignment (Reimers & Gurevych, 2019).

Second, topic modeling results are sensitive to parameter choices. We address this by employing default configurations validated in prior research, and by presenting findings as exploratory thematic structures rather than definitive categorizations. Researchers should interpret topics as descriptive summaries of discourse patterns rather than as objective representations of underlying reality.

Third, the aggregation strategy for BERTopic necessarily abstracts away from council-specific variation. Researchers should interpret BERTopic topics as characterizing the "collective discourse" within a category rather than representing any single council's activities.

---

## 8. Contribution to Public Sector Accounting Research

This methodology contributes to the growing intersection of accounting research and sustainability disclosure in several ways. First, it provides a systematic approach to classifying public sector activities according to global sustainability frameworks, addressing calls for more rigorous methodologies in SDG reporting research (Awuah et al., 2023; Erin et al., 2024). Second, the multi-level aggregation design enables comparative analysis across institutional contexts, responding to critiques that sustainability accounting research has focused predominantly on private sector entities (Farneti & Siboni, 2011).

Third, the combination of semantic classification with thematic characterization offers a more nuanced understanding of sustainability engagement than simple disclosure presence/absence measures. By examining what organizations say about their sustainability activities—through keyword analysis and topic modeling—researchers can assess both the extent and substance of SDG alignment.

---

## References

Awuah, G., Amponsem, F., & Ofori, K.S. (2023). Corporate reporting on the Sustainable Development Goals: A structured literature review and research agenda. *Journal of Accounting and Organizational Change*, 19(4), 629-656.

Blei, D.M., Ng, A.Y., & Jordan, M.I. (2003). Latent Dirichlet Allocation. *Journal of Machine Learning Research*, 3, 993-1022.

Bochkay, K., Brown, C., Leone, A.J., & Tucker, J. (2023). Textual analysis in accounting: What's next? *Contemporary Accounting Research*, 40(4), 2401-2431.

Coy, D., & Pratt, M. (1998). An empirical study of the reporting of responsibilities in annual reports. *Accounting, Accountability and Performance*, 4(4), 458-484.

Devlin, J., Chang, M.W., Lee, K., & Toutanova, K. (2019). BERT: Pre-training of deep bidirectional transformers for language understanding. *Proceedings of NAACL-HLT 2019*, 4171-4186.

Du Toit, E. (2024). Thirty years of sustainability reporting: A systematic literature review. *Sustainability*, 16(23), 10750.

Erin, O.A., Bamigboye, O.A., & Oyewo, B. (2024). Sustainable Development Goal research in accounting: A systematic literature review and direction for future research. *Journal of Financial Reporting and Accounting*.

Farneti, F., & Siboni, B. (2011). Sustainability reporting in Australian local government organisations. *Australian Accounting Review*, 21(4), 366-381.

Grootendorst, M. (2022). BERTopic: Neural topic modeling with a class-based TF-IDF procedure. *arXiv preprint arXiv:2203.05794*.

Kaur, H., Singh, K., & Singh, S. (2025). "Everything, everywhere, all at once": The role of accounting and reporting in achieving sustainable development goals. *Journal of Public Budgeting, Accounting & Financial Management*.

Loughran, T., & McDonald, B. (2011). When is a liability not a liability? Textual analysis, dictionaries, and 10-Ks. *Journal of Finance*, 66(1), 35-65.

Low, M.Y., Abdullah, N., & Khatib, S.F. (2023). Research trend in Sustainable Development Goals reporting: A systematic literature review. *Environmental Science and Pollution Research*, 30, 60817-60833.

Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. *Proceedings of EMNLP 2019*, 3982-3992.

Senave, M., Jans, M., & Srivastava, R.P. (2023). The application of text mining in accounting. *International Journal of Accounting Information Systems*, 48, 100620.

Steccolini, I. (2019). Sustainability reporting in local governments: A comparative analysis. *Public Money & Management*, 39(6), 405-412.

Székely, N., & vom Brocke, J. (2017). What can we learn from corporate sustainability reporting? Deriving propositions for research and practice from over 9,500 corporate sustainability reports. *PLoS ONE*, 12(6), e0174807.

Zhang, C., Stone, D., & Xie, Y. (2019). Text data sources in archival accounting research: Insights and strategies for accounting systems scholars. *Journal of Information Systems*, 33(2), 127-153.

Žnidaršič, J., Hafner, R., & Zupan, K. (2024). Textual analysis of corporate sustainability reporting and corporate ESG scores. *International Review of Financial Analysis*, 96, 103421.

---

## Footnotes

¹ Activity-level extraction employs PDF parsing tools to identify and segment activity descriptions within annual report narratives. The extraction process is guided by structural markers common to council reports (e.g., "Key Activities," "Service Delivery," "Achievements") and is supplemented by manual review for ambiguous cases.

² This approach aligns with recommendations from Senave et al. (2023) for text mining in accounting contexts, where document-level analysis may obscure important variation in disclosure content.

³ Lemmatization is preferred over stemming because it produces valid dictionary words, facilitating interpretability of topic modeling results. We employ spaCy's lemmatizer with the 'en_core_web_sm' language model.

⁴ The stopword list was developed iteratively through examination of high-frequency terms across the corpus, supplemented by domain expertise. It includes approximately 700 terms spanning standard English stopwords, Australian state and territory names, common council terminology (e.g., "council," "shire," "municipality"), and generic activity descriptors that appear frequently but carry limited discriminative value.

⁵ We employ the 'all-MiniLM-L6-v2' model from the Sentence-Transformers library, which provides a balance between computational efficiency and embedding quality suitable for large-scale analysis (Reimers & Gurevych, 2019).

⁶ Cosine similarity measures the cosine of the angle between two vectors in a high-dimensional space, with values ranging from -1 to 1. In semantic similarity applications, values typically range from 0 to 1, where 1 indicates identical semantic content and 0 indicates orthogonal (unrelated) content.

⁷ BERTopic employs a three-stage process: (1) document embedding via sentence transformers, (2) dimensionality reduction via UMAP (Uniform Manifold Approximation and Projection), and (3) clustering via HDBSCAN (Hierarchical Density-Based Spatial Clustering). Topic representations are derived using a class-based TF-IDF approach that emphasizes terms distinctive to each cluster.