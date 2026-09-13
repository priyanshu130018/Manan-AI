import os
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.responses import FileResponse
from app.api.dependencies import get_document_service
from app.services.document_service import DocumentService
from app.models.schemas.base import ApiResponse
from app.models.schemas.document import DocumentSchema, StorageStatsSchema

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.get("", response_model=ApiResponse[list[DocumentSchema]])
async def list_documents(
    doc_service: DocumentService = Depends(get_document_service),
):
    docs = await doc_service.list_documents()
    return ApiResponse(
        success=True,
        message="Documents retrieved.",
        data=[
            DocumentSchema(
                id=d.id,
                filename=d.filename,
                file_type=d.file_type,
                file_size=d.file_size,
                page_count=d.page_count,
                chunk_count=d.chunk_count,
                created_at=d.created_at,
            )
            for d in docs
        ],
    )

@router.post("/upload", response_model=ApiResponse[DocumentSchema])
async def upload_document(
    file: UploadFile = File(...),
    doc_service: DocumentService = Depends(get_document_service),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing.")
    doc = await doc_service.ingest_document(file)
    return ApiResponse(
        success=True,
        message="Document uploaded and processed successfully.",
        data=DocumentSchema(
            id=doc.id,
            filename=doc.filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            page_count=doc.page_count,
            chunk_count=doc.chunk_count,
            created_at=doc.created_at,
        ),
    )

@router.get("/storage", response_model=ApiResponse[StorageStatsSchema])
async def get_storage_stats(
    doc_service: DocumentService = Depends(get_document_service),
):
    stats = await doc_service.get_storage_usage()
    return ApiResponse(
        success=True,
        message="Storage stats loaded.",
        data=StorageStatsSchema(
            total_documents=stats.get("total_documents", 0),
            total_storage_bytes=stats.get("used_bytes", 0),
            total_storage_mb=stats.get("used_mb", 0.0),
            max_storage_mb=stats.get("limit_mb", 500),
        ),
    )

@router.get("/{document_id}", response_model=ApiResponse[DocumentSchema])
async def get_document(
    document_id: str,
    doc_service: DocumentService = Depends(get_document_service),
):
    doc = await doc_service.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return ApiResponse(
        success=True,
        message="Document loaded.",
        data=DocumentSchema(
            id=doc.id,
            filename=doc.filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            page_count=doc.page_count,
            chunk_count=doc.chunk_count,
            created_at=doc.created_at,
        ),
    )

@router.get("/{document_id}/file")
async def get_document_file(
    document_id: str,
    doc_service: DocumentService = Depends(get_document_service),
):
    doc = await doc_service.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    file_path = os.path.join(doc_service.settings.documents_dir, doc.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk.")
    return FileResponse(file_path, filename=doc.filename)

@router.delete("/{document_id}", response_model=ApiResponse[None])
async def delete_document(
    document_id: str,
    doc_service: DocumentService = Depends(get_document_service),
):
    await doc_service.delete_document(document_id)
    return ApiResponse(
        success=True,
        message="Document deleted.",
        data=None,
    )
