import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from app.services.rag_service import RAGService
from app.services.chat_service import ChatService
from app.models.schemas.chat import ChatRequest
from app.models.entities.user import UserEntity
from app.core.exceptions import LLMError


@pytest.mark.asyncio
async def test_rag_service_arbitrary_curly_braces_in_context():
    """
    Issue 1 Regression:
    Ensure that retrieved context containing arbitrary curly braces like
    {id}, {filename}, {sensor_id}, {e}, JSON, and code blocks does NOT
    cause LangChain missing variable errors in ChatPromptTemplate.
    """
    mock_retrieval_service = MagicMock()
    rag_service = RAGService(retrieval_service=mock_retrieval_service)

    problematic_context = """
    {
        "filename": "security.pdf",
        "sensor_id": "123",
        "e": "example",
        "id": "SEC-999"
    }
    The document contains {id}, {filename}, {e}, and {sensor_id}.
    Code snippet:
    function test() { return {"key": "value", "id": 1}; }
    """

    mock_chunks = [
        {
            "text": problematic_context,
            "filename": "security.pdf",
            "page_number": 1,
            "chunk_index": 1,
            "source_type": "pdf",
            "document_id": "doc-sec-1",
            "score": 0.95,
        }
    ]

    captured_messages: list[BaseMessage] = []

    async def mock_ainvoke(messages, *args, **kwargs):
        captured_messages.extend(messages)
        return AIMessage(content="The document describes sensor 123 and security rules.")

    mock_chat_model = MagicMock()
    mock_chat_model.ainvoke = AsyncMock(side_effect=mock_ainvoke)

    with patch.object(rag_service, "retrieve", new_callable=AsyncMock) as mock_retrieve, \
         patch("app.integrations.llm.factory.LLMFactory.get_chat_model", return_value=mock_chat_model):
        
        mock_retrieve.return_value = mock_chunks

        # User question also contains curly braces:
        user_prompt = "What does {id} and {\"sensor_id\": 123} mean in the document?"
        history = [{"role": "user", "content": "Hello {user}!"}, {"role": "assistant", "content": "Hi {name}!"}]

        ans, citations = await rag_service.generate_response(
            prompt=user_prompt,
            history=history,
            document_ids=["doc-sec-1"],
            user_id="user-123",
            provider="gemini",
            model_name="gemini-3.6-flash",
        )

        assert "sensor 123" in ans
        assert len(citations) == 1
        assert citations[0]["filename"] == "security.pdf"

        # Verify that captured messages contained the raw curly braces untouched
        assert len(captured_messages) >= 3
        system_msg = captured_messages[0]
        assert isinstance(system_msg, SystemMessage)
        assert "{filename}" in system_msg.content
        assert "{sensor_id}" in system_msg.content
        assert "{e}" in system_msg.content
        assert "{id}" in system_msg.content

        # Verify history and user prompt
        user_msg = captured_messages[-1]
        assert isinstance(user_msg, HumanMessage)
        assert user_msg.content == user_prompt


@pytest.mark.asyncio
async def test_rag_service_handles_latex_and_nested_json():
    """Verify LaTeX math and nested JSON in document context."""
    mock_retrieval_service = MagicMock()
    rag_service = RAGService(retrieval_service=mock_retrieval_service)

    latex_context = r"Formula: $f(x) = \frac{1}{\sqrt{2\pi\sigma^2}} e^{-\frac{(x-\mu)^2}{2\sigma^2}}$ and config: {'nested': {'id': '{val}'}}"
    mock_chunks = [
        {
            "text": latex_context,
            "filename": "stats.pdf",
            "page_number": 2,
            "chunk_index": 1,
            "source_type": "pdf",
            "document_id": "doc-stats-1",
            "score": 0.99,
        }
    ]

    captured_messages: list[BaseMessage] = []

    async def mock_ainvoke(messages, *args, **kwargs):
        captured_messages.extend(messages)
        return AIMessage(content="The formula is the normal distribution.")

    mock_chat_model = MagicMock()
    mock_chat_model.ainvoke = AsyncMock(side_effect=mock_ainvoke)

    with patch.object(rag_service, "retrieve", new_callable=AsyncMock) as mock_retrieve, \
         patch("app.integrations.llm.factory.LLMFactory.get_chat_model", return_value=mock_chat_model):
        
        mock_retrieve.return_value = mock_chunks

        ans, citations = await rag_service.generate_response(
            prompt="Explain the formula in stats.pdf",
            history=[],
            document_ids=["doc-stats-1"],
            user_id="user-123",
            provider="ollama",
            model_name="gpt-oss:120b",
        )

        assert "normal distribution" in ans
        assert len(citations) == 1
        assert captured_messages[0].content.find(r"\frac{1}{\sqrt{2\pi\sigma^2}}") != -1


@pytest.mark.asyncio
async def test_chat_service_execute_llm_failure_does_not_persist_fake_messages():
    """
    Issue 2 Regression:
    When LLM generation fails during POST /chat, NO message (neither user nor assistant)
    should be inserted into the database.
    """
    from tests.conftest import InMemorySessionRepository, InMemoryMemoryRepository

    session_repo = InMemorySessionRepository()
    memory_repo = InMemoryMemoryRepository()
    mock_retrieval_service = MagicMock()
    rag_service = RAGService(retrieval_service=mock_retrieval_service)

    chat_service = ChatService(
        session_repo=session_repo,
        memory_repo=memory_repo,
        rag_service=rag_service,
    )

    user = UserEntity(
        id="user-test-fail",
        name="Test User",
        email="fail_test@example.com",
        preferred_model="gemini-3.6-flash",
        preferred_provider="gemini",
    )

    # Mock rag_service.generate_response to raise an LLMError
    async def mock_fail(*args, **kwargs):
        raise LLMError("Gemini generation failed: Model quota exceeded.", provider="gemini", model="gemini-3.6-flash")

    with patch.object(rag_service, "generate_response", side_effect=mock_fail):
        req = ChatRequest(
            session_id="session-test-fail-1",
            message="What are the security precautions?",
            model="gemini-3.6-flash",
            provider="gemini",
        )

        with pytest.raises(LLMError) as exc_info:
            await chat_service.execute(req, user=user)

        assert "Model quota exceeded" in str(exc_info.value)

        # Verify that no messages were persisted in database for this session
        db_messages = await session_repo.get_messages("session-test-fail-1")
        assert len(db_messages) == 0


@pytest.mark.asyncio
async def test_chat_service_execute_success_returns_authoritative_ids():
    """
    When LLM generation succeeds during POST /chat, user and assistant messages
    are persisted in DB and real authoritative DB IDs are returned in ChatResponse.
    """
    from tests.conftest import InMemorySessionRepository, InMemoryMemoryRepository

    session_repo = InMemorySessionRepository()
    memory_repo = InMemoryMemoryRepository()
    mock_retrieval_service = MagicMock()
    rag_service = RAGService(retrieval_service=mock_retrieval_service)

    chat_service = ChatService(
        session_repo=session_repo,
        memory_repo=memory_repo,
        rag_service=rag_service,
    )

    user = UserEntity(
        id="user-test-success",
        name="Test User",
        email="success_test@example.com",
        preferred_model="gemini-3.6-flash",
        preferred_provider="gemini",
    )

    async def mock_success(*args, **kwargs):
        return "Admin roles include RBAC and system management.", [
            {"id": "cit-1", "document_id": "doc-1", "filename": "roles.pdf", "page_number": 1, "snippet": "RBAC and system management"}
        ]

    with patch.object(rag_service, "generate_response", side_effect=mock_success):
        req = ChatRequest(
            session_id="session-test-success-1",
            message="What are admin roles?",
            model="gemini-3.6-flash",
            provider="gemini",
        )

        res = await chat_service.execute(req, user=user)

        assert res.user_message_id is not None
        assert res.assistant_message_id is not None
        assert res.response == "Admin roles include RBAC and system management."
        assert len(res.citations) == 1

        # Check in DB
        db_messages = await session_repo.get_messages("session-test-success-1")
        assert len(db_messages) == 2
        assert db_messages[0].id == res.user_message_id
        assert db_messages[0].role == "user"
        assert db_messages[0].content == "What are admin roles?"
        assert db_messages[1].id == res.assistant_message_id
        assert db_messages[1].role == "assistant"
        assert db_messages[1].content == "Admin roles include RBAC and system management."

