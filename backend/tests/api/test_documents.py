"""Upload + processing + read endpoints (pipeline stubbed, queue inline)."""

import uuid

from conftest import PDF_BYTES


def _make_case(client, name="Fall"):
    return client.post("/cases", json={"name": name}).json()["id"]


def _upload(client, case_id, names):
    files = [("files", (name, PDF_BYTES, "application/pdf")) for name in names]
    return client.post(f"/cases/{case_id}/documents", files=files)


def test_upload_accepts_and_processes_to_done(client):
    case_id = _make_case(client)
    resp = _upload(client, case_id, ["akte.pdf"])
    assert resp.status_code == 202

    # Inline queue already processed it -> status reports done.
    status = client.get(f"/cases/{case_id}/status").json()
    assert status["status"] == "done"
    assert status["documents"][0]["processing_status"] == "done"
    assert status["documents"][0]["error_message"] is None


def test_upload_more_than_limit_rejected(client):
    case_id = _make_case(client)
    resp = _upload(client, case_id, ["a.pdf", "b.pdf", "c.pdf", "d.pdf"])
    assert resp.status_code == 409
    # Nothing was stored.
    assert client.get(f"/cases/{case_id}").json()["documents"] == []


def test_upload_limit_counts_existing(client):
    case_id = _make_case(client)
    assert _upload(client, case_id, ["a.pdf", "b.pdf"]).status_code == 202
    assert _upload(client, case_id, ["c.pdf", "d.pdf"]).status_code == 409


def test_non_pdf_rejected(client):
    case_id = _make_case(client)
    files = [("files", ("evil.pdf", b"not a pdf at all", "application/pdf"))]
    resp = client.post(f"/cases/{case_id}/documents", files=files)
    assert resp.status_code == 422


def test_case_detail_lists_documents_with_segment_count(client):
    case_id = _make_case(client)
    _upload(client, case_id, ["akte.pdf"])

    document = client.get(f"/cases/{case_id}").json()["documents"][0]
    assert document["processing_status"] == "done"
    # Segments are fetched separately now (GET /documents/{id}/segments) -- the
    # case detail only carries the count for the document dropdown.
    assert document["segment_count"] == 2
    assert "segments" not in document


def test_full_document_reconstructs_pages_and_segments(client):
    case_id = _make_case(client)
    document_id = _upload(client, case_id, ["akte.pdf"]).json()[0]["document_id"]

    full = client.get(f"/documents/{document_id}").json()
    assert full["document_id"] == document_id
    assert full["total_pages"] == 2
    assert len(full["pages"]) == 2
    assert full["pages"][0]["blocks"][0]["block_type"] == "heading"
    # Segments come back whole: pages re-attached, raw_text rebuilt.
    assert len(full["segments"][0]["pages"]) == 1
    assert full["segments"][0]["raw_text"]


def test_pdf_is_served(client):
    case_id = _make_case(client)
    document_id = _upload(client, case_id, ["akte.pdf"]).json()[0]["document_id"]

    resp = client.get(f"/documents/{document_id}/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


def test_unknown_document_returns_404(client):
    assert client.get(f"/documents/{uuid.uuid4()}").status_code == 404
