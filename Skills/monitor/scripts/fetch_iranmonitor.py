#!/usr/bin/env python3
"""
fetch_iranmonitor.py
Fetches news articles from iranmonitor.org

Usage:
    python3 fetch_iranmonitor.py [--output FILE.json]
    python3 fetch_iranmonitor.py --limit 50 --format compact

Requirements: Python 3.x with requests and beautifulsoup4 (optional)
Works in: Cloud VMs, AI chat apps (Gemini, ChatGPT, etc.)

Description:
    This script scrapes the latest articles from iranmonitor.org without
    requiring authentication. It extracts article titles, URLs, dates,
    and summaries.

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

# Try to import optional libraries
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    import urllib.request
    import urllib.error
    from urllib.parse import urlencode

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False


class IranMonitorFetcher:
    """Fetches articles from iranmonitor.org."""
    
    SITE_URL = "https://www.iranmonitor.org"
    USER_AGENT = ('Mozilla/5.0 (compatible; IranMonitorFetcher/1.0; ' 
                  '+https://github.com/situation-monitor)')
    TIMEOUT = 30
    MAX_RETRIES = 3
    
    def __init__(self):
        self.session = None
        if REQUESTS_AVAILABLE:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': self.USER_AGENT,
                'Accept': 'text/html',
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
            'Accept': 'text/html',
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
                    html = response.read().decode('utf-8')
                    return html, response.getcode()
                        
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
    
    def extract_articles(self, html, limit=50):
        """Extract articles from HTML using BeautifulSoup if available."""
        articles = []
        
        if BEAUTIFULSOUP_AVAILABLE:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try to find article containers
            article_containers = soup.find_all(['article', 'div'], class_=re.compile('post|article|news|item'), limit=limit)
            
            if not article_containers:
                # Try to find any links with text
                article_containers = soup.find_all('a', href=True, limit=limit)
            
            for i, container in enumerate(article_containers[:limit]):
                article = {}
                
                # Extract title
                title_elem = container.find(['h1', 'h2', 'h3'])
                if title_elem:
                    article['title'] = title_elem.get_text(strip=True)
                
                # Extract URL
                link_elem = container.find('a', href=True)
                if link_elem:
                    href = link_elem['href']
                    if href.startswith('/'):
                        href = f"{self.SITE_URL.rstrip('/')}{href}"
                    article['url'] = href
                
                # Extract date
                date_elem = container.find(['time', 'span'], class_=re.compile('date|time'))
                if date_elem:
                    article['date'] = date_elem.get('datetime', date_elem.get_text(strip=True))
                
                # Extract summary/excerpt
                summary_elem = container.find(['p', 'div'], class_=re.compile('excerpt|summary|desc'))
                if summary_elem:
                    article['summary'] = summary_elem.get_text(strip=True)
                
                # Ensure we have at least a title or URL
                if article.get('title') or article.get('url'):
                    article['id'] = i + 1
                    article['source'] = 'iranmonitor.org'
                    articles.append(article)
        else:
            # Fallback to regex extraction
            articles = self._extract_articles_with_regex(html, limit)
        
        return articles
    
    def _extract_articles_with_regex(self, html, limit):
        """Extract articles using regex patterns."""
        articles = []
        
        # Pattern 1: Look for article containers with titles and links
        # This is a simple regex-based approach
        
        # Extract all potential article blocks
        article_blocks = re.findall(
            r'(?:<article[^>]*>|<div[^>]*(?:post|article|news|item)[^>]*>)(.*?)(?:</article>|</div>)',
            html,
            re.DOTALL
        )
        
        for i, block in enumerate(article_blocks[:limit]):
            article = {}
            
            # Extract title
            title_match = re.search(r'<(?:h1|h2|h3)[^>]*>(.*?)</\1>', block, re.DOTALL)
            if title_match:
                article['title'] = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            
            # Extract URL
            url_match = re.search(r'<a\s+[^>]*href="([^"]+)"[^>]*>', block)
            if url_match:
                url = url_match.group(1)
                if url.startswith('/'):
                    url = f"{self.SITE_URL.rstrip('/')}{url}"
                article['url'] = url
            
            # Extract date
            date_match = re.search(
                r'(?:<time[^>]*datetime="([^"]+)"|<span[^>]*(?:date|time)[^>]*>(.*?)</span>)',
                block,
                re.DOTALL
            )
            if date_match:
                article['date'] = date_match.group(1) or date_match.group(2)
            
            # Extract summary
            summary_match = re.search(r'<p[^>]*>(.*?)</p>', block, re.DOTALL)
            if summary_match:
                article['summary'] = re.sub(r'<[^>]+>', '', summary_match.group(1)).strip()
            
            # Ensure we have at least a title or URL
            if article.get('title') or article.get('url'):
                article['id'] = i + 1
                article['source'] = 'iranmonitor.org'
                articles.append(article)
        
        return articles
    
    def extract_latest_news(self, html, limit=20):
        """Try to extract articles from a 'Latest News' or 'Recent' section."""
        # Look for latest news section
        latest_section = re.search(
            r'(?i)(?:latest\s+news|recent|breaking)[^<]*<[^>]+>(.*?)(?:</div>|</section>)',
            html,
            re.DOTALL
        )
        
        if latest_section:
            return self._extract_articles_with_regex(latest_section.group(1), limit)
        
        return []
    
    def fetch_articles(self, limit=20):
        """Fetch articles from iranmonitor.org."""
        timestamp = datetime.now(timezone.utc).isoformat()
        self.log(f"Starting IranMonitor fetch at {timestamp}")
        self.log(f"Limit: {limit}")
        
        # Fetch main page
        self.log(f"Fetching {self.SITE_URL}...")
        html, status_code = self.fetch_url(self.SITE_URL)
        
        if html is None:
            return {
                'status': 'error',
                'message': f'Failed to fetch main page. Status: {status_code}',
                'timestamp': timestamp,
                'source': self.SITE_URL
            }
        
        self.log("Main page fetched successfully")
        
        # Try to extract articles
        self.log("Extracting articles...")
        articles = self.extract_articles(html, limit)
        
        if not articles:
            self.log("No articles found with primary method. Trying latest news section...", 'warning')
            articles = self.extract_latest_news(html, limit)
        
        if not articles:
            self.log("No articles found. Trying alternative extraction...", 'warning')
            # Fallback: extract all links with text
            if BEAUTIFULSOUP_AVAILABLE:
                soup = BeautifulSoup(html, 'html.parser')
                links = soup.find_all('a', href=True, limit=limit)
                for i, link in enumerate(links):
                    href = link['href']
                    if href.startswith('/'):
                        href = f"{self.SITE_URL.rstrip('/')}{href}"
                    articles.append({
                        'id': i + 1,
                        'title': link.get_text(strip=True) or 'Untitled',
                        'url': href,
                        'source': self.SITE_URL
                    })
        
        self.log(f"Extracted {len(articles)} articles")
        
        return {
            'status': 'success',
            'timestamp': timestamp,
            'source': self.SITE_URL,
            'articles_count': len(articles),
            'articles': articles,
            'extracted_at': timestamp
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Fetch articles from iranmonitor.org',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 fetch_iranmonitor.py
  python3 fetch_iranmonitor.py --output articles.json
  python3 fetch_iranmonitor.py --limit 50 --format compact
  
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
        help='Output file path (e.g., articles.json)'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=20,
        help='Maximum number of articles to fetch (default: 20)'
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
        original_log = IranMonitorFetcher.log
        def silent_log(self, message, level='info'):
            if level == 'error':
                original_log(self, message, level)
        IranMonitorFetcher.log = silent_log
    
    fetcher = IranMonitorFetcher()
    result = fetcher.fetch_articles(limit=args.limit)
    
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
