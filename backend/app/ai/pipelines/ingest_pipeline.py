import uuid
from pathlib import Path

from app.ai.embeddings.factory import EmbeddingFactory
from app.ai.ingestion.loader import PDFLoader
from app.ai.ingestion.parser import Parser
from app.ai.ingestion.splitter import TextSplitter
from app.ai.vector_store.factory import VectorStoreFactory


class IngestPipeline:
    def __init__(
        self,
    ) -> None:
        self._loader = PDFLoader()
        self._parser = Parser()
        self._splitter = TextSplitter()

        self._embedding = (
            EmbeddingFactory.get_embedding()
        )

        self._vector_store = (
            VectorStoreFactory.get_vector_store()
        )

    async def run(
        self,
        file_path: str,
    ) -> dict:
        document_id = str(uuid.uuid4())
        filename = Path(file_path).name

        text = self._loader.load(
            file_path,
        )

        text = self._parser.parse(
            text,
        )

        chunks = self._splitter.split(
            text,
        )

        embeddings: list[list[float]] = []

        for chunk in chunks:
            embedding = await self._embedding.embed(
                chunk,
            )

            embeddings.append(
                embedding,
            )

        ids = [
            str(uuid.uuid4())
            for _ in chunks
        ]

        metadatas = [
            {
                "document_id": document_id,
                "filename": filename,
                "chunk": index,
            }
            for index, _ in enumerate(chunks)
        ]

        await self._vector_store.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        return {
            "document_id": document_id,
            "filename": filename,
            "chunks": len(chunks),
        }