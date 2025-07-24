"""
Spider for Pilulka.cz, a Czech pharmacy website.
This spider extracts product information including price, availability, and specifications.
"""

import re
import logging
from datetime import datetime

import scrapy
from scrapy.http.request import Request
from scrapy.http.response import Response
from scrapy.exceptions import DropItem
from scrapper.items import ProductItem

logger = logging.getLogger(__name__)

class PilulkaSpider(scrapy.Spider):
    name = 'pilulka'
    allowed_domains = ['www.pilulka.cz', 'pilulka.cz']
    
    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS': 1,
        'COOKIES_ENABLED': True
    }
    
    def __init__(self, urls=None, *args, **kwargs):
        super(PilulkaSpider, self).__init__(*args, **kwargs)
        self.start_urls = urls if urls else []

    def start_requests(self):
        for url in self.start_urls:
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
                errback=self.handle_error
            )

    def _get_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'cs-CZ,cs;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def parse_product(self, response):
        url = response.meta.get('url', response.url)
        
        try:
            # Create empty product item
            item = ProductItem.create_empty(url=url, website='pilulka.cz')
            
            # Extract product name
            product_name = response.css('h1.service-detail__title span::text').get()
            if not product_name:
                return item.mark_failure()
            item['product_name'] = product_name.strip()
            
            # Extract price
            price_element = response.css('div.product-card-price__prices b.notranslate::text').get()
            if price_element:
                item['raw_price'] = price_element.strip()
                # Extract numerical price
                price_match = re.search(r'(\d+(?:\s?\d+)*)', price_element)
                if price_match:
                    price_str = price_match.group(1).replace(' ', '')
                    item['price'] = float(price_str)
            
            # Extract stock status
            stock_text = response.css('div.stock::text').get()
            if stock_text:
                stock_text = stock_text.strip()
                stock_info = {
                    'status': stock_text,
                    'delivery_method': 'HOME_DELIVERY'
                }
                
                # Add quantity if available
                quantity_match = re.search(r'Skladem\s+(\d+)\+?ks', stock_text)
                if quantity_match:
                    stock_info['store_count'] = int(quantity_match.group(1))
                
                # Add delivery time
                delivery_time = response.css('div.fastestdelivery-date span::text').get()
                if delivery_time:
                    stock_info['delivery_time'] = delivery_time.strip()
                
                # Try to extract delivery cost
                delivery_cost = response.css('div.delivery-cost::text').get()
                if delivery_cost:
                    cost_match = re.search(r'(\d+(?:\s?\d+)*)', delivery_cost)
                    if cost_match:
                        cost_str = cost_match.group(1).replace(' ', '').replace('\xa0', '')
                        stock_info['delivery_cost'] = float(cost_str)
                        stock_info['delivery_cost_currency'] = 'CZK'
                
                item.add_stock_info(stock_info)
            
            # Extract product description
            description = response.css('div.truncated-text__fulldesc p::text').getall()
            if description:
                item.add_specs({'description': ' '.join(p.strip() for p in description if p.strip())})
            
            # Extract price per unit
            price_per_unit = response.css('div.price-perunit::text').get()
            if price_per_unit:
                item.add_specs({'price_per_unit': price_per_unit.strip()})
            
            # Extract delivery info
            delivery_info = response.css('div.block-availability__fastest .fastestdelivery-date span::text').get()
            if delivery_info:
                item.add_specs({'delivery_info': delivery_info.strip()})
            
            return item.mark_success()
            
        except Exception as e:
            logger.error(f"Error parsing product from {url}: {str(e)}")
            return ProductItem.create_empty(url=url, website='pilulka.cz').mark_failure()

    def handle_error(self, failure):
        """Handle request failures."""
        url = failure.request.meta.get('url', failure.request.url)
        
        if hasattr(failure.value, 'response') and failure.value.response:
            response = failure.value.response
            logger.error(f"Request failed for {url}: HTTP {response.status}")
        else:
            logger.error(f"Request failed for {url}")
            