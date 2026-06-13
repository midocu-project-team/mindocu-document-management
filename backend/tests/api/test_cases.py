"""Case CRUD endpoints + delete cascade (rows and PDF files)."""

import uuid

from conftest import PDF_BYTES


def _upload(client, case_id, names):
    files = [("files", (name, PDF_BYTES, "application/pdf")) for name in names]
    return client.post(f"/cases/{case_id}/documents", files=files)


def test_create_case(client):
    resp = client.post("/cases", json={"name": "Fall A"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Fall A"
    assert body["status"] == "done"  # no documents yet
    assert body["document_count"] == 0


def test_create_case_requires_name(client):
    assert client.post("/cases", json={"name": ""}).status_code == 422


def test_list_cases_newest_first(client):
    first = client.post("/cases", json={"name": "Alt"}).json()["id"]
    second = client.post("/cases", json={"name": "Neu"}).json()["id"]
    listing = client.get("/cases").json()
    assert [c["id"] for c in listing] == [second, first]


def test_rename_case(client):
    case_id = client.post("/cases", json={"name": "Alt"}).json()["id"]
    resp = client.patch(f"/cases/{case_id}", json={"name": "Neu"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Neu"
    assert client.get(f"/cases/{case_id}").json()["name"] == "Neu"


def test_get_unknown_case_returns_404(client):
    assert client.get(f"/cases/{uuid.uuid4()}").status_code == 404


def test_delete_case_removes_documents_and_pdfs(client, settings):
    case_id = client.post("/cases", json={"name": "Fall"}).json()["id"]
    _upload(client, case_id, ["a.pdf"])

    case_dir = settings.storage_dir / case_id
    assert case_dir.exists()

    assert client.delete(f"/cases/{case_id}").status_code == 204
    assert client.get(f"/cases/{case_id}").status_code == 404
    assert not case_dir.exists()
