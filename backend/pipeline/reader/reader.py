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
from .mapping import item_to_blocks
from .options import default_pdf_format_options

# ============================================================================
# Document assembly (main function)
# ============================================================================


def read_document(
    file: io.BytesIO,
    file_name: str | None = None,
    pdf_format_options: PdfFormatOption | None = None,
) -> CaseFileDocument:
    # Capture size before conversion: docling closes the stream after reading it.
    file_size_bytes = file.getbuffer().nbytes

    conversion_result = ocr_convert_pdf(file, file_name, pdf_format_options)
    document = conversion_result.document
    report = conversion_result.confidence

    # 1) Collect blocks per page (the only thing that genuinely needs accumulation)
    blocks_by_page: dict[int, list[ContentBlock]] = defaultdict(list)
    for item, _ in document.iterate_items():
        for page_no, block in item_to_blocks(item, doc=document):
            blocks_by_page[page_no].append(block)

    # 2) Build one PageContent per page, pulling metadata from the docling pages
    #    and per-page confidence / OCR signal from the confidence report.
    pages = [
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
    # TODO: Stich together raw_text-Field from blocks instead of exporting markdown
    # because export_to_markdown(page_no) sometimes contains text from page_no+1

    return CaseFileDocument(
        file_name=file_name or "",
        file_size_bytes=file_size_bytes,
        total_pages=len(document.pages),
        pages=pages,
        errors=[],
        extracted_at=datetime.now(),
        ocr_engine="tesseract-cli:deu+eng",
    )


##########################


def ocr_convert_pdf(
    pdf_file: io.BytesIO,
    file_name: str | None = None,
    pdf_format_options: PdfFormatOption | None = None,
) -> ConversionResult:

    if pdf_format_options is None:
        pdf_format_options = default_pdf_format_options()

    stream = DocumentStream(name=file_name, stream=pdf_file)

    converter = DocumentConverter(format_options={InputFormat.PDF: pdf_format_options})
    result = converter.convert(stream)

    return result


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
