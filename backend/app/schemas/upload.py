from app.schemas.base import ApiResponse
from app.schemas.base import BaseSchema


class UploadData(BaseSchema):
    document_id: str
    filename: str
    chunks: int


class UploadResponse(ApiResponse[UploadData]):
    pass