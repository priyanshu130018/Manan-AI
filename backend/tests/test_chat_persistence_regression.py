import pytest
from unittest.mock import AsyncMock
import uuid
from datetime import datetime, timezone

from app.models.entities.message import MessageEntity
from app.models.schemas.chat import ChatRequest
from app.services.chat_service import ChatService
from app.repositories.session_repository import SessionRepository
from app.utils.normalization import normalize_llm_response


def test_normalize_llm_response_types():
    """Verify normalize_llm_response handles str, dict, AIMessage, list, and Pydantic-like objects."""
    # 1. Plain str
    assert normalize_llm_response("Simple string") == "Simple string"

    # 2. Dict with text key
    assert normalize_llm_response({"text": "Dict response text"}) == "Dict response text"

    # 3. Dict with content key
    assert normalize_llm_response({"content": "Dict content text"}) == "Dict content text"

    # 4. List of block dicts (multimodal / LangChain Gemini format)
    blocks = [{"type": "text", "text": "Block 1"}, {"type": "text", "text": "Block 2"}]
    assert normalize_llm_response(blocks) == "Block 1\nBlock 2"

    # 5. AIMessage mock
    class MockAIMessage:
        content = [{"type": "text", "text": "AI message content"}]

    assert normalize_llm_response(MockAIMessage()) == "AI message content"

    # 6. Arbitrary dict
    assert normalize_llm_response({"raw_data": 123}) == '{"raw_data": 123}'


@pytest.mark.asyncio
async def test_regression_save_user_text_message():
    """1. Save normal user text message."""
    session_repo = SessionRepository()
    session_id = f"test-sess-{uuid.uuid4()}"
    await session_repo.get_or_create_session(session_id)

    user_msg = MessageEntity(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content="What is photosynthesis?",
        created_at=datetime.now(timezone.utc),
    )
    await session_repo.add_message(user_msg)

    msgs = await session_repo.get_messages(session_id)
    assert len(msgs) == 1
    assert msgs[0].role == "user"
    assert msgs[0].content == "What is photosynthesis?"


@pytest.mark.asyncio
async def test_regression_save_assistant_text_message():
    """2. Save normal assistant text message."""
    session_repo = SessionRepository()
    session_id = f"test-sess-{uuid.uuid4()}"
    await session_repo.get_or_create_session(session_id)

    ast_msg = MessageEntity(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content="Photosynthesis is the process by which plants turn light into energy.",
        created_at=datetime.now(timezone.utc),
    )
    await session_repo.add_message(ast_msg)

    msgs = await session_repo.get_messages(session_id)
    assert len(msgs) == 1
    assert msgs[0].role == "assistant"
    assert isinstance(msgs[0].content, str)


@pytest.mark.asyncio
async def test_regression_save_assistant_message_with_structured_metadata_or_dict_content():
    """3. Save assistant message with structured metadata and dict content gracefully adapted."""
    session_repo = SessionRepository()
    session_id = f"test-sess-{uuid.uuid4()}"
    await session_repo.get_or_create_session(session_id)

    dict_content = {"text": "Structured answer text", "confidence": 0.99}
    citations = [{"id": "cit-1", "filename": "doc.pdf", "page_number": 1, "snippet": "Sample"}]

    ast_msg = MessageEntity(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content=dict_content,  # type: ignore
        citations=citations,
        created_at=datetime.now(timezone.utc),
    )
    await session_repo.add_message(ast_msg)

    msgs = await session_repo.get_messages(session_id)
    assert len(msgs) == 1
    assert msgs[0].content == "Structured answer text"
    assert len(msgs[0].citations) == 1
    assert msgs[0].citations[0]["filename"] == "doc.pdf"


@pytest.mark.asyncio
async def test_regression_chat_service_persists_gemini_response_dict_or_aimessage():
    """4 & 6. ChatService can persist Gemini response (even if dict/AIMessage) and retrieve saved message."""
    session_repo = SessionRepository()
    mock_rag = AsyncMock()

    class FakeAIMessage:
        content = [{"type": "text", "text": "Gemini response text"}]

    mock_rag.generate_response.return_value = (FakeAIMessage(), [])

    chat_svc = ChatService(session_repo=session_repo, rag_service=mock_rag)
    req = ChatRequest(message="Tell me a joke", is_temporary=False)

    resp = await chat_svc.execute(req)
    assert resp.response == "Gemini response text"

    # 6. Verify retrieved saved message
    msgs = await session_repo.get_messages(resp.session_id)
    assert len(msgs) == 2  # user + assistant
    assert msgs[0].role == "user"
    assert msgs[0].content == "Tell me a joke"
    assert msgs[1].role == "assistant"
    assert msgs[1].content == "Gemini response text"


@pytest.mark.asyncio
async def test_regression_conversation_history_works():
    """7. Conversation history still works after the fix."""
    session_repo = SessionRepository()
    mock_rag = AsyncMock()
    mock_rag.generate_response.return_value = ("Second response", [])

    chat_svc = ChatService(session_repo=session_repo, rag_service=mock_rag)

    # First turn
    resp1 = await chat_svc.execute(ChatRequest(message="First message"))

    # Second turn
    resp2 = await chat_svc.execute(ChatRequest(message="Second message", session_id=resp1.session_id))

    history = await session_repo.get_messages(resp1.session_id)
    assert len(history) == 4  # user1, ast1, user2, ast2
    assert [m.role for m in history] == ["user", "assistant", "user", "assistant"]


def test_regression_post_chat_returns_200(client, monkeypatch):
    """5. POST /chat returns 200."""
    from app.services.rag_service import RAGService

    async def mock_gen(*args, **kwargs):
        return "Live response text", []

    monkeypatch.setattr(RAGService, "generate_response", mock_gen)

    res = client.post("/chat", json={"message": "Testing POST /chat live endpoint"})
    assert res.status_code == 200
    data = res.json()
    assert data["response"] == "Live response text"
    assert "session_id" in data
