from pydantic import BaseModel, Field
import enum
import uuid
from datetime import datetime

# Stage-1 contract: (x0, y0, x1, y1) in PDF points with a BOTTOM-LEFT origin
# (y grows upward). Every ReaderStrategy backend must emit this convention;
# a top-left-origin consumer (e.g. the frontend) flips y via the page height.
type BoundingBox = tuple[float, float, float, float]


class BlockType(enum.StrEnum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    LIST = "list"
    TABLE = "table"
    IMAGE = "image"  # logos, signatures, stamps, figures (PICTURE/CHART)
    FORM = "form"  # form / key-value regions, fields, checkboxes
    HANDWRITTEN = "handwritten"
    FOOTER = "footer"
    UNKNOWN = "unknown"


class PageExtractionErrorType(enum.StrEnum):
    OCR_FAILED = "ocr_failed"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


###################################
# Task 1: Output as CaseFileDocument
###################################
class ContentBlock(BaseModel):
    text: str
    block_type: BlockType
    bbox: BoundingBox | None  # see BoundingBox: PDF points, bottom-left origin
    source_ref: str | None = (
        None  # Common reference ID for grouping related ContentBlocks (e.g., fragments of the same item)
    )


class PageContent(BaseModel):
    page_number: int  # 1-indexed
    raw_text: str  # Full text of the page (joined)
    blocks: list[ContentBlock]  # Structured blocks (useful for later segmentation)
    was_ocr_applied: bool
    confidence: float | None
    width_pt: float  # Page width in points
    height_pt: float  # Page height in points


class PageExtractionError(BaseModel):
    page_number: int
    error_type: PageExtractionErrorType
    message: str


class CaseFileDocument(BaseModel):
    # kw_only ensures that the default value for document_id is allowed even when required fields follow.
    document_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )  # UUID, generated when loading
    file_name: str
    file_size_bytes: int
    total_pages: int
    pages: list[PageContent]  # All successfully loaded pages
    errors: list[
        PageExtractionError
    ]  # Store all pages that could not be read successfully
    extracted_at: datetime = Field(default_factory=datetime.now)
    ocr_engine: str


###################################


###################################
# Task 2: Output as SegmentationResult
###################################


class DocumentSegment(BaseModel):
    segment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))  # UUID

    start_page: int  # 1-indexed, inclusive
    end_page: int  # 1-indexed, inclusive
    raw_text: str  # Joined text of all pages in the segment
    pages: list[PageContent]  # Taken directly from Task 1
    confidence: float | None  # How certain the model is for the boundary


class SegmentationErrorType(enum.StrEnum):
    LLM_CALL_FAILED = "llm_call_failed"  # the model call raised
    INVALID_OUTPUT = "invalid_output"  # plan unparseable / unusable
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class SegmentationError(BaseModel):
    error_type: SegmentationErrorType
    message: str
    # Optional scope. Both None => the whole document. A range => e.g. a failed
    # window or the boundary between two pages. Not page-bound like stage 1.
    start_page: int | None = None
    end_page: int | None = None


class SegmentationResult(BaseModel):
    document_id: str  # Same ID as in CaseFileDocument
    segments: list[DocumentSegment]
    segmented_at: datetime = Field(default_factory=datetime.now)
    segmentation_method: str  # e.g., "llm", "rule-based", "hybrid"
    errors: list[SegmentationError]  # Stage-2 errors (not page-bound)


####################################


###################################
# Task 3: Output as EnrichmentResult
###################################


class EnrichmentErrorType(enum.StrEnum):
    LLM_CALL_FAILED = "llm_call_failed"  # title/summary generation raised
    INVALID_OUTPUT = "invalid_output"  # model response unparseable / unusable
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class EnrichmentError(BaseModel):
    error_type: EnrichmentErrorType
    message: str
    # Optional scope: None => the whole document, otherwise the affected segment.
    segment_id: str | None = None


class EnrichedSegment(DocumentSegment):
    """A DocumentSegment enriched with stage-3 metadata.

    Inherits all stage-2 fields unchanged; `confidence` remains the
    *boundary* confidence from segmentation, not an enrichment confidence.
    """

    title: str | None  # Short document title (LLM-generated); None if generation failed
    summary: str | None  # AI summary of the segment (LLM-generated); None if generation failed

    relevance: bool  # Keyword-based decision, deterministic
    matched_keywords: list[str]  # Keywords whose match decided relevance (empty => default applied)

    @classmethod
    def from_segment(
        cls,
        segment: DocumentSegment,
        *,
        title: str | None,
        summary: str | None,
        relevance: bool,
        matched_keywords: list[str],
    ) -> "EnrichedSegment":
        """Build an EnrichedSegment from an existing segment, preserving its segment_id."""
        return cls(
            **segment.model_dump(),
            title=title,
            summary=summary,
            relevance=relevance,
            matched_keywords=matched_keywords,
        )


class EnrichmentResult(BaseModel):
    document_id: str  # Same ID as in CaseFileDocument
    segments: list[EnrichedSegment]  # All segments from stage 2, enriched with metadata
    enriched_at: datetime = Field(default_factory=datetime.now)
    enrichment_method: str  # e.g., "llm+keyword"
    relevance_keywords: list[str]  # Keyword set used for the relevance decision
    errors: list[EnrichmentError]  # Stage-3 errors (segment-scoped or global)


####################################
