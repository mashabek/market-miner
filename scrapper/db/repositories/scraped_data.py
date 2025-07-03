from typing import Optional, List, Tuple, Dict
from datetime import datetime, timedelta
from supabase import Client
from scrapper.db.repositories.base import BaseRepository
from scrapper.db.models import ScrapedData

class ScrapedDataRepository(BaseRepository[ScrapedData]):
    """Repository for scraped data operations"""

    def __init__(self, supabase: Client):
        super().__init__(supabase, "scraped_data", ScrapedData)

    async def get_by_url(self, url: str) -> Optional[ScrapedData]:
        """Get scraped data by URL"""
        result = await self.supabase.table(self.table_name).select("*").eq("url", url).order("scraped_at", desc=True).limit(1).execute()
        return ScrapedData.from_dict(result.data[0]) if result.data else None

    async def get_latest_by_product(self, product_id: int) -> Optional[ScrapedData]:
        """Get latest scraped data for a product"""
        result = await self.supabase.table(self.table_name).select("*").eq("product_id", product_id).order("scraped_at", desc=True).limit(1).execute()
        return ScrapedData.from_dict(result.data[0]) if result.data else None

    async def get_price_history(self, product_id: int, days: int = 30) -> List[Tuple[datetime, float]]:
        """Get price history for a product"""
        start_date = datetime.now() - timedelta(days=days)
        result = await self.supabase.table(self.table_name).select("scraped_at, price").eq("product_id", product_id).gte("scraped_at", start_date.isoformat()).order("scraped_at").execute()
        return [(datetime.fromisoformat(item["scraped_at"]), item["price"]) for item in result.data if item["price"]]

    async def get_stock_history(self, product_id: int, days: int = 30) -> List[Tuple[datetime, List[Dict]]]:
        """Get stock info history for a product"""
        start_date = datetime.now() - timedelta(days=days)
        result = await self.supabase.table(self.table_name).select("scraped_at, stock_info").eq("product_id", product_id).gte("scraped_at", start_date.isoformat()).order("scraped_at").execute()
        return [(datetime.fromisoformat(item["scraped_at"]), item["stock_info"]) for item in result.data if item["stock_info"]]

    async def get_failed_scrapes(self, retailer_id: Optional[int] = None, days: int = 1) -> List[ScrapedData]:
        """Get failed scrapes for analysis"""
        start_date = datetime.now() - timedelta(days=days)
        query = self.supabase.table(self.table_name).select("*").eq("success", False).gte("scraped_at", start_date.isoformat())
        if retailer_id:
            query = query.eq("retailer_id", retailer_id)
        result = await query.execute()
        return [ScrapedData.from_dict(item) for item in result.data]

    async def get_price_changes(self, product_id: int, threshold_percent: float = 5.0) -> List[Tuple[datetime, float, float]]:
        """Get significant price changes for a product"""
        result = await self.supabase.table(self.table_name).select("*").eq("product_id", product_id).order("scraped_at").execute()
        changes = []
        last_price = None
        
        for item in result.data:
            current_price = item["price"]
            if current_price and last_price:
                change_percent = abs((current_price - last_price) / last_price * 100)
                if change_percent >= threshold_percent:
                    changes.append((
                        datetime.fromisoformat(item["scraped_at"]),
                        last_price,
                        current_price
                    ))
            last_price = current_price
        
        return changes

    async def get_competitor_prices(self, product_id: int) -> List[Tuple[str, float]]:
        """Get current prices from all retailers for a product"""
        result = await self.supabase.table(self.table_name).select("*").eq("product_id", product_id).order("scraped_at", desc=True).execute()
        
        # Group by retailer and get latest price
        retailer_prices = {}
        for item in result.data:
            retailer_id = item["retailer_id"]
            if retailer_id not in retailer_prices and item["price"]:
                retailer_prices[retailer_id] = item["price"]
        
        return list(retailer_prices.items()) 