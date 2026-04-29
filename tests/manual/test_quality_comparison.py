#!/usr/bin/env python3
"""Detailed comparison of activity extraction quality."""

import json
from pathlib import Path

def load_json(path):
    with open(path) as f:
        return json.load(f)

def analyze_quality(activities, label):
    print(f"\n{'='*70}")
    print(f"{label}")
    print(f"{'='*70}")

    print(f"\nTotal activities: {len(activities)}")

    if not activities:
        return

    # Word count distribution
    word_counts = [a.get("word_count", 0) for a in activities]
    print(f"\nWord Count Distribution:")
    print(f"  Min: {min(word_counts)}, Max: {max(word_counts)}")
    print(f"  Avg: {sum(word_counts)/len(word_counts):.1f}")

    buckets = {
        "15-30 words": 0,
        "31-50 words": 0,
        "51-75 words": 0,
        "76-100 words": 0,
        "100+ words": 0
    }
    for wc in word_counts:
        if wc <= 30:
            buckets["15-30 words"] += 1
        elif wc <= 50:
            buckets["31-50 words"] += 1
        elif wc <= 75:
            buckets["51-75 words"] += 1
        elif wc <= 100:
            buckets["76-100 words"] += 1
        else:
            buckets["100+ words"] += 1

    for bucket, count in buckets.items():
        pct = count / len(word_counts) * 100
        print(f"  {bucket}: {count} ({pct:.1f}%)")

    # Content quality checks
    print(f"\nContent Quality Indicators:")

    # Bullets
    bullet_count = sum(1 for a in activities if "•" in a.get("text", ""))
    print(f"  With embedded bullets: {bullet_count}")

    # TOC-like content
    toc_markers = ['contents', 'table of contents', 'introduction 4', 'message from']
    toc_count = sum(1 for a in activities if any(m in a.get("text", "").lower()[:100] for m in toc_markers))
    print(f"  TOC-like content: {toc_count}")

    # Acknowledgment text
    ack_markers = ['we acknowledge', 'we honour', 'traditional owners', 'spiritual connection']
    ack_count = sum(1 for a in activities if any(m in a.get("text", "").lower() for m in ack_markers))
    print(f"  Acknowledgment statements: {ack_count}")

    # Fragmented/missing start
    fragmented = sum(1 for a in activities if a.get("text", "").startswith(("•", "-", "given", "used to", "and", "or", "but")))
    print(f"  Fragmented starts: {fragmented}")

    # Confidence distribution
    confidences = [a.get("confidence", 0) for a in activities]
    print(f"\nConfidence Scores:")
    print(f"  Avg: {sum(confidences)/len(confidences):.2f}")
    high_conf = sum(1 for c in confidences if c >= 0.8)
    print(f"  High confidence (≥0.8): {high_conf} ({high_conf/len(confidences)*100:.1f}%)")

    # Sample activities by length
    print(f"\n--- Sample Activities ---")

    # Short activity
    short = [a for a in activities if 15 <= a.get("word_count", 0) <= 25]
    if short:
        print(f"\nShort activity (15-25 words):")
        print(f"  \"{short[0].get('text', '')}\"")

    # Medium activity
    medium = [a for a in activities if 40 <= a.get("word_count", 0) <= 60]
    if medium:
        print(f"\nMedium activity (40-60 words):")
        print(f"  \"{medium[0].get('text', '')[:150]}...\"")

    # Long activity
    long = [a for a in activities if a.get("word_count", 0) >= 80]
    if long:
        print(f"\nLong activity (80+ words):")
        print(f"  \"{long[0].get('text', '')[:200]}...\"")

def main():
    # Load existing result
    existing_path = Path("results/by_council/V1_Alpine Shire Council Annual Report 2022-23 - complete_alignment.json")
    if existing_path.exists():
        existing = load_json(existing_path)
        analyze_quality(existing.get("activities", []), "EXISTING (Before Fixes)")

    # Load new result
    new_path = Path("test_new_extraction.json")
    if new_path.exists():
        new = load_json(new_path)
        analyze_quality(new.get("activities", []), "NEW (After Fixes)")

    # Side-by-side comparison of specific problematic patterns
    print(f"\n{'='*70}")
    print("PROBLEMATIC PATTERN COMPARISON")
    print(f"{'='*70}")

    if existing_path.exists() and new_path.exists():
        old_acts = existing.get("activities", [])
        new_acts = new.get("activities", [])

        # Find specific examples
        print("\n1. EMBEDDED BULLETS:")
        old_bullets = [a for a in old_acts if "•" in a.get("text", "")][:2]
        print(f"   Before: {len([a for a in old_acts if '•' in a.get('text', '')])} activities with bullets")
        if old_bullets:
            print(f"   Example: {old_bullets[0].get('text', '')[:150]}...")
        print(f"   After: {len([a for a in new_acts if '•' in a.get('text', '')])} activities with bullets")

        print("\n2. FRAGMENTED STARTS ('used to...', 'given...'):")
        old_frag = [a for a in old_acts if a.get("text", "").startswith(("used to", "given"))][:2]
        new_frag = [a for a in new_acts if a.get("text", "").startswith(("used to", "given"))][:2]
        print(f"   Before: {len([a for a in old_acts if a.get('text', '').startswith(('used to', 'given'))])} fragmented")
        if old_frag:
            print(f"   Example: {old_frag[0].get('text', '')[:150]}...")
        print(f"   After: {len([a for a in new_acts if a.get('text', '').startswith(('used to', 'given'))])} fragmented")
        if new_frag:
            print(f"   Example: {new_frag[0].get('text', '')[:150]}...")

        print("\n3. VERY LONG ACTIVITIES (>200 words):")
        old_long = [a for a in old_acts if a.get("word_count", 0) > 200]
        new_long = [a for a in new_acts if a.get("word_count", 0) > 200]
        print(f"   Before: {len(old_long)} activities >200 words")
        print(f"   After: {len(new_long)} activities >200 words")
        if old_long:
            print(f"   Before example: {old_long[0].get('text', '')[:200]}...")

        print("\n4. ACKNOWLEDGMENTS:")
        ack_text = 'we acknowledge'
        old_ack = [a for a in old_acts if ack_text in a.get("text", "").lower()]
        new_ack = [a for a in new_acts if ack_text in a.get("text", "").lower()]
        print(f"   Before: {len(old_ack)} acknowledgment statements")
        print(f"   After: {len(new_ack)} acknowledgment statements")

if __name__ == "__main__":
    main()
