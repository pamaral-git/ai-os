#!/bin/bash
# fetch_monitor_the_situation.sh
# Fetches data from monitor-the-situation.com
# Uses the public /api/events endpoint which returns JSON without authentication.
#
# Usage: ./fetch_monitor_the_situation.sh [output_file.json] [--limit N] [--category CATEGORY]
#   If output_file.json is provided, saves to that file
#   Otherwise, prints to stdout
#   --limit N: Limit to N most recent events (default: all)
#   --category CATEGORY: Filter by category (political, conflict, etc.)
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
OUTPUT_FILE=""
LIMIT=""
CATEGORY=""

# Parse simple arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --limit)
            if [[ -n "${2:-}" && "${2:0:1}" != "-" ]]; then
                LIMIT="$2"
                shift 2
            else
                log_error "--limit requires a number"
                exit 1
            fi
            ;;
        --category)
            if [[ -n "${2:-}" && "${2:0:1}" != "-" ]]; then
                CATEGORY="$2"
                shift 2
            else
                log_error "--category requires a value"
                exit 1
            fi
            ;;
        --help|-h)
            echo "Usage: $0 [output_file.json] [--limit N] [--category CATEGORY]"
            echo "  Fetches events from monitor-the-situation.com"
            echo ""
            echo "Options:"
            echo "  output_file.json    Save output to file"
            echo "  --limit N          Limit to N most recent events"
            echo "  --category C       Filter by category (political, conflict, etc.)"
            echo "  --help, -h         Show this help message"
            exit 0
            ;;
        *)
            if [[ -z "$OUTPUT_FILE" && "${1:0:1}" != "-" ]]; then
                OUTPUT_FILE="$1"
            fi
            shift
            ;;
    esac
done

# API endpoint
API_URL="https://monitor-the-situation.com/api/events"

# User agent to mimic a browser
USER_AGENT="Mozilla/5.0 (compatible; MonitorTheSituationFetcher/1.0; +https://github.com/situation-monitor)"

# Temporary file for intermediate results
TMP_FILE=$(mktemp 2>/dev/null || echo "/tmp/mts_fetch_$$")
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
            -H "Accept: application/json" \
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

# Main execution
main() {
    log_info "Starting Monitor-the-Situation data fetch..."
    log_info "Timestamp: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    
    local success=0
    local result=""
    
    # Build query parameters
    local query_params=""
    if [ -n "$LIMIT" ]; then
        query_params="?limit=$LIMIT"
    fi
    
    # For category filtering, we'll filter locally since the API doesn't support it
    # But we can try to fetch and filter
    
    # Fetch events
    log_info "Fetching events from $API_URL..."
    if fetch_with_retry "$API_URL"; then
        # Check if response is valid JSON
        if jq empty "$TMP_FILE" 2>/dev/null; then
            result=$(cat "$TMP_FILE")
            success=1
            log_info "Successfully fetched events"
            
            # Apply limit if specified
            if [ -n "$LIMIT" ]; then
                result=$(echo "$result" | jq ".[:$LIMIT]")
                log_info "Limited to $LIMIT most recent events"
            fi
            
            # Apply category filter if specified
            if [ -n "$CATEGORY" ]; then
                result=$(echo "$result" | jq --arg cat "$CATEGORY" '.[] | select(.category == $cat)')
                log_info "Filtered by category: $CATEGORY"
            fi
            
        else
            log_warning "Response is not valid JSON"
            # Try to extract JSON from response
            result=$(grep -o '{[^{}]*}' "$TMP_FILE" | head -1 || echo "{}")
            if [ "$result" != "{}" ]; then
                success=1
                log_info "Extracted JSON from response"
            fi
        fi
    fi
    
    # If still no success, create a fallback response
    if [ $success -eq 0 ]; then
        log_warning "Unable to fetch data from Monitor-the-Situation. All methods failed."
        result='{
  "status": "error",
  "message": "Failed to fetch events. The API may be temporarily unavailable.",
  "timestamp": "'"$(date -u +'%Y-%m-%dT%H:%M:%SZ')"'",
  "source": "monitor-the-situation.com",
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
