"""The aggregated ``Document`` -- the whole pipeline's combined output.

A ``Document`` merges the three stage outputs (``CaseFileDocument``,
``SegmentationResult``, ``EnrichmentResult``) into one self-contained model:
the pages once at the top level (single source of truth) plus the enriched
segments and the per-stage error lists. It is pure composition -- no app, DB
or HTTP knowledge -- so it lives in ``pipeline`` next to the stages it
aggregates and is the value ``PipelineRunner.run`` returns.

``schema_version`` is carried for the persistence layer: stored ``Document``
JSON is versioned so a future field change can be upcast on read.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from pipeline.datatypes import (
    CaseFileDocument,
    EnrichedSegment,
    EnrichmentError,
    EnrichmentResult,
    PageContent,
    PageExtractionError,
    SegmentationError,
    SegmentationResult,
)

# Bump when the persisted Document shape changes; the repository upcasts on read.
CURRENT_SCHEMA_VERSION = 1


class Document(BaseModel):
    """A fully processed case-file document: metadata, pages and enriched segments."""

    document_id: str
    file_name: str
    file_size_bytes: int
    total_pages: int
    ocr_engine: str

    # The pages live here exactly once (single source of truth). The segments
    # reference page ranges via start_page/end_page; the persistence layer
    # strips their embedded pages to avoid storing the text twice.
    pages: list[PageContent]
    segments: list[EnrichedSegment]
    enrichment_method: str

    extraction_errors: list[PageExtractionError] = Field(default_factory=list)
    segmentation_errors: list[SegmentationError] = Field(default_factory=list)
    enrichment_errors: list[EnrichmentError] = Field(default_factory=list)

    extracted_at: datetime
    enriched_at: datetime
    schema_version: int = CURRENT_SCHEMA_VERSION

    @classmethod
    def from_pipeline(
        cls,
        doc: CaseFileDocument,
        seg: SegmentationResult,
        enr: EnrichmentResult,
    ) -> "Document":
        """Merges the three stage outputs into one ``Document``.

        The ``SegmentationResult`` is required (not derivable from the others)
        because its stage-2 errors live nowhere else; stage-1 errors come from
        ``doc`` and stage-3 errors from ``enr``.
        """
        return cls(
            document_id=doc.document_id,
            file_name=doc.file_name,
            file_size_bytes=doc.file_size_bytes,
            total_pages=doc.total_pages,
            ocr_engine=doc.ocr_engine,
            pages=doc.pages,
            segments=enr.segments,
            enrichment_method=enr.enrichment_method,
            extraction_errors=doc.errors,
            segmentation_errors=seg.errors,
            enrichment_errors=enr.errors,
            extracted_at=doc.extracted_at,
            enriched_at=enr.enriched_at,
        )
