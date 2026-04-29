#!/usr/bin/env python3
"""Test script to compare activity extraction before and after fixes."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.activity_extractor import ActivityExtractor


def analyze_activities(activities, label):
    """Analyze extracted activities and print statistics."""
    print(f"\n{'='*60}")
    print(f"{label}")
    print(f"{'='*60}")

    print(f"\nTotal activities: {len(activities)}")

    if not activities:
        print("No activities extracted!")
        return

    # Word count distribution
    word_counts = [a.get("word_count", 0) for a in activities]
    print(f"\nWord count stats:")
    print(f"  Min: {min(word_counts)}")
    print(f"  Max: {max(word_counts)}")
    print(f"  Avg: {sum(word_counts)/len(word_counts):.1f}")

    # Very long activities (potential boundary issues)
    long_activities = [a for a in activities if a.get("word_count", 0) > 100]
    print(f"\nActivities > 100 words: {len(long_activities)}")

    # Activities with bullet points (boundary issues)
    bullet_activities = [a for a in activities if "•" in a.get("text", "")]
    print(f"Activities with embedded bullets: {len(bullet_activities)}")

    # Show first few activities
    print(f"\n--- First 5 activities ---")
    for i, activity in enumerate(activities[:5], 1):
        text = activity.get("text", "")[:150]
        wc = activity.get("word_count", 0)
        print(f"\n{i}. [{wc} words] {text}...")

    # Show problematic examples if any
    if long_activities:
        print(f"\n--- Longest activity (potential boundary issue) ---")
        longest = max(activities, key=lambda x: x.get("word_count", 0))
        print(f"Word count: {longest.get('word_count', 0)}")
        print(f"Text: {longest.get('text', '')[:500]}...")

    if bullet_activities:
        print(f"\n--- Activity with embedded bullet (boundary issue) ---")
        bullet_act = bullet_activities[0]
        print(f"Word count: {bullet_act.get('word_count', 0)}")
        print(f"Text: {bullet_act.get('text', '')[:300]}...")


def main():
    """Run extraction test."""
    # Test with Alpine Shire Council (known to have boundary issues)
    pdf_path = Path("data/raw/2023/VIC/VIC_Alpine_Rural_2023.pdf")

    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        # Try alternative paths
        alternatives = [
            Path("/Users/alfonspalangkaraya/Documents/GitHub/claude3/sdg-alignment-analyzer/data/raw/2023/VIC/VIC_Alpine_Rural_2023.pdf"),
        ]
        for alt in alternatives:
            if alt.exists():
                pdf_path = alt
                break
        else:
            print("Could not find PDF file")
            return

    print(f"Testing extraction on: {pdf_path}")

    # Load existing result for comparison
    existing_result_path = Path("results/by_council/V1_Alpine Shire Council Annual Report 2022-23 - complete_alignment.json")
    if existing_result_path.exists():
        with open(existing_result_path) as f:
            existing_data = json.load(f)
        existing_activities = existing_data.get("activities", [])
        analyze_activities(existing_activities, "EXISTING RESULT (before fixes)")

    # Run new extraction
    print(f"\n\nRunning NEW extraction...")
    extractor = ActivityExtractor(
        min_activity_length=15,  # Slightly lower to catch more
        max_activity_length=100  # Lower max to force splitting
    )

    try:
        result = extractor.extract_from_pdf(pdf_path)
        new_activities = result.get("activities", [])
        analyze_activities(new_activities, "NEW RESULT (after fixes)")

        # Save new result for comparison
        output_path = Path("test_new_extraction.json")
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n\nNew extraction saved to: {output_path}")

        # Comparison summary
        print(f"\n{'='*60}")
        print("COMPARISON SUMMARY")
        print(f"{'='*60}")
        if existing_result_path.exists():
            print(f"Before: {len(existing_activities)} activities")
            print(f"After:  {len(new_activities)} activities")
            print(f"Change: {len(new_activities) - len(existing_activities):+d}")

            # Check for bullet reduction
            old_bullets = len([a for a in existing_activities if "•" in a.get("text", "")])
            new_bullets = len([a for a in new_activities if "•" in a.get("text", "")])
            print(f"\nActivities with embedded bullets:")
            print(f"  Before: {old_bullets}")
            print(f"  After:  {new_bullets}")
            print(f"  Change: {new_bullets - old_bullets:+d}")

    except Exception as e:
        print(f"Error during extraction: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
