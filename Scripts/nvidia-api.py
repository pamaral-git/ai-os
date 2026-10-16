#!/usr/bin/env python3
import os
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Any

# Paths & Settings
CACHE_FILE = Path.home() / ".cache" / "nvidia_models_cache.json"
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_MODELS_URL = "https://integrate.api.nvidia.com/v1/models"
CRAWL4AI_URL = "http://[Insert_IP]/md"
CRAWL4AI_TOKEN = os.getenv(
    "CRAWL4AI_API_TOKEN",
    "[Insert]"
)


def get_optimal_params(model_id: str) -> Dict[str, Any]:
    """Assigns optimal inference parameters based on model architecture/purpose."""
    m = model_id.lower()

    # Reasoning / Math / Strict Logic
    if any(k in m for k in ["r1", "reason", "math"]):
        return {
            "temperature": 0.2,
            "top_p": 0.95,
            "max_tokens": 8192,
            "stream": True,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0
        }
    # Coding / Function Calling / Tool Use
    elif any(k in m for k in ["coder", "code", "dev", "instruct-fp8"]):
        return {
            "temperature": 0.2,
            "top_p": 0.90,
            "max_tokens": 4096,
            "stream": True,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0
        }
    # Multimodal / Vision
    elif any(k in m for k in ["vision", "vl", "ocr", "multimodal"]):
        return {
            "temperature": 0.3,
            "top_p": 0.90,
            "max_tokens": 4096,
            "stream": True,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0
        }
    # General Chat / Creative / Assistant
    else:
        return {
            "temperature": 0.6,
            "top_p": 0.90,
            "max_tokens": 4096,
            "stream": True,
            "presence_penalty": 0.1,
            "frequency_penalty": 0.1
        }


def fetch_models_via_api() -> List[Dict[str, Any]]:
    """Fetch directly from NVIDIA NIM OpenAI-compatible API."""
    headers = {"Accept": "application/json"}
    if NVIDIA_API_KEY:
        headers["Authorization"] = f"Bearer {NVIDIA_API_KEY}"

    req = urllib.request.Request(NVIDIA_MODELS_URL, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
        return data.get("data", [])


def fetch_models_via_crawl4ai() -> List[Dict[str, Any]]:
    """Fallback: Scrape build.nvidia.com/models using your local Crawl4AI instance."""
    payload = json.dumps({
        "url": "https://build.nvidia.com/models",
        "f": "raw"
    }).encode()

    req = urllib.request.Request(
        CRAWL4AI_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CRAWL4AI_TOKEN}"
        }
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read().decode()

    # Extract unique model slugs/identifiers from raw content
    import re
    matches = set(re.findall(r'href="/([a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+)"', content))
    models = []
    for slug in matches:
        if not any(x in slug for x in ["api/", "docs", "_next", "models"]):
            models.append({"id": slug, "created": int(time.time())})
    return models


def load_cached_ids() -> set[str]:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_cached_ids(ids: set[str]):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(sorted(list(ids)), f, indent=2)


def main():
    force_all = "--all" in sys.argv

    print("[*] Fetching NVIDIA model catalog...", file=sys.stderr)
    try:
        models = fetch_models_via_api()
    except Exception as e:
        print(f"[!] API fetch failed ({e}). Falling back to local Crawl4AI...", file=sys.stderr)
        models = fetch_models_via_crawl4ai()

    if not models:
        print("[!] No models found.", file=sys.stderr)
        return

    cached_ids = load_cached_ids()
    current_ids = {m["id"] for m in models}

    if force_all or not cached_ids:
        target_ids = current_ids
        print(f"[*] Processing all {len(target_ids)} models...", file=sys.stderr)
    else:
        target_ids = current_ids - cached_ids
        print(f"[*] Found {len(target_ids)} newly added models.", file=sys.stderr)

    if not target_ids:
        print("[✓] No new models detected. Run with `--all` to dump all models.", file=sys.stderr)
        return

    endpoint_entries = []
    for model_id in sorted(target_ids):
        params = get_optimal_params(model_id)
        endpoint_entries.append({
            "name": f"nvidia/{model_id}",
            "model": model_id,
            "base_url": "https://integrate.api.nvidia.com/v1",
            "api_key": "${NVIDIA_API_KEY}",
            "type": "openai",
            "parameters": params
        })

    # Save cache
    save_cached_ids(current_ids)

    # Output formatted JSON block
    print(json.dumps(endpoint_entries, indent=2))


if __name__ == "__main__":
    main()
