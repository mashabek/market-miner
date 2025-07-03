from typing import Optional, List
from supabase import Client
from scrapper.db.repositories.base import BaseRepository
from scrapper.db.models import ProductData

class ProductRepository(BaseRepository[ProductData]):
    """Repository for product operations"""

    def __init__(self, supabase: Client):
        super().__init__(supabase, "products", ProductData)

    async def get_by_name_and_brand(self, name: str, brand: Optional[str] = None) -> Optional[ProductData]:
        """Get product by name and brand"""
        query = self.supabase.table(self.table_name).select("*").eq("name", name)
        if brand:
            query = query.eq("brand", brand)
        result = await query.execute()
        return ProductData.from_dict(result.data[0]) if result.data else None

    async def get_by_category(self, category_id: int) -> List[ProductData]:
        """Get all products in a category"""
        result = await self.supabase.table(self.table_name).select("*").eq("category_id", category_id).execute()
        return [ProductData.from_dict(item) for item in result.data]

    async def search_products(self, search_term: str) -> List[ProductData]:
        """Search products by name or brand"""
        search_pattern = f"%{search_term}%"
        result = await self.supabase.table(self.table_name).select("*").or_(
            f"name.ilike.{search_pattern},brand.ilike.{search_pattern}"
        ).execute()
        return [ProductData.from_dict(item) for item in result.data]

    async def get_products_without_category(self) -> List[ProductData]:
        """Get products without assigned category"""
        result = await self.supabase.table(self.table_name).select("*").is_("category_id", "null").execute()
        return [ProductData.from_dict(item) for item in result.data]

    async def update_category(self, product_id: int, category_id: Optional[int]) -> ProductData:
        """Update product category"""
        result = await self.supabase.table(self.table_name).update({"category_id": category_id}).eq("id", product_id).execute()
        return ProductData.from_dict(result.data[0]) if result.data else None 