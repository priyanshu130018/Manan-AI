from datetime import datetime
from typing import Generic
from typing import TypeVar

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=False,
        populate_by_name=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )


class ApiResponse(BaseSchema, Generic[T]):
    success: bool = Field(...)
    message: str = Field(...)
    data: T | None = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)