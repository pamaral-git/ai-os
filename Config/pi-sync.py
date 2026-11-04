#!/usr/bin/env python3
"""
Sync live models from llama-swap (port 8080) into ~/.pi/agent/models.json.
Automatically updates contextWindow, maxTokens, vision/text inputs, and removes deprecated models.
"""
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

LLAMA_SWAP_URL = "http://127.0.0.1:8080/v1"
MODELS_JSON_PATH = Path.home() / ".pi" / "agent" / "models.json"

def fetch_models():
    url = f"{LLAMA_SWAP_URL}/models"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pi-sync/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status != 200:
                print(f"Error: llama-swap returned HTTP {resp.status}", file=sys.stderr)
                return None
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"Error connecting to llama-swap at {url}: {e}", file=sys.stderr)
        return None

def main():
    catalog = fetch_models()
    if not catalog or "data" not in catalog:
        print("Failed to sync: llama-swap is not running or unreachable on port 8080.", file=sys.stderr)
        sys.exit(1)

    existing = {}
    if MODELS_JSON_PATH.exists():
        try:
            with open(MODELS_JSON_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}

    if "providers" not in existing or not isinstance(existing["providers"], dict):
        existing["providers"] = {}

    models = []
    for m in catalog.get("data", []):
        model_id = m.get("id")
        if not model_id:
            continue
        name = m.get("name", model_id)
        ctx = m.get("context_length") or m.get("context_window") or 32768
        arch = m.get("architecture", {})
        input_modalities = arch.get("input_modalities", ["text"])
        inputs = ["text"]
        if "image" in input_modalities:
            inputs.append("image")

        models.append({
            "id": model_id,
            "name": name,
            "contextWindow": ctx,
            "maxTokens": ctx,
            "input": inputs
        })

    # Sort models alphabetically by id
    models.sort(key=lambda x: x["id"])

    existing["providers"]["llama-swap"] = {
        "baseUrl": LLAMA_SWAP_URL,
        "api": "openai-completions",
        "apiKey": "local",
        "compat": {
            "supportsDeveloperRole": False,
            "supportsReasoningEffort": True
        },
        "models": models
    }

    MODELS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODELS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)
        f.write("\n")

    print(f"✓ Synced {len(models)} models from llama-swap into {MODELS_JSON_PATH}:")
    for m in models:
        modalities = "+".join(m["input"])
        print(f"  • {m['id']:<20} ({m['name']}, ctx: {m['contextWindow']}, {modalities})")

if __name__ == "__main__":
    main()
