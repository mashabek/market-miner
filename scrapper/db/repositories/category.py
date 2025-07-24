from typing import Optional, List
from supabase import AsyncClient
from scrapper.db.repositories import BaseRepository
from scrapper.db.models import CategoryData

class CategoryRepository(BaseRepository[CategoryData]):
    """Repository for category operations with ltree support"""

    def __init__(self, supabase: AsyncClient):
        super().__init__(supabase, "categories", CategoryData)

    async def get_by_path(self, path: str) -> Optional[CategoryData]:
        """Get category by ltree path"""
        result = await self.supabase.table(self.table_name).select("*").eq("path", path).execute()
        return CategoryData.from_dict(result.data[0]) if result.data else None

    async def get_children(self, parent_id: int) -> List[CategoryData]:
        """Get direct child categories"""
        result = await self.supabase.table(self.table_name).select("*").eq("parent_id", parent_id).execute()
        return [CategoryData.from_dict(item) for item in result.data]

    async def get_descendants(self, path: str) -> List[CategoryData]:
        """Get all descendant categories using ltree"""
        query = f"path <@ '{path}'"
        result = await self.supabase.table(self.table_name).select("*").filter("path", "neq", path).filter("path", "like", f"{path}.%").execute()
        return [CategoryData.from_dict(item) for item in result.data]

    async def get_ancestors(self, path: str) -> List[CategoryData]:
        """Get all ancestor categories using ltree"""
        query = f"path @> '{path}'"
        result = await self.supabase.table(self.table_name).select("*").filter("path", "neq", path).filter("path", "like", f"%.{path}").execute()
        return [CategoryData.from_dict(item) for item in result.data]

    async def get_siblings(self, category_id: int) -> List[CategoryData]:
        """Get sibling categories"""
        category = await self.get_by_id(category_id)
        if not category:
            return []
        result = await self.supabase.table(self.table_name).select("*").eq("parent_id", category.parent_id).neq("id", category_id).execute()
        return [CategoryData.from_dict(item) for item in result.data]

    async def get_root_categories(self) -> List[CategoryData]:
        """Get all root level categories"""
        result = await self.supabase.table(self.table_name).select("*").is_("parent_id", "null").execute()
        return [CategoryData.from_dict(item) for item in result.data]

    async def create(self, model: CategoryData) -> CategoryData:
        """Create a new category with proper path"""
        if model.parent_id:
            parent = await self.get_by_id(model.parent_id)
            if not parent:
                raise ValueError(f"Parent category with id {model.parent_id} not found")
            model.path = f"{parent.path}.{model.id}" if model.id else parent.path
        else:
            model.path = str(model.id) if model.id else None
        
        return await super().create(model)

    async def update(self, model: CategoryData) -> CategoryData:
        """Update category with path recalculation if parent changed"""
        if not model.id:
            raise ValueError("Category ID is required for update")

        current = await self.get_by_id(model.id)
        if not current:
            raise ValueError(f"Category with id {model.id} not found")

        # Recalculate path if parent changed
        if current.parent_id != model.parent_id:
            if model.parent_id:
                parent = await self.get_by_id(model.parent_id)
                if not parent:
                    raise ValueError(f"Parent category with id {model.parent_id} not found")
                model.path = f"{parent.path}.{model.id}"
            else:
                model.path = str(model.id)

            # Update paths of all descendants
            descendants = await self.get_descendants(current.path)
            for descendant in descendants:
                descendant.path = descendant.path.replace(current.path, model.path)
                await super().update(descendant)

        return await super().update(model) 