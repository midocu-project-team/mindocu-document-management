"""Data access for documents + the Pydantic<->relational mapping.

A finished ``Document`` is written across one row per entity (pages, blocks,
segments, summary_references, reference_blocks) via Core bulk inserts in FK
order; the summary-reference bigint ids are correlated back by ``(segment_id,
seq)`` so the M:N ``reference_blocks`` rows point at the right reference. On read
the graph is eager-loaded and the ``Document`` rebuilt; per-segment pages and
``raw_text`` are reconstructed from the page range (not stored). Errors are not
persisted -- the rebuilt error lists are always empty.
"""

import uuid

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session, selectinload

from api.db.models import (
    Block,
    DocumentRow,
    Page,
    ProcessingStatus,
    ReferenceBlock,
    Segment,
    SummaryReference,
)
from api.exceptions import DocumentNotFoundError
from pipeline import Document


class DocumentRepository:
    """CRUD + (de)serialization between ``Document`` and the relational tables."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_pending(
        self,
        *,
        document_id: uuid.UUID,
        case_id: uuid.UUID,
        file_name: str,
        file_size_bytes: int,
        pdf_path: str,
    ) -> DocumentRow:
        """Inserts a `pending` row (no processed output yet) for a fresh PDF."""
        row = DocumentRow(
            document_id=document_id,
            case_id=case_id,
            file_name=file_name,
            file_size_bytes=file_size_bytes,
            pdf_path=pdf_path,
            processing_status=ProcessingStatus.PENDING,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def get(self, document_id: uuid.UUID) -> DocumentRow | None:
        return self.session.get(DocumentRow, document_id)

    def require(self, document_id: uuid.UUID) -> DocumentRow:
        row = self.get(document_id)
        if row is None:
            raise DocumentNotFoundError(document_id)
        return row

    def count_for_case(self, case_id: uuid.UUID) -> int:
        count = self.session.scalar(
            select(func.count())
            .select_from(DocumentRow)
            .where(DocumentRow.case_id == case_id)
        )
        return count or 0

    def set_status(
        self,
        document_id: uuid.UUID,
        status: ProcessingStatus,
        *,
        error_message: str | None = None,
    ) -> DocumentRow:
        row = self.require(document_id)
        row.processing_status = status
        row.error_message = error_message
        return row

    def save_document(self, document_id: uuid.UUID, document: Document) -> DocumentRow:
        """Persists a finished ``Document`` (children bulk-inserted) and flips to `done`."""
        row = self.require(document_id)
        _update_row(row, document)
        self.session.flush()  # the documents row must exist before its children (FKs)
        self._insert_children(document)
        return row

    def load_document(self, document_id: uuid.UUID) -> Document:
        """Rebuilds the full ``Document`` from the eager-loaded relational graph."""
        row = self._require_with_graph(document_id)
        pages = [_page_to_dict(page) for page in row.pages]
        pages_by_number = {page["page_number"]: page for page in pages}
        return Document.model_validate(
            {
                "document_id": row.document_id,
                "file_name": row.file_name,
                "file_size_bytes": row.file_size_bytes,
                "total_pages": row.total_pages,
                "ocr_engine": row.ocr_engine,
                "pages": pages,
                "segments": [
                    _segment_to_dict(segment, pages_by_number) for segment in row.segments
                ],
                "enrichment_method": row.enrichment_method,
                "extracted_at": row.extracted_at,
                "enriched_at": row.enriched_at,
            }
        )

    # Internal helpers

    def _require_with_graph(self, document_id: uuid.UUID) -> DocumentRow:
        statement = (
            select(DocumentRow)
            .where(DocumentRow.document_id == document_id)
            .options(
                selectinload(DocumentRow.pages).selectinload(Page.blocks),
                selectinload(DocumentRow.segments)
                .selectinload(Segment.references)
                .selectinload(SummaryReference.reference_blocks),
            )
        )
        row = self.session.scalars(statement).first()
        if row is None:
            raise DocumentNotFoundError(document_id)
        return row

    def _insert_children(self, document: Document) -> None:
        """Bulk-inserts every child of ``document`` in foreign-key order."""
        doc_id = document.document_id
        self._insert_pages(doc_id, document)
        self._insert_blocks(doc_id, document)
        self._insert_segments(doc_id, document)
        self._insert_references(doc_id, document)

    def _insert_pages(self, doc_id: uuid.UUID, document: Document) -> None:
        rows = [
            {
                "document_id": doc_id,
                "page_number": page.page_number,
                "raw_text": page.raw_text,
                "was_ocr_applied": page.was_ocr_applied,
                "confidence": page.confidence,
                "width_pt": page.width_pt,
                "height_pt": page.height_pt,
            }
            for page in document.pages
        ]
        if rows:
            self.session.execute(insert(Page), rows)

    def _insert_blocks(self, doc_id: uuid.UUID, document: Document) -> None:
        rows = [
            _block_row(doc_id, page.page_number, block)
            for page in document.pages
            for block in page.blocks
        ]
        if rows:
            self.session.execute(insert(Block), rows)

    def _insert_segments(self, doc_id: uuid.UUID, document: Document) -> None:
        rows = [
            {
                "segment_id": segment.segment_id,
                "document_id": doc_id,
                "start_page": segment.start_page,
                "end_page": segment.end_page,
                "confidence": segment.confidence,
                "title": segment.title,
                "relevance": segment.relevance,
                "matched_keywords": list(segment.matched_keywords),
                "summary": segment.summary,  # denormalized, write-once
            }
            for segment in document.segments
        ]
        if rows:
            self.session.execute(insert(Segment), rows)

    def _insert_references(self, doc_id: uuid.UUID, document: Document) -> None:
        """Inserts summary_references, then their grounding reference_blocks.

        The generated bigint ids are correlated back by ``(segment_id, seq)`` --
        never by RETURNING order -- so each block link points at its reference.
        """
        ref_rows = [
            {"segment_id": segment.segment_id, "seq": seq, "text": reference.text}
            for segment in document.segments
            for seq, reference in enumerate(segment.references or [])
        ]
        if not ref_rows:
            return
        result = self.session.execute(
            insert(SummaryReference).returning(
                SummaryReference.id,
                SummaryReference.segment_id,
                SummaryReference.seq,
            ),
            ref_rows,
        )
        id_by_key = {(row.segment_id, row.seq): row.id for row in result}

        block_rows = [
            {
                "reference_id": id_by_key[(segment.segment_id, seq)],
                "block_id": block_id,
                "document_id": doc_id,
            }
            for segment in document.segments
            for seq, reference in enumerate(segment.references or [])
            for block_id in reference.block_ids
        ]
        if block_rows:
            self.session.execute(insert(ReferenceBlock), block_rows)


# Pure helpers (no repository state)


def _update_row(row: DocumentRow, document: Document) -> None:
    """Copies the document-level metadata onto the row and marks it `done`."""
    row.total_pages = document.total_pages
    row.ocr_engine = document.ocr_engine
    row.enrichment_method = document.enrichment_method
    row.extracted_at = document.extracted_at
    row.enriched_at = document.enriched_at
    row.processing_status = ProcessingStatus.DONE
    row.error_message = None


def _block_row(doc_id: uuid.UUID, page_number: int, block) -> dict:
    x0, y0, x1, y1 = block.bbox if block.bbox is not None else (None, None, None, None)
    return {
        "document_id": doc_id,
        "block_id": block.block_id,
        "page_number": page_number,
        "block_type": block.block_type.value,
        "text": block.text,
        "bbox_x0": x0,
        "bbox_y0": y0,
        "bbox_x1": x1,
        "bbox_y1": y1,
        "source_ref": block.source_ref,
    }


def _page_to_dict(page: Page) -> dict:
    return {
        "page_number": page.page_number,
        "raw_text": page.raw_text,
        "blocks": [_block_to_dict(block) for block in page.blocks],
        "was_ocr_applied": page.was_ocr_applied,
        "confidence": page.confidence,
        "width_pt": page.width_pt,
        "height_pt": page.height_pt,
    }


def _block_to_dict(block: Block) -> dict:
    return {
        "block_id": block.block_id,
        "text": block.text,
        "block_type": block.block_type,
        "bbox": _bbox_to_tuple(block),
        "source_ref": block.source_ref,
    }


def _bbox_to_tuple(block: Block) -> tuple[float, float, float, float] | None:
    if block.bbox_x0 is None:
        return None
    return (block.bbox_x0, block.bbox_y0, block.bbox_x1, block.bbox_y1)


def _segment_to_dict(segment: Segment, pages_by_number: dict) -> dict:
    pages = [
        pages_by_number[number]
        for number in range(segment.start_page, segment.end_page + 1)
        if number in pages_by_number
    ]
    references = [_reference_to_dict(reference) for reference in segment.references] or None
    return {
        "segment_id": segment.segment_id,
        "start_page": segment.start_page,
        "end_page": segment.end_page,
        # Same join convention as make_segment in the segmentation stage.
        "raw_text": "\n\n\n".join(page["raw_text"] for page in pages),
        "pages": pages,
        "confidence": segment.confidence,
        "title": segment.title,
        "references": references,
        "relevance": segment.relevance,
        "matched_keywords": list(segment.matched_keywords),
    }


def _reference_to_dict(reference: SummaryReference) -> dict:
    return {
        "text": reference.text,
        "block_ids": [link.block_id for link in reference.reference_blocks],
    }
