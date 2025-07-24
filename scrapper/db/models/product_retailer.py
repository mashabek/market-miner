from dataclasses import dataclass
from typing import Optional
from scrapper.db.models.base import BaseModel

@dataclass(kw_only=True)
class ProductRetailerData(BaseModel):
    """Association table for products and retailers (many-to-many)"""
    product_id: int
    retailer_id: int
    retailer_sku: Optional[str] = None  # SKU or code used by retailer for this product
    url: Optional[str] = None           # Main product URL on retailer's site
    image_urls: Optional[list] = None   # List of product image URLs (for variants, etc.)
    extra_data: Optional[dict] = None   # Any additional info (e.g., price, stock, etc.)
