"""Unit tests for the stage-3 keyword-relevance enrichment.

These cover the deterministic relevance decision (heading-only matching,
polarity precedence, defaults) and the strategy's result assembly: gated
title/summary generation, per-segment degradation on failed calls. The LLM
side runs against a canned fake provider, never a real backend.
"""

import itertools
import json

from pydantic import BaseModel

from pipeline.datatypes import (
    BlockType,
    ContentBlock,
    DocumentSegment,
    EnrichmentErrorType,
    PageContent,
    SegmentationResult,
)
from llm import LLMProvider, LLMResponse
from pipeline import (
    KeywordRelevanceEnrichmentStrategy,
    KeywordRelevanceOptions,
    RelevanceKeywords,
)
from pipeline.enrichment.utils import decide_relevance


# --------------------------------------------------------------------------
# Test doubles
# --------------------------------------------------------------------------

CANNED_TITLE = "Ärztliche Stellungnahme Dr. Müller, 12.03.2024"
# The summary is now assembled from references; CANNED_SUMMARY is their join.
CANNED_REFERENCES = [
    {"text": "Aus dem Dokument gehe hervor, dass etwas vorliege.", "block_ids": [0]},
    {"text": "Ferner werde Weiteres berichtet.", "block_ids": [0]},
]
CANNED_SUMMARY = " ".join(ref["text"] for ref in CANNED_REFERENCES)


class FakeProvider(LLMProvider):
    """Canned-response provider: records every prompt, returns fixed text."""

    def __init__(self, text: str | None = None, error: Exception | None = None):
        self.prompts: list[str] = []
        self.text = (
            text
            if text is not None
            else json.dumps(
                {"title": CANNED_TITLE, "references": CANNED_REFERENCES},
                ensure_ascii=False,
            )
        )
        self.error = error

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
        if self.error is not None:
            raise self.error
        return LLMResponse(text=self.text)


_block_ids = itertools.count()


def make_block(text: str, block_type: BlockType = BlockType.HEADING) -> ContentBlock:
    return ContentBlock(
        block_id=next(_block_ids), text=text, block_type=block_type, bbox=None
    )


def make_page(page_number: int, blocks: list[ContentBlock]) -> PageContent:
    return PageContent(
        page_number=page_number,
        raw_text=" ".join(block.text for block in blocks),
        blocks=blocks,
        was_ocr_applied=False,
        confidence=None,
        width_pt=595.0,
        height_pt=842.0,
    )


def make_segment(pages: list[PageContent]) -> DocumentSegment:
    return DocumentSegment(
        start_page=pages[0].page_number,
        end_page=pages[-1].page_number,
        raw_text="\n\n\n".join(page.raw_text for page in pages),
        pages=pages,
        confidence=None,
    )


def make_result(segments: list[DocumentSegment]) -> SegmentationResult:
    return SegmentationResult(
        document_id="doc-1",
        segments=segments,
        segmentation_method="llm",
        errors=[],
    )


# --------------------------------------------------------------------------
# decide_relevance: matching rules
# --------------------------------------------------------------------------


def test_irrelevant_keyword_in_heading_marks_segment_irrelevant():
    segment = make_segment(
        [make_page(1, [make_block("Signaturprüfprotokoll - Anlage 3")])]
    )
    keywords = RelevanceKeywords(irrelevant=["signaturprüfprotokoll"])

    relevance, matched = decide_relevance(segment, keywords)

    assert relevance is False
    assert matched == ["signaturprüfprotokoll"]


def test_matching_is_case_insensitive():
    segment = make_segment([make_page(1, [make_block("SIGNATURPRÜFPROTOKOLL")])])
    keywords = RelevanceKeywords(irrelevant=["Signaturprüfprotokoll"])

    relevance, _ = decide_relevance(segment, keywords)

    assert relevance is False


def test_keyword_only_fires_in_heading_blocks():
    # Same text, but as a paragraph: the rule is heading-only by design.
    segment = make_segment(
        [make_page(1, [make_block("Signaturprüfprotokoll", BlockType.PARAGRAPH)])]
    )
    keywords = RelevanceKeywords(irrelevant=["signaturprüfprotokoll"])

    relevance, matched = decide_relevance(segment, keywords)

    assert relevance is True  # default applies, nothing fired
    assert matched == []


def test_keyword_fires_on_any_page_of_the_segment():
    segment = make_segment(
        [
            make_page(1, [make_block("Anschreiben")]),
            make_page(2, [make_block("Signaturprüfprotokoll")]),
        ]
    )
    keywords = RelevanceKeywords(irrelevant=["signaturprüfprotokoll"])

    relevance, _ = decide_relevance(segment, keywords)

    assert relevance is False


def test_relevant_keyword_wins_over_irrelevant():
    # Fail safe toward keeping a document visible when both polarities fire.
    segment = make_segment(
        [make_page(1, [make_block("Urteil"), make_block("Signaturprüfprotokoll")])]
    )
    keywords = RelevanceKeywords(
        relevant=["urteil"], irrelevant=["signaturprüfprotokoll"]
    )

    relevance, matched = decide_relevance(segment, keywords)

    assert relevance is True
    assert matched == ["urteil"]


def test_default_relevance_applies_when_nothing_fires():
    segment = make_segment([make_page(1, [make_block("Anschreiben")])])

    assert decide_relevance(segment, RelevanceKeywords())[0] is True
    assert (
        decide_relevance(segment, RelevanceKeywords(default_relevance=False))[0]
        is False
    )


# --------------------------------------------------------------------------
# KeywordRelevanceEnrichmentStrategy: result assembly
# --------------------------------------------------------------------------


def test_strategy_enriches_all_segments_and_preserves_ids():
    relevant_segment = make_segment([make_page(1, [make_block("Anschreiben")])])
    junk_segment = make_segment([make_page(2, [make_block("Signaturprüfprotokoll")])])
    strategy = KeywordRelevanceEnrichmentStrategy(
        FakeProvider(), RelevanceKeywords(irrelevant=["signaturprüfprotokoll"])
    )

    result = strategy.enrich_segments(make_result([relevant_segment, junk_segment]))

    assert [s.segment_id for s in result.segments] == [
        relevant_segment.segment_id,
        junk_segment.segment_id,
    ]
    assert [s.relevance for s in result.segments] == [True, False]


def test_strategy_sets_title_and_summary_for_relevant_segments():
    strategy = KeywordRelevanceEnrichmentStrategy(FakeProvider(), RelevanceKeywords())
    segment = make_segment([make_page(1, [make_block("Anschreiben")])])

    enriched = strategy.enrich_segments(make_result([segment])).segments[0]

    assert enriched.title == CANNED_TITLE
    assert enriched.summary == CANNED_SUMMARY


def test_strategy_skips_llm_for_irrelevant_segments():
    provider = FakeProvider()
    strategy = KeywordRelevanceEnrichmentStrategy(
        provider, RelevanceKeywords(irrelevant=["signaturprüfprotokoll"])
    )
    segment = make_segment([make_page(1, [make_block("Signaturprüfprotokoll")])])

    enriched = strategy.enrich_segments(make_result([segment])).segments[0]

    assert provider.prompts == []  # no call spent on a junk segment
    assert enriched.title is None
    assert enriched.summary is None


def test_enrich_irrelevant_option_generates_for_junk_segments_too():
    provider = FakeProvider()
    strategy = KeywordRelevanceEnrichmentStrategy(
        provider,
        RelevanceKeywords(irrelevant=["signaturprüfprotokoll"]),
        KeywordRelevanceOptions(enrich_irrelevant=True),
    )
    segment = make_segment([make_page(1, [make_block("Signaturprüfprotokoll")])])

    enriched = strategy.enrich_segments(make_result([segment])).segments[0]

    assert len(provider.prompts) == 1
    assert enriched.title == CANNED_TITLE
    assert enriched.relevance is False


def test_failed_call_degrades_segment_and_records_error():
    strategy = KeywordRelevanceEnrichmentStrategy(
        FakeProvider(error=RuntimeError("connection refused")), RelevanceKeywords()
    )
    segment = make_segment([make_page(1, [make_block("Anschreiben")])])

    result = strategy.enrich_segments(make_result([segment]))

    enriched = result.segments[0]
    assert enriched.title is None and enriched.summary is None
    assert enriched.relevance is True  # the deterministic part survives
    assert [e.error_type for e in result.errors] == [
        EnrichmentErrorType.LLM_CALL_FAILED
    ]
    assert result.errors[0].segment_id == segment.segment_id


def test_unparseable_output_yields_invalid_output_error():
    strategy = KeywordRelevanceEnrichmentStrategy(
        FakeProvider(text="not json"), RelevanceKeywords()
    )
    segment = make_segment([make_page(1, [make_block("Anschreiben")])])

    result = strategy.enrich_segments(make_result([segment]))

    assert result.segments[0].title is None
    assert [e.error_type for e in result.errors] == [
        EnrichmentErrorType.INVALID_OUTPUT
    ]


def test_payload_is_head_truncated_to_max_input_chars():
    provider = FakeProvider()
    strategy = KeywordRelevanceEnrichmentStrategy(
        provider, RelevanceKeywords(), KeywordRelevanceOptions(max_input_chars=11)
    )
    segment = make_segment([make_page(1, [make_block("Anschreiben mit langem Text")])])

    strategy.enrich_segments(make_result([segment]))

    # Payload is block-tagged ("[#<id>] <text>") and capped to max_input_chars.
    block = segment.blocks[0]
    expected = f"[#{block.block_id}] {block.text}"[:11]
    assert provider.prompts == [expected]


def test_strategy_fills_result_metadata():
    strategy = KeywordRelevanceEnrichmentStrategy(
        FakeProvider(),
        RelevanceKeywords(relevant=["urteil"], irrelevant=["signaturprüfprotokoll"]),
    )

    result = strategy.enrich_segments(make_result([]))

    assert result.document_id == "doc-1"
    assert result.enrichment_method == "llm+keyword"
    assert result.relevance_keywords == ["urteil", "signaturprüfprotokoll"]
    assert result.errors == []
