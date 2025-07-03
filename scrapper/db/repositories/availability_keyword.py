from typing import List, Optional
from supabase import Client
from scrapper.db.models import AvailabilityKeyword
from scrapper.db.repositories import BaseRepository

class AvailabilityKeywordRepository(BaseRepository[AvailabilityKeyword]):
    """Repository for managing availability keywords."""
    
    def __init__(self, supabase: Client):
        super().__init__(supabase, "products", AvailabilityKeyword)


    async def create(self, keyword: AvailabilityKeyword) -> AvailabilityKeyword:
        """Create a new availability keyword entry."""
        response = await self.supabase.table(self.table).insert({
            'retailer_id': keyword.retailer_id,
            'keyword': keyword.keyword,
            'language': keyword.language,
            'indicates_in_stock': keyword.indicates_in_stock,
            'first_seen_at': keyword.first_seen_at.isoformat() if keyword.first_seen_at else None,
            'last_seen_at': keyword.last_seen_at.isoformat() if keyword.last_seen_at else None,
            'occurrence_count': keyword.occurrence_count,
            'is_configured': keyword.is_configured
        }).execute()
        
        return AvailabilityKeyword.from_row(response.data[0])

    async def get_by_retailer(self, retailer_id: int) -> List[AvailabilityKeyword]:
        """Get all availability keywords for a retailer."""
        response = await self.supabase.table(self.table)\
            .select('*')\
            .eq('retailer_id', retailer_id)\
            .execute()
        
        return [AvailabilityKeyword.from_row(row) for row in response.data]

    async def get_by_retailer_and_keyword(self, retailer_id: int, keyword: str) -> Optional[AvailabilityKeyword]:
        """Get a specific availability keyword for a retailer."""
        response = await self.supabase.table(self.table)\
            .select('*')\
            .eq('retailer_id', retailer_id)\
            .eq('keyword', keyword)\
            .execute()
        
        return AvailabilityKeyword.from_row(response.data[0]) if response.data else None

    async def update_configuration(self, id: int, indicates_in_stock: bool) -> AvailabilityKeyword:
        """Update the configuration of an availability keyword."""
        response = await self.supabase.table(self.table)\
            .update({
                'indicates_in_stock': indicates_in_stock,
                'is_configured': True
            })\
            .eq('id', id)\
            .execute()
        
        return AvailabilityKeyword.from_row(response.data[0])

    async def get_unconfigured(self) -> List[AvailabilityKeyword]:
        """Get all unconfigured availability keywords."""
        response = await self.supabase.table(self.table)\
            .select('*')\
            .eq('is_configured', False)\
            .execute()
        
        return [AvailabilityKeyword.from_row(row) for row in response.data] 