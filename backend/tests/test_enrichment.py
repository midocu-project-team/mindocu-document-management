"""Unit tests for the stage-3 keyword enrichment.

These cover the deterministic relevance decision (heading-only matching,
polarity precedence, defaults) and the keyword strategy's result assembly.
No LLM is involved anywhere in this strategy.
"""

from datatypes import (
    BlockType,
    ContentBlock,
    DocumentSegment,
    PageContent,
    SegmentationResult,
)
from enrichment import KeywordRelevanceEnrichmentStrategy, RelevanceKeywords
from enrichment.utils import decide_relevance


# --------------------------------------------------------------------------
# Test doubles
# --------------------------------------------------------------------------


def make_block(text: str, block_type: BlockType = BlockType.HEADING) -> ContentBlock:
    return ContentBlock(text=text, block_type=block_type, bbox=None)


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
        RelevanceKeywords(irrelevant=["signaturprüfprotokoll"])
    )

    result = strategy.enrich_segments(make_result([relevant_segment, junk_segment]))

    assert [s.segment_id for s in result.segments] == [
        relevant_segment.segment_id,
        junk_segment.segment_id,
    ]
    assert [s.relevance for s in result.segments] == [True, False]


def test_strategy_leaves_title_and_summary_unset():
    strategy = KeywordRelevanceEnrichmentStrategy(RelevanceKeywords())
    segment = make_segment([make_page(1, [make_block("Anschreiben")])])

    enriched = strategy.enrich_segments(make_result([segment])).segments[0]

    assert enriched.title is None
    assert enriched.summary is None


def test_strategy_fills_result_metadata():
    strategy = KeywordRelevanceEnrichmentStrategy(
        RelevanceKeywords(relevant=["urteil"], irrelevant=["signaturprüfprotokoll"])
    )

    result = strategy.enrich_segments(make_result([]))

    assert result.document_id == "doc-1"
    assert result.enrichment_method == "keyword"
    assert result.relevance_keywords == ["urteil", "signaturprüfprotokoll"]
    assert result.errors == []
