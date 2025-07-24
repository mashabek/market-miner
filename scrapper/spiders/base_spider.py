"""Base spider with Sentry integration."""

import logging
import json
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Generator
from urllib.parse import urlparse
import re

import scrapy
from scrapy.http.request import Request
from scrapy.http.response import Response
from scrapper.utils.sentry import add_breadcrumb, capture_error, monitor_errors
from scrapper.items import ProductItem

logger = logging.getLogger(__name__)

class BaseSpider(scrapy.Spider, ABC):
    """Base spider class with Sentry integration and common functionality."""
    
    @property
    @abstractmethod
    def allowed_domains(self) -> List[str]:
        """List of allowed domains for this spider. Must be implemented by subclass."""
        pass
    
    def __init__(self, urls=None, urls_file=None, *args, **kwargs):
        """
        Initialize spider with URLs either directly or from a file.
        
        Args:
            urls (str, optional): JSON array of URLs to scrape
            urls_file (str, optional): Path to file containing URLs (JSON array or one per line)
        """
        super().__init__(*args, **kwargs)
        # Handle URLs from file
        if urls_file:
            try:
                with open(urls_file, 'r', encoding='utf-8') as f:
                    try:
                        # Try to load as JSON array
                        self.start_urls = json.load(f)
                        if not isinstance(self.start_urls, list):
                            raise ValueError("JSON in urls_file must be a list of URLs")
                        logger.info(f"Loaded {len(self.start_urls)} URLs from JSON file: {urls_file}")
                    except json.JSONDecodeError:
                        # Fallback: treat as plain text, one URL per line
                        f.seek(0)
                        self.start_urls = [line.strip() for line in f if line.strip()]
                        logger.info(f"Loaded {len(self.start_urls)} URLs from text file: {urls_file}")
            except Exception as e:
                logger.error(f"Error loading URLs from file {urls_file}: {e}")
                raise
        # Handle URLs passed directly
        elif urls:
            try:
                if isinstance(urls, str):
                    # Try to parse as JSON array
                    self.start_urls = json.loads(urls)
                    if not isinstance(self.start_urls, list):
                        raise ValueError("URLs must be provided as a JSON array")
                    logger.info(f"Using {len(self.start_urls)} URLs from JSON array")
                elif isinstance(urls, list):
                    self.start_urls = urls
                    logger.info(f"Using {len(self.start_urls)} URLs passed directly")
                else:
                    raise ValueError("urls must be a JSON array string or list of strings")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse URLs as JSON: {e}")
                raise ValueError("URLs must be provided as a valid JSON array")
        else:
            self.start_urls = []
            logger.warning("No URLs provided to spider")
        
        # Add spider info to Sentry
        add_breadcrumb(
            message=f"Spider {self.name} initialized",
            category="spider.lifecycle",
            data={
                "start_urls_count": len(self.start_urls),
                "urls_source": "file" if urls_file else "direct" if urls else "none"
            }
        )

    def start_requests(self) -> Generator[Request, None, None]:
        """Generate initial requests with proper URL handling."""
        if not self.start_urls:
            logger.error("No URLs provided to spider")
            raise ValueError("No URLs provided to spider")

        for url in self.start_urls:
            try:
                # Clean up malformed URLs
                url = url.strip('"\'')  # Remove quotes
                url = re.sub(r'https?://(https?://)', r'\1', url)  # Fix double protocols
                
                # Ensure URL has scheme
                if not url.startswith(('http://', 'https://')):
                    url = f'https://{url}'
                
                # Validate URL
                parsed = urlparse(url)
                if not parsed.netloc:
                    logger.warning(f"Skipping URL with no domain: {url}")
                    continue
                    
                # Check if any allowed domain matches the URL's domain or its parent domains
                domain_parts = parsed.netloc.split('.')
                valid_domain = False
                for i in range(len(domain_parts) - 1):
                    check_domain = '.'.join(domain_parts[i:])
                    if check_domain in self.allowed_domains:
                        valid_domain = True
                        break
                        
                if not valid_domain:
                    logger.warning(f"Skipping URL with invalid domain: {url}")
                    continue
                
                add_breadcrumb(
                    message="Processing URL",
                    category="spider.request",
                    data={"url": url}
                )
                
                yield Request(
                    url=url,
                    callback=self.parse_product,
                    headers=self._get_headers(),
                    meta={
                        'url': url,
                        'dont_redirect': False,
                        'handle_httpstatus_list': [403, 503],
                        'download_timeout': 30,
                    },
                    errback=self.handle_error,
                    dont_filter=True
                )
            except Exception as e:
                capture_error(e, {"url": url})
                logger.error(f"Failed to create request for URL {url}: {e}")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers. Override in subclass if needed."""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    @monitor_errors
    def parse_product(self, response: Response) -> ProductItem:
        """Parse product page. Must be implemented by subclass."""
        raise NotImplementedError

    def handle_error(self, failure) -> ProductItem:
        """Handle request failures with Sentry integration."""
        url = failure.request.meta.get('url', failure.request.url)
        
        error_data = {
            "url": url,
            "spider": self.name,
            "error_type": failure.type.__name__
        }
        
        if hasattr(failure.value, 'response') and failure.value.response:
            response = failure.value.response
            error_data["status_code"] = response.status
            logger.error(f"HTTP {response.status} : Request failed for {url}.")
        else:
            logger.error(f"Request failed for {url}")
        
        capture_error(failure.value, error_data)
        return self.create_failed_item(url)

    def create_failed_item(self, url: str) -> ProductItem:
        """Create a failed product item."""
        return ProductItem.create_empty(url=url, website=self.allowed_domains[0]).mark_failure()

    def closed(self, reason):
        """Called when spider is closed."""
        add_breadcrumb(
            message=f"Spider {self.name} closed",
            category="spider.lifecycle",
            data={"reason": reason}
        ) 