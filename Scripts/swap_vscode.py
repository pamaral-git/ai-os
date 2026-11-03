#!/usr/bin/env python3
"""
Reads a llama-swap config.yaml and generates a VS Code customendpoint provider
snippet {llama-swap -> VS Code chatLanguageModels.json converter}

Usage:
  python llama_swap_to_vscode.py --config config.yaml --base-url http://127.0.0.1:8080/v1/chat/completions
  python llama_swap_to_vscode.py --config config.yaml --include-aliases --provider-name llama-swap
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

DEFAULT_BASE_URL = "http://127.0.0.1:8080/v1/chat/completions"
DEFAULT_MAX_OUTPUT = 4096
DEFAULT_OVERHEAD = 4096

def is_embedding_model(model_cfg: dict) -> bool:
    cmd = model_cfg.get("cmd", "")
    if isinstance(cmd, list):
        cmd = " ".join(cmd)
    cmd_lower = str(cmd).lower()
    return "--embedding" in cmd_lower

def parse_args():
    p = argparse.ArgumentParser(description="Convert llama-swap config.yaml to VS Code chatLanguageModels.json snippet")
    p.add_argument("--config", "-c", default="config.yaml", help="Path to llama-swap config.yaml")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL for chat completions (llama-swap listen endpoint)")
    p.add_argument("--provider-name", default="llama-cpp", help="Provider name field")
    p.add_argument("--vendor", default="customendpoint", help="Vendor field (usually customendpoint)")
    p.add_argument("--api-key", default="sk-local-no-key-required", help="API key placeholder")
    p.add_argument("--api-type", default="chat-completions", help="apiType, usually chat-completions")
    p.add_argument("--include-aliases", action="store_true", help="Also create entries for aliases (includeAliasesInList)")
    p.add_argument("--include-embedding", action="store_true", help="Include embedding models (filtered by default)")
    p.add_argument("--max-output", type=int, default=DEFAULT_MAX_OUTPUT, help="maxOutputTokens per model")
    p.add_argument("--overhead", type=int, default=DEFAULT_OVERHEAD, help="Tokens reserved from context for output (context - overhead = maxInputTokens)")
    p.add_argument("--output", "-o", help="Output JSON file (default: stdout)")
    p.add_argument("--dedup", action="store_true", default=True, help="Deduplicate by id (default on)")
    p.add_argument("--no-dedup", dest="dedup", action="store_false", help="Disable deduplication")
    return p.parse_args()

def load_config(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict) or "models" not in data:
        raise ValueError(f"{path} does not contain a 'models' dict")
    return data

def build_model_entry(model_id: str, cfg: dict, base_url: str, max_output: int, overhead: int):
    if not cfg:
        cfg = {}
    name = cfg.get("name") or model_id
    caps = cfg.get("capabilities") or {}
    ctx = caps.get("context")
    in_mods = caps.get("in") or []
    has_vision = "image" in [str(x).lower() for x in in_mods]
    tools_enabled = caps.get("tools")
    if tools_enabled is None:
        tools_enabled = False
    if isinstance(ctx, int) and ctx > overhead:
        max_input = ctx - overhead
        max_input = max(1024, max_input)
    else:
        max_input = 32768
        if isinstance(ctx, int):
            max_input = ctx

    entry = {
        "id": model_id,
        "name": name,
        "url": base_url,
        "toolCalling": bool(tools_enabled),
        "vision": bool(has_vision),
        "maxInputTokens": int(max_input),
        "maxOutputTokens": int(max_output),
    }
    return entry

def main():
    args = parse_args()
    cfg_path = Path(args.config)
    if not cfg_path.exists():
        print(f"Config not found: {cfg_path}", file=sys.stderr)
        sys.exit(1)

    data = load_config(cfg_path)
    models_dict = data.get("models", {})
    include_aliases_in_list = data.get("includeAliasesInList", False) or args.include_aliases

    entries = []
    seen_ids = set()

    for model_key, model_cfg in models_dict.items():
        model_cfg = model_cfg or {}
        if not args.include_embedding and is_embedding_model(model_cfg):
            continue

        entry = build_model_entry(model_key, model_cfg, args.base_url, args.max_output, args.overhead)
        if args.dedup and entry["id"] in seen_ids:
            continue
        entries.append(entry)
        seen_ids.add(entry["id"])

        if include_aliases_in_list:
            aliases = model_cfg.get("aliases") or []
            for alias in aliases:
                alias_id = str(alias).strip()
                if not alias_id:
                    continue
                if args.dedup and alias_id in seen_ids:
                    continue
                alias_entry = build_model_entry(alias_id, model_cfg, args.base_url, args.max_output, args.overhead)
                alias_entry["name"] = f"{model_cfg.get('name', model_key)} ({alias_id})"
                entries.append(alias_entry)
                seen_ids.add(alias_id)

    entries.sort(key=lambda m: m["name"].lower())

    provider = {
        "name": args.provider_name,
        "vendor": args.vendor,
        "apiKey": args.api_key,
        "apiType": args.api_type,
        "models": entries
    }

    output_json = json.dumps(provider, indent=2, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output_json + "\n", encoding="utf-8")
        print(f"Wrote {len(entries)} models to {args.output}")
    else:
        print(output_json)

if __name__ == "__main__":
    main()
