#!/usr/bin/env python3
"""Draw a random sample of alignment CSV files.

This script:
1. Finds all *_alignment.csv files in the source directory
2. Randomly samples N files (default: 100)
3. Copies them to a destination directory

Usage:
    python scripts/draw_sample.py
    python scripts/draw_sample.py --n 50 --source results/by_council/csv --dest results/sample_50
"""

import argparse
import glob
import os
import random
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Draw random sample of alignment CSV files')
    parser.add_argument('--n', type=int, default=100, help='Number of files to sample (default: 100)')
    parser.add_argument('--source', type=str, default='results/nofinancial/by_council/csv',
                        help='Source directory containing *_alignment.csv files')
    parser.add_argument('--dest', type=str, default='results/nofinancial/by_council/sample_100',
                        help='Destination directory for sampled files')
    parser.add_argument('--exclude', type=str, default=None,
                        help='Directory whose files are excluded from sampling')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for reproducibility (default: 42)')
    args = parser.parse_args()

    # Set seed for reproducibility
    random.seed(args.seed)

    # Find all matching files
    pattern = f'{args.source}/*_alignment.csv'
    all_files = glob.glob(pattern)

    if not all_files:
        print(f'No files found matching: {pattern}')
        return

    # Exclude files that already exist in the exclude directory
    if args.exclude:
        exclude_names = set(os.listdir(args.exclude)) if os.path.isdir(args.exclude) else set()
        before = len(all_files)
        all_files = [f for f in all_files if Path(f).name not in exclude_names]
        excluded_count = before - len(all_files)
        if excluded_count:
            print(f'Excluded {excluded_count} files already in {args.exclude}')

    print(f'Total files available: {len(all_files)}')

    # Draw random sample
    sample_files = random.sample(all_files, min(args.n, len(all_files)))
    print(f'Sampled: {len(sample_files)} files (seed={args.seed})')

    # Create destination directory
    os.makedirs(args.dest, exist_ok=True)

    # Copy files
    for f in sample_files:
        shutil.copy2(f, args.dest)

    print(f'Copied to: {args.dest}')

    # List sampled files
    print('\nSampled files:')
    for f in sample_files:
        print(f'  {Path(f).name}')


if __name__ == '__main__':
    main()
