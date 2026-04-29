#!/usr/bin/env python3
"""Analyze target boost false positives.

For each false positive caused by target boost (SDG activated by boost
but NOT in ground truth), identify which target had the max score,
which embedding variant drove that score, and common keywords.
"""

import sys
import json
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.alignment_engine import AlignmentEngine
from src.sdg_reference import SDGReference
from src.config.sdg_definitions import SDG_DEFINITIONS
from src.config.sdg_target_definitions import SDG_TARGET_DEFINITIONS
from src.config.threshold_config import get_threshold
import pandas as pd

XLSX_PATH = Path("data/external/30015124/Chinese_Development_Finance_SDG_Categorizations_2000-2021.xlsx")
SDG_COLS = [f"SDG{i}" for i in range(1, 18)]


def main():
    # Load data
    print("Loading data...")
    df = pd.read_excel(XLSX_PATH, sheet_name="Extended ver.")
    df = df.dropna(subset=["Description"])
    df = df[df["Description"].str.strip() != ""]
    for col in SDG_COLS:
        df[col] = df[col].fillna(0).astype(int)
    df = df.sample(1000, random_state=42).reset_index(drop=True)
    texts = df["Description"].tolist()
    y_true = df[SDG_COLS].values.astype(int)

    # Run both ST and ST+target_boost
    engine = AlignmentEngine()
    activities = [{"text": t} for t in texts]

    print("Running ST-only alignment...")
    results_st = engine.align_activities(activities, show_progress=False)

    print("Running ST+target_boost alignment...")
    results_boost = engine.align_activities(activities, show_progress=True, target_boost=True)

    # Initialize target embeddings for variant analysis
    ref = engine.sdg_reference
    ref.generate_target_embeddings()
    target_ids = sorted(SDG_TARGET_DEFINITIONS.keys())

    # Variant weights
    VARIANT_WEIGHTS = {"core": 0.50, "context": 0.30, "anchor": 0.20}

    # Identify false positives caused by target boost
    # A false positive from boost = SDG where:
    #   - ST-only: not aligned
    #   - ST+boost: aligned (boost flipped it)
    #   - Ground truth: NOT present
    boost_fp = defaultdict(list)  # sdg_num -> list of {text, target_id, target_text, variant_scores}
    boost_tp = defaultdict(list)  # true positives from boost

    # Also track which targets and variants are responsible
    target_fp_counts = Counter()  # target_id -> count
    variant_fp_contribution = Counter()  # variant -> total weighted contribution to FP scores

    print("\nAnalyzing false positives from target boost...")

    for i in range(len(texts)):
        st_scores = results_st[i]["sdg_scores"]
        boost_scores = results_boost[i]["sdg_scores"]

        for sdg_num in range(1, 18):
            st_aligned = st_scores[sdg_num]["is_aligned"]
            boost_aligned = boost_scores[sdg_num]["is_aligned"]
            gt_present = y_true[i, sdg_num - 1] == 1
            was_boosted = boost_scores[sdg_num].get("target_boost_applied", False)

            # Only care about cases where boost changed the alignment
            if not st_aligned and boost_aligned and was_boosted:
                # Compute target scores for this activity to find which target won
                target_scores = engine._compute_target_scores(
                    ref.encode_text(texts[i]), sdg_num=sdg_num
                )

                # Find top target for this SDG
                sdg_targets = {tid: t for tid, t in target_scores.items()
                               if t["sdg_num"] == sdg_num}
                if not sdg_targets:
                    continue
                top_tid = max(sdg_targets, key=lambda k: sdg_targets[k]["score"])
                top_score = sdg_targets[top_tid]["score"]

                # Compute per-variant scores for the top target
                target_def = SDG_TARGET_DEFINITIONS[top_tid]
                sdg_name = SDG_DEFINITIONS.get(sdg_num, {}).get("name", f"SDG {sdg_num}")
                core_text = target_def["target_text"]
                context_text = f"{target_def['layman_description']} {target_def['detailed_info']}"
                truncated = target_def["target_text"][:100] + ("..." if len(target_def["target_text"]) > 100 else "")
                anchor_text = f"Target {top_tid} of SDG {sdg_num} {sdg_name}: {truncated}"

                activity_emb = ref.encode_text(texts[i])
                core_emb = ref.model.encode(core_text, convert_to_numpy=True)
                context_emb = ref.model.encode(context_text, convert_to_numpy=True)
                anchor_emb = ref.model.encode(anchor_text, convert_to_numpy=True)

                core_sim = float(cosine_similarity(activity_emb.reshape(1, -1), core_emb.reshape(1, -1))[0, 0])
                context_sim = float(cosine_similarity(activity_emb.reshape(1, -1), context_emb.reshape(1, -1))[0, 0])
                anchor_sim = float(cosine_similarity(activity_emb.reshape(1, -1), anchor_emb.reshape(1, -1))[0, 0])

                # Weighted contribution of each variant to the combined score
                total_w = sum(VARIANT_WEIGHTS.values())
                core_contrib = (VARIANT_WEIGHTS["core"] / total_w) * core_sim
                context_contrib = (VARIANT_WEIGHTS["context"] / total_w) * context_sim
                anchor_contrib = (VARIANT_WEIGHTS["anchor"] / total_w) * anchor_sim

                # Determine dominant variant
                contribs = {"core": core_contrib, "context": context_contrib, "anchor": anchor_contrib}
                dominant_variant = max(contribs, key=contribs.get)

                is_fp = not gt_present

                entry = {
                    "text": texts[i][:120],
                    "target_id": top_tid,
                    "target_text": target_def["target_text"][:120],
                    "target_score": round(top_score, 4),
                    "goal_score": round(st_scores[sdg_num]["score"], 4),
                    "threshold": st_scores[sdg_num]["threshold_used"],
                    "variant_scores": {
                        "core": round(core_sim, 4),
                        "context": round(context_sim, 4),
                        "anchor": round(anchor_sim, 4),
                    },
                    "variant_contributions": {
                        "core": round(core_contrib, 4),
                        "context": round(context_contrib, 4),
                        "anchor": round(anchor_contrib, 4),
                    },
                    "dominant_variant": dominant_variant,
                    "is_fp": is_fp,
                }

                if is_fp:
                    boost_fp[sdg_num].append(entry)
                    target_fp_counts[top_tid] += 1
                    variant_fp_contribution[dominant_variant] += 1
                else:
                    boost_tp[sdg_num].append(entry)

    # Print results
    print("\n" + "=" * 80)
    print("TARGET BOOST FALSE POSITIVE ANALYSIS")
    print("=" * 80)

    total_fp = sum(len(v) for v in boost_fp.values())
    total_tp = sum(len(v) for v in boost_tp.values())
    print(f"\nTotal boost activations: {total_fp + total_tp}")
    print(f"  True positives (boost activated correctly): {total_tp}")
    print(f"  False positives (boost activated incorrectly): {total_fp}")
    print(f"  FP rate: {total_fp / (total_fp + total_tp) * 100:.1f}%")

    # Per-variant dominant contribution
    print(f"\n--- Dominant variant in false positives ---")
    for variant in ["core", "context", "anchor"]:
        count = variant_fp_contribution.get(variant, 0)
        pct = count / total_fp * 100 if total_fp > 0 else 0
        print(f"  {variant}: {count} ({pct:.1f}%)")

    # Per-SDG breakdown
    print(f"\n--- Per-SDG false positive breakdown ---")
    print(f"  {'SDG':>4}  {'Name':<35s}  {'FP':>4}  {'TP':>4}  {'FP%':>5}  {'Top FP targets'}")

    for sdg_num in range(1, 18):
        fp_list = boost_fp.get(sdg_num, [])
        tp_list = boost_tp.get(sdg_num, [])
        if not fp_list and not tp_list:
            continue

        total = len(fp_list) + len(tp_list)
        fp_pct = len(fp_list) / total * 100 if total > 0 else 0
        name = SDG_DEFINITIONS.get(sdg_num, {}).get("name", f"SDG {sdg_num}")

        # Most common FP targets for this SDG
        sdg_fp_targets = Counter(e["target_id"] for e in fp_list)
        top_targets = ", ".join(f"{tid}({cnt})" for tid, cnt in sdg_fp_targets.most_common(3))

        print(f"  {sdg_num:3d}  {name:<35s}  {len(fp_list):4d}  {len(tp_list):4d}  {fp_pct:4.0f}%  {top_targets}")

    # Top FP targets overall
    print(f"\n--- Top 15 targets responsible for false positives ---")
    print(f"  {'Target':<8}  {'Count':>5}  {'Core text (truncated)'}")
    for tid, cnt in target_fp_counts.most_common(15):
        tdef = SDG_TARGET_DEFINITIONS[tid]
        print(f"  {tid:<8}  {cnt:5d}  {tdef['target_text'][:90]}")

    # Keyword analysis on FP target texts
    print(f"\n--- Most common words in FP target texts ---")
    import re
    stop_words = {"by", "the", "of", "and", "to", "in", "for", "a", "with", "from",
                  "their", "its", "or", "an", "at", "on", "as", "that", "this", "are",
                  "is", "be", "has", "have", "was", "were", "will", "shall", "may",
                  "also", "such", "including", "other", "than", "into", "through",
                  "which", "where", "who", "whom", "all", "not", "no", "but", "up"}

    word_counts = Counter()
    fp_target_texts = []
    for sdg_num, fp_list in boost_fp.items():
        for entry in fp_list:
            tid = entry["target_id"]
            tdef = SDG_TARGET_DEFINITIONS[tid]
            # Combine all 3 variant texts
            all_text = f"{tdef['target_text']} {tdef['layman_description']} {tdef['detailed_info']}"
            fp_target_texts.append(all_text)
            words = re.findall(r'\b[a-zA-Z]{4,}\b', all_text.lower())
            word_counts.update(w for w in words if w not in stop_words)

    print(f"  Top 30 words across {len(fp_target_texts)} FP target texts:")
    for word, cnt in word_counts.most_common(30):
        print(f"    {word:<20s}  {cnt:5d}")

    # Variant score breakdown for top FP SDGs
    print(f"\n--- Variant score breakdown for top 5 FP SDGs ---")
    top_fp_sdgs = sorted(boost_fp.keys(), key=lambda k: len(boost_fp[k]), reverse=True)[:5]
    for sdg_num in top_fp_sdgs:
        fp_list = boost_fp[sdg_num]
        name = SDG_DEFINITIONS.get(sdg_num, {}).get("name", f"SDG {sdg_num}")
        print(f"\n  SDG {sdg_num} ({name}) — {len(fp_list)} FPs")

        # Average variant scores
        avg_core = np.mean([e["variant_scores"]["core"] for e in fp_list])
        avg_context = np.mean([e["variant_scores"]["context"] for e in fp_list])
        avg_anchor = np.mean([e["variant_scores"]["anchor"] for e in fp_list])
        print(f"    Avg variant scores: core={avg_core:.4f}  context={avg_context:.4f}  anchor={avg_anchor:.4f}")

        # Average variant contributions
        avg_core_c = np.mean([e["variant_contributions"]["core"] for e in fp_list])
        avg_ctx_c = np.mean([e["variant_contributions"]["context"] for e in fp_list])
        avg_anc_c = np.mean([e["variant_contributions"]["anchor"] for e in fp_list])
        print(f"    Avg contributions:   core={avg_core_c:.4f}  context={avg_ctx_c:.4f}  anchor={avg_anc_c:.4f}")

        # Top 3 example FP texts
        print(f"    Example FPs:")
        for e in fp_list[:3]:
            print(f"      text: \"{e['text'][:80]}...\"")
            print(f"      target: {e['target_id']} ({e['dominant_variant']}) score={e['target_score']} goal={e['goal_score']} thresh={e['threshold']}")


if __name__ == "__main__":
    main()