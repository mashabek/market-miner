# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import re
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from scrapy.exceptions import DropItem
from scrapy import Spider
from scrapper.items import ProductItem, VariantItem
from scrapper.db.config import get_supabase_client
from scrapper.db.services.scraping_service import ScrapingService

logger = logging.getLogger(__name__)

class ProductValidationPipeline:
    """Pipeline for validating and cleaning product data."""
    
    def __init__(self):
        self.items_processed = 0
        self.items_dropped = 0

    def process_item(self, item: ProductItem, spider) -> ProductItem:
        adapter = ItemAdapter(item)
        
        # Validate required fields
        required_fields = ['url', 'website', 'product_name']
        for field in required_fields:
            if not adapter.get(field):
                self.items_dropped += 1
                raise DropItem(f"Missing required field: {field}")

        # Clean and process the data
        try:
            # Clean product name
            if adapter.get('product_name'):
                adapter['product_name'] = self._clean_text(adapter['product_name'])

            # Process variants if present
            if adapter.get('variants'):
                adapter['variants'] = self._process_variants(adapter['variants'])
            
            # Process selected variant
            if adapter.get('selected_variant'):
                adapter['selected_variant'] = self._process_variant(adapter['selected_variant'])
                
                # Update main product price from selected variant
                if 'offer' in adapter['selected_variant']:
                    offer = adapter['selected_variant']['offer']
                    adapter['price'] = offer.get('price')
                    adapter['raw_price'] = offer.get('raw_price')
            
            # Clean stock info
            if adapter.get('stock_info'):
                adapter['stock_info'] = [self._clean_stock_info(info) for info in adapter['stock_info']]
            
            # Validate image URLs
            if adapter.get('images'):
                adapter['images'] = self._validate_image_urls(adapter['images'])
            
            # Clean specs
            if adapter.get('specs'):
                adapter['specs'] = self._clean_specs(adapter['specs'])
            
            # Ensure timestamp is in correct format
            if not adapter.get('timestamp'):
                adapter['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            self.items_processed += 1
            return item

        except Exception as e:
            logger.error(f"Error processing item: {str(e)}")
            self.items_dropped += 1
            raise DropItem(f"Error processing item: {str(e)}")

    def _process_variants(self, variants: List[Dict]) -> List[Dict]:
        """Process and validate a list of variants."""
        processed_variants = []
        for variant in variants:
            try:
                processed_variant = self._process_variant(variant)
                if processed_variant:
                    processed_variants.append(processed_variant)
            except Exception as e:
                logger.warning(f"Error processing variant: {str(e)}")
                continue
        return processed_variants

    def _process_variant(self, variant: Dict) -> Dict:
        """Process and validate a single variant."""
        if not variant:
            return {}

        processed = {}
        
        # Copy basic variant fields
        for field in ['variant_id', 'sku', 'color', 'color_hex', 'storage']:
            if field in variant:
                processed[field] = self._clean_text(str(variant[field]))
        
        # Process offer if present
        if 'offer' in variant:
            offer = variant['offer']
            processed_offer = {}
            
            # Process price fields
            if 'price' in offer:
                processed_offer['price'] = self._extract_price(str(offer['price']))
            if 'raw_price' in offer:
                processed_offer['raw_price'] = self._clean_text(str(offer['raw_price']))
            if 'delivery_price' in offer:
                processed_offer['delivery_price'] = self._extract_price(str(offer['delivery_price']))
            if 'total_price' in offer:
                processed_offer['total_price'] = self._extract_price(str(offer['total_price']))
            
            # Process stock status
            if 'stock_status' in offer:
                processed_offer['stock_status'] = self._normalize_stock_status(offer['stock_status'])
            
            # Copy seller information
            for field in ['seller_name', 'seller_url']:
                if field in offer:
                    processed_offer[field] = self._clean_text(str(offer[field]))
            
            processed['offer'] = processed_offer
        
        return processed

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text fields."""
        if not text:
            return ""
        # Remove extra whitespace and normalize
        return " ".join(text.strip().split())

    def _extract_price(self, raw_price: str) -> Optional[float]:
        """Extract numerical price from raw price string."""
        if not raw_price:
            return None
        
        # Remove currency symbols and normalize separators
        price_str = raw_price.replace(" ", "")
        price_str = re.sub(r'[^\d,.]', '', price_str)
        
        # Handle different number formats
        try:
            # Convert Hungarian format (123.456,78) to standard float
            if ',' in price_str:
                price_str = price_str.replace('.', '').replace(',', '.')
            return float(price_str)
        except ValueError:
            logger.warning(f"Could not parse price: {raw_price}")
            return None

    def _normalize_stock_status(self, status: str) -> str:
        """Normalize stock status to standard values."""
        return self._clean_text(status).upper()

    def _validate_image_urls(self, urls: list) -> list:
        """Validate and clean image URLs."""
        valid_urls = []
        for url in urls:
            if url and isinstance(url, str):
                # Basic URL validation
                if url.startswith(('http://', 'https://')):
                    valid_urls.append(url.strip())
        return valid_urls

    def _clean_specs(self, specs: Dict[str, Any]) -> Dict[str, str]:
        """Clean and validate product specifications."""
        cleaned_specs = {}
        for key, value in specs.items():
            if key and value:
                cleaned_key = self._clean_text(str(key))
                cleaned_value = self._clean_text(str(value))
                if cleaned_key and cleaned_value:
                    cleaned_specs[cleaned_key] = cleaned_value
        return cleaned_specs

    def _clean_stock_info(self, stock_info: Dict) -> Dict:
        """Clean and validate stock info dictionary."""
        cleaned = {}
        
        # Clean text fields
        for field in ['status', 'delivery_method', 'delivery_time', 'additional_info']:
            if field in stock_info and stock_info[field]:
                cleaned[field] = self._clean_text(str(stock_info[field]))
        
        # Clean numeric fields
        if 'delivery_cost' in stock_info and stock_info['delivery_cost'] is not None:
            cleaned['delivery_cost'] = self._extract_price(str(stock_info['delivery_cost']))
        
        if 'store_count' in stock_info and stock_info['store_count'] is not None:
            try:
                cleaned['store_count'] = int(stock_info['store_count'])
            except (ValueError, TypeError):
                pass
        
        # Copy currency as is
        if 'delivery_cost_currency' in stock_info:
            cleaned['delivery_cost_currency'] = stock_info['delivery_cost_currency']
        
        return cleaned

    def close_spider(self, spider):
        """Log pipeline statistics when spider closes."""
        logger.info(f"Pipeline processed {self.items_processed} items")
        logger.info(f"Pipeline dropped {self.items_dropped} items")

class DatabasePipeline:
    """Pipeline for storing scraped data in the database"""
    
    def __init__(self):
        self.supabase = None
        self.scraping_service = None
        self.retailer_cache = {}

    async def process_item(self, item: ProductItem, spider: Spider) -> ProductItem:
        """Process item and store in database"""
        # Skip processing if item was dropped by previous pipeline
        if isinstance(item, DropItem):
            return item
            
        adapter = ItemAdapter(item)
        
        # Initialize connection on first use
        if not self.scraping_service:
            try:
                self.supabase = await get_supabase_client()
                self.scraping_service = ScrapingService(self.supabase)
                logger.info("Successfully initialized Supabase client")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {str(e)}")
                raise DropItem("Failed to initialize database connection")

        try:
            # Get retailer ID from cache or database
            retailer_id = await self._get_retailer_id(spider)
            if not retailer_id:
                raise DropItem(f"No retailer found for spider {spider.name}")

            # Process the item using scraping service
            response = await self.scraping_service.process_scraped_item(dict(adapter), retailer_id)
            
            # Handle Supabase response
            if not response:
                raise DropItem("Failed to store item in database - no data returned")
            
            scraped_data = response
            if not scraped_data:
                raise DropItem("Failed to store item in database - invalid data format")
            
            return item

        except Exception as e:
            logger.error(f"Error storing item in database: {str(e)}")
            return DropItem(f"Database error: {str(e)}")

    async def _get_retailer_id(self, spider: Spider) -> Optional[int]:
        """Get retailer ID for spider, using cache to minimize database queries"""
        if spider.name in self.retailer_cache:
            return self.retailer_cache[spider.name]

        # Map spider names to retailer names and types
        retailer_mapping = {
            'datart': ('Datart', 'DIRECT_RETAILER'),
            'euronics': ('Euronics', 'DIRECT_RETAILER'),
            'mediamarkt': ('MediaMarkt', 'DIRECT_RETAILER'),
            'pilulka': ('Pilulka', 'DIRECT_RETAILER'),
            'planeo': ('Planeo', 'DIRECT_RETAILER'),
            'telekom': ('Telekom', 'DIRECT_RETAILER'),
            'zbozi': ('Zbozi', 'PRICE_COMPARER')
        }

        if spider.name not in retailer_mapping:
            return None

        retailer_name, _ = retailer_mapping[spider.name]
        
        try:
            retailer = await self.scraping_service.retailer_repo.get_by_name(retailer_name)
            if not retailer:
                return None
            
            
            self.retailer_cache[spider.name] = retailer.id
            return retailer.id
            
        except Exception as e:
            logger.error(f"Error fetching retailer ID for {retailer_name}: {str(e)}")
            return None

    def close_spider(self, spider: Spider):
        """Clean up resources when spider closes"""
        self.supabase = None
        self.scraping_service = None
