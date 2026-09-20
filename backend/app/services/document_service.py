"""Document ingestion and lifecycle service using Cloudinary cloud storage and PostgreSQL pgvector."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import (
    DocumentNotFoundError,
    DocumentProcessingError,
    DocumentValidationError,
    EmbeddingError,
)
from app.core.logging import LoggerFactory
from app.integrations.documents.parsers import detect_source_type, get_parser
from app.integrations.documents.splitter import StructurePreservingSplitter
from app.integrations.embeddings import HuggingFaceEmbedding
from app.integrations.gemini.client import GeminiEmbedding
from app.integrations.storage.cloudinary_storage import CloudinaryStorage
from app.models.entities.document import DocumentEntity
from app.models.entities.enums import DocumentStatus
from app.repositories.document_repository import DocumentRepository
from app.repositories.vector_repository import VectorRepository

logger = LoggerFactory.create_logger("DocumentService")


class DocumentService:
    def __init__(
        self,
        doc_repo: Optional[DocumentRepository] = None,
        vector_repo: Optional[VectorRepository] = None,
        cloudinary_storage: Optional[CloudinaryStorage] = None,
        embedding: Optional[object] = None,
    ) -> None:
        self._settings = get_settings()
        self._doc_repo = doc_repo or DocumentRepository()
        self._vector_repo = vector_repo or VectorRepository()
        self._cloudinary = cloudinary_storage or CloudinaryStorage()

        provider = (self._settings.embedding_provider or "huggingface").lower().strip()
        if embedding is not None:
            self._embedding = embedding
            self._embedding_provider = "custom"
        elif provider in ["huggingface", "hf"]:
            logger.info("Embedding provider: huggingface (%s)", self._settings.embedding_model)
            self._embedding = HuggingFaceEmbedding()
            self._embedding_provider = "huggingface"
        elif provider in ["google", "gemini"]:
            logger.info("Embedding provider: Google (%s)", self._settings.embedding_model)
            self._embedding = GeminiEmbedding()
            self._embedding_provider = "google"
        else:
            raise EmbeddingError(
                f"Unsupported embedding provider '{self._settings.embedding_provider}'. Supported providers are: 'huggingface', 'google'"
            )

        self._splitter = StructurePreservingSplitter(
            chunk_size=self._settings.chunk_size,
            chunk_overlap=self._settings.chunk_overlap,
        )

    async def ingest_document(self, file: UploadFile, user_id: str | None = None) -> DocumentEntity:
        if not user_id:
            raise ValueError("user_id is required for document ingestion")
        if not file.filename:
            raise DocumentValidationError("No filename provided in upload.")

        original_name = Path(file.filename).name.strip()
        source_type = detect_source_type(original_name)

        doc_id = str(uuid.uuid4())
        ext = Path(original_name).suffix
        stored_filename = f"{doc_id}{ext}"

        max_bytes = self._settings.max_upload_size_mb * 1024 * 1024
        total_storage_limit_bytes = self._settings.total_storage_limit_mb * 1024 * 1024
        current_used_bytes = await self._doc_repo.get_total_storage_bytes(user_id=user_id)

        # Create temporary file for initial upload & parsing
        temp_dir = Path(tempfile.gettempdir())
        temp_file_path = temp_dir / f"manan_upload_{doc_id}{ext}"

        total_bytes = 0
        try:
            with open(temp_file_path, "wb") as f:
                while chunk := await file.read(256 * 1024):
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        raise DocumentValidationError(
                            f"File too large. Maximum allowed file size is {self._settings.max_upload_size_mb} MB."
                        )
                    if current_used_bytes + total_bytes > total_storage_limit_bytes:
                        raise DocumentValidationError(
                            f"Storage limit reached. You cannot upload this document because it would exceed your available storage ({self._settings.total_storage_limit_mb} MB). Delete one or more existing documents and try again."
                        )
                    f.write(chunk)
        except Exception as e:
            if temp_file_path.exists():
                try:
                    temp_file_path.unlink()
                except Exception:
                    pass
            if isinstance(e, DocumentValidationError):
                raise
            raise DocumentProcessingError(f"Failed to read uploaded file: {e}")

        # --- Step 1: Upload original document to Cloudinary ---
        logger.info("[1/4] Uploading '%s' to Cloudinary for user '%s'", original_name, user_id)
        try:
            cloud_res = self._cloudinary.upload_file(
                file_obj=str(temp_file_path),
                filename=original_name,
                user_id=user_id,
                document_id=doc_id,
            )
        except Exception as e:
            if temp_file_path.exists():
                try:
                    temp_file_path.unlink()
                except Exception:
                    pass
            raise

        doc_entity = DocumentEntity(
            document_id=doc_id,
            user_id=user_id,
            original_filename=original_name,
            stored_filename=stored_filename,
            mime_type=file.content_type or "application/octet-stream",
            size_bytes=total_bytes,
            status=DocumentStatus.PROCESSING,
            source_type=source_type,
            cloudinary_public_id=cloud_res.get("cloudinary_public_id"),
            cloudinary_secure_url=cloud_res.get("cloudinary_secure_url"),
            cloudinary_resource_type=cloud_res.get("cloudinary_resource_type"),
        )
        await self._doc_repo.create(doc_entity)

        try:
            # --- Step 2: Parse pages from temporary spool ---
            logger.info("[2/4] Parsing pages (provider=%s)", source_type.value)
            parser = get_parser(source_type)
            parsed_pages = parser.parse_file(str(temp_file_path))
            if not parsed_pages or not any(getattr(p, "text", "").strip() for p in parsed_pages):
                raise DocumentProcessingError(
                    f"'{original_name}' has no readable text. It may be empty or OCR is required."
                )
            logger.info("Extracted %d page(s).", len(parsed_pages))

            # --- Step 3: Chunk text -> vectors ---
            logger.info("[3/4] Chunking text and generating vectors (%s embeddings).", self._embedding_provider)
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

            if len(embeddings) != len(chunks):
                raise DocumentProcessingError(
                    f"Embedding count mismatch: got {len(embeddings)} vectors for {len(chunks)} chunks."
                )

            # --- Step 4: Save vectors to PostgreSQL pgvector + FTS and mark READY ---
            logger.info("[4/4] Saving %d vectors to PostgreSQL pgvector for user '%s'.", len(embeddings), user_id)
            ids = [c.chunk_id for c in chunks]
            metadatas = [
                {
                    "document_id": doc_id,
                    "user_id": user_id,
                    "filename": original_name,
                    "page": int(c.page_number or 1),
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
                user_id=user_id,
            )

            # Index FTS chunks as well
            await self._doc_repo.index_chunks_fts(chunks, user_id=user_id)

            doc_entity.status = DocumentStatus.READY
            doc_entity.page_count = len(parsed_pages)
            doc_entity.chunk_count = len(chunks)
            await self._doc_repo.update(doc_entity)

            logger.info(
                "Successfully ingested '%s' — %d pages, %d chunks, provider=%s.",
                original_name,
                len(parsed_pages),
                len(chunks),
                self._embedding_provider,
            )
            return doc_entity

        except Exception as e:
            logger.exception("Ingest failed for '%s': %s. Rolling back Cloudinary asset.", original_name, e)
            # Cleanup Cloudinary asset if processing/indexing failed
            if doc_entity.cloudinary_public_id:
                try:
                    self._cloudinary.delete_file(
                        public_id=doc_entity.cloudinary_public_id,
                        resource_type=doc_entity.cloudinary_resource_type or "raw",
                    )
                except Exception as del_err:
                    logger.warning("Failed to destroy Cloudinary asset after ingest failure: %s", del_err)

            doc_entity.status = DocumentStatus.FAILED
            doc_entity.processing_error = str(e)
            try:
                await self._doc_repo.update(doc_entity)
            except Exception:
                pass
            raise DocumentProcessingError(f"Processing failed: {e}")

        finally:
            # Always clean up temporary file
            if temp_file_path.exists():
                try:
                    temp_file_path.unlink()
                except Exception:
                    pass

    async def list_documents(self, user_id: str | None = None) -> list[DocumentEntity]:
        return await self._doc_repo.list_all(user_id=user_id)

    async def get_document(self, document_id: str, user_id: str | None = None) -> DocumentEntity:
        doc = await self._doc_repo.get_by_id(document_id, user_id=user_id)
        if not doc:
            raise DocumentNotFoundError(document_id)
        return doc

    async def delete_document(self, document_id: str, user_id: str | None = None) -> None:
        doc = await self._doc_repo.get_by_id(document_id, user_id=user_id)
        if doc:
            if doc.cloudinary_public_id:
                self._cloudinary.delete_file(
                    public_id=doc.cloudinary_public_id,
                    resource_type=doc.cloudinary_resource_type or "raw",
                )
            await self._vector_repo.delete_document(document_id, user_id=user_id)
            await self._doc_repo.delete_chunks_fts(document_id, user_id=user_id)
            await self._doc_repo.delete(document_id, user_id=user_id)
            logger.info("Deleted document %s and associated pgvector chunks/Cloudinary files for user %s.", document_id, user_id)

    async def get_file_delivery_url(self, document_id: str, user_id: str | None = None) -> str:
        """Return secure Cloudinary delivery URL for document viewing/download."""
        doc = await self.get_document(document_id, user_id=user_id)
        if doc.cloudinary_secure_url:
            return doc.cloudinary_secure_url
        if doc.cloudinary_public_id:
            return self._cloudinary.get_secure_url(
                doc.cloudinary_public_id,
                resource_type=doc.cloudinary_resource_type or "raw",
            )
        raise DocumentNotFoundError(f"File for document {document_id} has no storage location.")

    async def get_storage_usage(self, user_id: str | None = None) -> dict:
        used_bytes = await self._doc_repo.get_total_storage_bytes(user_id=user_id)
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
