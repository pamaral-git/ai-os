#!/usr/bin/env python3
"""
fetch_pizzint.py
Fetches data from pizzint.watch (Pentagon Pizza Index) without authentication.

This script attempts to extract structured data from the Next.js SPA
by fetching the main page and Polyglobe app, then extracting metadata
and any embedded JSON data.

Usage:
    python3 fetch_pizzint.py [--output FILE.json]
    python3 fetch_pizzint.py --polyglobe
    python3 fetch_pizzint.py --help

Requirements: Python 3.x with requests library (or uses urllib as fallback)
Works in: Cloud VMs, AI chat apps (Gemini, ChatGPT, etc.)
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


class PizzintFetcher:
    """Fetches data from pizzint.watch."""
    
    BASE_URLS = {
        'main': 'https://www.pizzint.watch',
        'polyglobe': 'https://www.pizzint.watch/polyglobe/app',
    }
    
    USER_AGENT = ('Mozilla/5.0 (compatible; PizzintFetcher/1.0; ' 
                  '+https://github.com/situation-monitor)')
    TIMEOUT = 60
    MAX_RETRIES = 3
    
    def __init__(self):
        self.session = None
        if REQUESTS_AVAILABLE:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': self.USER_AGENT,
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
    
    def fetch_url(self, url):
        """Fetch a URL with retry logic."""
        if REQUESTS_AVAILABLE:
            return self._fetch_with_requests(url)
        else:
            return self._fetch_with_urllib(url)
    
    def _fetch_with_requests(self, url):
        """Fetch using requests library."""
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.get(
                    url,
                    timeout=self.TIMEOUT
                )
                
                if response.status_code == 200:
                    return response.text, response.status_code
                elif response.status_code == 429:
                    retry_after = response.headers.get('Retry-After', 5)
                    if attempt < self.MAX_RETRIES - 1:
                        self.log(f"Rate limited. Retrying after {retry_after} seconds...", 'warning')
                        time.sleep(int(retry_after))
                        continue
                else:
                    self.log(f"HTTP {response.status_code} for {url}", 'error')
                    return None, response.status_code
                    
            except requests.exceptions.Timeout:
                self.log(f"Timeout (attempt {attempt + 1})", 'warning')
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None, 0
            except requests.exceptions.RequestException as e:
                self.log(f"Request error: {e}", 'error')
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None, 0
        
        return None, 0
    
    def _fetch_with_urllib(self, url):
        """Fetch using urllib as fallback."""
        req = urllib.request.Request(
            url,
            headers={'User-Agent': self.USER_AGENT}
        )
        
        for attempt in range(self.MAX_RETRIES):
            try:
                with urllib.request.urlopen(req, timeout=self.TIMEOUT) as response:
                    data = response.read().decode('utf-8')
                    status_code = response.getcode()
                    
                    if status_code == 200:
                        return data, status_code
                    else:
                        self.log(f"HTTP {status_code}", 'error')
                        return None, status_code
                        
            except urllib.error.URLError as e:
                self.log(f"URL error: {e}", 'error')
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None, 0
            except Exception as e:
                self.log(f"Error: {e}", 'error')
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None, 0
        
        return None, 0
    
    def extract_json_from_html(self, html):
        """Extract JSON data from HTML."""
        # Look for window.__* = {...} patterns
        json_pattern = re.compile(r'window\.__([A-Za-z]+)\s*=\s*(\{.*?\})', re.DOTALL)
        matches = json_pattern.findall(html)
        
        results = {}
        for var_name, json_str in matches:
            try:
                parsed = json.loads(json_str)
                results[var_name] = parsed
            except (json.JSONDecodeError, ValueError):
                pass
        
        return results
    
    def extract_metadata(self, html, url):
        """Extract metadata from HTML."""
        metadata = {}
        
        # Extract title
        title_match = re.search(r'<title>(.*?)</title>', html)
        if title_match:
            metadata['title'] = title_match.group(1)
        
        # Extract meta description
        desc_match = re.search(r'name="description"[^>]*content="(.*?)"', html)
        if desc_match:
            metadata['description'] = desc_match.group(1)
        
        # Extract OG tags
        og_tags = {
            'og_title': r'property="og:title"[^>]*content="(.*?)"',
            'og_description': r'property="og:description"[^>]*content="(.*?)"',
            'og_url': r'property="og:url"[^>]*content="(.*?)"',
            'og_image': r'property="og:image"[^>]*content="(.*?)"',
        }
        
        for tag_name, pattern in og_tags.items():
            match = re.search(pattern, html)
            if match:
                metadata[tag_name] = match.group(1)
        
        # Extract JSON data
        json_data = self.extract_json_from_html(html)
        
        return {
            'url': url,
            'metadata': metadata,
            'json_data': json_data
        }
    
    def fetch_main_page(self):
        """Fetch and parse the main PizzINT page."""
        self.log("Fetching main PizzINT page...")
        html, status = self.fetch_url(self.BASE_URLS['main'])
        
        if status == 200 and html:
            self.log("Successfully fetched main page")
            return self.extract_metadata(html, self.BASE_URLS['main'])
        return None
    
    def fetch_polyglobe(self):
        """Fetch and parse the Polyglobe app."""
        self.log("Fetching Polyglobe app...")
        html, status = self.fetch_url(self.BASE_URLS['polyglobe'])
        
        if status == 200 and html:
            self.log("Successfully fetched Polyglobe app")
            return self.extract_metadata(html, self.BASE_URLS['polyglobe'])
        return None
    
    def fetch_all(self, include_polyglobe=False):
        """Fetch data from all available sources."""
        self.log("Starting PizzINT data fetch...")
        self.log(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
        
        results = {}
        
        # Always fetch main page
        main_data = self.fetch_main_page()
        if main_data:
            results['main'] = main_data
        
        # Optionally fetch polyglobe
        if include_polyglobe:
            polyglobe_data = self.fetch_polyglobe()
            if polyglobe_data:
                results['polyglobe'] = polyglobe_data
        
        if not results:
            return {
                'status': 'error',
                'message': 'All fetch methods failed',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'source': 'pizzint.watch',
                'retry_after': 300
            }
        
        return {
            'status': 'success',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'source': 'pizzint.watch',
            'results': results
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Fetch data from pizzint.watch',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 fetch_pizzint.py
  python3 fetch_pizzint.py --output data.json
  python3 fetch_pizzint.py --polyglobe
  python3 fetch_pizzint.py --format compact
        """
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file path (e.g., data.json)'
    )
    parser.add_argument(
        '--polyglobe', '-p',
        action='store_true',
        help='Also fetch data from Polyglobe app'
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
        original_log = PizzintFetcher.log
        def silent_log(self, message, level='info'):
            if level == 'error':
                original_log(self, message, level)
        PizzintFetcher.log = silent_log
    
    fetcher = PizzintFetcher()
    result = fetcher.fetch_all(include_polyglobe=args.polyglobe)
    
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
