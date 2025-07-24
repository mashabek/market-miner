from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime
from scrapper.db.models.base import BaseModel

@dataclass(kw_only=True)
class RetailerProduct(BaseModel):
    """Model for retailer-specific product data"""
    retailer_id: int
    url: str
    name: str
    retailer_sku: Optional[str] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    category_path: Optional[str] = None
    category_id: Optional[int] = None
    current_price: Optional[float] = None
    currency: Optional[str] = None
    stock_info: List[Dict] = field(default_factory=list)
    specifications: Dict = field(default_factory=dict)
    images: List[str] = field(default_factory=list)
    variants: List[Dict] = field(default_factory=list)
    retailer_metadata: Dict = field(default_factory=dict)
    is_active: bool = True
    last_scraped_at: Optional[datetime] = None
    last_successful_scrape_at: Optional[datetime] = None
    scrape_error_count: int = 0

    @classmethod
    def from_scraped_item(cls, item, retailer_id: int) -> 'RetailerProduct':
        """Create RetailerProduct from scraped item"""
        # Extract brand from item or specs
        brand = item.get('brand')
        if not brand and item.get('specs'):
            brand = item.get('specs', {}).get('brand')
        
        return cls(
            retailer_id=retailer_id,
            url=item['url'],
            name=item['product_name'],
            retailer_sku=item.get('product_id'),
            brand=brand,
            description=item.get('specs', {}).get('description'),
            current_price=item.get('price'),
            currency=item.get('currency'),
            stock_info=item.get('stock_info', []),
            specifications=item.get('specs', {}),
            images=item.get('images', []),
            variants=item.get('variants', []),
            retailer_metadata={
                'rating': item.get('rating'),
                'review_count': item.get('review_count'),
                'offers': item.get('offers', [])
            },
            last_scraped_at=datetime.now(),
            last_successful_scrape_at=datetime.now() if item.get('success') else None
        )
