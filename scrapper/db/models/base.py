from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass(kw_only=True)
class BaseModel:
    """Base model with common fields for all models"""
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            key: self._format_datetime(value) if isinstance(value, datetime) else value
            for key, value in self.__dict__.items()
            if value is not None
        }

    def _format_datetime(self, dt: datetime) -> str:
        """Format datetime to ISO format"""
        try:
            return dt.isoformat()
        except Exception:
            # Fallback for non-standard datetime formats
            return str(dt)

    @classmethod
    def from_dict(cls, data: dict) -> 'BaseModel':
        """Create model instance from dictionary"""
        # Convert string dates to datetime objects
        if 'created_at' in data and isinstance(data['created_at'], str):
            try:
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            except ValueError:
                # Try to parse non-ISO format
                try:
                    data['created_at'] = datetime.strptime(data['created_at'], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    # Keep as string if parsing fails
                    pass
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            try:
                data['updated_at'] = datetime.fromisoformat(data['updated_at'])
            except ValueError:
                # Try to parse non-ISO format
                try:
                    data['updated_at'] = datetime.strptime(data['updated_at'], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    # Keep as string if parsing fails
                    pass
        return cls(**data) 