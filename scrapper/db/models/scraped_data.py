from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime

from scrapper.items import ProductItem
from scrapper.db.models.base import BaseModel
from scrapper.db.models.enums import Currency

@dataclass(kw_only=True)
class ScrapedData(BaseModel):
    """Data model for scraped product data"""
    url: str
    image_urls: Optional[list] = None  # List of product image URLs (for variants, etc.)
    retailer_id: int
    name: str
    success: bool = False
    product_id: Optional[int] = None
    brand: Optional[str] = None
    raw_category: Optional[str] = None
    category_id: Optional[int] = None
    price: Optional[float] = None
    currency: Optional[Currency] = None
    stock_info: List[Dict] = field(default_factory=list)
    delivery_info: Dict = field(default_factory=dict)
    offers: List[Dict] = field(default_factory=list)
    extended_info: Dict = field(default_factory=dict)
    scraped_at: datetime = field(default_factory=datetime.now)
    error_info: Optional[Dict] = None

    @classmethod
    def from_scraped_item(cls, item: ProductItem, retailer_id: int) -> 'ScrapedData':
        """Create ScrapedData from scraped ProductItem"""
        return cls(
            url=item['url'],
            image_urls=item.get('image_urls') or item.get('images') or None,
            retailer_id=retailer_id,
            name=item['product_name'],
            success=item.get('success', False),
            brand=item.get('specs', {}).get('brand', None),
            price=item.get('price', None),
            currency=Currency(item.get('currency')) if item.get('currency') else None,
            stock_info=item.get('stock_info', []),
            offers=[offer for offer in item.get('offers', [])],
            extended_info=item.get('specs', {}),
            scraped_at=datetime.fromisoformat(item['timestamp']),
            error_info=item.get('error_info')
        )

    def to_dict(self) -> dict:
        """Convert ScrapedData to dictionary"""
        data = super().to_dict()
        if self.currency:
            data['currency'] = self.currency.value
        return data 