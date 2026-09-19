import pytest
from app.models.entities.user import UserEntity
from app.api.dependencies.auth import get_current_user
from app.services.rag_service import RAGService


@pytest.fixture
def edit_user():
    return UserEntity(
        id="test-edit-flow-user-id",
        name="Edit Flow User",
        email="editflow@example.com",
        auth_provider="local",
    )


def test_full_edit_flow_regressions(client, edit_user, monkeypatch):
    """
    Tests:
    1. Send Q1 -> Receive A1
    2. Send Q2 -> Receive A2
    3. Regenerate A2 -> Receive regenerated A2 (replaces old A2)
    4. Edit Q2 -> Submit edited text -> Replaces Q2 & A2, runs new RAG retrieval, earlier Q1/A1 intact
    5. Attempt to edit stale/deleted message ID -> Returns 404
    """
    client.app.dependency_overrides[get_current_user] = lambda: edit_user

    rag_calls = []

    async def mock_generate_response(
        self,
        prompt: str,
        history: list,
        document_ids=None,
        user_id=None,
        memories=None,
        summary=None,
        provider=None,
        model_name=None,
    ):
        rag_calls.append({
            "prompt": prompt,
            "history": history,
            "document_ids": document_ids,
        })
        if "roles of admin" in prompt.lower():
            citations = [{"id": "cit-role-1", "filename": "admin_roles.pdf", "page_number": 1, "snippet": "Admin roles include user management."}]
            return "Admin has several roles including user management.", citations
        elif "reset password" in prompt.lower():
            citations = [{"id": "cit-pwd-1", "filename": "auth_guide.pdf", "page_number": 3, "snippet": "To reset password, click forgot password."}]
            return "To reset password, go to settings or click forgot password.", citations
        elif "security precautions" in prompt.lower():
            citations = [{"id": "cit-sec-1", "filename": "security_policy.pdf", "page_number": 5, "snippet": "Admins must use 2FA and strong passwords."}]
            return "Security precautions for admin include 2FA and strict access control.", citations
        return f"Answer for: {prompt}", []

    monkeypatch.setattr(RAGService, "generate_response", mock_generate_response)

    # 1. Send Q1
    res1 = client.post("/chat", json={"message": "What are the roles of admin?"})
    assert res1.status_code == 200
    data1 = res1.json()["data"]
    session_id = data1["session_id"]
    assert "user management" in data1["response"]
    assert data1["citations"][0]["filename"] == "admin_roles.pdf"

    sess_res1 = client.get(f"/sessions/{session_id}")
    assert sess_res1.status_code == 200
    msgs1 = sess_res1.json()["data"]["messages"]
    assert len(msgs1) == 2
    q1_id = msgs1[0]["id"]
    a1_id = msgs1[1]["id"]
    assert msgs1[0]["content"] == "What are the roles of admin?"

    # 2. Send Q2
    res2 = client.post("/chat", json={"session_id": session_id, "message": "How do I reset password?"})
    assert res2.status_code == 200
    data2 = res2.json()["data"]
    assert data2["citations"][0]["filename"] == "auth_guide.pdf"

    sess_res2 = client.get(f"/sessions/{session_id}")
    msgs2 = sess_res2.json()["data"]["messages"]
    assert len(msgs2) == 4
    q2_id = msgs2[2]["id"]
    a2_id = msgs2[3]["id"]
    assert msgs2[2]["content"] == "How do I reset password?"

    # 3. Test Regenerate on A2
    regen_res = client.post(f"/messages/{a2_id}/regenerate", json={})
    assert regen_res.status_code == 200
    regen_data = regen_res.json()["data"]
    assert "messages" in regen_data and len(regen_data["messages"]) == 4

    sess_res_after_regen = client.get(f"/sessions/{session_id}")
    msgs_after_regen = sess_res_after_regen.json()["data"]["messages"]
    assert len(msgs_after_regen) == 4
    assert msgs_after_regen[0]["id"] == q1_id  # Q1 intact
    assert msgs_after_regen[1]["id"] == a1_id  # A1 intact
    assert msgs_after_regen[2]["id"] == q2_id  # Q2 ID intact after regenerate!
    a2_regen_id = msgs_after_regen[3]["id"]
    assert a2_regen_id != a2_id  # Old A2 replaced by new regenerated A2

    # 4. Test Edit Q2 AFTER Regenerate
    # Change Q2 to: "What are the security precautions for admin?"
    edit_res = client.patch(f"/messages/{q2_id}", json={"content": "What are the security precautions for admin?"})
    assert edit_res.status_code == 200
    edit_data = edit_res.json()["data"]

    # Verify new answer and new citations returned from edit endpoint
    assert "Security precautions" in edit_data["response"]
    assert len(edit_data["citations"]) == 1
    assert edit_data["citations"][0]["filename"] == "security_policy.pdf"
    assert edit_data["citations"][0]["id"] == "cit-sec-1"

    # Verify returned messages in ChatResponse
    assert "messages" in edit_data and len(edit_data["messages"]) == 4

    sess_res_after_edit = client.get(f"/sessions/{session_id}")
    msgs_after_edit = sess_res_after_edit.json()["data"]["messages"]
    assert len(msgs_after_edit) == 4

    # Verification of acceptance criteria:
    # - Earlier history (Q1, A1) remains intact
    assert msgs_after_edit[0]["id"] == q1_id
    assert msgs_after_edit[0]["content"] == "What are the roles of admin?"
    assert msgs_after_edit[1]["id"] == a1_id

    # - Q2 content is updated to new prompt
    assert msgs_after_edit[2]["id"] == q2_id
    assert msgs_after_edit[2]["content"] == "What are the security precautions for admin?"

    # - Old A2 (and regenerated A2) is replaced by NEW assistant response with new citations
    a2_new_id = msgs_after_edit[3]["id"]
    assert a2_new_id != a2_id
    assert a2_new_id != a2_regen_id
    assert "Security precautions" in msgs_after_edit[3]["content"]
    assert msgs_after_edit[3]["citations"][0]["filename"] == "security_policy.pdf"

    # Verify RAG retrieval was executed for the edited prompt
    last_rag_call = rag_calls[-1]
    assert last_rag_call["prompt"] == "What are the security precautions for admin?"
    assert len(last_rag_call["history"]) == 2  # Q1 and A1 in history

    # 5. Test Stale/Deleted Message ID handling -> Invalid message ID returns proper 404
    stale_res = client.patch(f"/messages/{a2_id}", json={"content": "Stale edit"})
    assert stale_res.status_code == 404
    assert "not found" in stale_res.json()["message"].lower()

    stale_regen = client.post(f"/messages/{a2_id}/regenerate", json={})
    assert stale_regen.status_code == 404
    assert "not found" in stale_regen.json()["message"].lower()


def test_edit_after_regenerate_single_turn(client, edit_user, monkeypatch):
    """
    Test exact Test A sequence:
    1. Ask: "What are the roles of admin?"
    2. Receive answer A1.
    3. Click Regenerate on A1 -> Receive A2.
    4. Click pencil on user question (Q1) -> Change to: "What are the security precautions for admin?"
    5. Submit -> Old Q1 & A1/A2 replaced by edited question & new answer.
    """
    client.app.dependency_overrides[get_current_user] = lambda: edit_user

    async def mock_generate_response(
        self,
        prompt: str,
        history: list,
        document_ids=None,
        user_id=None,
        memories=None,
        summary=None,
        provider=None,
        model_name=None,
    ):
        if "roles of admin" in prompt.lower():
            return "Admin roles explanation", [{"id": "c1", "filename": "roles.pdf", "page_number": 1, "snippet": "Roles"}]
        elif "security precautions" in prompt.lower():
            return "Security precautions explanation", [{"id": "c2", "filename": "security.pdf", "page_number": 2, "snippet": "Security"}]
        return "Default answer", []

    monkeypatch.setattr(RAGService, "generate_response", mock_generate_response)

    # 1. Ask Q1
    res1 = client.post("/chat", json={"message": "What are the roles of admin?"})
    assert res1.status_code == 200
    data1 = res1.json()["data"]
    session_id = data1["session_id"]
    q1_id = data1["user_message_id"]
    a1_id = data1["assistant_message_id"]

    # 2. Click Regenerate on A1
    regen_res = client.post(f"/messages/{a1_id}/regenerate", json={})
    assert regen_res.status_code == 200
    a2_id = regen_res.json()["data"]["assistant_message_id"]
    assert a2_id != a1_id

    # 3. Click pencil on Q1 and Submit edited question
    edit_res = client.patch(f"/messages/{q1_id}", json={"content": "What are the security precautions for admin?"})
    assert edit_res.status_code == 200
    edit_data = edit_res.json()["data"]
    assert edit_data["response"] == "Security precautions explanation"
    assert edit_data["citations"][0]["filename"] == "security.pdf"

    # Verify session messages in DB
    sess_res = client.get(f"/sessions/{session_id}")
    assert sess_res.status_code == 200
    msgs = sess_res.json()["data"]["messages"]
    assert len(msgs) == 2
    assert msgs[0]["id"] == q1_id
    assert msgs[0]["content"] == "What are the security precautions for admin?"
    assert msgs[1]["content"] == "Security precautions explanation"
    assert msgs[1]["id"] != a1_id
    assert msgs[1]["id"] != a2_id


def test_transaction_safety_on_generation_failure(client, edit_user, monkeypatch):
    """Verify that if RAG/LLM generation fails during edit, the database remains in its original consistent state."""
    client.app.dependency_overrides[get_current_user] = lambda: edit_user

    async def mock_success(self, *args, **kwargs):
        return "Original assistant answer", []

    monkeypatch.setattr(RAGService, "generate_response", mock_success)

    # Create initial Q1 & A1
    res1 = client.post("/chat", json={"message": "Initial Question"})
    assert res1.status_code == 200
    session_id = res1.json()["data"]["session_id"]
    q1_id = res1.json()["data"]["user_message_id"]

    # Now simulate LLM service failure during edit
    from app.core.exceptions import LLMError

    async def mock_failure(self, *args, **kwargs):
        raise LLMError("Simulated LLM network timeout or rate limit")

    monkeypatch.setattr(RAGService, "generate_response", mock_failure)

    edit_res = client.patch(f"/messages/{q1_id}", json={"content": "Failing Edit Question"})
    assert edit_res.status_code in [500, 502, 503]

    # Check DB state: initial message and answer must NOT be destroyed or corrupted
    sess_res = client.get(f"/sessions/{session_id}")
    assert sess_res.status_code == 200
    msgs = sess_res.json()["data"]["messages"]
    assert len(msgs) == 2
    assert msgs[0]["content"] == "Initial Question"
    assert msgs[1]["content"] == "Original assistant answer"


def test_edit_truncates_further_downstream_turns(client, edit_user, monkeypatch):
    """
    Test editing in a 3-turn conversation:
    Q1 / A1
    Q2 / A2
    Q3 / A3
    Edit Q2 -> Q1/A1 remain intact, Q2 updated, A2 replaced, Q3/A3 truncated.
    """
    client.app.dependency_overrides[get_current_user] = lambda: edit_user

    async def mock_generate_response(self, prompt: str, *args, **kwargs):
        return f"Answer to {prompt}", []

    monkeypatch.setattr(RAGService, "generate_response", mock_generate_response)

    res1 = client.post("/chat", json={"message": "Q1"})
    session_id = res1.json()["data"]["session_id"]
    q1_id = res1.json()["data"]["user_message_id"]

    res2 = client.post("/chat", json={"session_id": session_id, "message": "Q2"})
    q2_id = res2.json()["data"]["user_message_id"]

    res3 = client.post("/chat", json={"session_id": session_id, "message": "Q3"})

    sess_before = client.get(f"/sessions/{session_id}").json()["data"]["messages"]
    assert len(sess_before) == 6

    # Edit Q2
    edit_res = client.patch(f"/messages/{q2_id}", json={"content": "Q2 Edited"})
    assert edit_res.status_code == 200

    sess_after = client.get(f"/sessions/{session_id}").json()["data"]["messages"]
    assert len(sess_after) == 4
    assert sess_after[0]["id"] == q1_id
    assert sess_after[0]["content"] == "Q1"
    assert sess_after[2]["id"] == q2_id
    assert sess_after[2]["content"] == "Q2 Edited"
    assert sess_after[3]["content"] == "Answer to Q2 Edited"


def test_edit_with_gemini_36_succeeds_and_gemini_25_unavailable_preserves_conversation(client, edit_user, monkeypatch):
    """
    Verify:
    1. Initial question with Gemini 3.6 Flash succeeds.
    2. Editing with Qwen 3.8 27B when LLM encounters an error:
       - Returns 500/503 with informative error message.
       - Database is NOT updated; original question and answer remain intact.
       - No error message is persisted as an assistant message.
    3. User switches to Gemini 3.6 Flash and submits edit again:
       - Edit succeeds, old answer replaced with new Gemini 3.6 answer.
    """
    from app.core.exceptions import LLMError
    client.app.dependency_overrides[get_current_user] = lambda: edit_user

    async def mock_generate_response(self, prompt: str, history: list, *args, **kwargs):
        model_name = kwargs.get("model_name")
        if model_name == "qwen3.8-27b":
            raise LLMError(
                "Qwen LLM execution failed: Connection refused.",
                provider="qwen",
                model="qwen3.8-27b",
                status_code=503,
            )
        elif "security precautions" in prompt.lower():
            return "Gemini 3.6 Flash: Security precautions for admin include MFA and RBAC.", [
                {"id": "cit-sec", "filename": "security_policy.pdf", "page_number": 1, "snippet": "MFA and RBAC"}
            ]
        return "Gemini 3.6 Flash: Admin roles include user administration.", [
            {"id": "cit-role", "filename": "roles.pdf", "page_number": 1, "snippet": "User administration"}
        ]

    monkeypatch.setattr(RAGService, "generate_response", mock_generate_response)

    # 1. Ask initial question using Gemini 3.6 Flash
    res1 = client.post("/chat", json={"message": "What are the roles of admin?", "model": "gemini-3.6-flash"})
    assert res1.status_code == 200
    data1 = res1.json()["data"]
    session_id = data1["session_id"]
    q1_id = data1["user_message_id"]
    a1_id = data1["assistant_message_id"]
    assert "Admin roles include" in data1["response"]

    # 2. Edit with qwen3.8-27b (simulating unavailable model)
    res_fail = client.patch(
        f"/messages/{q1_id}",
        json={"content": "What are the security precautions for admin?", "model": "qwen3.8-27b"}
    )
    assert res_fail.status_code == 503 or res_fail.status_code == 500
    err_json = res_fail.json()
    assert "Connection refused" in err_json["message"]

    # Check that database messages were NOT mutated or deleted
    sess_res = client.get(f"/sessions/{session_id}")
    assert sess_res.status_code == 200
    msgs = sess_res.json()["data"]["messages"]
    assert len(msgs) == 2
    assert msgs[0]["id"] == q1_id
    assert msgs[0]["content"] == "What are the roles of admin?"
    assert msgs[1]["id"] == a1_id
    assert "Admin roles include" in msgs[1]["content"]

    # 3. Retry edit using Gemini 3.6 Flash
    res_retry = client.patch(
        f"/messages/{q1_id}",
        json={"content": "What are the security precautions for admin?", "model": "gemini-3.6-flash"}
    )
    assert res_retry.status_code == 200
    retry_data = res_retry.json()["data"]
    assert "Security precautions for admin include MFA" in retry_data["response"]
    assert retry_data["citations"][0]["filename"] == "security_policy.pdf"

    # Verify session now has updated question and new assistant answer
    sess_after = client.get(f"/sessions/{session_id}")
    msgs_after = sess_after.json()["data"]["messages"]
    assert len(msgs_after) == 2
    assert msgs_after[0]["id"] == q1_id
    assert msgs_after[0]["content"] == "What are the security precautions for admin?"
    assert "Security precautions for admin include MFA" in msgs_after[1]["content"]
    assert msgs_after[1]["id"] != a1_id




