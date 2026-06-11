import json
import time
from typing import NamedTuple

from pydantic import BaseModel, Field

from datatypes import (
    CaseFileDocument,
    DocumentSegment,
    PageContent,
    SegmentationError,
    SegmentationErrorType,
    SegmentationResult,
)
from llm import LLMProvider
from logging_config import get_logger
from pipeline.segmentation.pairwise_boundary.prompt import SIMILARITY_SYSTEM_PROMPT
from pipeline.segmentation.strategy import SegmentationStrategy
from pipeline.segmentation.utils import make_segment

logger = get_logger(__name__)
logger.setLevel(level="DEBUG")


class _SimilarityResult(BaseModel):
    confidence: float = Field(ge=0, le=1)
    are_similar: bool
    # reasoning: str # take out to test model performance

class _PairDecision(NamedTuple):
    """Boundary decision for the adjacent pair (pages[index], pages[index+1])."""

    index: int
    result: _SimilarityResult | None  # None => the LLM call raised
    error: str | None = None


# ============================================================================
#  Segmentation strategy
# ============================================================================


class PairwiseBoundarySegmentationStrategy(SegmentationStrategy):
    """Local pairwise adjacent-page boundary classification via an LLM.

    Each adjacent page pair is judged independently for whether the second page
    continues the first's document; the boolean boundaries are then turned into
    segments in a single pass. The LLM endpoint is an injected provider, so
    different instances can run different models/backends without touching the
    logic.
    """

    def __init__(self, provider: LLMProvider, temperature: float = 0.0) -> None:
        self.provider = provider
        self.temperature = temperature

    def segment_document(self, doc: CaseFileDocument) -> SegmentationResult:
        """Splits a case file into per-document segments."""
        start_time = time.perf_counter()
        pages = doc.pages
        # Stage-1 read errors stay on the CaseFileDocument (linked via
        # document_id); SegmentationResult.errors holds only stage-2 errors.
        errors: list[SegmentationError] = []

        if len(pages) == 0:
            segments: list[DocumentSegment] = []
        elif len(pages) == 1:
            segments = [make_segment([pages[0]], [])]
        else:
            decisions = self._decide_boundaries(pages)
            # Record failed calls so they are not silently swallowed. The scope
            # is the boundary between the two pages the failed pair covered.
            errors.extend(
                SegmentationError(
                    error_type=SegmentationErrorType.LLM_CALL_FAILED,
                    message=dec.error or "similarity decision failed",
                    start_page=pages[dec.index].page_number,
                    end_page=pages[dec.index + 1].page_number,
                )
                for dec in decisions
                if dec.result is None
            )
            segments = _group_pages(pages, decisions)

        logger.debug("Segmentation time: %.2f s", time.perf_counter() - start_time)

        return SegmentationResult(
            document_id=doc.document_id,
            segments=segments,
            segmentation_method="llm",
            errors=errors,
        )

    def _decide_boundaries(self, pages: list[PageContent]) -> list[_PairDecision]:
        """Runs the N-1 adjacent-pair decisions in order.

        A single failed call yields a _PairDecision with result=None instead of
        bringing the whole document down.
        """

        def decide(i: int) -> _PairDecision:
            start_time = time.perf_counter()
            try:
                result = self._decide_page_similarity(pages[i], pages[i + 1])
                logger.debug(
                    "Iteration [%d] - decision performance: %.2f s",
                    i,
                    time.perf_counter() - start_time,
                )
                return _PairDecision(i, result)
            except Exception as exc:  # noqa: BLE001 - one bad pair must not abort all
                logger.exception("An error during boundary decision %d occured", i)
                return _PairDecision(i, None, error=str(exc))

        return [decide(i) for i in range(len(pages) - 1)]

    def _decide_page_similarity(
        self, previous_page: PageContent, contestant_page: PageContent
    ) -> _SimilarityResult:
        """Asks the LLM whether contestant_page continues previous_page's document.

        Only the two adjacent pages are sent (as compact block lists); the reply
        is constrained to the SimilarityResult schema and parsed back into one.
        """
        start_time = time.perf_counter()
        user_prompt = json.dumps(
            {
                "previous_page": _page_payload(previous_page),
                "contestant_page": _page_payload(contestant_page),
            },
            ensure_ascii=False,
        )

        response = self.provider.generate(
            user_prompt,
            system=SIMILARITY_SYSTEM_PROMPT,
            schema=_SimilarityResult,
            temperature=self.temperature,
        )
        logger.debug(
            "LLM similarity call: wall=%.2fs | %s",
            time.perf_counter() - start_time,
            response.timing_summary(),
        )
        return _SimilarityResult.model_validate_json(response.text)


# ============================================================================
#  Pure helpers (no strategy state)
# ============================================================================


def _is_boundary(decision: _PairDecision) -> bool:
    """A pair is a boundary only on an explicit dissimilar result.

    Failed calls (result is None) default to "continuation" -- fail safe toward
    NOT over-splitting.
    """
    if decision.result is None:
        return False
    return not decision.result.are_similar


def _group_pages(
    pages: list[PageContent], decisions: list[_PairDecision]
) -> list[DocumentSegment]:
    """Turns the ordered pairwise boundaries into DocumentSegments (pure)."""
    segments: list[DocumentSegment] = []
    current_pages: list[PageContent] = [pages[0]]
    # Continuation confidences of the pairs *inside* the open segment.
    confidences: list[float] = []

    for i, decision in enumerate(decisions):
        if _is_boundary(decision):
            segments.append(make_segment(current_pages, confidences))
            current_pages = [pages[i + 1]]
            confidences = []
        else:
            current_pages.append(pages[i + 1])
            if decision.result is not None:
                confidences.append(decision.result.confidence)

    segments.append(make_segment(current_pages, confidences))
    return segments


def _page_payload(page: PageContent) -> dict:
    """Compact page representation for the LLM: block text + type, no bbox.

    Bounding boxes carry no usable signal for a text-only model and only inflate
    tokens; block_type (e.g. HEADING/FOOTER) is a cheap structural hint.
    """
    return {
        "page_number": page.page_number,
        "blocks": [
            {"text": block.text, "type": block.block_type} for block in page.blocks
        ],
    }
