#!/bin/bash
set -u

# =============================================================================
# INTERACTIVE STACK AUDIT SCRIPT
# Generates a comprehensive markdown report with configurable scan scope
# =============================================================================

SCRIPT_NAME=$(basename "$0")
VERSION="2.0.0"

# Default values
OUTPUT_DIR="$HOME/Documents"
OUTPUT_FILE=""
SCAN_DIRS=()
SKIP_SECURITY=false
SKIP_AUDITS=false
VERBOSE=false
QUICK_MODE=false
AUDIT_NPM=true
AUDIT_BUN=true
AUDIT_UV=true
AUDIT_PIP=true

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

usage() {
  cat <<'EOF'
Usage: $SCRIPT_NAME [OPTIONS]

Generate a comprehensive stack audit report in markdown format.

Options:
  -o, --output FILE     Output file path (default: ~/Documents/stack-YYYY-MM-DD.md)
  -d, --dir PATH        Add directory to scan with security tools (can be used multiple times)
  -p, --project         Scan current directory as project (default)
  -a, --all             Scan entire home directory (NOT RECOMMENDED - slow)
  --skip-security       Skip trivy and gitleaks scans
  --skip-audits         Skip npm audit, bun audit, uv audit, pip check
  -q, --quick           Quick mode: minimal scans, fast execution
  -v, --verbose         Verbose output
  -h, --help            Show this help message
  --version             Show version

Examples:
  $SCRIPT_NAME                                    # Interactive mode
  $SCRIPT_NAME -p                                 # Scan current directory
  $SCRIPT_NAME -d ~/code/myapp -d ~/code/another # Scan specific directories
  $SCRIPT_NAME --skip-security --skip-audits     # Fast system info only
  $SCRIPT_NAME -q                                 # Quick mode

Notes:
  - Security scans (trivy, gitleaks) can take a long time on large directories
  - Use -d or -p to limit scan scope to specific project directories
  - Without -d or -p, only basic system info will be collected
EOF
}

log() {
  if [ "$VERBOSE" = true ]; then
    echo "[DEBUG] $1"
  fi
}

# =============================================================================
# OPTION PARSING
# =============================================================================

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--output)
      OUTPUT_FILE="$2"
      shift 2
      ;;
    -d|--dir)
      SCAN_DIRS+=("$2")
      shift 2
      ;;
    -p|--project)
      SCAN_DIRS+=("$(pwd)")
      shift
      ;;
    -a|--all)
      SCAN_DIRS+=("$HOME")
      shift
      ;;
    --skip-security)
      SKIP_SECURITY=true
      shift
      ;;
    --skip-audits)
      SKIP_AUDITS=true
      shift
      ;;
    -q|--quick)
      QUICK_MODE=true
      SKIP_SECURITY=true
      SKIP_AUDITS=true
      shift
      ;;
    -v|--verbose)
      VERBOSE=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --version)
      echo "$SCRIPT_NAME version $VERSION"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

# If no output file specified, generate one
if [ -z "$OUTPUT_FILE" ]; then
  OUTPUT_FILE="$OUTPUT_DIR/stack-$(date +%F).md"
fi

# Ensure output directory exists
mkdir -p "$(dirname "$OUTPUT_FILE")"

# If no scan directories and not skipping, add current directory
if [ ${#SCAN_DIRS[@]} -eq 0 ] && [ "$SKIP_SECURITY" = false ]; then
  SCAN_DIRS+=("$(pwd)")
fi

# If skipping audits, set all audit flags to false
if [ "$SKIP_AUDITS" = true ]; then
  AUDIT_NPM=false
  AUDIT_BUN=false
  AUDIT_UV=false
  AUDIT_PIP=false
fi

# =============================================================================
# REPORT GENERATION HELPERS
# =============================================================================

MDSection() {
  printf '\n\n### %s\n\n' "$1"
}

MDSubSection() {
  printf '\n#### %s\n\n' "$1"
}

cmd_exists() {
  command -v "$1" >/dev/null 2>&1
}

show_file() {
  [ -f "$1" ] || return
  MDSubSection "$(basename "$1")"
  printf '```\n'
  sed -E '/(api[_-]?key|token|secret|password|authorization|bearer|credential)/Id' "$1"
  printf '\n```\n'
}

run_cmd() {
  local name="$1"
  shift
  if cmd_exists "$name"; then
    MDSubSection "$name"
    printf '```\n'
    if ! "$@" 2>&1; then
      echo "(command failed with exit code $?)"
    fi
    printf '\n```\n'
  else
    printf '#### %s *(not installed)*\n\n' "$name"
  fi
}

timed_cmd() {
  local name="$1"
  local timeout_sec="${2:-10}"
  shift 2
  if cmd_exists "$name"; then
    MDSubSection "$name"
    printf '```\n'
    if ! timeout "$timeout_sec" "$@" 2>&1; then
      exit_code=$?
      if [ $exit_code -eq 124 ]; then
        echo "(command timed out after ${timeout_sec}s)"
      else
        echo "(command failed with exit code $exit_code)"
      fi
    fi
    printf '\n```\n'
  else
    printf '#### %s *(not installed)*\n\n' "$name"
  fi
}

# =============================================================================
# MAIN REPORT GENERATION
# =============================================================================

log "Starting report generation: $OUTPUT_FILE"

# Use a temporary file to avoid issues with redirecting the entire script
TMP_FILE=$(mktemp)
trap "rm -f \"$TMP_FILE\"" EXIT

# Start building the report
{
  # Header
  printf '# Stack Audit Report\n'
  printf 'Generated: %s  \n' "$(date -Iseconds)"
  printf 'User: %s  \n' "$USER"
  printf 'Hostname: %s  \n' "$(uname -n)"
  printf 'Script: %s v%s  \n' "$SCRIPT_NAME" "$VERSION"

  if [ "$QUICK_MODE" = true ]; then
    printf '\n*Running in quick mode - security scans and audits skipped*\n'
  fi

  printf '\n---\n\n'

  # System Overview
  MDSection "System Overview"
  printf '| Property | Value |\n'
  printf '|----------|-------|\n'
  printf '| **OS** | %s |\n' "$(sw_vers -productVersion 2>/dev/null || uname -srm 2>/dev/null || echo 'unknown')"
  printf '| **Kernel** | %s |\n' "$(uname -r)"
  printf '| **Shell** | %s |\n' "$SHELL"
  printf '| **Home** | %s |\n' "$HOME"
  printf '| **Current Dir** | %s |\n' "$(pwd)"

  # Hardware
  MDSection "Hardware"
  if cmd_exists system_profiler; then
    system_profiler SPHardwareDataType 2>/dev/null | head -20
  else
    uname -a
  fi

  # System Storage
  MDSection "System Storage"
  MDSubSection "Disk Usage"
  df -h | grep -v "^tmpfs\|^devtmpfs\|^udev" || df -h

  if [ "$QUICK_MODE" = false ]; then
    MDSubSection "Top Directories in Home (top 10)"
    if [ -d "$HOME" ]; then
      timeout 30 du -h -d 1 "$HOME" 2>/dev/null | sort -hr | head -10 || echo "(could not determine directory sizes)"
    fi

    MDSubSection "Largest Files in Home (>100MB, top 10)"
    timeout 30 find "$HOME" -type f -size +100M -exec du -h {} + 2>/dev/null | sort -hr | head -10 || echo "(could not find large files)"
  fi

  # PATH Analysis
  MDSection "PATH Analysis"
  printf '| # | PATH Entry | Exists? |\n'
  printf '|---|-------------|---------|\n'
  i=1
  IFS=':' read -ra dirs <<< "$PATH"
  for d in "${dirs[@]}"; do
    if [ -d "$d" ]; then
      printf '| %d | %s | ✅ |\n' "$i" "$d"
    else
      printf '| %d | %s | ❌ |\n' "$i" "$d"
    fi
    ((i++))
  done

  # Shell Configuration Files
  MDSection "Shell Configuration Files"
  for f in "$HOME/.zshenv" "$HOME/.zprofile" "$HOME/.zshrc" "$HOME/.zlogin" "$HOME/.bash_profile" "$HOME/.bashrc" "$HOME/.profile"; do
    show_file "$f"
  done

  # Homebrew
  if cmd_exists brew; then
    MDSection "Homebrew"
    run_cmd "brew --version"
    run_cmd "brew list --versions" brew list --versions
    run_cmd "brew list --cask" brew list --cask
    run_cmd "brew services list" brew services list
    run_cmd "brew outdated" brew outdated
    run_cmd "brew doctor" brew doctor
  fi

  # Docker
  if cmd_exists docker; then
    MDSection "Docker"
    run_cmd "docker --version"

    MDSubSection "Docker Info"
    timeout 10 docker info 2>&1 | head -20

    MDSubSection "Containers"
    timeout 10 docker ps -a --format "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Image}}" 2>&1

    MDSubSection "Images"
    timeout 10 docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" 2>&1

    MDSubSection "Docker Disk Usage"
    timeout 10 docker system df 2>&1
  fi

  # mise
  if cmd_exists mise; then
    MDSection "mise"
    run_cmd "mise --version"

    MDSubSection "Installed Tools"
    timeout 10 mise list 2>&1

    MDSubSection "mise doctor"
    timeout 10 mise doctor 2>&1
  fi

  # Python Ecosystem
  MDSection "Python Ecosystem"
  for p in python python3 python3.11 python3.12 python3.13 python3.14; do
    if cmd_exists "$p"; then
      MDSubSection "$p"
      printf '```\n'
      "$p" --version 2>&1
      "$p" -m pip --version 2>&1
      "$p" -m pip list --format=freeze 2>&1
      printf '\n```\n'
    fi
  done

  if cmd_exists uv; then
    MDSubSection "uv --version"
    uv --version 2>&1

    MDSubSection "uv tools"
    uv tool list 2>&1

    if [ "$AUDIT_UV" = true ]; then
      MDSubSection "uv audit"
      uv audit 2>&1

      MDSubSection "uv tool --audit"
      uv tool --audit 2>&1
    fi
  fi

  if cmd_exists pipx; then
    MDSubSection "pipx"
    pipx list 2>&1
  fi

  if cmd_exists conda; then
    MDSubSection "conda"
    conda --version 2>&1
    conda env list 2>&1
  fi

  if cmd_exists pyenv; then
    MDSubSection "pyenv"
    pyenv versions 2>&1
  fi

  # Node and JavaScript
  MDSection "Node and JavaScript"
  for tool in node npm npx pnpm yarn bun; do
    if cmd_exists "$tool"; then
      MDSubSection "$tool"
      printf '```\n'
      "$tool" --version 2>&1
      printf '\n```\n'
    fi
  done

  if cmd_exists corepack; then
    MDSubSection "corepack"
    corepack --version 2>&1
  fi

  if [ -d "$HOME/.nvm" ]; then
    MDSubSection "nvm versions"
    find "$HOME/.nvm/versions/node" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | sed 's|.*/||'
  fi

  # Node Audits
  if [ "$SKIP_AUDITS" = false ]; then
    MDSection "Package Audits"

    if [ "$AUDIT_BUN" = true ] && cmd_exists bun; then
      MDSubSection "bun audit"
      bun audit 2>&1
    fi

    if [ "$AUDIT_NPM" = true ] && cmd_exists npm; then
      MDSubSection "npm audit"
      npm audit 2>&1 | head -50
    fi
  fi

  # Other Language Tooling
  MDSection "Other Language Tooling"
  if cmd_exists rustc; then
    MDSubSection "rustc"
    rustc --version 2>&1
  fi
  if cmd_exists cargo; then
    MDSubSection "cargo"
    cargo --version 2>&1
    cargo install --list 2>&1 | head -20
  fi
  if cmd_exists go; then
    MDSubSection "go"
    go version 2>&1
    go env GOPATH GOROOT 2>&1
  fi
  if cmd_exists java; then
    MDSubSection "java"
    java -version 2>&1
  fi
  if cmd_exists ruby; then
    MDSubSection "ruby"
    ruby -v 2>&1
    gem list --local 2>&1 | head -20
  fi

  # Security Scanning
  if [ "$SKIP_SECURITY" = false ] && [ ${#SCAN_DIRS[@]} -gt 0 ]; then
    MDSection "Security Scanning"

    for scan_dir in "${SCAN_DIRS[@]}"; do
      MDSubSection "Scanning: $scan_dir"

      if cmd_exists trivy; then
        printf '##### Trivy\n\n'
        printf '```\n'
        echo "Scanning: $scan_dir"
        timeout 300 trivy fs --security-checks vuln,config,secret --severity HIGH,CRITICAL "$scan_dir" 2>&1 | head -50
        printf '\n```\n'
      else
        printf '*Trivy not installed*\n\n'
      fi

      if cmd_exists gitleaks; then
        printf '##### Gitleaks\n\n'
        printf '```\n'
        echo "Scanning: $scan_dir"
        timeout 300 gitleaks detect --source="$scan_dir" --report-format=markdown --exit-code=0 2>&1 | head -50
        printf '\n```\n'
      else
        printf '*Gitleaks not installed*\n\n'
      fi
    done
  elif [ "$SKIP_SECURITY" = true ]; then
    MDSection "Security Scanning"
    printf "*Security scanning skipped*\n"
  fi

  # Python Audits
  if [ "$SKIP_AUDITS" = false ]; then
    MDSection "Python Package Audits"

    if [ "$AUDIT_PIP" = true ]; then
      for p in python python3 python3.11 python3.12 python3.13 python3.14; do
        if cmd_exists "$p"; then
          MDSubSection "$p pip check"
          printf '```\n'
          $p -m pip check 2>&1 || true
          printf '\n```\n'
        fi
      done
    fi

    if cmd_exists uv && [ "$AUDIT_UV" = true ]; then
      MDSubSection "uv pip compile check"
      printf '```\n'
      for req in $(timeout 30 find "$HOME" -name "requirements*.txt" -o -name "pyproject.toml" 2>/dev/null | head -5); do
        echo "--- $req ---"
        timeout 30 uv pip compile "$req" --check 2>&1 || true
      done
      printf '\n```\n'
    fi
  fi

  # VS Code
  if cmd_exists code; then
    MDSection "VS Code"
    run_cmd "code --version"
    run_cmd "code --list-extensions --show-versions"
    run_cmd "code --status"

    show_file "$HOME/Library/Application Support/Code/User/settings.json"
    show_file "$HOME/Library/Application Support/Code/User/keybindings.json"

    MDSubSection "Profiles"
    find "$HOME/Library/Application Support/Code/User/profiles" -maxdepth 2 -type f 2>/dev/null

    MDSubSection "Extensions"
    find "$HOME/.vscode/extensions" -maxdepth 1 -mindepth 1 -type d -exec basename {} \; 2>/dev/null
  fi

  # AI Tools and Models
  MDSection "AI Tools and Models"
  for x in codex claude gemini ollama llama-cli llama-server lmstudio hf; do
    if cmd_exists "$x"; then
      MDSubSection "$x"
      printf '```\n'
      "$x" --version 2>&1 | head -5
      printf '\n```\n'
    fi
  done

  MDSubSection "Model directories"
  printf '| Directory | Size |\n|-----------|------|\n'
  for d in "$HOME/models" "$HOME/.cache/huggingface/hub" "$HOME/.ollama/models"; do
    if [ -d "$d" ]; then
      size=$(timeout 10 du -sh "$d" 2>/dev/null | cut -f1)
      printf '| %s | %s |\n' "$(basename "$d")" "$size"
    fi
  done

  MDSubSection "AI/MCP Configuration Files"
  find "$HOME/.codex" "$HOME/.claude" "$HOME/.gemini" "$HOME/.continue" "$HOME/.config" \
    -maxdepth 4 -type f \( -iname '*mcp*.json' -o -iname '*mcp*.toml' -o -iname 'config.json' -o -iname 'settings.json' \) \
    2>/dev/null | while read -r f; do
      printf "- %s\n" "$f"
    done

  # Git and SSH
  MDSection "Git and SSH"
  if cmd_exists git; then
    run_cmd "git --version"

    MDSubSection "Git Global Config"
    git config --global --list | sed -E '/(token|password|secret)/Id'
  fi

  MDSubSection "SSH Keys"
  printf '| Private | Public |\n|---------|--------|\n'
  for f in "$HOME/.ssh"/id_*; do
    if [ -f "$f" ]; then
      bn=$(basename "$f")
      if [[ "$bn" != *"pub" ]]; then
        printf '| %s | %s |\n' "$bn" "${bn}.pub"
      fi
    fi
  done

  # Applications and Services
  MDSection "Applications and Services"

  MDSubSection "Installed Applications"
  printf '| Application |\n|--------------|\n'
  (timeout 10 find /Applications "$HOME/Applications" -maxdepth 1 -name '*.app' -printf '%f\n' 2>/dev/null || \
    timeout 10 find /Applications "$HOME/Applications" -maxdepth 1 -name '*.app' 2>/dev/null) | \
    sort | while read -r app; do
      printf '| %s |\n' "$app"
    done

  MDSubSection "LaunchAgents"
  find "$HOME/Library/LaunchAgents" -maxdepth 1 -type f -name '*.plist' -printf '%f\n' 2>/dev/null

  MDSubSection "Cron Jobs"
  crontab -l 2>/dev/null || echo "No cron jobs"

  # Environment Variables
  MDSection "Environment Variables"
  printf '| Variable |\n|----------|\n'
  env | cut -d= -f1 | sort | while read -r var; do
    printf '| %s |\n' "$var"
  done

  # Footer
  printf '\n---\n'
  printf '*Report generated by %s v%s on %s*\n' "$SCRIPT_NAME" "$VERSION" "$(date -Iseconds)"

  if [ "$SKIP_SECURITY" = true ]; then
    printf '\n*Security scanning was skipped*\n'
  fi
  if [ "$SKIP_AUDITS" = true ]; then
    printf '\n*Package audits were skipped*\n'
  fi
  if [ "$QUICK_MODE" = true ]; then
    printf '\n*Quick mode enabled*\n'
  fi

  # Scan summary
  if [ "$SKIP_SECURITY" = false ] && [ ${#SCAN_DIRS[@]} -gt 0 ]; then
    printf '\n*Scanned directories:*\n'
    for scan_dir in "${SCAN_DIRS[@]}"; do
      printf '- %s\n' "$scan_dir"
    done
  fi

} > "$TMP_FILE" 2>&1

# Copy temp file to final output
cp "$TMP_FILE" "$OUTPUT_FILE"

REPORT_SIZE=$(stat -f%z "$OUTPUT_FILE" 2>/dev/null || stat -c%s "$OUTPUT_FILE" 2>/dev/null || echo "unknown")
REPORT_LINES=$(wc -l < "$OUTPUT_FILE" 2>/dev/null || echo "unknown")

echo ""
echo "========================================="
echo "  Audit report generated successfully!"
echo "========================================="
echo "  File: $OUTPUT_FILE"
echo "  Size: $REPORT_SIZE bytes"
echo "  Lines: $REPORT_LINES"
echo "========================================="
echo ""

# Open the report if we're in a GUI environment
if [ "$(uname)" = "Darwin" ] && command -v open >/dev/null 2>&1; then
  open "$OUTPUT_FILE"
fi
