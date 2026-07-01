"""Public interface of the three-stage mindocu pipeline.

Code outside this package imports pipeline entry points from here
(``from pipeline import DoclingReaderStrategy, FullContextSegmentationStrategy``);
the per-stage subpackages stay an implementation detail. The data contract
(``CaseFileDocument``, ``SegmentationResult``, ``EnrichmentResult``, ...)
lives in ``pipeline.datatypes``.
"""

from .document import Document
from .enrichment import (
    KeywordRelevanceEnrichmentStrategy,
    KeywordRelevanceOptions,
    RelevanceKeywords,
)
from .enrichment.strategy import EnrichmentStrategy
from .reader import (
    DoclingReaderStrategy,
    ReaderStrategy,
    default_pdf_format_options,
    ocr_convert_pdf,
)
from .runner import PipelineRunner
from .segmentation import (
    FullContextOptions,
    FullContextSegmentationStrategy,
    PairwiseBoundarySegmentationStrategy,
)
from .segmentation.strategy import SegmentationStrategy
from .segmentation.utils import make_segment

__all__ = [
    # Stage 1: read
    "ReaderStrategy",
    "DoclingReaderStrategy",
    "default_pdf_format_options",
    "ocr_convert_pdf",
    # Stage 2: segment
    "SegmentationStrategy",
    "FullContextOptions",
    "FullContextSegmentationStrategy",
    "PairwiseBoundarySegmentationStrategy",
    "make_segment",
    # Stage 3: enrich
    "EnrichmentStrategy",
    "RelevanceKeywords",
    "KeywordRelevanceOptions",
    "KeywordRelevanceEnrichmentStrategy",
    # Composition (runs all three stages into one Document)
    "PipelineRunner",
    "Document",
]
