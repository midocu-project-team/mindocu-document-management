"""Shared, strategy-agnostic helpers for stage-3 enrichment.

The keyword relevance decision lives here rather than in a single strategy
because it is deterministic by contract (EnrichedSegment.relevance) and every
enrichment strategy -- keyword-only today, LLM-backed ones later -- reuses it
unchanged.
"""

from pydantic import BaseModel, Field

from pipeline.datatypes import BlockType, DocumentSegment


class RelevanceKeywords(BaseModel):
    """Keyword rule set for the deterministic relevance decision.

    A keyword fires when it occurs (case-insensitive substring) in the text of
    a HEADING block on any page of the segment. `relevant` matches win over
    `irrelevant` ones -- failing safe toward keeping a document visible; when
    nothing fires, `default_relevance` applies. A whitelist setup is the same
    rules with only `relevant` keywords and `default_relevance=False`.
    """

    relevant: list[str] = Field(default_factory=list)
    irrelevant: list[str] = Field(default_factory=list)
    default_relevance: bool = True

    def all_keywords(self) -> list[str]:
        """Flat keyword set, for EnrichmentResult.relevance_keywords."""
        return [*self.relevant, *self.irrelevant]


def decide_relevance(
    segment: DocumentSegment, keywords: RelevanceKeywords
) -> tuple[bool, list[str]]:
    """Returns (relevance, matched keywords) for one segment.

    Only the keywords of the winning polarity are reported, so the matched
    list always explains the decision; an empty list means no keyword fired
    and the default was applied.
    """
    headings = _heading_texts(segment)
    relevant_hits = _matches(keywords.relevant, headings)
    if relevant_hits:
        return True, relevant_hits
    irrelevant_hits = _matches(keywords.irrelevant, headings)
    if irrelevant_hits:
        return False, irrelevant_hits
    return keywords.default_relevance, []


def _heading_texts(segment: DocumentSegment) -> list[str]:
    """Casefolded text of every HEADING block across the segment's pages."""
    return [
        block.text.casefold()
        for page in segment.pages
        for block in page.blocks
        if block.block_type is BlockType.HEADING
    ]


def _matches(keywords: list[str], headings: list[str]) -> list[str]:
    """Keywords that occur (case-insensitive) in at least one heading."""
    return [kw for kw in keywords if any(kw.casefold() in h for h in headings)]
