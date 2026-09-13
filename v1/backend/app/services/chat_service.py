import uuid
from datetime import datetime, timezone
from typing import List, Optional
from app.core.logging import LoggerFactory
from app.models.entities.message import MessageEntity
from app.models.entities.session import SessionEntity
from app.models.schemas.chat import ChatRequest, ChatResponse, CitationSchema
from app.repositories.session_repository import SessionRepository
from app.services.rag_service import RAGService

logger = LoggerFactory.create_logger("ChatService")

class ChatService:
    def __init__(
        self,
        session_repo: Optional[SessionRepository] = None,
        rag_service: Optional[RAGService] = None,
    ):
        self.session_repo = session_repo or SessionRepository()
        self.rag_service = rag_service or RAGService()

    async def execute(self, request: ChatRequest) -> ChatResponse:
        session_id = request.session_id or str(uuid.uuid4())
        is_temporary = bool(request.is_temporary)

        session: Optional[SessionEntity] = None
        history_dicts = []
        summary: Optional[str] = None

        if not is_temporary:
            session = await self.session_repo.get_session(session_id)
            if not session:
                session = await self.session_repo.get_or_create_session(
                    session_id=session_id,
                    title=request.message[:40] if request.message else "New Chat",
                    chat_number=request.chat_number,
                )
            if request.selected_document_ids is not None:
                session.selected_document_ids = request.selected_document_ids
                await self.session_repo.update_session(session)

            # Persist user message
            user_msg = MessageEntity(
                id=str(uuid.uuid4()),
                session_id=session.id,
                role="user",
                content=request.message,
                created_at=datetime.now(timezone.utc),
            )
            await self.session_repo.add_message(user_msg)

            # Load history
            db_messages = await self.session_repo.get_messages(session.id)
            history_dicts = [
                {"role": m.role, "content": m.content}
                for m in db_messages[:-1]
            ]
            summary = await self.session_repo.get_summary(session.id)
        else:
            if request.history:
                history_dicts = [
                    {"role": m.role, "content": m.content}
                    for m in request.history
                ]

        active_docs = request.selected_document_ids
        if active_docs is None and session:
            active_docs = session.selected_document_ids

        assistant_text, citations_data = await self.rag_service.generate_rag_response(
            prompt=request.message,
            history=history_dicts,
            document_ids=active_docs,
            summary=summary,
        )

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
                created_at=datetime.now(timezone.utc),
            )
            await self.session_repo.add_message(assistant_msg)

        return ChatResponse(
            response=assistant_text,
            session_id=session_id if not is_temporary else "temp-session",
            chat_number=session.chat_number if (session and not is_temporary) else None,
            citations=response_citations,
        )
