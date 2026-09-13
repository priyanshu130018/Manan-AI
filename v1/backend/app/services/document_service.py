from __future__ import annotations
import os
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import (
    DocumentNotFoundError,
    DocumentProcessingError,
    DocumentValidationError,
)
from app.core.logging import LoggerFactory
from app.integrations.documents.parsers import detect_source_type, get_parser
from app.integrations.documents.splitter import StructurePreservingSplitter
from app.integrations.embeddings import LocalEmbedding
from app.integrations.gemini.client import GeminiEmbedding
from app.integrations.storage.local_storage import LocalStorage
from app.models.entities.document import DocumentEntity
from app.models.entities.enums import DocumentStatus
from app.repositories.document_repository import DocumentRepository
from app.repositories.vector_repository import VectorRepository

logger = LoggerFactory.create_logger("DocumentService")

class DocumentService:
    def __init__(
        self,
        doc_repo: DocumentRepository | None = None,
        vector_repo: VectorRepository | None = None,
        storage: LocalStorage | None = None,
        embedding: object | None = None,
    ) -> None:
        self._settings = get_settings()
        self._doc_repo = doc_repo or DocumentRepository()
        self._vector_repo = vector_repo or VectorRepository()
        self._storage = storage or LocalStorage()

        provider = (self._settings.embedding_provider or "local").lower().strip()
        if embedding is not None:
            self._embedding = embedding
            self._embedding_provider = "custom"
        elif provider == "google":
            logger.info("Embedding provider: Google (%s)", self._settings.embedding_model)
            self._embedding = GeminiEmbedding()
            self._embedding_provider = "google"
        else:
            logger.info("Embedding provider: local (%s)", self._settings.embedding_model)
            self._embedding = LocalEmbedding()
            self._embedding_provider = "local"

        self._splitter = StructurePreservingSplitter(
            chunk_size=self._settings.chunk_size,
            chunk_overlap=self._settings.chunk_overlap,
        )

    async def ingest_document(self, file: UploadFile) -> DocumentEntity:
        if not file.filename:
            raise DocumentValidationError("No filename provided in upload.")

        original_name = Path(file.filename).name.strip()
        source_type = detect_source_type(original_name)

        doc_id = str(uuid.uuid4())
        ext = Path(original_name).suffix
        stored_filename = f"{doc_id}{ext}"
        target_path = self._storage.get_target_path(stored_filename)

        max_bytes = self._settings.max_upload_size_mb * 1024 * 1024
        total_storage_limit_bytes = self._settings.total_storage_limit_mb * 1024 * 1024
        current_used_bytes = await self._doc_repo.get_total_storage_bytes()

        # Step 1: Save file
        logger.info("[1/4] Saving '%s' to %s", original_name, target_path)
        total_bytes = 0
        try:
            with open(target_path, "wb") as f:
                while chunk := await file.read(256 * 1024):
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        raise DocumentValidationError(
                            f"File too large. Maximum allowed file size is {self._settings.max_upload_size_mb} MB."
                        )
                    if current_used_bytes + total_bytes > total_storage_limit_bytes:
                        raise DocumentValidationError(
                            f"Storage limit reached ({self._settings.total_storage_limit_mb} MB)."
                        )
                    f.write(chunk)
        except Exception as e:
            self._storage.delete_file(stored_filename)
            if isinstance(e, DocumentValidationError):
                raise
            raise DocumentProcessingError(f"Failed to save uploaded file: {e}")

        doc_entity = DocumentEntity(
            document_id=doc_id,
            original_filename=original_name,
            stored_filename=stored_filename,
            mime_type=file.content_type or "application/octet-stream",
            size_bytes=total_bytes,
            status=DocumentStatus.PROCESSING,
            source_type=source_type,
        )
        await self._doc_repo.create(doc_entity)

        try:
            # Step 2: Parse pages
            logger.info("[2/4] Parsing pages (provider=%s)", source_type.value)
            parser = get_parser(source_type)
            parsed_pages = parser.parse_file(str(target_path))
            if not parsed_pages or not any(getattr(p, "text", "").strip() for p in parsed_pages):
                raise DocumentProcessingError(
                    f"'{original_name}' has no readable text."
                )

            # Step 3: Chunk text
            logger.info("[3/4] Chunking text and generating vectors.")
            chunks = self._splitter.split_document(
                document_id=doc_id,
                filename=original_name,
                source_type=source_type.value,
                pages=parsed_pages,
            )
            if not chunks:
                raise DocumentProcessingError(f"No text chunks could be generated for '{original_name}'.")

            chunk_texts = [c.text for c in chunks]
            if hasattr(self._embedding, "embed_batch"):
                embeddings = await self._embedding.embed_batch(chunk_texts)
            else:
                embeddings = [await self._embedding.embed(t) for t in chunk_texts]

            # Step 4: Save to Chroma
            logger.info("[4/4] Saving %d vectors to ChromaDB.", len(embeddings))
            ids = [c.chunk_id for c in chunks]
            metadatas = [
                {
                    "document_id": doc_id,
                    "filename": original_name,
                    "page": int(c.page_number or 0),
                    "chunk": int(c.chunk_index or i),
                    "source_type": source_type.value,
                    "heading": (c.heading or "")[:200],
                }
                for i, c in enumerate(chunks)
            ]
            await self._vector_repo.add(
                ids=ids,
                documents=chunk_texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )

            doc_entity.status = DocumentStatus.READY
            doc_entity.page_count = len(parsed_pages)
            doc_entity.chunk_count = len(chunks)
            await self._doc_repo.update(doc_entity)
            return doc_entity

        except Exception as e:
            logger.exception("Ingest failed for '%s': %s", original_name, e)
            doc_entity.status = DocumentStatus.FAILED
            doc_entity.processing_error = str(e)
            try:
                await self._doc_repo.update(doc_entity)
            except Exception:
                pass
            raise DocumentProcessingError(f"Processing failed: {e}")

    async def list_documents(self) -> list[DocumentEntity]:
        return await self._doc_repo.list_all()

    async def get_document(self, document_id: str) -> DocumentEntity:
        doc = await self._doc_repo.get_by_id(document_id)
        if not doc:
            raise DocumentNotFoundError(document_id)
        return doc

    async def delete_document(self, document_id: str) -> None:
        doc = await self._doc_repo.get_by_id(document_id)
        if doc:
            self._storage.delete_file(doc.stored_filename)
            await self._doc_repo.delete(document_id)
            await self._vector_repo.delete_document(document_id)

    async def get_file_path(self, document_id: str) -> Path:
        doc = await self.get_document(document_id)
        path = self._storage.get_target_path(doc.stored_filename)
        if not path.exists():
            raise DocumentNotFoundError(f"File for document {document_id} not found on disk.")
        return path

    async def get_storage_usage(self) -> dict:
        used_bytes = await self._doc_repo.get_total_storage_bytes()
        limit_bytes = self._settings.total_storage_limit_mb * 1024 * 1024
        used_mb = round(used_bytes / (1024 * 1024), 2)
        limit_mb = self._settings.total_storage_limit_mb
        percent = min(100, round((used_bytes / limit_bytes) * 100, 1)) if limit_bytes > 0 else 0
        return {
            "used_bytes": used_bytes,
            "limit_bytes": limit_bytes,
            "used_mb": used_mb,
            "limit_mb": limit_mb,
            "usage_percent": percent,
        }
