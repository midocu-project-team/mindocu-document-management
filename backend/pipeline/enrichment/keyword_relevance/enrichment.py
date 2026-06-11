from datatypes import (
    DocumentSegment,
    EnrichedSegment,
    EnrichmentResult,
    SegmentationResult,
)
from pipeline.enrichment.strategy import EnrichmentStrategy
from pipeline.enrichment.utils import RelevanceKeywords, decide_relevance
from logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
#  Enrichment strategy
# ============================================================================


class KeywordRelevanceEnrichmentStrategy(EnrichmentStrategy):
    """Deterministic keyword-only enrichment (no LLM).

    Relevance is decided purely by the shared heading-keyword rules
    (enrichment/utils.py); title and summary stay None -- generating them
    needs an LLM and belongs to a future strategy that combines generation
    with the same keyword decision.
    """

    def __init__(self, keywords: RelevanceKeywords) -> None:
        self.keywords = keywords

    def enrich_segments(self, segmentation: SegmentationResult) -> EnrichmentResult:
        """Enriches every stage-2 segment with the keyword relevance decision."""
        segments = [self._enrich(segment) for segment in segmentation.segments]
        logger.debug(
            "Enriched %d segments (%d marked irrelevant)",
            len(segments),
            sum(1 for s in segments if not s.relevance),
        )
        return EnrichmentResult(
            document_id=segmentation.document_id,
            segments=segments,
            enrichment_method="keyword",
            relevance_keywords=self.keywords.all_keywords(),
            # The decision is deterministic; nothing can fail per segment.
            errors=[],
        )

    def _enrich(self, segment: DocumentSegment) -> EnrichedSegment:
        """One segment: keyword relevance only, no generated title/summary."""
        relevance, matched = decide_relevance(segment, self.keywords)
        return EnrichedSegment.from_segment(
            segment,
            title=None,
            summary=None,
            relevance=relevance,
            matched_keywords=matched,
        )
