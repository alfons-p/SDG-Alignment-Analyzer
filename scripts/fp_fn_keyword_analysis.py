#!/usr/bin/env python3
"""Analyze false positive and false negative keywords for top 2 models.

For each SDG with many errors (3, 8, 10, 11, 16, 17), identify distinctive
keywords in FP and FN texts using log-odds ratio.

Models analyzed:
  - ST OSDG+ChineseLLM (hybrid-20260329) — best ST model
  - BERT current (multilabel-20260420) — best BERT model

Usage:
    python scripts/fp_fn_keyword_analysis.py
    python scripts/fp_fn_keyword_analysis.py --device cpu
"""

import sys
import json
import argparse
import re
from pathlib import Path
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "optimize_thresholds",
    str(Path(__file__).parent / "optimize_thresholds.py"),
)
_opt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_opt)

precompute_st_scores = _opt.precompute_st_scores
precompute_sdg_bert_scores = _opt.precompute_sdg_bert_scores

from src.alignment_engine import AlignmentEngine
from src.sdg_bert_classifier import SDGBERTClassifier

NUM_SDGS = 17
MODELS_DIR = Path("models")
DATA_PATH = "data/processed/sdganalyzer_ft_labels.csv"
RESULTS_PATH = "results/sdganalyzer_comparison.json"

SDG_NAMES = {
    1: "No Poverty", 2: "Zero Hunger", 3: "Good Health",
    4: "Quality Education", 5: "Gender Equality", 6: "Clean Water",
    7: "Affordable Energy", 8: "Decent Work", 9: "Innovation",
    10: "Reduced Inequalities", 11: "Sustainable Cities",
    12: "Responsible Consumption", 13: "Climate Action",
    14: "Life Below Water", 15: "Life on Land",
    16: "Peace and Justice", 17: "Partnerships",
}

# Focus SDGs with the most errors
FOCUS_SDGS = [3, 8, 10, 11, 16, 17]

# Model configs
ST_MODEL_NAME = "ST OSDG+ChineseLLM (hybrid-20260329)"
ST_MODEL_PATH = str(MODELS_DIR / "sdg-finetuned/sdg-hybrid_enhanced-20260329_154654")
BERT_MODEL_NAME = "BERT current (multilabel-20260420)"
BERT_MODEL_PATH = str(MODELS_DIR / "sdg-bert-multilabel/sdg-bert-multilabel-20260420_120423")

# Stopwords to exclude from keyword analysis
STOPWORDS = set(
    "the a an and or but in on at to for of with by from is it this that "
    "are was were be been being have has had do does did will would shall "
    "should may might can could we they our their its he she his her i me my "
    "you your not no so if as than more also into over then each which when "
    "what where who how all some any both few many most other some such only "
    "own same than too very just about above after again against between "
    "through during before under until up down out off over under again "
    "further then once here there where why how what which who whom these "
    "those am are was were been being have has had did does doing would "
    "should could ought im its per via due one two three four five six "
    "seven eight nine ten new also however therefore thus hence moreover "
    "nevertheless nonetheless accordingly consequently meanwhile otherwise "
    "rather instead indeed anyway amongst amongst regarding concerning "
    "throughout within without among upon except apart alongside towards "
    "onto since until whether whereas whereby wherein wherever whoever "
    "whomever whichever whichever wherever whomever notwithstanding"
    .split()
)


def tokenize(text: str) -> list:
    """Simple lowercase word tokenization."""
    text = text.lower()
    # Remove punctuation except hyphens within words
    text = re.sub(r'[^\w\s\-]', ' ', text)
    words = text.split()
    # Keep hyphenated words, split on remaining hyphens
    result = []
    for w in words:
        if '-' in w and len(w) > 1:
            # Keep the hyphenated form and also add parts
            result.append(w)
        else:
            result.append(w)
    return [w for w in result if len(w) > 2 and w not in STOPWORDS]


def compute_log_odds_keywords(target_texts, complement_texts, min_count=3, top_n=10):
    """Compute distinctive keywords using log-odds ratio.

    For each word, compute: log-odds ratio = log((freq_in_target + 0.5) / (target_total + 0.5))
                                              - log((freq_in_complement + 0.5) / (complement_total + 0.5))

    Also compute frequency ratio for interpretability.
    """
    target_words = Counter()
    complement_words = Counter()
    target_doc_freq = Counter()  # number of docs containing the word
    complement_doc_freq = Counter()

    for text in target_texts:
        words = set(tokenize(text))
        target_words.update(tokenize(text))
        target_doc_freq.update(words)

    for text in complement_texts:
        words = set(tokenize(text))
        complement_words.update(tokenize(text))
        complement_doc_freq.update(words)

    target_total = sum(target_words.values())
    complement_total = sum(complement_words.values())

    # Get all candidate words (min count in target)
    candidates = {w for w, c in target_words.items() if c >= min_count}

    results = []
    for word in sorted(candidates):
        t_count = target_words[word]
        c_count = complement_words[word]

        # Log-odds ratio
        t_freq = (t_count + 0.5) / (target_total + 0.5)
        c_freq = (c_count + 0.5) / (complement_total + 0.5)
        log_odds = np.log(t_freq) - np.log(c_freq)

        # Frequency ratio (with smoothing)
        freq_ratio = t_count / max(c_count, 1)

        # Doc frequency ratio
        t_docs = target_doc_freq[word]
        c_docs = complement_doc_freq[word]
        t_doc_pct = t_docs / len(target_texts) if target_texts else 0
        c_doc_pct = c_docs / len(complement_texts) if complement_texts else 0

        results.append({
            'word': word,
            'target_count': t_count,
            'complement_count': c_count,
            'log_odds': log_odds,
            'freq_ratio': freq_ratio,
            'target_doc_pct': t_doc_pct,
            'complement_doc_pct': c_doc_pct,
        })

    # Sort by log-odds descending
    results.sort(key=lambda x: x['log_odds'], reverse=True)
    return results[:top_n]


def load_sdganalyzer_labels(path=DATA_PATH):
    """Load sdganalyzer labels and pivot to multi-label binary matrix."""
    df = pd.read_csv(path)
    texts = df["text"].unique().tolist()
    text_to_idx = {t: i for i, t in enumerate(texts)}
    n = len(texts)
    labels = np.zeros((n, NUM_SDGS), dtype=np.int32)
    for _, row in df.iterrows():
        idx = text_to_idx[row["text"]]
        labels[idx, int(row["sdg"]) - 1] = 1
    return texts, labels


def apply_thresholds(scores, thresholds):
    """Apply per-SDG thresholds with min-1-positive fallback."""
    y_pred = np.zeros_like(scores, dtype=np.int32)
    for sdg_num in range(1, 18):
        y_pred[:, sdg_num - 1] = (scores[:, sdg_num - 1] >= thresholds[sdg_num]).astype(int)
    # Min 1 positive
    for i in range(len(y_pred)):
        if y_pred[i].sum() == 0:
            y_pred[i, scores[i].argmax()] = 1
    return y_pred


def main():
    parser = argparse.ArgumentParser(description="FP/FN keyword analysis")
    parser.add_argument("--device", default=None, help="Force device (cpu/mps/cuda)")
    parser.add_argument("--top-n", type=int, default=10, help="Top N keywords to show")
    parser.add_argument("--min-count", type=int, default=3, help="Min occurrences in target set")
    args = parser.parse_args()

    # Load labels
    print("Loading sdganalyzer labels...")
    texts, labels = load_sdganalyzer_labels()
    n = len(texts)
    n_pos = labels.sum(axis=1)
    print(f"  {n} texts, {labels.sum()} positive labels")
    print(f"  Labels per text: min={n_pos.min()}, max={n_pos.max()}, mean={n_pos.mean():.2f}")

    # Load benchmark results for thresholds
    print("Loading benchmark thresholds...")
    with open(RESULTS_PATH) as f:
        all_results = json.load(f)

    # Get thresholds for the two models
    st_thresholds = {}
    bert_thresholds = {}
    for sdg_str, data in all_results[ST_MODEL_NAME]["per_sdg"].items():
        st_thresholds[int(sdg_str)] = data["threshold"]
    for sdg_str, data in all_results[BERT_MODEL_NAME]["per_sdg"].items():
        bert_thresholds[int(sdg_str)] = data["threshold"]

    # === ST model ===
    print(f"\nLoading ST model: {ST_MODEL_PATH}")
    st_engine = AlignmentEngine(model_name=ST_MODEL_PATH)
    st_scores = precompute_st_scores(st_engine, texts)
    st_pred = apply_thresholds(st_scores, st_thresholds)

    # === BERT model ===
    print(f"\nLoading BERT model: {BERT_MODEL_PATH}")
    bert_classifier = SDGBERTClassifier(model_name=BERT_MODEL_PATH, device=args.device)
    bert_scores = precompute_sdg_bert_scores(bert_classifier, texts)
    bert_pred = apply_thresholds(bert_scores, bert_thresholds)

    # === Analysis ===
    focus_sdgs = FOCUS_SDGS
    models = [
        (ST_MODEL_NAME, st_pred),
        (BERT_MODEL_NAME, bert_pred),
    ]

    for model_name, pred in models:
        print("\n" + "=" * 100)
        print(f"  MODEL: {model_name}")
        print("=" * 100)

        for sdg in focus_sdgs:
            sdg_idx = sdg - 1
            sdg_name = SDG_NAMES[sdg]

            # Ground truth and predictions for this SDG
            y_true = labels[:, sdg_idx]
            y_hat = pred[:, sdg_idx]

            tp_mask = (y_true == 1) & (y_hat == 1)
            fp_mask = (y_true == 0) & (y_hat == 1)
            fn_mask = (y_true == 1) & (y_hat == 0)
            tn_mask = (y_true == 0) & (y_hat == 0)

            n_tp = tp_mask.sum()
            n_fp = fp_mask.sum()
            n_fn = fn_mask.sum()
            n_tn = tn_mask.sum()

            fp_texts = [texts[i] for i in range(n) if fp_mask[i]]
            fn_texts = [texts[i] for i in range(n) if fn_mask[i]]
            # For FP: compare against TN+TP (correctly classified for this SDG)
            correct_texts = [texts[i] for i in range(n) if tp_mask[i] or tn_mask[i]]
            # For FN: compare against TP (correctly identified positives)
            tp_texts = [texts[i] for i in range(n) if tp_mask[i]]

            threshold = st_thresholds[sdg] if "ST" in model_name else bert_thresholds[sdg]

            print(f"\n  --- SDG {sdg}: {sdg_name} (threshold={threshold:.3f}) ---")
            print(f"      TP={n_tp}, FP={n_fp}, FN={n_fn}, TN={n_tn}")

            if n_fp > 0:
                fp_keywords = compute_log_odds_keywords(
                    fp_texts, correct_texts,
                    min_count=args.min_count, top_n=args.top_n
                )
                print(f"\n      FALSE POSITIVE keywords (model predicts SDG {sdg}, annotators don't):")
                print(f"      {'Word':<25} {'LogOdds':>8} {'FreqRatio':>10} {'FP_docs%':>9} {'Other_docs%':>11} {'FP_cnt':>7} {'Other_cnt':>10}")
                for kw in fp_keywords:
                    print(f"      {kw['word']:<25} {kw['log_odds']:>8.3f} {kw['freq_ratio']:>10.2f} "
                          f"{kw['target_doc_pct']:>9.1%} {kw['complement_doc_pct']:>11.1%} "
                          f"{kw['target_count']:>7d} {kw['complement_count']:>10d}")
            else:
                print(f"\n      FALSE POSITIVE keywords: None (0 FP samples)")

            if n_fn > 0:
                fn_keywords = compute_log_odds_keywords(
                    fn_texts, tp_texts,
                    min_count=args.min_count, top_n=args.top_n
                )
                print(f"\n      FALSE NEGATIVE keywords (annotators label SDG {sdg}, model misses):")
                print(f"      {'Word':<25} {'LogOdds':>8} {'FreqRatio':>10} {'FN_docs%':>9} {'TP_docs%':>11} {'FN_cnt':>7} {'TP_cnt':>10}")
                for kw in fn_keywords:
                    print(f"      {kw['word']:<25} {kw['log_odds']:>8.3f} {kw['freq_ratio']:>10.2f} "
                          f"{kw['target_doc_pct']:>9.1%} {kw['complement_doc_pct']:>11.1%} "
                          f"{kw['target_count']:>7d} {kw['complement_count']:>10d}")
            else:
                print(f"\n      FALSE NEGATIVE keywords: None (0 FN samples)")

    # === Summary comparison table ===
    print("\n\n" + "=" * 100)
    print("  SUMMARY: ERROR COUNTS PER SDG PER MODEL")
    print("=" * 100)
    print(f"\n  {'SDG':<4} {'Name':<24} ", end="")
    for model_name, _ in models:
        short = model_name.split("(")[0].strip()
        print(f"{'FP('+short+')':>14} {'FN('+short+')':>14} ", end="")
    print()
    print(f"  {'-'*4} {'-'*24} ", end="")
    for _ in models:
        print(f"{'-'*14} {'-'*14} ", end="")
    print()

    for sdg in focus_sdgs:
        sdg_idx = sdg - 1
        name = SDG_NAMES[sdg]
        print(f"  {sdg:<4} {name:<24} ", end="")
        for model_name, pred in models:
            y_true = labels[:, sdg_idx]
            y_hat = pred[:, sdg_idx]
            n_fp = int(((y_true == 0) & (y_hat == 1)).sum())
            n_fn = int(((y_true == 1) & (y_hat == 0)).sum())
            print(f"{n_fp:>14d} {n_fn:>14d} ", end="")
        print()


if __name__ == "__main__":
    main()