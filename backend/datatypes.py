from dataclasses import dataclass
from typing import Literal
from datetime import datetime

###################################
# Task 1: Output als CaseFileDocument 
###################################
@dataclass
class TextBlock:
    text: str
    block_type: Literal["paragraph", "heading", "table", "footer", "unknown"]
    bbox: tuple[float, float, float, float] | None  # x0, y0, x1, y1

@dataclass
class PageContent:
    page_number: int           # 1-indexed
    raw_text: str              # Volltext der Seite (joined)
    blocks: list[TextBlock]    # strukturierte Blöcke (für spätere Segmentierung nützlich)
    was_ocr_applied: bool
    confidence: float | None
    width_pt: float            # Seitengröße in Points
    height_pt: float

@dataclass
class ExtracedPageError:
    page_number: int
    error_type: Literal["ocr_failed", "corrupted", "encrypted", "timeout"]
    message: str

@dataclass
class CaseFileDocument:
    document_id: str           # UUID, generiert beim Einlesen
    source_path: str
    file_size_bytes: int
    total_pages: int
    pages: list[PageContent] # Alle erfolgreich eingelesenen Seiten
    errors: list[ExtracedPageError] # Speichere alle nicht erfolgreich gelesenen Dateien
    extracted_at: datetime
    ocr_engine: str         

###################################



###################################
# Task 2: Output als SegmentationResult 
###################################
@dataclass
class DocumentSegment:
    segment_id: str           # UUID
    start_page: int           # 1-indexed, inklusiv
    end_page: int             # 1-indexed, inklusiv
    raw_text: str             # joined text aller Seiten des Segments
    pages: list[PageContent]  # direkt aus Task 1
    confidence: float | None  # wie sicher ist das Modell bei dieser Grenze

@dataclass
class SegmentationResult:
    document_id: str                    # dieselbe ID wie im CaseFileDocument
    segments: list[DocumentSegment]
    segmented_at: datetime
    segmentation_method: str            # z.B. "llm", "rule-based", "hybrid"
    unassigned_pages: list[PageContent] # Seiten die keinem Segment zugeordnet werden konnten
    errors: list[ExtracedPageError]     # Fehlerhafte Seiten
####################################