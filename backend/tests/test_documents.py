import io
from unittest.mock import AsyncMock
import pytest


def test_document_txt_upload_and_delete(client, mock_embedding, monkeypatch):
    mock_add = AsyncMock()
    mock_delete = AsyncMock()
    monkeypatch.setattr("app.repositories.vector_repository.VectorRepository.add", mock_add)
    monkeypatch.setattr("app.repositories.vector_repository.VectorRepository.delete_document", mock_delete)

    # Upload TXT file
    txt_content = b"Operating Systems: Deadlocks and Concurrency.\n\nA deadlock occurs when processes hold resources and wait for others."
    files = {"file": ("os_lecture.txt", io.BytesIO(txt_content), "text/plain")}

    upload_res = client.post("/doc/upload", files=files)
    assert upload_res.status_code == 200
    upload_data = upload_res.json()["data"]
    assert upload_data["filename"] == "os_lecture.txt"
    assert upload_data["chunks"] >= 1
    doc_id = upload_data["document_id"]

    # List documents
    list_res = client.get("/doc")
    assert list_res.status_code == 200
    assert any(d["document_id"] == doc_id for d in list_res.json()["data"])

    # Get single document
    get_res = client.get(f"/doc/{doc_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["filename"] == "os_lecture.txt"

    # Delete document
    del_res = client.delete(f"/doc/{doc_id}")
    assert del_res.status_code == 200

    # Ensure document is no longer listed
    list_after = client.get("/doc")
    assert not any(d["document_id"] == doc_id for d in list_after.json()["data"])

    # Assert obsolete /documents route aliases return 404
    assert client.get("/documents").status_code == 404
    assert client.post("/documents/upload").status_code == 404
    assert client.get("/documents/storage").status_code == 404
    assert client.get(f"/documents/{doc_id}").status_code == 404
    assert client.delete(f"/documents/{doc_id}").status_code == 404
