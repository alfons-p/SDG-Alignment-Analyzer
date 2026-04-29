#!/usr/bin/env python3
"""CLI script for running SDG alignment analysis.

Entry point for batch processing of council annual reports.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.activity_extractor import ActivityExtractor
from src.alignment_engine import AlignmentEngine
from src.reporter import Reporter


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze council annual reports for SDG alignment",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Input PDF file or directory containing PDFs"
    )

    parser.add_argument(
        "--output", "-o",
        default="data/results",
        help="Output directory for results"
    )

    parser.add_argument(
        "--model", "-m",
        default="all-MiniLM-L6-v2",
        help="Sentence transformer model to use"
    )

    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.3,
        help="Similarity threshold for SDG alignment"
    )

    parser.add_argument(
        "--min-words",
        type=int,
        default=20,
        help="Minimum word count for activities"
    )

    parser.add_argument(
        "--max-words",
        type=int,
        default=500,
        help="Maximum word count for activities"
    )

    parser.add_argument(
        "--top-activities",
        type=int,
        default=100,
        help="Number of top activities to analyze"
    )

    parser.add_argument(
        "--compare",
        action="store_true",
        help="Create comparison across multiple reports"
    )

    parser.add_argument(
        "--no-viz",
        action="store_true",
        help="Skip visualization generation"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reprocessing even if output exists"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    return parser.parse_args()


def find_pdf_files(input_path: str) -> List[Path]:
    """Find PDF files from input path."""
    path = Path(input_path)

    if path.is_file():
        if path.suffix.lower() == '.pdf':
            return [path]
        else:
            raise ValueError(f"Input file must be a PDF: {path}")

    if path.is_dir():
        pdfs = list(path.glob("*.pdf"))
        if not pdfs:
            pdfs = list(path.glob("**/*.pdf"))
        return sorted(pdfs)

    raise ValueError(f"Input path not found: {path}")


def process_single_report(
    pdf_path: Path,
    output_dir: Path,
    extractor: ActivityExtractor,
    engine: AlignmentEngine,
    reporter: Reporter,
    args: argparse.Namespace
) -> Optional[dict]:
    """Process a single report."""
    try:
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_path.name}")
        print(f"{'='*60}")

        # Check if output already exists
        source_name = pdf_path.stem
        json_path = output_dir / f"{source_name}_alignment.json"

        if json_path.exists() and not args.force:
            print(f"Output already exists: {json_path}")
            print("Use --force to reprocess")
            return None

        # Extract activities
        print("Extracting activities from PDF...")
        activities_data = extractor.extract_from_pdf(pdf_path)
        print(f"Found {activities_data['total_activities']} activities")

        if activities_data['total_activities'] == 0:
            print("Warning: No activities found in document")
            return None

        # Filter to top activities
        activities_data['activities'] = activities_data['activities'][:args.top_activities]
        print(f"Analyzing top {len(activities_data['activities'])} activities...")

        # Align with SDGs
        print("Computing SDG alignment...")
        alignment_results = engine.align_report(activities_data)

        # Generate reports
        print("Generating reports...")
        output_files = reporter.generate_full_report(
            alignment_results,
            include_visualizations=not args.no_viz
        )

        print("\nGenerated files:")
        for file_type, file_path in output_files.items():
            print(f"  [{file_type:12}] {file_path}")

        # Print summary
        report = alignment_results.get('report_alignment', {})
        top_sdgs = report.get('top_sdgs', [])

        print("\nTop 5 SDGs:")
        for i, sdg in enumerate(top_sdgs[:5], 1):
            print(f"  {i}. SDG {sdg['sdg']}: {sdg['name']} (score: {sdg['mean_score']:.3f})")

        return alignment_results

    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main entry point."""
    args = parse_args()

    # Setup paths
    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"SDG Alignment Analyzer")
    print(f"Model: {args.model}")
    print(f"Threshold: {args.threshold}")
    print(f"Output directory: {output_dir}")

    # Find PDF files
    try:
        pdf_files = find_pdf_files(args.input)
        print(f"Found {len(pdf_files)} PDF file(s)")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    if not pdf_files:
        print("No PDF files found")
        sys.exit(1)

    # Initialize components
    extractor = ActivityExtractor(
        min_activity_length=args.min_words,
        max_activity_length=args.max_words
    )

    engine = AlignmentEngine(
        model_name=args.model,
        similarity_threshold=args.threshold
    )

    reporter = Reporter(output_dir=output_dir)

    # Process files
    results = []
    for pdf_path in pdf_files:
        result = process_single_report(
            pdf_path, output_dir, extractor, engine, reporter, args
        )
        if result:
            results.append(result)

    # Create comparison if multiple files and requested
    if len(results) > 1 and args.compare:
        print(f"\n{'='*60}")
        print("Generating comparison report...")
        print(f"{'='*60}")

        try:
            comparison_path = reporter.create_comparison_chart(results)
            print(f"Comparison chart: {comparison_path}")

            comparison_df = reporter.create_multi_report_comparison(results)
            comparison_csv = output_dir / "comparison_summary.csv"
            comparison_df.to_csv(comparison_csv, index=False)
            print(f"Comparison CSV: {comparison_csv}")

            print("\nComparison Summary:")
            print(comparison_df.to_string(index=False))

        except Exception as e:
            print(f"Error creating comparison: {e}")

    print(f"\n{'='*60}")
    print(f"Analysis complete! Results saved to: {output_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
