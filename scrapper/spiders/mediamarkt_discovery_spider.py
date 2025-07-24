from .base_discovery_spider import BaseDiscoverySpider
import re
from urllib.parse import urljoin
from scrapy.http import Request, Response
import xml.etree.ElementTree as ET
from typing import Any, Optional, Generator


class MediaMarktDiscoverySpider(BaseDiscoverySpider):
    name = 'mediamarkt_discovery'
    allowed_domains = ['mediamarkt.hu']
    start_urls = ['https://www.mediamarkt.hu/']
    
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 2.0,
        'AUTOTHROTTLE_DEBUG': True,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'ROBOTSTXT_OBEY': True,  # For competitive intelligence
        'CONCURRENT_REQUESTS': 8,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
    }
    
    def __init__(self, mode: str = 'full', *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.mode = mode  # 'sitemap_only', 'category_only', 'full'
        self.discovered_products = set()
        self.discovered_categories = set()
        self.product_urls = []
        self.discovery_methods = {
            'sitemap': 0,
            'category_traversal': 0,
            'pattern_recognition': 0,
            'search_discovery': 0
        }
        
    def start_requests(self) -> Generator[Request, None, None]:
        """Start with discovery approaches based on mode"""
        if self.mode in ['sitemap_only', 'full']:
            # Primary: Sitemap discovery (fastest and most comprehensive)
            yield Request(
                url='https://www.mediamarkt.hu/sitemaps/sitemap-index.xml',
                callback=self.parse_sitemap_index,
                errback=self.sitemap_error,
                meta={'discovery_method': 'sitemap'},
                priority=100  # Highest priority
            )
        
        if self.mode in ['category_only', 'full']:
            # Secondary: Category traversal (backup method)
            yield Request(
                url='https://www.mediamarkt.hu/',
                callback=self.parse_homepage,
                meta={'discovery_method': 'category_traversal'},
                priority=50
            )
        

    def sitemap_error(self, failure: Any) -> None:
        """Handle sitemap access errors"""
        self.logger.warning(f"Sitemap access failed: {failure.value}")
        
    def parse_sitemap_index(self, response: Response) -> Generator[Request, None, None]:
        """Parse sitemap index to find product sitemaps"""
        try:
            root = ET.fromstring(response.body)
            
            # Look for product-related sitemaps
            for sitemap in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                loc = sitemap.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc is not None:
                    sitemap_url = loc.text
                    
                    # Prioritize product detail sitemaps (these contain the actual product URLs)
                    if 'productdetailspages' in sitemap_url.lower():
                        self.logger.info(f"Found product details sitemap: {sitemap_url}")
                        yield Request(
                            url=sitemap_url,
                            callback=self.parse_product_sitemap,
                            meta={'discovery_method': 'sitemap', 'sitemap_type': 'product_details'},
                            priority=90
                        )
                    # Also process product list pages (category pages) for fallback
                    elif 'productlistpages' in sitemap_url.lower() and self.mode == 'full':
                        self.logger.info(f"Found product list sitemap: {sitemap_url}")
                        yield Request(
                            url=sitemap_url,
                            callback=self.parse_sitemap,
                            meta={'discovery_method': 'sitemap', 'sitemap_type': 'product_lists'},
                            priority=60
                        )
        except ET.ParseError as e:
            self.logger.error(f"Error parsing sitemap index: {e}")

    def parse_sitemap(self, response: Response) -> Generator[Request, None, None]:
        """Parse individual sitemap files (for category pages)"""
        try:
            root = ET.fromstring(response.body)
            
            for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                loc = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc is not None:
                    url = loc.text     
                    
                    # Only process category URLs from generic sitemaps
                    if self.is_category_url(url):
                        if url not in self.discovered_categories:
                            self.discovered_categories.add(url)
                            yield Request(
                                url=url,
                                callback=self.parse_category,
                                meta={'discovery_method': 'sitemap'},
                                priority=40
                            )
        except ET.ParseError as e:
            self.logger.error(f"Error parsing sitemap: {e}")

    def parse_product_sitemap(self, response: Response) -> None:
        """Parse dedicated product sitemaps - CORE URL COLLECTION"""
        sitemap_type = response.meta.get('sitemap_type', 'unknown')
        self.logger.info(f"Processing {sitemap_type} sitemap: {response.url}")
        
        try:
            root = ET.fromstring(response.body)
            url_count = 0
            
            for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                loc = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc is not None:
                    url = loc.text
                    
                    if self.is_product_url(url) and url not in self.discovered_products:
                        self.discovered_products.add(url)
                        self.discovery_methods['sitemap'] += 1
                        url_count += 1
                        
                        # Extract lastmod if available for freshness tracking
                        lastmod_elem = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
                        lastmod = lastmod_elem.text if lastmod_elem is not None else None
                        
                        # Store URL with metadata (NO REQUESTS TO PRODUCT PAGES)
                        product_url_data = {
                            'url': url,
                            'discovery_method': 'sitemap',
                            'sitemap_type': sitemap_type,
                            'lastmod': lastmod,
                            'discovered_at': self.get_timestamp()
                        }
                        
                        self.product_urls.append(product_url_data)
                        
                        # Log progress every 500 products
                        if len(self.discovered_products) % 500 == 0:
                            self.logger.info(f"Discovered {len(self.discovered_products)} product URLs so far...")
            
            self.logger.info(f"Extracted {url_count} product URLs from {response.url}")
                            
        except ET.ParseError as e:
            self.logger.error(f"Error parsing product sitemap {response.url}: {e}")

    def parse_homepage(self, response: Response) -> Generator[Request, None, None]:
        """Parse homepage to discover category structure"""
        # Extract navigation menu categories
        category_links = response.css('a[href*="/category/"]::attr(href)').getall()
        category_links.extend(response.css('a[href*="/hu/category/"]::attr(href)').getall())
        
        for link in category_links:
            full_url = urljoin(response.url, link)
            if full_url not in self.discovered_categories and self.is_category_url(full_url):
                self.discovered_categories.add(full_url)
                yield Request(
                    url=full_url,
                    callback=self.parse_category,
                    meta={'discovery_method': 'category_traversal'},
                    priority=30
                )
        
        # Look for direct product links on homepage (collect URLs only)
        product_links = response.css('a[href*="/product/"]::attr(href)').getall()
        for link in product_links:
            full_url = urljoin(response.url, link)
            if self.is_product_url(full_url) and full_url not in self.discovered_products:
                self.discovered_products.add(full_url)
                self.discovery_methods['category_traversal'] += 1
                
                # Store URL without making request
                product_url_data = {
                    'url': full_url,
                    'discovery_method': 'category_traversal',
                    'source_page': response.url,
                    'discovered_at': self.get_timestamp()
                }
                self.product_urls.append(product_url_data)

    def parse_category(self, response: Response) -> Generator[Request, None, None]:
        """Parse category pages to discover product URLs and subcategories"""
        # Extract product links
        product_selectors = [
            'a[href*="/product/"]::attr(href)',
            'a[href*="/hu/product/"]::attr(href)',
            '.product-tile a::attr(href)',
            '.product-item a::attr(href)',
            '.product-card a::attr(href)',
            '[data-test="product-link"]::attr(href)',
        ]
        
        products_found = 0
        for selector in product_selectors:
            product_links = response.css(selector).getall()
            for link in product_links:
                full_url = urljoin(response.url, link)
                if self.is_product_url(full_url) and full_url not in self.discovered_products:
                    self.discovered_products.add(full_url)
                    self.discovery_methods['category_traversal'] += 1
                    products_found += 1
                    
                    # Store URL without making request
                    product_url_data = {
                        'url': full_url,
                        'discovery_method': 'category_traversal',
                        'source_page': response.url,
                        'category': self.extract_category_name(response.url),
                        'discovered_at': self.get_timestamp()
                    }
                    self.product_urls.append(product_url_data)
        
        self.logger.debug(f"Found {products_found} products on category page: {response.url}")
        
        # Extract subcategory links (for deeper discovery)
        subcategory_links = response.css('a[href*="/category/"]::attr(href)').getall()
        subcategory_links.extend(response.css('a[href*="/hu/category/"]::attr(href)').getall())
        
        for link in subcategory_links:
            full_url = urljoin(response.url, link)
            if full_url not in self.discovered_categories and self.is_category_url(full_url):
                self.discovered_categories.add(full_url)
                yield Request(
                    url=full_url,
                    callback=self.parse_category,
                    meta={'discovery_method': 'category_traversal'},
                    priority=20
                )
        
        # Handle pagination (limit depth to avoid infinite loops)
        current_depth = response.meta.get('pagination_depth', 0)
        if current_depth < 10:  # Max 10 pages per category
            pagination_selectors = [
                '.pagination a[href*="page="]::attr(href)',
                'a[href*="page="]::attr(href)',
                '.next-page::attr(href)',
                '[data-test="pagination-next"]::attr(href)',
            ]
            
            for selector in pagination_selectors:
                next_page_links = response.css(selector).getall()
                for link in next_page_links[:3]:  # Limit pagination links
                    full_url = urljoin(response.url, link)
                    if full_url != response.url:  # Avoid same page
                        yield Request(
                            url=full_url,
                            callback=self.parse_category,
                            meta={
                                'discovery_method': 'category_traversal',
                                'pagination_depth': current_depth + 1
                            },
                            priority=10
                        )

    def extract_category_name(self, url: str) -> Optional[str]:
        """Extract category name from URL"""
        match = re.search(r'/category/([^-]+)', url)
        if match:
            return match.group(1).replace('_', ' ').replace('-', ' ').title()
        return None

    def get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

    def is_product_url(self, url: str) -> bool:
        """Check if URL is a product page"""
        product_patterns = [
            r'/hu/product/',
            r'/product/',
        ]
        return any(re.search(pattern, url) for pattern in product_patterns)

    def is_category_url(self, url: str) -> bool:
        """Check if URL is a category page"""
        category_patterns = [
            r'/hu/category/',
            r'/category/',
        ]
        return any(re.search(pattern, url) for pattern in category_patterns)
