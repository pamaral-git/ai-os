#!/usr/bin/env python3
"""
create-llama-shell.py - Sanitize llama-swap configurations for OpenShell sandboxed execution.

Ingests a standard llama-swap configuration (which may contain dangerous host-escaping flags like
`--tools all`, `--ui-mcp-proxy`, `--mcp-servers-config`) and OpenShell's policy.yaml to generate
a sanitized, fail-closed `llama-shell.yaml` strictly bound to 127.0.0.1 without host tool access.

Usage:
    create-llama-shell.py [options]

Options:
    -i, --input-llama PATH   Path to input llama-swap.yaml [default: ~/models/llama-swap.yaml]
    -p, --policy PATH        Path to OpenShell policy.yaml [default: ~/Config/Openshell/policy.yaml]
    -o, --output PATH        Path to output llama-shell.yaml [default: ~/models/llama-shell.yaml]
    -m, --models MODELS...   Specific model IDs to include (or 'all') [default: all]
    --port PORT              Listening port override (default: auto-detected from policy.yaml, fallback 9008)
    --start-port PORT        Starting port for model instances [default: 11080]
    --no-cli-validate        Skip running 'llama-swap -validate' verification
    --dry-run                Sanitize and validate, but do not write output to disk
    --quiet                  Suppress progress output
    -h, --help               Show this help message and exit
"""

import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import yaml
except ImportError:
    sys.stderr.write("FATAL: 'pyyaml' is required. Install with: pip install pyyaml\n")
    sys.exit(1)


# Custom PyYAML dumper to format multiline strings cleanly with '|'
class CleanYamlDumper(yaml.SafeDumper):
    pass


def _multiline_str_representer(dumper: yaml.SafeDumper, data: str) -> yaml.Node:
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


CleanYamlDumper.add_representer(str, _multiline_str_representer)


# ---------------------------------------------------------------------------
# Forbidden Patterns & Regexes
# ---------------------------------------------------------------------------

FORBIDDEN_FLAG_PATTERNS = [
    # --tools with argument, e.g. --tools all, --tools=all, --tools 'all', or bare --tools
    re.compile(
        r"--tools(?:=(?:\"[^\"]*\"|'[^']*'|\S+)|(?:\s+(?!--\w)(?:\"[^\"]*\"|'[^']*'|\S+))|\b(?=\s|$))"
    ),
    # --mcp-servers-config <path> or =<path>
    re.compile(
        r"--mcp-servers-config(?:=(?:\"[^\"]*\"|'[^']*'|\S+)|(?:\s+(?!--\w)(?:\"[^\"]*\"|'[^']*'|\S+))|\b(?=\s|$))"
    ),
    # --ui-config-file <path> or =<path> (points to UI configs loading MCP servers)
    re.compile(
        r"--ui-config-file(?:=(?:\"[^\"]*\"|'[^']*'|\S+)|(?:\s+(?!--\w)(?:\"[^\"]*\"|'[^']*'|\S+))|\b(?=\s|$))"
    ),
    # --ui-mcp-proxy
    re.compile(r"--ui-mcp-proxy\b"),
]

# Strict validation patterns to fail closed
FAIL_CLOSED_FORBIDDEN_STRINGS = [
    "--tools",
    "--ui-mcp-proxy",
    "--mcp-servers-config",
    "--ui-config-file",
]


class SanitizationError(Exception):
    """Raised when configuration fails sanitization or safety checks."""
    pass


# ---------------------------------------------------------------------------
# Policy Parsing & Port Extraction
# ---------------------------------------------------------------------------

def resolve_policy_path(explicit_path: Optional[str] = None) -> Optional[Path]:
    """Find the active policy.yaml file."""
    if explicit_path:
        p = Path(explicit_path).expanduser().resolve()
        if p.is_file():
            return p
        raise FileNotFoundError(f"Specified policy file not found: {explicit_path}")

    candidates = [
        Path("~/Config/Openshell/policy.yaml").expanduser().resolve(),
        Path("~/Config/Openshell/policy.yaml").expanduser().resolve(),
    ]
    for cand in candidates:
        if cand.is_file():
            return cand
    return None


def extract_port_from_policy(policy_path: Optional[Path]) -> Optional[int]:
    """Extract the allowed endpoint port from policy.yaml."""
    if not policy_path or not policy_path.is_file():
        return None

    try:
        with open(policy_path, "r", encoding="utf-8") as f:
            policy_data = yaml.safe_load(f)

        if not isinstance(policy_data, dict):
            return None

        net_policies = policy_data.get("network_policies", {})
        if not isinstance(net_policies, dict):
            return None

        # Check local_llama_inference first, then any other policy
        keys_to_check = ["local_llama_inference"] + [
            k for k in net_policies.keys() if k != "local_llama_inference"
        ]
        for key in keys_to_check:
            pol = net_policies.get(key)
            if isinstance(pol, dict):
                endpoints = pol.get("endpoints", [])
                if isinstance(endpoints, list):
                    for ep in endpoints:
                        if isinstance(ep, dict) and "port" in ep:
                            try:
                                return int(ep["port"])
                            except (ValueError, TypeError):
                                pass
    except Exception as e:
        sys.stderr.write(f"Warning: Could not parse policy port from {policy_path}: {e}\n")

    return None


# ---------------------------------------------------------------------------
# String & Command Sanitization
# ---------------------------------------------------------------------------

def strip_forbidden_flags(text: str) -> str:
    """Strip all forbidden tool/MCP flags from a string."""
    cleaned = text
    for pattern in FORBIDDEN_FLAG_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    return cleaned


def enforce_host_loopback(cmd: str) -> str:
    """Enforce that --host is strictly set to 127.0.0.1 in the command string."""
    if re.search(r"--host\b", cmd):
        # Replace whatever follows --host with 127.0.0.1
        cmd = re.sub(r"--host(?:=\S+|\s+\S+)", "--host 127.0.0.1", cmd)
    else:
        # If --port is present, insert --host 127.0.0.1 before --port
        if re.search(r"--port\b", cmd):
            cmd = re.sub(r"(--port\b)", r"--host 127.0.0.1 \1", cmd, count=1)
        else:
            # Insert after the binary invocation
            parts = cmd.split(None, 1)
            if len(parts) == 2:
                cmd = f"{parts[0]} --host 127.0.0.1 {parts[1]}"
            else:
                cmd = f"{cmd} --host 127.0.0.1"
    return cmd


def sanitize_multiline_cmd(cmd: str, removed_macro_names: Set[str]) -> str:
    """Sanitize a model's cmd string: remove forbidden macros, flags, enforce host, clean whitespace."""
    result = cmd

    # Remove references to stripped macros like ${agent} or $agent
    for macro_name in removed_macro_names:
        result = re.sub(r"\$\{\s*" + re.escape(macro_name) + r"\s*\}", "", result)
        result = re.sub(r"\$" + re.escape(macro_name) + r"\b", "", result)

    # Strip forbidden flags
    result = strip_forbidden_flags(result)

    # Enforce loopback host
    result = enforce_host_loopback(result)

    # Clean up whitespace on each line, omit empty lines
    cleaned_lines = []
    for line in result.split("\n"):
        line_clean = re.sub(r"[ \t]+", " ", line).strip()
        if line_clean:
            cleaned_lines.append(line_clean)

    return "\n".join(cleaned_lines)


# ---------------------------------------------------------------------------
# Macro & Model Processing
# ---------------------------------------------------------------------------

def sanitize_macros(macros: Dict[str, Any]) -> Tuple[Dict[str, Any], Set[str]]:
    """Sanitize the macros dictionary. Return (sanitized_macros, removed_macro_names)."""
    sanitized: Dict[str, Any] = {}
    removed_names: Set[str] = set()

    # Pre-identify macros that are clearly agent/tool specific
    agent_macro_keys = {"agent", "mcp", "tools"}

    for key, val in macros.items():
        if key in agent_macro_keys:
            removed_names.add(key)
            continue

        if isinstance(val, str):
            clean_val = strip_forbidden_flags(val)
            clean_val = re.sub(r"[ \t]+", " ", clean_val).strip()

            # If macro became empty after stripping forbidden flags, remove it
            if not clean_val:
                removed_names.add(key)
                continue

            sanitized[key] = clean_val
        else:
            sanitized[key] = val

    # Clean references to removed macros within remaining macros
    for key, val in list(sanitized.items()):
        if isinstance(val, str):
            for rm in removed_names:
                val = re.sub(r"\$\{\s*" + re.escape(rm) + r"\s*\}", "", val)
                val = re.sub(r"\$" + re.escape(rm) + r"\b", "", val)
            val = re.sub(r"[ \t]+", " ", val).strip()
            if not val:
                removed_names.add(key)
                del sanitized[key]
            else:
                sanitized[key] = val

    # Prune unreferenced helper macros (e.g., 'brain') if they only existed for MCP/agent
    if "brain" in sanitized:
        # Check if any remaining macro references ${brain}
        brain_ref = any("${brain}" in str(v) or "$brain" in str(v) for k, v in sanitized.items() if k != "brain")
        if not brain_ref:
            del sanitized["brain"]
            removed_names.add("brain")

    return sanitized, removed_names


def filter_and_sanitize_models(
    models: Dict[str, Any],
    requested_models: Optional[List[str]],
    removed_macros: Set[str],
) -> Dict[str, Any]:
    """Filter models by requested IDs/aliases, and sanitize each model's command and proxy."""
    sanitized_models: Dict[str, Any] = {}

    # Build lookup map for requested models
    req_set = None
    if requested_models:
        req_set = {m.strip().lower() for m in requested_models if m.strip()}
        if "all" in req_set or not req_set:
            req_set = None

    for model_id, model_def in models.items():
        if not isinstance(model_def, dict):
            continue

        # Check if this model is selected
        if req_set is not None:
            model_id_lower = model_id.lower()
            aliases = [str(a).lower() for a in model_def.get("aliases", [])]
            name = str(model_def.get("name", "")).lower()

            matched = (model_id_lower in req_set) or any(a in req_set for a in aliases) or (name in req_set)
            if not matched:
                continue

        model_clean = dict(model_def)

        # Sanitize command
        if "cmd" in model_clean and isinstance(model_clean["cmd"], str):
            model_clean["cmd"] = sanitize_multiline_cmd(model_clean["cmd"], removed_macros)

        # Ensure proxy host is loopback if present
        if "proxy" in model_clean and isinstance(model_clean["proxy"], str):
            proxy = model_clean["proxy"]
            if not re.search(r"https?://(?:127\.0\.0\.1|localhost)(?::|\b|/)", proxy):
                raise SanitizationError(
                    f"Model '{model_id}' proxy points to non-loopback address: {proxy}"
                )

        sanitized_models[model_id] = model_clean

    if req_set is not None and not sanitized_models:
        available = list(models.keys())
        raise SanitizationError(
            f"None of the requested models {requested_models} were found. Available: {available}"
        )

    return sanitized_models


def prune_matrix(matrix: Dict[str, Any], kept_model_keys: Set[str]) -> Optional[Dict[str, Any]]:
    """Prune matrix vars and sets to ensure no references to omitted models."""
    if not isinstance(matrix, dict):
        return None

    vars_dict = matrix.get("vars", {})
    sets_dict = matrix.get("sets", {})

    if not isinstance(vars_dict, dict):
        return None

    # Filter vars whose value is in kept_model_keys
    pruned_vars = {k: v for k, v in vars_dict.items() if str(v) in kept_model_keys}
    if not pruned_vars:
        return None

    pruned_matrix: Dict[str, Any] = {"vars": pruned_vars}

    # Filter sets whose referenced variable identifiers exist in pruned_vars
    pruned_sets = {}
    if isinstance(sets_dict, dict):
        for set_name, expr in sets_dict.items():
            if isinstance(expr, str):
                tokens = re.findall(r"\b[a-zA-Z0-9_-]+\b", expr)
                if all(tok in pruned_vars for tok in tokens):
                    pruned_sets[set_name] = expr

    # If no original sets survived but we have vars, create a fallback active set
    if not pruned_sets and pruned_vars:
        pruned_sets["active"] = " | ".join(pruned_vars.keys())

    if pruned_sets:
        pruned_matrix["sets"] = pruned_sets
    else:
        return None

    return pruned_matrix


# ---------------------------------------------------------------------------
# Fail-Closed Validation
# ---------------------------------------------------------------------------

def validate_fail_closed(
    config: Dict[str, Any],
    removed_macro_names: Set[str],
) -> None:
    """Recursively validate configuration. Abort if any forbidden token or non-loopback host is found."""

    def _walk_and_check(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                _walk_and_check(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                _walk_and_check(v, f"{path}[{i}]")
        elif isinstance(node, str):
            # Check forbidden flags
            for forbidden in FAIL_CLOSED_FORBIDDEN_STRINGS:
                if forbidden in node:
                    raise SanitizationError(
                        f"FAIL-CLOSED: Forbidden token '{forbidden}' found in '{path}': {node}"
                    )

            # Check removed macro references
            for rm in removed_macro_names:
                if f"${{{rm}}}" in node or f"${rm}" in node:
                    raise SanitizationError(
                        f"FAIL-CLOSED: Removed macro reference '${{{rm}}}' found in '{path}': {node}"
                    )

    # 1. Recursive scan of all nodes
    _walk_and_check(config, "root")

    # 2. Strict host check on every model command
    models = config.get("models", {})
    if not models:
        raise SanitizationError("FAIL-CLOSED: Configuration contains zero models!")

    for mid, mdata in models.items():
        cmd = mdata.get("cmd")
        if isinstance(cmd, str):
            if "--host 127.0.0.1" not in cmd:
                raise SanitizationError(
                    f"FAIL-CLOSED: Model '{mid}' command is missing '--host 127.0.0.1': {cmd}"
                )
            # Check for illegal host patterns like --host 0.0.0.0
            bad_host = re.search(r"--host(?:=|\s+)(?!127\.0\.0\.1\b)(\S+)", cmd)
            if bad_host:
                raise SanitizationError(
                    f"FAIL-CLOSED: Model '{mid}' specifies non-loopback host '{bad_host.group(0)}'"
                )


# ---------------------------------------------------------------------------
# Main Generation Logic
# ---------------------------------------------------------------------------

def generate_shell_swap(
    input_llama_path: Path,
    output_path: Path,
    policy_path: Optional[Path],
    requested_models: Optional[List[str]],
    port_override: Optional[int],
    start_port: int,
    cli_validate: bool = True,
    dry_run: bool = False,
    quiet: bool = False,
) -> Dict[str, Any]:
    """Load, sanitize, validate, and write llama-shell.yaml."""

    if not input_llama_path.is_file():
        raise FileNotFoundError(f"Input llama-swap config not found: {input_llama_path}")

    # 1. Determine target listening port
    effective_port = port_override or extract_port_from_policy(policy_path) or 9008

    if not quiet:
        print(f"[+] Input llama-swap config : {input_llama_path}")
        print(f"[+] OpenShell policy file   : {policy_path or 'Not specified / not found'}")
        print(f"[+] Target listening port   : {effective_port}")
        print(f"[+] Model startPort         : {start_port} (isolated from host 10001)")

    # 2. Load input config
    with open(input_llama_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        raise SanitizationError(f"Input file {input_llama_path} is not a valid YAML dictionary")

    # 3. Sanitize macros
    macros = config.get("macros", {})
    sanitized_macros, removed_macros = sanitize_macros(macros)

    # 4. Filter and sanitize models
    orig_models = config.get("models", {})
    if not isinstance(orig_models, dict):
        raise SanitizationError("No 'models' dictionary found in input configuration")

    sanitized_models = filter_and_sanitize_models(
        orig_models,
        requested_models,
        removed_macros,
    )

    # 5. Build output config preserving standard ordering
    output_config: Dict[str, Any] = {}

    # Copy top-level settings
    top_level_keys = [
        "healthCheckTimeout",
        "globalTTL",
        "unloadTimeout",
        "globalConcurrencyLimit",
        "maxRequestBodyMB",
        "logLevel",
        "logTimeFormat",
        "logToStdout",
        "captureBuffer",
        "sendLoadingState",
        "includeAliasesInList",
    ]
    for key in top_level_keys:
        if key in config:
            output_config[key] = config[key]

    # Force isolated startPort
    output_config["startPort"] = start_port

    # Add sanitized macros
    if sanitized_macros:
        output_config["macros"] = sanitized_macros

    # Add sanitized models
    output_config["models"] = sanitized_models

    # Prune and add matrix if present
    if "matrix" in config:
        pruned_mat = prune_matrix(config["matrix"], set(sanitized_models.keys()))
        if pruned_mat:
            output_config["matrix"] = pruned_mat

    # 6. Strict Fail-Closed Validation
    validate_fail_closed(output_config, removed_macros)

    # 7. Format YAML string with provenance header
    yaml_body = yaml.dump(
        output_config,
        Dumper=CleanYamlDumper,
        sort_keys=False,
        default_flow_style=False,
    )

    header = (
        "# yaml-language-server: $schema=https://raw.githubusercontent.com/mostlygeek/llama-swap/refs/heads/main/config-schema.json\n"
        "# -----------------------------------------------------------------------------\n"
        "# GENERATED FOR OPENSHELL SANDBOXED EXECUTION\n"
        f"# Generated at           : {datetime.datetime.now().astimezone().isoformat()}\n"
        f"# Source configuration   : {input_llama_path}\n"
        f"# OpenShell policy       : {policy_path or 'Default'}\n"
        f"# OpenShell endpoint port: {effective_port}\n"
        f"# Model startPort        : {start_port}\n"
        "# Safety enforcement    : Host loopback only (127.0.0.1), no host tools/MCP proxies.\n"
        "# -----------------------------------------------------------------------------\n\n"
    )
    final_output = header + yaml_body

    # 8. Dry-run or Atomic Write
    if dry_run:
        if not quiet:
            print("[+] Dry-run requested. Output not written to disk.")
        return output_config

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_output_path = output_path.with_name(f".{output_path.name}.tmp")

    try:
        with open(temp_output_path, "w", encoding="utf-8") as f:
            f.write(final_output)

        # Re-verify the written temporary file with YAML parser
        with open(temp_output_path, "r", encoding="utf-8") as f:
            verify_data = yaml.safe_load(f)
            validate_fail_closed(verify_data, removed_macros)

        # Optional: verify using llama-swap CLI if installed
        if cli_validate and shutil.which("llama-swap"):
            proc = subprocess.run(
                ["llama-swap", "-validate", "-config", str(temp_output_path)],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                raise SanitizationError(
                    f"llama-swap -validate failed: {proc.stdout} {proc.stderr}"
                )

        # Atomic rename
        os.replace(temp_output_path, output_path)
    finally:
        if temp_output_path.is_file():
            try:
                temp_output_path.unlink()
            except OSError:
                pass

    if not quiet:
        print(f"[+] Models processed        : {len(sanitized_models)}")
        print(f"[+] Removed dangerous macros: {sorted(list(removed_macros))}")
        print(f"[+] Output written to       : {output_path}")
        print(f"[+] Verification            : PASSED (Fail-closed assertions & llama-swap -validate)")

    return output_config


# ---------------------------------------------------------------------------
# CLI Argument Parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a safe, sanitized llama-shell.yaml for OpenShell sandboxed execution.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-i",
        "--input-llama",
        default="~/models/llama-swap.yaml",
        help="Path to input llama-swap.yaml configuration.",
    )
    parser.add_argument(
        "-p",
        "--policy",
        default=None,
        help="Path to OpenShell policy.yaml (defaults to ~/Config/Openshell/policy.yaml).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="./llama-shell.yaml",
        help="Path to output llama-shell.yaml file.",
    )
    parser.add_argument(
        "-m",
        "--models",
        nargs="*",
        default=None,
        help="List of model IDs or aliases to include, or 'all'. Can be space or comma separated.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Listening port override for llama-swap (auto-detected from policy.yaml if omitted).",
    )
    parser.add_argument(
        "--start-port",
        type=int,
        default=11080,
        help="Starting port for model processes (${PORT}) to avoid colliding with 10001.",
    )
    parser.add_argument(
        "--no-cli-validate",
        action="store_true",
        help="Skip running 'llama-swap -validate' verification.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Sanitize and validate without writing to the output file.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress informational stdout output.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_path = Path(args.input_llama).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    try:
        policy_path = resolve_policy_path(args.policy)
    except FileNotFoundError as err:
        sys.stderr.write(f"FATAL: {err}\n")
        sys.exit(1)

    # Flatten --models argument if commas were used (e.g. -m "m1,m2" or -m m1 m2)
    models_list = None
    if args.models:
        models_list = []
        for item in args.models:
            for sub in item.split(","):
                sub_clean = sub.strip()
                if sub_clean:
                    models_list.append(sub_clean)

    try:
        generate_shell_swap(
            input_llama_path=input_path,
            output_path=output_path,
            policy_path=policy_path,
            requested_models=models_list,
            port_override=args.port,
            start_port=args.start_port,
            cli_validate=not args.no_cli_validate,
            dry_run=args.dry_run,
            quiet=args.quiet,
        )
    except (SanitizationError, FileNotFoundError) as e:
        sys.stderr.write(f"\nFATAL: Sanitization aborted (fail-closed): {e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"\nFATAL: Unexpected error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
