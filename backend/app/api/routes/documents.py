from fastapi import APIRouter, File, UploadFile, Depends, status
from fastapi.responses import RedirectResponse
from app.api.dependencies import get_document_service
from app.api.dependencies.auth import get_current_user
from app.models.entities.user import UserEntity
from app.services.document_service import DocumentService
from app.models.schemas.base import ApiResponse
from app.models.schemas.document import DocumentItem, UploadData

router = APIRouter(tags=["Documents"])


@router.post("/doc/upload", response_model=ApiResponse[UploadData])
async def upload_document(
    file: UploadFile = File(...),
    current_user: UserEntity = Depends(get_current_user),
    doc_svc: DocumentService = Depends(get_document_service),
) -> ApiResponse[UploadData]:
    doc = await doc_svc.ingest_document(file, user_id=current_user.id)
    return ApiResponse(
        success=True,
        message=f"'{doc.original_filename}' uploaded and indexed successfully.",
        data=UploadData(
            document_id=doc.document_id,
            filename=doc.original_filename,
            chunks=doc.chunk_count,
            page_count=doc.page_count,
            source_type=doc.source_type.value,
            status=doc.status.value,
            cloudinary_secure_url=doc.cloudinary_secure_url,
        ),
    )


@router.get("/doc", response_model=ApiResponse[list[DocumentItem]])
async def list_documents(
    current_user: UserEntity = Depends(get_current_user),
    doc_svc: DocumentService = Depends(get_document_service),
) -> ApiResponse[list[DocumentItem]]:
    docs = await doc_svc.list_documents(user_id=current_user.id)
    items = [
        DocumentItem(
            document_id=d.document_id,
            filename=d.original_filename,
            chunks=d.chunk_count,
            page_count=d.page_count,
            size_bytes=d.size_bytes,
            mime_type=d.mime_type,
            status=d.status.value,
            source_type=d.source_type.value,
            created_at=d.created_at,
            processing_error=d.processing_error,
            cloudinary_secure_url=d.cloudinary_secure_url,
        )
        for d in docs
    ]
    return ApiResponse(
        success=True,
        message=f"Retrieved {len(items)} documents.",
        data=items,
    )


@router.get("/doc/storage", response_model=ApiResponse[dict])
async def get_storage_stats(
    current_user: UserEntity = Depends(get_current_user),
    doc_svc: DocumentService = Depends(get_document_service),
):
    stats = await doc_svc.get_storage_usage(user_id=current_user.id)
    return ApiResponse(
        success=True,
        message="Storage statistics retrieved.",
        data=stats,
    )


@router.get("/doc/{document_id}/file")
async def get_document_file(
    document_id: str,
    current_user: UserEntity = Depends(get_current_user),
    doc_svc: DocumentService = Depends(get_document_service),
):
    """Securely deliver uploaded document file for the authenticated user via Cloudinary redirect."""
    delivery_url = await doc_svc.get_file_delivery_url(document_id, user_id=current_user.id)
    return RedirectResponse(
        url=delivery_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )


@router.get("/doc/{document_id}", response_model=ApiResponse[DocumentItem])
async def get_document(
    document_id: str,
    current_user: UserEntity = Depends(get_current_user),
    doc_svc: DocumentService = Depends(get_document_service),
):
    doc = await doc_svc.get_document(document_id, user_id=current_user.id)
    return ApiResponse(
        success=True,
        message="Document found.",
        data=DocumentItem(
            document_id=doc.document_id,
            filename=doc.original_filename,
            chunks=doc.chunk_count,
            page_count=doc.page_count,
            size_bytes=doc.size_bytes,
            mime_type=doc.mime_type,
            status=doc.status.value,
            source_type=doc.source_type.value,
            created_at=doc.created_at,
            processing_error=doc.processing_error,
            cloudinary_secure_url=doc.cloudinary_secure_url,
        ),
    )


@router.delete("/doc/{document_id}", response_model=ApiResponse[None])
async def delete_document(
    document_id: str,
    current_user: UserEntity = Depends(get_current_user),
    doc_svc: DocumentService = Depends(get_document_service),
):
    await doc_svc.delete_document(document_id, user_id=current_user.id)
    return ApiResponse(
        success=True,
        message="Document deleted successfully.",
        data=None,
    )
