"""Unit tests for the evaluation harness's stage-3 plumbing.

These cover the segments source for enrichment (the ground-truth →
SegmentationResult conversion and the read-once segmentation cache) and the
unscored enrichment prediction. No OCR and no real LLM anywhere.
"""

import json

from pydantic import BaseModel

from datatypes import (
    BlockType,
    CaseFileDocument,
    ContentBlock,
    PageContent,
    SegmentationResult,
)
from evaluation.ground_truth import GroundTruth, TrueSegment
from evaluation.harness import (
    load_cached_segmentation,
    predict_enrichment,
    truth_segmentation,
)
from llm import LLMProvider, LLMResponse
from pipeline import KeywordRelevanceEnrichmentStrategy, RelevanceKeywords


# --------------------------------------------------------------------------
# Test doubles
# --------------------------------------------------------------------------


def make_page(
    page_number: int,
    text: str | None = None,
    block_type: BlockType = BlockType.PARAGRAPH,
) -> PageContent:
    text = text if text is not None else f"Seite {page_number}"
    return PageContent(
        page_number=page_number,
        raw_text=text,
        blocks=[ContentBlock(text=text, block_type=block_type, bbox=None)],
        was_ocr_applied=False,
        confidence=None,
        width_pt=595.0,
        height_pt=842.0,
    )


def make_doc(pages: list[PageContent]) -> CaseFileDocument:
    return CaseFileDocument(
        file_name="x.pdf",
        file_size_bytes=1,
        total_pages=len(pages),
        pages=pages,
        errors=[],
        ocr_engine="none",
    )


class FakeProvider(LLMProvider):
    """Returns a canned title/summary JSON and records every prompt."""

    def __init__(self):
        self.prompts: list[str] = []

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        schema: type[BaseModel] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        self.prompts.append(prompt)
        return LLMResponse(
            text=json.dumps(
                {"title": "Titel", "summary": "Zusammenfassung."}, ensure_ascii=False
            ),
            prompt_tokens=10,
            completion_tokens=5,
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
    doc = make_doc([make_page(n) for n in range(1, 5)])
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
    doc = make_doc([make_page(1), make_page(2)])
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
    doc = make_doc([make_page(1), make_page(2)])
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


# --------------------------------------------------------------------------
# predict_enrichment
# --------------------------------------------------------------------------


def test_predict_enrichment_reduces_segments_and_meters_usage():
    doc = make_doc(
        [
            make_page(1, "Anschreiben", BlockType.HEADING),
            make_page(2, "Signaturprüfprotokoll", BlockType.HEADING),
        ]
    )
    truth = GroundTruth(
        file_name="x.pdf",
        total_pages=2,
        segments=[
            TrueSegment(start_page=1, end_page=1),
            TrueSegment(start_page=2, end_page=2),
        ],
    )
    keywords = RelevanceKeywords(irrelevant=["signaturprüfprotokoll"])

    row = predict_enrichment(
        strategy_name="kw",
        factory=lambda p: KeywordRelevanceEnrichmentStrategy(p, keywords),
        segmentation=truth_segmentation(doc, truth),
        segments_source="ground-truth",
        pdf_name="x.pdf",
        provider=FakeProvider(),
    )

    assert (row.n_segments, row.n_irrelevant, row.errors) == (2, 1, 0)
    assert row.segments[0].relevance is True
    assert row.segments[0].title == "Titel"
    assert row.segments[1].relevance is False
    assert row.segments[1].title is None
    assert row.segments[1].matched_keywords == ["signaturprüfprotokoll"]
    assert row.usage.calls == 1  # the junk segment cost no LLM call
    assert row.usage.prompt_tokens == 10
