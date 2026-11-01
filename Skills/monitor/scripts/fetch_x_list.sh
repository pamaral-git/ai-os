#!/bin/bash
# fetch_x_list.sh
# Fetches tweets from a public X.com (Twitter) list using various methods.
# Since direct access to X.com lists requires authentication, this script
# uses alternative approaches:
# 1. RSS feed (if available)
# 2. Public API via RSS-to-JSON services
# 3. Twitter API v2 (requires Bearer token, but script provides instructions)
#
# Usage: ./fetch_x_list.sh LIST_ID [output_file.json] [--method METHOD] [--limit N]
#   LIST_ID: The X.com list ID (e.g., 1854578015587500532)
#   output_file.json: Optional output file
#   --method: rss, nitter, or api (default: rss)
#   --limit: Maximum number of tweets to fetch (default: 20)
#
# Requirements: curl, jq (optional)
# Works in: Cloud VMs, AI chat apps (Gemini, ChatGPT, etc.)
#
# NOTE: X.com lists may require authentication. This script uses public
#       alternatives that may have limitations.

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
LIST_ID=""
OUTPUT_FILE=""
METHOD="rss"
LIMIT=20

while [[ $# -gt 0 ]]; do
    case "$1" in
        --method)
            if [[ -n "${2:-}" && "${2:0:1}" != "-" ]]; then
                METHOD="$2"
                shift 2
            else
                log_error "--method requires a value (rss, nitter, or api)"
                exit 1
            fi
            ;;
        --limit)
            if [[ -n "${2:-}" && "${2:0:1}" != "-" ]]; then
                LIMIT="$2"
                shift 2
            else
                log_error "--limit requires a number"
                exit 1
            fi
            ;;
        --help|-h)
            echo "Usage: $0 LIST_ID [output_file.json] [--method METHOD] [--limit N]"
            echo ""
            echo "Fetches tweets from a public X.com list."
            echo ""
            echo "Arguments:"
            echo "  LIST_ID             X.com list ID (e.g., 1854578015587500532)"
            echo "  output_file.json    Optional output file"
            echo ""
            echo "Options:"
            echo "  --method METHOD     Method to use: rss, nitter, or api (default: rss)"
            echo "  --limit N          Maximum number of tweets (default: 20)"
            echo "  --help, -h         Show this help message"
            echo ""
            echo "Methods:"
            echo "  rss      Use RSS feed (may not work for all lists)"
            echo "  nitter   Use Nitter instance (if available)"
            echo "  api      Use Twitter API v2 (requires BEARER_TOKEN env var)"
            exit 0
            ;;
        *)
            if [[ -z "$LIST_ID" ]]; then
                LIST_ID="$1"
            elif [[ -z "$OUTPUT_FILE" ]]; then
                OUTPUT_FILE="$1"
            fi
            shift
            ;;
    esac
done

if [[ -z "$LIST_ID" ]]; then
    log_error "LIST_ID is required. Usage: $0 LIST_ID [output_file.json]"
    exit 1
fi

# User agent
USER_AGENT="Mozilla/5.0 (compatible; XListFetcher/1.0; +https://github.com/situation-monitor)"

# Temporary file
TMP_FILE=$(mktemp 2>/dev/null || echo "/tmp/x_list_fetch_$$")
trap "rm -f \"$TMP_FILE\"" EXIT

# Function to fetch with retry
fetch_with_retry() {
    local url="$1"
    local max_retries=3
    local retry_delay=2
    local attempt=1
    
    while [ $attempt -le $max_retries ]; do
        if curl -s -f --retry 2 --max-time 30 \
            -A "$USER_AGENT" \
            "$url" > "$TMP_FILE" 2>/dev/null; then
            return 0
        fi
        
        if [ $attempt -lt $max_retries ]; then
            log_warning "Attempt $attempt failed. Retrying in $retry_delay seconds..."
            sleep $retry_delay
            ((attempt++))
            retry_delay=$((retry_delay * 2))
        else
            return 1
        fi
    done
    
    return 1
}

# Method: RSS feed
fetch_rss() {
    local list_id="$1"
    local limit="$2"
    
    # Try different RSS feed formats
    local rss_urls=(
        "https://x.com/i/lists/$list_id/rss"
        "https://twitter.com/i/lists/$list_id/rss"
        "https://nitter.net/i/lists/$list_id/rss"
        "https://rss2json.com/api/v1/json?rss_url=https://x.com/i/lists/$list_id"
    )
    
    for rss_url in "${rss_urls[@]}"; do
        log_info "Trying RSS URL: $rss_url"
        if fetch_with_retry "$rss_url"; then
            # Check if it's valid XML/RSS
            if head -1 "$TMP_FILE" | grep -q '<?xml'; then
                # Convert RSS to JSON if jq is available
                if command -v jq &> /dev/null; then
                    # Simple RSS to JSON conversion (basic)
                    local json_result
                    json_result=$(cat "$TMP_FILE" | sed 's/</\n</g' | grep -E '<title>|<link>|<pubDate>|<description>' | sed 's/<\///' | sed 's/<.*>//' || echo "[]")
                    echo "[{\"items\": [${json_result}]}]"
                    return 0
                else
                    cat "$TMP_FILE"
                    return 0
                fi
            fi
        fi
    done
    
    return 1
}

# Method: Nitter (self-hosted Twitter alternative)
fetch_nitter() {
    local list_id="$1"
    local limit="$2"
    
    # Try various Nitter instances
    local nitter_instances=(
        "https://nitter.net"
        "https://nitter.1d4.us"
        "https://nitter.privacydev.net"
        "https://nitter.fly.dev"
    )
    
    for instance in "${nitter_instances[@]}"; do
        local url="$instance/i/lists/$list_id"
        log_info "Trying Nitter instance: $url"
        
        if fetch_with_retry "$url"; then
            # Check if we got HTML (Nitter returns HTML)
            if head -1 "$TMP_FILE" | grep -q '<!DOCTYPE html'; then
                # Try to extract tweets from HTML
                local json_result
                json_result=$(grep -Eo '{"id":[^}]*}' "$TMP_FILE" | head -$limit || echo "[]")
                echo "{\"source\": \"$instance\", \"tweets\": [$(echo "$json_result" | paste -sd ',' -)]}" || echo "{}"
                return 0
            fi
        fi
    done
    
    return 1
}

# Method: Twitter API v2
fetch_api() {
    local list_id="$1"
    local limit="$2"
    
    # Check for Bearer token
    if [[ -z "${BEARER_TOKEN:-}" ]]; then
        log_error "Twitter API v2 requires BEARER_TOKEN environment variable"
        log_error "Get a free Bearer token from: https://developer.twitter.com/en/portal/dashboard"
        return 1
    fi
    
    # Twitter API v2 endpoint for list tweets
    local api_url="https://api.twitter.com/2/lists/$list_id/tweets"
    
    log_info "Fetching from Twitter API v2..."
    
    # Build query parameters
    local params="tweet.fields=created_at,author_id,text&max_results=$limit&expansions=author_id"
    
    if ! curl -s -f --max-time 30 \
        -A "$USER_AGENT" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "Content-Type: application/json" \
        "$api_url?$params" > "$TMP_FILE" 2>/dev/null; then
        
        log_error "Failed to fetch from Twitter API. Check BEARER_TOKEN."
        return 1
    fi
    
    # Check if we got valid JSON
    if command -v jq &> /dev/null; then
        if jq empty "$TMP_FILE" 2>/dev/null; then
            cat "$TMP_FILE" | jq .
            return 0
        fi
    fi
    
    cat "$TMP_FILE"
    return 0
}

# Main execution
main() {
    log_info "Starting X.com list fetch..."
    log_info "List ID: $LIST_ID"
    log_info "Method: $METHOD"
    log_info "Limit: $LIMIT"
    log_info "Timestamp: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    
    local success=0
    local result=""
    
    case "$METHOD" in
        rss)
            if result=$(fetch_rss "$LIST_ID" "$LIMIT" 2>/dev/null) || [ -n "$result" ]; then
                success=1
            fi
            ;;
        nitter)
            if result=$(fetch_nitter "$LIST_ID" "$LIMIT" 2>/dev/null) || [ -n "$result" ]; then
                success=1
            fi
            ;;
        api)
            if result=$(fetch_api "$LIST_ID" "$LIMIT" 2>/dev/null) || [ -n "$result" ]; then
                success=1
            fi
            ;;
        *)
            log_error "Unknown method: $METHOD. Use rss, nitter, or api."
            exit 1
            ;;
    esac
    
    if [ $success -eq 0 ]; then
        log_warning "Unable to fetch data from X.com list. Method '$METHOD' failed."
        result='{
  "status": "error",
  "message": "Failed to fetch list data. Try a different method (--method rss/nitter/api).",
  "list_id": "'"$LIST_ID"'",
  "method": "'"$METHOD"'",
  "timestamp": "'"$(date -u +'%Y-%m-%dT%H:%M:%SZ')"'",
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
