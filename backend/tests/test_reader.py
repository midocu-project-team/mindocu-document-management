"""Unit tests for the pure helpers in the reader package.

These cover the DocItem -> ContentBlock mapping, label mapping, and the
per-page confidence/OCR signals. The heavy OCR paths (read_document,
ocr_convert_pdf) are intentionally left to integration tests because they
exercise docling, not our logic.
"""

import math
from types import SimpleNamespace
from unittest.mock import MagicMock

from docling_core.types.doc.document import (
    FormItem,
    KeyValueItem,
    PictureItem,
    TableItem,
    TextItem,
)
from docling_core.types.doc.labels import DocItemLabel

from datatypes import BlockType
from pipeline.reader import mapping
from pipeline.reader.mapping import (
    _fallback_items_to_blocks,
    _floating_items_to_blocks,
    _floating_text,
    _map_label,
    _text_item_to_blocks,
    item_to_blocks,
)
from pipeline.reader.reader import _page_confidence, _was_ocr_applied


# --------------------------------------------------------------------------
# Test doubles
# --------------------------------------------------------------------------


def make_prov(page_no: int, charspan: tuple[int, int], bbox=(0.0, 0.0, 1.0, 1.0)):
    """A minimal stand-in for a docling ProvenanceItem.

    bbox exposes .as_tuple() like the real BoundingBox; charspan/page_no are
    plain values, matching how reader.py reads them.
    """
    return SimpleNamespace(
        page_no=page_no,
        charspan=charspan,
        bbox=SimpleNamespace(as_tuple=lambda b=bbox: b),
    )


def make_report(mean_score: float, ocr_score: float, page_no: int = 1):
    """A minimal stand-in for a docling ConfidenceReport."""
    return SimpleNamespace(
        pages={page_no: SimpleNamespace(mean_score=mean_score, ocr_score=ocr_score)}
    )


# --------------------------------------------------------------------------
# _map_label
# --------------------------------------------------------------------------


def test_map_label_known_values():
    assert _map_label(DocItemLabel.TITLE) == BlockType.HEADING
    assert _map_label(DocItemLabel.SECTION_HEADER) == BlockType.HEADING
    assert _map_label(DocItemLabel.LIST_ITEM) == BlockType.LIST
    assert _map_label(DocItemLabel.TABLE) == BlockType.TABLE
    assert _map_label(DocItemLabel.DOCUMENT_INDEX) == BlockType.TABLE
    assert _map_label(DocItemLabel.PAGE_FOOTER) == BlockType.FOOTER
    assert _map_label(DocItemLabel.TEXT) == BlockType.PARAGRAPH
    assert _map_label(DocItemLabel.HANDWRITTEN_TEXT) == BlockType.HANDWRITTEN


def test_map_label_images():
    assert _map_label(DocItemLabel.PICTURE) == BlockType.IMAGE
    assert _map_label(DocItemLabel.CHART) == BlockType.IMAGE


def test_map_label_form_bucket():
    # Forms, key-value regions, fields and checkboxes collapse into one FORM type.
    for label in (
        DocItemLabel.FORM,
        DocItemLabel.KEY_VALUE_REGION,
        DocItemLabel.FIELD_REGION,
        DocItemLabel.FIELD_KEY,
        DocItemLabel.FIELD_VALUE,
        DocItemLabel.CHECKBOX_SELECTED,
        DocItemLabel.CHECKBOX_UNSELECTED,
        DocItemLabel.EMPTY_VALUE,
    ):
        assert _map_label(label) == BlockType.FORM


def test_map_label_unmapped_falls_back_to_unknown():
    # PAGE_HEADER / MARKER are deliberately not in the mapping table.
    assert _map_label(DocItemLabel.PAGE_HEADER) == BlockType.UNKNOWN
    assert _map_label(DocItemLabel.MARKER) == BlockType.UNKNOWN


# --------------------------------------------------------------------------
# _page_confidence / _was_ocr_applied
# --------------------------------------------------------------------------


def test_page_confidence_returns_float():
    report = make_report(mean_score=0.87, ocr_score=math.nan)
    assert _page_confidence(report, 1) == 0.87


def test_page_confidence_nan_becomes_none():
    report = make_report(mean_score=math.nan, ocr_score=math.nan)
    assert _page_confidence(report, 1) is None


def test_was_ocr_applied_true_when_ocr_score_set():
    report = make_report(mean_score=0.9, ocr_score=0.95)
    assert _was_ocr_applied(report, 1) is True


def test_was_ocr_applied_false_when_ocr_score_nan():
    # NaN ocr_score => the page had an embedded text layer, no OCR.
    report = make_report(mean_score=0.9, ocr_score=math.nan)
    assert _was_ocr_applied(report, 1) is False


# --------------------------------------------------------------------------
# text_item_to_blocks
# --------------------------------------------------------------------------


def test_text_item_single_prov_slices_charspan():
    item = SimpleNamespace(
        text="HelloWorld",
        label=DocItemLabel.TEXT,
        self_ref="#/texts/0",
        prov=[make_prov(page_no=1, charspan=(0, 5), bbox=(1.0, 2.0, 3.0, 4.0))],
    )

    blocks = _text_item_to_blocks(item)

    assert len(blocks) == 1
    page_no, block = blocks[0]
    assert page_no == 1
    assert block.text == "Hello"
    assert block.block_type == BlockType.PARAGRAPH
    assert block.bbox == (1.0, 2.0, 3.0, 4.0)
    assert block.source_ref == "#/texts/0"


def test_text_item_one_block_per_prov_with_shared_source_ref():
    # A single TextItem may span multiple provs (even across pages); each prov
    # becomes its own block, sliced by its own charspan, linked via source_ref.
    item = SimpleNamespace(
        text="HelloWorld",
        label=DocItemLabel.TEXT,
        self_ref="#/texts/7",
        prov=[
            make_prov(page_no=1, charspan=(0, 5)),
            make_prov(page_no=2, charspan=(5, 10)),
        ],
    )

    blocks = _text_item_to_blocks(item)

    assert [p for p, _ in blocks] == [1, 2]
    assert [b.text for _, b in blocks] == ["Hello", "World"]
    assert {b.source_ref for _, b in blocks} == {"#/texts/7"}


# --------------------------------------------------------------------------
# floating_items_to_blocks
# --------------------------------------------------------------------------


def test_floating_item_text_only_on_first_prov():
    # Plain stub (not a known floating type) => _floating_text falls back to
    # item.text, which lets us test the "first prov only" text rule in isolation.
    item = SimpleNamespace(
        text="cell-a | cell-b",
        label=DocItemLabel.TABLE,
        self_ref="#/tables/0",
        prov=[
            make_prov(page_no=3, charspan=(0, 0)),
            make_prov(page_no=4, charspan=(0, 0)),
        ],
    )

    blocks = _floating_items_to_blocks(item, doc=None)

    assert len(blocks) == 2
    assert blocks[0][1].text == "cell-a | cell-b"
    assert blocks[1][1].text == ""  # following provs carry position only
    assert blocks[0][1].block_type == BlockType.TABLE
    assert all(b.source_ref == "#/tables/0" for _, b in blocks)


# --------------------------------------------------------------------------
# fallback_items_to_blocks
# --------------------------------------------------------------------------


def test_fallback_uses_text_when_present():
    item = SimpleNamespace(
        text="field value",
        label=DocItemLabel.TEXT,
        self_ref="#/x/0",
        prov=[make_prov(page_no=1, charspan=(0, 0))],
    )

    blocks = _fallback_items_to_blocks(item)

    assert blocks[0][1].text == "field value"


def test_fallback_uses_label_placeholder_when_no_text():
    # A plain DocItem without a .text attribute -> "[<label>]" placeholder.
    # MARKER is deliberately unmapped, so the block type stays UNKNOWN.
    item = SimpleNamespace(
        label=DocItemLabel.MARKER,
        self_ref="#/y/0",
        prov=[make_prov(page_no=1, charspan=(0, 0))],
    )

    blocks = _fallback_items_to_blocks(item)

    assert blocks[0][1].text == "[marker]"
    assert blocks[0][1].block_type == BlockType.UNKNOWN


# --------------------------------------------------------------------------
# _floating_text (dispatch on docling type)
# --------------------------------------------------------------------------


def test_floating_text_table_exports_markdown():
    item = MagicMock(spec=TableItem)
    item.export_to_markdown.return_value = "| a | b |"
    assert _floating_text(item, doc="DOC") == "| a | b |"
    item.export_to_markdown.assert_called_once_with("DOC")


def test_floating_text_picture_uses_caption():
    item = MagicMock(spec=PictureItem)
    item.caption_text.return_value = "Figure 1"
    assert _floating_text(item, doc=None) == "Figure 1"


def test_floating_text_picture_without_caption_falls_back():
    item = MagicMock(spec=PictureItem)
    item.caption_text.return_value = ""
    assert _floating_text(item, doc=None) == "[Image]"


def test_floating_text_keyvalue_joins_cells():
    # `graph` is a pydantic field invisible to MagicMock's spec introspection,
    # so we drive isinstance via __class__ and attach graph by hand.
    item = MagicMock()
    item.__class__ = KeyValueItem
    item.graph = SimpleNamespace(
        cells=[SimpleNamespace(text="Name"), SimpleNamespace(text="Mustermann")]
    )
    assert _floating_text(item, doc=None) == "Name Mustermann"


def test_floating_text_form_without_cells_falls_back():
    item = MagicMock()
    item.__class__ = FormItem
    item.graph = SimpleNamespace(cells=[])
    assert _floating_text(item, doc=None) == "[Form]"


# --------------------------------------------------------------------------
# item_to_blocks (dispatch)
# --------------------------------------------------------------------------


def test_item_to_blocks_routes_text_item(monkeypatch):
    monkeypatch.setattr(mapping, "_text_item_to_blocks", lambda item: "TEXT")
    monkeypatch.setattr(mapping, "_floating_items_to_blocks", lambda item, doc: "FLOAT")
    monkeypatch.setattr(mapping, "_fallback_items_to_blocks", lambda item: "FALLBACK")

    assert item_to_blocks(MagicMock(spec=TextItem), doc=None) == "TEXT"


def test_item_to_blocks_routes_floating_item(monkeypatch):
    monkeypatch.setattr(mapping, "_text_item_to_blocks", lambda item: "TEXT")
    monkeypatch.setattr(mapping, "_floating_items_to_blocks", lambda item, doc: "FLOAT")
    monkeypatch.setattr(mapping, "_fallback_items_to_blocks", lambda item: "FALLBACK")

    # TableItem is a FloatingItem but not a TextItem.
    assert item_to_blocks(MagicMock(spec=TableItem), doc=None) == "FLOAT"


def test_item_to_blocks_routes_plain_item_to_fallback(monkeypatch):
    monkeypatch.setattr(mapping, "_text_item_to_blocks", lambda item: "TEXT")
    monkeypatch.setattr(mapping, "_floating_items_to_blocks", lambda item, doc: "FLOAT")
    monkeypatch.setattr(mapping, "_fallback_items_to_blocks", lambda item: "FALLBACK")

    # A bare object is neither TextItem nor FloatingItem.
    assert item_to_blocks(object(), doc=None) == "FALLBACK"
