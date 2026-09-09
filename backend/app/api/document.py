from fastapi import APIRouter

from app.schemas.document import DocumentListResponse
from app.services.document_service import document_service

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


@router.get(
    "",
    response_model=DocumentListResponse,
)
async def list_documents() -> DocumentListResponse:
    return await document_service.list_documents()


@router.delete(
    "/{document_id}",
)
async def delete_document(
    document_id: str,
):
    return await document_service.delete_document(
        document_id,
    )