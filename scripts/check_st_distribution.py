#!/usr/bin/env python3
"""Check raw ST cosine similarity score distribution against real activities.

Compares two engines:
  1. AlignmentEngine   — pure ST (cosine similarity, no ensemble)
  2. HybridAlignmentEngine — ST + sdgBERT ensemble + keyword boosting + bias corrections
"""

import sys
import os
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Disable tokenizers parallelism
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from src.activity_extractor import ActivityExtractor
from src.alignment_engine import AlignmentEngine
from src.hybrid_alignment_engine import HybridAlignmentEngine

# ── Extract activities ──────────────────────────────────────────────────────

pdfs = sorted(Path("data/raw").rglob("*.pdf"))
print(f"Total PDFs: {len(pdfs)}")

sample_pdfs = pdfs[:5]
print(f"Checking {len(sample_pdfs)} PDFs: {[p.name for p in sample_pdfs]}")

print("\nExtracting activities (BERT classifier)...")
extractor = ActivityExtractor(
    min_activity_length=20,
    max_activity_length=500,
    use_bert_classifier=True,
)
activities = []
for pdf_path in sample_pdfs:
    result = extractor.extract_from_pdf(str(pdf_path))
    activities.extend(result["activities"])
    print(f"  {pdf_path.name}: {len(result['activities'])} activities")

print(f"\nTotal activities: {len(activities)}")
for i, act in enumerate(activities[:3]):
    text = act.get("text", "")[:80]
    print(f"  [{i}] {text}...")

# ── Engine 1: AlignmentEngine (ST-only) ─────────────────────────────────────

print(f"\n{'='*60}")
print("ENGINE 1: AlignmentEngine (ST-only)")
print("="*60)

engine_st = AlignmentEngine()

st_scores = []  # (activity_text, [sdg1, ..., sdg17])
for act in activities:
    text = act["text"]
    result = engine_st.align_activity(text, return_top_n=None)
    sdg_scores = [result["sdg_scores"][sdg]["score"] for sdg in range(1, 18)]
    st_scores.append((text, sdg_scores))

# ── Engine 2: HybridAlignmentEngine ─────────────────────────────────────────

print(f"\n{'='*60}")
print("ENGINE 2: HybridAlignmentEngine (ST + sdgBERT ensemble)")
print("="*60)

engine_hybrid = HybridAlignmentEngine(
    ensemble_mode="weighted",
    sdg_bert_weight=0.55,
    st_weight=0.45,
)

hybrid_scores = []  # (activity_text, [sdg1, ..., sdg17])
for act in activities:
    text = act["text"]
    result = engine_hybrid.align_activity(text, return_top_n=None)
    sdg_scores = [result["sdg_scores"][sdg]["score"] for sdg in range(1, 18)]
    hybrid_scores.append((text, sdg_scores))

# ── Aggregate helpers ───────────────────────────────────────────────────────

def aggregate(all_scores):
    """Compute per-activity stats from list of (text, [17 scores])."""
    all_flat = []
    all_max = []
    all_mean = []
    all_top_sdg = []
    for text, scores in all_scores:
        flat = np.array(scores)
        all_flat.extend(flat)
        all_max.append(flat.max())
        all_mean.append(flat.mean())
        top_idx = flat.argmax()
        all_top_sdg.append(top_idx + 1)  # 1-indexed
    return np.array(all_flat), np.array(all_max), np.array(all_mean), np.array(all_top_sdg)


def print_stats(label, flat, max_scores, mean_scores, top_sdg):
    print(f"\n--- {label} ---")
    print(f"All scores:")
    print(f"  min={flat.min():.4f}  max={flat.max():.4f}  mean={flat.mean():.4f}  median={np.median(flat):.4f}  std={flat.std():.4f}")
    print(f"Max per activity (top-1 SDG):")
    print(f"  min={max_scores.min():.4f}  max={max_scores.max():.4f}  mean={max_scores.mean():.4f}  median={np.median(max_scores):.4f}")
    print(f"Mean per activity (avg across SDGs):")
    print(f"  min={mean_scores.min():.4f}  max={mean_scores.max():.4f}  mean={mean_scores.mean():.4f}  median={np.median(mean_scores):.4f}")


def print_distribution(label, flat):
    bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    bin_labels = ["0.0-0.1", "0.1-0.2", "0.2-0.3", "0.3-0.4", "0.4-0.5",
                  "0.5-0.6", "0.6-0.7", "0.7-0.8", "0.8-0.9", "0.9-1.0"]
    print(f"\n--- {label} score distribution ---")
    for i, (lo, hi) in enumerate(zip(bins[:-1], bins[1:])):
        count = int(np.sum((flat >= lo) & (flat < hi)))
        pct = count / len(flat) * 100
        bar = "#" * int(pct / 2)
        print(f"  {bin_labels[i]:>9}: {count:5d} ({pct:5.1f}%) {bar}")


# ── Compute stats ───────────────────────────────────────────────────────────

st_flat, st_max, st_mean, st_top = aggregate(st_scores)
hybrid_flat, hybrid_max, hybrid_mean, hybrid_top = aggregate(hybrid_scores)

print("\n" + "="*60)
print("COMPARISON: ST-only vs Hybrid")
print("="*60)

print_stats("ST-only", st_flat, st_max, st_mean, st_top)
print_stats("Hybrid", hybrid_flat, hybrid_max, hybrid_mean, hybrid_top)

print_distribution("ST-only", st_flat)
print_distribution("Hybrid", hybrid_flat)

# ── Per-SDG comparison ──────────────────────────────────────────────────────

sdg_names = {
    1: "No Poverty", 2: "Zero Hunger", 3: "Good Health", 4: "Quality Education",
    5: "Gender Equality", 6: "Clean Water", 7: "Affordable Energy",
    8: "Decent Work", 9: "Innovation", 10: "Reduced Inequalities",
    11: "Sustainable Cities", 12: "Responsible Consumption", 13: "Climate Action",
    14: "Life Below Water", 15: "Life on Land", 16: "Peace & Justice",
    17: "Partnerships"
}

print("\n" + "="*60)
print("PER-SDG COMPARISON (max score across all activities)")
print("="*60)
print(f"{'SDG':>4s}  {'Name':<22s}  {'ST-max':>7s}  {'Hyb-max':>7s}  {'ST-top1':>8s}  {'Hyb-top1':>9s}")
print("-" * 75)
for sdg_num in range(1, 18):
    st_sdg = np.array([scores[sdg_num - 1] for _, scores in st_scores])
    hyb_sdg = np.array([scores[sdg_num - 1] for _, scores in hybrid_scores])
    st_top_count = (st_top == sdg_num).sum()
    hyb_top_count = (hybrid_top == sdg_num).sum()
    print(f"  {sdg_num:2d}  {sdg_names[sdg_num]:<22s}  {st_sdg.max():7.4f}  {hyb_sdg.max():7.4f}  {st_top_count:8d}  {hyb_top_count:9d}")

# ── Top-1 agreement ─────────────────────────────────────────────────────────

print("\n" + "="*60)
print("TOP-1 SDG AGREEMENT")
print("="*60)
agreements = (st_top == hybrid_top).sum()
total = len(st_top)
print(f"  Same top-1 SDG: {agreements}/{total} ({agreements/total*100:.1f}%)")
print(f"  Different:")
for sdg_num in range(1, 18):
    st_only = int(((st_top == sdg_num) & (hybrid_top != sdg_num)).sum())
    if st_only > 0:
        print(f"    ST top={sdg_num} (Hybrid disagrees): {st_only}")

# ── Score differences ───────────────────────────────────────────────────────

print("\n" + "="*60)
print("SCORE DIFFERENCES (Hybrid - ST)")
print("="*60)
diffs = []
for (_, st_s), (_, hyb_s) in zip(st_scores, hybrid_scores):
    for i in range(17):
        diffs.append(hyb_s[i] - st_s[i])
diffs = np.array(diffs)
print(f"  mean diff: {diffs.mean():.4f}")
print(f"  std diff:  {diffs.std():.4f}")
print(f"  min diff:  {diffs.min():.4f}")
print(f"  max diff:  {diffs.max():.4f}")

# ── Top 10 highest scores per engine ────────────────────────────────────────

print("\n" + "="*60)
print("TOP 10 HIGHEST SCORES — ST-only")
print("="*60)
top10_st = sorted(st_scores, key=lambda x: max(x[1]), reverse=True)[:10]
for i, (text, scores) in enumerate(top10_st):
    top_score = max(scores)
    top_sdg = scores.index(top_score) + 1
    preview = text[:60] + "..." if len(text) > 60 else text
    print(f"  [{i+1}] SDG {top_sdg}: {top_score:.4f} — '{preview}'")

print("\n" + "="*60)
print("TOP 10 HIGHEST SCORES — Hybrid")
print("="*60)
top10_hyb = sorted(hybrid_scores, key=lambda x: max(x[1]), reverse=True)[:10]
for i, (text, scores) in enumerate(top10_hyb):
    top_score = max(scores)
    top_sdg = scores.index(top_score) + 1
    preview = text[:60] + "..." if len(text) > 60 else text
    print(f"  [{i+1}] SDG {top_sdg}: {top_score:.4f} — '{preview}'")
