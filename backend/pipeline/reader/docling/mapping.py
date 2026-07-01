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
from pydantic import BaseModel
from pipeline.datatypes import BlockType, BoundingBox

class RawContentBlock(BaseModel):
    text: str
    block_type: BlockType
    bbox: BoundingBox | None  # see BoundingBox: PDF points, bottom-left origin
    source_ref: str | None = (
        None  # Common reference ID for grouping related ContentBlocks (e.g., fragments of the same item)
    )


# MAIN MAPPING FUNCTION #
def item_to_blocks(
    item: DocItem, doc: DoclingDocument
) -> list[tuple[int, RawContentBlock]]:
    """Splits a DocItem into (page_no, ContentBlock) for each ProvenanceItem."""

    # Prefer TextItem (some elements inherit from Text and FloatingItem)
    if isinstance(item, TextItem):
        return _text_item_to_blocks(item)
    elif isinstance(item, FloatingItem):
        return _floating_items_to_blocks(item, doc)

    # Fallback for plain DocItems (e.g., FieldRegionItem, FieldItem) and unknown types
    return _fallback_items_to_blocks(item)


#########################


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


def _text_item_to_blocks(item: TextItem) -> list[tuple[int, RawContentBlock]]:
    """Splits a TextItem into (page_no, ContentBlock) for each ProvenanceItem."""

    text = item.text
    block_type = _map_label(item.label)

    blocks = []
    for prov in item.prov:
        start, end = prov.charspan
        blocks.append(
            (
                prov.page_no,
                RawContentBlock(
                    text=text[start:end],
                    block_type=block_type,
                    bbox=prov.bbox.as_tuple(),
                    source_ref=item.self_ref,  # links fragments of the same item
                ),
            )
        )

    return blocks


def _floating_items_to_blocks(item: FloatingItem, doc) -> list[tuple[int, RawContentBlock]]:
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
                RawContentBlock(
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


def _fallback_items_to_blocks(item: DocItem) -> list[tuple[int, RawContentBlock]]:
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
                RawContentBlock(
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


def _floating_text(item: FloatingItem, doc: DoclingDocument) -> str:
    """Text representation for non-textual DocItems."""
    if isinstance(item, TableItem):
        return item.export_to_markdown(doc)
    if isinstance(item, PictureItem):
        return item.caption_text(doc) or "[Image]"
    if isinstance(item, (KeyValueItem, FormItem)):
        # Attempt to concatenate all cell texts, or use placeholder if empty
        return " ".join(c.text for c in item.graph.cells) or "[Form]"
    return getattr(item, "text", "")  # Fallback: naked DocItems / unknown
