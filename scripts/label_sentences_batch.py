#!/usr/bin/env python3
"""
Label sentences in batches using Ollama or OpenAI-compatible CoT prompting.

Reads candidate sentences from raw_sentences_10percent.csv, samples
stratified by tier, labels them in batches via Ollama or OpenRouter,
and saves results incrementally to avoid losing progress.

Usage:
    # Local Ollama model
    python scripts/label_sentences_batch.py --sample 500
    python scripts/label_sentences_batch.py --sample 8000 --model kimi-k2.6:cloud

    # OpenRouter model
    python scripts/label_sentences_batch.py --backend openai --model google/gemma-3-27b-it --sample 500
    python scripts/label_sentences_batch.py --sample 8000 --model deepseek/deepseek-v4-pro
    
    # Label everything
    python scripts/label_sentences_batch.py --sample all
"""

import argparse
import csv
import os
import random
import re
import sys
import time
import signal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

LABEL_MAP = {"[ACTION]": "ACTION", "[POLICY]": "POLICY", "[NEUTRAL]": "NEUTRAL"}

BATCH_SYSTEM_PROMPT = """You are a linguistic expert specializing in public administration reports.
Your task is to classify sentences based on their SUBSTANTIVE intent.

### DEFINITIONS & RULES:
1. [POLICY]: Future intent or goals (e.g., 'will', 'aims', 'commits').
2. [ACTION]: This is the key implementation category. It includes:
   - Physical work (e.g., 'built', 'installed').
   - Financial work (e.g., 'spent', 'allocated').
   - GOVERNANCE OUTPUTS: If a council 'produced', 'finalized', or 'endorsed'
     a specific plan, report, or framework, this is an ACTION.
3. [NEUTRAL]: Administrative noise. Use this ONLY if there is no substantive
   project or document being created. Examples: meeting dates, greetings,
   personnel changes.

### HANDLING DISTRACTORS:
- Do not let 'Dates' (e.g., 8 July) or 'Committees' (e.g., Audit Committee)
  trick you into a [NEUTRAL] tag if a document was produced or a task completed.

### INPUT FORMAT:
You will receive {batch_size} numbered sentences. Classify EACH one.

### OUTPUT FORMAT:
For EACH sentence, output EXACTLY this format on its own line:
Sentence <number>: Reasoning: (1-sentence analysis) | Category: [TAG]

Example output for 3 sentences:
Sentence 1: Reasoning: Council completed a review of its financial plan. | Category: [ACTION]
Sentence 2: Reasoning: Council aims to improve services next year. | Category: [POLICY]
Sentence 3: Reasoning: The Audit Committee met on 15 March 2024. | Category: [NEUTRAL]
"""

LINE_PATTERN = re.compile(
    r"Sentence\s+(\d+)\s*:\s*Reasoning:\s*(.+?)\s*\|\s*Category:\s*\[(ACTION|POLICY|NEUTRAL)\]",
    re.IGNORECASE,
)


class OllamaTimeout(Exception):
    pass


def _timeout_handler(signum, frame):
    raise OllamaTimeout("Ollama API call timed out")


def build_user_prompt(sentences: list[str]) -> str:
    """Build the user prompt for a batch of sentences."""
    prompt = "Classify each sentence:\n\n"
    for i, sent in enumerate(sentences, 1):
        words = sent.split()
        if len(words) > 200:
            sent = " ".join(words[:200]) + "..."
        prompt += f"Sentence {i}: {sent}\n\n"
    return prompt

def parse_batch_response(response_text: str, batch_size: int) -> list[dict]:
    """Parse structured batch response into per-sentence results.

    Tries the strict format first, then falls back to line-by-line
    extraction for sentences where the model deviated from the template.
    """
    results = {}
    for match in LINE_PATTERN.finditer(response_text):
        sent_num = int(match.group(1))
        reasoning = match.group(2).strip()
        label = match.group(3).upper()
        if 1 <= sent_num <= batch_size:
            results[sent_num] = {
                "label": label,
                "reasoning": reasoning,
            }

    # Fallback: try to find labels in lines that didn't match strict format
    if len(results) < batch_size:
        for line in response_text.split("\n"):
            line = line.strip()
            # Look for sentence number and tag in looser format
            num_match = re.match(r"(?:Sentence\s+)?(\d+)\s*[:.)]\s*", line, re.IGNORECASE)
            if not num_match:
                continue
            num = int(num_match.group(1))
            if num in results or num < 1 or num > batch_size:
                continue
            # Find tag
            tag_match = re.search(r"\[(ACTION|POLICY|NEUTRAL)\]", line, re.IGNORECASE)
            if tag_match:
                label = tag_match.group(1).upper()
                # Extract reasoning (everything between number prefix and category)
                rest = line[num_match.end():]
                reasoning = re.sub(r"\s*\|\s*Category:\s*\[" + label + r"\]\s*$", "", rest).strip()
                # Strip "Reasoning:" prefix if present
                reasoning = re.sub(r"^Reasoning:\s*", "", reasoning, flags=re.IGNORECASE).strip()
                results[num] = {"label": label, "reasoning": reasoning}

    # Build ordered list, filling gaps with parse failures
    parsed = []
    for i in range(1, batch_size + 1):
        if i in results:
            parsed.append(results[i])
        else:
            parsed.append({"label": "PARSE_ERROR", "reasoning": ""})

    return parsed


def _ollama_chat(
    model_name: str,
    messages: list[dict],
    timeout: int = 600,
) -> str:
    """Call Ollama chat API with think=false to disable thinking mode."""
    import json
    import urllib.request

    payload = json.dumps({
        "model": model_name,
        "messages": messages,
        "options": {"temperature": 0},
        "think": False,
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read())
    return result["message"]["content"]


def label_batch_ollama(
    model_name: str,
    sentences: list[str],
    batch_size: int,
    max_retries: int = 2,
    timeout: int = 600,
) -> list[dict]:
    """Send a batch of sentences to Ollama and parse the response."""
    user_prompt = build_user_prompt(sentences)

    messages = [
        {"role": "system", "content": BATCH_SYSTEM_PROMPT.format(batch_size=batch_size)},
        {"role": "user", "content": user_prompt},
    ]

    for attempt in range(max_retries + 1):
        try:
            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(timeout)

            output = _ollama_chat(model_name, messages, timeout=timeout)

            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

            parsed = parse_batch_response(output, batch_size)

            parse_errors = sum(1 for p in parsed if p["label"] == "PARSE_ERROR")
            if parse_errors == 0:
                return parsed
            if attempt < max_retries:
                time.sleep(2)
                continue
            return parsed

        except OllamaTimeout:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
            print(f"    Ollama call timed out after {timeout}s, retrying ({attempt+1}/{max_retries})...")
            if attempt < max_retries:
                time.sleep(5)
                continue
            return [{"label": "ERROR", "reasoning": f"Timed out after {timeout}s"} for _ in sentences]

        except Exception as e:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
            if attempt < max_retries:
                time.sleep(2)
                continue
            return [{"label": "ERROR", "reasoning": str(e)} for _ in sentences]


def label_batch_openai(
    model_name: str,
    sentences: list[str],
    batch_size: int,
    max_retries: int = 2,
) -> list[dict]:
    """Send a batch of sentences to an OpenAI-compatible API and parse the response."""
    from openai import OpenAI

    base_url = os.environ.get("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    api_key = os.environ.get("OPENAI_API_KEY", "")
    client = OpenAI(base_url=base_url, api_key=api_key)

    user_prompt = build_user_prompt(sentences)

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": BATCH_SYSTEM_PROMPT.format(batch_size=batch_size)},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
            )
            output = response.choices[0].message.content
            parsed = parse_batch_response(output, batch_size)

            parse_errors = sum(1 for p in parsed if p["label"] == "PARSE_ERROR")
            if parse_errors == 0:
                return parsed
            if attempt < max_retries:
                time.sleep(2)
                continue
            return parsed

        except Exception as e:
            is_rate_limit = "429" in str(e) or "rate" in str(e).lower()
            if is_rate_limit:
                wait = min(2 ** (attempt + 1) * 5, 120)
                print(f"    Rate limited (429), waiting {wait}s before retry...")
                time.sleep(wait)
                continue
            if attempt < max_retries:
                time.sleep(5)
                continue
            return [{"label": "ERROR", "reasoning": str(e)} for _ in sentences]


def label_batch_google(
    model_name: str,
    sentences: list[str],
    batch_size: int,
    max_retries: int = 2,
) -> list[dict]:
    """Send a batch of sentences to Google Gemini API and parse the response."""
    from google import genai

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    client = genai.Client(api_key=api_key)

    user_prompt = build_user_prompt(sentences)

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=BATCH_SYSTEM_PROMPT.format(batch_size=batch_size),
                    temperature=0,
                ),
            )
            output = response.text
            parsed = parse_batch_response(output, batch_size)

            parse_errors = sum(1 for p in parsed if p["label"] == "PARSE_ERROR")
            if parse_errors == 0:
                return parsed
            if attempt < max_retries:
                time.sleep(2)
                continue
            return parsed

        except Exception as e:
            is_rate_limit = "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "rate" in str(e).lower()
            if is_rate_limit:
                wait = min(2 ** (attempt + 1) * 5, 120)
                print(f"    Rate limited, waiting {wait}s before retry...")
                time.sleep(wait)
                continue
            if attempt < max_retries:
                time.sleep(5)
                continue
            return [{"label": "ERROR", "reasoning": str(e)} for _ in sentences]


def label_batch(
    model_name: str,
    sentences: list[str],
    batch_size: int,
    backend: str = "ollama",
    max_retries: int = 2,
    rate_limit_rpm: float | None = None,
    timeout: int = 600,
) -> list[dict]:
    """Send a batch of sentences to the chosen backend and parse the response."""
    if backend == "openai":
        return label_batch_openai(model_name, sentences, batch_size, max_retries)
    elif backend == "google":
        return label_batch_google(model_name, sentences, batch_size, max_retries)
    else:
        return label_batch_ollama(model_name, sentences, batch_size, max_retries, timeout)


def sample_sentences(
    input_csv: Path,
    tier_allocations: dict[str, int],
    seed: int = 42,
) -> list[dict]:
    """Sample sentences from input CSV stratified by tier."""
    by_tier = {"A": [], "B": [], "C": []}
    with open(input_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tier = row["tier"]
            if tier in by_tier:
                by_tier[tier].append(row)

    rng = random.Random(seed)
    sampled = []
    for tier, alloc in sorted(tier_allocations.items()):
        pool = by_tier.get(tier, [])
        n = min(alloc, len(pool))
        chosen = rng.sample(pool, n)
        for row in chosen:
            row["tier"] = tier
        sampled.extend(chosen)

    rng.shuffle(sampled)
    return sampled


def load_existing_results(output_csv: Path) -> set[str]:
    """Load already-labeled sentence texts to skip them on resume."""
    done = set()
    if not output_csv.exists():
        return done
    with open(output_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            done.add(row["text"])
    return done


def parse_tier_allocations(spec: str) -> dict[str, int]:
    """Parse tier allocation spec like 'A:400,B:900,C:700'."""
    allocs = {}
    for part in spec.split(","):
        tier, count = part.strip().split(":")
        allocs[tier.strip().upper()] = int(count.strip())
    return allocs


def main():
    parser = argparse.ArgumentParser(
        description="Label sentences in batches using Ollama, OpenAI-compatible, or Google Gemini CoT prompting."
    )
    parser.add_argument(
        "--input", type=Path, default=Path("data/processed/raw_sentences_10percent.csv"),
        help="Input CSV of candidate sentences (default: data/processed/raw_sentences_10percent.csv)",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/processed/sentence_labels_raw.csv"),
        help="Output CSV with labels (default: data/processed/sentence_labels_raw_<model>.csv)",
    )
    parser.add_argument(
        "--backend", choices=["ollama", "openai", "google", "auto"], default="auto",
        help="Backend: 'ollama' local, 'openai' OpenRouter/OpenAI, 'google' Gemini direct, "
             "'auto' to detect from model name (default: auto). "
             "Auto: 'gemini' → google, '/' → openai, ':' → ollama",
    )
    parser.add_argument(
        "--model", default="gemma4:31b",
        help="Model name. For Ollama: local model name (default: gemma4:31b). For openai: OpenRouter model ID (e.g. google/gemma-3-27b-it)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=5,
        help="Sentences per API call (default: 5)",
    )
    parser.add_argument(
        "--sample", type=str, default=None,
        help="Number of sentences to label, or 'all' for entire input. "
             "Overrides --tier-alloc (distributed 20%% A / 45%% B / 35%% C). "
             "Default without this flag: A:400,B:900,C:700 (2000 total)",
    )
    parser.add_argument(
        "--tier-alloc", type=str, default="A:400,B:900,C:700",
        help="Per-tier allocation, e.g. 'A:400,B:900,C:700' (default: 2000 total)",
    )
    parser.add_argument(
        "--timeout", type=int, default=600,
        help="Timeout in seconds per API call for Ollama (default: 600)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for sampling (default: 42)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Sample sentences and show counts without calling any API",
    )
    parser.add_argument(
        "--rate-limit", type=float, default=None,
        help="Max API requests per minute (default: auto). OpenRouter free: 20 RPM / 50 RPD. "
             "Google free: 10 RPM / 250 RPD. Paid: no limit. Ollama: no limit. "
             "Examples: --rate-limit 8 (safe for Google free), --rate-limit 0 (unlimited)",
    )
    args = parser.parse_args()

    # Auto-detect backend from model name
    if args.backend == "auto":
        if "gemini" in args.model.lower():
            args.backend = "google"
        elif "/" in args.model:
            args.backend = "openai"
        elif ":" in args.model:
            args.backend = "ollama"
        else:
            args.backend = "ollama"  # default fallback

    # Auto-detect rate limit for OpenRouter free tier
    rate_limit_rpm = args.rate_limit
    if rate_limit_rpm is None:
        if args.backend == "google":
            rate_limit_rpm = 8  # safe default for Gemini free tier (10 RPM)
        elif args.backend == "openai":
            rate_limit_rpm = 15  # safe default for OpenRouter free tier (20 RPM)
        else:
            rate_limit_rpm = 0  # Ollama has no rate limit
    # Compute inter-call sleep from rate limit
    inter_call_sleep = (60.0 / rate_limit_rpm) if rate_limit_rpm > 0 else 0

    # Determine tier allocations
    if args.sample:
        if args.sample.lower() == "all":
            # Count all sentences per tier in the input CSV
            tier_counts = {"A": 0, "B": 0, "C": 0}
            with open(args.input, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    t = row.get("tier", "")
                    if t in tier_counts:
                        tier_counts[t] += 1
            tier_allocs = tier_counts
        else:
            total = int(args.sample)
            tier_allocs = {"A": int(total * 0.20), "B": int(total * 0.45), "C": int(total * 0.35)}
            # Distribute remainder
            remainder = total - sum(tier_allocs.values())
            tier_allocs["B"] += remainder
    else:
        tier_allocs = parse_tier_allocations(args.tier_alloc)

    # Sample sentences
    print(f"Sampling from {args.input}...")
    print(f"  Tier allocations: A={tier_allocs['A']}, B={tier_allocs['B']}, C={tier_allocs['C']} (total={sum(tier_allocs.values())})")
    sentences = sample_sentences(args.input, tier_allocs, seed=args.seed)
    print(f"  Sampled {len(sentences)} sentences")

    if args.dry_run:
        from collections import Counter
        tier_counts = Counter(s["tier"] for s in sentences)
        print(f"\nDry run — tier breakdown:")
        for tier in ["A", "B", "C"]:
            print(f"  Tier {tier}: {tier_counts[tier]}")
        api_calls = (len(sentences) + args.batch_size - 1) // args.batch_size
        print(f"\nBackend: {args.backend}")
        print(f"Model: {args.model}")
        print(f"API calls needed: {api_calls}")
        if rate_limit_rpm > 0:
            print(f"Rate limit: {rate_limit_rpm:.0f} RPM ({inter_call_sleep:.1f}s between calls)")
            est_min = api_calls * inter_call_sleep / 60
            print(f"Estimated time (at rate limit): {est_min:.0f}min + inference time")
        print(f"To label: python scripts/label_sentences_batch.py --backend {args.backend} --model {args.model} --batch-size {args.batch_size}")
        return

    # If using default output, inject model name into filename
    if args.output == Path("data/processed/sentence_labels_raw.csv"):
        safe_model = args.model.replace(":", "-").replace("/", "_")
        args.output = Path(f"data/processed/sentence_labels_raw_{safe_model}.csv")

    # Append date suffix to output filename: stem-YYYY-MM-DD.suffix
    from datetime import date
    date_suffix = date.today().strftime("%Y-%m-%d")
    stem = args.output.stem
    args.output = args.output.with_name(f"{stem}-{date_suffix}{args.output.suffix}")

    # Validate backend requirements
    if args.backend == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            print("ERROR: OPENAI_API_KEY environment variable is required for openai backend.")
            print("  Set it with: export OPENAI_API_KEY=your-key")
            print("  For OpenRouter: export OPENAI_BASE_URL=https://openrouter.ai/api/v1")
            sys.exit(1)
    elif args.backend == "google":
        if not os.environ.get("GOOGLE_API_KEY"):
            print("ERROR: GOOGLE_API_KEY environment variable is required for google backend.")
            print("  Set it with: export GOOGLE_API_KEY=your-key")
            print("  Get one at: https://aistudio.google.com/apikey")
            sys.exit(1)

    # Load existing results for resume support
    done_texts = load_existing_results(args.output)
    if done_texts:
        print(f"  Resuming: {len(done_texts)} sentences already labeled, skipping them")

    # Filter out already-done sentences
    todo = [s for s in sentences if s["text"] not in done_texts]
    print(f"  Remaining to label: {len(todo)}")

    if not todo:
        print("Nothing to label. Exiting.")
        return

    # Warn if daily request budget may exceed free-tier limits
    total_api_calls = (len(todo) + args.batch_size - 1) // args.batch_size
    if args.backend == "openai" and rate_limit_rpm <= 20 and total_api_calls > 50:
        print(f"\nWARNING: {total_api_calls} API calls needed, but OpenRouter free tier allows only 50/day.")
        print("  Options: add credits ($10+) to raise to 1000/day, use --rate-limit 0 (paid tier),")
        print("  or reduce --sample. Resume will pick up where you left off if you hit the daily limit.")
    elif args.backend == "google" and rate_limit_rpm <= 10 and total_api_calls > 250:
        print(f"\nWARNING: {total_api_calls} API calls needed, but Google free tier allows only 250/day.")
        print("  Options: enable billing to raise limits, use --rate-limit 0 (paid tier),")
        print("  or reduce --sample. Resume will pick up where you left off if you hit the daily limit.")

    # Prepare output file
    fieldnames = [
        "text", "source", "year", "state", "tier",
        "label", "reasoning", "model",
        "relevance_score", "passes_spacy", "has_action_verb",
    ]
    file_exists = args.output.exists()
    if not file_exists:
        args.output.parent.mkdir(parents=True, exist_ok=True)

    # Open in append mode for incremental saving
    out_f = open(args.output, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(out_f, fieldnames=fieldnames)
    if not file_exists:
        writer.writeheader()
        out_f.flush()

    # Label in batches
    total_batches = (len(todo) + args.batch_size - 1) // args.batch_size
    total_labeled = 0
    total_errors = 0
    start_time = time.time()

    print(f"\nLabeling {len(todo)} sentences in {total_batches} batches (batch_size={args.batch_size})")
    if args.backend == "ollama":
        print(f"Loading model {args.model} (first batch may be slow while Ollama loads it into memory)...")
        if args.batch_size > 2 and "glm" in args.model.lower():
            print(f"WARNING: glm models may hang with batch_size > 2. Consider --batch-size 2 --timeout 300.")
    if rate_limit_rpm > 0:
        print(f"Rate limit: {rate_limit_rpm:.0f} RPM ({inter_call_sleep:.1f}s between calls)")
    else:
        print("Rate limit: none")

    for batch_idx in range(total_batches):
        start = batch_idx * args.batch_size
        end = min(start + args.batch_size, len(todo))
        batch = todo[start:end]
        batch_texts = [s["text"] for s in batch]
        actual_batch_size = len(batch)

        call_start = time.time()
        results = label_batch(
            args.model, batch_texts, actual_batch_size,
            backend=args.backend, rate_limit_rpm=rate_limit_rpm,
            timeout=args.timeout,
        )
        call_elapsed = time.time() - call_start

        # Throttle to stay within rate limit
        if inter_call_sleep > 0 and batch_idx < total_batches - 1:
            time.sleep(inter_call_sleep)

        for i, (sent, result) in enumerate(zip(batch, results)):
            label = result["label"]
            reasoning = result["reasoning"]
            is_error = label in ("PARSE_ERROR", "ERROR")

            if is_error:
                total_errors += 1

            row = {
                "text": sent["text"],
                "source": sent["source"],
                "year": sent["year"],
                "state": sent["state"],
                "tier": sent["tier"],
                "label": label,
                "reasoning": reasoning,
                "model": args.model,
                "relevance_score": sent.get("relevance_score", ""),
                "passes_spacy": sent.get("passes_spacy", ""),
                "has_action_verb": sent.get("has_action_verb", ""),
            }
            writer.writerow(row)
            total_labeled += 1

        out_f.flush()

        # Progress
        elapsed = time.time() - start_time
        rate = (batch_idx + 1) / elapsed if elapsed > 0 else 0
        eta = (total_batches - batch_idx - 1) / rate if rate > 0 else 0
        call_str = f"{call_elapsed:.0f}s" if call_elapsed < 60 else f"{call_elapsed/60:.1f}min"
        print(
            f"  [{batch_idx+1}/{total_batches}] "
            f"{total_labeled} labeled, {total_errors} errors | "
            f"Call: {call_str} | Elapsed: {elapsed/60:.0f}min | ETA: {eta/60:.0f}min"
        )

    out_f.close()

    elapsed = time.time() - start_time
    print(f"\nDone. {total_labeled} labeled, {total_errors} errors in {elapsed/60:.1f}min")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()