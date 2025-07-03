from dataclasses import dataclass
from typing import Optional
from scrapper.db.models.base import BaseModel
from scrapper.db.models.enums import RetailerType

@dataclass(kw_only=True)
class RetailerData(BaseModel):
    """Data model for retailers"""
    name: str
    type: RetailerType
    country: str
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RetailerData':
        """Create RetailerData instance from dictionary"""
        if 'type' in data:
            data['type'] = RetailerType(data['type'])
        return super().from_dict(data)

    def to_dict(self) -> dict:
        """Convert RetailerData to dictionary"""
        data = super().to_dict()
        if self.type:
            data['type'] = self.type.value
        return data 