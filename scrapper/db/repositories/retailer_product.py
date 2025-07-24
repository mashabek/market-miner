from typing import Optional, List
from supabase import AsyncClient
from scrapper.db.repositories.base import BaseRepository
from scrapper.db.models.retailer_product import RetailerProduct

class RetailerProductRepository(BaseRepository[RetailerProduct]):
    """Repository for retailer product operations"""

    def __init__(self, supabase: AsyncClient):
        super().__init__(supabase, "retailer_products", RetailerProduct)

    async def get_by_url(self, retailer_id: int, url: str) -> Optional[RetailerProduct]:
        """Get retailer product by URL"""
        result = await self.supabase.table(self.table_name)\
            .select("*")\
            .eq("retailer_id", retailer_id)\
            .eq("url", url)\
            .execute()
        return RetailerProduct.from_dict(result.data[0]) if result.data else None

    async def get_by_retailer(self, retailer_id: int, active_only: bool = True) -> List[RetailerProduct]:
        """Get all products for a retailer"""
        query = self.supabase.table(self.table_name).select("*").eq("retailer_id", retailer_id)
        if active_only:
            query = query.eq("is_active", True)
        result = await query.execute()
        return [RetailerProduct.from_dict(item) for item in result.data]

    async def upsert(self, product: RetailerProduct) -> RetailerProduct:
        """Upsert retailer product by (retailer_id, url)"""
        data = product.to_dict()
        update_data = {k: v for k, v in data.items() if k != 'created_at'}
        result = await self.supabase.table(self.table_name)\
            .upsert(update_data, on_conflict="retailer_id,url")\
            .execute()
        return RetailerProduct.from_dict(result.data[0])

    async def search_by_name(self, search_term: str, retailer_id: Optional[int] = None) -> List[RetailerProduct]:
        """Search products by name"""
        query = self.supabase.table(self.table_name)\
            .select("*")\
            .textSearch("name", search_term)
        if retailer_id:
            query = query.eq("retailer_id", retailer_id)
        result = await query.execute()
        return [RetailerProduct.from_dict(item) for item in result.data]
