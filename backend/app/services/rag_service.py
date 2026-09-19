from typing import Optional, List, Tuple, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
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
                logger.info(
                    "RAG context retrieved: user_id='%s', document_ids=%s, chunks_retrieved=%d, provider='%s', model='%s'",
                    user_id or "anonymous",
                    document_ids,
                    len(retrieved),
                    provider or self.settings.llm_provider,
                    model_name or self.settings.llm_model,
                )
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
            else:
                logger.warning(
                    "RAG context empty: user_id='%s', requested document_ids=%s returned 0 matching chunks.",
                    user_id or "anonymous",
                    document_ids,
                )

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
        elif document_ids:
            system_instruction += (
                "\n\nNote: The user has selected document(s) for this conversation, but no matching context chunks could be retrieved from the index for this query."
            )
        if summary:
            system_instruction += f"\n\nConversation Summary so far:\n{summary}"

        # Initialize explicit provider chat model (NO silent cross-provider fallback)
        chat_model = LLMFactory.get_chat_model(provider=provider, model_name=model_name)


        lc_messages: list[BaseMessage] = [SystemMessage(content=system_instruction)]
        for h in history:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role in ["user", "human"]:
                lc_messages.append(HumanMessage(content=content))
            else:
                lc_messages.append(AIMessage(content=content))
        lc_messages.append(HumanMessage(content=prompt))

        try:
            res = await chat_model.ainvoke(lc_messages)
            content = normalize_llm_response(res)
            return content, citations
        except LLMError:
            raise
        except Exception as e:
            prov = provider or self.settings.llm_provider
            err_msg = str(e)
            logger.error("LLM execution error with provider '%s' (model='%s'): %s", prov, model_name, e)
            raise LLMError(f"LLM execution failed for provider '{prov}': {err_msg}", provider=prov, model=model_name) from e
