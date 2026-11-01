#!/bin/bash
#
# fetch_pressreader.sh
# Fetches news from PressReader.com
#
# Usage:
#   ./fetch_pressreader.sh [QUERY] [OUTPUT_FILE]
#   ./fetch_pressreader.sh "Iran" pressreader_iran.json
#   ./fetch_pressreader.sh "" latest.json  # Get latest
#
# Description:
#   This script searches PressReader for news articles. PressReader provides
#   a web interface with free access to many newspapers. This script extracts
#   article metadata and links.
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
#   - Search functionality
#

set -euo pipefail

# Configuration
BASE_URL="https://www.pressreader.com"
SEARCH_URL="https://www.pressreader.com/search"
TIMEOUT=30
MAX_RETRIES=3
RETRY_DELAY=5
USER_AGENT="Mozilla/5.0 (compatible; PressReaderFetcher/1.0; +https://github.com/situation-monitor)"

# Colors for output
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
            -H "Accept: text/html" \
            -H "Accept-Language: en-US,en;q=0.9" \
            -H "X-Requested-With: XMLHttpRequest" \
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
        
        # Check for errors in response
        if echo "$response" | grep -qi "404\|403\|500\|503\|Not Found\|Forbidden\|Access Denied"; then
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

# URL encode a string
url_encode() {
    local string="${1}"
    local encoded=""
    local length=${#string}
    
    for (( i=0; i<length; i++ )); do
        local char="${string:$i:1}"
        case "$char" in
            [a-zA-Z0-9._-])
                encoded+="$char"
                ;;
            *)
                printf -v encoded_char '%02x' "'${char}"
                encoded+="%${encoded_char}"
                ;;
        esac
    done
    
    echo "$encoded"
}

# Search PressReader
search_pressreader() {
    local query="${1:-}"
    local page="${2:-1}"
    
    log_info "Searching PressReader for: ${query:-latest}"
    
    if [ -n "$query" ]; then
        local encoded_query
        encoded_query=$(url_encode "$query")
        local url="${SEARCH_URL}?query=${encoded_query}&page=${page}"
    else
        local url="${BASE_URL}/catalog"
    fi
    
    local html
    html=$(fetch_url "$url")
    
    if [ $? -ne 0 ] || [ -z "$html" ]; then
        log_error "Failed to fetch search results"
        echo "[]"
        return
    fi
    
    extract_articles "$html"
}

# Extract articles from HTML
extract_articles() {
    local html="$1"
    local json_output="[]"
    local count=0
    
    # Try to find article cards/containers
    # PressReader typically uses specific class names
    local articles
    articles=$(echo "$html" | grep -o '<article[^>]*>.*?</article>' | head -30)
    
    if [ -n "$articles" ]; then
        echo "$html" | grep -o '<article[^>]*>.*?</article>' | head -30 | while IFS= read -r article_html; do
            count=$((count + 1))
            
            # Extract title
            local title
            title=$(echo "$article_html" | grep -o '<h[1-3][^>]*>.*?</h[1-3]>' | sed 's/<[^>]*>//g' | head -1 | tr -d '\n' | sed 's/^[ \t]*//;s/[ \t]*$//')
            
            # Extract URL
            local url
            url=$(echo "$article_html" | grep -oE 'https?://\S+' | grep pressreader.com | head -1 | tr -d '\n')
            
            # Extract publication name
            local publication
            publication=$(echo "$article_html" | grep -oE '[A-Za-z][^<>]+' | grep -i "newspaper\|publication\|magazine" | head -1 | tr -d '\n' | sed 's/^[ \t]*//;s/[ \t]*$//')
            
            # Extract date
            local date
            date=$(echo "$article_html" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}|[A-Za-z]{3} [0-9]{1,2}, [0-9]{4}|[0-9]{1,2} [A-Za-z]{3} [0-9]{4}' | head -1 | tr -d '\n')
            
            # Extract snippet
            local snippet
            snippet=$(echo "$article_html" | grep -o '<p[^>]*>.*?</p>' | sed 's/<[^>]*>//g' | head -1 | tr -d '\n' | sed 's/^[ \t]*//;s/[ \t]*$//')
            
            if [ -n "$title" ] || [ -n "$url" ]; then
                local article_json
                article_json=$(cat <<EOF
{
    "id": $count,
    "title": "${title:-Untitled}",
    "url": "${url:-$BASE_URL}",
    "publication": "${publication:-}",
    "date": "${date:-}",
    "snippet": "${snippet:-}",
    "source": "pressreader.com",
    "extracted_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
                )
                json_output=$(echo "$json_output" | jq --argjson a "$article_json" '. + [$a]')
            fi
        done
    else
        # Try alternative pattern: div-based article containers
        echo "$html" | grep -o '<div[^>]*(article|post|card|publication)[^>]*>.*?</div>' | head -30 | while IFS= read -r item; do
            count=$((count + 1))
            
            title=$(echo "$item" | grep -o '<[ha][1-6][^>]*>.*?</[ha][1-6]>' | sed 's/<[^>]*>//g' | head -1 | tr -d '\n')
            url=$(echo "$item" | grep -oE 'https?://\S+' | grep pressreader.com | head -1 | tr -d '\n')
            publication=$(echo "$item" | grep -oE '[A-Za-z][^<>]+' | grep -iE "times|herald|tribune|post|news|daily" | head -1 | tr -d '\n')
            
            if [ -n "$title" ] || [ -n "$url" ]; then
                local article_json
                article_json=$(cat <<EOF
{
    "id": $count,
    "title": "${title:-Untitled}",
    "url": "${url:-$BASE_URL}",
    "publication": "${publication:-}",
    "source": "pressreader.com",
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

# Extract from catalog page (latest)
extract_catalog() {
    local html="$1"
    
    # Look for publication links
    local json_output="[]"
    local count=0
    
    echo "$html" | grep -oE '<a[^>]+href="[^"]+/catalog/[^"]+"[^>]*>.*?</a>' | head -30 | while IFS= read -r link; do
        count=$((count + 1))
        
        local href
        href=$(echo "$link" | grep -oE 'href="([^"]+)"' | sed 's/href="//;s/"//' | head -1)
        
        local title
        title=$(echo "$link" | sed 's/<[^>]*>//g' | tr -d '\n' | sed 's/^[ \t]*//;s/[ \t]*$//')
        
        if [ -n "$href" ]; then
            local article_json
            article_json=$(cat <<EOF
{
    "id": $count,
    "title": "${title:-Untitled}",
    "url": "${BASE_URL}${href}",
    "source": "pressreader.com/catalog",
    "extracted_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
            )
            json_output=$(echo "$json_output" | jq --argjson a "$article_json" '. + [$a]')
        fi
    done
    
    echo "$json_output"
}

# Main function
main() {
    local query="${1:-}"
    local output_file="${2:-}"
    local timestamp
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    
    log_info "Starting PressReader fetch at $timestamp"
    
    local articles_json="[]"
    
    if [ -n "$query" ]; then
        articles_json=$(search_pressreader "$query" 1)
    else
        # Fetch catalog (latest)
        log_info "Fetching latest from catalog..."
        local html
        html=$(fetch_url "${BASE_URL}/catalog")
        
        if [ $? -ne 0 ] || [ -z "$html" ]; then
            log_error "Failed to fetch catalog"
            articles_json=$(search_pressreader "" 1)
        else
            articles_json=$(extract_catalog "$html")
        fi
    fi
    
    local article_count
    article_count=$(echo "$articles_json" | jq 'length')
    
    # Build final output
    local final_json
    final_json=$(cat <<EOF
{
    "status": "success",
    "timestamp": "$timestamp",
    "source": "pressreader.com",
    "query": "${query:-latest}",
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

# Run main
main "$@"
