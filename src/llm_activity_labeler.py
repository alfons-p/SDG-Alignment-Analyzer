"""LLM-based activity labeling module using Ollama.

Supports both single-server and multi-server configurations with load balancing.
Multi-server mode enables true parallelism for faster processing.
"""

import json
import subprocess
import os
from typing import Dict, List, Optional, Any, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import itertools


class LLMActivityLabeler:
    """Label extracted activities using LLM for intuitive descriptions.

    Supports multi-server mode for parallel processing across multiple Ollama instances.
    """

    def __init__(
        self,
        model: str = "kimi-k2.5:cloud",
        ollama_hosts: Optional[List[str]] = None,
        timeout: int = 120
    ):
        """
        Initialize the LLM labeler.

        Args:
            model: Ollama model name to use for labeling
            ollama_hosts: List of Ollama server URLs for multi-server mode.
                         If None, uses single server (default Ollama behavior)
            timeout: Timeout for each Ollama call in seconds
        """
        self.model = model
        self.timeout = timeout

        # Multi-server configuration
        if ollama_hosts:
            self.ollama_hosts = ollama_hosts
            self.multi_server = True
            self._host_iterator = itertools.cycle(ollama_hosts)
            self._host_lock = threading.Lock()
        else:
            self.ollama_hosts = None
            self.multi_server = False
            self._host_iterator = None
            self._host_lock = None

        self.system_prompt = """You are an expert in analyzing local government annual reports and identifying sustainable development activities.

Your task is to generate concise, intuitive labels for council activities extracted from annual reports.

Given a raw activity text, generate:
1. A short label (3-6 words) that describes the activity type
2. A category (e.g., "Housing", "Education", "Environment", "Governance", "Economic")
3. Key entities mentioned (programs, locations, initiatives)

Output ONLY a JSON object with this structure:
{
    "label": "Concise activity description",
    "category": "Category name",
    "entities": ["entity1", "entity2"],
    "summary": "One-sentence summary of what was done"
}

Be specific and use council terminology."""

    def _get_next_host(self) -> str:
        """Get next Ollama host in round-robin fashion (thread-safe)."""
        if not self.multi_server:
            return "http://localhost:11434"

        with self._host_lock:
            return next(self._host_iterator)

    def _call_ollama(self, prompt: str, temperature: float = 0.3) -> str:
        """
        Call Ollama API with the given prompt.

        Args:
            prompt: The prompt to send to the model
            temperature: Sampling temperature (lower = more focused)

        Returns:
            Model response text
        """
        host = self._get_next_host()

        # Set OLLAMA_HOST for this call if using multi-server
        env = os.environ.copy()
        if self.multi_server:
            # Extract host:port from URL
            if host.startswith("http://"):
                host_addr = host[7:]  # Remove http://
            elif host.startswith("https://"):
                host_addr = host[8:]  # Remove https://
            else:
                host_addr = host
            env["OLLAMA_HOST"] = host_addr

        try:
            # Use ollama command line
            result = subprocess.run(
                [
                    "ollama", "run", self.model,
                    "--format", "json",
                ],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env
            )

            if result.returncode != 0:
                print(f"Ollama error: {result.stderr}")
                return None

            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            print(f"Ollama call timed out ({self.timeout}s)")
            return None
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return None

    def label_activity(self, activity_text: str, context: str = "") -> Dict[str, Any]:
        """
        Generate an intuitive label for an activity.

        Args:
            activity_text: Raw extracted activity text
            context: Optional surrounding context

        Returns:
            Dictionary with label, category, entities, summary
        """
        prompt = f"""{self.system_prompt}

Raw Activity Text:
```
{activity_text}
```

{f'Context: {context}' if context else ''}

Generate a JSON response with the label, category, entities, and summary."""

        response = self._call_ollama(prompt)

        if not response:
            # Fallback if LLM fails
            return {
                "label": self._generate_fallback_label(activity_text),
                "category": "General",
                "entities": [],
                "summary": activity_text[:100] + "..." if len(activity_text) > 100 else activity_text,
                "llm_error": True
            }

        try:
            # Try to parse JSON response
            # Sometimes Ollama returns markdown code blocks
            cleaned = response
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0]

            result = json.loads(cleaned.strip())
            result["llm_error"] = False
            return result

        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "label": self._generate_fallback_label(activity_text),
                "category": "General",
                "entities": [],
                "summary": activity_text[:100] + "..." if len(activity_text) > 100 else activity_text,
                "raw_response": response,
                "llm_error": True
            }

    def _generate_fallback_label(self, text: str) -> str:
        """Generate a simple label when LLM fails."""
        # Extract first few meaningful words
        words = text.split()
        if len(words) >= 4:
            return " ".join(words[:4]).capitalize()
        return text[:30] if len(text) > 30 else text

    def label_activities(self, activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Label multiple activities with LLM (sequential).

        Args:
            activities: List of activity dictionaries

        Returns:
            Activities with added 'llm_label' field
        """
        labeled_activities = []

        print(f"\nLabeling {len(activities)} activities with LLM ({self.model})...")
        if self.multi_server:
            print(f"Multi-server mode: {len(self.ollama_hosts)} servers")

        for i, activity in enumerate(activities, 1):
            print(f"  Labeling activity {i}/{len(activities)}...", end=" ")

            label_data = self.label_activity(activity["text"])

            # Merge LLM label data into activity
            activity_with_label = activity.copy()
            activity_with_label["llm_label"] = label_data.get("label", "")
            activity_with_label["category"] = label_data.get("category", "General")
            activity_with_label["entities"] = label_data.get("entities", [])
            activity_with_label["summary"] = label_data.get("summary", "")
            activity_with_label["llm_error"] = label_data.get("llm_error", False)

            labeled_activities.append(activity_with_label)

            status = "✓" if not label_data.get("llm_error") else "✗ (fallback)"
            print(f"{status} - {activity_with_label['llm_label'][:50]}")

        return labeled_activities

    def label_activities_parallel(
        self,
        activities: List[Dict[str, Any]],
        max_workers: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Label multiple activities with LLM using parallel threading.

        In multi-server mode, activities are distributed across all configured
        Ollama instances for maximum throughput.

        Args:
            activities: List of activity dictionaries
            max_workers: Number of parallel threads (default: 4)

        Returns:
            Activities with added 'llm_label' field
        """
        labeled_activities = [None] * len(activities)
        completed = 0
        failed = 0
        lock = threading.Lock()

        print(f"\nLabeling {len(activities)} activities with LLM ({self.model})...")
        print(f"Using {max_workers} parallel threads...")
        if self.multi_server:
            print(f"Multi-server mode: {len(self.ollama_hosts)} Ollama instances")

        def label_single_activity(idx_activity):
            nonlocal completed, failed
            idx, activity = idx_activity

            label_data = self.label_activity(activity["text"])

            activity_with_label = activity.copy()
            activity_with_label["llm_label"] = label_data.get("label", "")
            activity_with_label["category"] = label_data.get("category", "General")
            activity_with_label["entities"] = label_data.get("entities", [])
            activity_with_label["summary"] = label_data.get("summary", "")
            activity_with_label["llm_error"] = label_data.get("llm_error", False)

            with lock:
                labeled_activities[idx] = activity_with_label
                completed += 1
                status = "✓" if not label_data.get("llm_error") else "✗"
                if label_data.get("llm_error"):
                    failed += 1
                print(f"  [{completed}/{len(activities)}] {status} {activity_with_label['llm_label'][:50]}")

            return activity_with_label

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(executor.map(label_single_activity, enumerate(activities)))

        print(f"\nCompleted: {completed} labeled, {failed} fallback")
        return labeled_activities

    def batch_label_activities(
        self,
        activities: List[Dict[str, Any]],
        batch_size: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Label activities in batches for efficiency.

        Args:
            activities: List of activity dictionaries
            batch_size: Number of activities to label per batch

        Returns:
            Activities with added 'llm_label' field
        """
        labeled_activities = []
        total = len(activities)

        print(f"\nLabeling {total} activities in batches of {batch_size}...")

        for i in range(0, total, batch_size):
            batch = activities[i:i + batch_size]
            print(f"\nBatch {i//batch_size + 1}/{(total-1)//batch_size + 1}:")

            for j, activity in enumerate(batch, 1):
                print(f"  {j}. ", end="")
                label_data = self.label_activity(activity["text"])

                activity_with_label = activity.copy()
                activity_with_label["llm_label"] = label_data.get("label", "")
                activity_with_label["category"] = label_data.get("category", "General")
                activity_with_label["entities"] = label_data.get("entities", [])
                activity_with_label["summary"] = label_data.get("summary", "")
                activity_with_label["llm_error"] = label_data.get("llm_error", False)

                labeled_activities.append(activity_with_label)
                print(f"{activity_with_label['llm_label'][:50]}")

        return labeled_activities


def label_activity_simple(text: str) -> str:
    """
    Simple standalone function to label a single activity.

    Args:
        text: Activity text to label

    Returns:
        Generated label
    """
    labeler = LLMActivityLabeler()
    result = labeler.label_activity(text)
    return result.get("label", text[:50])
