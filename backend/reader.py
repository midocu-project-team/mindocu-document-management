import io

from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
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
from docling_core.types.io import DocumentStream
from datatypes import (
    BlockType,
    CaseFileDocument,
    ContentBlock,
)


# Apple Silicon (MPS) does not support float64, which is required by the RT-DETR-Layout model.
# Therefore, models should be run on the CPU; otherwise, the layout stage will crash.
def _get_pdf_format_options() -> PdfFormatOption:
    accelerator_options = AcceleratorOptions(device=AcceleratorDevice.CPU)

    pipeline_options = PdfPipelineOptions(accelerator_options=accelerator_options)
    return PdfFormatOption(pipeline_options=pipeline_options)


def ocr_convert_pdf(
    pdf_file: io.BytesIO, file_name: str | None = None
) -> ConversionResult:
    stream = DocumentStream(name=file_name, stream=pdf_file)

    converter = DocumentConverter(
        format_options={InputFormat.PDF: _get_pdf_format_options()}
    )
    result = converter.convert(stream)

    return result


# A few possible approaches, but it's up to you: (maybe don't use BytesIO, but a filename as string instead, etc.)
def read_document(file: io.BytesIO, file_name: str | None = None) -> CaseFileDocument:
    pass


# docling label -> general BlockType. Labels not listed (PAGE_HEADER,
# PICTURE, FORM, KEY_VALUE_REGION, CHECKBOX_*, Field*, ...) -> UNKNOWN.
_LABEL_TO_BLOCKTYPE: dict[DocItemLabel, BlockType] = {
    DocItemLabel.TITLE: BlockType.HEADING,
    DocItemLabel.SECTION_HEADER: BlockType.HEADING,
    DocItemLabel.PAGE_FOOTER: BlockType.FOOTER,
    DocItemLabel.TABLE: BlockType.TABLE,
    DocItemLabel.DOCUMENT_INDEX: BlockType.TABLE,  # Table of contents is treated as table
    DocItemLabel.TEXT: BlockType.PARAGRAPH,
    DocItemLabel.PARAGRAPH: BlockType.PARAGRAPH,
    DocItemLabel.LIST_ITEM: BlockType.PARAGRAPH,
    DocItemLabel.CODE: BlockType.PARAGRAPH,
    DocItemLabel.CAPTION: BlockType.PARAGRAPH,
    DocItemLabel.FOOTNOTE: BlockType.PARAGRAPH,
    DocItemLabel.FORMULA: BlockType.PARAGRAPH,
    DocItemLabel.REFERENCE: BlockType.PARAGRAPH,
    DocItemLabel.HANDWRITTEN_TEXT: BlockType.PARAGRAPH,
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
