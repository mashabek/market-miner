from dataclasses import dataclass
from typing import Optional
from scrapper.db.models.base import BaseModel

@dataclass(kw_only=True)
class CategoryData(BaseModel):
    """Data model for categories"""
    name: str
    parent_id: Optional[int] = None
    path: Optional[str] = None

    def get_path_labels(self) -> list[str]:
        """Get category path as list of labels"""
        return self.path.split('.') if self.path else []

    def get_depth(self) -> int:
        """Get category depth in the tree"""
        return len(self.get_path_labels())

    def is_root(self) -> bool:
        """Check if category is root level"""
        return self.parent_id is None

    def is_child_of(self, potential_parent_path: str) -> bool:
        """Check if category is child of given parent path"""
        if not self.path or not potential_parent_path:
            return False
        return self.path.startswith(f"{potential_parent_path}.") 