#!/usr/bin/env python3
"""
fetch_pressreader.py
Fetches news articles from PressReader.com

Usage:
    python3 fetch_pressreader.py [--query "search term"] [--output FILE.json]
    python3 fetch_pressreader.py --query "Iran" --limit 30
    python3 fetch_pressreader.py --limit 50 --format compact

Requirements: Python 3.x with requests and beautifulsoup4 (optional)
Works in: Cloud VMs, AI chat apps (Gemini, ChatGPT, etc.)

Description:
    This script searches PressReader for news articles. PressReader provides
    a web interface with free access to many newspapers. This script extracts
    article metadata, titles, publication names, and URLs.

Features:
    - Rate limiting detection and retry
    - Error handling with graceful degradation
    - Clean JSON output
    - Search functionality
"""

import sys
import os
import json
import time
import re
import argparse
from datetime import datetime, timezone
from urllib.parse import quote, urlencode

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


class PressReaderFetcher:
    """Fetches articles from PressReader.com."""
    
    BASE_URL = "https://www.pressreader.com"
    SEARCH_URL = "https://www.pressreader.com/search"
    USER_AGENT = ('Mozilla/5.0 (compatible; PressReaderFetcher/1.0; ' 
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
                'Accept-Language': 'en-US,en;q=0.9',
                'X-Requested-With': 'XMLHttpRequest'
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
            'Accept-Language': 'en-US,en;q=0.9',
            'X-Requested-With': 'XMLHttpRequest'
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
    
    def search(self, query=None, page=1, limit=20):
        """Search PressReader for articles."""
        if query:
            self.log(f"Searching for: {query}")
            search_url = f"{self.SEARCH_URL}?query={quote(query)}&page={page}"
        else:
            self.log("Fetching latest from catalog")
            search_url = f"{self.BASE_URL}/catalog"
        
        html, status_code = self.fetch_url(search_url)
        
        if html is None:
            self.log(f"Failed to fetch search results. Status: {status_code}", 'error')
            return []
        
        articles = self.extract_articles(html, limit)
        self.log(f"Found {len(articles)} articles")
        
        return articles
    
    def extract_articles(self, html, limit):
        """Extract articles from HTML."""
        articles = []
        
        if BEAUTIFULSOUP_AVAILABLE:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try to find article containers
            article_containers = soup.find_all(['article', 'div'], 
                class_=re.compile('article|post|card|publication|news-item'), 
                limit=limit)
            
            if not article_containers:
                # Try to find any article-like structure
                article_containers = soup.find_all(['article', 'div'], limit=limit * 2)
            
            for i, container in enumerate(article_containers[:limit]):
                article = self._extract_article_from_container(container, i + 1)
                if article:
                    articles.append(article)
        else:
            # Fallback to regex extraction
            articles = self._extract_articles_with_regex(html, limit)
        
        return articles
    
    def _extract_article_from_container(self, container, article_id):
        """Extract article data from a BeautifulSoup container."""
        article = {}
        
        # Extract title
        title_elem = container.find(['h1', 'h2', 'h3', 'h4'])
        if title_elem:
            article['title'] = title_elem.get_text(strip=True)
        
        # Extract URL
        link_elem = container.find('a', href=True)
        if link_elem:
            href = link_elem['href']
            if href.startswith('/'):
                href = f"{self.BASE_URL.rstrip('/')}{href}"
            article['url'] = href
        
        # Extract publication name
        publication_elem = container.find(['span', 'div', 'p'], 
            class_=re.compile('publication|source|newspaper|magazine'))
        if publication_elem:
            article['publication'] = publication_elem.get_text(strip=True)
        else:
            # Try to find publication from title or other elements
            title_text = container.get_text().lower()
            # Common newspaper names
            newspaper_patterns = [
                r'\btimes\b', r'\bherald\b', r'\btribune\b', r'\bpost\b',
                r'\bdaily\b', r'\bnews\b', r'\bjournal\b', r'\bguardian\b'
            ]
            for pattern in newspaper_patterns:
                if re.search(pattern, title_text):
                    article['publication'] = re.search(pattern, title_text, re.IGNORECASE).group()
                    break
        
        # Extract date
        date_elem = container.find(['time', 'span', 'div'], 
            class_=re.compile('date|time|timestamp|published'))
        if date_elem:
            article['date'] = date_elem.get('datetime', date_elem.get_text(strip=True))
        
        # Extract snippet/description
        snippet_elem = container.find(['p', 'div'], 
            class_=re.compile('snippet|description|excerpt|summary'))
        if snippet_elem:
            article['snippet'] = snippet_elem.get_text(strip=True)
        
        # Ensure we have at least a title or URL
        if article.get('title') or article.get('url'):
            article['id'] = article_id
            article['source'] = 'pressreader.com'
            article['extracted_at'] = datetime.now(timezone.utc).isoformat()
            return article
        
        return None
    
    def _extract_articles_with_regex(self, html, limit):
        """Extract articles using regex patterns."""
        articles = []
        
        # Pattern to find article blocks
        article_blocks = re.findall(
            r'(?:<article[^>]*>|<div[^>]*(?:article|post|card|publication)[^>]*>)(.*?)(?:</article>|</div>)',
            html,
            re.DOTALL
        )
        
        for i, block in enumerate(article_blocks[:limit]):
            article = {}
            
            # Extract title
            title_match = re.search(r'<(?:h1|h2|h3|h4)[^>]*>(.*?)</\1>', block, re.DOTALL)
            if title_match:
                article['title'] = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            
            # Extract URL
            url_match = re.search(r'<a\s+[^>]*href="([^"]+)"[^>]*>', block)
            if url_match:
                url = url_match.group(1)
                if url.startswith('/'):
                    url = f"{self.BASE_URL.rstrip('/')}{url}"
                elif not url.startswith(('http://', 'https://')):
                    url = f"{self.BASE_URL.rstrip('/')}/{url.lstrip('/')}"
                article['url'] = url
            
            # Extract publication
            pub_match = re.search(
                r'(?:<[^>]+(?:publication|source|newspaper|magazine)[^>]*>)(.*?)</[^>]+>',
                block,
                re.DOTALL
            )
            if pub_match:
                article['publication'] = re.sub(r'<[^>]+>', '', pub_match.group(1)).strip()
            
            # Extract date
            date_match = re.search(
                r'(?:<[^>]+(?:date|time|timestamp)[^>]*>)(.*?)</[^>]+>',
                block,
                re.DOTALL
            )
            if date_match:
                article['date'] = re.sub(r'<[^>]+>', '', date_match.group(1)).strip()
            
            # Extract snippet
            snippet_match = re.search(r'<p[^>]*>(.*?)</p>', block, re.DOTALL)
            if snippet_match:
                article['snippet'] = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()
            
            # Ensure we have at least a title or URL
            if article.get('title') or article.get('url'):
                article['id'] = i + 1
                article['source'] = 'pressreader.com'
                article['extracted_at'] = datetime.now(timezone.utc).isoformat()
                articles.append(article)
        
        return articles
    
    def fetch_catalog(self, limit=20):
        """Fetch latest publications from catalog."""
        self.log("Fetching latest from catalog...")
        
        html, status_code = self.fetch_url(f"{self.BASE_URL}/catalog")
        
        if html is None:
            self.log(f"Failed to fetch catalog. Status: {status_code}", 'error')
            return []
        
        articles = []
        
        if BEAUTIFULSOUP_AVAILABLE:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find publication links
            links = soup.find_all('a', href=re.compile('/catalog/'), limit=limit)
            
            for i, link in enumerate(links):
                href = link['href']
                if href.startswith('/'):
                    full_url = f"{self.BASE_URL.rstrip('/')}{href}"
                else:
                    full_url = href
                
                articles.append({
                    'id': i + 1,
                    'title': link.get_text(strip=True) or 'Untitled',
                    'url': full_url,
                    'source': 'pressreader.com/catalog',
                    'extracted_at': datetime.now(timezone.utc).isoformat()
                })
        else:
            # Regex fallback
            link_matches = re.findall(
                r'<a\s+[^>]*href="(/catalog/[^"]+)"[^>]*>([^<]+)</a>',
                html
            )
            
            for i, (href, title) in enumerate(link_matches[:limit]):
                full_url = f"{self.BASE_URL.rstrip('/')}{href}"
                
                articles.append({
                    'id': i + 1,
                    'title': title.strip() or 'Untitled',
                    'url': full_url,
                    'source': 'pressreader.com/catalog',
                    'extracted_at': datetime.now(timezone.utc).isoformat()
                })
        
        return articles
    
    def fetch_all(self, query=None, limit=20):
        """Fetch articles from PressReader."""
        timestamp = datetime.now(timezone.utc).isoformat()
        self.log(f"Starting PressReader fetch at {timestamp}")
        self.log(f"Query: {query or 'latest'}")
        self.log(f"Limit: {limit}")
        
        articles = []
        
        if query:
            articles = self.search(query, page=1, limit=limit)
        else:
            # Get from catalog
            articles = self.fetch_catalog(limit)
        
        self.log(f"Total articles: {len(articles)}")
        
        return {
            'status': 'success',
            'timestamp': timestamp,
            'source': 'pressreader.com',
            'query': query or 'latest',
            'articles_count': len(articles),
            'articles': articles,
            'extracted_at': timestamp
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Fetch articles from PressReader.com',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 fetch_pressreader.py
  python3 fetch_pressreader.py --query "Iran"
  python3 fetch_pressreader.py --query "Ukraine" --limit 30
  python3 fetch_pressreader.py --output pressreader.json --format compact
  
Requirements:
  - Python 3.x
  - requests library (recommended)
  - beautifulsoup4 library (optional, for better extraction)
  
Install requirements:
  pip install requests beautifulsoup4
        """
    )
    parser.add_argument(
        '--query', '-q',
        type=str,
        default=None,
        help='Search query (optional, fetches latest if not provided)'
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
        '--quiet',
        action='store_true',
        help='Suppress log output, only show results'
    )
    
    args = parser.parse_args()
    
    # Suppress logging if quiet mode
    if args.quiet:
        original_log = PressReaderFetcher.log
        def silent_log(self, message, level='info'):
            if level == 'error':
                original_log(self, message, level)
        PressReaderFetcher.log = silent_log
    
    fetcher = PressReaderFetcher()
    result = fetcher.fetch_all(
        query=args.query,
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
