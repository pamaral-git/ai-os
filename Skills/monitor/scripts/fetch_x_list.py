#!/usr/bin/env python3
"""
fetch_x_list.py
Fetches tweets from a public X.com (Twitter) list using various methods.

Since direct access to X.com lists requires authentication, this script
uses alternative approaches:
1. RSS feed (if available)
2. Nitter instances (self-hosted Twitter alternatives)
3. Twitter API v2 (requires Bearer token from developer.twitter.com)

Usage:
    python3 fetch_x_list.py LIST_ID [--output FILE.json]
    python3 fetch_x_list.py 1854578015587500532 --method nitter --limit 50
    python3 fetch_x_list.py --help

Requirements: Python 3.x with requests library (or uses urllib as fallback)
Works in: Cloud VMs, AI chat apps (Gemini, ChatGPT, etc.)

NOTE: X.com lists may require authentication. This script uses public
      alternatives that may have limitations.
"""

import sys
import os
import json
import time
import re
import argparse
from datetime import datetime, timezone

# Try to import requests, fall back to urllib
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    import urllib.request
    import urllib.error
    from urllib.parse import urlencode


class XListFetcher:
    """Fetches tweets from X.com lists using various methods."""
    
    USER_AGENT = ('Mozilla/5.0 (compatible; XListFetcher/1.0; ' 
                  '+https://github.com/situation-monitor)')
    TIMEOUT = 30
    MAX_RETRIES = 3
    
    # Nitter instances to try
    NITTER_INSTANCES = [
        'https://nitter.net',
        'https://nitter.1d4.us',
        'https://nitter.privacydev.net',
        'https://nitter.fly.dev',
    ]
    
    # RSS-to-JSON services
    RSS_TO_JSON_SERVICES = [
        'https://rss2json.com/api/v1/json',
        'https://api.rss2json.com/v1',
    ]
    
    def __init__(self):
        self.session = None
        if REQUESTS_AVAILABLE:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': self.USER_AGENT,
                'Accept': 'application/json',
            })
    
    def log(self, message, level='info'):
        """Print formatted log messages."""
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        if level == 'error':
            print(f"[{timestamp}] [ERROR] {message}", file=sys.stderr)
        elif level == 'warning':
            print(f"[{timestamp}] [WARNING] {message}", file=sys.stderr)
        else:
            print(f"[{timestamp}] [INFO] {message}")
    
    def fetch_url(self, url, use_json_accept=True):
        """Fetch a URL with retry logic."""
        headers = {'User-Agent': self.USER_AGENT}
        if use_json_accept:
            headers['Accept'] = 'application/json'
        
        if REQUESTS_AVAILABLE:
            return self._fetch_with_requests(url, headers)
        else:
            return self._fetch_with_urllib(url, headers)
    
    def _fetch_with_requests(self, url, headers):
        """Fetch using requests library."""
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.get(
                    url,
                    headers=headers,
                    timeout=self.TIMEOUT
                )
                
                if response.status_code == 200:
                    try:
                        return response.json(), response.status_code, response.headers
                    except (json.JSONDecodeError, ValueError):
                        return response.text, response.status_code, response.headers
                elif response.status_code == 429:
                    retry_after = response.headers.get('Retry-After', 5)
                    if attempt < self.MAX_RETRIES - 1:
                        self.log(f"Rate limited. Retrying after {retry_after} seconds...", 'warning')
                        time.sleep(int(retry_after))
                        continue
                else:
                    self.log(f"HTTP {response.status_code}", 'error')
                    return None, response.status_code, {}
                    
            except requests.exceptions.Timeout:
                self.log(f"Timeout (attempt {attempt + 1})", 'warning')
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None, 0, {}
            except requests.exceptions.RequestException as e:
                self.log(f"Request error: {e}", 'error')
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None, 0, {}
        
        return None, 0, {}
    
    def _fetch_with_urllib(self, url, headers):
        """Fetch using urllib as fallback."""
        req = urllib.request.Request(url, headers=headers)
        
        for attempt in range(self.MAX_RETRIES):
            try:
                with urllib.request.urlopen(req, timeout=self.TIMEOUT) as response:
                    data = response.read().decode('utf-8')
                    status_code = response.getcode()
                    response_headers = dict(response.headers)
                    
                    if status_code == 200:
                        try:
                            parsed = json.loads(data)
                            return parsed, status_code, response_headers
                        except (json.JSONDecodeError, ValueError):
                            return data, status_code, response_headers
                    else:
                        self.log(f"HTTP {status_code}", 'error')
                        return None, status_code, {}
                        
            except urllib.error.URLError as e:
                self.log(f"URL error: {e}", 'error')
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None, 0, {}
            except Exception as e:
                self.log(f"Error: {e}", 'error')
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None, 0, {}
        
        return None, 0, {}
    
    def fetch_via_rss(self, list_id, limit):
        """Try to fetch list via RSS feed."""
        self.log(f"Fetching list {list_id} via RSS...")
        
        # Try direct X.com RSS (unlikely to work without auth)
        rss_urls = [
            f'https://x.com/i/lists/{list_id}/rss',
            f'https://twitter.com/i/lists/{list_id}/rss',
        ]
        
        for rss_url in rss_urls:
            self.log(f"Trying RSS URL: {rss_url}")
            data, status, headers = self.fetch_url(rss_url, use_json_accept=False)
            
            if status == 200 and data:
                # Check if it's XML/RSS
                if isinstance(data, str) and data.strip().startswith('<?xml'):
                    # Convert RSS to JSON
                    return self._rss_to_json(data, list_id, limit)
        
        # Try RSS-to-JSON services
        for service_url in self.RSS_TO_JSON_SERVICES:
            params = {'rss_url': f'https://x.com/i/lists/{list_id}'}
            service_full_url = f"{service_url}?{urlencode(params)}"
            self.log(f"Trying RSS-to-JSON: {service_full_url}")
            
            data, status, headers = self.fetch_url(service_full_url)
            if status == 200 and data:
                return data
        
        return None
    
    def _rss_to_json(self, rss_xml, list_id, limit):
        """Convert RSS XML to JSON."""
        # Simple RSS parsing (for basic RSS feeds)
        items = []
        
        # Extract items using regex (simple approach)
        item_pattern = re.compile(
            r'<item>.*?<title>(.*?)</title>.*?'
            r'<link>(.*?)</link>.*?'
            r'<pubDate>(.*?)</pubDate>.*?'
            r'<description>(.*?)</description>.*?'
            r'</item>',
            re.DOTALL
        )
        
        matches = item_pattern.findall(rss_xml)
        for match in matches[:limit]:
            items.append({
                'title': match[0],
                'link': match[1],
                'pubDate': match[2],
                'description': match[3]
            })
        
        return {
            'source': 'rss',
            'list_id': list_id,
            'items': items,
            'count': len(items)
        }
    
    def fetch_via_nitter(self, list_id, limit):
        """Try to fetch list via Nitter instances."""
        self.log(f"Fetching list {list_id} via Nitter...")
        
        for instance in self.NITTER_INSTANCES:
            url = f"{instance}/i/lists/{list_id}"
            self.log(f"Trying Nitter: {url}")
            
            data, status, headers = self.fetch_url(url, use_json_accept=False)
            
            if status == 200 and data:
                # Nitter returns HTML, try to extract tweets
                if isinstance(data, str):
                    tweets = self._extract_tweets_from_nitter(data, limit)
                    if tweets:
                        return {
                            'source': 'nitter',
                            'instance': instance,
                            'list_id': list_id,
                            'tweets': tweets,
                            'count': len(tweets)
                        }
        
        return None
    
    def _extract_tweets_from_nitter(self, html, limit):
        """Extract tweets from Nitter HTML."""
        # Look for tweet JSON in the HTML
        tweets = []
        
        # Pattern to find tweet data in script tags
        tweet_pattern = re.compile(r'window\.__tweets\s*=\s*(\[.*?\])', re.DOTALL)
        match = tweet_pattern.search(html)
        
        if match:
            try:
                tweets_data = json.loads(match.group(1))
                return tweets_data[:limit]
            except (json.JSONDecodeError, ValueError):
                pass
        
        # Alternative: look for individual tweet JSON objects
        json_pattern = re.compile(r'\{"id":[^}]*\}', re.DOTALL)
        matches = json_pattern.findall(html)
        
        for match in matches[:limit]:
            try:
                tweet = json.loads(match)
                tweets.append(tweet)
            except (json.JSONDecodeError, ValueError):
                pass
        
        return tweets
    
    def fetch_via_api(self, list_id, limit):
        """Try to fetch list via Twitter API v2."""
        self.log(f"Fetching list {list_id} via Twitter API v2...")
        
        # Check for Bearer token
        bearer_token = os.environ.get('BEARER_TOKEN')
        if not bearer_token:
            self.log("Twitter API v2 requires BEARER_TOKEN environment variable", 'error')
            self.log("Get a free Bearer token from: https://developer.twitter.com/en/portal/dashboard", 'error')
            return None
        
        # Twitter API v2 endpoint
        api_url = f'https://api.twitter.com/2/lists/{list_id}/tweets'
        
        # Query parameters
        params = {
            'tweet.fields': 'created_at,author_id,text,public_metrics',
            'max_results': limit,
            'expansions': 'author_id',
            'user.fields': 'name,username'
        }
        
        headers = {
            'Authorization': f'Bearer {bearer_token}',
            'Content-Type': 'application/json',
        }
        
        if REQUESTS_AVAILABLE:
            try:
                response = self.session.get(
                    api_url,
                    headers=headers,
                    params=params,
                    timeout=self.TIMEOUT
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'source': 'twitter_api_v2',
                        'list_id': list_id,
                        'data': data,
                        'meta': {
                            'result_count': data.get('meta', {}).get('result_count', 0)
                        }
                    }
                else:
                    self.log(f"Twitter API returned status {response.status_code}", 'error')
                    return None
            except Exception as e:
                self.log(f"Twitter API error: {e}", 'error')
                return None
        else:
            # urllib fallback for API
            url_with_params = f"{api_url}?{urlencode(params)}"
            req = urllib.request.Request(url_with_params, headers=headers)
            
            try:
                with urllib.request.urlopen(req, timeout=self.TIMEOUT) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    return {
                        'source': 'twitter_api_v2',
                        'list_id': list_id,
                        'data': data,
                        'meta': {
                            'result_count': data.get('meta', {}).get('result_count', 0)
                        }
                    }
            except Exception as e:
                self.log(f"Twitter API error: {e}", 'error')
                return None
        
        return None
    
    def fetch_list(self, list_id, method='rss', limit=20):
        """Fetch list using specified method."""
        self.log(f"Starting X.com list fetch for list ID: {list_id}")
        self.log(f"Method: {method}, Limit: {limit}")
        self.log(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
        
        result = None
        
        if method == 'rss':
            result = self.fetch_via_rss(list_id, limit)
        elif method == 'nitter':
            result = self.fetch_via_nitter(list_id, limit)
        elif method == 'api':
            result = self.fetch_via_api(list_id, limit)
        else:
            self.log(f"Unknown method: {method}. Use rss, nitter, or api.", 'error')
            return None
        
        if result:
            return {
                'status': 'success',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'list_id': list_id,
                'method': method,
                'result': result
            }
        else:
            return {
                'status': 'error',
                'message': f'Failed to fetch list using method: {method}',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'list_id': list_id,
                'method': method,
                'retry_after': 300
            }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Fetch tweets from X.com lists',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 fetch_x_list.py 1854578015587500532
  python3 fetch_x_list.py 1854578015587500532 --output tweets.json
  python3 fetch_x_list.py 1854578015587500532 --method nitter --limit 50
  python3 fetch_x_list.py 1854578015587500532 --method api --limit 100
  
Methods:
  rss      Use RSS feed (may not work for all lists)
  nitter   Use Nitter instance (self-hosted Twitter alternative)
  api      Use Twitter API v2 (requires BEARER_TOKEN env var)

Note: For the 'api' method, set BEARER_TOKEN environment variable:
  export BEARER_TOKEN="your_bearer_token_here"
        """
    )
    parser.add_argument(
        'list_id',
        type=str,
        help='X.com list ID (e.g., 1854578015587500532)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output file path (e.g., tweets.json)'
    )
    parser.add_argument(
        '--method', '-m',
        choices=['rss', 'nitter', 'api'],
        default='rss',
        help='Method to use (default: rss)'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=20,
        help='Maximum number of tweets to fetch (default: 20)'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['pretty', 'compact'],
        default='pretty',
        help='Output format (default: pretty)'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress log output, only show results'
    )
    
    args = parser.parse_args()
    
    # Suppress logging if quiet mode
    if args.quiet:
        original_log = XListFetcher.log
        def silent_log(self, message, level='info'):
            if level == 'error':
                original_log(self, message, level)
        XListFetcher.log = silent_log
    
    fetcher = XListFetcher()
    result = fetcher.fetch_list(
        list_id=args.list_id,
        method=args.method,
        limit=args.limit
    )
    
    # Format output
    if args.format == 'compact':
        json_str = json.dumps(result, separators=(',', ':'), ensure_ascii=False)
    else:
        json_str = json.dumps(result, indent=2, ensure_ascii=False)
    
    # Output to file or stdout
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(json_str)
            if not args.quiet:
                print(f"Data saved to: {args.output}")
        except Exception as e:
            print(f"Error writing to {args.output}: {e}", file=sys.stderr)
            print(json_str)
    else:
        print(json_str)


if __name__ == '__main__':
    main()
