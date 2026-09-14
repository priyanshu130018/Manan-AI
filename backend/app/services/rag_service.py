from typing import List, Optional, Tuple, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import get_settings
from app.core.exceptions import AIServiceError, LLMError
from app.core.logging import LoggerFactory
from app.integrations.llm.factory import LLMFactory
from app.services.retrieval_service import RetrievalService
from app.utils.normalization import normalize_llm_response

logger = LoggerFactory.create_logger("RAGService")


class RAGService:
    def __init__(self, retrieval_service: Optional[RetrievalService] = None):
        self.settings = get_settings()
        self.retrieval_service = retrieval_service or RetrievalService()

    async def retrieve(
        self,
        query: str,
        document_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        top_k: int = 5,
    ) -> List[dict]:
        if not document_ids:
            return []

        try:
            chunks = await self.retrieval_service.hybrid_retrieve(
                query=query,
                document_ids=document_ids,
                user_id=user_id,
                top_k=top_k,
            )
            return [
                {
                    "text": c.text,
                    "filename": c.filename,
                    "page_number": c.page_number,
                    "chunk_index": c.chunk_index,
                    "source_type": getattr(c, "source_type", "pdf"),
                    "heading": getattr(c, "heading", None),
                    "document_id": c.document_id,
                    "score": getattr(c, "score", 0.0),
                }
                for c in chunks
            ]
        except Exception as e:
            logger.error("Hybrid retrieval error: %s", e)
            return []

    async def generate_response(
        self,
        prompt: str,
        history: List[dict],
        document_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        memories: Optional[List[str]] = None,
        summary: Optional[str] = None,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> Tuple[str, List[dict]]:
        citations = []
        context_text = ""

        if document_ids:
            retrieved = await self.retrieve(prompt, document_ids=document_ids, user_id=user_id, top_k=5)
            if retrieved:
                context_blocks = []
                for i, c in enumerate(retrieved):
                    stype = (c.get("source_type") or "pdf").lower()
                    page_val = c.get("page_number") if stype == "pdf" or (c.get("page_number") and c.get("page_number") > 0) else None
                    chunk_idx = c.get("chunk_index", 1)
                    row_range = f"Rows {(chunk_idx-1)*20+1}-{chunk_idx*20}" if stype in ["csv", "excel"] else None
                    table_context = c.get("heading") if stype in ["sql", "table"] and c.get("heading") else None

                    context_blocks.append(f"[{i+1}] From {c['filename']} ({stype.upper()}):\n{c['text']}")
                    citations.append({
                        "id": f"cit-{i+1}",
                        "document_id": c.get("document_id", ""),
                        "filename": c["filename"],
                        "page_number": page_val,
                        "page": page_val,
                        "chunk_index": chunk_idx,
                        "source_type": stype,
                        "row_range": row_range,
                        "table_context": table_context,
                        "retrieval_method": "Hybrid Search (Dense + FTS + RRF)",
                        "score": round(c.get("score", 0.0), 4) if c.get("score") else None,
                        "snippet": c["text"][:250],
                    })
                context_text = "\n\n".join(context_blocks)

        system_instruction = "You are Manan AI, an advanced, intelligent, and thoughtful AI assistant."
        if memories:
            mem_block = "\n".join(f"- {m}" for m in memories)
            system_instruction += f"\n\nUser Long-Term Preferences & Memories:\n{mem_block}"

        if context_text:
            system_instruction += (
                "\n\nRelevant Document Context:\n"
                f"{context_text}\n\n"
                "Use the provided context to answer the question accurately with citations."
            )
        if summary:
            system_instruction += f"\n\nConversation Summary so far:\n{summary}"

        # Initialize explicit provider chat model (NO silent cross-provider fallback)
        chat_model = LLMFactory.get_chat_model(provider=provider, model_name=model_name)

        messages = [("system", system_instruction)]
        for h in history:
            role = "human" if h["role"] == "user" else "ai"
            messages.append((role, h["content"]))
        messages.append(("human", prompt))

        try:
            chain = ChatPromptTemplate.from_messages(messages) | chat_model
            res = await chain.ainvoke({})
            content = normalize_llm_response(res)
            return content, citations
        except Exception as e:
            prov = provider or self.settings.llm_provider
            logger.error("LLM execution error with provider '%s': %s", prov, e)
            raise LLMError(f"LLM execution failed for provider '{prov}': {e}", provider=prov) from e
