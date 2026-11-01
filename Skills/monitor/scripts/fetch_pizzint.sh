#!/bin/bash
# fetch_pizzint.sh
# Fetches data from pizzint.watch (Pentagon Pizza Index)
# Attempts to extract structured data from the SPA without authentication.
#
# Usage: ./fetch_pizzint.sh [output_file.json]
#   If output_file.json is provided, saves to that file
#   Otherwise, prints to stdout
#
# Requirements: curl, jq (optional for pretty printing)
# Works in: Cloud VMs, AI chat apps (Gemini, ChatGPT, etc.)

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print error messages
log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Function to print info messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

# Function to print warnings
log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

# Check if curl is available
if ! command -v curl &> /dev/null; then
    log_error "curl is required but not installed. Please install curl."
    exit 1
fi

# Parse arguments
OUTPUT_FILE="${1:-}"

# API endpoints
MAIN_URL="https://www.pizzint.watch"
POLYGLOBE_URL="https://www.pizzint.watch/polyglobe/app"

# User agent to mimic a browser
USER_AGENT="Mozilla/5.0 (compatible; PizzintFetcher/1.0; +https://github.com/situation-monitor)"

# Temporary file for intermediate results
TMP_FILE=$(mktemp 2>/dev/null || echo "/tmp/pizzint_fetch_$$")
trap "rm -f \"$TMP_FILE\"" EXIT

# Function to fetch with retry logic
fetch_with_retry() {
    local url="$1"
    local max_retries=3
    local retry_delay=2
    local attempt=1
    
    while [ $attempt -le $max_retries ]; do
        if curl -s -f --retry 2 --max-time 60 \
            -A "$USER_AGENT" \
            "$url" > "$TMP_FILE" 2>/dev/null; then
            return 0
        fi
        
        if [ $attempt -lt $max_retries ]; then
            log_warning "Attempt $attempt failed for $url. Retrying in $retry_delay seconds..."
            sleep $retry_delay
            ((attempt++))
            retry_delay=$((retry_delay * 2))  # Exponential backoff
        else
            return 1
        fi
    done
    
    return 1
}

# Function to extract JSON from HTML
extract_json_from_html() {
    local html_file="$1"
    # Look for JSON in script tags and data attributes
    # This extracts JSON from script tags containing window.__* or similar
    grep -Eo 'window\.__[A-Za-z]+\s*=\s*\{[^}]*\}' "$html_file" | sed 's/window\.__[A-Za-z]*\s*=\s*//' | head -1 || echo "{}"
}

# Function to extract metadata from HTML
extract_metadata() {
    local html_file="$1"
    local url="$2"
    
    # Extract title, description, etc.
    local title
    title=$(grep -o '<title>[^<]*</title>' "$html_file" | sed 's/<title>//;s/<\/title>//' | head -1 || echo "")
    
    local description
    description=$(grep -o 'name="description"[^>]*content="[^"]*"' "$html_file" | sed 's/.*content="\([^"]*\)".*/\1/' | head -1 || echo "")
    
    local og_title
    og_title=$(grep -o 'property="og:title"[^>]*content="[^"]*"' "$html_file" | sed 's/.*content="\([^"]*\)".*/\1/' | head -1 || echo "")
    
    local og_description
    og_description=$(grep -o 'property="og:description"[^>]*content="[^"]*"' "$html_file" | sed 's/.*content="\([^"]*\)".*/\1/' | head -1 || echo "")
    
    # Extract any JSON data
    local json_data
    json_data=$(extract_json_from_html "$html_file")
    
    # Build result
    printf '{\n  "source": "%s",\n  "timestamp": "%s",\n  "metadata": {\n    "title": "%s",\n    "description": "%s",\n    "og_title": "%s",\n    "og_description": "%s"\n  },\n  "data": %s\n}\n' "$url" "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$title" "$description" "$og_title" "$og_description" "$json_data"
}

# Main execution
main() {
    log_info "Starting PizzINT data fetch..."
    log_info "Timestamp: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    
    local success=0
    local result=""
    
    # Try main URL
    log_info "Fetching main page: $MAIN_URL"
    if fetch_with_retry "$MAIN_URL"; then
        result=$(extract_metadata "$TMP_FILE" "$MAIN_URL")
        success=1
        log_info "Successfully extracted data from main page"
    fi
    
    # If main page failed, try polyglobe
    if [ $success -eq 0 ]; then
        log_info "Fetching Polyglobe app: $POLYGLOBE_URL"
        if fetch_with_retry "$POLYGLOBE_URL"; then
            result=$(extract_metadata "$TMP_FILE" "$POLYGLOBE_URL")
            success=1
            log_info "Successfully extracted data from Polyglobe app"
        fi
    fi
    
    # If still no success, create a fallback response
    if [ $success -eq 0 ]; then
        log_warning "Unable to fetch data from PizzINT. All methods failed."
        result='{
  "status": "error",
  "message": "All fetch methods failed. PizzINT may be blocking automated requests.",
  "timestamp": "'"$(date -u +'%Y-%m-%dT%H:%M:%SZ')"'",
  "source": "pizzint.watch",
  "retry_after": 300
}'
    fi
    
    # Output the result
    if [ -n "$OUTPUT_FILE" ]; then
        if command -v jq &> /dev/null; then
            echo "$result" | jq . > "$OUTPUT_FILE"
        else
            echo "$result" > "$OUTPUT_FILE"
        fi
        log_info "Data saved to: $OUTPUT_FILE"
    else
        if command -v jq &> /dev/null; then
            echo "$result" | jq .
        else
            echo "$result"
        fi
    fi
    
    log_info "Fetch completed."
}

main
