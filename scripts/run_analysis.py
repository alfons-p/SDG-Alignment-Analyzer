#!/usr/bin/env python3
"""CLI script for running SDG alignment analysis.

Entry point for batch processing of council annual reports.
Supports parallel processing for multiple councils.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import os
import subprocess
import time
import signal
import atexit

# Add parent directory to path for imports (MUST be before src imports)
sys.path.insert(0, str(Path(__file__).parent.parent))

# Environment variables are loaded centrally by EnvLoader
# No need to call load_dotenv here - EnvLoader auto-loads on import
from src.config.env_loader import EnvLoader

# Disable tokenizers parallelism to avoid deadlocks in multiprocessing
# This must be set before importing transformers/tokenizers
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Suppress torch.distributed.reduce_op deprecation warning (fires on import)
import warnings
warnings.filterwarnings(
    "ignore",
    message="torch.distributed.reduce_op is deprecated",
    category=UserWarning,
)

# Registry of MPS model objects for cleanup at exit
# Populated by process_sequential / process_parallel
_mps_models = []


def _cleanup_mps():
    """Move all MPS tensors to CPU. Best-effort — cannot reach C++ internals."""
    import gc
    import torch

    for obj in _mps_models:
        if obj is not None and hasattr(obj, 'cleanup'):
            try:
                obj.cleanup()
            except Exception:
                pass
    _mps_models.clear()
    gc.collect()
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        torch.mps.empty_cache()

from src.activity_extractor import ActivityExtractor
from src.alignment_engine import AlignmentEngine
from src.hybrid_alignment_engine import HybridAlignmentEngine
from src.reports import Reporter
from src.trends import TrendAnalyzer
from src.sdg_mention_finder import scan_directory_for_sdg_mentions

# Import logging
import logging

# Suppress matplotlib info logs (categorical unit messages)
logging.getLogger('matplotlib.category').setLevel(logging.WARNING)


# Financial statement section headings to detect and exclude
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
        default="results",
        help="Output directory for results"
    )

    parser.add_argument(
        "--model", "-m",
        default="models/sdg-finetuned/sdg-variant-finetuned-20260417_085525",
        help="Sentence transformer model to use (default: 5-variant fine-tuned model)"
    )

    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=None,
        help="Similarity threshold for SDG alignment (default: uses THRESHOLD_CONFIG optimized values)"
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
        default=None,
        help="Number of top activities to analyze"
    )

    parser.add_argument(
        "--no-compare",
        action="store_true",
        default=False,
        help="Skip creating comparison across multiple reports"
    )

    parser.add_argument(
        "--no-aggregate",
        action="store_true",
        default=False,
        help="Skip generating aggregated analysis by state, year, and all councils"
    )

    parser.add_argument(
        "--no-trends",
        action="store_true",
        default=False,
        help="Skip generating trend analysis across years"
    )

    parser.add_argument(
        "--no-yearly-charts",
        action="store_true",
        default=False,
        help="Skip generating yearly comparison charts (bar and line charts by year)"
    )

    parser.add_argument(
        "--no-viz",
        action="store_true",
        help="Skip visualization generation"
    )

    parser.add_argument(
        "--no-keywords",
        action="store_true",
        default=False,
        help="Skip SDG keyword analysis and word cloud generation"
    )

    parser.add_argument(
        "--nofinancial",
        action="store_true",
        default=False,
        help="Exclude financial statements section from analysis. "
             "Text after 'Financial Statements' or similar headings will be removed. "
             "Output will be directed to results/nofinancial/ subfolder."
    )

    parser.add_argument(
        "--sdg-mentions-only",
        action="store_true",
        default=False,
        help="Only scan for SDG mentions (SDG/sustainable development goal), skip full alignment analysis"
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

    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=1,
        help="Number of parallel workers (default: 1 for sequential processing)"
    )

    parser.add_argument(
        "--no-hybrid",
        action="store_true",
        help="Use sentence transformer only (disable hybrid sdgBERT approach)"
    )

    parser.add_argument(
        "--ensemble-mode",
        choices=["weighted", "fallback", "single"],
        default="weighted",
        help="Ensemble mode for hybrid approach (default: weighted)"
    )

    parser.add_argument(
        "--sdg-bert-weight",
        type=float,
        default=0.55,
        help="Weight for sdgBERT in ensemble (default: 0.55)"
    )

    parser.add_argument(
        "--st-weight",
        type=float,
        default=0.45,
        help="Weight for sentence transformer in ensemble (default: 0.45)"
    )

    parser.add_argument(
        "--use-llm-labeling",
        action="store_true",
        default=False,
        help="Enable LLM-based activity labeling using Ollama (default: disabled)"
    )

    parser.add_argument(
        "--llm-model",
        type=str,
        default="kimi-k2.5:cloud",
        help="Ollama model for LLM labeling (default: kimi-k2.5:cloud)"
    )

    parser.add_argument(
        "--llm-max-workers",
        type=int,
        default=4,
        help="Number of parallel threads for LLM labeling (default: 4)"
    )

    parser.add_argument(
        "--llm-ollama-hosts",
        type=str,
        default=None,
        help="Comma-separated list of Ollama hosts for multi-server mode (e.g., 'localhost:11434,localhost:11435,localhost:11436')"
    )

    parser.add_argument(
        "--auto-start-ollama",
        type=int,
        default=None,
        metavar="N",
        help="Automatically start N Ollama servers before analysis and stop them after (default: 4 to match --llm-max-workers)"
    )

    parser.add_argument(
        "--spacymodel",
        type=str,
        default="en_core_web_sm",
        choices=["en_core_web_sm", "en_core_web_md", "en_core_web_lg", "en_core_web_trf"],
        help="spaCy model for NLP processing. Options: en_core_web_sm (fast, basic), en_core_web_md (medium), en_core_web_lg (high accuracy), en_core_web_trf (highest accuracy, requires spacy-transformers)"
    )

    # Activity classifier
    classifier_group = parser.add_argument_group('Activity Classifier')
    classifier_group.add_argument(
        "--no-bert-classifier",
        action="store_true",
        help="Disable BERT activity classifier and use spaCy heuristics instead"
    )
    classifier_group.add_argument(
        "--bert-classifier-model",
        type=str,
        default=None,
        help="Path to BERT classifier model (Hub repo ID or local path. default: voyager205/sdg-activity-classifier)"
    )
    classifier_group.add_argument(
        "--min-confidence",
        type=float,
        default=0.7,
        help="Minimum BERT classifier confidence to keep ACTION sentence (default: 0.7)"
    )
    classifier_group.add_argument(
        "--require-action-verb",
        action="store_true",
        help="Require at least one action verb (priority or standard) in BERT-classified ACTION sentences"
    )

    # Cache management
    cache_group = parser.add_argument_group('Cache Management')
    cache_group.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear all cached embeddings before running"
    )
    cache_group.add_argument(
        "--cache-stats",
        action="store_true",
        help="Show cache statistics and exit"
    )
    cache_group.add_argument(
        "--no-activity-cache",
        action="store_true",
        default=False,
        help="Disable activity embedding cache"
    )

    return parser.parse_args()


# Global list to track spawned Ollama processes for cleanup
_ollama_processes = []

def start_ollama_servers(num_servers: int, model: str, base_port: int = 11434) -> List[str]:
    """
    Start multiple Ollama servers for parallel LLM labeling.

    Args:
        num_servers: Number of Ollama servers to start
        model: Model to load (must be available)
        base_port: Starting port number

    Returns:
        List of Ollama host URLs
    """
    print(f"\n{'='*60}")
    print(f"Starting {num_servers} Ollama servers with model: {model}")
    print(f"{'='*60}")

    # Check if model is available
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if model not in result.stdout:
            print(f"Model {model} not found. Pulling...")
            subprocess.run(["ollama", "pull", model], check=True, timeout=600)
            print(f"✓ Model {model} pulled successfully")
    except Exception as e:
        print(f"⚠ Warning: Could not verify model: {e}")

    hosts = []

    for i in range(num_servers):
        port = base_port + i
        log_file = f"/tmp/ollama_{port}.log"

        # Check if port is already in use
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            if result == 0:
                print(f"  Port {port} already in use, using existing server")
                hosts.append(f"http://localhost:{port}")
                continue
        except:
            pass

        # Start new Ollama server
        print(f"  Starting server {i+1}/{num_servers} on port {port}...", end=" ")
        env = os.environ.copy()
        env["OLLAMA_HOST"] = f"0.0.0.0:{port}"

        try:
            # Start ollama serve in background
            process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=open(log_file, "w"),
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True
            )
            _ollama_processes.append((process, port))
            time.sleep(2)  # Give server time to start

            # Verify server is ready
            for attempt in range(30):
                try:
                    import urllib.request
                    urllib.request.urlopen(f"http://localhost:{port}/api/tags", timeout=2)
                    print(f"✓ Ready")
                    hosts.append(f"http://localhost:{port}")
                    break
                except:
                    time.sleep(1)
            else:
                print(f"✗ Failed to start")
                process.terminate()

        except Exception as e:
            print(f"✗ Error: {e}")

    print(f"\n✓ Started {len(hosts)} Ollama server(s)")
    return hosts


def stop_ollama_servers():
    """Stop all Ollama servers started by this script."""
    if not _ollama_processes:
        return

    print(f"\n{'='*60}")
    print("Stopping Ollama servers...")
    print(f"{'='*60}")

    for process, port in _ollama_processes:
        try:
            print(f"  Stopping server on port {port}...", end=" ")
            process.terminate()
            try:
                process.wait(timeout=5)
                print("✓")
            except:
                process.kill()
                process.wait()
                print("✓ (killed)")
        except Exception as e:
            print(f"✗ {e}")

    # Clean up any remaining ollama processes started by us
    try:
        subprocess.run(["pkill", "-f", "ollama serve"], capture_output=True)
    except:
        pass

    # Clean up log files
    for _, port in _ollama_processes:
        try:
            os.remove(f"/tmp/ollama_{port}.log")
        except:
            pass

    _ollama_processes.clear()
    print("✓ All Ollama servers stopped")


def find_pdf_files(input_path: str) -> List[Path]:
    """Find PDF files from input path."""
    path = Path(input_path)

    if path.is_file():
        if path.suffix.lower() == '.pdf':
            return [path]
        else:
            raise ValueError(f"Input file must be a PDF: {path}")

    if path.is_dir():
        pdfs = list(path.rglob("*.pdf"))
        return sorted(pdfs)

    raise ValueError(f"Input path not found: {path}")


def extract_metadata_from_path(pdf_path: Path, base_path: Path) -> Dict[str, str]:
    """Extract year, state, and urban/rural classification from path and filename."""
    import re

    try:
        relative = pdf_path.relative_to(base_path)
        parts = relative.parts

        metadata = {
            'year': '',
            'state': '',
            'council_name': '',
            'urban_rural': '',
            'relative_path': str(relative)
        }

        # First try to extract year from directory path
        for part in parts[:-1]:
            if part.isdigit():
                metadata['year'] = part
            elif part.isalpha() and len(part) <= 3:
                metadata['state'] = part.upper()

        # If year not found in path, extract from filename (e.g., NSW_Balranald_Rural_2025.pdf)
        if not metadata['year']:
            filename = pdf_path.stem
            # Look for 4-digit year in filename (e.g., 2025, 2024, 2023)
            years = re.findall(r'(20\d{2})', filename)
            if years:
                metadata['year'] = years[0]

        # Extract urban/rural from filename
        filename_lower = pdf_path.stem.lower()
        if 'urban' in filename_lower:
            metadata['urban_rural'] = 'Urban'
        elif 'rural' in filename_lower:
            metadata['urban_rural'] = 'Rural'

        # Extract state from filename if not found in path (e.g., VIC_Alpine_Rural_2024.pdf)
        if not metadata['state']:
            filename = pdf_path.stem.upper()
            state_patterns = ['VIC', 'NSW', 'QLD', 'WA', 'SA', 'TAS', 'ACT', 'NT']
            for state in state_patterns:
                if filename.startswith(state + '_') or state in filename:
                    metadata['state'] = state
                    break

        # Extract council name from filename: {STATE}_{COUNCIL}_{URBAN/RURAL}_{YEAR}.pdf
        # e.g., VIC_Melbourne_Urban_2025.pdf → council_name="Melbourne"
        stem = pdf_path.stem
        parts = stem.split('_')
        if len(parts) >= 4 and parts[0].upper() in ['VIC', 'NSW', 'QLD', 'WA', 'SA', 'TAS', 'ACT', 'NT']:
            # parts[0]=state, parts[1]=council, parts[-2]=urban/rural, parts[-1]=year
            council_parts = parts[1:-2]  # everything between state and urban_rural/year
            metadata['council_name'] = '_'.join(council_parts)

        return metadata
    except ValueError:
        return {'year': '', 'state': '', 'council_name': '', 'urban_rural': '', 'relative_path': str(pdf_path)}


def process_single_report_parallel(
    pdf_path: Path,
    output_dir: Path,
    base_input_path: Path,
    model: str,
    threshold: float,
    min_words: int,
    max_words: int,
    top_activities: Optional[int],
    no_viz: bool,
    force: bool,
    verbose: bool,
    use_hybrid: bool = True,
    ensemble_mode: str = "weighted",
    sdg_bert_weight: float = 0.55,
    st_weight: float = 0.45,
    use_llm_labeling: bool = False,
    llm_model: str = "kimi-k2.5:cloud",
    llm_max_workers: int = 4,
    llm_ollama_hosts: Optional[List[str]] = None,
    use_cache: bool = True,
    spacy_model: str = "en_core_web_sm",
    nofinancial: bool = False,
    use_bert_classifier: bool = True,
    bert_classifier_model: Optional[str] = None,
    min_confidence: float = 0.7,
    require_action_verb: bool = False,
) -> Optional[dict]:
    """
    Process a single report (standalone function for parallel execution).

    Each worker initializes its own components since they can't be shared
    across processes (especially the ML model).
    """
    # Print the PDF being processed
    print(f"\n>>> Processing: {pdf_path.name}")

    try:
        # Initialize components inside the worker
        extractor = ActivityExtractor(
            min_activity_length=min_words,
            max_activity_length=max_words,
            use_llm_labeling=use_llm_labeling,
            llm_model=llm_model,
            llm_max_workers=llm_max_workers,
            llm_ollama_hosts=llm_ollama_hosts,
            spacy_model=spacy_model,
            nofinancial=nofinancial,
            use_bert_classifier=use_bert_classifier,
            bert_classifier_model=bert_classifier_model,
            min_confidence=min_confidence,
            require_action_verb=require_action_verb,
        )

        # Use HybridAlignmentEngine by default (unless disabled)
        if use_hybrid:
            engine = HybridAlignmentEngine(
                model_name=model,
                similarity_threshold=threshold,
                use_sdg_bert=True,
                ensemble_mode=ensemble_mode,
                sdg_bert_weight=sdg_bert_weight,
                st_weight=st_weight
            )
        else:
            engine = AlignmentEngine(
                model_name=model,
                similarity_threshold=threshold
            )

        reporter = Reporter(output_dir=output_dir, council_subdir=True)

        # Extract metadata
        metadata = extract_metadata_from_path(pdf_path, base_input_path)

        if verbose:
            print(f"\nProcessing: {pdf_path.name}")

        # Check if output already exists
        source_name = pdf_path.stem
        json_path = output_dir / f"{source_name}_alignment.json"

        if json_path.exists() and not force:
            print(f"Skipping {pdf_path.name} - output exists (use --force to reprocess)")
            return None

        # Extract activities
        activities_data = extractor.extract_from_pdf(pdf_path)

        # Add metadata
        activities_data['metadata']['year'] = metadata['year']
        activities_data['metadata']['state'] = metadata['state']
        activities_data['metadata']['council_name'] = metadata.get('council_name', '')
        activities_data['metadata']['urban_rural'] = metadata['urban_rural']
        activities_data['metadata']['relative_path'] = metadata['relative_path']

        if activities_data['total_activities'] == 0:
            print(f"Warning: No activities found in {pdf_path.name}")
            return None

        # Filter to top activities if limit specified
        if top_activities:
            activities_data['activities'] = activities_data['activities'][:top_activities]

        # Align with SDGs
        alignment_results = engine.align_report(activities_data, use_cache=use_cache)

        # Generate reports
        output_files = reporter.generate_full_report(
            alignment_results,
            include_visualizations=not no_viz
        )

        if verbose:
            print(f"Completed: {pdf_path.name}")

        # Move models to CPU before worker process exits to prevent MPS bus error.
        # __del__ on each class also calls cleanup(), so this is belt-and-suspenders.
        for obj in [extractor, engine, reporter]:
            if obj is not None and hasattr(obj, 'cleanup'):
                try:
                    obj.cleanup()
                except Exception:
                    pass

        return alignment_results

    except Exception as e:
        print(f"Error processing {pdf_path.name}: {e}")
        import traceback
        traceback.print_exc()
        return None


def process_sequential(
    pdf_files: List[Path],
    output_dir: Path,
    base_input_path: Path,
    args: argparse.Namespace
) -> List[dict]:
    """Process files sequentially (original behavior)."""
    results = []

    # Initialize components once
    extractor = ActivityExtractor(
        min_activity_length=args.min_words,
        max_activity_length=args.max_words,
        use_llm_labeling=getattr(args, 'use_llm_labeling', False),
        llm_model=getattr(args, 'llm_model', 'kimi-k2.5:cloud'),
        llm_max_workers=getattr(args, 'llm_max_workers', 4),
        llm_ollama_hosts=args.llm_ollama_hosts.split(',') if args.llm_ollama_hosts else None,
        spacy_model=getattr(args, 'spacymodel', 'en_core_web_sm'),
        nofinancial=args.nofinancial,
        use_bert_classifier=not getattr(args, 'no_bert_classifier', False),
        bert_classifier_model=getattr(args, 'bert_classifier_model', None),
        min_confidence=args.min_confidence,
        require_action_verb=getattr(args, 'require_action_verb', False),
    )

    # Use HybridAlignmentEngine by default (unless --no-hybrid)
    if args.no_hybrid:
        engine = AlignmentEngine(
            model_name=args.model,
            similarity_threshold=args.threshold
        )
    else:
        engine = HybridAlignmentEngine(
            model_name=args.model,
            similarity_threshold=args.threshold,
            use_sdg_bert=True,
            ensemble_mode=args.ensemble_mode,
            sdg_bert_weight=args.sdg_bert_weight,
            st_weight=args.st_weight
        )

    reporter = Reporter(output_dir=output_dir)

    # Register models for MPS cleanup at exit
    _mps_models.extend([extractor, engine, reporter])

    for pdf_path in pdf_files:
        result = process_single_report(
            pdf_path, output_dir, extractor, engine, reporter, args,
            base_input_path=base_input_path
        )
        if result:
            results.append(result)

    return results


def process_parallel(
    pdf_files: List[Path],
    output_dir: Path,
    base_input_path: Path,
    args: argparse.Namespace
) -> List[dict]:
    """Process files in parallel using ProcessPoolExecutor."""
    results = []
    completed = 0
    failed = 0

    print(f"\nProcessing {len(pdf_files)} PDFs with {args.workers} workers...")
    print("-" * 60)

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        # Submit all tasks
        future_to_pdf = {
            executor.submit(
                process_single_report_parallel,
                pdf_path,
                output_dir,
                base_input_path,
                args.model,
                args.threshold,
                args.min_words,
                args.max_words,
                args.top_activities,
                args.no_viz,
                args.force,
                args.verbose,
                not args.no_hybrid,  # use_hybrid
                args.ensemble_mode,
                args.sdg_bert_weight,
                args.st_weight,
                getattr(args, 'use_llm_labeling', False),
                getattr(args, 'llm_model', 'kimi-k2.5:cloud'),
                getattr(args, 'llm_max_workers', 4),
                args.llm_ollama_hosts.split(',') if args.llm_ollama_hosts else None,
                not args.no_activity_cache,  # use_cache
                getattr(args, 'spacymodel', 'en_core_web_sm'),  # spacy_model
                args.nofinancial,  # nofinancial
                not getattr(args, 'no_bert_classifier', False),  # use_bert_classifier
                getattr(args, 'bert_classifier_model', None),  # bert_classifier_model
                args.min_confidence,  # min_confidence
                getattr(args, 'require_action_verb', False),  # require_action_verb
            ): pdf_path
            for pdf_path in pdf_files
        }

        # Collect results as they complete
        for future in as_completed(future_to_pdf):
            pdf_path = future_to_pdf[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
                    completed += 1
                    print(f"✓ Completed ({completed}/{len(pdf_files)}): {pdf_path.name}")
                else:
                    failed += 1
                    print(f"✗ Failed/Skipped ({failed}): {pdf_path.name}")
            except Exception as e:
                failed += 1
                print(f"✗ Error ({failed}) in {pdf_path.name}: {e}")

    return results


def process_single_report(
    pdf_path: Path,
    output_dir: Path,
    extractor: ActivityExtractor,
    engine: AlignmentEngine,
    reporter: Reporter,
    args: argparse.Namespace,
    base_input_path: Path = None
) -> Optional[dict]:
    """Process a single report (sequential version)."""
    try:
        # Extract metadata from path
        if base_input_path is None:
            base_input_path = Path(args.input)
        metadata = extract_metadata_from_path(pdf_path, base_input_path)

        print(f"\n{'='*60}")
        print(f"Processing: {pdf_path.name}")
        if metadata['year']:
            print(f"Year: {metadata['year']}")
        if metadata['state']:
            print(f"State: {metadata['state']}")
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

        # Add metadata
        activities_data['metadata']['year'] = metadata['year']
        activities_data['metadata']['state'] = metadata['state']
        activities_data['metadata']['council_name'] = metadata.get('council_name', '')
        activities_data['metadata']['urban_rural'] = metadata['urban_rural']
        activities_data['metadata']['relative_path'] = metadata['relative_path']

        print(f"Found {activities_data['total_activities']} activities")

        if activities_data['total_activities'] == 0:
            print("Warning: No activities found in document")
            return None

        # Filter to top activities if limit specified
        if args.top_activities:
            activities_data['activities'] = activities_data['activities'][:args.top_activities]
            print(f"Analyzing top {len(activities_data['activities'])} activities (filtered from {activities_data['total_activities']})...")
        else:
            print(f"Analyzing all {len(activities_data['activities'])} activities...")

        # Align with SDGs
        print("Computing SDG alignment...")
        use_cache = getattr(args, 'no_activity_cache', False) is False
        alignment_results = engine.align_report(activities_data, use_cache=use_cache)

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

    # Initialize logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    logger.info("="*60)
    logger.info("SDG Alignment Analyzer started")
    logger.info(f"Log file: logs/sdg_analyzer_{time.strftime('%Y%m%d_%H%M%S')}.log")
    logger.info("="*60)

    # Handle cache management commands
    from src.embedding_cache import EmbeddingCache
    cache = EmbeddingCache()

    if args.cache_stats:
        print("="*60)
        print("Cache Statistics")
        print("="*60)
        stats = cache.get_cache_stats()
        print(f"  SDG cache files: {stats['sdg_cache_files']}")
        print(f"  Activity cache files: {stats['activity_cache_files']}")
        print(f"  Total size: {stats['total_size_mb']:.2f} MB")
        if stats['oldest_entry']:
            print(f"  Oldest entry: {stats['oldest_entry']}")
        if stats['newest_entry']:
            print(f"  Newest entry: {stats['newest_entry']}")
        return

    if args.clear_cache:
        print("="*60)
        print("Clearing Cache")
        print("="*60)
        stats = cache.clear_cache()
        print(f"  Removed {stats['sdg']} SDG cache files")
        print(f"  Removed {stats['activity']} activity cache files")
        if stats['errors'] > 0:
            print(f"  Errors: {stats['errors']}")
        print("\nCache cleared successfully!")

    # Auto-start Ollama servers if requested (when using LLM labeling)
    auto_started_hosts = None
    if args.use_llm_labeling:
        # Check if configured servers are already running
        configured_hosts = args.llm_ollama_hosts.split(',') if args.llm_ollama_hosts else []
        running_servers = []

        for host in configured_hosts:
            host = host.strip()
            if not host:
                continue
            try:
                import urllib.request
                urllib.request.urlopen(f"http://{host}/api/tags", timeout=2)
                running_servers.append(host)
            except:
                pass

        # If not enough servers running, auto-start them
        # Default to 4 servers to match llm_max_workers, or use specified count
        desired_servers = args.auto_start_ollama if args.auto_start_ollama else 4
        if len(running_servers) < desired_servers:
            print(f"\n{'='*60}")
            print(f"Detected {len(running_servers)}/{len(configured_hosts)} Ollama servers running")
            print(f"Auto-starting {desired_servers} server(s)...")
            print(f"{'='*60}")

            auto_started_hosts = start_ollama_servers(
                desired_servers,
                args.llm_model
            )
            if auto_started_hosts:
                # Merge running and auto-started servers
                all_hosts = list(dict.fromkeys(running_servers + auto_started_hosts))
                args.llm_ollama_hosts = ','.join(all_hosts)
                # Register cleanup on exit
                atexit.register(stop_ollama_servers)
        elif len(running_servers) > 0:
            print(f"\n✓ Using {len(running_servers)} existing Ollama server(s): {', '.join(running_servers)}")
            args.llm_ollama_hosts = ','.join(running_servers)

    # Setup paths - follow standard output structure
    input_path = Path(args.input)
    output_dir = Path(args.output)

    # If nofinancial option is enabled, redirect output to nofinancial subfolder
    if args.nofinancial:
        output_dir = output_dir / "nofinancial"
        print(f"Financial statements exclusion: Enabled")
        print(f"Output will be saved to: {output_dir}")

    # Handle SDG mentions only mode
    if args.sdg_mentions_only:
        print("="*60)
        print("SDG Mention Scanner")
        print("Scanning for 'SDG' and 'sustainable development goal'")
        print("="*60)
        print(f"Input: {input_path}")
        print(f"Output: {output_dir / 'sdg_mentions'}")
        print()

        sdg_mentions_dir = output_dir / "sdg_mentions"
        results = scan_directory_for_sdg_mentions(
            input_path,
            sdg_mentions_dir,
            verbose=args.verbose
        )
        print("\nSDG mentions scan complete!")
        return

    # Create main output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories for different aggregation levels
    by_state_dir = output_dir / "by_state"
    by_state_dir.mkdir(parents=True, exist_ok=True)

    print(f"SDG Alignment Analyzer")
    print(f"Model: {args.model}")
    if args.threshold is not None:
        print(f"Threshold: {args.threshold} (manual override)")
    else:
        mode = "hybrid" if not args.no_hybrid else "sentence_transformer"
        print(f"Threshold: Using THRESHOLD_CONFIG ({mode} mode, SDG-specific)")
    print(f"Workers: {args.workers}")
    print(f"Output directory: {output_dir}")

    # Show hybrid mode status
    if args.no_hybrid:
        print(f"Mode: Sentence Transformer only")
    else:
        print(f"Mode: Hybrid Ensemble (sdgBERT + Sentence Transformer)")
        print(f"  Ensemble mode: {args.ensemble_mode}")
        print(f"  Weights: sdgBERT={args.sdg_bert_weight}, ST={args.st_weight}")

    # Show LLM labeling status
    if args.use_llm_labeling:
        print(f"LLM Labeling: Enabled")
        print(f"  Model: {args.llm_model}")
        print(f"  Workers: {args.llm_max_workers}")
        if args.llm_ollama_hosts:
            num_servers = len(args.llm_ollama_hosts.split(','))
            print(f"  Multi-server mode: {num_servers} server(s)")
            print(f"    Hosts: {args.llm_ollama_hosts}")
        else:
            print(f"  Single-server mode: localhost:11434")

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

    # Process files
    print(f"Processing {len(pdf_files)} PDF files...")
    print(f"Council results will be saved to: {output_dir}")

    if args.workers > 1 and len(pdf_files) > 1:
        # Parallel processing
        results = process_parallel(pdf_files, output_dir, input_path, args)
    else:
        # Sequential processing
        results = process_sequential(pdf_files, output_dir, input_path, args)

    # Create comparison if multiple files (enabled by default) - save to national level (output_dir)
    if len(results) > 1 and not args.no_compare:
        print(f"\n{'='*60}")
        print("Generating comparison report (National level)...")
        print(f"{'='*60}")

        # Initialize reporter for comparison - save to output_dir (national level)
        reporter = Reporter(output_dir=output_dir, council_subdir=True)

        try:
            # Create comparison charts (box plot and bar chart)
            print("\nGenerating comparison charts...")
            comparison_paths = reporter.create_comparison_charts(results, filename_prefix="comparison")
            print(f"  Box plot: {comparison_paths['boxplot']}")
            print(f"  Bar chart: {comparison_paths['bar_chart']}")

            # Original comparison summary
            comparison_df = reporter.create_multi_report_comparison(results)
            comparison_csv = output_dir / "comparison_summary.csv"
            comparison_df.to_csv(comparison_csv, index=False)
            print(f"Comparison CSV: {comparison_csv}")

            print("\nComparison Summary:")
            print(comparison_df.to_string(index=False))

        except Exception as e:
            print(f"Error creating comparison: {e}")

        # Create alignment summary with coverage for ALL SDGs
        try:
            print(f"\n{'='*60}")
            print("Generating alignment summary (all SDGs coverage)...")
            print(f"{'='*60}")

            # Export alignment summary CSV
            alignment_summary_path = reporter.export_alignment_summary_csv(
                results,
                filename="alignment_summary.csv"
            )
            print(f"Alignment summary CSV: {alignment_summary_path}")

            # Display summary
            alignment_df = reporter.create_alignment_summary(results)
            print("\nAlignment Summary (Coverage % for each SDG):")
            print(alignment_df.to_string(index=False))

        except Exception as e:
            print(f"Error creating alignment summary: {e}")

        # Create coverage comparison charts
        try:
            print(f"\n{'='*60}")
            print("Generating coverage comparison charts...")
            print(f"{'='*60}")

            coverage_paths = reporter.create_coverage_comparison_charts(
                results,
                filename_prefix="coverage_comparison",
                sort_by="sdg"  # Sort by SDG number (SDG 1, 2, 3... 17)
            )
            print(f"  Box plot: {coverage_paths['boxplot']}")
            print(f"  Bar chart: {coverage_paths['bar_chart']}")
            print("\nThese charts show the proportion of activities aligned (is_aligned=True) for each SDG")
            print("SDGs are sorted by number (SDG 1 → SDG 17).")

            # Create council coverage comparison chart
            print(f"\n{'='*60}")
            print("Generating council coverage comparison chart...")
            print(f"{'='*60}")
            council_coverage_path = reporter.create_council_coverage_chart(
                results,
                filename="council_coverage_comparison_bar.png",
                sort_by="sdg",
                threshold=args.threshold
            )
            print(f"  Council coverage bar chart: {council_coverage_path}")
            print("\nThis chart shows the % of councils with activities in each SDG.")

        except Exception as e:
            print(f"Error creating coverage charts: {e}")

    # Generate aggregated analysis if not disabled
    if len(results) > 1 and not args.no_aggregate:
        print(f"\n{'='*60}")
        print("GENERATING AGGREGATED ANALYSIS")
        print(f"{'='*60}")

        # Council-level results already saved to by_council_dir

        # State-level aggregated outputs go to by_state_dir
        print(f"State-level results will be saved to: {by_state_dir}")

        # Initialize reporter for state-level outputs
        state_reporter = Reporter(output_dir=by_state_dir, council_subdir=False)

        # National-level aggregated outputs go to output_dir (root)
        print(f"National-level results will be saved to: {output_dir}")

        # Initialize reporter for national-level outputs
        nat_reporter = Reporter(output_dir=output_dir, council_subdir=False)

        # Collect state and year groups
        state_groups = nat_reporter.aggregate_results_by_state(results)
        year_groups = nat_reporter.aggregate_results_by_year(results)

        # Print summary tables
        print(f"\n{'='*60}")
        print("Councils by State")
        print(f"{'='*60}")
        for state, group in sorted(state_groups.items()):
            print(f"  {state:20s}: {len(group):4d} councils")
        print("-" * 60)
        print(f"  {'Total':20s}: {sum(len(g) for g in state_groups.values()):4d} councils")

        print(f"\n{'='*60}")
        print("Councils by Year")
        print(f"{'='*60}")
        for year, group in sorted(year_groups.items()):
            print(f"  {year:20s}: {len(group):4d} councils")
        print("-" * 60)
        print(f"  {'Total':20s}: {sum(len(g) for g in year_groups.values()):4d} councils")

        # LEVEL 1: National summary already exported as alignment_summary.csv above.
        # LEVEL 2: State Aggregation (State level - save to by_state_dir)
        print(f"\n{'='*60}")
        print("LEVEL 2: State-Level Aggregation")
        print(f"{'='*60}")
        if len(state_groups) >= 2:
            try:
                print(f"Generating charts for {len(state_groups)} states...")
                paths = nat_reporter.create_state_aggregated_charts(
                    results,
                    filename_prefix="state_aggregated"
                )
                for name, path in paths.items():
                    print(f"  {name:15s}: {path.name}")
            except Exception as e:
                print(f"Error creating state charts: {e}")
        else:
            print(f"Only {len(state_groups)} state(s) found. Need at least 2 for comparison.")

        # LEVEL 2b: State-Specific Analysis (State level)
        print(f"\n{'='*60}")
        print("LEVEL 2b: State-Specific Analysis")
        print(f"{'='*60}")
        try:
            print("Generating per-state comparison charts and tables...")
            state_specific_paths = nat_reporter.create_state_specific_analysis(
                results,
                output_dir=by_state_dir,
                threshold=args.threshold
            )
            print(f"\nCreated {len(state_specific_paths)} state-specific files")
        except Exception as e:
            print(f"Error creating state-specific analysis: {e}")

        # LEVEL 2c: Year-Specific Analysis (National level with by_year subfolder)
        print(f"\n{'='*60}")
        print("LEVEL 2c: Year-Specific Analysis")
        print(f"{'='*60}")
        try:
            print("Generating per-year comparison charts and tables...")
            year_specific_paths = nat_reporter.create_year_specific_analysis(
                results,
                output_dir=output_dir / "by_year"
            )
            print(f"\nCreated {len(year_specific_paths)} year-specific files")
        except Exception as e:
            print(f"Error creating year-specific analysis: {e}")

        # LEVEL 3: Year Aggregation (National level)
        print(f"\n{'='*60}")
        print("LEVEL 3: Year-Level Aggregation (National)")
        print(f"{'='*60}")
        if len(year_groups) >= 2:
            try:
                print(f"Generating charts for {len(year_groups)} years...")
                paths = nat_reporter.create_year_aggregated_charts(
                    results,
                    filename_prefix="year_aggregated"
                )
                for name, path in paths.items():
                    print(f"  {name:15s}: {path.name}")
            except Exception as e:
                print(f"Error creating year charts: {e}")
        else:
            print(f"Only {len(year_groups)} year(s) found. Need at least 2 for comparison.")

        # LEVEL 4: All Councils Aggregation (National level)
        print(f"\n{'='*60}")
        print("LEVEL 4: All Councils Aggregation (National)")
        print(f"{'='*60}")
        try:
            print("Generating comprehensive aggregate report...")
            paths = nat_reporter.create_all_aggregated_charts(
                results,
                filename_prefix="all_councils_aggregated"
            )
            for name, path in paths.items():
                print(f"  {name:15s}: {path.name}")
        except Exception as e:
            print(f"Error creating all-councils charts: {e}")

        print(f"\n{'='*60}")
        print(f"AGGREGATED ANALYSIS COMPLETE")
        print(f"Results saved to: {output_dir}")
        print(f"  - National level: {output_dir}/")
        print(f"  - State level: {by_state_dir}/")
        print(f"  - Council level: {output_dir}/by_council/")
        print(f"{'='*60}")

    # Generate trend analysis if not disabled
    if not args.no_trends:
        print(f"\n{'='*60}")
        print("GENERATING TREND ANALYSIS")
        print(f"{'='*60}")

        trend_analyzer = TrendAnalyzer(results_dir=output_dir)

        try:
            # Overall trends
            print("\nAnalyzing overall trends...")
            output_files = trend_analyzer.generate_full_trend_analysis()

            print(f"\nOverall trend analysis complete!")
            print(f"Output directory: {trend_analyzer.results_dir / 'trends'}")
            print("\nGenerated files:")
            for file_type, file_path in output_files.items():
                print(f"  [{file_type:25}] {file_path.name}")

            # State-specific trends
            available_states = trend_analyzer.get_available_states()
            if len(available_states) >= 1:
                print(f"\n\nGenerating state-specific trend analysis...")
                print(f"States found: {', '.join(available_states)}")

                state_output_files = trend_analyzer.generate_state_trend_analysis(
                    states=available_states
                )

                print(f"\nState-specific analysis complete!")
                print(f"Output directory: {trend_analyzer.results_dir / 'trends' / 'by_state'}")
                print("\nGenerated state files:")
                for file_type, file_path in state_output_files.items():
                    print(f"  [{file_type:25}] {file_path}")

            # Print summary of findings
            overall_trends = trend_analyzer.analyze_overall_trends()
            if overall_trends:
                summary_df = trend_analyzer.get_trend_summary_dataframe(overall_trends)
                if not summary_df.empty:
                    print("\n" + "-" * 60)
                    print("OVERALL TREND SUMMARY")
                    print("-" * 60)

                    sig_increasing = summary_df[(summary_df['Significant'] == True) &
                                                (summary_df['Trend Direction'] == 'increasing')]
                    sig_decreasing = summary_df[(summary_df['Significant'] == True) &
                                                (summary_df['Trend Direction'] == 'decreasing')]

                    print(f"\nSignificant increasing trends: {len(sig_increasing)}")
                    for _, row in sig_increasing.iterrows():
                        print(f"  SDG {int(row['SDG'])} ({row['SDG Name']}): "
                              f"+{row['Percent Change']:.1f}% change")

                    print(f"\nSignificant decreasing trends: {len(sig_decreasing)}")
                    for _, row in sig_decreasing.iterrows():
                        print(f"  SDG {int(row['SDG'])} ({row['SDG Name']}): "
                              f"{row['Percent Change']:.1f}% change")

        except Exception as e:
            print(f"Error generating trend analysis: {e}")
            import traceback
            traceback.print_exc()

    # Generate yearly comparison charts if not disabled
    if len(results) > 1 and not args.no_yearly_charts:
        print(f"\n{'='*60}")
        print("GENERATING YEARLY COMPARISON CHARTS")
        print(f"{'='*60}")

        reporter = Reporter(output_dir=output_dir, council_subdir=True)

        try:
            # Generate comprehensive yearly analysis (all 6 chart types)
            yearly_paths = reporter.create_comprehensive_yearly_analysis(
                results,
                filename_prefix="yearly_comprehensive"
            )

            print(f"\nYearly charts saved to: {output_dir}")
            print("\nGenerated charts:")
            for chart_type, path in yearly_paths.items():
                print(f"  [{chart_type:25}] {path.name}")

        except Exception as e:
            print(f"Error generating yearly charts: {e}")
            import traceback
            traceback.print_exc()

    # Generate SDG keyword analysis if not disabled
    if len(results) > 0 and not args.no_keywords:
        print(f"\n{'='*60}")
        print("GENERATING SDG KEYWORD ANALYSIS")
        print(f"{'='*60}")

        reporter = Reporter(output_dir=output_dir, council_subdir=True)

        try:
            keyword_results = reporter.analyze_sdg_keywords(
                results,
                min_score=0.5,
                top_n=50,
                output_dir=output_dir / "sdg_keywords"
            )

            print(f"\nKeyword analysis saved to: {output_dir / 'sdg_keywords'}")
            print(f"  CSV table: {keyword_results['tables']['csv'].name}")
            print(f"  JSON table: {keyword_results['tables']['json'].name}")
            print(f"  Word clouds: {len(keyword_results['wordclouds'])} images")

        except Exception as e:
            print(f"Error generating keyword analysis: {e}")
            import traceback
            traceback.print_exc()

    # Always run SDG mention scan as part of normal analysis
    print(f"\n{'='*60}")
    print("RUNNING SDG MENTION SCAN")
    print(f"{'='*60}")
    try:
        sdg_mentions_dir = output_dir / "sdg_mentions"
        print(f"Scanning for 'SDG' and 'sustainable development goal' mentions...")
        scan_directory_for_sdg_mentions(input_path, sdg_mentions_dir)
        print(f"SDG mention scan complete! Results saved to: {sdg_mentions_dir}")
    except Exception as e:
        print(f"Error running SDG mention scan: {e}")

    print(f"\n{'='*60}")
    print(f"Analysis complete! Results saved to: {output_dir}")
    print(f"{'='*60}")

    # Cleanup auto-started Ollama servers (if atexit hasn't run yet)
    stop_ollama_servers()


if __name__ == "__main__":
    # Set up signal handlers for clean shutdown
    def signal_handler(signum, frame):
        print(f"\n\nReceived signal {signum}, shutting down...")
        stop_ollama_servers()
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        main()
    finally:
        # 1. Release MPS models (move to CPU)
        _cleanup_mps()
        # 2. Stop Ollama servers
        stop_ollama_servers()
        # 3. Clean up multiprocessing resources.
        #    Workers exit normally (no os._exit), so they unregister their
        #    own semaphores. The remaining semaphore is from ProcessPoolExecutor
        #    internals; the resource tracker would warn about it but it's
        #    already released by the OS when the main process dies.
        try:
            tracker = multiprocessing.resource_tracker._resource_tracker
            if tracker._fd is not None:
                os.close(tracker._fd)
                tracker._fd = None
            if tracker._pid is not None:
                # Kill tracker before it enters cleanup loop (prevents
                # "leaked semaphore" warning which is cosmetic here)
                os.kill(tracker._pid, signal.SIGKILL)
                os.waitpid(tracker._pid, 0)
                tracker._pid = None
        except Exception:
            pass
        # 4. Flush all output streams
        sys.stdout.flush()
        sys.stderr.flush()
        # 5. Skip C++ static teardown — prevents MPS bus error.
        #    os._exit(0) is the primary fix: Python's gc.get_objects() cannot
        #    reach C++ internal tensors, so the atexit/cleanup approach alone
        #    is insufficient. Skipping C++ teardown is safe for a CLI script
        #    — all output files are already written before this point.
        os._exit(0)
