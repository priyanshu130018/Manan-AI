from app.ai.llm.factory import LLMFactory
from app.ai.memory.factory import MemoryFactory
from app.ai.memory.summarizer import ConversationSummarizer
from app.ai.prompts.rag_prompt import RAGPrompt
from app.ai.retrieval.citation_builder import CitationBuilder
from app.ai.retrieval.context_builder import ContextBuilder
from app.ai.retrieval.history_builder import HistoryBuilder
from app.ai.retrieval.query_rewriter import QueryRewriter
from app.ai.retrieval.retriever import Retriever
from app.schemas.chat import Citation


class QueryPipeline:
    def __init__(
        self,
    ) -> None:
        self._memory = MemoryFactory.get_memory()

        self._summarizer = (
            ConversationSummarizer()
        )

        self._retriever = Retriever()

        self._rewriter = QueryRewriter()

        self._context_builder = ContextBuilder()

        self._history_builder = HistoryBuilder()

        self._citation_builder = CitationBuilder()

        self._llm = LLMFactory.get_llm()

    async def run(
        self,
        session_id: str,
        question: str,
        filters: dict[str, str] | None = None,
    ) -> tuple[str, list[Citation]]:
        history = await self._memory.get_history(
            session_id=session_id,
        )

        summary = await self._memory.get_summary(
            session_id=session_id,
        )

        history_text = self._history_builder.build(
            summary=summary,
            history=history,
        )

        search_query = await self._rewriter.rewrite(
            question=question,
        )

        chunks = await self._retriever.retrieve(
            query=search_query,
            filters=filters,
        )

        context = self._context_builder.build(
            chunks=chunks,
        )

        citations = self._citation_builder.build(
            chunks=chunks,
        )

        prompt = RAGPrompt.build(
            history=history_text,
            context=context,
            question=question,
        )

        answer = await self._llm.generate(
            prompt,
        )

        await self._memory.add_message(
            session_id=session_id,
            role="user",
            content=question,
        )

        await self._memory.add_message(
            session_id=session_id,
            role="assistant",
            content=answer,
        )

        history = await self._memory.get_history(
            session_id=session_id,
        )

        if len(history) >= 20:
            summary = await self._summarizer.summarize(
                history=history[:-10],
            )

            await self._memory.save_summary(
                session_id=session_id,
                summary=summary,
            )

            await self._memory.trim_history(
                session_id=session_id,
                keep_last=10,
            )

        return (
            answer,
            citations,
        )