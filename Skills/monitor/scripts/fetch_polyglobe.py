#!/usr/bin/env python3
"""
fetch_polyglobe.py
Fetches data from Pizzint.watch Polyglobe app

Usage:
    python3 fetch_polyglobe.py [--output FILE.json]
    python3 fetch_polyglobe.py --format compact

Requirements: Python 3.x with requests and beautifulsoup4 (optional)
Works in: Cloud VMs, AI chat apps (Gemini, ChatGPT, etc.)

Description:
    This script fetches data from the Polyglobe visualization app at
    https://www.pizzint.watch/polyglobe/app. It extracts geographic
    data, events, and visualizations.

Features:
    - Rate limiting detection and retry
    - Error handling with graceful degradation
    - Clean JSON output
    - Multiple extraction strategies
"""

import sys
import os
import json
import time
import re
import argparse
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

# Try to import optional libraries
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    import urllib.request
    import urllib.error

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False


class PolyglobeFetcher:
    """Fetches data from Pizzint.watch Polyglobe app."""
    
    SITE_URL = "https://www.pizzint.watch/polyglobe/app"
    BASE_URL = "https://www.pizzint.watch"
    USER_AGENT = ('Mozilla/5.0 (compatible; PolyglobeFetcher/1.0; ' 
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
                'Accept-Language': 'en-US,en;q=0.9'
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
        headers = {
            'User-Agent': self.USER_AGENT,
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
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
                
                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = response.headers.get('Retry-After', 5)
                    if attempt < self.MAX_RETRIES - 1:
                        self.log(f"Rate limited. Retrying after {retry_after} seconds...", 'warning')
                        time.sleep(int(retry_after))
                        continue
                    else:
                        self.log("Rate limited. Max retries reached.", 'error')
                        return None, response.status_code
                
                if response.status_code == 200:
                    try:
                        return response.json(), response.status_code
                    except (json.JSONDecodeError, ValueError):
                        return response.text, response.status_code
                else:
                    self.log(f"HTTP {response.status_code}", 'error')
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(2 ** attempt)
                        continue
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
    
    def _fetch_with_urllib(self, url, headers):
        """Fetch using urllib as fallback."""
        req = urllib.request.Request(url, headers=headers)
        
        for attempt in range(self.MAX_RETRIES):
            try:
                with urllib.request.urlopen(req, timeout=self.TIMEOUT) as response:
                    data = response.read().decode('utf-8')
                    status_code = response.getcode()
                    
                    try:
                        parsed = json.loads(data)
                        return parsed, status_code
                    except (json.JSONDecodeError, ValueError):
                        return data, status_code
                        
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < self.MAX_RETRIES - 1:
                    retry_after = e.headers.get('Retry-After', 5)
                    self.log(f"Rate limited. Retrying after {retry_after} seconds...", 'warning')
                    time.sleep(int(retry_after))
                    continue
                self.log(f"HTTP error: {e.code}", 'error')
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return None, e.code
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
    
    def find_data_endpoint(self, html=None):
        """Try to find the data endpoint from the HTML."""
        if html is None:
            # Fetch main page first
            html, status_code = self.fetch_url(self.SITE_URL)
            if html is None:
                self.log("Failed to fetch main page", 'error')
                return [f"{self.BASE_URL}/polyglobe/data.json"]
        
        endpoints = []
        
        if BEAUTIFULSOUP_AVAILABLE:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for script tags with data
            script_tags = soup.find_all('script')
            for script in script_tags:
                script_text = script.string or ''
                
                # Look for API endpoints
                api_matches = re.findall(
                    r'"(https?://[^"]+/polyglobe/(api|data|events)[^"]*)"',
                    script_text
                )
                endpoints.extend([url for url, _ in api_matches])
                
                # Look for fetch/axios calls
                fetch_matches = re.findall(
                    r"['\"]?(https?://[^'\"]+/polyglobe/[^'\"]+)['\"]?",
                    script_text
                )
                endpoints.extend(fetch_matches)
        else:
            # Regex-based extraction
            api_matches = re.findall(
                r'"(https?://[^"]+/polyglobe/(api|data|events)[^"]*)"',
                html
            )
            endpoints.extend([url for url, _ in api_matches])
            
            fetch_matches = re.findall(
                r"['\"]?(https?://[^'\"]+/polyglobe/[^'\"]+)['\"]?",
                html
            )
            endpoints.extend(fetch_matches)
        
        # Add default endpoints
        default_endpoints = [
            f"{self.BASE_URL}/polyglobe/data.json",
            f"{self.BASE_URL}/polyglobe/api/data",
            f"{self.BASE_URL}/polyglobe/api/events",
            f"{self.BASE_URL}/polyglobe/events.json",
        ]
        
        # Combine and deduplicate
        all_endpoints = list(set(endpoints + default_endpoints))
        
        self.log(f"Found {len(all_endpoints)} potential endpoints")
        
        return all_endpoints
    
    def extract_json_from_html(self, html):
        """Try to extract JSON data from HTML."""
        # Look for JSON data in script tags
        if BEAUTIFULSOUP_AVAILABLE:
            soup = BeautifulSoup(html, 'html.parser')
            script_tags = soup.find_all('script')
            
            for script in script_tags:
                script_text = script.string or ''
                
                # Look for JSON objects
                json_matches = re.findall(
                    r'\s*\{.*polyglobe.*\}\s*',
                    script_text,
                    re.DOTALL
                )
                
                for match in json_matches:
                    try:
                        data = json.loads(match)
                        if isinstance(data, dict) and len(data) > 0:
                            self.log("Extracted JSON from HTML script tag")
                            return data
                    except (json.JSONDecodeError, ValueError):
                        continue
        
        # Try regex extraction
        json_matches = re.findall(
            r'\s*\{.*polyglobe.*\}\s*',
            html,
            re.DOTALL
        )
        
        for match in json_matches:
            try:
                data = json.loads(match)
                if isinstance(data, dict) and len(data) > 0:
                    self.log("Extracted JSON from HTML using regex")
                    return data
            except (json.JSONDecodeError, ValueError):
                continue
        
        # Try to find any large JSON object
        json_matches = re.findall(
            r'\{.*\{.*\}.*\}',
            html,
            re.DOTALL
        )
        
        for match in json_matches[:3]:
            try:
                data = json.loads(match)
                if isinstance(data, dict) and len(data) > 0:
                    self.log("Extracted JSON from HTML (generic)")
                    return data
            except (json.JSONDecodeError, ValueError):
                continue
        
        return {}
    
    def extract_events(self, html):
        """Extract geographic events from HTML."""
        events = []
        
        if BEAUTIFULSOUP_AVAILABLE:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for elements with data attributes
            event_elements = soup.find_all(
                attrs={'data-lat': True, 'data-lng': True}
            )
            
            for i, elem in enumerate(event_elements):
                lat = elem.get('data-lat')
                lng = elem.get('data-lng')
                name = elem.get('data-name') or elem.get_text(strip=True)
                
                if lat and lng:
                    try:
                        lat_float = float(lat)
                        lng_float = float(lng)
                        events.append({
                            'id': i + 1,
                            'latitude': lat_float,
                            'longitude': lng_float,
                            'name': name or 'Unknown Event',
                            'source': 'pizzint.watch/polyglobe',
                            'extracted_at': datetime.now(timezone.utc).isoformat()
                        })
                    except ValueError:
                        continue
            
            # Look for script tags with location data
            script_tags = soup.find_all('script')
            for script in script_tags:
                script_text = script.string or ''
                
                # Look for latitude/longitude patterns
                location_matches = re.findall(
                    r'\{.*?lat\s*[\:=\s]+\s*([\-0-9.]+).*?lng\s*[\:=\s]+\s*([\-0-9.]+).*?\}',
                    script_text,
                    re.DOTALL | re.IGNORECASE
                )
                
                for j, (lat, lng) in enumerate(location_matches):
                    try:
                        events.append({
                            'id': len(events) + 1 + j,
                            'latitude': float(lat),
                            'longitude': float(lng),
                            'name': 'Event from script',
                            'source': 'pizzint.watch/polyglobe',
                            'extracted_at': datetime.now(timezone.utc).isoformat()
                        })
                    except ValueError:
                        continue
        else:
            # Regex-based extraction
            location_matches = re.findall(
                r'latitude[\"\']?\s*[\:=\s]+\s*([\-0-9.]+).*?longitude[\"\']?\s*[\:=\s]+\s*([\-0-9.]+)',
                html,
                re.DOTALL | re.IGNORECASE
            )
            
            for i, (lat, lng) in enumerate(location_matches):
                try:
                    events.append({
                        'id': i + 1,
                        'latitude': float(lat),
                        'longitude': float(lng),
                        'name': 'Event',
                        'source': 'pizzint.watch/polyglobe',
                        'extracted_at': datetime.now(timezone.utc).isoformat()
                    })
                except ValueError:
                    continue
        
        self.log(f"Extracted {len(events)} events")
        return events
    
    def fetch_data(self):
        """Fetch data from Polyglobe app."""
        timestamp = datetime.now(timezone.utc).isoformat()
        self.log(f"Starting Polyglobe fetch at {timestamp}")
        
        data = {}
        
        # Try direct data endpoints first
        self.log("Fetching main page...")
        html, status_code = self.fetch_url(self.SITE_URL)
        
        if html is None:
            self.log("Failed to fetch main page, trying direct endpoints", 'warning')
            html = None
        
        # Find data endpoints
        endpoints = self.find_data_endpoint(html)
        
        # Try each endpoint
        for endpoint in endpoints:
            self.log(f"Trying endpoint: {endpoint}")
            
            response_data, status_code = self.fetch_url(endpoint)
            
            if response_data is not None:
                if isinstance(response_data, dict):
                    data = response_data
                    self.log(f"Success! Got data from {endpoint}")
                    break
                elif isinstance(response_data, str):
                    try:
                        data = json.loads(response_data)
                        self.log(f"Success! Got JSON data from {endpoint}")
                        break
                    except (json.JSONDecodeError, ValueError):
                        # Not JSON, continue trying
                        pass
        
        # If no data from endpoints, try to extract from HTML
        if not data:
            self.log("No data from endpoints, trying HTML extraction")
            data = self.extract_json_from_html(html)
        
        # If still no data, try event extraction
        if not data:
            self.log("No JSON data found, trying event extraction")
            events = self.extract_events(html)
            data = {
                'events': events,
                'source': self.SITE_URL,
                'extracted_at': timestamp
            }
        
        # Ensure we have some data
        if not data:
            data = {
                'source': self.SITE_URL,
                'message': 'Unable to extract data from Polyglobe app',
                'url': self.SITE_URL,
                'extracted_at': timestamp
            }
        
        return {
            'status': 'success',
            'timestamp': timestamp,
            'source': self.SITE_URL,
            'endpoints_tried': endpoints[:5],  # First 5 endpoints
            'data': data,
            'extracted_at': timestamp
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Fetch data from Pizzint.watch Polyglobe app',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 fetch_polyglobe.py
  python3 fetch_polyglobe.py --output polyglobe_data.json
  python3 fetch_polyglobe.py --format compact
  
Requirements:
  - Python 3.x
  - requests library (recommended)
  - beautifulsoup4 library (optional, for better extraction)
  
Install requirements:
  pip install requests beautifulsoup4
        """
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output file path (e.g., polyglobe_data.json)'
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
        original_log = PolyglobeFetcher.log
        def silent_log(self, message, level='info'):
            if level == 'error':
                original_log(self, message, level)
        PolyglobeFetcher.log = silent_log
    
    fetcher = PolyglobeFetcher()
    result = fetcher.fetch_data()
    
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
