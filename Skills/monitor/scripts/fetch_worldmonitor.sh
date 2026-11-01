#!/bin/bash
# fetch_worldmonitor.sh
# Fetches data from WorldMonitor.app
# This script fetches the main dashboard page or uses the public MCP endpoint
# to extract structured data without authentication.
#
# Usage: ./fetch_worldmonitor.sh [output_file.json]
#   If output_file.json is provided, saves to that file
#   Otherwise, prints to stdout
#
# Requirements: curl
# Works in: Cloud VMs, AI chat apps (Gemini, ChatGPT, etc.)

set -euo pipefail

# Color codes for output (only shown in terminal)
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

# WorldMonitor endpoints
MCP_ENDPOINT="https://worldmonitor.app/mcp"
API_HEALTH="https://api.worldmonitor.app/api/health?compact=1"
MAIN_DASHBOARD="https://www.worldmonitor.app/dashboard"
SITEMAP="https://www.worldmonitor.app/sitemap.xml"

# User agent to mimic a browser
USER_AGENT="Mozilla/5.0 (compatible; WorldMonitorFetcher/1.0; +https://github.com/situation-monitor)"

# Output file (optional)
OUTPUT_FILE="${1:-}"

# Temporary file for intermediate results
TMP_FILE=$(mktemp 2>/dev/null || echo "/tmp/wm_fetch_$$")
trap "rm -f \"$TMP_FILE\"" EXIT

# Function to fetch with retry logic
fetch_with_retry() {
    local url="$1"
    local max_retries=3
    local retry_delay=2
    local attempt=1
    
    while [ $attempt -le $max_retries ]; do
        if curl -s -f --retry 2 --max-time 30 \
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

# Function to extract JSON from MCP server card
fetch_mcp_server_card() {
    local server_card_url="https://worldmonitor.app/.well-known/mcp/server-card.json"
    
    log_info "Fetching WorldMonitor MCP Server Card..."
    if fetch_with_retry "$server_card_url"; then
        # Validate it's JSON
        if jq empty "$TMP_FILE" 2>/dev/null; then
            cat "$TMP_FILE"
            return 0
        else
            log_warning "Server card response is not valid JSON"
        fi
    fi
    
    return 1
}

# Function to check API health
check_api_health() {
    log_info "Checking WorldMonitor API health..."
    if fetch_with_retry "$API_HEALTH"; then
        if jq empty "$TMP_FILE" 2>/dev/null; then
            cat "$TMP_FILE"
            return 0
        fi
    fi
    
    return 1
}

# Function to fetch public tools list (no auth required)
fetch_public_tools() {
    local tools_url="https://worldmonitor.app/mcp"
    
    log_info "Fetching public tools list..."
    
    # Try to get tools/list which is public
    local tools_list_url="$tools_url"
    
    # Create a JSON-RPC request for tools/list
    cat > "$TMP_FILE" << 'EOF'
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
EOF
    
    # Send the request
    local response
    response=$(curl -s -f --max-time 30 \
        -A "$USER_AGENT" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -d @"$TMP_FILE" \
        "$tools_url" 2>/dev/null || echo "")
    
    if [ -n "$response" ]; then
        echo "$response"
        return 0
    fi
    
    return 1
}

# Main execution
main() {
    log_info "Starting WorldMonitor data fetch..."
    log_info "Timestamp: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    
    # Try multiple approaches
    local success=0
    local result=""
    
    # Approach 1: Try public tools list
    log_info "Attempting to fetch public tools list..."
    if result=$(fetch_public_tools 2>/dev/null) || [ -n "$result" ]; then
        success=1
        log_info "Successfully fetched public tools list"
    fi
    
    # Approach 2: If tools list fails, try server card
    if [ $success -eq 0 ]; then
        log_info "Attempting to fetch MCP server card..."
        if result=$(fetch_mcp_server_card 2>/dev/null) || [ -n "$result" ]; then
            success=1
            log_info "Successfully fetched MCP server card"
        fi
    fi
    
    # Approach 3: If both fail, try API health check
    if [ $success -eq 0 ]; then
        log_info "Attempting to check API health..."
        if result=$(check_api_health 2>/dev/null) || [ -n "$result" ]; then
            success=1
            log_info "Successfully fetched API health status"
        fi
    fi
    
    # If nothing worked, try the main dashboard HTML and extract metadata
    if [ $success -eq 0 ]; then
        log_info "Attempting to fetch main dashboard..."
        if fetch_with_retry "$MAIN_DASHBOARD"; then
            # Try to extract any JSON from the page
            result=$(grep -o '{[^{}]*}' "$TMP_FILE" | head -1 || echo "{}")
            if [ "$result" != "{}" ]; then
                success=1
                log_info "Extracted metadata from dashboard page"
            fi
        fi
    fi
    
    # If still no success, create a fallback response
    if [ $success -eq 0 ]; then
        log_warning "Unable to fetch data from WorldMonitor. All methods failed."
        result='{
  "status": "error",
  "message": "All fetch methods failed. WorldMonitor may be blocking automated requests.",
  "timestamp": "'"$(date -u +'%Y-%m-%dT%H:%M:%SZ')"'",
  "source": "worldmonitor.app",
  "retry_after": 300
}'
    fi
    
    # Output the result
    if [ -n "$OUTPUT_FILE" ]; then
        echo "$result" | jq . > "$OUTPUT_FILE" 2>/dev/null || echo "$result" > "$OUTPUT_FILE"
        log_info "Data saved to: $OUTPUT_FILE"
    else
        echo "$result" | jq . 2>/dev/null || echo "$result"
    fi
    
    log_info "Fetch completed."
}

# Check if jq is available for JSON formatting
if command -v jq &> /dev/null; then
    main
else
    log_warning "jq not found. Output will not be pretty-printed."
    main
fi
