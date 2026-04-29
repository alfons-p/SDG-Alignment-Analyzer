#!/usr/bin/env python3
"""Monitor grid search progress and notify when complete.

Checks periodically for grid search completion and creates a notification.
"""

import json
import time
from pathlib import Path
from datetime import datetime
import sys


def check_grid_search_status():
    """Check if grid search has completed all 17 SDGs."""
    results_file = Path("results/grid_search_results.json")
    log_file = Path("results/grid_search_all_sdgs.log")

    if not results_file.exists():
        return False, 0, "No results file yet"

    try:
        with open(results_file) as f:
            data = json.load(f)

        sdgs_completed = len(data.keys())
        total_sdgs = 17

        # Check if log file shows completion
        log_complete = False
        if log_file.exists():
            log_content = log_file.read_text()
            # Look for completion indicators
            if "Grid Search Summary" in log_content or sdgs_completed >= total_sdgs:
                log_complete = True

        is_complete = sdgs_completed >= total_sdgs or log_complete

        return is_complete, sdgs_completed, f"{sdgs_completed}/{total_sdgs} SDGs completed"

    except Exception as e:
        return False, 0, f"Error reading results: {e}"


def create_notification(complete: bool, sdgs_completed: int, message: str):
    """Create a notification file."""
    notification_file = Path("results/grid_search_notification.txt")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if complete:
        content = f"""
{'='*60}
GRID SEARCH COMPLETE!
{'='*60}

Time: {timestamp}
Status: All 17 SDGs processed
SDGs completed: {sdgs_completed}

Results saved to: results/grid_search_results.json
Log saved to: results/grid_search_all_sdgs.log

Next steps:
1. Review results in results/grid_search_results.json
2. Update src/sdg_ensemble_weights.py with optimal weights
3. Re-benchmark to validate improvements

{'='*60}
"""
    else:
        content = f"""
{'='*60}
GRID SEARCH PROGRESS UPDATE
{'='*60}

Time: {timestamp}
Status: {message}
Progress: {sdgs_completed}/17 SDGs

Check log: tail -f results/grid_search_all_sdgs.log
{'='*60}
"""

    notification_file.write_text(content)
    return notification_file


def monitor_loop(check_interval_minutes: int = 30):
    """Monitor grid search and notify when complete."""
    print("="*60)
    print("GRID SEARCH MONITOR")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Checking every {check_interval_minutes} minutes...")
    print("Press Ctrl+C to stop monitoring")
    print("="*60)

    last_sdgs = 0

    try:
        while True:
            complete, sdgs_completed, message = check_grid_search_status()

            # Create progress notification if SDGs completed changed
            if sdgs_completed > last_sdgs:
                notification = create_notification(complete, sdgs_completed, message)
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {message}")
                print(f"Notification saved to: {notification}")
                last_sdgs = sdgs_completed

            # Exit if complete
            if complete:
                print("\n" + "="*60)
                print("GRID SEARCH COMPLETE!")
                print("="*60)
                print(f"All {sdgs_completed} SDGs processed")
                print(f"Results: results/grid_search_results.json")
                print(f"Notification: results/grid_search_notification.txt")
                print("="*60)
                return 0

            # Sleep until next check
            time.sleep(check_interval_minutes * 60)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
        return 1


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Monitor grid search progress")
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Check interval in minutes (default: 30)"
    )
    parser.add_argument(
        "--one-shot",
        action="store_true",
        help="Check once and exit"
    )

    args = parser.parse_args()

    if args.one_shot:
        complete, sdgs_completed, message = check_grid_search_status()
        print(f"Status: {message}")
        notification = create_notification(complete, sdgs_completed, message)
        print(f"Notification: {notification}")
        return 0 if complete else 1
    else:
        return monitor_loop(args.interval)


if __name__ == "__main__":
    sys.exit(main())
