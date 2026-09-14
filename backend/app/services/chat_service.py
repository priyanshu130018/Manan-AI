import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

from app.core.exceptions import EntityNotFoundError, MananException
from app.core.logging import LoggerFactory
from app.models.entities.message import MessageEntity
from app.models.entities.session import SessionEntity
from app.models.entities.user import UserEntity
from app.models.schemas.chat import ChatRequest, ChatResponse, CitationSchema
from app.repositories.session_repository import SessionRepository
from app.repositories.memory_repository import MemoryRepository
from app.services.rag_service import RAGService
from app.utils.normalization import normalize_llm_response

logger = LoggerFactory.create_logger("ChatService")


class ChatService:
    def __init__(
        self,
        session_repo: Optional[SessionRepository] = None,
        memory_repo: Optional[MemoryRepository] = None,
        rag_service: Optional[RAGService] = None,
        memory_service: Optional[Any] = None,
    ):
        self.session_repo = session_repo or SessionRepository()
        self.memory_repo = memory_repo or MemoryRepository()
        self.rag_service = rag_service or RAGService()
        self.memory_service = memory_service

    async def _extract_and_save_facts(self, user_id: str, message: str, session_id: str) -> None:
        """Lightweight background extraction of user facts into long term memory."""
        # Detect clear user preference statements (e.g., 'my name is', 'i prefer', 'i like', 'remember that')
        msg_lower = message.lower()
        trigger_phrases = ["my name is ", "i am ", "i prefer ", "i like ", "remember that ", "my email is ", "i work at "]
        for tp in trigger_phrases:
            if tp in msg_lower:
                # Save as memory
                try:
                    await self.memory_repo.create_memory(
                        content=message.strip()[:500],
                        user_id=user_id,
                        source_session_id=session_id,
                    )
                except Exception as e:
                    logger.debug("Automatic memory extraction skipped: %s", e)
                break

    async def execute(self, request: ChatRequest, user: Optional[UserEntity] = None) -> ChatResponse:
        session_id = request.session_id or str(uuid.uuid4())
        is_temporary = bool(request.is_temporary)
        user_id = user.id if user else None

        # Provider and model resolution
        provider = request.provider or (user.preferred_provider if user else None)
        model = request.model or (user.preferred_model if user else None)

        session: Optional[SessionEntity] = None
        history_dicts = []
        summary: Optional[str] = None
        memories_list = []

        if not is_temporary:
            session = await self.session_repo.get_session(session_id, user_id=user_id)
            if not session:
                session = await self.session_repo.get_or_create_session(
                    session_id=session_id,
                    user_id=user_id,
                    title=request.message[:40] if request.message else "New Chat",
                    chat_number=request.chat_number,
                    is_temporary=False,
                )
            if request.selected_document_ids is not None:
                session.selected_document_ids = request.selected_document_ids
                await self.session_repo.update_session(session)

            user_msg = MessageEntity(
                id=str(uuid.uuid4()),
                session_id=session.id,
                role="user",
                content=request.message,
                created_at=datetime.now(timezone.utc),
            )
            await self.session_repo.add_message(user_msg)

            db_messages = await self.session_repo.get_messages(session.id)
            history_dicts = [
                {"role": m.role, "content": m.content}
                for m in db_messages[:-1]
            ]
            summary = await self.session_repo.get_summary(session.id)

            # Long term memory
            if user and user.long_term_memory_enabled:
                user_mems = await self.memory_repo.list_memories(user_id=user.id)
                memories_list = [m["content"] for m in user_mems]
                # Try extracting facts
                await self._extract_and_save_facts(user.id, request.message, session.id)
        else:
            if request.history:
                history_dicts = [
                    {"role": m.role, "content": m.content}
                    for m in request.history
                ]

        active_docs = request.selected_document_ids
        if active_docs is None and session:
            active_docs = session.selected_document_ids

        assistant_text, citations_data = await self.rag_service.generate_response(
            prompt=request.message,
            history=history_dicts,
            document_ids=active_docs,
            user_id=user_id,
            memories=memories_list,
            summary=summary,
            provider=provider,
            model_name=model,
        )
        assistant_text = normalize_llm_response(assistant_text)

        response_citations = [
            CitationSchema(
                id=c["id"],
                document_id=c.get("document_id", ""),
                filename=c["filename"],
                page_number=c["page_number"],
                snippet=c["snippet"],
            )
            for c in citations_data
        ]

        if not is_temporary and session:
            assistant_msg = MessageEntity(
                id=str(uuid.uuid4()),
                session_id=session.id,
                role="assistant",
                content=assistant_text,
                citations=[c.model_dump() for c in response_citations] if response_citations else None,
                model_used=model,
                provider_used=provider,
                created_at=datetime.now(timezone.utc),
            )
            await self.session_repo.add_message(assistant_msg)

        c_num = session.chat_number if (session and not is_temporary) else None
        return ChatResponse(
            response=assistant_text,
            session_id=session.id if (session and not is_temporary) else session_id,
            chat_number=c_num,
            chat_id=c_num,
            citations=response_citations,
        )

    async def edit_message_and_regenerate(
        self,
        message_id: str,
        new_content: str,
        user: UserEntity,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> ChatResponse:
        """Edits an existing user message, trims subsequent messages, and generates a fresh response."""
        target_msg = await self.session_repo.get_message(message_id)
        if not target_msg:
            raise EntityNotFoundError(f"Message '{message_id}' not found.")

        session = await self.session_repo.get_session(target_msg.session_id, user_id=user.id)
        if not session:
            raise EntityNotFoundError(f"Session not found or unauthorized.")

        # Update the message content
        await self.session_repo.update_message(message_id, new_content)

        # Delete all messages created after target message
        await self.session_repo.delete_messages_after(session.id, target_msg.created_at)

        # Re-fetch history up to this message
        all_msgs = await self.session_repo.get_messages(session.id)
        history_dicts = [
            {"role": m.role, "content": m.content}
            for m in all_msgs if m.id != message_id
        ]
        summary = await self.session_repo.get_summary(session.id)

        memories_list = []
        if user.long_term_memory_enabled:
            user_mems = await self.memory_repo.list_memories(user_id=user.id)
            memories_list = [m["content"] for m in user_mems]

        prov = provider or user.preferred_provider
        mdl = model or user.preferred_model

        assistant_text, citations_data = await self.rag_service.generate_response(
            prompt=new_content,
            history=history_dicts,
            document_ids=session.selected_document_ids,
            user_id=user.id,
            memories=memories_list,
            summary=summary,
            provider=prov,
            model_name=mdl,
        )
        assistant_text = normalize_llm_response(assistant_text)

        response_citations = [
            CitationSchema(
                id=c["id"],
                document_id=c.get("document_id", ""),
                filename=c["filename"],
                page_number=c["page_number"],
                snippet=c["snippet"],
            )
            for c in citations_data
        ]

        assistant_msg = MessageEntity(
            id=str(uuid.uuid4()),
            session_id=session.id,
            role="assistant",
            content=assistant_text,
            citations=[c.model_dump() for c in response_citations] if response_citations else None,
            model_used=mdl,
            provider_used=prov,
            created_at=datetime.now(timezone.utc),
        )
        await self.session_repo.add_message(assistant_msg)

        return ChatResponse(
            response=assistant_text,
            session_id=session.id,
            chat_number=session.chat_number,
            chat_id=session.chat_number,
            citations=response_citations,
        )

    async def regenerate_response(
        self,
        message_id: str,
        user: UserEntity,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> ChatResponse:
        """Regenerates the assistant response for a given message."""
        target_msg = await self.session_repo.get_message(message_id)
        if not target_msg:
            raise EntityNotFoundError(f"Message '{message_id}' not found.")

        session = await self.session_repo.get_session(target_msg.session_id, user_id=user.id)
        if not session:
            raise EntityNotFoundError(f"Session not found or unauthorized.")

        all_msgs = await self.session_repo.get_messages(session.id)

        # If the target is an assistant message, locate the preceding user prompt
        user_prompt = ""
        cutoff_ts = target_msg.created_at

        if target_msg.role == "assistant":
            # find preceding user message
            preceding = None
            for m in all_msgs:
                if m.id == target_msg.id:
                    break
                if m.role == "user":
                    preceding = m
            if not preceding:
                raise MananException("No preceding user prompt found to regenerate.")
            user_prompt = preceding.content
            cutoff_ts = preceding.created_at
        else:
            user_prompt = target_msg.content
            cutoff_ts = target_msg.created_at

        # Delete target and subsequent messages
        await self.session_repo.delete_messages_after(session.id, cutoff_ts)

        # Re-fetch remaining history
        remaining = await self.session_repo.get_messages(session.id)
        history_dicts = [
            {"role": m.role, "content": m.content}
            for m in remaining if m.content != user_prompt
        ]
        summary = await self.session_repo.get_summary(session.id)

        memories_list = []
        if user.long_term_memory_enabled:
            user_mems = await self.memory_repo.list_memories(user_id=user.id)
            memories_list = [m["content"] for m in user_mems]

        prov = provider or user.preferred_provider
        mdl = model or user.preferred_model

        assistant_text, citations_data = await self.rag_service.generate_response(
            prompt=user_prompt,
            history=history_dicts,
            document_ids=session.selected_document_ids,
            user_id=user.id,
            memories=memories_list,
            summary=summary,
            provider=prov,
            model_name=mdl,
        )
        assistant_text = normalize_llm_response(assistant_text)

        response_citations = [
            CitationSchema(
                id=c["id"],
                document_id=c.get("document_id", ""),
                filename=c["filename"],
                page_number=c["page_number"],
                snippet=c["snippet"],
            )
            for c in citations_data
        ]

        assistant_msg = MessageEntity(
            id=str(uuid.uuid4()),
            session_id=session.id,
            role="assistant",
            content=assistant_text,
            citations=[c.model_dump() for c in response_citations] if response_citations else None,
            model_used=mdl,
            provider_used=prov,
            created_at=datetime.now(timezone.utc),
        )
        await self.session_repo.add_message(assistant_msg)

        return ChatResponse(
            response=assistant_text,
            session_id=session.id,
            chat_number=session.chat_number,
            chat_id=session.chat_number,
            citations=response_citations,
        )
