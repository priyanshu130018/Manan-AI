import pytest
from unittest.mock import AsyncMock
import uuid
from datetime import datetime, timezone

from app.models.entities.message import MessageEntity
from app.models.schemas.chat import ChatRequest
from app.services.chat_service import ChatService
from app.repositories.session_repository import SessionRepository
from app.utils.normalization import normalize_llm_response
from tests.conftest import InMemorySessionRepository


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
    session_repo = InMemorySessionRepository()
    session_id = f"test-sess-{uuid.uuid4()}"
    await session_repo.get_or_create_session(session_id)

    user_msg = MessageEntity(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content="What is photosynthesis?",
        created_at=datetime.now(timezone.utc).timestamp(),
    )
    await session_repo.add_message(user_msg)

    msgs = await session_repo.get_messages(session_id)
    assert len(msgs) == 1
    assert msgs[0].role == "user"
    assert msgs[0].content == "What is photosynthesis?"


@pytest.mark.asyncio
async def test_regression_save_assistant_text_message():
    """2. Save normal assistant text message."""
    session_repo = InMemorySessionRepository()
    session_id = f"test-sess-{uuid.uuid4()}"
    await session_repo.get_or_create_session(session_id)

    ast_msg = MessageEntity(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content="Photosynthesis is the process by which plants turn light into energy.",
        created_at=datetime.now(timezone.utc).timestamp(),
    )
    await session_repo.add_message(ast_msg)

    msgs = await session_repo.get_messages(session_id)
    assert len(msgs) == 1
    assert msgs[0].role == "assistant"
    assert isinstance(msgs[0].content, str)


@pytest.mark.asyncio
async def test_regression_save_assistant_message_with_structured_metadata_or_dict_content():
    """3. Save assistant message with structured metadata and dict content gracefully adapted."""
    session_repo = InMemorySessionRepository()
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
        created_at=datetime.now(timezone.utc).timestamp(),
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
    session_repo = InMemorySessionRepository()
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
    session_repo = InMemorySessionRepository()
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
    resp_data = data.get("data", data)
    assert resp_data["response"] == "Live response text"
    assert "session_id" in resp_data


@pytest.mark.asyncio
async def test_document_grounded_chat_flow_and_citations():
    """Verify selected document IDs reach ChatService/RAGService, retrieve chunks, and return citations."""
    session_repo = InMemorySessionRepository()
    mock_rag = AsyncMock()

    mock_citations = [{
        "id": "cit-1",
        "document_id": "doc-123",
        "filename": "job_description.pdf",
        "page_number": 1,
        "snippet": "Software Engineer position requiring Python experience.",
    }]
    mock_rag.generate_response.return_value = (
        "The job description requires Python experience for a Software Engineer position.",
        mock_citations,
    )

    chat_svc = ChatService(session_repo=session_repo, rag_service=mock_rag)
    req = ChatRequest(
        message="tell me job description this pdf has?",
        document_ids=["doc-123"],
    )

    resp = await chat_svc.execute(req)

    # 1. Check response text and citations
    assert "Software Engineer" in resp.response
    assert len(resp.citations) == 1
    assert resp.citations[0].document_id == "doc-123"
    assert resp.citations[0].filename == "job_description.pdf"

    # 2. Check that RAGService received document_ids
    mock_rag.generate_response.assert_called_once()
    call_kwargs = mock_rag.generate_response.call_args.kwargs
    assert call_kwargs["document_ids"] == ["doc-123"]

    # 3. Check session persistence of selected_document_ids
    session = await session_repo.get_session(resp.session_id)
    assert session is not None
    assert session.selected_document_ids == ["doc-123"]


@pytest.mark.asyncio
async def test_session_selected_document_ids_loaded_on_subsequent_chat():
    """Verify session selected_document_ids are loaded when subsequent request omits document_ids."""
    session_repo = InMemorySessionRepository()
    mock_rag = AsyncMock()
    mock_rag.generate_response.return_value = ("Follow-up answer", [])

    chat_svc = ChatService(session_repo=session_repo, rag_service=mock_rag)

    # First turn: set document_ids
    resp1 = await chat_svc.execute(ChatRequest(
        message="First message about PDF",
        document_ids=["doc-abc"],
    ))

    # Second turn: omit document_ids in request
    resp2 = await chat_svc.execute(ChatRequest(
        message="Follow up question",
        session_id=resp1.session_id,
    ))

    # RAGService should receive active_docs loaded from session
    second_call_kwargs = mock_rag.generate_response.call_args_list[1].kwargs
    assert second_call_kwargs["document_ids"] == ["doc-abc"]


def test_document_grounded_post_chat_api(client, monkeypatch):
    """Verify POST /chat with document_ids returns HTTP 200, citations, and PDF-derived content."""
    from app.services.rag_service import RAGService

    async def mock_gen(*args, **kwargs):
        assert kwargs.get("document_ids") == ["doc-999"]
        return "Based on the PDF, the position is Senior Developer.", [{
            "id": "cit-1",
            "document_id": "doc-999",
            "filename": "senior_dev.pdf",
            "page_number": 2,
            "snippet": "Senior Developer position.",
        }]

    monkeypatch.setattr(RAGService, "generate_response", mock_gen)

    res = client.post("/chat", json={
        "message": "What is the job role?",
        "document_ids": ["doc-999"],
    })
    assert res.status_code == 200
    data = res.json()
    resp_data = data.get("data", data)
    assert "Senior Developer" in resp_data["response"]
    assert len(resp_data["citations"]) == 1
    assert resp_data["citations"][0]["document_id"] == "doc-999"


def test_model_selection_sent_via_request_and_header(client, monkeypatch):
    """Verify model selection is honored when passed via payload body or X-Model-Name header."""
    from app.services.rag_service import RAGService

    captured_models = []

    async def mock_gen(*args, **kwargs):
        captured_models.append(kwargs.get("model_name"))
        return "Model response", []

    monkeypatch.setattr(RAGService, "generate_response", mock_gen)

    # 1. Model in request JSON
    res1 = client.post("/chat", json={"message": "Hi", "model": "qwen3.8-27b"})
    assert res1.status_code == 200
    assert captured_models[-1] == "qwen3.8-27b"

    # 2. Model in X-Model-Name header
    res2 = client.post("/chat", json={"message": "Hi"}, headers={"X-Model-Name": "gemini-3.6-flash"})
    assert res2.status_code == 200
    assert captured_models[-1] == "gemini-3.6-flash"

