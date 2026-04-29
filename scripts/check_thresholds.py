#!/usr/bin/env python3
"""Check and display SDG alignment threshold configuration.

This script shows the current optimized threshold settings and validates
that they're being applied correctly in the codebase.

Usage:
    python scripts/check_thresholds.py
    python scripts/check_thresholds.py --show-all
    python scripts/check_thresholds.py --test-sdg 12
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.config.threshold_config import (
    get_threshold,
    get_all_thresholds,
    print_threshold_table,
    THRESHOLD_CONFIG
)
from src.alignment_engine import AlignmentEngine
from src.hybrid_alignment_engine import HybridAlignmentEngine


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Check SDG alignment thresholds")
    parser.add_argument('--show-all', action='store_true',
                        help='Show all SDG-specific thresholds')
    parser.add_argument('--test-sdg', type=int, choices=range(1, 18),
                        help='Test threshold for specific SDG')
    parser.add_argument('--validate', action='store_true',
                        help='Validate thresholds are correctly applied')

    args = parser.parse_args()

    print("="*80)
    print("SDG ALIGNMENT THRESHOLD CONFIGURATION")
    print("="*80)
    print()

    # Show configuration version and date
    config = Config()
    status = config.get_optimization_status()

    print(f"Configuration Version: {status['config_version']} ({status['config_date']})")
    print(f"ST Default Threshold: {status['st_default']}")
    print(f"Hybrid Default Threshold: {status['hybrid_default']}")
    print()

    # Show validation status
    if status['validated_sdgs']:
        print("Validated SDGs:")
        for sdg in status['validated_sdgs']:
            key = f'validated_threshold_{sdg}'
            if key in status:
                val = status[key]
                if val:
                    print(f"  SDG {sdg}: {val.get('threshold', 'N/A')} "
                          f"(F1={val.get('f1_score', 'N/A')}, "
                          f"P={val.get('precision', 'N/A')}, "
                          f"R={val.get('recall', 'N/A')})")
    else:
        print("No validated SDGs yet (using research-based defaults)")
    print()

    # Show specific SDG threshold if requested
    if args.test_sdg:
        sdg = args.test_sdg
        st_thresh = get_threshold('st', sdg=sdg)
        hybrid_thresh = get_threshold('hybrid', sdg=sdg)

        print(f"Thresholds for SDG {sdg}:")
        print(f"  ST-only mode: {st_thresh}")
        print(f"  Hybrid mode: {hybrid_thresh}")
        print()

    # Show all thresholds if requested
    if args.show_all:
        print("="*80)
        print("ALL SDG-SPECIFIC THRESHOLDS")
        print("="*80)
        print()

        st_thresholds = get_all_thresholds('st')
        hybrid_thresholds = get_all_thresholds('hybrid')

        print(f"{'SDG':<6} {'Name':<35} {'ST':<8} {'Hybrid':<8} {'Difference':<12}")
        print("-" * 80)

        for sdg in range(1, 18):
            from src.config.sdg_definitions import SDG_DEFINITIONS
            name = SDG_DEFINITIONS.get(sdg, {}).get('name', f'SDG {sdg}')
            name = name[:34]  # Truncate long names

            st_thresh = st_thresholds[sdg]
            hybrid_thresh = hybrid_thresholds[sdg]
            diff = hybrid_thresh - st_thresh

            marker = ""
            if abs(diff) > 0.1:
                marker = " ***"
            elif abs(diff) > 0.05:
                marker = " **"

            print(f"{sdg:<6} {name:<35} {st_thresh:<8.2f} {hybrid_thresh:<8.2f} "
                  f"{diff:+8.2f}{marker}")

        print()
        print("*** = Significant difference (>0.10)")
        print("**  = Moderate difference (0.05-0.10)")
        print()

    # Validate thresholds are applied correctly
    if args.validate or args.test_sdg:
        print("="*80)
        print("VALIDATION")
        print("="*80)
        print()

        # Test ST engine
        print("Testing Sentence Transformer Engine:")
        st_engine = AlignmentEngine()
        st_default = st_engine.similarity_threshold
        print(f"  Default threshold: {st_default}")
        print(f"  Config default: {get_threshold('st')}")
        print(f"  Match: {'✓' if abs(st_default - get_threshold('st')) < 0.001 else '✗'}")

        if args.test_sdg:
            st_sdg = st_engine.get_threshold_for_sdg(args.test_sdg)
            print(f"  SDG {args.test_sdg} threshold: {st_sdg}")
            print(f"  Config SDG {args.test_sdg}: {get_threshold('st', sdg=args.test_sdg)}")
            print(f"  Match: {'✓' if abs(st_sdg - get_threshold('st', sdg=args.test_sdg)) < 0.001 else '✗'}")

        print()

        # Test hybrid engine
        print("Testing Hybrid Engine:")
        hybrid_engine = HybridAlignmentEngine(use_sdg_bert=False)  # Don't load sdgBERT for speed
        hybrid_default = hybrid_engine.similarity_threshold
        print(f"  Default threshold: {hybrid_default}")
        print(f"  Config default: {get_threshold('hybrid')}")
        print(f"  Match: {'✓' if abs(hybrid_default - get_threshold('hybrid')) < 0.001 else '✗'}")

        if args.test_sdg:
            hybrid_sdg = hybrid_engine.get_threshold_for_sdg(args.test_sdg)
            print(f"  SDG {args.test_sdg} threshold: {hybrid_sdg}")
            print(f"  Config SDG {args.test_sdg}: {get_threshold('hybrid', sdg=args.test_sdg)}")
            print(f"  Match: {'✓' if abs(hybrid_sdg - get_threshold('hybrid', sdg=args.test_sdg)) < 0.001 else '✗'}")

        print()

    # Print full table
    print_threshold_table()


if __name__ == "__main__":
    main()