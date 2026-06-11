"""Public interface of the three-stage mindocu pipeline.

Code outside this package imports pipeline entry points from here
(``from pipeline import read_document, FullContextSegmentationStrategy``);
the per-stage subpackages stay an implementation detail. The data contract
(``CaseFileDocument``, ``SegmentationResult``, ``EnrichmentResult``, ...)
lives in the top-level ``datatypes`` module, not here.
"""

from .enrichment import (
    KeywordRelevanceEnrichmentStrategy,
    KeywordRelevanceOptions,
    RelevanceKeywords,
)
from .enrichment.strategy import EnrichmentStrategy
from .reader import ocr_convert_pdf, read_document
from .reader.options import default_pdf_format_options
from .segmentation import (
    FullContextOptions,
    FullContextSegmentationStrategy,
    PairwiseBoundarySegmentationStrategy,
)
from .segmentation.strategy import SegmentationStrategy

__all__ = [
    # Stage 1: read
    "read_document",
    "ocr_convert_pdf",
    "default_pdf_format_options",
    # Stage 2: segment
    "SegmentationStrategy",
    "FullContextOptions",
    "FullContextSegmentationStrategy",
    "PairwiseBoundarySegmentationStrategy",
    # Stage 3: enrich
    "EnrichmentStrategy",
    "RelevanceKeywords",
    "KeywordRelevanceOptions",
    "KeywordRelevanceEnrichmentStrategy",
]
