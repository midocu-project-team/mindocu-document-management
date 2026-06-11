"""Unit tests for the evaluation harness's stage-3 plumbing.

These cover the segments source for enrichment: the ground-truth →
SegmentationResult conversion and the read-once segmentation cache. No OCR
and no LLM anywhere.
"""

from datatypes import (
    BlockType,
    CaseFileDocument,
    ContentBlock,
    PageContent,
    SegmentationResult,
)
from evaluation.ground_truth import GroundTruth, TrueSegment
from evaluation.harness import load_cached_segmentation, truth_segmentation


# --------------------------------------------------------------------------
# Test doubles
# --------------------------------------------------------------------------


def make_page(page_number: int) -> PageContent:
    text = f"Seite {page_number}"
    return PageContent(
        page_number=page_number,
        raw_text=text,
        blocks=[ContentBlock(text=text, block_type=BlockType.PARAGRAPH, bbox=None)],
        was_ocr_applied=False,
        confidence=None,
        width_pt=595.0,
        height_pt=842.0,
    )


def make_doc(n_pages: int) -> CaseFileDocument:
    return CaseFileDocument(
        file_name="x.pdf",
        file_size_bytes=1,
        total_pages=n_pages,
        pages=[make_page(n) for n in range(1, n_pages + 1)],
        errors=[],
        ocr_engine="none",
    )


class StubStrategy:
    """Counts segment_document calls and returns a fixed result."""

    def __init__(self, result: SegmentationResult):
        self.result = result
        self.calls = 0

    def segment_document(self, doc: CaseFileDocument) -> SegmentationResult:
        self.calls += 1
        return self.result


# --------------------------------------------------------------------------
# truth_segmentation
# --------------------------------------------------------------------------


def test_truth_segmentation_builds_true_segments():
    doc = make_doc(4)
    truth = GroundTruth(
        file_name="x.pdf",
        total_pages=4,
        segments=[
            TrueSegment(start_page=1, end_page=2),
            TrueSegment(start_page=3, end_page=4),
        ],
    )

    result = truth_segmentation(doc, truth)

    assert result.document_id == doc.document_id
    assert result.segmentation_method == "ground-truth"
    assert result.errors == []
    assert [(s.start_page, s.end_page) for s in result.segments] == [(1, 2), (3, 4)]
    assert [p.page_number for p in result.segments[0].pages] == [1, 2]
    assert "Seite 3" in result.segments[1].raw_text


# --------------------------------------------------------------------------
# load_cached_segmentation
# --------------------------------------------------------------------------


def test_load_cached_segmentation_segments_once_then_reads_cache(tmp_path):
    doc = make_doc(2)
    stub = StubStrategy(
        SegmentationResult(
            document_id=doc.document_id,
            segments=[],
            segmentation_method="llm",
            errors=[],
        )
    )

    first = load_cached_segmentation(
        "x.pdf", doc, factory=lambda provider: stub, provider=None, cache_dir=tmp_path
    )
    second = load_cached_segmentation(
        "x.pdf", doc, factory=lambda provider: stub, provider=None, cache_dir=tmp_path
    )

    assert stub.calls == 1  # the second call was served from the cache
    assert (tmp_path / "x.segments.json").exists()
    assert second.document_id == first.document_id


def test_load_cached_segmentation_refresh_forces_resegmentation(tmp_path):
    doc = make_doc(2)
    stub = StubStrategy(
        SegmentationResult(
            document_id=doc.document_id,
            segments=[],
            segmentation_method="llm",
            errors=[],
        )
    )
    factory = lambda provider: stub  # noqa: E731

    load_cached_segmentation(
        "x.pdf", doc, factory=factory, provider=None, cache_dir=tmp_path
    )
    load_cached_segmentation(
        "x.pdf", doc, factory=factory, provider=None, cache_dir=tmp_path, refresh=True
    )

    assert stub.calls == 2
