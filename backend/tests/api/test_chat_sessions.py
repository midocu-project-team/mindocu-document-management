"""Chat session endpoints: create/list sessions, post a message, delete.

The chat strategy itself is faked (FakeChatStrategy in fakes.py, wired in
conftest's client fixture) -- these tests cover persistence/orchestration
(session/message rows, title auto-fill, grounding round-trip), not answer
quality.
"""

import uuid

from conftest import PDF_BYTES


def _make_case(client, name="Fall"):
    return client.post("/cases", json={"name": name}).json()["id"]


def _upload(client, case_id, names):
    files = [("files", (name, PDF_BYTES, "application/pdf")) for name in names]
    return client.post(f"/cases/{case_id}/documents", files=files)


def _document_id(client) -> str:
    case_id = _make_case(client)
    return _upload(client, case_id, ["akte.pdf"]).json()[0]["document_id"]


def _session_id(client, document_id: str) -> str:
    return client.post(f"/documents/{document_id}/chat/sessions").json()["session_id"]


def test_create_and_list_chat_sessions(client):
    document_id = _document_id(client)

    created = client.post(f"/documents/{document_id}/chat/sessions")
    assert created.status_code == 201
    assert created.json()["document_id"] == document_id
    assert created.json()["title"] is None
    session_id = created.json()["session_id"]

    listed = client.get(f"/documents/{document_id}/chat/sessions").json()
    assert [s["session_id"] for s in listed] == [session_id]


def test_create_session_for_unknown_document_404(client):
    assert client.post(f"/documents/{uuid.uuid4()}/chat/sessions").status_code == 404


def test_list_sessions_for_unknown_document_404(client):
    assert client.get(f"/documents/{uuid.uuid4()}/chat/sessions").status_code == 404


def test_post_message_returns_grounded_answer_and_sets_title(client):
    document_id = _document_id(client)
    session_id = _session_id(client, document_id)

    resp = client.post(
        f"/chat/sessions/{session_id}/messages", json={"question": "Wer ist der Vater?"}
    )
    assert resp.status_code == 200
    message = resp.json()
    assert message["role"] == "assistant"
    assert message["text"] == "Fake answer to: Wer ist der Vater?"
    assert message["references"][0]["block_ids"]  # grounded, not empty

    detail = client.get(f"/chat/sessions/{session_id}").json()
    assert detail["title"] == "Wer ist der Vater?"
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][0]["text"] == "Wer ist der Vater?"
    assert detail["messages"][0]["references"] == []  # user turns carry no grounding
    assert detail["messages"][1]["references"] == message["references"]


def test_second_message_does_not_overwrite_title(client):
    document_id = _document_id(client)
    session_id = _session_id(client, document_id)

    client.post(f"/chat/sessions/{session_id}/messages", json={"question": "Erste Frage?"})
    client.post(f"/chat/sessions/{session_id}/messages", json={"question": "Zweite Frage?"})

    detail = client.get(f"/chat/sessions/{session_id}").json()
    assert detail["title"] == "Erste Frage?"
    assert len(detail["messages"]) == 4


def test_post_message_to_unknown_session_404(client):
    resp = client.post(
        f"/chat/sessions/{uuid.uuid4()}/messages", json={"question": "Frage?"}
    )
    assert resp.status_code == 404


def test_get_unknown_session_404(client):
    assert client.get(f"/chat/sessions/{uuid.uuid4()}").status_code == 404


def test_empty_question_rejected(client):
    document_id = _document_id(client)
    session_id = _session_id(client, document_id)

    resp = client.post(f"/chat/sessions/{session_id}/messages", json={"question": ""})
    assert resp.status_code == 422


def test_delete_chat_session(client):
    document_id = _document_id(client)
    session_id = _session_id(client, document_id)

    assert client.delete(f"/chat/sessions/{session_id}").status_code == 204
    assert client.get(f"/chat/sessions/{session_id}").status_code == 404
    assert client.get(f"/documents/{document_id}/chat/sessions").json() == []


def test_delete_unknown_session_404(client):
    assert client.delete(f"/chat/sessions/{uuid.uuid4()}").status_code == 404
