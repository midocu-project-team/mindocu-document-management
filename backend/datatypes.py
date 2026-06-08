from pydantic import BaseModel, Field
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
class ContentBlock(BaseModel):
    text: str
    block_type: BlockType
    bbox: BoundingBox | None  # x0, y0, x1, y1
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


class SegmentationResult(BaseModel):
    document_id: str  # Same ID as in CaseFileDocument
    segments: list[DocumentSegment]
    segmented_at: datetime = Field(default_factory=datetime.now)
    segmentation_method: str  # e.g., "llm", "rule-based", "hybrid"
    errors: list[PageExtractionError]  # Pages with extraction errors


class SimilarityResult(BaseModel):
    confidence: float = Field(ge=0, le=1)
    are_similar: bool
    # reasoning: str # take out to test model performance


####################################
