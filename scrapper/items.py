# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import scrapy


class StockAvailability(scrapy.Item):
    """Represents detailed stock and delivery availability information."""
    status = scrapy.Field()
    delivery_method = scrapy.Field()  # HOME_DELIVERY, STORE_PICKUP, PARCEL_POINT
    delivery_time = scrapy.Field()  # e.g. "1-3 working days"
    delivery_cost = scrapy.Field()  # Cost in the currency specified
    delivery_cost_currency = scrapy.Field()  # Currency code (e.g. HUF, EUR)
    store_count = scrapy.Field()  # Number of stores where item is available (for store pickup)
    additional_info = scrapy.Field()  # Any additional availability information


class OfferItem(scrapy.Item):
    """Represents a single offer from a seller on an aggregator site."""
    seller_name = scrapy.Field()
    seller_url = scrapy.Field()
    price = scrapy.Field()
    raw_price = scrapy.Field()
    stock_status = scrapy.Field()
    delivery_price = scrapy.Field()
    total_price = scrapy.Field()


class VariantItem(scrapy.Item):
    """Represents a product variant with its specific attributes and offer."""
    variant_id = scrapy.Field()
    sku = scrapy.Field()
    color = scrapy.Field()
    color_hex = scrapy.Field()
    storage = scrapy.Field()
    offer = scrapy.Field()

    def add_offer(self, offer: OfferItem):
        """Add an offer to the variant."""
        self['offer'] = dict(offer)
        return self


class ProductItem(scrapy.Item):
    # Required fields
    url = scrapy.Field()
    website = scrapy.Field()
    product_name = scrapy.Field()
    raw_price = scrapy.Field()
    price = scrapy.Field()
    currency = scrapy.Field()
    stock_info = scrapy.Field()  # List of StockAvailability items for detailed availability
    timestamp = scrapy.Field()
    success = scrapy.Field()

    # Optional fields
    product_id = scrapy.Field()
    specs = scrapy.Field()
    images = scrapy.Field()

    @classmethod
    def create_empty(cls, url: str, website: str) -> 'ProductItem':
        """Create an empty product item with default values."""
        return cls(
            url=url,
            website=website,
            product_name=None,
            raw_price=None,
            price=None,
            stock_info=[],
            product_id=None,
            specs={},
            images=[],
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            success=False
        )

    def mark_success(self):
        """Mark the item as successfully scraped."""
        self['success'] = True
        return self

    def mark_failure(self):
        """Mark the item as failed to scrape."""
        self['success'] = False
        return self

    def add_specs(self, specs: Dict[str, str]):
        """Add specifications to the item."""
        self['specs'] = specs
        return self

    def add_images(self, images: List[str]):
        """Add image URLs to the item."""
        self['images'] = images
        return self

    def add_stock_info(self, stock_info: StockAvailability):
        """Add detailed stock availability information."""
        if 'stock_info' not in self:
            self['stock_info'] = []
        self['stock_info'].append(dict(stock_info))
        return self

class AggregatorProductItem(ProductItem):
    """Represents a product from an aggregator site with multiple offers and variants."""
    
    # Additional fields specific to aggregator products
    offers = scrapy.Field()
    variants = scrapy.Field()
    selected_variant = scrapy.Field()
    category = scrapy.Field()
    brand = scrapy.Field()
    rating = scrapy.Field()
    review_count = scrapy.Field()

    @classmethod
    def create_empty(cls, url: str, website: str) -> 'AggregatorProductItem':
        """Create an empty aggregator product item with default values."""
        item = super().create_empty(url, website)
        item['offers'] = []
        item['variants'] = []
        item['selected_variant'] = None
        item['category'] = None
        item['brand'] = None
        item['rating'] = None
        item['review_count'] = None
        return item

    def add_offer(self, offer: OfferItem):
        """Add an offer to the product."""
        if 'offers' not in self:
            self['offers'] = []
        self['offers'].append(dict(offer))
        return self

    def add_variants(self, variants: List[VariantItem]):
        """Add variants to the product."""
        if 'variants' not in self:
            self['variants'] = []
        self['variants'].extend([dict(variant) for variant in variants])
        return self

    def set_selected_variant(self, variant: VariantItem):
        """Set the selected variant and update product price/stock from its offer."""
        self['selected_variant'] = dict(variant)
        
        # Update product price and stock status from selected variant's offer
        if 'offer' in variant:
            offer = variant['offer']
            self['price'] = offer.get('price')
            self['raw_price'] = offer.get('raw_price')
            self['stock_status'] = offer.get('stock_status', 'UNKNOWN')
        
        return self

    def get_selected_variant(self) -> Optional[Dict]:
        """Get the currently selected variant."""
        return self.get('selected_variant')

class ProductDiscoveryItem(scrapy.Item):
    """Represents a discovered product URL and its category information."""
    url = scrapy.Field()          # absolute product URL
    website = scrapy.Field()      # 'mediamarkt.hu' / 'alza.hu'
    category_path = scrapy.Field()# e.g. "Electronics > Smartphones"
    product_name = scrapy.Field() # optional – list page title
    timestamp = scrapy.Field()    # when the URL was discovered

    @classmethod
    def create(cls, url: str, website: str, category_path: str, product_name: Optional[str] = None) -> 'ProductDiscoveryItem':
        """Create a new discovery item with the current timestamp."""
        return cls(
            url=url,
            website=website,
            category_path=category_path,
            product_name=product_name,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
