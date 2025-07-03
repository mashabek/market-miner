"""
Spider for Planeo.cz, a Czech electronics retailer website.
This spider extracts product information including price, availability, and specifications.
"""

import re
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

import scrapy
from scrapy.http import Request, Response
from scrapy.exceptions import DropItem
from scrapper.items import AggregatorProductItem, VariantItem

logger = logging.getLogger(__name__)

class PlaneoSpider(scrapy.Spider):
    name = 'planeo'
    allowed_domains = ['www.planeo.cz', 'planeo.cz']
    
    custom_settings = {
        'ROBOTSTXT_OBEY': True,
        'DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS': 1,
        'COOKIES_ENABLED': True
    }
    
    def __init__(self, urls=None, *args, **kwargs):
        super(PlaneoSpider, self).__init__(*args, **kwargs)
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
        item = AggregatorProductItem.create_empty(url=url, website='planeo.cz')
        
        try:
            # Essential fields - if these fail, we return failure
            try:
                # Extract product name - required
                product_name = response.css('div.c-pdt__title h1::text').get()
                if not product_name:
                    return item.mark_failure()
                item['product_name'] = product_name.strip()
                
                # Extract price - required
                price_element = response.css('div.c-pdt__price strong::text').get()
                if price_element:
                    item['raw_price'] = price_element.strip()
                    price_match = re.search(r'(\d+(?:\s?\d+)*)', price_element)
                    if price_match:
                        price_str = price_match.group(1).replace(' ', '').replace('\xa0', '')
                        item['price'] = float(price_str)
                else:
                    return item.mark_failure()
                
                # Extract stock status
                stock_text = response.css('div.c-availability__state p::text').get()
                if stock_text:
                    stock_text = stock_text.strip()
                    
                    # Create stock info with delivery details
                    stock_info = {
                        'status': stock_text,
                        'delivery_method': 'HOME_DELIVERY'
                    }
                    
                    # Add delivery time
                    delivery_date = response.css('div.c-availability__text p::text').get()
                    if delivery_date:
                        stock_info['delivery_time'] = delivery_date.strip()
                    
                    item.add_stock_info(stock_info)
                    
                    # Add store availability if present
                    try:
                        store_text = response.css('div.c-availability__text p.mb0.fz90p.c--link::text').get()
                        if store_text and 'prodejnách' in store_text:
                            store_count = re.search(r'na (\d+)', store_text)
                            if store_count:
                                store_info = {
                                    'status': stock_text,
                                    'delivery_method': 'STORE_PICKUP',
                                    'store_count': int(store_count.group(1))
                                }
                                item.add_stock_info(store_info)
                    except Exception as e:
                        logger.warning(f"Non-critical error parsing store availability: {str(e)}")
                else:
                    item['stock_status'] = 'UNKNOWN'
            
            except Exception as e:
                logger.error(f"Error parsing essential fields from {url}: {str(e)}")
                return item.mark_failure()
            
            # Optional fields - if these fail, we continue
            try:
                # Extract product ID
                product_id = response.css('div.c-pdt__id span::text').get()
                if product_id:
                    item['product_id'] = product_id.replace('ID: ', '').strip()
            except Exception as e:
                logger.warning(f"Non-critical error parsing product ID: {str(e)}")
            
            try:
                # Extract product description
                description = response.css('div.c-pdt__description div.js-clamp::text').get()
                if description:
                    item.add_specs({'description': description.strip()})
            except Exception as e:
                logger.warning(f"Non-critical error parsing description: {str(e)}")
            
            try:
                # Extract product type/category
                product_type = response.css('div.c-pdt__type-n-rating h2::text').get()
                if product_type:
                    item.add_specs({'product_type': product_type.strip()})
                    item['category'] = product_type.strip()
            except Exception as e:
                logger.warning(f"Non-critical error parsing category: {str(e)}")
            
            try:
                # Extract rating and review count
                rating_text = response.css('div.c-rating-stars + div::text').get()
                if rating_text:
                    rating = float(rating_text.strip().replace(',', '.'))
                    item['rating'] = rating
                    
                review_count_text = response.css('a[href="#recenze"]::text').get()
                if review_count_text:
                    count = re.search(r'(\d+)', review_count_text)
                    if count:
                        item['review_count'] = int(count.group(1))
            except Exception as e:
                logger.warning(f"Non-critical error parsing rating/reviews: {str(e)}")
            
            try:
                # Extract images
                images = response.css('div.c-carousel__item[href]::attr(href)').getall()
                if images:
                    item.add_images(images)
            except Exception as e:
                logger.warning(f"Non-critical error parsing images: {str(e)}")
            
            try:
                # Extract variants
                variants = []
                variant_sections = response.css('div.c-pdt__variants-item')
                
                for section in variant_sections:
                    try:
                        label = section.css('label::text').get('')
                        options = section.css('select option')
                        
                        for option in options:
                            if not option.attrib.get('selected'):
                                variant = VariantItem()
                                variant['variant_id'] = option.attrib.get('value', '')
                                variant_text = option.css('::text').get('').strip()
                                
                                # Only add supported variant fields
                                if 'Barva' in label:
                                    variant['color'] = variant_text
                                elif 'GB' in variant_text:
                                    variant['storage'] = variant_text
                                
                                if variant:
                                    variants.append(dict(variant))
                    except Exception as e:
                        logger.warning(f"Non-critical error parsing variant section: {str(e)}")
                        continue
                
                if variants:
                    item.add_variants(variants)
            except Exception as e:
                logger.warning(f"Non-critical error parsing variants: {str(e)}")
            
            try:
                # Extract brand from product name
                if product_name:
                    brand_match = product_name.split()[0]
                    if brand_match:
                        item['brand'] = brand_match
            except Exception as e:
                logger.warning(f"Non-critical error parsing brand: {str(e)}")
            
            return item.mark_success()
            
        except Exception as e:
            logger.error(f"Error parsing product from {url}: {str(e)}")
            return item.mark_failure()

    def handle_error(self, failure):
        """Handle request failures."""
        url = failure.request.meta.get('url', failure.request.url)
        
        if hasattr(failure.value, 'response') and failure.value.response:
            response = failure.value.response
            logger.error(f"Request failed for {url}: HTTP {response.status}")
        else:
            logger.error(f"Request failed for {url}")