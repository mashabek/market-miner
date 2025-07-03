"""
Spider for Zbozi.cz, a Czech price comparison website.
This spider extracts product information and offers from multiple sellers.
"""

import json
import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs
from datetime import datetime

import scrapy
from scrapy.http import Request, Response
from scrapy.exceptions import DropItem

from scrapper.items import AggregatorProductItem, OfferItem

logger = logging.getLogger(__name__)

class ZboziSpider(scrapy.Spider):
    name = 'zbozi'
    allowed_domains = ['www.zbozi.cz', 'zbozi.cz']
    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_DELAY': 1,  # Higher delay for aggregator site
        'CONCURRENT_REQUESTS': 16
    }
    
    def __init__(self, urls=None, *args, **kwargs):
        super(ZboziSpider, self).__init__(*args, **kwargs)
        self.start_urls = urls if urls else []
        if not self.start_urls:
            logger.error("No URLs provided to spider")
            raise ValueError("No URLs provided to spider")

    def _get_api_url(self, url: str) -> str:
        """Convert product page URL to API URL."""
        parsed_url = urlparse(url)
        path = parsed_url.path.strip('/')
        query = parse_qs(parsed_url.query)
        
           # Check if this is a direct offer URL
        if 'nabidka' in path:
            # Extract offer hash from the URL
            offer_hash = path.split('nabidka/')[1].rstrip('/')
            # Construct offer API URL
            api_url = f"https://www.zbozi.cz/api/v3/offer/{offer_hash}?filterFields=$all$&enableRedirect=1"
            return api_url
        
        # Extract product slug
        if 'vyrobek' in path:
            product_slug = path.split('vyrobek/')[1].rstrip('/')
        else:
            path_parts = path.split('/')
            product_slug = path_parts[-1]
        
        if not product_slug:
            raise ValueError(f"Could not extract product slug from URL: {url}")
        
        # Handle variant if present
        variant_param = ""
        if 'varianta' in query and query['varianta']:
            variant_param = f"productVariant={query['varianta'][0]}&"
        
        # Construct API URL for product data
        return f"https://www.zbozi.cz/api/v3/product/{product_slug}/?{variant_param}limitOffers=12&filterFields=$all$"

    def start_requests(self):
        """Generate initial requests."""
        if not self.start_urls:
            logger.error("No URLs to process")
            return

        for url in self.start_urls:
            try:
                api_url = self._get_api_url(url)
                yield Request(
                    url=api_url,
                    callback=self.parse_product,
                    headers=self._get_headers(),
                    meta={
                        'url': url,  # Keep original URL for reference
                        'dont_redirect': False,
                        'max_redirects': 5,
                        'original_url': url  # Store original URL for error handling
                    },
                    errback=self.handle_error,
                    dont_filter=True
                )
            except Exception as e:
                logger.error(f"Error generating request for {url}: {str(e)}", exc_info=True)
                yield AggregatorProductItem.create_empty(url=url, website='zbozi.cz').mark_failure()

    def _get_headers(self):
        """Get request headers."""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9,cs;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }

    def parse_product(self, response):
        """Parse product API response."""
        try:
            # Parse JSON response
            data = json.loads(response.text)
            url = response.meta.get('url', response.url)
            
            # Check for API-level redirect
            if data.get('status') in [301, 302] and (data.get('url') or data.get('redirectUrl')):
                redirect_path = data.get('url') or data.get('redirectUrl')
                try:
                    new_api_url = self._get_api_url(f"https://www.zbozi.cz{redirect_path}")
                    logger.info(f"Following API redirect to: {new_api_url}")
                    return Request(
                        url=new_api_url,
                        callback=self.parse_product,
                        headers=self._get_headers(),
                        meta=response.meta,
                        dont_filter=True
                    )
                except Exception as e:
                    logger.error(f"Failed to construct API URL from redirect: {str(e)}")
                    return AggregatorProductItem.create_empty(url=url, website='zbozi.cz').mark_failure()
            
            # Check if we have a direct offer response (has 'offer' field)
            if 'offer' in data:
                return self.parse_offer_response(data, url)
            
            # Create product item
            item = AggregatorProductItem.create_empty(url=url, website='zbozi.cz')
            
            # Extract basic product info
            product_data = data.get('product', {})
            if not product_data:
                return item.mark_failure()
            
            # Set product details
            item['product_name'] = product_data.get('displayName')
            item['product_id'] = product_data.get('id')
            item['category'] = product_data.get('category', {}).get('displayName')
            item['brand'] = product_data.get('vendor', {}).get('displayName')
            item['rating'] = product_data.get('rating')
            
            # Extract images
            images = product_data.get('images', [])
            if images:
                item.add_images(images)
            
            # Extract specifications
            specs = {}
            for param in product_data.get('parameters', []):
                if param.get('displayName') and param.get('displayValue'):
                    value = param['displayValue']
                    if param.get('displayAbbreviation'):
                        value += f" {param['displayAbbreviation']}"
                    specs[param['displayName']] = value
            item.add_specs(specs)
            
            # Process offers
            best_offers = data.get('product', {}).get('bestOffers', {}).get('offers', [])
            if not best_offers:
                logger.warning(f"No offers found for product: {url}")
            
            for offer_data in best_offers:
                offer = OfferItem()
                offer['seller_name'] = offer_data.get('shop', {}).get('displayName')
                offer['seller_url'] = offer_data.get('url')
                offer['raw_price'] = str(offer_data.get('price', 0))
                offer['price'] = float(offer_data.get('price', 0)) / 100
                
                # Get delivery price from delivery info
                delivery = offer_data.get('delivery', {})
                delivery_price = delivery.get('minPrice', 0) if delivery else 0
                offer['delivery_price'] = float(delivery_price) / 100 if delivery_price else 0.0
                offer['total_price'] = offer['price'] + offer['delivery_price']
                
                # Just store raw availability
                offer['stock_status'] = offer_data.get('availability')
                
                item.add_offer(offer)
            
            # Set overall product price to the lowest offer price
            if item['offers']:
                min_price_offer = min(item['offers'], key=lambda x: x['total_price'])
                item['price'] = min_price_offer['price'] / 100
                item['raw_price'] = min_price_offer['raw_price']
                
                # Add stock info from best offer
                stock_info = {
                    'status': min_price_offer['stock_status'],
                    'delivery_method': 'HOME_DELIVERY',
                    'delivery_cost': min_price_offer.get('delivery_price'),
                    'delivery_cost_currency': 'CZK'
                }
                item.add_stock_info(stock_info)
            
            return item.mark_success()
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response for {url}: {str(e)}")
            return AggregatorProductItem.create_empty(url=url, website='zbozi.cz').mark_failure()
        except Exception as e:
            logger.error(f"Error parsing product from {url}: {str(e)}")
            return AggregatorProductItem.create_empty(url=url, website='zbozi.cz').mark_failure()

    def parse_offer_response(self, data, url):
        """Parse direct offer API response."""
        try:
            # Create product item
            item = AggregatorProductItem.create_empty(url=url, website='zbozi.cz')
            
            # Get main offer data for product details
            main_offer = data.get('offer', {})
            if not main_offer:
                logger.error(f"No main offer data found in API response for URL: {url}")
                return item.mark_failure()
            
            # Set basic product info from main offer
            item['product_name'] = main_offer.get('displayName')
            item['product_id'] = main_offer.get('id')
            item['category'] = main_offer.get('category', {}).get('displayName') if main_offer.get('category') else None
            
            # Add images
            if main_offer.get('image'):
                item.add_images([main_offer['image']])
            
            # Add specifications from parameters if available
            if main_offer.get('parameters'):
                specs = {}
                for param in main_offer['parameters']:
                    if param.get('displayName') and param.get('displayValue'):
                        specs[param['displayName']] = param['displayValue']
                item.add_specs(specs)
            
            # Collect all offers from both bestOffers and cheapestOffers
            all_offers = []
            
            # Get offers from bestOffers if available
            best_offers = data.get('offer', {}).get('bestOffers', {}).get('offers', [])
            if best_offers:
                all_offers.extend(best_offers)
            
            # Get offers from cheapestOffers if available
            cheapest_offers = data.get('offer', {}).get('cheapestOffers', {}).get('offers', [])
            if cheapest_offers:
                # Add only unique offers that aren't already in best_offers
                existing_ids = {offer.get('id') for offer in all_offers}
                all_offers.extend([offer for offer in cheapest_offers if offer.get('id') not in existing_ids])
            
            if not all_offers:
                logger.error(f"No offers found in either bestOffers or cheapestOffers for URL: {url}")
                return item.mark_failure()
            
            lowest_price = float('inf')
            for offer_data in all_offers:
                offer = OfferItem()
                
                # Get shop info
                shop_data = offer_data.get('shop', {})
                offer['seller_name'] = shop_data.get('displayName', 'Unknown Seller')
                offer['seller_url'] = offer_data.get('url', '')
                
                # Get price info (convert from haléře to CZK)
                raw_price = offer_data.get('price', 0)
                offer['raw_price'] = str(raw_price)
                offer['price'] = float(raw_price) / 100 if raw_price else 0.0
                
                # Get delivery price
                delivery = offer_data.get('delivery', {})
                delivery_price = delivery.get('minPrice', 0) if delivery else 0
                offer['delivery_price'] = float(delivery_price) / 100 if delivery_price else 0.0
                offer['total_price'] = offer['price'] + offer['delivery_price']
                
                # Just store raw availability
                offer['stock_status'] = offer_data.get('availability')
                
                item.add_offer(offer)
                
                # Track lowest price for main product price
                if offer['price'] < lowest_price:
                    lowest_price = offer['price']
                    item['price'] = offer['price']
                    item['raw_price'] = offer['raw_price']
            
            # Set overall product price to the lowest offer price
            if item['offers']:
                min_price_offer = min(item['offers'], key=lambda x: x['total_price'])
                item['price'] = min_price_offer['price'] / 100
                item['raw_price'] = min_price_offer['raw_price']
                
                # Add stock info from best offer
                stock_info = {
                    'status': min_price_offer['stock_status'],
                    'delivery_method': 'HOME_DELIVERY',
                    'delivery_cost': min_price_offer.get('delivery_price'),
                    'delivery_cost_currency': 'CZK'
                }
                item.add_stock_info(stock_info)
            
            return item.mark_success()
            
        except Exception as e:
            logger.error(f"Error parsing offer data from {url}: {str(e)}")
            return AggregatorProductItem.create_empty(url=url, website='zbozi.cz').mark_failure()

    def handle_error(self, failure):
        """Handle request failures."""
        url = failure.request.meta.get('original_url', failure.request.url)
        
        if hasattr(failure.value, 'response') and failure.value.response:
            response = failure.value.response
            logger.error(f"Request failed for {url}: HTTP {response.status}")
        else:
            logger.error(f"Request failed for {url}")
            