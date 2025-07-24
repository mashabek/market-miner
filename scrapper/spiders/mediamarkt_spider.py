"""
Scraper for MediaMarkt.hu, a Hungarian electronics retailer.
This scraper extracts product information including price, availability, and specifications.
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

# Set up logger for this module
logger = logging.getLogger(__name__)

class MediaMarktSpider(BaseSpider):
    @property
    def allowed_domains(self) -> List[str]:
        """List of allowed domains for this spider."""
        return ['www.mediamarkt.hu', 'mediamarkt.hu', 'www.mediamarkt.hu/hu']

    name = 'mediamarkt'
    custom_settings = {
        'ROBOTSTXT_OBEY': True,
        'DOWNLOAD_DELAY': 0.01,
        'CONCURRENT_REQUESTS': 26,
        'COOKIES_ENABLED': True,
        'RETRY_TIMES': 5,
        'RETRY_HTTP_CODES': [403, 429, 500, 502, 503, 504, 408],
        'DOWNLOAD_TIMEOUT': 60,
    }

    def _get_headers(self):
        """Override base headers with MediaMarkt specific ones"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'TE': 'Trailers',
        }

    def parse_product(self, response: Response) -> ProductItem:
        """Parse product page and extract information"""
        url = response.meta.get('url', response.url)
        try:
            # Create empty product item
            item = ProductItem.create_empty(url=url, website='mediamarkt.hu')

            # Extract product name
            product_name = response.css('div[data-test="mms-select-details-header"] h1::text').get()
            if not product_name:
                return item.mark_failure()
            item['product_name'] = product_name.strip()

            # Extract price
            price_whole = response.css('span[data-test="branded-price-whole-value"]::text').get()
            price_decimal = response.css('span[data-test="branded-price-decimal-value"]::text').get()
            price_currency = response.css('span[data-test="branded-price-currency"]::text').get()

            raw_price = f"{price_whole or ''}{price_decimal or ''} {price_currency or ''}".strip()
            item['raw_price'] = raw_price

            # Clean and extract numeric price and currency
            if raw_price:
                # Remove non-breaking spaces and other special characters
                clean_price = raw_price.replace('\xa0', ' ').replace('–', '').replace(',', '').strip()
                # Extract numeric part
                price_match = re.search(r'(\d+(?:\s*\d+)*)\s*Ft', clean_price)
                if price_match:
                    numeric_price = price_match.group(1).replace(' ', '')
                    item['price'] = float(numeric_price)
                    item['currency'] = 'HUF'  # ISO 4217 currency code for Hungarian Forint

            # Extract stock status - handle both available and not available
            stock_info = self._extract_stock_status(response)
            if stock_info:
                item.add_stock_info(stock_info)

            # Extract product ID from URL or page
            product_id = self._extract_product_id(response)
            if product_id:
                item['product_id'] = product_id

            # Extract specifications
            specs = self._extract_specifications(response)
            if specs:
                item.add_specs(specs)

            # Extract image URLs
            images = self._extract_images(response)
            if images:
                item.add_images(images)

            # Extract brand
            brand = self._extract_brand(response)
            if brand:
                item['specs']['brand'] = brand

            return item.mark_success()

        except Exception as e:
            logger.error(f"Error parsing product from {url}: {str(e)}")
            return ProductItem.create_empty(url=url, website='mediamarkt.hu').mark_failure()

    def _extract_product_id(self, response) -> Optional[str]:
        """Extract product ID from the page."""
        # Try to get from article number
        article_number = response.css('p[data-test="pdp-article-number"]::text').get()
        if article_number:
            # Extract just the number part
            id_match = re.search(r'(\d+)', article_number)
            if id_match:
                return id_match.group(1)
        
        # Try to get from URL
        url_match = re.search(r'-(\d+)\.html', response.url)
        if url_match:
            return url_match.group(1)
        return None

    def _extract_stock_status(self, response) -> Optional[StockAvailability]:
        """Extract stock status for all availability states."""
        
        # Check for AVAILABLE delivery
        available_delivery = response.css('div[data-test="mms-cofr-delivery_AVAILABLE"] p::text').get()
        if available_delivery:
            return self._create_delivery_stock_info(response, available_delivery, 'AVAILABLE')
        
        # Check for PARTIALLY_AVAILABLE delivery (like this product)
        partially_available = response.css('div[data-test="mms-cofr-delivery_PARTIALLY_AVAILABLE"] p::text').get()
        if partially_available:
            stock_info = StockAvailability()
            stock_info['status'] = partially_available.strip()
            stock_info['delivery_method'] = 'HOME_DELIVERY'
            
            # Extract delivery cost for partially available
            delivery_cost = response.css('div[data-test="mms-cofr-delivery_PARTIALLY_AVAILABLE"] p:last-child::text').get()
            if delivery_cost and 'Ft' in delivery_cost:
                cost_match = re.search(r'(\d+(?:\s?\d+)*)', delivery_cost)
                if cost_match:
                    cost_str = cost_match.group(1).replace(' ', '').replace('\xa0', '')
                    stock_info['delivery_cost'] = float(cost_str)
                    stock_info['delivery_cost_currency'] = 'HUF'
            
            return stock_info
        
        # Check for NOT AVAILABLE delivery (out of stock)
        not_available_delivery = response.css('div[data-test="mms-cofr-delivery_NOT_AVAILABLE"] p::text').get()
        if not_available_delivery:
            stock_info = StockAvailability()
            stock_info['status'] = not_available_delivery.strip()
            stock_info['delivery_method'] = 'HOME_DELIVERY'
            return stock_info
        
        # Check for pickup availability states
        pickup_states = [
            'mms-cofr-pickup_AVAILABLE',
            'mms-cofr-pickup_PARTIALLY_AVAILABLE', 
            'mms-cofr-pickup_NOT_AVAILABLE',
            'mms-cofr-pickup_NO_STORE_SELECTED'
        ]
        
        for state in pickup_states:
            pickup_text = response.css(f'div[data-test="{state}"] p::text').get()
            if pickup_text:
                stock_info = StockAvailability()
                stock_info['status'] = pickup_text.strip()
                stock_info['delivery_method'] = 'STORE_PICKUP'
                return stock_info
        
        # Fallback: look for general validation message
        validation_message = response.css('div[data-test="validationMessage"] p::text').get()
        if validation_message:
            stock_info = StockAvailability()
            stock_info['status'] = validation_message.strip()
            stock_info['delivery_method'] = 'UNKNOWN'
            return stock_info
        
        return None

    def _create_delivery_stock_info(self, response, status_text, availability_type) -> StockAvailability:
        """Helper to create delivery stock info with cost extraction."""
        stock_info = StockAvailability()
        stock_info['status'] = status_text.strip()
        stock_info['delivery_method'] = 'HOME_DELIVERY'
        
        # Extract delivery time if available
        delivery_time = response.css(f'div[data-test="mms-cofr-delivery_{availability_type}"] span::text').get()
        if delivery_time:
            stock_info['delivery_time'] = delivery_time.strip()
        
        # Extract delivery cost
        delivery_cost_text = response.css(f'div[data-test="mms-cofr-delivery_{availability_type}"] p:contains("HUF")::text').get()
        if delivery_cost_text:
            cost_match = re.search(r'(\d+(?:\s?\d+)*)', delivery_cost_text)
            if cost_match:
                cost_str = cost_match.group(1).replace(' ', '').replace('\xa0', '')
                stock_info['delivery_cost'] = float(cost_str)
                stock_info['delivery_cost_currency'] = 'HUF'
        
        return stock_info

    def _extract_brand(self, response) -> Optional[str]:
        """Extract brand information."""
        # Try from brand link
        brand = response.css('a[href*="/brand/"] span::text').get()
        if brand:
            return brand.strip()
        
        # Try from manufacturer image alt text
        brand_alt = response.css('img[data-test="manufacturer-image"]::attr(alt)').get()
        if brand_alt:
            return brand_alt.strip()
        
        return None

    def _extract_specifications(self, response) -> Dict[str, str]:
        """Extract product specifications from multiple sections."""
        specs = {}
        
        # Method 1: Extract from main specification tables
        spec_tables = response.css('table.sc-69ef002d-0')
        for table in spec_tables:
            # Get table header to categorize specs
            table_header = table.css('thead th p::text').get()
            category_prefix = f"{table_header.strip()}: " if table_header else ""
            
            # Extract rows from table body
            rows = table.css('tbody tr')
            for row in rows:
                cells = row.css('td')
                if len(cells) >= 2:
                    key_element = cells[0].css('p::text').get()
                    value_element = cells[1].css('p::text').get()
                    
                    if key_element and value_element:
                        key = key_element.strip()
                        value = value_element.strip()
                        # Add category prefix if available
                        full_key = f"{category_prefix}{key}" if category_prefix else key
                        specs[full_key] = value
        
        # Method 2: Extract from quick specs section (main features)
        quick_specs = response.css('div[data-test="mms-pdp-details-mainfeatures"] button')
        for spec_button in quick_specs:
            spans = spec_button.css('span.sc-be471825-5::text').getall()
            if len(spans) >= 2:
                key = spans[0].strip()
                value = spans[1].strip()
                specs[key] = value
        
        # Method 3: Extract from product variants (color, capacity, etc.)
        color_info = response.css('div[data-test="mms-pdp-variants-color"] span::text').get()
        if color_info and "Color:" in color_info:
            color = color_info.replace("Color:", "").strip()
            specs['Color'] = color
        
        # Extract capacity/storage options
        capacity_buttons = response.css('div.sc-992e5866-8 a span::text').getall()
        if capacity_buttons:
            # Find the selected/active capacity (you might need to adjust this logic)
            active_capacity = None
            for capacity in capacity_buttons:
                if capacity and ("GB" in capacity or "TB" in capacity):
                    active_capacity = capacity.strip()
                    break
            if active_capacity:
                specs['Storage Capacity'] = active_capacity
        
        # Method 4: Extract from energy efficiency section
        energy_class = response.css('div[data-test="cofr-energy-efficiency"] span::text').get()
        if energy_class:
            specs['Energy Efficiency Class'] = energy_class.strip()
        
        # Clean up specifications - remove empty values and duplicates
        cleaned_specs = {}
        for key, value in specs.items():
            if value and value.strip() and value.strip() != "-":
                cleaned_key = key.strip()
                cleaned_value = value.strip()
                # Remove HTML entities and clean up text
                cleaned_value = re.sub(r'&[a-zA-Z0-9#]+;', '', cleaned_value)
                cleaned_specs[cleaned_key] = cleaned_value
        
        return cleaned_specs

    def _extract_images(self, response) -> List[str]:
        """Extract product image URLs from gallery."""
        images = []
        base_url = response.urljoin('/')
        
        # Method 1: Extract from main product gallery
        gallery_images = response.css('div[data-test="mms-pdp-gallery"] img::attr(src)').getall()
        for img_url in gallery_images:
            if img_url and self._is_valid_image_url(img_url):
                # Convert relative URLs to absolute
                full_url = urljoin(base_url, img_url)
                # Get higher quality version by removing size constraints
                high_quality_url = self._get_high_quality_image_url(full_url)
                if high_quality_url not in images:
                    images.append(high_quality_url)
        
        # Method 2: Extract from thumbnail gallery
        thumbnail_images = response.css('button[data-test="mms-image-thumbnail"] img::attr(src)').getall()
        for img_url in thumbnail_images:
            if img_url and self._is_valid_image_url(img_url):
                full_url = urljoin(base_url, img_url)
                high_quality_url = self._get_high_quality_image_url(full_url)
                if high_quality_url not in images:
                    images.append(high_quality_url)
        
        # Method 3: Extract from color variant images
        variant_images = response.css('div.sc-992e5866-5 img::attr(src)').getall()
        for img_url in variant_images:
            if img_url and self._is_valid_image_url(img_url):
                full_url = urljoin(base_url, img_url)
                high_quality_url = self._get_high_quality_image_url(full_url)
                if high_quality_url not in images:
                    images.append(high_quality_url)
        
        # Remove duplicates while preserving order
        unique_images = []
        seen = set()
        for img in images:
            if img not in seen:
                seen.add(img)
                unique_images.append(img)
        
        return unique_images

    def _is_valid_image_url(self, url: str) -> bool:
        """Check if URL is a valid product image."""
        if not url:
            return False
        
        # Skip placeholder images, icons, and non-product images
        skip_patterns = [
            'playButton.png',
            'icon-',
            'logo',
            '/assets/skins/',
            'data:image',
            '.svg'
        ]
        
        for pattern in skip_patterns:
            if pattern in url:
                return False
        
        # Must be from MediaMarkt assets
        return 'assets.mmsrg.com' in url or 'mediamarkt' in url

    def _get_high_quality_image_url(self, url: str) -> str:
        """Convert image URL to highest quality version by removing all query parameters."""
        # Remove everything after '?' to strip all query parameters
        url = url.split('?', 1)[0]
        return url