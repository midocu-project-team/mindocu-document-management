"""Shared, strategy-agnostic helpers for stage-2 segmentation.

Helpers needed by more than one segmentation strategy live here so the
strategies do not have to cross-import from a sibling strategy package.
"""

from statistics import mean

from datatypes import DocumentSegment, PageContent


def make_segment(
    pages: list[PageContent], confidences: list[float]
) -> DocumentSegment:
    """Builds a DocumentSegment from its pages and within-segment confidences.

    Single-page segments have no internal pair, hence confidence is None.
    """
    page_numbers = [p.page_number for p in pages]
    return DocumentSegment(
        start_page=min(page_numbers),
        end_page=max(page_numbers),
        raw_text="\n\n\n".join(p.raw_text for p in pages),
        pages=list(pages),
        confidence=mean(confidences) if confidences else None,
    )
