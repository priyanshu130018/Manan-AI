from typing import List, Optional, Tuple
from app.core.config import get_settings
from app.core.logging import LoggerFactory
from app.integrations.gemini.client import GeminiClient
import chromadb
from chromadb.config import Settings as ChromaSettings

logger = LoggerFactory.create_logger("RAGService")

class RAGService:
    def __init__(self):
        self.settings = get_settings()
        self.gemini_client = GeminiClient()
        self.chroma_client = chromadb.PersistentClient(
            path=self.settings.chroma_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.settings.chroma_collection
        )

    async def retrieve(
        self,
        query: str,
        document_ids: Optional[List[str]] = None,
        top_k: int = 4,
    ) -> List[dict]:
        if not document_ids:
            return []

        where_clause = None
        if len(document_ids) == 1:
            where_clause = {"document_id": document_ids[0]}
        elif len(document_ids) > 1:
            where_clause = {"$or": [{"document_id": did} for did in document_ids]}

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(top_k, 10),
                where=where_clause,
            )
        except Exception as e:
            logger.error("Chroma retrieval error: %s", e)
            return []

        chunks = []
        if results and results.get("documents"):
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results.get("metadatas") else []
            for i, text in enumerate(docs):
                meta = metas[i] if i < len(metas) else {}
                chunks.append({
                    "text": text,
                    "filename": meta.get("filename", "document"),
                    "page_number": meta.get("page_number", 1),
                    "document_id": meta.get("document_id", ""),
                })
        return chunks

    async def generate_rag_response(
        self,
        prompt: str,
        history: List[dict],
        document_ids: Optional[List[str]] = None,
        summary: Optional[str] = None,
    ) -> Tuple[str, List[dict]]:
        citations = []
        context_text = ""

        if document_ids:
            retrieved = await self.retrieve(prompt, document_ids)
            if retrieved:
                context_blocks = []
                for i, c in enumerate(retrieved):
                    context_blocks.append(f"[{i+1}] From {c['filename']} (Page {c['page_number']}):\n{c['text']}")
                    citations.append({
                        "id": str(i + 1),
                        "filename": c["filename"],
                        "page_number": c["page_number"],
                        "snippet": c["text"][:200],
                    })
                context_text = "\n\n".join(context_blocks)

        system_instruction = "You are Manan AI, a helpful, clear, and insightful AI assistant."
        if context_text:
            system_instruction += (
                "\n\nRelevant Document Context:\n"
                f"{context_text}\n\n"
                "Use the provided context to answer the question accurately. If the context doesn't contain the answer, say so while answering to the best of your knowledge."
            )
        if summary:
            system_instruction += f"\n\nConversation Summary so far:\n{summary}"

        response_text = await self.gemini_client.generate(
            prompt=prompt,
            history=history,
            system_instruction=system_instruction,
        )
        return response_text, citations
