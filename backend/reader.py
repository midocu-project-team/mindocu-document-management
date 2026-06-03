import io

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
from datatypes import (
    BlockType,
    CaseFileDocument,
    ContentBlock,
)


# Ein paar Ansätze, ist aber selbst überlassen: (vlt. auch kein BytesObjekt als Input sondern file name als string direkt, etc.)
def read_document(file: io.BytesIO) -> CaseFileDocument:
    pass


# docling-Label -> grober BlockType. Nicht aufgeführte Labels (PAGE_HEADER,
# PICTURE, FORM, KEY_VALUE_REGION, CHECKBOX_*, Field*, ...) -> UNKNOWN.
_LABEL_TO_BLOCKTYPE: dict[DocItemLabel, BlockType] = {
    DocItemLabel.TITLE: BlockType.HEADING,
    DocItemLabel.SECTION_HEADER: BlockType.HEADING,
    DocItemLabel.PAGE_FOOTER: BlockType.FOOTER,
    DocItemLabel.TABLE: BlockType.TABLE,
    DocItemLabel.DOCUMENT_INDEX: BlockType.TABLE,  # Inhaltsverzeichnis ist tabellarisch
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
    return _LABEL_TO_BLOCKTYPE.get(label, BlockType.UNKNOWN)


def item_to_blocks(
    item: DocItem, doc: DoclingDocument
) -> list[tuple[int, ContentBlock]]:

    # check for TextItem first
    # some elements inherit from Text and FloatingItem
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
    """Converts a non-textual DocItem into (page_no, ContentBlock) per prov.

    No charspan slicing: full text only for the first prov, subsequent provs only provide bbox.
    """
    text = _floating_text(item, doc)
    block_type = _map_label(item.label)

    out = []
    for i, prov in enumerate(item.prov):
        out.append(
            (
                prov.page_no,
                ContentBlock(
                    text=text if i == 0 else "",  # Folge-Rechtecke: nur Position
                    block_type=block_type,
                    bbox=prov.bbox.as_tuple(),
                    source_ref=item.self_ref,
                ),
            )
        )
    return out


def fallback_items_to_blocks(item: DocItem) -> list[tuple[int, ContentBlock]]:
    """Generische Behandlung für nackte/unbekannte DocItems.

    Greift für DocItems, die weder TextItem noch FloatingItem sind
    (FieldRegionItem, FieldItem) sowie für künftige/unerwartete Typen.
    Keine bekannte Textquelle und kein charspan: Best-Effort-Text aufs
    erste prov, Folge-prov nur als bbox.
    """
    # nackte DocItems haben kein .text -> als Platzhalter das Label nutzen
    text = getattr(item, "text", "") or f"[{item.label.value}]"
    block_type = _map_label(item.label)

    blocks = []
    for i, prov in enumerate(item.prov):
        blocks.append(
            (
                prov.page_no,
                ContentBlock(
                    text=text if i == 0 else "",  # Folge-Rechtecke: nur Position
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
        return item.caption_text(doc) or "[Abbildung]"
    if isinstance(item, (KeyValueItem, FormItem)):
        return " ".join(c.text for c in item.graph.cells) or "[Formular]"
    return getattr(item, "text", "")  # Fallback: nackte DocItems / Unbekanntes
