from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class ApiResponse(BaseSchema, Generic[T]):
    success: bool
    message: str = "Operation successful"
    data: T
