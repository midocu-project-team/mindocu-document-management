from collections import defaultdict
from datetime import datetime
import io
import math
import os

from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import ConfidenceReport, InputFormat
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import (
    TableFormerMode,
    ThreadedPdfPipelineOptions,
)
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.threaded_standard_pdf_pipeline import ThreadedStandardPdfPipeline
from docling_core.types.io import DocumentStream
from backend.datatypes import (
    BlockType,
    CaseFileDocument,
    ContentBlock,
    PageContent,
)


# ============================================================================
# OCR / PDF conversion
# ============================================================================

# docling's default OCR engine for the PDF pipeline (see conversion logs)
OCR_ENGINE = "docling:rapidocr"


# Apple Silicon (MPS) does not support float64, which is required by the RT-DETR-Layout model.
# Therefore, models should be run on the CPU; otherwise, the layout stage will crash.
# This is needed because the backend will likely run on a Silicon Mac Mini
def _get_pdf_format_options() -> PdfFormatOption:
    num_cores = os.cpu_count() or 1

    accelerator_options = AcceleratorOptions(
        device=AcceleratorDevice.CPU, num_threads=num_cores
    )
    pipeline_options = ThreadedPdfPipelineOptions(
        do_ocr=True,
        do_table_structure=True,
        generate_page_images=False,
        generate_picture_images=False,
        images_scale=1.0,
        accelerator_options=accelerator_options,
        ocr_batch_size=4,
        layout_batch_size=4,
        table_batch_size=4,
        document_timeout=60 * 30,  # reading may not take longer than 30 minutes
    )

    pipeline_options.table_structure_options.mode = TableFormerMode.FAST

    return PdfFormatOption(
        pipeline_options=pipeline_options,
        pipeline_cls=ThreadedStandardPdfPipeline,
        backend=PyPdfiumDocumentBackend,
    )


def _page_confidence(report: ConfidenceReport, page_no: int) -> float | None:
    """Mean confidence score of the page; NaN (no score) -> None."""
    score = report.pages[page_no].mean_score
    return None if math.isnan(score) else float(score)


def _was_ocr_applied(report: ConfidenceReport, page_no: int) -> bool:
    """OCR contributed on the page iff its ocr_score is set (not NaN).

    Note: page cells (TextCell.from_ocr) are cleared during assembling, so the
    confidence report is the only per-page OCR signal left after conversion.
    """
    return not math.isnan(report.pages[page_no].ocr_score)


def ocr_convert_pdf(
    pdf_file: io.BytesIO, file_name: str | None = None
) -> ConversionResult:
    stream = DocumentStream(name=file_name, stream=pdf_file)

    converter = DocumentConverter(
        format_options={InputFormat.PDF: _get_pdf_format_options()}
    )
    result = converter.convert(stream)

    return result


# ============================================================================
# Document assembly (main function)
# ============================================================================


def read_document(file: io.BytesIO, file_name: str | None = None) -> CaseFileDocument:
    # Capture size before conversion: docling closes the stream after reading it.
    file_size_bytes = file.getbuffer().nbytes

    conversion_result = ocr_convert_pdf(file, file_name)
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

    return CaseFileDocument(
        file_name=file_name or "",
        file_size_bytes=file_size_bytes,
        total_pages=len(document.pages),
        pages=pages,
        errors=[],
        extracted_at=datetime.now(),
        ocr_engine=OCR_ENGINE,
    )


# ============================================================================
# DocItem -> ContentBlock mapping
# ============================================================================

from docling_core.types.doc.document import (
    DocItem,
    DoclingDocument,
    FloatingItem,
    FormItem,
    KeyValueItem,
    PictureItem,
    TableItem,
    TextItem,
)
from docling_core.types.doc.labels import DocItemLabel

# docling label -> general BlockType. Labels not listed (PAGE_HEADER, MARKER,
# and any future/unknown labels) -> UNKNOWN.
_LABEL_TO_BLOCKTYPE: dict[DocItemLabel, BlockType] = {
    # Headings
    DocItemLabel.TITLE: BlockType.HEADING,
    DocItemLabel.SECTION_HEADER: BlockType.HEADING,
    # Lists
    DocItemLabel.LIST_ITEM: BlockType.LIST,
    # Tables
    DocItemLabel.TABLE: BlockType.TABLE,
    DocItemLabel.DOCUMENT_INDEX: BlockType.TABLE,  # Table of contents is treated as table
    # Paragraph-like text (deliberately folded together)
    DocItemLabel.TEXT: BlockType.PARAGRAPH,
    DocItemLabel.PARAGRAPH: BlockType.PARAGRAPH,
    DocItemLabel.CODE: BlockType.PARAGRAPH,
    DocItemLabel.CAPTION: BlockType.PARAGRAPH,
    DocItemLabel.FOOTNOTE: BlockType.PARAGRAPH,
    DocItemLabel.FORMULA: BlockType.PARAGRAPH,
    DocItemLabel.REFERENCE: BlockType.PARAGRAPH,
    # Images: logos, signatures, stamps, figures (strong segmentation signal)
    DocItemLabel.PICTURE: BlockType.IMAGE,
    DocItemLabel.CHART: BlockType.IMAGE,
    # Structured form / key-value regions (one coarse bucket, not per-field)
    DocItemLabel.FORM: BlockType.FORM,
    DocItemLabel.KEY_VALUE_REGION: BlockType.FORM,
    DocItemLabel.FIELD_REGION: BlockType.FORM,
    DocItemLabel.FIELD_HEADING: BlockType.FORM,
    DocItemLabel.FIELD_ITEM: BlockType.FORM,
    DocItemLabel.FIELD_KEY: BlockType.FORM,
    DocItemLabel.FIELD_VALUE: BlockType.FORM,
    DocItemLabel.FIELD_HINT: BlockType.FORM,
    DocItemLabel.EMPTY_VALUE: BlockType.FORM,
    DocItemLabel.GRADING_SCALE: BlockType.FORM,
    DocItemLabel.CHECKBOX_SELECTED: BlockType.FORM,
    DocItemLabel.CHECKBOX_UNSELECTED: BlockType.FORM,
    # Footer / handwriting
    DocItemLabel.PAGE_FOOTER: BlockType.FOOTER,  # NOTE: currently dead (FURNITURE layer, not traversed)
    DocItemLabel.HANDWRITTEN_TEXT: BlockType.HANDWRITTEN,
}


def _map_label(label: DocItemLabel) -> BlockType:
    # Returns the corresponding BlockType for a given DocItemLabel, or UNKNOWN if not found.
    return _LABEL_TO_BLOCKTYPE.get(label, BlockType.UNKNOWN)


def item_to_blocks(
    item: DocItem, doc: DoclingDocument
) -> list[tuple[int, ContentBlock]]:
    # Prefer TextItem (some elements inherit from Text and FloatingItem)
    if isinstance(item, TextItem):
        return text_item_to_blocks(item)
    elif isinstance(item, FloatingItem):
        return floating_items_to_blocks(item, doc)

    # Fallback for plain DocItems (e.g., FieldRegionItem, FieldItem) and unknown types
    return fallback_items_to_blocks(item)


def text_item_to_blocks(item: TextItem) -> list[tuple[int, ContentBlock]]:
    """Splits a DocItem into (page_no, ContentBlock) for each ProvenanceItem."""
    blocks = []
    for prov in item.prov:
        start, end = prov.charspan
        blocks.append(
            (
                prov.page_no,
                ContentBlock(
                    text=item.text[start:end],
                    block_type=_map_label(item.label),
                    bbox=prov.bbox.as_tuple(),
                    source_ref=item.self_ref,  # links fragments of the same item
                ),
            )
        )

    return blocks


def floating_items_to_blocks(item: DocItem, doc) -> list[tuple[int, ContentBlock]]:
    """
    Converts a non-textual DocItem into (page_no, ContentBlock) per prov.

    No charspan slicing: full text only for the first prov, subsequent provs only provide bbox (empty text).
    """
    text = _floating_text(item, doc)
    block_type = _map_label(item.label)

    out = []
    for i, prov in enumerate(item.prov):
        out.append(
            (
                prov.page_no,
                ContentBlock(
                    text=(
                        text if i == 0 else ""
                    ),  # Following rectangles: only position, no text
                    block_type=block_type,
                    bbox=prov.bbox.as_tuple(),
                    source_ref=item.self_ref,
                ),
            )
        )
    return out


def fallback_items_to_blocks(item: DocItem) -> list[tuple[int, ContentBlock]]:
    """
    Generic handling for plain/unknown DocItems.

    Applies to DocItems that are neither TextItem nor FloatingItem
    (FieldRegionItem, FieldItem), as well as for future/unexpected types.
    No known text source and no charspan: best-effort text on the
    first prov, following provs only as bbox (no text).
    """
    # Plain DocItems often have no .text -> use label as placeholder text
    text = getattr(item, "text", "") or f"[{item.label.value}]"
    block_type = _map_label(item.label)

    blocks = []
    for i, prov in enumerate(item.prov):
        blocks.append(
            (
                prov.page_no,
                ContentBlock(
                    text=(
                        text if i == 0 else ""
                    ),  # Following rectangles: only position, no text
                    block_type=block_type,
                    bbox=prov.bbox.as_tuple(),
                    source_ref=item.self_ref,
                ),
            )
        )
    return blocks


def _floating_text(item: DocItem, doc: DoclingDocument) -> str:
    """Text representation for non-textual DocItems."""
    if isinstance(item, TableItem):
        return item.export_to_markdown(doc)
    if isinstance(item, PictureItem):
        return item.caption_text(doc) or "[Image]"
    if isinstance(item, (KeyValueItem, FormItem)):
        # Attempt to concatenate all cell texts, or use placeholder if empty
        return " ".join(c.text for c in item.graph.cells) or "[Form]"
    return getattr(item, "text", "")  # Fallback: naked DocItems / unknown
