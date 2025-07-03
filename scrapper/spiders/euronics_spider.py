"""
Spider for Euronics.hu, a Hungarian electronics retailer.
This spider extracts product information including prices and stock status.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
import re

import scrapy
from scrapy.http import Request, Response
from scrapy.exceptions import DropItem

from scrapper.items import ProductItem, StockAvailability

logger = logging.getLogger(__name__)

class EuronicsSpider(scrapy.Spider):
    name = 'euronics'
    allowed_domains = ['euronics.hu']
    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_DELAY': 1.5,
        'CONCURRENT_REQUESTS': 2,
        'COOKIES_ENABLED': True,
        'HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
        }
    }
    
    def __init__(self, urls=None, *args, **kwargs):
        super(EuronicsSpider, self).__init__(*args, **kwargs)
        self.start_urls = urls if urls else []
        if not self.start_urls:
            logger.error("No URLs provided to spider")
            raise ValueError("No URLs provided to spider")

    def safe_extract_price(self, text: str) -> Tuple[Optional[float], Optional[str]]:
        """Safely extract price from text, returns (numeric_price, raw_price)."""
        if not text:
            return None, None
        try:
            # Clean and normalize price text
            price_text = text.replace('/ db', '').strip()
            # Extract numbers, handling Hungarian format (spaces and non-breaking spaces as thousand separators)
            numeric_str = re.sub(r'[^\d]', '', price_text)
            if numeric_str:
                return float(numeric_str), price_text
        except Exception as e:
            logger.warning(f"Failed to parse price from '{text}': {str(e)}")
        return None, text

    def safe_extract_delivery_info(self, text: str) -> Tuple[Optional[str], Optional[float]]:
        """Safely extract delivery time and cost, returns (time, cost)."""
        if not text:
            return None, None
        
        delivery_time = None
        delivery_cost = None
        
        try:
            # Try to extract delivery time
            time_match = re.search(r'(\d+-\d+)\s*(?:munkanapon|napon)', text)
            if time_match:
                delivery_time = time_match.group(1)
        except Exception as e:
            logger.warning(f"Failed to parse delivery time from '{text}': {str(e)}")

        try:
            # Try to extract cost
            # First, normalize the text by replacing non-breaking spaces and other whitespace with regular spaces
            normalized_text = ' '.join(text.split())
            # Then extract the price
            cost_match = re.search(r'(\d+(?:\s+\d+)*)\s*Ft', normalized_text)
            if cost_match:
                # Remove all types of spaces from the matched number
                cost_str = re.sub(r'\s+', '', cost_match.group(1))
                delivery_cost = float(cost_str)
        except Exception as e:
            logger.warning(f"Failed to parse delivery cost from '{text}': {str(e)}")

        return delivery_time, delivery_cost

    def safe_extract_store_count(self, text: str) -> Optional[int]:
        """Safely extract store count from text."""
        if not text:
            return None
        try:
            # Normalize text by replacing all types of spaces with regular spaces
            normalized_text = ' '.join(text.split())
            match = re.search(r'(\d+)\s*áruházban', normalized_text)
            if match:
                return int(match.group(1))
        except Exception as e:
            logger.warning(f"Failed to parse store count from '{text}': {str(e)}")
        return None

    def start_requests(self):
        """Generate initial requests."""
        if not self.start_urls:
            logger.error("No URLs to process")
            return

        for url in self.start_urls:
            try:
                yield Request(
                    url=url,
                    callback=self.parse_product,
                    headers=self.custom_settings['HEADERS'],
                    meta={
                        'url': url,
                        'dont_redirect': False,
                        'max_redirects': 5,
                        'original_url': url
                    },
                    errback=self.handle_error,
                    dont_filter=True
                )
            except Exception as e:
                logger.error(f"Error generating request for {url}: {str(e)}", exc_info=True)
                yield ProductItem.create_empty(url=url, website='euronics.hu').mark_failure()

    def parse_stock_availability(self, response, item: ProductItem) -> None:
        """Parse stock availability information for all delivery methods."""
        try:
            stock_wrapper = response.css('.product__stock-wrapper')
            
            # Home delivery availability
            home_delivery = StockAvailability()
            home_delivery['delivery_method'] = 'HOME_DELIVERY'
            home_delivery_info = stock_wrapper.css('.product__stock-info-wrapper:contains("Házhozszállítással")')
            if home_delivery_info:
                status_indicator = home_delivery_info.css('.courier-services__item-display::attr(class)').get()
                home_delivery['status'] = 'IN_STOCK' if status_indicator and 'bg-success' in status_indicator else 'OUT_OF_STOCK'
                
                delivery_text = home_delivery_info.css('.d-flex div::text').get()
                if delivery_text:
                    time, cost = self.safe_extract_delivery_info(delivery_text)
                    if time:
                        home_delivery['delivery_time'] = f"{time} working days"
                    if cost:
                        home_delivery['delivery_cost'] = cost
                        home_delivery['delivery_cost_currency'] = 'HUF'
            item.add_stock_info(home_delivery)

            # Store pickup availability
            store_pickup = StockAvailability()
            store_pickup['delivery_method'] = 'STORE_PICKUP'
            store_info = stock_wrapper.css('.product__stock-info-wrapper:contains("Áruházi készletinformáció")')
            if store_info:
                status_indicator = store_info.css('.courier-services__item-display::attr(class)').get()
                store_pickup['status'] = 'IN_STOCK' if status_indicator and 'bg-success' in status_indicator else 'OUT_OF_STOCK'
                
                store_text = store_info.css('.product__stock-info span::text').get()
                store_count = self.safe_extract_store_count(store_text)
                if store_count:
                    store_pickup['store_count'] = store_count
                
                store_pickup['delivery_cost'] = 0
                store_pickup['delivery_cost_currency'] = 'HUF'
                store_pickup['delivery_time'] = 'immediate'
                store_pickup['additional_info'] = 'Free pickup from store'
            item.add_stock_info(store_pickup)

            # Parcel point availability
            parcel_point = StockAvailability()
            parcel_point['delivery_method'] = 'PARCEL_POINT'
            parcel_info = stock_wrapper.css('.product__stock-info-wrapper:contains("Csomagponton átvehető")')
            if parcel_info:
                status_indicator = parcel_info.css('.courier-services__item-display::attr(class)').get()
                parcel_point['status'] = 'IN_STOCK' if status_indicator and 'bg-success' in status_indicator else 'OUT_OF_STOCK'
                
                delivery_text = parcel_info.css('.d-flex div span::text').get()
                if delivery_text:
                    time, cost = self.safe_extract_delivery_info(delivery_text)
                    if time:
                        parcel_point['delivery_time'] = f"{time} days"
                    if cost:
                        parcel_point['delivery_cost'] = cost
                        parcel_point['delivery_cost_currency'] = 'HUF'
            item.add_stock_info(parcel_point)
            
        except Exception as e:
            logger.warning(f"Failed to parse stock availability info: {str(e)}")

    def parse_product(self, response):
        """Parse product page response."""
        url = response.meta.get('url', response.url)
        item = ProductItem.create_empty(url=url, website='euronics.hu')
        
        try:
            # Extract product name
            product_name = response.css('h1.product__title::text').get()
            if not product_name:
                product_name = response.css('title::text').get()
                if product_name and '|' in product_name:
                    product_name = product_name.split('|')[0].strip()
            item['product_name'] = product_name

            # Extract price
            price_elem = response.css('.price__content.price::text').get()
            if price_elem:
                numeric_price, raw_price = self.safe_extract_price(price_elem)
                if numeric_price:
                    item['price'] = numeric_price
                if raw_price:
                    item['raw_price'] = raw_price

            # Parse stock availability
            self.parse_stock_availability(response, item)

            # Extract specifications if available
            try:
                specs = {}
                for spec_row in response.css('.product-parameters__item'):
                    label = spec_row.css('.product-parameters__label::text').get()
                    value = spec_row.css('.product-parameters__value::text').get()
                    if label and value:
                        specs[label.strip()] = value.strip()
                if specs:
                    item.add_specs(specs)
            except Exception as e:
                logger.warning(f"Failed to parse specifications: {str(e)}")

            # Extract images
            try:
                images = response.css('.product-gallery__image::attr(src)').getall()
                if images:
                    item.add_images(images)
            except Exception as e:
                logger.warning(f"Failed to parse images: {str(e)}")

            return item.mark_success()
            
        except Exception as e:
            logger.error(f"Critical error parsing product from {url}: {str(e)}")
            return item.mark_failure()

    def handle_error(self, failure):
        """Handle request failures."""
        url = failure.request.meta.get('original_url', failure.request.url)
        
        if hasattr(failure.value, 'response') and failure.value.response:
            response = failure.value.response
            logger.error(f"Request failed for {url}: HTTP {response.status}")
        else:
            logger.error(f"Request failed for {url}")
            