from collections import defaultdict
from datetime import datetime
import io
import math
from docling.datamodel.base_models import ConfidenceReport, InputFormat
from docling.datamodel.document import ConversionResult
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.io import DocumentStream
from pipeline.datatypes import (
    CaseFileDocument,
    ContentBlock,
    PageContent,
)
from pipeline.reader.strategy import ReaderStrategy
from .mapping import item_to_blocks
from .options import default_pdf_format_options


class DoclingReaderStrategy(ReaderStrategy):
    """Stage-1 reader built on docling (layout model + OCR).

    The docling configuration (OCR engine, pipeline class, backend) is
    constructor state: pass a custom ``PdfFormatOption`` to swap any of them
    without touching the reading code; ``None`` selects the default (threaded
    pipeline, CPU, Tesseract CLI deu+eng).
    """

    def __init__(self, pdf_format_options: PdfFormatOption | None = None):
        self._pdf_format_options = pdf_format_options or default_pdf_format_options()

    def read_document(
        self, file: io.BytesIO, file_name: str | None = None
    ) -> CaseFileDocument:
        # Capture size before conversion: docling closes the stream after reading it.
        file_size_bytes = file.getbuffer().nbytes
        result = ocr_convert_pdf(file, file_name, self._pdf_format_options)
        return CaseFileDocument(
            file_name=file_name or "",
            file_size_bytes=file_size_bytes,
            total_pages=len(result.document.pages),
            pages=_build_pages(result),
            errors=[],
            extracted_at=datetime.now(),
            ocr_engine=_ocr_engine_label(self._pdf_format_options),
        )


def ocr_convert_pdf(
    pdf_file: io.BytesIO,
    file_name: str | None = None,
    pdf_format_options: PdfFormatOption | None = None,
) -> ConversionResult:
    """Raw docling conversion — the escape hatch below the CaseFileDocument mapping."""
    if pdf_format_options is None:
        pdf_format_options = default_pdf_format_options()

    stream = DocumentStream(name=file_name or "", stream=pdf_file)

    converter = DocumentConverter(format_options={InputFormat.PDF: pdf_format_options})
    result = converter.convert(stream)

    return result


# ============================================================================
# Pure helpers (no strategy state)
# ============================================================================


def _build_pages(conversion_result: ConversionResult) -> list[PageContent]:
    """One PageContent per converted page: blocks, confidence and OCR signal."""
    document = conversion_result.document
    report = conversion_result.confidence

    # Collect blocks per page (the only thing that genuinely needs accumulation)
    blocks_by_page: dict[int, list[ContentBlock]] = defaultdict(list)
    for item, idx in document.iterate_items():
        for page_no, raw_block in item_to_blocks(item, doc=document):

            # propagate raw blocks with unique document wide idx as id
            block = ContentBlock(block_id=idx, **raw_block.model_dump())
            blocks_by_page[page_no].append(block)

    # TODO: Stitch together raw_text from blocks instead of exporting markdown
    # because export_to_markdown(page_no) sometimes contains text from page_no+1
    return [
        PageContent(
            page_number=page.page_no,
            raw_text=document.export_to_markdown(page_no=page.page_no),
            blocks=blocks_by_page[page.page_no],
            was_ocr_applied=_was_ocr_applied(report, page.page_no),
            confidence=_page_confidence(report, page.page_no),
            width_pt=page.size.width if page.size else 0.0,
            height_pt=page.size.height if page.size else 0.0,
        )
        for page in conversion_result.pages
    ]


def _ocr_engine_label(pdf_format_options: PdfFormatOption) -> str:
    """Derives the CaseFileDocument.ocr_engine tag from the configured options.

    A hardcoded label would silently lie as soon as custom options are
    injected; ``kind`` is docling's discriminator for the OCR engine.
    """
    ocr = getattr(pdf_format_options.pipeline_options, "ocr_options", None)
    if ocr is None:
        return "unknown"
    return f"{ocr.kind}:{'+'.join(ocr.lang)}"


def _page_confidence(report: ConfidenceReport, page_no: int) -> float | None:
    """Mean confidence score of the page; NaN (no score) -> None."""
    score = report.pages[page_no].mean_score
    return None if math.isnan(score) else float(score)


def _was_ocr_applied(report: ConfidenceReport, page_no: int) -> bool:
    """OCR contributed on the page iff its ocr_score is set (not NaN).

    Note: page cells (TextCell.from_ocr) are cleared during assembling, so the
    confidence report is the only per-page OCR signal left after conversion.

    Limitation: this only works for engines that report per-cell OCR confidence
    (e.g. RapidOCR). The Tesseract CLI does not, so ocr_score stays NaN and this
    returns False even on pages that were OCR'd. With the current Tesseract
    default the flag is therefore unreliable; switch ocr_options back to RapidOCR
    if a trustworthy per-page OCR signal is required.
    """
    return not math.isnan(report.pages[page_no].ocr_score)
