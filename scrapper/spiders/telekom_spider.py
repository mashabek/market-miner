"""
Spider for Telekom.hu, a Hungarian telecommunications provider.
This spider extracts product information using Telekom's API.
"""

import json
import logging
import re
from urllib.parse import urlparse, parse_qs

import scrapy
from scrapy.http.request import Request

from scrapper.items import AggregatorProductItem, OfferItem, VariantItem

logger = logging.getLogger(__name__)

class TelekomSpider(scrapy.Spider):
    name = 'telekom'
    allowed_domains = ['telekom.hu']
    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_DELAY': 1.5,
        'CONCURRENT_REQUESTS': 2,
        'COOKIES_ENABLED': True
    }
    
    def __init__(self, urls=None, *args, **kwargs):
        super(TelekomSpider, self).__init__(*args, **kwargs)
        self.start_urls = urls if urls else []
        if not self.start_urls:
            logger.error("No URLs provided to spider")
            raise ValueError("No URLs provided to spider")

    def _get_api_url(self, url: str) -> tuple:
        """Convert product page URL to API URL and extract SKU ID."""
        product_seo_name = None
        sku_id = None
        
        # Parse the product URL to extract necessary parts
        if 'termek/' in url:
            product_path = url.split('termek/')[1]
            product_seo_name = product_path.split('?')[0] if '?' in product_path else product_path
            
            # Extract skuId from query parameters if present
            sku_match = re.search(r'skuId=([^&]+)', url)
            if sku_match:
                sku_id = sku_match.group(1)
        
        if not product_seo_name:
            raise ValueError(f"Could not extract product name from URL: {url}")
        
        # Construct the API URL
        api_url = f"https://www.telekom.hu/webshop/api/v1/devices/getDeviceSpecification/{product_seo_name}"
        if sku_id:
            api_url += f"?skuId={sku_id}"
            
        return api_url, sku_id

    def _get_headers(self):
        """Get request headers."""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'x-segment': 'residential',
            'Accept-Language': 'en-US,en;q=0.9,hu;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }

    def start_requests(self):
        """Generate initial requests."""
        if not self.start_urls:
            logger.error("No URLs to process")
            return

        for url in self.start_urls:
            try:
                api_url, sku_id = self._get_api_url(url)
                yield Request(
                    url=api_url,
                    callback=self.parse_product,
                    headers=self._get_headers(),
                    meta={
                        'url': url,
                        'sku_id': sku_id,
                        'dont_redirect': False,
                        'max_redirects': 5,
                        'original_url': url
                    },
                    errback=self.handle_error,
                    dont_filter=True
                )
            except Exception as e:
                logger.error(f"Error generating request for {url}: {str(e)}", exc_info=True)
                yield AggregatorProductItem.create_empty(url=url, website='telekom.hu').mark_failure()

    def parse_product(self, response):
        """Parse product API response."""
        url = response.meta.get('url', response.url)
        sku_id = response.meta.get('sku_id')
        
        try:
            item = AggregatorProductItem.create_empty(url=url, website='telekom.hu')
            
            try:
                data = json.loads(response.text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response for {url}: {str(e)}")
                return item.mark_failure()
            
            # Extract basic product info
            item['product_name'] = data.get('name', 'Unknown Product')
            item['product_id'] = data.get('id')
            item['brand'] = data.get('brand', '')
            
            # Process all SKUs as variants
            variants = []
            for sku in data.get('skus', []):
                variant = VariantItem()
                variant['variant_id'] = sku.get('id')
                variant['sku'] = sku.get('skuId')
                
                # Add color and storage info
                if 'color' in sku:
                    variant['color'] = sku['color'].get('label')
                    variant['color_hex'] = sku['color'].get('value')
                if 'storage' in sku:
                    variant['storage'] = sku['storage'].get('value')
                
                # Create offer for this variant
                offer = OfferItem()
                offer['seller_name'] = "Telekom"
                offer['seller_url'] = url
                
                # Extract list price from the SKU data
                list_price_data = sku.get('listPrice', {})
                if not list_price_data and 'onetimePrice' in sku:
                    list_price_data = sku.get('onetimePrice', {})
                
                if list_price_data and 'listPrice' in list_price_data:
                    price = float(list_price_data['listPrice'])
                    price_text = f"{price} Ft"
                    
                    offer['price'] = price
                    offer['raw_price'] = price_text
                    offer['delivery_price'] = 0.0
                    offer['total_price'] = price
                
                # Set stock status
                stock_status = "IN_STOCK" if sku.get('availableInStock', 0) > 0 else "OUT_OF_STOCK"
                offer['stock_status'] = stock_status
                
                variant.add_offer(offer)
                variants.append(variant)
            
            # Add all variants to the item
            item.add_variants(variants)
            
            # If a specific SKU was requested, set it as the selected variant
            if sku_id:
                for variant in variants:
                    if variant['sku'] == sku_id:
                        item.set_selected_variant(variant)
                        break
            elif variants:  # Default to first variant if none specified
                item.set_selected_variant(variants[0])
            
            # Extract specifications (common to all variants)
            specs = {}
            for spec in data.get('specifications', []):
                if spec.get('name') and spec.get('value'):
                    specs[spec['name']] = spec['value']
            
            if specs:
                item.add_specs(specs)
            
            # Extract images (from selected variant)
            selected_variant = item.get_selected_variant()
            if selected_variant:
                images = []
                target_sku = next((sku for sku in data.get('skus', []) if sku.get('skuId') == selected_variant['sku']), None)
                if target_sku:
                    for image_set in target_sku.get('imageUrls', []):
                        # Get the highest resolution image from each set
                        highest_res = max(image_set, key=lambda x: int(x.get('width', 0)))
                        if highest_res.get('url'):
                            images.append(highest_res['url'])
                
                if images:
                    item.add_images(images)
            
            return item.mark_success()
            
        except Exception as e:
            logger.error(f"Error parsing product from {url}: {str(e)}")
            return AggregatorProductItem.create_empty(url=url, website='telekom.hu').mark_failure()

    def handle_error(self, failure):
        """Handle request failures."""
        url = failure.request.meta.get('original_url', failure.request.url)
        
        if hasattr(failure.value, 'response') and failure.value.response:
            response = failure.value.response
            logger.error(f"Request failed for {url}: HTTP {response.status}")
        else:
            logger.error(f"Request failed for {url}")
            