from typing import TypeVar, Generic, Optional, List, Type
from supabase import AsyncClient
from scrapper.db.models import BaseModel

T = TypeVar('T', bound=BaseModel)

class BaseRepository(Generic[T]):
    """Base repository with CRUD operations"""
    
    def __init__(self, supabase: AsyncClient, table_name: str, model_class: Type[T]):
        self.supabase = supabase
        self.table_name = table_name
        self.model_class = model_class

    async def create(self, model: T) -> T:
        """Create a new record"""
        data = model.to_dict()
        result = await self.supabase.table(self.table_name).insert(data).execute()
        return self.model_class.from_dict(result.data[0])

    async def get_by_id(self, id: int) -> Optional[T]:
        """Get record by ID"""
        result = await self.supabase.table(self.table_name).select("*").eq("id", id).execute()
        return self.model_class.from_dict(result.data[0]) if result.data else None

    async def update(self, model: T) -> T:
        """Update an existing record"""
        if not model.id:
            raise ValueError("Model ID is required for update")
        data = model.to_dict()
        result = await self.supabase.table(self.table_name).update(data).eq("id", model.id).execute()
        return self.model_class.from_dict(result.data[0])

    async def delete(self, id: int) -> bool:
        """Delete a record by ID"""
        result = await self.supabase.table(self.table_name).delete().eq("id", id).execute()
        return bool(result.data)

    async def list_all(self) -> List[T]:
        """Get all records"""
        result = await self.supabase.table(self.table_name).select("*").execute()
        return [self.model_class.from_dict(item) for item in result.data]

    async def find_by(self, **filters) -> List[T]:
        """Find records by filters"""
        query = self.supabase.table(self.table_name).select("*")
        for field, value in filters.items():
            query = query.eq(field, value)
        result = await query.execute()
        return [self.model_class.from_dict(item) for item in result.data]

    async def exists(self, **filters) -> bool:
        """Check if record exists with given filters"""
        query = self.supabase.table(self.table_name).select("id")
        for field, value in filters.items():
            query = query.eq(field, value)
        result = await query.execute()
        return bool(result.data) 