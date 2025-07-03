from dataclasses import dataclass
from typing import Optional

from scrapper.items import ProductItem
from scrapper.db.models.base import BaseModel

@dataclass(kw_only=True)
class ProductData(BaseModel):
    """Data model for products"""
    name: str
    brand: Optional[str] = None
    category_id: Optional[int] = None

    @classmethod
    def from_scraped_item(cls, item: ProductItem) -> 'ProductData':
        """Create ProductData from scraped ProductItem"""
        return cls(
            name=item['product_name'],
            brand=item.get('specs', {}).get('brand'),
            # category_id will be set after category is resolved
        ) 