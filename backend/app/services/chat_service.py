import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any

from app.core.config import get_settings
from app.core.exceptions import (
    EntityNotFoundError,
    MananException,
    ValidationError,
)
from app.core.logging import LoggerFactory
from app.models.entities.enums import AppMode
from app.models.entities.message import MessageEntity
from app.models.entities.session import SessionEntity
from app.models.entities.user import UserEntity
from app.models.schemas.chat import ChatRequest, ChatResponse, CitationSchema
from app.repositories.memory_repository import MemoryRepository
from app.repositories.session_repository import SessionRepository
from app.services.rag_service import RAGService
from app.utils.normalization import normalize_llm_response

logger = LoggerFactory.create_logger("ChatService")


from app.models.schemas.session import MessageSchema

class ChatService:
    def __init__(
        self,
        session_repo: Optional[SessionRepository] = None,
        memory_repo: Optional[MemoryRepository] = None,
        rag_service: Optional[RAGService] = None,
        memory_service: Optional[Any] = None,
    ):
        self.settings = get_settings()
        self.session_repo = session_repo or SessionRepository()
        self.memory_repo = memory_repo or MemoryRepository()
        self.rag_service = rag_service or RAGService()
        self.memory_service = memory_service

    async def _extract_and_save_facts(self, user_id: str, message: str, session_id: str) -> None:
        """Lightweight background extraction of user facts into long term memory."""
        msg_lower = message.lower()
        trigger_phrases = ["my name is ", "i am ", "i prefer ", "i like ", "remember that ", "my email is ", "i work at "]
        for tp in trigger_phrases:
            if tp in msg_lower:
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

        provider = request.provider or (user.preferred_provider if user else None)
        model = request.model or (user.preferred_model if user else None)
        if model and "qwen" in model.lower() and not provider:
            provider = "qwen"

        requested_docs = request.selected_document_ids if request.selected_document_ids is not None else request.document_ids

        session: Optional[SessionEntity] = None
        history_dicts = []
        summary: Optional[str] = None
        memories_list = []
        user_msg: Optional[MessageEntity] = None
        assistant_msg: Optional[MessageEntity] = None

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
            if requested_docs is not None:
                session.selected_document_ids = requested_docs
                await self.session_repo.update_session(session)

            db_messages = await self.session_repo.get_messages(session.id)
            history_dicts = [
                {"role": m.role, "content": m.content}
                for m in db_messages
            ]
            summary = await self.session_repo.get_summary(session.id)

            if user and user.long_term_memory_enabled:
                user_mems = await self.memory_repo.list_memories(user_id=user.id)
                memories_list = [m["content"] for m in user_mems]
        else:
            if request.history:
                history_dicts = [
                    {"role": m.role, "content": m.content}
                    for m in request.history
                ]

        active_docs = requested_docs
        if active_docs is None and session:
            active_docs = session.selected_document_ids

        # Perform RAG + LLM generation first (transaction safety: if LLM fails, DB is not mutated)
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

        messages_schema: Optional[List[MessageSchema]] = None
        if not is_temporary and session:
            now_utc = datetime.now(timezone.utc)
            user_msg = MessageEntity(
                id=str(uuid.uuid4()),
                session_id=session.id,
                role="user",
                content=request.message,
                created_at=now_utc,
            )
            await self.session_repo.add_message(user_msg)

            if user and user.long_term_memory_enabled:
                await self._extract_and_save_facts(user.id, request.message, session.id)

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

            all_db_msgs = await self.session_repo.get_messages(session.id)
            messages_schema = [
                MessageSchema(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    citations=m.citations or [],
                    created_at=m.created_at if isinstance(m.created_at, float) else (m.created_at.timestamp() if hasattr(m.created_at, "timestamp") else float(m.created_at)),
                )
                for m in all_db_msgs
            ]

        c_num = session.chat_number if (session and not is_temporary) else None
        return ChatResponse(
            response=assistant_text,
            session_id=session.id if (session and not is_temporary) else session_id,
            chat_number=c_num,
            chat_id=c_num,
            citations=response_citations,
            user_message_id=user_msg.id if user_msg else None,
            assistant_message_id=assistant_msg.id if assistant_msg else None,
            messages=messages_schema,
        )

    async def edit_message_and_regenerate(
        self,
        message_id: str,
        new_content: str,
        user: UserEntity,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> ChatResponse:
        """Edits an existing user message, removes downstream messages, and generates a fresh response."""
        target_msg = await self.session_repo.get_message(message_id)
        if not target_msg:
            raise EntityNotFoundError(f"Message '{message_id}' not found.")

        session = await self.session_repo.get_session(target_msg.session_id, user_id=user.id)
        if not session:
            raise EntityNotFoundError(f"Session not found or unauthorized.")

        target_user_msg = target_msg
        if target_msg.role == "assistant":
            all_msgs = await self.session_repo.get_messages(session.id)
            preceding = None
            for m in all_msgs:
                if m.id == target_msg.id:
                    break
                if m.role == "user":
                    preceding = m
            if preceding:
                target_user_msg = preceding
            else:
                raise ValidationError("Cannot edit an assistant message with no preceding user prompt.")

        # Re-fetch remaining history strictly before target_user_msg
        all_msgs = await self.session_repo.get_messages(session.id)
        history_dicts = []
        for m in all_msgs:
            if m.id == target_user_msg.id:
                break
            history_dicts.append({"role": m.role, "content": m.content})

        summary = await self.session_repo.get_summary(session.id)

        memories_list = []
        if user.long_term_memory_enabled:
            user_mems = await self.memory_repo.list_memories(user_id=user.id)
            memories_list = [m["content"] for m in user_mems]

        prov = provider or user.preferred_provider
        mdl = model or user.preferred_model

        # Perform LLM & RAG generation first (transaction safety: if LLM fails, DB is preserved untouched)
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

        # Update the user message content in database
        await self.session_repo.update_message(target_user_msg.id, new_content)

        # Delete all downstream messages in the session created after target_user_msg
        await self.session_repo.delete_messages_after_message(session.id, target_user_msg.id)

        # Insert fresh assistant response
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

        # Query updated message sequence from DB
        updated_db_msgs = await self.session_repo.get_messages(session.id)
        messages_schema = [
            MessageSchema(
                id=m.id,
                role=m.role,
                content=m.content,
                citations=m.citations,
                created_at=m.created_at if isinstance(m.created_at, float) else (m.created_at.timestamp() if hasattr(m.created_at, "timestamp") else float(m.created_at)),
            )
            for m in updated_db_msgs
        ]

        return ChatResponse(
            response=assistant_text,
            session_id=session.id,
            chat_number=session.chat_number,
            chat_id=session.chat_number,
            citations=response_citations,
            user_message_id=target_user_msg.id,
            assistant_message_id=assistant_msg.id,
            messages=messages_schema,
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
        target_user_msg = target_msg

        if target_msg.role == "assistant":
            preceding = None
            for m in all_msgs:
                if m.id == target_msg.id:
                    break
                if m.role == "user":
                    preceding = m
            if not preceding:
                raise MananException("No preceding user prompt found to regenerate.")
            target_user_msg = preceding

        # Re-fetch remaining history strictly before target_user_msg
        history_dicts = []
        for m in all_msgs:
            if m.id == target_user_msg.id:
                break
            history_dicts.append({"role": m.role, "content": m.content})

        summary = await self.session_repo.get_summary(session.id)

        memories_list = []
        if user.long_term_memory_enabled:
            user_mems = await self.memory_repo.list_memories(user_id=user.id)
            memories_list = [m["content"] for m in user_mems]

        prov = provider or user.preferred_provider
        mdl = model or user.preferred_model

        # Perform LLM & RAG generation first (transaction safety: if LLM fails, DB is preserved untouched)
        assistant_text, citations_data = await self.rag_service.generate_response(
            prompt=target_user_msg.content,
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

        # Delete all downstream messages created after target_user_msg
        await self.session_repo.delete_messages_after_message(session.id, target_user_msg.id)

        # Insert fresh assistant response
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

        # Query updated message sequence from DB
        updated_db_msgs = await self.session_repo.get_messages(session.id)
        messages_schema = [
            MessageSchema(
                id=m.id,
                role=m.role,
                content=m.content,
                citations=m.citations,
                created_at=m.created_at if isinstance(m.created_at, float) else (m.created_at.timestamp() if hasattr(m.created_at, "timestamp") else float(m.created_at)),
            )
            for m in updated_db_msgs
        ]

        return ChatResponse(
            response=assistant_text,
            session_id=session.id,
            chat_number=session.chat_number,
            chat_id=session.chat_number,
            citations=response_citations,
            user_message_id=target_user_msg.id,
            assistant_message_id=assistant_msg.id,
            messages=messages_schema,
        )
