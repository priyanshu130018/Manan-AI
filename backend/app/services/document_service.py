from app.ai.vector_store.factory import VectorStoreFactory
from app.schemas.base import ApiResponse
from app.schemas.document import Document
from app.schemas.document import DocumentListResponse
from app.services.base_service import BaseService


class DocumentService(BaseService):
    def __init__(
        self,
    ) -> None:
        super().__init__()

        self._vector_store = (
            VectorStoreFactory.get_vector_store()
        )

    async def list_documents(
        self,
    ) -> DocumentListResponse:
        documents = (
            await self._vector_store.list_documents()
        )

        return DocumentListResponse(
            success=True,
            data=[
                Document(**document)
                for document in documents
            ],
        )

    async def delete_document(
        self,
        document_id: str,
    ) -> ApiResponse[None]:
        await self._vector_store.delete_document(
            document_id=document_id,
        )

        return ApiResponse(
            success=True,
            message="Document deleted successfully.",
            data=None,
        )


document_service = DocumentService()