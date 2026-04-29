#!/usr/bin/env python3
"""Topic modeling for SDG activities using LDA and BERTopic.

This script:
1. Reads all {state}_{council}_{region}_{year}_alignment.csv files
2. Groups activity_text by council/year/state/region AND top_sdg
3. Applies LDA and BERTopic for topic discovery
4. Outputs topic summaries to CSV files

Usage:
    python scripts/council_topsdg_topics.py
    python scripts/council_topsdg_topics.py --method lda
    python scripts/council_topsdg_topics.py --method bertopic
    python scripts/council_topsdg_topics.py --num-topics 5
"""

import argparse
import glob
import os
import re
import warnings
import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter

# Suppress warnings
warnings.filterwarnings('ignore')

# NLP imports
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation

# Check for spaCy lemmatization
SPACY_AVAILABLE = False
try:
    import spacy
    nlp = spacy.load('en_core_web_sm', disable=['parser', 'ner'])
    SPACY_AVAILABLE = True
except (ImportError, OSError):
    pass

# Check if BERTopic is available (optional)
BERTOPIC_AVAILABLE = False
try:
    from bertopic import BERTopic
    from sentence_transformers import SentenceTransformer
    BERTOPIC_AVAILABLE = True
except ImportError:
    pass


# Common English stopwords (extended list)
STOPWORDS = set([
    # Articles and determiners
    'a', 'an', 'the', 'this', 'that', 'these', 'those', 'my', 'your', 'his', 'her',
    'its', 'our', 'their', 'mine', 'yours', 'hers', 'ours', 'theirs',
    # Conjunctions
    'and', 'or', 'but', 'nor', 'so', 'yet', 'for', 'as', 'if', 'than',
    # Prepositions
    'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'about', 'against',
    'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
    'up', 'down', 'out', 'off', 'over', 'under', 'again', 'further', 'across',
    # Pronouns
    'i', 'you', 'he', 'she', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
    'it', 'we', 'who', 'whom', 'whose', 'which', 'what', 'where', 'when', 'why', 'how',
    # Verbs
    'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does',
    'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall',
    'can', 'need', 'dare', 'ought', 'used', 'am', 'being',
    # Adverbs and quantifiers
    'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such',
    'no', 'not', 'only', 'own', 'same', 'so', 'too', 'very', 'just', 'also', 'now',
    'here', 'there', 'then', 'once', 'any',
    # Council/government stopwords
    'council', 'city', 'shire', 'government', 'local', 'area', 'region', 'state',
    'nsw', 'vic', 'qld', 'sa', 'wa', 'tas', 'nt', 'act', 'australia', 'australian',
    'year', 'financial', 'annual', 'report', '2022', '2023', '2024', '2025', '2021',
    '2020', '2019', 'per', 'cent', 'total', 'new', 'including', 'within', 'across',
    'following', 'provided', 'based', 'related', 'associated', 'various',
    # State abbreviations and names
    'new', 'south', 'wales', 'victoria', 'queensland', 'tasmania', 'northern',
    'territory', 'western', 'australia', 'australian',
    # Council name components (extracted from council names)
    'adelaide', 'albany', 'albury', 'alexander', 'alexandrina', 'alice', 'alpine',
    'anangu', 'ararat', 'areas', 'armadale', 'armidale', 'arnhem', 'arthur', 'ashburton',
    'augusta', 'aurukun', 'balingup', 'ballarat', 'ballidu', 'ballina', 'balonne',
    'balranald', 'banana', 'banks', 'banyule', 'barcaldine', 'barcoo', 'barker', 'barkly',
    'barmera', 'barossa', 'barunga', 'bass', 'bassendean', 'bathurst', 'baw', 'bay',
    'bayside', 'bayswater', 'beaches', 'bega', 'bellingen', 'belmont', 'benalla',
    'bendigo', 'berri', 'berrigan', 'beverley', 'blackall', 'blacktown', 'bland',
    'blayney', 'blue', 'boddington', 'bogan', 'boroondara', 'boulder', 'boulia',
    'bourke', 'boyup', 'break', 'brewarrina', 'bridge', 'bridgetown', 'brighton',
    'brimbank', 'brisbane', 'broken', 'brooke', 'brookton', 'broome', 'broomehill',
    'bruce', 'bulloo', 'buloke', 'bunbury', 'bundaberg', 'burdekin', 'burke', 'burnett',
    'burnie', 'burnside', 'burwood', 'busselton', 'byron', 'cabonne', 'cairns', 'cambridge',
    'camden', 'campaspe', 'campbelltown', 'canada', 'canning', 'canterbury', 'capel',
    'cardinia', 'carnamah', 'carnarvon', 'carpentaria', 'carrathool', 'carrieton',
    'casey', 'cassowary', 'ceduna', 'central', 'cessnock', 'chapman', 'charles',
    'charters', 'cherbourg', 'chittering', 'circular', 'clare', 'claremont', 'clarence',
    'cleve', 'cloncurry', 'coast', 'cobar', 'cockburn', 'coffs', 'colac', 'collie',
    'coober', 'cook', 'coolamon', 'coolgardie', 'coomalie', 'coonamble', 'coorong',
    'coorow', 'cootamundra', 'copper', 'corangamite', 'corrigin', 'cottesloe', 'cove',
    'cowra', 'creek', 'croydon', 'cuballing', 'cue', 'cumberland', 'cunderdin',
    'dalwallinu', 'daly', 'dandaragan', 'dandenong', 'dardanup', 'darebin', 'darling',
    'darwin', 'denmark', 'derby', 'derwent', 'desert', 'devonport', 'diamantina',
    'donnybrook', 'doomadgee', 'dorset', 'douglas', 'dowerin', 'downs', 'dubbo',
    'dumbleyung', 'dundas', 'dungog', 'east', 'edward', 'eira', 'elliston', 'enfield',
    'esperance', 'etheridge', 'eurobodalla', 'exmouth', 'eyre', 'fairfield', 'federation',
    'flinders', 'forbes', 'franklin', 'frankston', 'fraser', 'fremantle', 'gai', 'gambier',
    'gannawarra', 'gascoyne', 'gawler', 'geelong', 'george', 'georges', 'geraldton',
    'gilbert', 'gilgandra', 'gingin', 'gippsland', 'gladstone', 'glamorgan', 'glen',
    'glenelg', 'glenorchy', 'gnowangerup', 'goldcoast', 'golden', 'goldfields',
    'goomalling', 'goondiwindi', 'gosnells', 'goulburn', 'goyder', 'grace', 'grampians',
    'grant', 'greenbushes', 'griffith', 'grove', 'gulf', 'gully', 'gundagai', 'gunnedah',
    'gwydir', 'gympie', 'halls', 'harbor', 'harbour', 'harvey', 'hastings', 'hawkesbury',
    'hay', 'head', 'hedland', 'hepburn', 'highlands', 'hill', 'hills', 'hilltops',
    'hinchinbrook', 'hindmarsh', 'hobart', 'hobsons', 'holdfast', 'hope', 'hornsby',
    'horsham', 'hume', 'hunter', 'hunters', 'huon', 'indigo', 'inner', 'innes',
    'inverell', 'ipswich', 'irwin', 'isa', 'isaac', 'island', 'islands', 'jarrahdale',
    'joondalup', 'junee', 'kalamunda', 'kalgoorlie', 'kangaroo', 'karoonda', 'karratha',
    'katanning', 'katherine', 'kellerberrin', 'kempsey', 'kent', 'kentish', 'kiama',
    'kimba', 'kimberley', 'king', 'kingborough', 'kingston', 'knox', 'kojonup',
    'kondinin', 'koorda', 'kowanyama', 'ku', 'kulin', 'kwinana', 'kyogle', 'lachlan',
    'lake', 'lane', 'latrobe', 'launceston', 'laverton', 'leeton', 'leonora', 'light',
    'lincoln', 'lismore', 'litchfield', 'lithgow', 'liverpool', 'livingstone', 'lockhart',
    'lockyer', 'loddon', 'logan', 'longreach', 'lower', 'loxton', 'lucindale', 'macdonnell',
    'macedon', 'mackay', 'macquarie', 'magnet', 'maitland', 'mallee', 'mandurah',
    'manjimup', 'manningham', 'mansfield', 'mapoon', 'maranoa', 'mareeba', 'margaret',
    'maribyrnong', 'marion', 'maroondah', 'marshall', 'mckinlay', 'meander', 'meekatharra',
    'melbourne', 'melton', 'melville', 'menzies', 'merredin', 'merri', 'mid', 'midlands',
    'mildura', 'mingenew', 'mitcham', 'mitchell', 'moira', 'monaro', 'monash', 'moonee',
    'moora', 'moorabool', 'morawa', 'moree', 'moreton', 'mornington', 'mosman', 'mount',
    'mountains', 'moyne', 'mt', 'mukinbudin', 'mulwaree', 'mundaring', 'murchison',
    'murray', 'murrindindi', 'murrumbidgee', 'murweh', 'muswellbrook', 'nambucca',
    'nannup', 'napranum', 'naracoorte', 'narembeen', 'narrabri', 'narrandera', 'narrogin',
    'narromine', 'nedlands', 'newcastle', 'ngaanyatjarraku', 'nillumbik', 'noosa',
    'north', 'northam', 'northampton', 'northern', 'norwood', 'nungarin', 'oberon',
    'onkaparinga', 'orange', 'orroroo', 'otway', 'palerang', 'palm', 'palmerston',
    'paringa', 'park', 'parkes', 'paroo', 'parramatta', 'payneham', 'pedy', 'peninsula',
    'penrith', 'peppermint', 'perenjori', 'perth', 'peters', 'phillip', 'pilbara',
    'pingelly', 'pirie', 'plains', 'plantagenet', 'playford', 'pormpuraaw', 'port',
    'prospect', 'pyrenees', 'quairading', 'queanbeyan', 'queenscliffe', 'quilpie',
    'randwick', 'range', 'ranges', 'ravensthorpe', 'redland', 'remarkable', 'renmark',
    'richmond', 'rim', 'ring', 'river', 'robe', 'rock', 'rockhampton', 'rockingham',
    'roper', 'roxby', 'ryde', 'salisbury', 'sandstone', 'scenic', 'serpentine', 'severn',
    'shark', 'shellharbour', 'shepparton', 'shoalhaven', 'singleton', 'snowy', 'somerset',
    'sorell', 'south', 'southern', 'spring', 'springs', 'st', 'stephens', 'stirling',
    'stonnington', 'strait', 'strathbogie', 'strathfield', 'streaky', 'sturt', 'subiaco',
    'sunshine', 'surf', 'sutherland', 'swan', 'sydney', 'tablelands', 'tamar', 'tambellup',
    'tambo', 'tammin', 'tamworth', 'tasman', 'tatiara', 'tea', 'temora', 'tenterfield',
    'the', 'three', 'tiwi', 'toodyay', 'toowoomba', 'torres', 'towers', 'town',
    'townsville', 'towong', 'trayning', 'tree', 'tumby', 'tweed', 'unley', 'upper',
    'uralla', 'victor', 'victoria', 'vincent', 'wagait', 'wagga', 'wagin', 'waikerie',
    'wakefield', 'walcha', 'walgett', 'walkerville', 'wandering', 'wangaratta', 'wanneroo',
    'waratah', 'waroona', 'warren', 'warrnambool', 'warrumbungle', 'wattle', 'waverley',
    'weddin', 'weipa', 'wellington', 'wentworth', 'west', 'western', 'westonia',
    'whitehorse', 'whitsunday', 'whittlesea', 'whyalla', 'wickepin', 'williams',
    'willoughby', 'wiluna', 'wimmera', 'wingecarribee', 'winton', 'wodonga', 'wollondilly',
    'wollongong', 'wongan', 'woodanilling', 'woollahra', 'wuddina', 'wudinna', 'wujal',
    'wyalkatchem', 'wyndham', 'wynyard', 'yankalilla', 'yarra', 'yarrabah', 'yarriambiack',
    'yass', 'yilgarn', 'york', 'yorke',
])


def parse_filename(filename: str) -> dict:
    """Parse council alignment filename into components."""
    name = Path(filename).stem.replace('_alignment', '')
    parts = name.split('_')

    state = parts[0] if len(parts) > 0 else 'Unknown'
    year = parts[-1] if len(parts) > 0 else 'Unknown'
    region = parts[-2] if len(parts) > 1 else 'Unknown'
    council = '_'.join(parts[1:-2]) if len(parts) > 2 else 'Unknown'

    return {
        'state': state,
        'council': council,
        'region': region,
        'year': year
    }


def preprocess_text(text: str) -> str:
    """Clean and preprocess text for topic modeling with lemmatization."""
    if pd.isna(text) or not isinstance(text, str):
        return ''

    # Convert to lowercase
    text = text.lower()

    # Remove numbers and punctuation
    text = re.sub(r'\d+', '', text)
    text = re.sub(r'[^\w\s]', ' ', text)

    # Remove extra whitespace
    text = ' '.join(text.split())

    # Apply lemmatization if spaCy is available
    if SPACY_AVAILABLE:
        try:
            doc = nlp(text)
            # Lemmatize and filter stopwords
            words = [token.lemma_ for token in doc
                     if token.lemma_.lower() not in STOPWORDS
                     and token.text.lower() not in STOPWORDS
                     and len(token.lemma_) > 2
                     and not token.is_stop]
            return ' '.join(words)
        except Exception:
            pass

    # Fallback: remove stopwords without lemmatization
    words = text.split()
    words = [w for w in words if w not in STOPWORDS and len(w) > 2]

    return ' '.join(words)


class LDATopicModeler:
    """LDA-based topic modeling for SDG activities."""

    def __init__(self, n_topics=5, n_words=10):
        self.n_topics = n_topics
        self.n_words = n_words
        self.vectorizer = None
        self.lda_model = None

    def fit(self, documents):
        """Fit LDA model to documents."""
        if not documents or all(doc.strip() == '' for doc in documents):
            return None

        documents = [doc for doc in documents if doc.strip()]
        if not documents:
            return None

        # Vectorize documents
        # Adjust parameters based on document count
        n_docs = len(documents)
        max_df = min(0.95, 1.0) if n_docs < 5 else 0.95
        min_df = 1

        self.vectorizer = CountVectorizer(
            max_features=500,
            min_df=min_df,
            max_df=max_df,
            ngram_range=(1, 3),
            stop_words='english'
        )

        try:
            doc_term_matrix = self.vectorizer.fit_transform(documents)

            # Check if we have enough features
            n_features = doc_term_matrix.shape[1]
            if n_features < 2:
                return None

            # Fit LDA with appropriate number of topics
            n_components = min(self.n_topics, n_docs, n_features)

            self.lda_model = LatentDirichletAllocation(
                n_components=max(1, n_components),
                random_state=42,
                max_iter=50
            )
            self.lda_model.fit(doc_term_matrix)

            return self.lda_model

        except Exception as e:
            print(f"LDA fitting error: {e}")
            return None

    def get_topics(self):
        """Extract topics from fitted model."""
        if self.lda_model is None or self.vectorizer is None:
            return []

        feature_names = self.vectorizer.get_feature_names_out()
        topics = []

        for topic_idx, topic in enumerate(self.lda_model.components_):
            top_words_idx = topic.argsort()[-self.n_words:][::-1]
            top_words = [feature_names[i] for i in top_words_idx]
            topics.append({
                'topic_id': topic_idx,
                'words': top_words,
                'weights': [float(topic[i]) for i in top_words_idx]
            })

        return topics


class BERTopicModeler:
    """BERTopic-based topic modeling for SDG activities."""

    def __init__(self, n_topics=5, n_words=10):
        self.n_topics = n_topics
        self.n_words = n_words
        self.topic_model = None

    def fit(self, documents, original_documents=None):
        """Fit BERTopic model to documents.

        Args:
            documents: Preprocessed documents for topic representation (may have empty strings)
            original_documents: Original documents for embedding (required)
        """
        if not BERTOPIC_AVAILABLE:
            return None

        if original_documents is None:
            original_documents = documents

        if not original_documents or len(original_documents) < 2:
            return None

        # Filter out None/empty documents
        valid_docs = [(i, orig) for i, orig in enumerate(original_documents)
                      if pd.notna(orig) and str(orig).strip()]
        if len(valid_docs) < 2:
            return None

        # Use original documents for embedding
        docs_for_embedding = [str(orig) for _, orig in valid_docs]

        try:
            # Use a lightweight sentence transformer
            sentence_model = SentenceTransformer('all-MiniLM-L6-v2')

            # Custom vectorizer for topic representation with stopwords filtering
            # This filters common words from topic representations
            from sklearn.feature_extraction.text import CountVectorizer

            # Build stopwords list for vectorizer (sklearn's stop_words + our custom list)
            sklearn_stopwords = list(STOPWORDS)  # Our expanded stopwords

            vectorizer_model = CountVectorizer(
                max_features=1000,
                min_df=1,
                max_df=1.0,
                ngram_range=(1, 2),  # Unigrams and bigrams
                stop_words=sklearn_stopwords
            )

            # Cap min_topic_size at 50 to avoid all documents becoming outliers
            # with nr_topics='auto' on large homogeneous datasets
            effective_min_topic_size = min(50, max(2, len(docs_for_embedding) // 20))

            self.topic_model = BERTopic(
                embedding_model=sentence_model,
                vectorizer_model=vectorizer_model,
                min_topic_size=effective_min_topic_size,
                calculate_probabilities=False,
                verbose=False
            )

            # Fit using original documents for embeddings
            topics, probs = self.topic_model.fit_transform(docs_for_embedding)

            return self.topic_model

        except Exception as e:
            print(f"BERTopic fitting error: {e}")
            return None

    def get_topics(self):
        """Extract topics from fitted model."""
        if self.topic_model is None:
            return []

        try:
            topic_info = self.topic_model.get_topic_info()
            topics = []

            for idx, row in topic_info.iterrows():
                if row['Topic'] == -1:  # Skip outlier topic
                    continue

                topic_words = self.topic_model.get_topic(row['Topic'])
                if topic_words:
                    topics.append({
                        'topic_id': row['Topic'],
                        'words': [w for w, _ in topic_words[:self.n_words]],
                        'weights': [float(s) for _, s in topic_words[:self.n_words]],
                        'count': row['Count']
                    })

            return topics[:self.n_topics]

        except Exception as e:
            print(f"Error extracting BERTopic topics: {e}")
            return []


def extract_topics_for_group(texts_by_sdg: dict, method='lda', n_topics=5, n_words=10) -> dict:
    """Extract topics for each SDG from grouped texts.

    Args:
        texts_by_sdg: Dict mapping SDG number to list of activity texts
        method: 'lda' or 'bertopic'
        n_topics: Number of topics to extract per SDG
        n_words: Number of words per topic

    Returns:
        Dict mapping SDG number to list of topics
    """
    topics_by_sdg = {}

    for sdg_num in range(1, 18):
        texts = texts_by_sdg.get(sdg_num, [])

        if not texts:
            topics_by_sdg[sdg_num] = []
            continue

        # Preprocess texts
        preprocessed = [preprocess_text(t) for t in texts]
        preprocessed = [t for t in preprocessed if t.strip()]

        if not preprocessed:
            topics_by_sdg[sdg_num] = []
            continue

        # Create topic modeler
        if method == 'bertopic' and BERTOPIC_AVAILABLE:
            modeler = BERTopicModeler(n_topics=n_topics, n_words=n_words)
        else:
            modeler = LDATopicModeler(n_topics=n_topics, n_words=n_words)

        # Fit model
        modeler.fit(preprocessed)

        # Extract topics
        topics = modeler.get_topics()
        topics_by_sdg[sdg_num] = topics

    return topics_by_sdg


def format_topics(topics: list) -> str:
    """Format topics as a string for CSV output."""
    if not topics:
        return ''

    formatted = []
    for topic in topics:
        words_str = ', '.join(topic['words'][:5])  # Top 5 words
        formatted.append(f"Topic {topic['topic_id']}: {words_str}")

    return ' | '.join(formatted)


def run_bertopic_optimized(files: list, min_activities: int, n_topics: int, n_words: int, output_dir: str):
    """Run BERTopic once per SDG on aggregated data (optimized approach).

    This is much faster than running BERTopic per-council per-SDG.
    """
    print("\n" + "="*60)
    print("Running BERTOPIC topic modeling (optimized - aggregated by SDG)...")
    print("="*60)

    # First, aggregate all texts by SDG across all councils
    print("Aggregating texts by SDG across all councils...")
    all_texts_by_sdg = {sdg: [] for sdg in range(1, 18)}
    council_data = []  # Store council metadata for later assignment

    for csv_path in files:
        filename = os.path.basename(csv_path)
        parsed = parse_filename(filename)

        try:
            df = pd.read_csv(csv_path)
            if 'top_sdg' not in df.columns or 'activity_text' not in df.columns:
                continue
            if len(df) < min_activities:
                continue

            df['top_sdg_int'] = df['top_sdg'].astype(str).str.extract(r'(\d+)')[0].astype(int)

            council_texts_by_sdg = {}
            for sdg_num in range(1, 18):
                texts = df[df['top_sdg_int'] == sdg_num]['activity_text'].tolist()
                if texts:
                    council_texts_by_sdg[sdg_num] = texts
                    all_texts_by_sdg[sdg_num].extend(texts)

            council_data.append({
                'parsed': parsed,
                'texts_by_sdg': council_texts_by_sdg,
                'total_activities': len(df)
            })
        except Exception as e:
            continue

    print(f"Loaded {len(council_data)} councils")
    for sdg in range(1, 18):
        print(f"  SDG {sdg}: {len(all_texts_by_sdg[sdg])} activities")

    # Run BERTopic once per SDG on aggregated data
    print("\nRunning BERTopic for each SDG (17 runs total)...")
    global_topics_by_sdg = {}

    for sdg_num in range(1, 18):
        texts = all_texts_by_sdg[sdg_num]
        if len(texts) < min_activities:
            print(f"  SDG {sdg_num}: Skipped (only {len(texts)} activities)")
            global_topics_by_sdg[sdg_num] = []
            continue

        print(f"  SDG {sdg_num}: Processing {len(texts)} activities...")

        # For BERTopic, use original text for embeddings
        # Preprocessing is only needed for topic word extraction
        original_texts = [str(t) for t in texts if pd.notna(t) and str(t).strip()]

        if len(original_texts) < 2:
            global_topics_by_sdg[sdg_num] = []
            continue

        # Preprocess texts for topic representation (may be empty for some docs)
        preprocessed = [preprocess_text(t) for t in original_texts]

        modeler = BERTopicModeler(n_topics=n_topics, n_words=n_words)
        modeler.fit(preprocessed, original_documents=original_texts)
        topics = modeler.get_topics()
        global_topics_by_sdg[sdg_num] = topics

        if topics:
            print(f"    Found {len(topics)} topics")

    # Now assign topics to each council based on SDG
    print("\nAssigning topics to councils...")
    results = []

    for council in council_data:
        row = {
            'year': council['parsed']['year'],
            'state': council['parsed']['state'],
            'region': council['parsed']['region'],
            'council': council['parsed']['council'],
            'total_activities': council['total_activities']
        }

        for sdg_num in range(1, 18):
            # Use global topics for this SDG
            row[f'topsdg{sdg_num}_topics'] = format_topics(global_topics_by_sdg.get(sdg_num, []))
            row[f'topsdg{sdg_num}_ntopics'] = len(global_topics_by_sdg.get(sdg_num, []))

        results.append(row)

    # Save results - simplified output with just SDG topics
    if global_topics_by_sdg:
        # Create single-row summary with just SDG topics
        summary_row = {}
        for sdg_num in range(1, 18):
            summary_row[f'topsdg{sdg_num}_topics'] = format_topics(global_topics_by_sdg.get(sdg_num, []))
            summary_row[f'topsdg{sdg_num}_ntopics'] = len(global_topics_by_sdg.get(sdg_num, []))

        df_summary = pd.DataFrame([summary_row])
        output_file = os.path.join(output_dir, 'council_topsdg_topics_bertopic.csv')
        df_summary.to_csv(output_file, index=False)
        print(f"Saved BERTopic topics to: {output_file}")
        print(f"Total rows: {len(df_summary)} (global topics)")

    return True


def run_bertopic_by_dimension(files: list, min_activities: int, n_topics: int, n_words: int,
                               output_dir: str, dimension: str, dimension_key: str):
    """Run BERTopic aggregated by a specific dimension (state, region, or year).

    Args:
        files: List of CSV file paths
        min_activities: Minimum activities per SDG
        n_topics: Number of topics per SDG
        n_words: Number of words per topic
        output_dir: Output directory
        dimension: 'state', 'region', or 'year'
        dimension_key: Key name for the dimension in parsed data
    """
    print(f"\n{'='*60}")
    print(f"Running BERTOPIC topic modeling (aggregated by {dimension})...")
    print(f"{'='*60}")

    # First pass: collect all texts by SDG and dimension value
    print(f"Aggregating texts by SDG and {dimension}...")
    all_texts_by_sdg_dim = {}  # {(sdg_num, dim_value): [texts]}
    council_data = []

    for csv_path in files:
        filename = os.path.basename(csv_path)
        parsed = parse_filename(filename)

        try:
            df = pd.read_csv(csv_path)
            if 'top_sdg' not in df.columns or 'activity_text' not in df.columns:
                continue
            if len(df) < min_activities:
                continue

            df['top_sdg_int'] = df['top_sdg'].astype(str).str.extract(r'(\d+)')[0].astype(int)

            dim_value = parsed[dimension_key]

            council_texts_by_sdg = {}
            for sdg_num in range(1, 18):
                texts = df[df['top_sdg_int'] == sdg_num]['activity_text'].tolist()
                if texts:
                    council_texts_by_sdg[sdg_num] = texts
                    key = (sdg_num, dim_value)
                    if key not in all_texts_by_sdg_dim:
                        all_texts_by_sdg_dim[key] = []
                    all_texts_by_sdg_dim[key].extend(texts)

            council_data.append({
                'parsed': parsed,
                'texts_by_sdg': council_texts_by_sdg,
                'total_activities': len(df)
            })
        except Exception as e:
            continue

    print(f"Loaded {len(council_data)} councils")

    # Get unique dimension values
    dim_values = sorted(set(k[1] for k in all_texts_by_sdg_dim.keys()))
    print(f"Found {len(dim_values)} {dimension} values: {dim_values}")

    # Run BERTopic for each (SDG, dimension) combination
    print(f"\nRunning BERTopic for each SDG-{dimension} combination...")
    topics_by_sdg_dim = {}

    for sdg_num in range(1, 18):
        for dim_value in dim_values:
            key = (sdg_num, dim_value)
            texts = all_texts_by_sdg_dim.get(key, [])

            if len(texts) < min_activities:
                topics_by_sdg_dim[key] = []
                continue

            print(f"  SDG {sdg_num}, {dimension}={dim_value}: {len(texts)} activities...")

            original_texts = [str(t) for t in texts if pd.notna(t) and str(t).strip()]
            if len(original_texts) < 2:
                topics_by_sdg_dim[key] = []
                continue

            preprocessed = [preprocess_text(t) for t in original_texts]
            # Filter out empty preprocessed documents
            valid_indices = [i for i, p in enumerate(preprocessed) if p.strip()]
            if len(valid_indices) < 2:
                print(f"    Warning: All documents filtered out after preprocessing for SDG {sdg_num}, {dimension}={dim_value}")
                topics_by_sdg_dim[key] = []
                continue

            # Keep only valid documents for both preprocessed and original
            preprocessed = [preprocessed[i] for i in valid_indices]
            original_texts = [original_texts[i] for i in valid_indices]

            modeler = BERTopicModeler(n_topics=n_topics, n_words=n_words)
            modeler.fit(preprocessed, original_documents=original_texts)
            topics_by_sdg_dim[key] = modeler.get_topics()

    # Assign topics to each council based on their dimension value
    print(f"\nCreating summary by {dimension}...")

    # Create unique rows for each dimension value
    unique_rows = []
    seen_values = set()

    for council in council_data:
        dim_value = council['parsed'][dimension_key]
        if dim_value in seen_values:
            continue
        seen_values.add(dim_value)

        row = {dimension: dim_value}
        for sdg_num in range(1, 18):
            key = (sdg_num, dim_value)
            topics = topics_by_sdg_dim.get(key, [])
            row[f'topsdg{sdg_num}_topics'] = format_topics(topics)
            row[f'topsdg{sdg_num}_ntopics'] = len(topics)

        unique_rows.append(row)

    # Save results (unique dimension values only)
    if unique_rows:
        df_results = pd.DataFrame(unique_rows)
        # Sort by dimension
        df_results = df_results.sort_values([dimension])
        output_file = os.path.join(output_dir, f'council_topsdg_topics_bertopic_{dimension}.csv')
        df_results.to_csv(output_file, index=False)
        print(f"Saved BERTopic topics ({dimension}) to: {output_file}")
        print(f"Total {dimension}s: {len(df_results)}")

    return True


def main():
    parser = argparse.ArgumentParser(description='Topic modeling for SDG activities')
    parser.add_argument('--source', type=str,
                        default='results/nofinancial/by_council/csv',
                        help='Source directory containing alignment CSV files')
    parser.add_argument('--output-dir', type=str,
                        default='results/nofinancial/topics',
                        help='Output directory for topic files')
    parser.add_argument('--method', type=str, choices=['lda', 'bertopic', 'both'],
                        default='lda', help='Topic modeling method (lda, bertopic, or both)')
    parser.add_argument('--num-topics', type=int, default=5,
                        help='Number of topics per SDG (default: 5)')
    parser.add_argument('--num-words', type=int, default=10,
                        help='Number of words per topic (default: 10)')
    parser.add_argument('--min-activities', type=int, default=10,
                        help='Minimum activities per SDG for topic modeling (default: 10)')
    args = parser.parse_args()

    # Check BERTopic availability
    if args.method == 'bertopic' and not BERTOPIC_AVAILABLE:
        print("BERTopic not available. Falling back to LDA.")
        args.method = 'lda'

    # Find all alignment CSV files
    pattern = f'{args.source}/*_alignment.csv'
    files = glob.glob(pattern)

    if not files:
        print(f'No files found matching: {pattern}')
        return

    print(f'Found {len(files)} alignment files')

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    methods = ['lda', 'bertopic'] if args.method == 'both' else [args.method]

    for method in methods:
        if method == 'bertopic' and not BERTOPIC_AVAILABLE:
            continue

        # Use optimized BERTopic approach
        if method == 'bertopic':
            # Run BERTopic aggregated by SDG (all councils combined)
            run_bertopic_optimized(files, args.min_activities, args.num_topics, args.num_words, args.output_dir)

            # Run BERTopic aggregated by SDG and state
            run_bertopic_by_dimension(files, args.min_activities, args.num_topics, args.num_words,
                                      args.output_dir, 'state', 'state')

            # Run BERTopic aggregated by SDG and region
            run_bertopic_by_dimension(files, args.min_activities, args.num_topics, args.num_words,
                                      args.output_dir, 'region', 'region')

            # Run BERTopic aggregated by SDG and year
            run_bertopic_by_dimension(files, args.min_activities, args.num_topics, args.num_words,
                                      args.output_dir, 'year', 'year')
            continue

        # LDA method (per-council processing)
        print(f"\n{'='*60}")
        print(f"Running {method.upper()} topic modeling...")
        print(f"{'='*60}")

        results = []

        for csv_path in files:
            filename = os.path.basename(csv_path)
            parsed = parse_filename(filename)

            try:
                df = pd.read_csv(csv_path)
            except Exception as e:
                continue

            if 'top_sdg' not in df.columns or 'activity_text' not in df.columns:
                continue

            if len(df) < args.min_activities:
                continue

            # Normalize top_sdg to int
            df['top_sdg_int'] = df['top_sdg'].astype(str).str.extract(r'(\d+)')[0].astype(int)

            # Group texts by SDG
            texts_by_sdg = {}
            for sdg_num in range(1, 18):
                texts = df[df['top_sdg_int'] == sdg_num]['activity_text'].tolist()
                if len(texts) >= args.min_activities:
                    texts_by_sdg[sdg_num] = texts

            # Extract topics for each SDG
            topics_by_sdg = extract_topics_for_group(
                texts_by_sdg,
                method=method,
                n_topics=args.num_topics,
                n_words=args.num_words
            )

            # Build result row
            row = {
                'year': parsed['year'],
                'state': parsed['state'],
                'region': parsed['region'],
                'council': parsed['council'],
                'total_activities': len(df)
            }

            # Add topic columns
            for sdg_num in range(1, 18):
                topics = topics_by_sdg.get(sdg_num, [])
                row[f'topsdg{sdg_num}_topics'] = format_topics(topics)
                row[f'topsdg{sdg_num}_ntopics'] = len(topics)

            results.append(row)

        if not results:
            print(f'No results for {method}')
            continue

        # Create DataFrame and save
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values(['year', 'state', 'council'])

        output_file = os.path.join(args.output_dir, f'council_topsdg_topics_{method}.csv')
        df_results.to_csv(output_file, index=False)

        print(f'Saved {method} topics to: {output_file}')
        print(f'Total councils: {len(df_results)}')

        # Create grouped summary
        print(f'\nCreating grouped {method} summary...')

        grouped_results = []

        for year in df_results['year'].unique():
            for state in df_results[df_results['year'] == year]['state'].unique():
                for region in df_results[(df_results['year'] == year) & (df_results['state'] == state)]['region'].unique():
                    group_files = [f for f in files if
                                    parse_filename(f)['year'] == year and
                                    parse_filename(f)['state'] == state and
                                    parse_filename(f)['region'] == region]

                    texts_by_sdg = {sdg: [] for sdg in range(1, 18)}

                    for f in group_files:
                        try:
                            df = pd.read_csv(f)
                            if 'top_sdg' in df.columns and 'activity_text' in df.columns:
                                df['top_sdg_int'] = df['top_sdg'].astype(str).str.extract(r'(\d+)')[0].astype(int)
                                for sdg_num in range(1, 18):
                                    texts = df[df['top_sdg_int'] == sdg_num]['activity_text'].tolist()
                                    texts_by_sdg[sdg_num].extend(texts)
                        except:
                            continue

                    # Extract topics
                    topics_by_sdg = extract_topics_for_group(
                        texts_by_sdg,
                        method=method,
                        n_topics=args.num_topics,
                        n_words=args.num_words
                    )

                    row = {
                        'year': year,
                        'state': state,
                        'region': region
                    }

                    for sdg_num in range(1, 18):
                        topics = topics_by_sdg.get(sdg_num, [])
                        row[f'topsdg{sdg_num}_topics'] = format_topics(topics)

                    grouped_results.append(row)

        df_grouped = pd.DataFrame(grouped_results)
        df_grouped = df_grouped.sort_values(['year', 'state', 'region'])

        grouped_file = os.path.join(args.output_dir, f'council_topsdg_topics_{method}_grouped.csv')
        df_grouped.to_csv(grouped_file, index=False)

        print(f'Saved grouped {method} topics to: {grouped_file}')
        print(f'Total groups: {len(df_grouped)}')

        # Print sample
        print(f'\nSample {method} output:')
        print(df_results[['year', 'state', 'region', 'council', 'topsdg11_topics']].head(3).to_string())


if __name__ == '__main__':
    main()