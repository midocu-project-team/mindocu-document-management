"""Document endpoints: full document (pages/blocks) and the stored PDF."""

import uuid

from fastapi import APIRouter
from fastapi.responses import FileResponse

from api.dependencies import BlockServiceDep, DocumentServiceDep, SegmentServiceDep
from api.exceptions import DocumentNotFoundError
from api.schemas.blocks import BlockOut
from api.schemas.cases import SegmentSummary
from pipeline import Document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{document_id}", response_model=Document)
def get_document(document_id: uuid.UUID, service: DocumentServiceDep) -> Document:
    """The full Document incl. pages and blocks (for the segment/PDF view)."""
    return service.get_document_full(document_id)


@router.get("/{document_id}/segments", response_model=list[SegmentSummary])
def list_document_segments(
    document_id: uuid.UUID, service: SegmentServiceDep
) -> list[SegmentSummary]:
    """The document's segments as a slim list (no pages/blocks)."""
    return [
        SegmentSummary.from_segment(segment)
        for segment in service.list_for_document(document_id)
    ]


@router.get("/{document_id}/blocks/{block_id}", response_model=BlockOut)
def get_document_block(
    document_id: uuid.UUID, block_id: int, service: BlockServiceDep
) -> BlockOut:
    """A single block of a document by its ``block_id``."""
    return BlockOut.from_block(service.get_block(document_id, block_id))


@router.get("/{document_id}/pdf")
def get_document_pdf(document_id: uuid.UUID, service: DocumentServiceDep) -> FileResponse:
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
