#!/usr/bin/env python3
"""Test auto-start Ollama feature with one PDF."""

import subprocess
import sys
from pathlib import Path

# Configuration
PDF_PATH = "/Users/alfonspalangkaraya/Documents/GitHub/claude3/sdg-alignment-analyzer/data/raw/2025/SA/SA_Cooper Pedy_Rural_2025.pdf"
OUTPUT_DIR = "/Users/alfonspalangkaraya/Documents/GitHub/claude3/sdg-alignment-analyzer/test_results"

def main():
    print("=" * 80)
    print("TEST: Auto-start Ollama Feature")
    print("=" * 80)
    print(f"\nPDF: {PDF_PATH}")
    print(f"Output: {OUTPUT_DIR}")

    # First, check if Ollama is already running
    print("\n--- Checking existing Ollama servers ---")
    try:
        import urllib.request
        for port in [11434, 11435, 11436, 11437]:
            try:
                urllib.request.urlopen(f"http://localhost:{port}/api/tags", timeout=2)
                print(f"  ✓ Server on port {port}: Running")
            except:
                print(f"  ✗ Server on port {port}: Not running")
    except Exception as e:
        print(f"  Error checking: {e}")

    # Build the command
    cmd = [
        "python", "scripts/run_analysis.py",
        "--input", PDF_PATH,
        "--output", OUTPUT_DIR,
        "--use-llm-labeling",
        "--llm-model", "qwen3:8b",
        "--llm-max-workers", "4",
        "--top-activities", "10",  # Only process top 10 for quick test
        # Auto-start will be triggered because no servers are running
    ]

    print("\n--- Running analysis ---")
    print(f"Command: {' '.join(cmd)}")
    print("\nExpected behavior:")
    print("  1. Detect no servers running on default ports")
    print("  2. Auto-start 4 Ollama servers (ports 11434-11437)")
    print("  3. Extract and label activities")
    print("  4. Stop servers after completion")
    print("")

    # Run the command
    try:
        result = subprocess.run(
            cmd,
            cwd="/Users/alfonspalangkaraya/Documents/GitHub/claude3/sdg-alignment-analyzer",
            capture_output=False,  # Show output in real-time
            text=True,
            timeout=3600  # 60 minute timeout for LLM labeling
        )

        print(f"\n--- Result ---")
        print(f"Exit code: {result.returncode}")

        if result.returncode == 0:
            print("✓ Analysis completed successfully!")
        else:
            print("✗ Analysis failed")

    except subprocess.TimeoutExpired:
        print("\n✗ Timeout: Analysis took too long (>10 minutes)")
    except Exception as e:
        print(f"\n✗ Error: {e}")

    # Final check - servers should be stopped
    print("\n--- Final check: Ollama servers ---")
    try:
        import urllib.request
        running = 0
        for port in [11434, 11435, 11436, 11437]:
            try:
                urllib.request.urlopen(f"http://localhost:{port}/api/tags", timeout=2)
                print(f"  ✓ Server on port {port}: Still running")
                running += 1
            except:
                print(f"  ✗ Server on port {port}: Stopped")

        if running == 0:
            print("\n✓ All servers cleaned up properly")
        else:
            print(f"\n⚠ {running} server(s) still running (cleanup issue)")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
