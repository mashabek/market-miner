from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime
from scrapper.db.models.base import BaseModel

@dataclass(kw_only=True)
class PricePoint(BaseModel):
    """Model for price history data points"""
    retailer_product_id: int
    price: Optional[float] = None
    currency: Optional[str] = None
    stock_info: List[Dict] = field(default_factory=list)
    offers: List[Dict] = field(default_factory=list)
    scraped_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_scraped_item(cls, item, retailer_product_id: int) -> 'PricePoint':
        """Create PricePoint from scraped item"""
        # Handle timestamp conversion
        scraped_at = datetime.now()
        if 'timestamp' in item:
            timestamp_str = item['timestamp']
            try:
                if isinstance(timestamp_str, str):
                    # Try ISO format first
                    if 'T' in timestamp_str:
                        scraped_at = datetime.fromisoformat(timestamp_str)
                    else:
                        # Try common format like '2023-12-25 14:30:00'
                        scraped_at = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                elif isinstance(timestamp_str, datetime):
                    scraped_at = timestamp_str
            except (ValueError, TypeError):
                # Use current time if parsing fails
                scraped_at = datetime.now()
        
        return cls(
            retailer_product_id=retailer_product_id,
            price=item.get('price'),
            currency=item.get('currency'),
            stock_info=item.get('stock_info', []),
            offers=item.get('offers', []),
            scraped_at=scraped_at
        )

    def to_dict(self) -> dict:
        """Convert model to dictionary, excluding updated_at field"""
        result = {}
        for key, value in self.__dict__.items():
            # Skip updated_at field as it doesn't exist in price_history table
            if key == 'updated_at':
                continue
            if value is not None:
                if isinstance(value, datetime):
                    result[key] = self._format_datetime(value)
                else:
                    result[key] = value
        return result
