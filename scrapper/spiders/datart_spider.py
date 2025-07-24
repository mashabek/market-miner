"""
Spider for Datart.cz, a Czech electronics retailer website.
This spider extracts product information including price, availability, and specifications.
"""

import re
import logging
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, urljoin
from scrapy.http.request import Request
from scrapy.http.response import Response
from scrapy.exceptions import DropItem
from scrapper.items import ProductItem, StockAvailability
from scrapper.spiders.base_spider import BaseSpider
from scrapper.utils.sentry import add_breadcrumb, monitor_errors

logger = logging.getLogger(__name__)

class DatartSpider(BaseSpider):
    @property
    def allowed_domains(self) -> List[str]:
        """List of allowed domains for this spider."""
        return ['www.datart.cz', 'datart.cz']
    
    name = 'datart'
    custom_settings = {
        'ROBOTSTXT_OBEY': True,
        'DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS': 1,
        'COOKIES_ENABLED': True,
        'RETRY_TIMES': 5,
        'RETRY_HTTP_CODES': [403, 429, 500, 502, 503, 504, 408],
        'DOWNLOAD_TIMEOUT': 60,
    }

    def _get_headers(self) -> Dict[str, str]:
        """Get Datart-specific headers."""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'cs-CZ,cs;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    @monitor_errors
    def parse_product(self, response: Response) -> ProductItem:
        """Parse product page response."""
        url = response.meta.get('url', response.url)
        
        try:
            # Create empty product item
            item = ProductItem.create_empty(url=url, website='datart.cz')
            
            # Extract product name - Updated selector
            product_name = response.css('h1.product-detail-title::text').get()
            if not product_name:
                # Try alternative selector
                product_name = response.css('h1[data-match]::text').get()
            
            if not product_name:
                add_breadcrumb(
                    message="Failed to extract product name",
                    category="spider.extraction",
                    level="error",
                    data={"url": url}
                )
                return item.mark_failure()
            
            item['product_name'] = product_name.strip()
            add_breadcrumb(
                message="Extracted product name",
                category="spider.extraction",
                data={"product_name": item['product_name']}
            )
            
            # Extract price - Updated selector and logic
            price_element = response.css('div.price-wrap .actual::text').get()
            if not price_element:
                # Try alternative selector
                price_element = response.css('div.product-price-main .actual::text').get()
            
            if price_element:
                item['raw_price'] = price_element.strip()
                # Extract numerical price - handle Czech format with non-breaking spaces
                price_match = re.search(r'(\d+(?:[\s\xa0]\d+)*)', price_element)
                if price_match:
                    price_str = price_match.group(1).replace(' ', '').replace('\xa0', '')
                    try:
                        item['price'] = float(price_str)
                        item['currency'] = 'CZK'  # ISO 4217 currency code for Czech Koruna
                        add_breadcrumb(
                            message="Extracted price",
                            category="spider.extraction",
                            data={"price": item['price'], "raw_price": item['raw_price']}
                        )
                    except ValueError:
                        logger.warning(f"Could not convert price '{price_str}' to float for {url}")
            
            # Extract stock status - Updated selector
            stock_text = response.css('span.product-availability-state::text').get()
            if not stock_text:
                # Try data-qa attribute selector
                stock_text = response.css('[data-qa="product-availability-state"]::text').get()
            
            if stock_text:
                stock_info = self._extract_stock_status(response, stock_text)
                if stock_info:
                    item.add_stock_info(stock_info)
                    add_breadcrumb(
                        message="Extracted stock info",
                        category="spider.extraction",
                        data={"stock_info": dict(stock_info)}
                    )
            
            # Extract product description - Updated selector
            description = response.css('div.product-detail-perex-box p::text').get()
            if not description:
                description = response.css('div.product-detail-perex .product-detail-perex-box p::text').get()
            
            if description:
                item.add_specs({'description': description.strip()})
            
            # Extract brand - Updated logic
            brand = self._extract_brand(response)
            if brand:
                item.add_specs({'brand': brand})
            
            # Extract images - Updated selectors
            images = self._extract_images(response)
            if images:
                item.add_images(images)
            
            # Extract product ID - Updated logic
            product_id = self._extract_product_id(response)
            if product_id:
                item['product_id'] = product_id

            # Extract additional specifications from parameters table
            specs = self._extract_specifications(response)
            if specs:
                item.add_specs(specs)

            # Extract rating information
            rating_info = self._extract_rating(response)
            if rating_info:
                item.add_specs(rating_info)

            return item.mark_success()
            
        except Exception as e:
            logger.error(f"Error parsing product from {url}: {str(e)}")
            return ProductItem.create_empty(url=url, website='datart.cz').mark_failure()

    def _extract_stock_status(self, response, stock_text: str) -> Optional[StockAvailability]:
        """Extract stock status information."""
        if not stock_text:
            return None
            
        stock_info = StockAvailability()
        stock_info['status'] = stock_text.strip()
        stock_info['delivery_method'] = 'HOME_DELIVERY'
        
        # Extract delivery time - Updated selector
        delivery_date = response.css('span.product-availability-estimated-delivery::text').get()
        if not delivery_date:
            delivery_date = response.css('[data-qa="product-availability-estimated-delivery"]::text').get()
        
        if delivery_date:
            stock_info['delivery_time'] = delivery_date.strip()
        
        # Extract delivery cost - Updated selector
        delivery_cost = response.css('div.delivery-price::text').get()
        if delivery_cost:
            cost_match = re.search(r'(\d+(?:[\s\xa0]\d+)*)', delivery_cost)
            if cost_match:
                cost_str = cost_match.group(1).replace(' ', '').replace('\xa0', '')
                try:
                    stock_info['delivery_cost'] = float(cost_str)
                    stock_info['delivery_cost_currency'] = 'CZK'
                except ValueError:
                    logger.warning(f"Could not convert delivery cost '{cost_str}' to float")
        
        return stock_info

    def _extract_product_id(self, response) -> Optional[str]:
        """Extract product ID from the page."""
        # Try to get from data-match attribute
        product_id = response.css('h1[data-match]::attr(data-match)').get()
        if product_id:
            return product_id.strip()
        
        # Try to get from data-ean attribute
        ean = response.css('h1[data-ean]::attr(data-ean)').get()
        if ean:
            return ean.strip()
        
        # Try to get from URL - Datart URLs typically have product IDs
        url_match = re.search(r'/(\w+)\.html', response.url)
        if url_match:
            return url_match.group(1)
        
        # Try to get from GTM data
        gtm_data = response.css('[data-gtm-data-product]::attr(data-gtm-data-product)').get()
        if gtm_data:
            import json
            try:
                data = json.loads(gtm_data.replace('&quot;', '"'))
                if 'item_id' in data:
                    return data['item_id']
            except:
                pass
        
        return None

    def _extract_brand(self, response) -> Optional[str]:
        """Extract brand information."""
        # Try from brand logo alt text
        brand = response.css('div.brand-logo img::attr(alt)').get()
        if brand:
            return brand.strip()
        
        # Try from brand logo title
        brand = response.css('div.brand-logo img::attr(title)').get()
        if brand:
            return brand.strip()
        
        # Try from GTM data
        gtm_data = response.css('[data-gtm-data-product]::attr(data-gtm-data-product)').get()
        if gtm_data:
            import json
            try:
                data = json.loads(gtm_data.replace('&quot;', '"'))
                if 'item_brand' in data:
                    return data['item_brand']
            except:
                pass
        
        # Try from specifications table
        brand_row = response.css('table.table-bordered tr:contains("Značky") td::text').get()
        if brand_row:
            return brand_row.strip()
        
        return None

    def _extract_images(self, response) -> List[str]:
        """Extract product image URLs."""
        images = []
        base_url = response.urljoin('/')
        
        # Extract main product image
        main_image = response.css('div.product-gallery-main img::attr(src)').get()
        if main_image and self._is_valid_image_url(main_image):
            full_url = urljoin(base_url, main_image)
            images.append(full_url)
        
        # Extract gallery images from slider
        gallery_images = response.css('div.product-gallery-slider img::attr(src)').getall()
        for img_url in gallery_images:
            if img_url and self._is_valid_image_url(img_url):
                full_url = urljoin(base_url, img_url)
                if full_url not in images:
                    images.append(full_url)
        
        # Extract high-res images from data-src attributes
        data_src_images = response.css('div.product-gallery [data-src]::attr(data-src)').getall()
        for img_url in data_src_images:
            if img_url and self._is_valid_image_url(img_url):
                full_url = urljoin(base_url, img_url)
                if full_url not in images:
                    images.append(full_url)
        
        return images

    def _extract_specifications(self, response) -> Dict[str, str]:
        """Extract product specifications from parameters table."""
        specs = {}
        
        # Extract from product property tables
        tables = response.css('div.product-property-table table.table-bordered')
        
        for table in tables:
            # Get table header to categorize specs
            header = table.css('thead th span::text').get()
            if header:
                header = header.strip()
            
            # Extract rows
            rows = table.css('tbody tr')
            for row in rows:
                key = row.css('th span::text').get()
                value = row.css('td::text').get()
                
                if key and value:
                    key = key.strip()
                    value = value.strip()
                    
                    # Prefix with header if available
                    if header and header != key:
                        key = f"{header}_{key}"
                    
                    specs[key] = value
        
        return specs

    def _extract_rating(self, response) -> Dict[str, Any]:
        """Extract rating and review information."""
        rating_info = {}
        
        # Extract overall rating
        rating_elem = response.css('div.rating-overview-link strong::text').get()
        if rating_elem:
            try:
                rating_info['rating'] = float(rating_elem.strip())
            except ValueError:
                pass
        
        # Extract number of reviews
        review_count = response.css('div.rating-overview-link span::text').get()
        if review_count:
            # Extract number from parentheses
            count_match = re.search(r'\((\d+)\)', review_count)
            if count_match:
                try:
                    rating_info['review_count'] = int(count_match.group(1))
                except ValueError:
                    pass
        
        return rating_info

    def _is_valid_image_url(self, url: str) -> bool:
        """Check if URL is a valid product image."""
        if not url:
            return False
        
        # Skip placeholder images, icons, and non-product images
        skip_patterns = [
            'placeholder',
            'icon-',
            'logo',
            'data:image',
            'no-image',
            'svg-icon'
        ]
        
        for pattern in skip_patterns:
            if pattern in url.lower():
                return False
        
        # Must be a valid image extension or from Datart foto directory
        return (any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']) 
                or '/foto/' in url 
                or 'datart.cz' in url)