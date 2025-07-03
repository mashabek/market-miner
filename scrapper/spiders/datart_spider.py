"""
Spider for Datart.cz, a Czech electronics retailer website.
This spider extracts product information including price, availability, and specifications.
"""

import re
import logging
from typing import Dict

from scrapy.http import Response
from scrapper.utils.sentry import add_breadcrumb, monitor_errors
from scrapper.items import ProductItem
from scrapper.spiders.base_spider import BaseSpider

logger = logging.getLogger(__name__)

class DatartSpider(BaseSpider):
    name = 'datart'
    allowed_domains = ['www.datart.cz', 'datart.cz']
    
    custom_settings = {
        'ROBOTSTXT_OBEY': True,
        'DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS': 1,
        'COOKIES_ENABLED': True
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
            
            # Extract product name
            product_name = response.css('h1.product-detail-title::text').get()
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
            
            # Extract price
            price_element = response.css('div.product-price-main .actual::text').get()
            if price_element:
                item['raw_price'] = price_element.strip()
                # Extract numerical price
                price_match = re.search(r'(\d+(?:\s?\d+)*)', price_element)
                if price_match:
                    price_str = price_match.group(1).replace(' ', '').replace('\xa0', '')
                    item['price'] = float(price_str)
                    add_breadcrumb(
                        message="Extracted price",
                        category="spider.extraction",
                        data={"price": item['price'], "raw_price": item['raw_price']}
                    )
            
            # Extract stock status
            stock_text = response.css('span.product-availability-state::text').get()
            if stock_text:
                stock_text = stock_text.strip()
                
                # Create stock info with delivery details
                stock_info = {
                    'status': stock_text,
                    'delivery_method': 'HOME_DELIVERY'
                }
                
                # Extract delivery time
                delivery_date = response.css('span.product-availability-estimated-delivery::text').get()
                if delivery_date:
                    stock_info['delivery_time'] = delivery_date.strip()
                
                # Extract delivery cost
                delivery_cost = response.css('div.delivery-price::text').get()
                if delivery_cost:
                    cost_match = re.search(r'(\d+(?:\s?\d+)*)', delivery_cost)
                    if cost_match:
                        cost_str = cost_match.group(1).replace(' ', '').replace('\xa0', '')
                        stock_info['delivery_cost'] = float(cost_str)
                        stock_info['delivery_cost_currency'] = 'CZK'
                
                item.add_stock_info(stock_info)
                add_breadcrumb(
                    message="Extracted stock info",
                    category="spider.extraction",
                    data={"stock_info": stock_info}
                )
            
            # Extract product description
            description = response.css('div.product-detail-perex-box p::text').get()
            if description:
                item.add_specs({'description': description.strip()})
            
            # Extract brand
            brand = response.css('div.brand-logo img::attr(alt)').get()
            if brand:
                item.add_specs({'brand': brand.strip()})
            
            # Extract images
            main_image = response.css('div.product-gallery-main img::attr(src)').get()
            if main_image:
                item.add_images([main_image])
            
            return item.mark_success()
            
        except Exception as e:
            logger.error(f"Error parsing product from {url}: {str(e)}")
            return self.create_failed_item(url)
        