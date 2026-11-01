#!/usr/bin/env python3
"""
fetch_worldmonitor.py
Fetches data from WorldMonitor.app without authentication.

This script attempts multiple approaches to extract structured data:
1. Public MCP server card (no auth required)
2. API health check endpoint
3. Public tools/list via MCP (no auth required for discovery)
4. Main dashboard metadata extraction

Usage:
    python3 fetch_worldmonitor.py [--output FILE.json]
    python3 fetch_worldmonitor.py --help

Requirements: Python 3.x with requests library (or uses urllib as fallback)
Works in: Cloud VMs, AI chat apps (Gemini, ChatGPT, etc.)
"""

import sys
import os
import json
import time
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


class WorldMonitorFetcher:
    """Fetches data from WorldMonitor.app using various endpoints."""
    
    BASE_URLS = {
        'mcp': 'https://worldmonitor.app/mcp',
        'api_health': 'https://api.worldmonitor.app/api/health?compact=1',
        'dashboard': 'https://www.worldmonitor.app/dashboard',
        'server_card': 'https://worldmonitor.app/.well-known/mcp/server-card.json',
        'docs_mcp': 'https://www.worldmonitor.app/docs/mcp',
    }
    
    USER_AGENT = ('Mozilla/5.0 (compatible; WorldMonitorFetcher/1.0; ' 
                  '+https://github.com/situation-monitor)')
    TIMEOUT = 30
    MAX_RETRIES = 3
    
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
        """Fetch a URL with retry logic and exponential backoff."""
        if REQUESTS_AVAILABLE:
            return self._fetch_with_requests(url, use_json_accept)
        else:
            return self._fetch_with_urllib(url, use_json_accept)
    
    def _fetch_with_requests(self, url, use_json_accept):
        """Fetch using requests library."""
        headers = {'User-Agent': self.USER_AGENT}
        if use_json_accept:
            headers['Accept'] = 'application/json'
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.get(
                    url,
                    headers=headers,
                    timeout=self.TIMEOUT
                )
                
                if response.status_code == 200:
                    # Try to parse as JSON
                    try:
                        return response.json(), response.status_code
                    except (json.JSONDecodeError, ValueError):
                        return response.text, response.status_code
                elif response.status_code == 429:
                    # Rate limited
                    retry_after = response.headers.get('Retry-After', 5)
                    if attempt < self.MAX_RETRIES - 1:
                        self.log(f"Rate limited. Retrying after {retry_after} seconds...", 'warning')
                        time.sleep(int(retry_after))
                        continue
                elif response.status_code in (403, 401):
                    self.log(f"Authentication required or access denied for {url}", 'error')
                    return None, response.status_code
                else:
                    self.log(f"HTTP {response.status_code} for {url}", 'error')
                    return None, response.status_code
                    
            except requests.exceptions.Timeout:
                self.log(f"Timeout fetching {url} (attempt {attempt + 1})", 'warning')
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return None, 0
            except requests.exceptions.RequestException as e:
                self.log(f"Request error for {url}: {e}", 'error')
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None, 0
        
        return None, 0
    
    def _fetch_with_urllib(self, url, use_json_accept):
        """Fetch using urllib as fallback."""
        headers = {'User-Agent': self.USER_AGENT}
        if use_json_accept:
            headers['Accept'] = 'application/json'
        
        req = urllib.request.Request(url, headers=headers)
        
        for attempt in range(self.MAX_RETRIES):
            try:
                with urllib.request.urlopen(req, timeout=self.TIMEOUT) as response:
                    data = response.read().decode('utf-8')
                    status_code = response.getcode()
                    
                    if status_code == 200:
                        try:
                            return json.loads(data), status_code
                        except (json.JSONDecodeError, ValueError):
                            return data, status_code
                    else:
                        self.log(f"HTTP {status_code} for {url}", 'error')
                        return None, status_code
                        
            except urllib.error.URLError as e:
                self.log(f"URL error for {url}: {e}", 'error')
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None, 0
            except Exception as e:
                self.log(f"Error fetching {url}: {e}", 'error')
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None, 0
        
        return None, 0
    
    def post_json_rpc(self, url, method, params=None):
        """Send a JSON-RPC request."""
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': method,
            'params': params or {}
        }
        
        if REQUESTS_AVAILABLE:
            headers = {
                'User-Agent': self.USER_AGENT,
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }
            
            for attempt in range(self.MAX_RETRIES):
                try:
                    response = self.session.post(
                        url,
                        json=payload,
                        headers=headers,
                        timeout=self.TIMEOUT
                    )
                    
                    if response.status_code == 200:
                        return response.json(), response.status_code
                    elif response.status_code == 429:
                        retry_after = response.headers.get('Retry-After', 5)
                        if attempt < self.MAX_RETRIES - 1:
                            self.log(f"Rate limited. Retrying after {retry_after} seconds...", 'warning')
                            time.sleep(int(retry_after))
                            continue
                    else:
                        self.log(f"HTTP {response.status_code} for JSON-RPC {method}", 'error')
                        return None, response.status_code
                        
                except Exception as e:
                    self.log(f"Error in JSON-RPC request: {e}", 'error')
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return None, 0
        
        return None, 0
    
    def fetch_server_card(self):
        """Fetch the MCP server card (public, no auth required)."""
        self.log("Fetching WorldMonitor MCP Server Card...")
        data, status = self.fetch_url(self.BASE_URLS['server_card'])
        if status == 200 and data:
            self.log("Successfully fetched MCP server card")
            return {
                'source': 'mcp_server_card',
                'url': self.BASE_URLS['server_card'],
                'data': data,
                'status_code': status
            }
        return None
    
    def fetch_api_health(self):
        """Check API health endpoint."""
        self.log("Checking WorldMonitor API health...")
        data, status = self.fetch_url(self.BASE_URLS['api_health'])
        if status == 200 and data:
            self.log("Successfully fetched API health status")
            return {
                'source': 'api_health',
                'url': self.BASE_URLS['api_health'],
                'data': data,
                'status_code': status
            }
        return None
    
    def fetch_public_tools(self):
        """Fetch public tools list via MCP (no auth required)."""
        self.log("Fetching public tools list via MCP...")
        
        # Try to call tools/list which is public
        result, status = self.post_json_rpc(
            self.BASE_URLS['mcp'],
            'tools/list',
            {}
        )
        
        if status == 200 and result:
            self.log("Successfully fetched public tools list")
            return {
                'source': 'mcp_tools_list',
                'url': self.BASE_URLS['mcp'],
                'data': result,
                'status_code': status
            }
        return None
    
    def fetch_dashboard(self):
        """Fetch main dashboard and extract metadata."""
        self.log("Fetching main dashboard...")
        data, status = self.fetch_url(self.BASE_URLS['dashboard'], use_json_accept=False)
        if status == 200 and data:
            self.log("Successfully fetched dashboard HTML")
            # Extract any JSON from the page
            import re
            json_matches = re.findall(r'\{[^{}]*\}', data)
            extracted_data = {}
            for match in json_matches[:10]:  # Limit to first 10 matches
                try:
                    parsed = json.loads(match)
                    extracted_data[str(len(extracted_data))] = parsed
                except:
                    pass
            
            return {
                'source': 'dashboard',
                'url': self.BASE_URLS['dashboard'],
                'data': {
                    'html_metadata': extracted_data,
                    'status': 'success'
                },
                'status_code': status
            }
        return None
    
    def fetch_all(self):
        """Try all methods in order of preference."""
        self.log("Starting WorldMonitor data fetch...")
        self.log(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
        
        results = {}
        
        # Try methods in order
        methods = [
            ('public_tools', self.fetch_public_tools),
            ('server_card', self.fetch_server_card),
            ('api_health', self.fetch_api_health),
            ('dashboard', self.fetch_dashboard),
        ]
        
        for method_name, method_func in methods:
            try:
                result = method_func()
                if result and result.get('data'):
                    results[method_name] = result
                    # If we got tools list or server card, we can stop
                    if method_name in ('public_tools', 'server_card'):
                        self.log(f"Found data via {method_name}, stopping further attempts")
                        break
            except Exception as e:
                self.log(f"Error in {method_name}: {e}", 'error')
                continue
        
        if not results:
            # Create fallback response
            return {
                'status': 'error',
                'message': 'All fetch methods failed. WorldMonitor may be blocking automated requests.',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'source': 'worldmonitor.app',
                'retry_after': 300,
                'methods_tried': [name for name, _ in methods]
            }
        
        return {
            'status': 'success',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'source': 'worldmonitor.app',
            'results': results
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Fetch data from WorldMonitor.app without authentication',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 fetch_worldmonitor.py
  python3 fetch_worldmonitor.py --output data.json
  python3 fetch_worldmonitor.py --format compact
        """
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file path (e.g., data.json)'
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
        import logging
        logging.getLogger().setLevel(logging.ERROR)
        
        # Monkey patch the log method
        original_log = WorldMonitorFetcher.log
        def silent_log(self, message, level='info'):
            if level == 'error':
                original_log(self, message, level)
        WorldMonitorFetcher.log = silent_log
    
    fetcher = WorldMonitorFetcher()
    result = fetcher.fetch_all()
    
    # Format output
    if args.format == 'compact':
        json_str = json.dumps(result, separators=(',', ':'))
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
