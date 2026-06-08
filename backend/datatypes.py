from dataclasses import dataclass, field
import enum
import uuid
from datetime import datetime

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
@dataclass
class ContentBlock:
    text: str
    block_type: BlockType
    bbox: BoundingBox | None  # x0, y0, x1, y1
    source_ref: str | None = (
        None  # Common reference ID for grouping related ContentBlocks (e.g., fragments of the same item)
    )


@dataclass
class PageContent:
    page_number: int  # 1-indexed
    raw_text: str  # Full text of the page (joined)
    blocks: list[ContentBlock]  # Structured blocks (useful for later segmentation)
    was_ocr_applied: bool
    confidence: float | None
    width_pt: float  # Page width in points
    height_pt: float  # Page height in points


@dataclass
class PageExtractionError:
    page_number: int
    error_type: PageExtractionErrorType
    message: str


@dataclass
class CaseFileDocument:
    # kw_only ensures that the default value for document_id is allowed even when required fields follow.
    document_id: str = field(
        default_factory=lambda: str(uuid.uuid4()), kw_only=True
    )  # UUID, generated when loading
    file_name: str
    file_size_bytes: int
    total_pages: int
    pages: list[PageContent]  # All successfully loaded pages
    errors: list[
        PageExtractionError
    ]  # Store all pages that could not be read successfully
    extracted_at: datetime
    ocr_engine: str


###################################


###################################
# Task 2: Output as SegmentationResult
###################################
@dataclass
class DocumentSegment:
    segment_id: str  # UUID
    start_page: int  # 1-indexed, inclusive
    end_page: int  # 1-indexed, inclusive
    raw_text: str  # Joined text of all pages in the segment
    pages: list[PageContent]  # Taken directly from Task 1
    confidence: float | None  # How certain the model is for the boundary


@dataclass
class SegmentationResult:
    document_id: str  # Same ID as in CaseFileDocument
    segments: list[DocumentSegment]
    segmented_at: datetime
    segmentation_method: str  # e.g., "llm", "rule-based", "hybrid"
    unassigned_pages: list[
        PageContent
    ]  # Pages that could not be assigned to any segment
    errors: list[PageExtractionError]  # Pages with extraction errors


####################################
