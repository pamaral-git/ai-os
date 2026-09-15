#!/usr/bin/env python3
"""
  llama-swap-to-cli.py — Convert llama-swap YAML configurations into valid llama-cli commands and markdown.

Features:
- Recursive macro resolution (resolving nested macros like ${agent} -> ${basic}).
- Complete filtering of server-only flags (both value-taking and valueless/boolean flags).
- Conversion of filters.setParams into standard llama-cli sampling flags.
- Native support for chat_template_kwargs via --chat-template-kwargs '<json>'.
- Standardized ordering of CLI options.
- M4 Apple Silicon optimization: default injection of -t 4 -tb 4 -b 2048 -ub 1024.

Use the following commands:

docker run --rm \
  -v "/your/path/with/llama-swap.yaml:/models:ro" \
  -v "/your/path/to/this/script/llama-swap-to-cli.py:/scripts:ro" \
  -v "/the/output/path/for/llama-cli.md:/out" \
  python:3.11-slim \
  sh -c "pip install --no-cache-dir pyyaml >/dev/null 2>&1 && python3 /scripts/swap2climd.py /your/llama-swap.yaml -o /out/llama-cli.md"

"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import yaml
except ImportError:
    sys.exit("Error: PyYAML is required. Please install it via 'pip install pyyaml'.")


class RawFloat(float):
    """Preserves original string formatting of floats (e.g. '0.60' instead of '0.6')."""
    raw: str | None = None

    def __new__(cls, value: float, raw: str | None = None) -> RawFloat:
        self = super().__new__(cls, value)
        self.raw = raw
        return self


class RawLoader(yaml.SafeLoader):
    pass


RawLoader.add_constructor(
    "tag:yaml.org/1.0/float",
    lambda loader, node: RawFloat(float(node.value), node.value)
)


def fmt_val(val: Any) -> str:
    if isinstance(val, RawFloat) and val.raw is not None:
        return val.raw
    if isinstance(val, float):
        return f"{val:.4f}".rstrip("0").rstrip(".") if not str(val).endswith(".0") else str(val)
    if isinstance(val, bool):
        return "on" if val else "off"
    return str(val)


SERVER_VALUE_FLAGS: Set[str] = {
    "--host",
    "--port",
    "--alias",
    "--api-key",
    "--ui-config-file",
    "--mcp-servers-config",
    "--tools",
    "--slots-endpoint-disable",
    "--metrics",
    "--props",
    "--webui-path",
}

SERVER_BOOL_FLAGS: Set[str] = {
    "--ui-mcp-proxy",
    "--no-mcp",
    "--webui",
    "--no-webui",
    "--public",
    "--log-requests",
    "--log-format",
    "--no-slots",
    "--embeddings",
    "--rerank",
}

PARAM_MAPPING: List[Tuple[str, str]] = [
    ("temperature", "--temp"),
    ("top_p", "--top-p"),
    ("top_k", "--top-k"),
    ("min_p", "--min-p"),
    ("repeat_penalty", "--repeat-penalty"),
    ("presence_penalty", "--presence-penalty"),
    ("frequency_penalty", "--frequency-penalty"),
    ("mirostat", "--mirostat"),
    ("mirostat_tau", "--mirostat-tau"),
    ("mirostat_eta", "--mirostat-eta"),
    ("seed", "--seed"),
]

PLACEHOLDER_REGEX = re.compile(r"^\$\{[A-Za-z0-9_.-]+\}$")


def expand_macros(text: str, macros: Dict[str, Any]) -> str:
    """Recursively expands ${macro} placeholders."""
    if not macros:
        return text
    keys_sorted = sorted(macros.keys(), key=len, reverse=True)
    for _ in range(16):
        changed = False
        for k in keys_sorted:
            token = f"${{{k}}}"
            if token in text:
                text = text.replace(token, str(macros[k]))
                changed = True
        if not changed:
            break
    return text


def clean_tokens(cmd_str: str) -> List[str]:
    """Tokenizes shell string, drops llama-server executable and server-specific options."""
    try:
        tokens = shlex.split(cmd_str)
    except ValueError:
        tokens = cmd_str.split()

    if tokens and ("llama-server" in tokens[0] or "llama-swap" in tokens[0]):
        tokens = tokens[1:]

    out: List[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]

        if tok in SERVER_VALUE_FLAGS:
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                i += 2
            else:
                i += 1
            continue

        if tok in SERVER_BOOL_FLAGS:
            i += 1
            continue

        if PLACEHOLDER_REGEX.match(tok):
            i += 1
            continue

        out.append(tok)
        i += 1

    return out


def parse_cli_tokens(tokens: List[str]) -> Dict[str, Any]:
    """Sorts CLI tokens into logical groups."""
    parsed: Dict[str, Any] = {
        "model": None,
        "mmproj": None,
        "ctx": [],
        "cache": [],
        "engine": [],
        "vision": [],
        "reasoning": [],
    }

    i = 0
    while i < len(tokens):
        tok = tokens[i]

        if tok in ("-m", "--model") and i + 1 < len(tokens):
            parsed["model"] = tokens[i + 1]
            i += 2
        elif tok in ("--mmproj", "-mm") and i + 1 < len(tokens):
            parsed["mmproj"] = tokens[i + 1]
            i += 2
        elif tok in ("-c", "--ctx-size", "--context-size") and i + 1 < len(tokens):
            parsed["ctx"] = ["-c", tokens[i + 1]]
            i += 2
        elif tok in ("--cache-type-k", "-ctk", "--cache-type-v", "-ctv") and i + 1 < len(tokens):
            parsed["cache"].extend([tok, tokens[i + 1]])
            i += 2
        elif tok.startswith("--image") and i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
            parsed["vision"].extend([tok, tokens[i + 1]])
            i += 2
        elif tok.startswith("--reasoning"):
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                parsed["reasoning"].extend([tok, tokens[i + 1]])
                i += 2
            else:
                parsed["reasoning"].append(tok)
                i += 1
        elif tok in ("-ngl", "--n-gpu-layers", "-fa", "--flash-attn", "-t", "--threads", "-tb", "--threads-batch", "-b", "--batch-size", "-ub", "--ubatch-size", "--parallel", "-np"):
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                if tok in ("--parallel", "-np") and tokens[i + 1] == "1":
                    i += 2
                    continue
                parsed["engine"].extend([tok, tokens[i + 1]])
                i += 2
            else:
                parsed["engine"].append(tok)
                i += 1
        else:
            parsed["engine"].append(tok)
            i += 1

    return parsed


def extract_params(set_params: Optional[Dict[str, Any]]) -> Tuple[List[str], Optional[str]]:
    """Translates filters.setParams into CLI sampling flags and template kwargs."""
    if not set_params:
        return [], None

    sampling_flags: List[str] = []
    for key, flag in PARAM_MAPPING:
        if key in set_params and set_params[key] is not None:
            sampling_flags.extend([flag, fmt_val(set_params[key])])

    if "reasoning_budget" in set_params and set_params["reasoning_budget"] is not None:
        sampling_flags.extend(["--reasoning-budget", fmt_val(set_params["reasoning_budget"])])

    chat_kwargs = set_params.get("chat_template_kwargs")
    chat_kwargs_str = None
    if isinstance(chat_kwargs, dict) and chat_kwargs:
        chat_kwargs_str = json.dumps(chat_kwargs, separators=(",", ":"))

    return sampling_flags, chat_kwargs_str


def format_command(
    parsed: Dict[str, Any],
    sampling: List[str],
    chat_kwargs: Optional[str],
    hardware_optimize: bool = True
) -> str:
    """Renders formatted multi-line command with line continuation backslashes."""
    lines: List[str] = [f"llama-cli -m {parsed['model']}"]

    if parsed["mmproj"]:
        lines.append(f"--mmproj {parsed['mmproj']}")

    if parsed["vision"]:
        lines.append(" ".join(parsed["vision"]))

    engine_flags = list(parsed["engine"])
    if hardware_optimize:
        if not any(f in engine_flags for f in ("-t", "--threads")):
            engine_flags.extend(["-t", "4"])
        if not any(f in engine_flags for f in ("-tb", "--threads-batch")):
            engine_flags.extend(["-tb", "4"])
        if not any(f in engine_flags for f in ("-b", "--batch-size")):
            engine_flags.extend(["-b", "2048"])
        if not any(f in engine_flags for f in ("-ub", "--ubatch-size")):
            engine_flags.extend(["-ub", "1024"])

    if engine_flags:
        lines.append(" ".join(engine_flags))

    if parsed["cache"]:
        lines.append(" ".join(parsed["cache"]))

    if parsed["ctx"]:
        lines.append(" ".join(parsed["ctx"]))

    if parsed["reasoning"]:
        lines.append(" ".join(parsed["reasoning"]))

    if sampling:
        lines.append(" ".join(sampling))

    if chat_kwargs:
        lines.append(f"--chat-template-kwargs '{chat_kwargs}'")

    formatted: List[str] = []
    for idx, line in enumerate(lines):
        indent = "" if idx == 0 else "  "
        suffix = " \\" if idx < len(lines) - 1 else ""
        formatted.append(f"{indent}{line}{suffix}")

    return "\n".join(formatted)


def convert_config(config_path: str, hardware_optimize: bool = True) -> str:
    """Parses YAML configuration and outputs full Markdown documentation with commands."""
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.load(f, Loader=RawLoader)

    macros = cfg.get("macros") or {}
    models = cfg.get("models") or {}

    if not models:
        sys.exit("Error: No models found in configuration file.")

    blocks: List[str] = []
    for key, m_cfg in models.items():
        if not isinstance(m_cfg, dict) or "cmd" not in m_cfg:
            continue

        raw_cmd = m_cfg["cmd"]
        if isinstance(raw_cmd, (list, tuple)):
            raw_cmd = " ".join(str(x) for x in raw_cmd)

        expanded_cmd = expand_macros(str(raw_cmd), macros)
        tokens = clean_tokens(expanded_cmd)
        parsed = parse_cli_tokens(tokens)

        if not parsed["model"]:
            continue

        set_params = (m_cfg.get("filters") or {}).get("setParams") or {}
        sampling, chat_kwargs = extract_params(set_params)

        cmd_rendered = format_command(parsed, sampling, chat_kwargs, hardware_optimize=hardware_optimize)
        
        display_name = m_cfg.get("name") or key
        desc = m_cfg.get("description", "")
        desc_line = f"\n_{desc}_\n" if desc else "\n"
        
        block = f"### {display_name} (`{key}`){desc_line}\n```bash\n{cmd_rendered}\n```"
        blocks.append(block)

    header = (
        "# llama-cli Command Cheat Sheet\n\n"
        f"_Auto-generated from `{config_path}`. Server-only flags stripped, macros expanded, "
        "and M4 4-performance-core affinity applied._\n\n"
    )
    return header + "\n\n".join(blocks) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Convert llama-swap YAML config to llama-cli commands.")
    parser.add_argument("config", nargs="?", default="/your/path/with/llama-swap.yaml", help="Path to llama-swap config YAML")
    parser.add_argument("-o", "--output", default="-", help="Output file (default: stdout)")
    parser.add_argument("--no-hw-opt", action="store_true", help="Do not auto-inject M4 thread / batch flags")
    args = parser.parse_args()

    doc = convert_config(args.config, hardware_optimize=not args.no_hw_opt)

    if args.output == "-":
        sys.stdout.write(doc)
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(doc)
        print(f"Successfully wrote {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
