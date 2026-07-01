"""Single-block endpoint: GET /documents/{id}/blocks/{block_id}."""

import uuid

from conftest import PDF_BYTES


def _make_case(client, name="Fall"):
    return client.post("/cases", json={"name": name}).json()["id"]


def _upload(client, case_id, names):
    files = [("files", (name, PDF_BYTES, "application/pdf")) for name in names]
    return client.post(f"/cases/{case_id}/documents", files=files)


def test_get_block_matches_full_document(client):
    case_id = _make_case(client)
    document_id = _upload(client, case_id, ["akte.pdf"]).json()[0]["document_id"]

    full = client.get(f"/documents/{document_id}").json()
    first = full["pages"][0]["blocks"][0]

    block = client.get(f"/documents/{document_id}/blocks/{first['block_id']}").json()
    assert block["block_id"] == first["block_id"]
    assert block["block_type"] == first["block_type"] == "heading"
    assert block["text"] == first["text"]
    assert block["page_number"] == 1


def test_unknown_block_returns_404(client):
    case_id = _make_case(client)
    document_id = _upload(client, case_id, ["akte.pdf"]).json()[0]["document_id"]

    assert client.get(f"/documents/{document_id}/blocks/999999").status_code == 404


def test_block_unknown_document_returns_404(client):
    assert client.get(f"/documents/{uuid.uuid4()}/blocks/0").status_code == 404
