from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from scrapper.db.models.base import BaseModel

@dataclass
class AvailabilityKeyword(BaseModel):
    """Model representing an availability keyword for a retailer."""
    
    def __init__(
        self,
        retailer_id: int,
        keyword: str,
        language: Optional[str] = None,
        indicates_in_stock: Optional[bool] = None,
        first_seen_at: Optional[datetime] = None,
        last_seen_at: Optional[datetime] = None,
        occurrence_count: int = 1,
        is_configured: bool = False,
        id: Optional[int] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.retailer_id = retailer_id
        self.keyword = keyword
        self.language = language
        self.indicates_in_stock = indicates_in_stock
        self.first_seen_at = first_seen_at or datetime.now()
        self.last_seen_at = last_seen_at or datetime.now()
        self.occurrence_count = occurrence_count
        self.is_configured = is_configured

    @classmethod
    def from_row(cls, row: dict) -> 'AvailabilityKeyword':
        """Create an instance from a database row."""
        return cls(
            id=row.get('id'),
            retailer_id=row.get('retailer_id'),
            keyword=row.get('keyword'),
            language=row.get('language'),
            indicates_in_stock=row.get('indicates_in_stock'),
            first_seen_at=row.get('first_seen_at'),
            last_seen_at=row.get('last_seen_at'),
            occurrence_count=row.get('occurrence_count', 1),
            is_configured=row.get('is_configured', False),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
        ) 