"""Repository round-trip: the relational save/load rebuilds a whole Document.

Highest-risk path is the summary-reference persistence: bigint ids are correlated
back by ``(segment_id, seq)`` and the M:N grounding must keep each reference's
block_ids. This also covers the all-or-nothing bbox column mapping.
"""

import uuid
from datetime import datetime

from api.repositories import CaseRepository, DocumentRepository
from pipeline import Document, make_segment
from pipeline.datatypes import (
    BlockType,
    ContentBlock,
    EnrichedSegment,
    PageContent,
    SummaryReference,
)


def _build_document() -> Document:
    """A one-page document whose single segment has three ordered references."""
    page = PageContent(
        page_number=1,
        raw_text="Verfügung\nInhalt",
        blocks=[
            ContentBlock(block_id=10, text="h", block_type=BlockType.HEADING, bbox=(1, 2, 3, 4)),
            ContentBlock(block_id=11, text="p", block_type=BlockType.PARAGRAPH, bbox=None),
            ContentBlock(block_id=12, text="q", block_type=BlockType.PARAGRAPH, bbox=(5, 6, 7, 8)),
        ],
        was_ocr_applied=False,
        confidence=0.9,
        width_pt=612,
        height_pt=792,
    )
    segment = EnrichedSegment.from_segment(
        make_segment([page], [0.95]),
        title="Verfügung",
        references=[
            SummaryReference(text="A.", block_ids=[10, 12]),
            SummaryReference(text="B.", block_ids=[11]),
            SummaryReference(text="C.", block_ids=[10]),
        ],
        relevance=True,
        matched_keywords=["Verfügung"],
    )
    now = datetime.now()
    return Document(
        document_id=uuid.uuid4(),
        file_name="t.pdf",
        file_size_bytes=1,
        total_pages=1,
        ocr_engine="fake",
        pages=[page],
        segments=[segment],
        enrichment_method="fake",
        extracted_at=now,
        enriched_at=now,
    )


def _persist(session_factory, document: Document) -> None:
    with session_factory() as session:
        case = CaseRepository(session).create("Fall")
        session.flush()  # need case.id for the FK
        repo = DocumentRepository(session)
        repo.create_pending(
            document_id=document.document_id,
            case_id=case.id,
            file_name=document.file_name,
            file_size_bytes=document.file_size_bytes,
            pdf_path="x.pdf",
        )
        repo.save_document(document.document_id, document)
        session.commit()


def test_segment_references_and_bbox_roundtrip(session_factory):
    document = _build_document()
    _persist(session_factory, document)

    with session_factory() as session:
        loaded = DocumentRepository(session).load_document(document.document_id)

    assert loaded.document_id == document.document_id
    segment = loaded.segments[0]
    # References come back in seq order with their grounded block_ids intact.
    assert [r.text for r in segment.references or []] == ["A.", "B.", "C."]
    assert [r.block_ids for r in segment.references or []] == [[10, 12], [11], [10]]
    # Summary is the denormalized join of the reference texts.
    assert segment.summary == "A. B. C."

    blocks = loaded.pages[0].blocks
    assert [b.bbox for b in blocks] == [(1, 2, 3, 4), None, (5, 6, 7, 8)]


def test_duplicate_block_ids_in_a_reference_do_not_break_the_save(session_factory):
    """Regression: an LLM may cite the same block twice within one reference;
    that used to violate the (reference_id, block_id) PK. The datatype now
    normalizes block_ids to a sorted set, so the save must succeed."""
    document = _build_document()
    document.segments[0].references = [
        SummaryReference(text="A.", block_ids=[12, 10, 10, 12]),
    ]
    _persist(session_factory, document)

    with session_factory() as session:
        loaded = DocumentRepository(session).load_document(document.document_id)

    assert [r.block_ids for r in loaded.segments[0].references or []] == [[10, 12]]


def test_irrelevant_segment_has_no_references(session_factory):
    """A segment saved with references=None comes back as None (not [])."""
    document = _build_document()
    document.segments[0].references = None
    _persist(session_factory, document)

    with session_factory() as session:
        loaded = DocumentRepository(session).load_document(document.document_id)

    assert loaded.segments[0].references is None
    assert loaded.segments[0].summary is None
