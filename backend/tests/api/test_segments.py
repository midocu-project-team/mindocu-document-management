"""Granular segment endpoints: list per document, detail, relevance toggle."""

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


def test_list_document_segments(client):
    document_id = _document_id(client)

    segments = client.get(f"/documents/{document_id}/segments").json()
    assert len(segments) == 2
    assert {s["relevance"] for s in segments} == {True, False}
    assert "pages" not in segments[0]  # slim list


def test_list_segments_unknown_document_404(client):
    assert client.get(f"/documents/{uuid.uuid4()}/segments").status_code == 404


def test_segment_detail_includes_references(client):
    document_id = _document_id(client)
    segments = client.get(f"/documents/{document_id}/segments").json()
    relevant = next(s for s in segments if s["relevance"])

    detail = client.get(f"/segments/{relevant['segment_id']}").json()
    assert detail["segment_id"] == relevant["segment_id"]
    assert detail["title"] == "Verfügung des Gerichts"
    assert detail["references"]  # relevant segment carries at least one reference
    assert detail["references"][0]["block_ids"]


def test_unknown_segment_returns_404(client):
    assert client.get(f"/segments/{uuid.uuid4()}").status_code == 404


def test_patch_segment_relevance_toggles(client):
    document_id = _document_id(client)
    segments = client.get(f"/documents/{document_id}/segments").json()
    relevant = next(s for s in segments if s["relevance"])

    resp = client.patch(f"/segments/{relevant['segment_id']}", json={"relevance": False})
    assert resp.status_code == 200
    assert resp.json()["relevance"] is False

    # The change is persisted and visible from the detail + the list.
    assert client.get(f"/segments/{relevant['segment_id']}").json()["relevance"] is False
    listed = client.get(f"/documents/{document_id}/segments").json()
    changed = next(s for s in listed if s["segment_id"] == relevant["segment_id"])
    assert changed["relevance"] is False


def test_patch_unknown_segment_returns_404(client):
    resp = client.patch(f"/segments/{uuid.uuid4()}", json={"relevance": True})
    assert resp.status_code == 404
