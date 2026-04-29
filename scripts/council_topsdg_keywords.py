#!/usr/bin/env python3
"""Extract top keywords for each SDG from council alignment files.

This script:
1. Reads all {state}_{council}_{region}_{year}_alignment.csv files
2. Groups activity_text by council/year/state/region AND top_sdg
3. Extracts top keywords using TF-IDF for each SDG grouping
4. Outputs a summary CSV with year, state, region, council, and top keywords per SDG

Usage:
    python scripts/council_topsdg_keywords.py
    python scripts/council_topsdg_keywords.py --top-n 20
"""

import argparse
import glob
import os
import re
import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer

# Check for spaCy lemmatization
SPACY_AVAILABLE = False
try:
    import spacy
    nlp = spacy.load('en_core_web_sm', disable=['parser', 'ner'])
    SPACY_AVAILABLE = True
except (ImportError, OSError):
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
    """Clean and preprocess text for keyword extraction with lemmatization."""
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


def extract_keywords_tfidf(documents: list, top_n: int = 15) -> list:
    """Extract top keywords using TF-IDF from a list of documents.

    Args:
        documents: List of preprocessed text documents
        top_n: Number of top keywords to return

    Returns:
        List of (keyword, score) tuples
    """
    if not documents or all(doc.strip() == '' for doc in documents):
        return []

    # Filter empty documents
    documents = [doc for doc in documents if doc.strip()]

    if not documents:
        return []

    try:
        # Use TF-IDF with unigrams, bigrams, and trigrams
        vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 3),
            min_df=1,
            max_df=0.95,
            stop_words='english'
        )

        tfidf_matrix = vectorizer.fit_transform(documents)

        # Get feature names and scores
        feature_names = vectorizer.get_feature_names_out()

        # Sum TF-IDF scores across all documents
        scores = tfidf_matrix.sum(axis=0).A1

        # Get top keywords
        top_indices = scores.argsort()[-top_n:][::-1]
        keywords = [(feature_names[i], round(scores[i], 3)) for i in top_indices]

        return keywords

    except Exception as e:
        # Fallback to frequency-based extraction if TF-IDF fails
        return extract_keywords_frequency(documents, top_n)


def extract_keywords_frequency(documents: list, top_n: int = 15) -> list:
    """Extract top keywords using frequency count (fallback method).

    Args:
        documents: List of preprocessed text documents
        top_n: Number of top keywords to return

    Returns:
        List of (keyword, count) tuples
    """
    if not documents:
        return []

    # Combine all documents
    all_words = []
    for doc in documents:
        if doc.strip():
            all_words.extend(doc.split())

    # Count word frequencies
    word_counts = Counter(all_words)

    # Get top keywords
    keywords = [(word, count) for word, count in word_counts.most_common(top_n)]

    return keywords


def extract_keywords_for_group(texts_by_sdg: dict, top_n: int = 15) -> dict:
    """Extract keywords for each SDG from grouped texts.

    Args:
        texts_by_sdg: Dict mapping SDG number to list of activity texts
        top_n: Number of keywords per SDG

    Returns:
        Dict mapping SDG number to list of keywords
    """
    keywords_by_sdg = {}

    for sdg_num in range(1, 18):
        texts = texts_by_sdg.get(sdg_num, [])

        if not texts:
            keywords_by_sdg[sdg_num] = []
            continue

        # Preprocess texts
        preprocessed = [preprocess_text(t) for t in texts]

        # Extract keywords
        keywords = extract_keywords_tfidf(preprocessed, top_n)

        keywords_by_sdg[sdg_num] = keywords

    return keywords_by_sdg


def main():
    parser = argparse.ArgumentParser(description='Extract top keywords for each SDG from council alignments')
    parser.add_argument('--source', type=str,
                        default='results/nofinancial/by_council/csv',
                        help='Source directory containing alignment CSV files')
    parser.add_argument('--output', type=str,
                        default='results/nofinancial/council_topsdg_keywords.csv',
                        help='Output CSV file path')
    parser.add_argument('--top-n', type=int, default=15,
                        help='Number of top keywords per SDG (default: 15)')
    parser.add_argument('--min-activities', type=int, default=1,
                        help='Minimum number of activities to include (default: 1)')
    args = parser.parse_args()

    # Find all alignment CSV files
    pattern = f'{args.source}/*_alignment.csv'
    files = glob.glob(pattern)

    if not files:
        print(f'No files found matching: {pattern}')
        return

    print(f'Found {len(files)} alignment files')

    # Process each file
    results = []

    for csv_path in files:
        filename = os.path.basename(csv_path)
        parsed = parse_filename(filename)

        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            print(f'Error reading {csv_path}: {e}')
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
            if texts:
                texts_by_sdg[sdg_num] = texts

        # Extract keywords for each SDG
        keywords_by_sdg = extract_keywords_for_group(texts_by_sdg, args.top_n)

        # Build result row
        row = {
            'year': parsed['year'],
            'state': parsed['state'],
            'region': parsed['region'],
            'council': parsed['council'],
            'total_activities': len(df)
        }

        # Add keyword columns
        for sdg_num in range(1, 18):
            keywords = keywords_by_sdg.get(sdg_num, [])
            # Store as comma-separated string
            row[f'topsdg{sdg_num}_keywords'] = ', '.join([kw for kw, _ in keywords]) if keywords else ''
            # Also store scores
            row[f'topsdg{sdg_num}_scores'] = ', '.join([f'{kw}:{score}' for kw, score in keywords]) if keywords else ''

        results.append(row)

    if not results:
        print('No results to save')
        return

    # Create DataFrame
    df_results = pd.DataFrame(results)

    # Sort by year, state, council
    df_results = df_results.sort_values(['year', 'state', 'council'])

    # Save to CSV
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    df_results.to_csv(args.output, index=False)

    print(f'Saved keywords summary to: {args.output}')
    print(f'Total councils: {len(df_results)}')

    # Also create a grouped summary (aggregated by year, state, region)
    print('\nCreating grouped summary...')

    # For grouped summary, we need to aggregate keywords differently
    # We'll read all files again and group by year/state/region
    grouped_results = []

    for year in df_results['year'].unique():
        for state in df_results[df_results['year'] == year]['state'].unique():
            for region in df_results[(df_results['year'] == year) & (df_results['state'] == state)]['region'].unique():
                # Get all texts for this group
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

                # Extract keywords for each SDG
                keywords_by_sdg = extract_keywords_for_group(texts_by_sdg, args.top_n)

                row = {
                    'year': year,
                    'state': state,
                    'region': region
                }

                for sdg_num in range(1, 18):
                    keywords = keywords_by_sdg.get(sdg_num, [])
                    row[f'topsdg{sdg_num}_keywords'] = ', '.join([kw for kw, _ in keywords]) if keywords else ''

                grouped_results.append(row)

    # Save grouped summary
    df_grouped = pd.DataFrame(grouped_results)
    df_grouped = df_grouped.sort_values(['year', 'state', 'region'])
    grouped_output = args.output.replace('.csv', '_grouped.csv')
    df_grouped.to_csv(grouped_output, index=False)

    print(f'Saved grouped keywords to: {grouped_output}')
    print(f'Total groups: {len(df_grouped)}')

    # Print sample output
    print('\nSample output (first 3 rows):')
    print(df_results[['year', 'state', 'region', 'council', 'topsdg1_keywords', 'topsdg11_keywords']].head(3).to_string())


if __name__ == '__main__':
    main()