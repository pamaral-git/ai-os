#!/bin/bash
#
# fetch_polyglobe.sh
# Fetches data from Pizzint.watch Polyglobe app
#
# Usage:
#   ./fetch_polyglobe.sh [OUTPUT_FILE]
#   ./fetch_polyglobe.sh polyglobe_data.json
#
# Description:
#   This script fetches data from the Polyglobe visualization app at
#   https://www.pizzint.watch/polyglobe/app. It extracts geographic
#   data, events, and visualizations.
#
# Requirements:
#   - curl (for HTTP requests)
#   - jq (optional, for JSON formatting)
#   - grep, sed (for text processing)
#
# Works in: Cloud VMs, AI chat apps (Gemini, ChatGPT, etc.)
#
# Features:
#   - Rate limiting detection and retry
#   - Error handling with graceful degradation
#   - Clean JSON output
#

set -euo pipefail

# Configuration
SITE_URL="https://www.pizzint.watch/polyglobe/app"
API_URL="https://www.pizzint.watch/polyglobe/api"
DATA_URL="https://www.pizzint.watch/polyglobe/data.json"
TIMEOUT=30
MAX_RETRIES=3
RETRY_DELAY=5
USER_AGENT="Mozilla/5.0 (compatible; PolyglobeFetcher/1.0; +https://github.com/situation-monitor)"

# Colors
RED=''
GREEN=''
YELLOW=''
BLUE=''
NC=''

if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
fi

# Logging
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARNING]${NC} $1" >&2; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# Rate limiting and retry
fetch_url() {
    local url="$1"
    local attempt=0
    
    while [ $attempt -lt $MAX_RETRIES ]; do
        attempt=$((attempt + 1))
        
        local response
        response=$(curl -s -f -L --max-time $TIMEOUT \
            -A "$USER_AGENT" \
            -H "Accept: application/json" \
            -H "Accept-Language: en-US,en;q=0.9" \
            "$url" 2>/dev/null)
        
        local status=$?
        
        # Rate limit check
        if echo "$response" | grep -qi "rate limit\|too many requests\|429\|slow down"; then
            if [ $attempt -lt $MAX_RETRIES ]; then
                log_warn "Rate limited. Retrying in $RETRY_DELAY seconds..."
                sleep $RETRY_DELAY
                continue
            else
                log_error "Rate limited. Max retries reached."
                return 1
            fi
        fi
        
        if [ $status -ne 0 ]; then
            if [ $attempt -lt $MAX_RETRIES ]; then
                log_warn "Failed to fetch $url (attempt $attempt/$MAX_RETRIES). Retrying..."
                sleep $((RETRY_DELAY * attempt))
                continue
            else
                log_error "Failed to fetch $url after $MAX_RETRIES attempts."
                return 1
            fi
        fi
        
        # Check for HTTP errors
        if echo "$response" | grep -qi "404\|403\|500\|503\|Not Found\|Forbidden"; then
            if [ $attempt -lt $MAX_RETRIES ]; then
                log_warn "HTTP error in response. Retrying..."
                sleep $RETRY_DELAY
                continue
            else
                log_error "HTTP error. Max retries reached."
                return 1
            fi
        fi
        
        echo "$response"
        return 0
    done
    
    return 1
}

# Try to find the data endpoint
find_data_endpoint() {
    log_info "Finding data endpoint..."
    
    local html
    html=$(fetch_url "$SITE_URL")
    
    if [ $? -ne 0 ] || [ -z "$html" ]; then
        log_error "Failed to fetch main page"
        echo "$DATA_URL"
        return
    fi
    
    # Look for data URLs in the HTML
    local data_urls
    data_urls=$(echo "$html" | grep -oE 'https?://[^"]+/polyglobe/(api|data|events)[^"]*' | head -5)
    
    if [ -n "$data_urls" ]; then
        # Use the first one found
        echo "$data_urls" | head -1
        return
    fi
    
    # Look for API endpoint in script tags
    local api_urls
    api_urls=$(echo "$html" | grep -oE '"(https?://[^"]+/polyglobe/api/[^"]*)"' | sed 's/"//g' | head -5)
    
    if [ -n "$api_urls" ]; then
        echo "$api_urls" | head -1
        return
    fi
    
    # Look for fetch/axios calls
    local fetch_urls
    fetch_urls=$(echo "$html" | grep -oE "fetch\('[^']*'\)" | sed "s/fetch('//;s/')//" | head -5)
    
    if [ -n "$fetch_urls" ]; then
        echo "$fetch_urls" | head -1
        return
    fi
    
    # Default to known data URL
    echo "$DATA_URL"
}

# Try to extract JSON from the main page
extract_json_from_html() {
    local html="$1"
    
    # Look for JSON data embedded in the page
    local json_data
    json_data=$(echo "$html" | grep -oE '\{[^{}]*polyglobe[^{}]*\}' | head -1)
    
    if [ -n "$json_data" ]; then
        # Try to extract valid JSON
        echo "$html" | grep -oE '\{[^{}]*\}' | \
            while IFS= read -r candidate; do
                if echo "$candidate" | jq empty 2>/dev/null; then
                    echo "$candidate"
                    return
                fi
            done
    fi
    
    echo "{}"
}

# Extract events data
extract_events() {
    local html="$1"
    local json_output="[]"
    local count=0
    
    # Look for event markers in the HTML
    echo "$html" | grep -oE 'latitude.*longitude\|lat.*lng\|position.*\{[^}]*\}' | \
        while IFS= read -r location_data; do
            count=$((count + 1))
            
            local lat
            lat=$(echo "$location_data" | grep -oE '[0-9\.-]+' | head -1)
            
            local lng
            lng=$(echo "$location_data" | grep -oE '[0-9\.-]+' | tail -1)
            
            local event_name
            event_name=$(echo "$html" | grep -B 5 -A 5 "$location_data" | grep -oE '"[^"]+"' | head -1 | sed 's/"//g')
            
            if [ -n "$lat" ] && [ -n "$lng" ]; then
                local event_json
                event_json=$(cat <<EOF
{
    "id": $count,
    "latitude": ${lat:--999},
    "longitude": ${lng:--999},
    "name": "${event_name:-Unknown Event}",
    "source": "pizzint.watch/polyglobe",
    "extracted_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
                )
                json_output=$(echo "$json_output" | jq --argjson a "$event_json" '. + [$a]')
            fi
        done
    
    echo "$json_output"
}

# Main function
main() {
    local output_file="${1:-}"
    local timestamp
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    
    log_info "Starting Polyglobe fetch at $timestamp"
    
    local data_url
    data_url=$(find_data_endpoint)
    
    log_info "Trying data endpoint: $data_url"
    
    local json_data
    json_data=$(fetch_url "$data_url")
    
    local status=$?
    local articles_json="[]"
    
    if [ $status -eq 0 ] && [ -n "$json_data" ]; then
        # Check if it's valid JSON
        if echo "$json_data" | jq empty 2>/dev/null; then
            log_info "Valid JSON data found"
            articles_json="$json_data"
        else
            log_info "Invalid JSON from endpoint, trying to extract from main page"
            local html
            html=$(fetch_url "$SITE_URL")
            articles_json=$(extract_json_from_html "$html")
        fi
    else
        log_info "Failed to fetch from data endpoint, trying main page"
        local html
        html=$(fetch_url "$SITE_URL")
        articles_json=$(extract_json_from_html "$html")
        
        if [ "$articles_json" = "{}" ]; then
            log_info "Trying event extraction"
            articles_json=$(extract_events "$html")
        fi
    fi
    
    # Check if we have any data
    local item_count
    item_count=$(echo "$articles_json" | jq 'length // 0' 2>/dev/null)
    
    if [ "$item_count" -eq 0 ]; then
        log_warn "No data found. Creating basic output..."
        articles_json=$(cat <<EOF
{
    "source": "pizzint.watch/polyglobe",
    "message": "Unable to extract data",
    "url": "$SITE_URL",
    "extracted_at": "$timestamp"
}
EOF
        )
    fi
    
    # Build final output
    local final_json
    final_json=$(cat <<EOF
{
    "status": "success",
    "timestamp": "$timestamp",
    "source": "pizzint.watch/polyglobe",
    "url": "$SITE_URL",
    "data_url": "$data_url",
    "items_count": $item_count,
    "data": $articles_json,
    "extracted_at": "$timestamp"
}
EOF
    )
    
    # Format output if jq is available
    if command -v jq &>/dev/null; then
        final_json=$(echo "$final_json" | jq '.')
    fi
    
    # Output to file or stdout
    if [ -n "$output_file" ]; then
        echo "$final_json" > "$output_file"
        log_info "Data saved to: $output_file"
    else
        echo "$final_json"
    fi
    
    log_info "Fetch complete"
}

# Check if jq is available
if ! command -v jq &>/dev/null; then
    log_warn "jq is not installed. JSON output will not be pretty-printed."
    log_warn "Install jq with: apt install jq (Debian/Ubuntu) or apk add jq (Alpine)"
fi

# Run main
main "$@"
