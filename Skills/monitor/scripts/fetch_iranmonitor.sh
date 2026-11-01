#!/bin/bash
#
# fetch_iranmonitor.sh
# Fetches news/updates from iranmonitor.org
#
# Usage:
#   ./fetch_iranmonitor.sh [OUTPUT_FILE]
#   ./fetch_iranmonitor.sh articles.json
#
# Description:
#   This script scrapes the latest articles and updates from iranmonitor.org
#   without requiring authentication. It extracts article titles, URLs, dates,
#   and summaries.
#
# Requirements:
#   - curl (for HTTP requests)
#   - jq (optional, for JSON formatting)
#   - grep, sed, awk (for text processing)
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
SITE_URL="https://www.iranmonitor.org"
TIMEOUT=30
MAX_RETRIES=3
RETRY_DELAY=5
USER_AGENT="Mozilla/5.0 (compatible; IranMonitorFetcher/1.0; +https://github.com/situation-monitor)"

# Colors for output (disabled by default for scripting)
RED=''
GREEN=''
YELLOW=''
BLUE=''
NC=''

# Enable colors if not running in a pipeline
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
fi

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Rate limiting and retry logic
fetch_url() {
    local url="$1"
    local attempt=0
    local success=0
    
    while [ $attempt -lt $MAX_RETRIES ]; do
        attempt=$((attempt + 1))
        
        local response
        response=$(curl -s -f -L --max-time $TIMEOUT \
            -A "$USER_AGENT" \
            -H "Accept: text/html" \
            -H "Accept-Language: en-US,en;q=0.9" \
            "$url" 2>/dev/null)
        
        local status=$?
        
        # Check for rate limiting
        if echo "$response" | grep -qi "rate limit\|too many requests\|429"; then
            if [ $attempt -lt $MAX_RETRIES ]; then
                log_warn "Rate limited. Retrying in $RETRY_DELAY seconds..."
                sleep $RETRY_DELAY
                continue
            else
                log_error "Rate limited. Max retries reached."
                return 1
            fi
        fi
        
        # Check for other errors
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
        
        # Check for HTTP errors in response
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
        
        # Success
        echo "$response"
        return 0
    done
    
    return 1
}

# Extract articles from main page
extract_articles() {
    local html="$1"
    local json_output="[]"
    
    # Counter for articles
    local count=0
    
    # Extract article links and info using a simple approach
    # This looks for common patterns in news sites
    
    # Pattern 1: Look for <article> tags
    local articles
    articles=$(echo "$html" | grep -o '<article[^>]*>.*?</article>' | head -20)
    
    if [ -n "$articles" ]; then
        echo "$html" | while IFS= read -r line; do
            # Extract article data
            title=$(echo "$line" | grep -o '<h[1-3][^>]*>.*?</h[1-3]>' | sed 's/<[^>]*>//g' | head -1 | tr -d '\n')
            url=$(echo "$line" | grep -oE 'https?://\S+' | head -1 | tr -d '\n')
            date=$(echo "$line" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}|[A-Za-z]{3} [0-9]{1,2}, [0-9]{4}' | head -1 | tr -d '\n')
            summary=$(echo "$line" | grep -o '<p[^>]*>.*?</p>' | sed 's/<[^>]*>//g' | head -1 | tr -d '\n' | sed 's/^[ \t]*//;s/[ \t]*$//')
            
            if [ -n "$title" ] || [ -n "$url" ]; then
                count=$((count + 1))
                local article_json
                article_json=$(cat <<EOF
{
    "id": $count,
    "title": "${title:-Untitled}",
    "url": "${url:-$SITE_URL}",
    "date": "${date:-}",
    "summary": "${summary:-}",
    "source": "iranmonitor.org",
    "extracted_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
                )
                json_output=$(echo "$json_output" | jq --argjson a "$article_json" '. + [$a]')
            fi
        done
    else
        # Pattern 2: Look for common news item patterns
        echo "$html" | grep -o '<div class="[^"]*post[^"]*"[^>]*>.*?</div>' | head -20 | while IFS= read -r item; do
            title=$(echo "$item" | grep -o '<h[1-3][^>]*>.*?</h[1-3]>' | sed 's/<[^>]*>//g' | head -1 | tr -d '\n')
            url=$(echo "$item" | grep -oE 'https?://\S+' | head -1 | tr -d '\n')
            date=$(echo "$item" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}|[A-Za-z]{3} [0-9]{1,2}, [0-9]{4}' | head -1 | tr -d '\n')
            
            if [ -n "$title" ] || [ -n "$url" ]; then
                count=$((count + 1))
                local article_json
                article_json=$(cat <<EOF
{
    "id": $count,
    "title": "${title:-Untitled}",
    "url": "${url:-$SITE_URL}",
    "date": "${date:-}",
    "source": "iranmonitor.org",
    "extracted_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
                )
                json_output=$(echo "$json_output" | jq --argjson a "$article_json" '. + [$a]')
            fi
        done
    fi
    
    echo "$json_output"
}

# Extract latest news section
extract_latest_news() {
    local html="$1"
    
    # Look for a "Latest News" or "Recent" section
    local latest_section
    latest_section=$(echo "$html" | grep -A 50 -i "latest news\|recent\|breaking" | head -50)
    
    if [ -n "$latest_section" ]; then
        extract_articles "$latest_section"
    else
        echo "[]"
    fi
}

# Main function
main() {
    local output_file="${1:-}"
    local timestamp
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    
    log_info "Starting IranMonitor fetch at $timestamp"
    
    # Fetch main page
    log_info "Fetching $SITE_URL..."
    local html
    html=$(fetch_url "$SITE_URL")
    
    if [ $? -ne 0 ] || [ -z "$html" ]; then
        log_error "Failed to fetch main page from $SITE_URL"
        exit 1
    fi
    
    log_info "Main page fetched successfully"
    
    # Try to extract articles
    log_info "Extracting articles..."
    local articles_json
    articles_json=$(extract_articles "$html")
    
    if [ "$articles_json" = "[]" ]; then
        # Try latest news section
        log_info "Trying latest news section..."
        articles_json=$(extract_latest_news "$html")
    fi
    
    # Check if we have any articles
    local article_count
    article_count=$(echo "$articles_json" | jq 'length')
    
    if [ "$article_count" -eq 0 ]; then
        log_warn "No articles found. Trying alternative extraction..."
        
        # Try to extract all links as fallback
        articles_json=$(echo "$html" | grep -oE '<a[^>]+href="[^"]*"[^>]*>[^<]+</a>' | \
            grep -oE 'href="([^"]+)".*>([^<]+)<' | \
            sed 's/href="\([^"]*\)".*>\?\([^<]*\)/{"url":"\1","title":"\2"}/' | \
            head -20 | jq -s '.')
    fi
    
    # Build final output
    local final_json
    final_json=$(cat <<EOF
{
    "status": "success",
    "timestamp": "$timestamp",
    "source": "iranmonitor.org",
    "url": "$SITE_URL",
    "articles_count": $article_count,
    "articles": $articles_json,
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

# Run main function
main "$@"
