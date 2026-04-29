#!/usr/bin/env python3
"""Compare different embedding models on SDG alignment task.

Quick benchmark to test model quality vs speed trade-offs.
"""

import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.activity_extractor import ActivityExtractor
from src.alignment_engine import AlignmentEngine


def test_model(pdf_path: Path, model_name: str, max_activities: int = 50):
    """Test a single model."""
    print(f"\n{'='*60}")
    print(f"Testing: {model_name}")
    print(f"{'='*60}")

    # Extract activities (reuse across models)
    extractor = ActivityExtractor()
    print(f"Extracting activities from {pdf_path.name}...")
    activities_data = extractor.extract_from_pdf(pdf_path)

    if activities_data['total_activities'] == 0:
        print("No activities found!")
        return None

    # Limit for speed
    activities_data['activities'] = activities_data['activities'][:max_activities]
    print(f"Analyzing {len(activities_data['activities'])} activities...")

    # Time the alignment
    engine = AlignmentEngine(model_name=model_name)

    start = time.time()
    results = engine.align_report(activities_data, show_progress=False)
    elapsed = time.time() - start

    # Get report stats
    report = results['report_alignment']

    print(f"\nResults:")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Activities/sec: {len(activities_data['activities'])/elapsed:.1f}")
    print(f"  Top SDG: SDG {report['top_sdgs'][0]['sdg']} - {report['top_sdgs'][0]['name']}")
    print(f"  Top Score: {report['top_sdgs'][0]['mean_score']:.3f}")
    print(f"  Coverage: {report['top_sdgs'][0]['coverage']*100:.1f}%")

    return {
        'model': model_name,
        'time': elapsed,
        'top_sdg': report['top_sdgs'][0],
        'mean_score': report['mean_alignment_score']
    }


def main():
    """Compare models."""
    import argparse

    parser = argparse.ArgumentParser(description="Compare embedding models")
    parser.add_argument("--input", "-i", required=True, help="PDF file to test")
    parser.add_argument("--max-activities", type=int, default=50)
    args = parser.parse_args()

    pdf_path = Path(args.input)
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        return

    # Models to compare
    models = [
        "all-MiniLM-L6-v2",      # Current - fastest
        "all-MiniLM-L12-v2",     # Better quality, still fast
        "all-mpnet-base-v2",     # Best quality, slower
        "paraphrase-mpnet-base-v2",  # Alternative high quality
    ]

    results = []
    for model in models:
        try:
            result = test_model(pdf_path, model, args.max_activities)
            if result:
                results.append(result)
        except Exception as e:
            print(f"Error with {model}: {e}")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"{'Model':<30} {'Time':>8}s {'Top SDG':>20} {'Score':>8}")
    print("-" * 70)
    for r in results:
        print(f"{r['model']:<30} {r['time']:>8.1f} "
              f"{r['top_sdg']['name'][:18]:>20} {r['top_sdg']['mean_score']:>8.3f}")

    if len(results) > 1:
        fastest = min(results, key=lambda x: x['time'])
        best_score = max(results, key=lambda x: x['top_sdg']['mean_score'])
        print(f"\nFastest: {fastest['model']} ({fastest['time']:.1f}s)")
        print(f"Best Quality: {best_score['model']} (score: {best_score['top_sdg']['mean_score']:.3f})")


if __name__ == "__main__":
    main()
