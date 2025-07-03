from typing import Optional, List, Dict
from datetime import datetime, timedelta
from supabase import Client

from scrapper.db.models import ProductData
from scrapper.db.models import ScrapedData
from scrapper.db.models import CategoryData
from scrapper.db.models import RetailerData
from scrapper.db.models import RetailerType
from scrapper.db.models import AvailabilityKeyword

from scrapper.db.repositories import ProductRepository
from scrapper.db.repositories import ScrapedDataRepository
from scrapper.db.repositories import CategoryRepository
from scrapper.db.repositories import RetailerRepository
from scrapper.db.repositories import AvailabilityKeywordRepository
from scrapper.items import ProductItem

class ScrapingService:
    """Service for coordinating scraping operations and data processing"""

    def __init__(self, supabase: Client):
        self.product_repo = ProductRepository(supabase)
        self.scraped_data_repo = ScrapedDataRepository(supabase)
        self.category_repo = CategoryRepository(supabase)
        self.retailer_repo = RetailerRepository(supabase)
        self.availability_keyword_repo = AvailabilityKeywordRepository(supabase)

    async def process_scraped_item(self, item: ProductItem, retailer_id: int) -> ScrapedData:
        """Process a scraped item and save to database"""
        # Create scraped data entry
        scraped_data = ScrapedData.from_scraped_item(item, retailer_id)
        
        # Process availability keyword if present
        if 'stock_status' in item and isinstance(item['stock_status'], str):
            await self._process_availability_keyword(retailer_id, item['stock_status'])
        
        # Try to find existing product
        product = await self._find_or_create_product(item)
        if product:
            scraped_data.product_id = product.id
        
        # Try to resolve category
        if item.get('category'):
            category = await self._find_or_create_category(item['category'])
            if category:
                scraped_data.category_id = category.id
                if product:
                    await self.product_repo.update_category(product.id, category.id)
        
        # Save scraped data
        return await self.scraped_data_repo.create(scraped_data)

    async def _process_availability_keyword(self, retailer_id: int, status_text: str) -> None:
        """Process and store availability keyword."""
        # Clean and normalize the keyword
        keyword = status_text.strip()
        if not keyword:
            return

        try:
            # Check if keyword exists
            existing = await self.availability_keyword_repo.get_by_retailer_and_keyword(retailer_id, keyword)
            
            if not existing:
                # Create new keyword entry
                new_keyword = AvailabilityKeyword(
                    retailer_id=retailer_id,
                    keyword=keyword,
                    # Language could be detected here if needed
                    language=None,
                    indicates_in_stock=None  # Will be configured manually
                )
                await self.availability_keyword_repo.create(new_keyword)
        except Exception as e:
            # Log error but don't fail the entire process
            pass

    async def _find_or_create_product(self, item: ProductItem) -> Optional[ProductData]:
        """Find existing product or create new one"""
        product_name = item['product_name']
        brand = item.get('specs', {}).get('brand')
        
        # Try to find by name and brand
        product = await self.product_repo.get_by_name_and_brand(product_name, brand)
        if product:
            return product
        
        # Create new product
        new_product = ProductData.from_scraped_item(item)
        return await self.product_repo.create(new_product)

    async def _find_or_create_category(self, category_path: str) -> Optional[CategoryData]:
        """Find or create category from path string"""
        # Split path into hierarchy
        categories = [c.strip() for c in category_path.split('>')]
        if not categories:
            return None
        
        current_path = []
        parent_id = None
        last_category = None
        
        for category_name in categories:
            current_path.append(str(hash(category_name) % 1000000))  # Simple path generation
            path = '.'.join(current_path)
            
            # Try to find existing category
            category = await self.category_repo.get_by_path(path)
            if not category:
                # Create new category
                category = CategoryData(
                    name=category_name,
                    parent_id=parent_id,
                    path=path
                )
                category = await self.category_repo.create(category)
            
            parent_id = category.id
            last_category = category
        
        return last_category

    async def get_product_price_analytics(self, product_id: int) -> Dict:
        """Get comprehensive price analytics for a product"""
        # Get price history
        price_history = await self.scraped_data_repo.get_price_history(product_id)
        
        # Get significant price changes
        price_changes = await self.scraped_data_repo.get_price_changes(product_id)
        
        # Get competitor prices
        competitor_prices = await self.scraped_data_repo.get_competitor_prices(product_id)
        
        # Calculate analytics
        if price_history:
            current_price = price_history[-1][1]
            min_price = min(price for _, price in price_history)
            max_price = max(price for _, price in price_history)
            avg_price = sum(price for _, price in price_history) / len(price_history)
        else:
            current_price = min_price = max_price = avg_price = None
        
        return {
            "current_price": current_price,
            "min_price": min_price,
            "max_price": max_price,
            "avg_price": avg_price,
            "price_history": price_history,
            "significant_changes": price_changes,
            "competitor_prices": competitor_prices
        }

    async def get_retailer_performance(self, retailer_id: int, days: int = 30) -> Dict:
        """Get scraping performance metrics for a retailer"""
        # Get failed scrapes
        failed_scrapes = await self.scraped_data_repo.get_failed_scrapes(retailer_id, days)
        
        # Get all scrapes for the period
        start_date = datetime.now() - timedelta(days=days)
        all_scrapes = await self.scraped_data_repo.find_by(
            retailer_id=retailer_id,
            scraped_at={"gte": start_date.isoformat()}
        )
        
        total_scrapes = len(all_scrapes)
        failed_count = len(failed_scrapes)
        success_rate = (total_scrapes - failed_count) / total_scrapes if total_scrapes > 0 else 0
        
        return {
            "total_scrapes": total_scrapes,
            "failed_scrapes": failed_count,
            "success_rate": success_rate,
            "recent_failures": [
                {
                    "url": scrape.url,
                    "error": scrape.error_info,
                    "timestamp": scrape.scraped_at
                }
                for scrape in failed_scrapes[-5:]  # Last 5 failures
            ]
        } 