from typing import Optional, List
from supabase import AsyncClient
from scrapper.db.repositories.base import BaseRepository
from scrapper.db.models.price_point import PricePoint

class PricePointRepository(BaseRepository[PricePoint]):
    """Repository for price history data points"""

    def __init__(self, supabase: AsyncClient):
        super().__init__(supabase, "price_history", PricePoint)

    async def create(self, model: PricePoint) -> PricePoint:
        """Create a new price point record."""
        data = model.to_dict()
        result = await self.supabase.table(self.table_name).insert(data).execute()
        return PricePoint.from_dict(result.data[0])

    async def get_by_id(self, id: int) -> Optional[PricePoint]:
        """Get a price point by ID."""
        result = await self.supabase.table(self.table_name).select("*").eq("id", id).execute()
        return PricePoint.from_dict(result.data[0]) if result.data else None

    async def list_by_product(self, retailer_product_id: int, limit: int = 100) -> List[PricePoint]:
        """List price points for a retailer product, most recent first."""
        result = await self.supabase.table(self.table_name).select("*").eq("retailer_product_id", retailer_product_id).order("scraped_at", desc=True).limit(limit).execute()
        return [PricePoint.from_dict(item) for item in result.data]
