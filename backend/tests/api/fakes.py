"""Deterministic fake pipeline strategies for the API tests (no LLM/OCR).

Mirrors the StubReader/StubStrategy convention in tests/test_evaluation.py: the
reader returns a fixed two-page CaseFileDocument, the segmenter makes one
segment per page, and the enricher marks the 'Verfügung' page relevant and the
'Prüfvermerk' page irrelevant -- so a real Document flows through the runner.
"""

import io
import itertools

from pipeline import (
    EnrichmentStrategy,
    ReaderStrategy,
    SegmentationStrategy,
    make_segment,
)
from pipeline.datatypes import (
    BlockType,
    CaseFileDocument,
    ContentBlock,
    DocumentSegment,
    EnrichedSegment,
    EnrichmentResult,
    PageContent,
    SegmentationResult,
    SummaryReference,
)

_block_ids = itertools.count()


class FakeReader(ReaderStrategy):
    def read_document(self, file: io.BytesIO, file_name: str | None = None) -> CaseFileDocument:
        size = len(file.getvalue()) if isinstance(file, io.BytesIO) else 0
        pages = [
            _page(1, "Verfügung", "Die Unterbringung wird angeordnet."),
            _page(2, "Prüfvermerk", "Eingangsstempel und Aktenzeichen."),
        ]
        return CaseFileDocument(
            file_name=file_name or "fake.pdf",
            file_size_bytes=size,
            total_pages=len(pages),
            pages=pages,
            errors=[],
            ocr_engine="fake",
        )


class FakeSegmenter(SegmentationStrategy):
    def segment_document(self, doc: CaseFileDocument) -> SegmentationResult:
        segments = [make_segment([page], [1.0]) for page in doc.pages]
        return SegmentationResult(
            document_id=doc.document_id,
            segments=segments,
            segmentation_method="fake",
            errors=[],
        )


class FakeEnricher(EnrichmentStrategy):
    def enrich_segments(self, segmentation: SegmentationResult) -> EnrichmentResult:
        return EnrichmentResult(
            document_id=segmentation.document_id,
            segments=[_enrich(seg) for seg in segmentation.segments],
            enrichment_method="fake",
            relevance_keywords=["Verfügung"],
            errors=[],
        )


# Pure helpers


def _enrich(segment: DocumentSegment) -> EnrichedSegment:
    relevant = any(
        block.block_type is BlockType.HEADING and "Verfügung" in block.text
        for page in segment.pages
        for block in page.blocks
    )
    references = (
        [
            SummaryReference(
                text="Anordnung der Unterbringung.",
                block_ids=[segment.blocks[0].block_id],
            )
        ]
        if relevant
        else None
    )
    return EnrichedSegment.from_segment(
        segment,
        title="Verfügung des Gerichts" if relevant else None,
        references=references,
        relevance=relevant,
        matched_keywords=["Verfügung"] if relevant else ["Prüfvermerk"],
    )


def _page(number: int, heading: str, body: str) -> PageContent:
    return PageContent(
        page_number=number,
        raw_text=f"{heading}\n{body}",
        blocks=[
            ContentBlock(block_id=next(_block_ids), text=heading, block_type=BlockType.HEADING, bbox=(72, 700, 540, 740)),
            ContentBlock(block_id=next(_block_ids), text=body, block_type=BlockType.PARAGRAPH, bbox=(72, 600, 540, 690)),
        ],
        was_ocr_applied=False,
        confidence=0.95,
        width_pt=612,
        height_pt=792,
    )
