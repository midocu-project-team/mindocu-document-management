"""Document endpoints: full document (pages/blocks) and the stored PDF."""

from fastapi import APIRouter
from fastapi.responses import FileResponse

from api.dependencies import DocumentServiceDep
from api.exceptions import DocumentNotFoundError
from pipeline import Document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{document_id}", response_model=Document)
def get_document(document_id: str, service: DocumentServiceDep) -> Document:
    """The full Document incl. pages and blocks (for the segment/PDF view)."""
    return service.get_document_full(document_id)


@router.get("/{document_id}/pdf")
def get_document_pdf(document_id: str, service: DocumentServiceDep) -> FileResponse:
    """Streams the stored original PDF for the preview."""
    row, path = service.get_pdf(document_id)
    if not path.exists():
        raise DocumentNotFoundError(document_id)
    # The stored PDF for a given (UUID) document_id never changes, so let the
    # browser keep it without revalidating. "private" keeps it out of shared
    # caches (CDNs/proxies) since case files are sensitive.
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=row.file_name,
        headers={"Cache-Control": "private, max-age=31536000, immutable"},
    )
