#!/usr/bin/env python3
"""
fetch_monitor_the_situation.py
Fetches data from monitor-the-situation.com without authentication.

This script uses the public /api/events endpoint which returns JSON data
without requiring authentication.

Usage:
    python3 fetch_monitor_the_situation.py [--output FILE.json]
    python3 fetch_monitor_the_situation.py --limit 100 --category political
    python3 fetch_monitor_the_situation.py --help

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


class MonitorTheSituationFetcher:
    """Fetches events from monitor-the-situation.com."""
    
    API_URL = 'https://monitor-the-situation.com/api/events'
    USER_AGENT = ('Mozilla/5.0 (compatible; MonitorTheSituationFetcher/1.0; ' 
                  '+https://github.com/situation-monitor)')
    TIMEOUT = 60
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
    
    def fetch_events(self):
        """Fetch all events from the API."""
        self.log("Fetching events from monitor-the-situation.com...")
        
        if REQUESTS_AVAILABLE:
            return self._fetch_with_requests()
        else:
            return self._fetch_with_urllib()
    
    def _fetch_with_requests(self):
        """Fetch using requests library."""
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.get(
                    self.API_URL,
                    timeout=self.TIMEOUT
                )
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        self.log(f"Successfully fetched {len(data) if isinstance(data, list) else 0} events")
                        return data, response.status_code
                    except (json.JSONDecodeError, ValueError) as e:
                        self.log(f"Failed to parse JSON: {e}", 'error')
                        return None, response.status_code
                elif response.status_code == 429:
                    # Rate limited
                    retry_after = response.headers.get('Retry-After', 5)
                    if attempt < self.MAX_RETRIES - 1:
                        self.log(f"Rate limited. Retrying after {retry_after} seconds...", 'warning')
                        time.sleep(int(retry_after))
                        continue
                elif response.status_code in (403, 401):
                    self.log("Authentication required or access denied", 'error')
                    return None, response.status_code
                else:
                    self.log(f"HTTP {response.status_code}", 'error')
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
    
    def _fetch_with_urllib(self):
        """Fetch using urllib as fallback."""
        req = urllib.request.Request(
            self.API_URL,
            headers={
                'User-Agent': self.USER_AGENT,
                'Accept': 'application/json',
            }
        )
        
        for attempt in range(self.MAX_RETRIES):
            try:
                with urllib.request.urlopen(req, timeout=self.TIMEOUT) as response:
                    data = response.read().decode('utf-8')
                    status_code = response.getcode()
                    
                    if status_code == 200:
                        try:
                            parsed = json.loads(data)
                            self.log(f"Successfully fetched {len(parsed) if isinstance(parsed, list) else 0} events")
                            return parsed, status_code
                        except (json.JSONDecodeError, ValueError) as e:
                            self.log(f"Failed to parse JSON: {e}", 'error')
                            return None, status_code
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
    
    def filter_events(self, events, limit=None, category=None):
        """Filter events by limit and category."""
        if not events or not isinstance(events, list):
            return events
        
        filtered = events
        
        # Apply category filter
        if category:
            filtered = [e for e in filtered if e.get('category') == category]
            self.log(f"Filtered to {len(filtered)} events with category: {category}")
        
        # Apply limit
        if limit and isinstance(limit, int):
            filtered = filtered[:limit]
            self.log(f"Limited to {len(filtered)} most recent events")
        
        return filtered


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Fetch events from monitor-the-situation.com',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 fetch_monitor_the_situation.py
  python3 fetch_monitor_the_situation.py --output events.json
  python3 fetch_monitor_the_situation.py --limit 50
  python3 fetch_monitor_the_situation.py --category conflict --limit 100
  python3 fetch_monitor_the_situation.py --format compact
        """
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file path (e.g., events.json)'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=None,
        help='Limit to N most recent events'
    )
    parser.add_argument(
        '--category', '-c',
        type=str,
        default=None,
        help='Filter by category (e.g., political, conflict, natural_disaster)'
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
    parser.add_argument(
        '--raw',
        action='store_true',
        help='Output raw JSON without wrapper metadata'
    )
    
    args = parser.parse_args()
    
    # Suppress logging if quiet mode
    if args.quiet:
        import logging
        logging.getLogger().setLevel(logging.ERROR)
        
        # Monkey patch the log method
        original_log = MonitorTheSituationFetcher.log
        def silent_log(self, message, level='info'):
            if level == 'error':
                original_log(self, message, level)
        MonitorTheSituationFetcher.log = silent_log
    
    fetcher = MonitorTheSituationFetcher()
    events, status_code = fetcher.fetch_events()
    
    if status_code != 200 or not events:
        result = {
            'status': 'error',
            'message': 'Failed to fetch events',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'source': 'monitor-the-situation.com',
            'http_status': status_code
        }
        json_str = json.dumps(result, indent=2 if args.format == 'pretty' else None)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(json_str)
        else:
            print(json_str)
        sys.exit(1)
    
    # Apply filters
    filtered_events = fetcher.filter_events(events, args.limit, args.category)
    
    # Prepare output
    if args.raw:
        result = filtered_events
    else:
        result = {
            'status': 'success',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'source': 'monitor-the-situation.com',
            'api_url': fetcher.API_URL,
            'total_events': len(events),
            'returned_events': len(filtered_events),
            'events': filtered_events
        }
    
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
