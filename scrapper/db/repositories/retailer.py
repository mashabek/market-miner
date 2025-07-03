from typing import Optional
from supabase import Client
from scrapper.db.repositories.base import BaseRepository
from scrapper.db.models import RetailerData
from scrapper.db.models import RetailerType

class RetailerRepository(BaseRepository[RetailerData]):
    """Repository for retailer operations"""

    def __init__(self, supabase: Client):
        super().__init__(supabase, "retailers", RetailerData)

    async def get_by_name(self, name: str) -> Optional[RetailerData]:
        """Get retailer by name (case-insensitive)"""
        result = await self.supabase.table(self.table_name).select("*").ilike("name", f"{name}").execute()
        return RetailerData.from_dict(result.data[0]) if result.data else None

    async def get_by_type(self, retailer_type: RetailerType) -> list[RetailerData]:
        """Get retailers by type"""
        result = await self.supabase.table(self.table_name).select("*").eq("type", retailer_type.value).execute()
        return [RetailerData.from_dict(item) for item in result.data]

    async def get_by_country(self, country_code: str) -> list[RetailerData]:
        """Get retailers by country code"""
        result = await self.supabase.table(self.table_name).select("*").eq("country", country_code.upper()).execute()
        return [RetailerData.from_dict(item) for item in result.data] 