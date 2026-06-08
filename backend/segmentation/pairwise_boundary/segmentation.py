import json
import time
from statistics import mean
from typing import NamedTuple

import ollama

from datatypes import (
    CaseFileDocument,
    DocumentSegment,
    PageContent,
    PageExtractionError,
    PageExtractionErrorType,
    SegmentationResult,
    SimilarityResult,
)
from logging_config import get_logger
from segmentation.pairwise_boundary.prompt import SIMILARITY_SYSTEM_PROMPT
from segmentation.strategy import SegmentationStrategy

logger = get_logger(__name__)
logger.setLevel(level="DEBUG")

DEFAULT_SIMILARITY_MODEL = "gemma4:e4b"


class _PairDecision(NamedTuple):
    """Boundary decision for the adjacent pair (pages[index], pages[index+1])."""

    index: int
    result: SimilarityResult | None  # None => the LLM call raised
    error: str | None = None


# ============================================================================
#  Segmentation strategy
# ============================================================================


class PairwiseBoundarySegmentationStrategy(SegmentationStrategy):
    """Local pairwise adjacent-page boundary classification via an LLM.

    Each adjacent page pair is judged independently for whether the second page
    continues the first's document; the boolean boundaries are then turned into
    segments in a single pass. The model and sampling config are instance state,
    so different instances can run different models without touching the logic.
    """

    def __init__(
        self,
        model: str = DEFAULT_SIMILARITY_MODEL,
        temperature: float = 0.0,
        keep_alive: int = 45 * 60,  # keep the model loaded for 45 min
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.keep_alive = keep_alive

    def segment_document(self, doc: CaseFileDocument) -> SegmentationResult:
        """Splits a case file into per-document segments."""
        start_time = time.perf_counter()
        pages = doc.pages
        errors = list(doc.errors)

        if len(pages) == 0:
            segments: list[DocumentSegment] = []
        elif len(pages) == 1:
            segments = [_make_segment([pages[0]], [])]
        else:
            decisions = self._decide_boundaries(pages)
            # Record failed calls so they are not silently swallowed.
            errors.extend(
                PageExtractionError(
                    page_number=pages[dec.index + 1].page_number,
                    error_type=PageExtractionErrorType.UNKNOWN,
                    message=dec.error or "similarity decision failed",
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
    ) -> SimilarityResult:
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

        response = ollama.generate(
            model=self.model,
            prompt=user_prompt,
            system=SIMILARITY_SYSTEM_PROMPT,
            format=SimilarityResult.model_json_schema(),
            think=False,
            options={"temperature": self.temperature},
            keep_alive=self.keep_alive,
        )
        logger.debug(
            "LLM similarity call: wall=%.2fs | %s",
            time.perf_counter() - start_time,
            _format_ollama_timing(response),
        )
        return SimilarityResult.model_validate_json(response.response)


# ============================================================================
#  Pure helpers (no strategy state)
# ============================================================================


def _format_ollama_timing(response: ollama.GenerateResponse) -> str:
    """Breaks an Ollama call's wall-clock into load / prefill / decode.

    Ollama returns these counters per call; splitting them tells whether a slow
    decision is prefill-bound (large prompt), decode-bound (long output) or just
    a model reload. Durations come back in nanoseconds and any field may be None.
    """

    def secs(ns: int | None) -> float:
        return (ns or 0) / 1e9

    def rate(count: int | None, ns: int | None) -> float:
        duration = secs(ns)
        return count / duration if count and duration else 0.0

    return (
        f"prompt={response.prompt_eval_count or 0} tok "
        f"prefill={secs(response.prompt_eval_duration):.2f}s "
        f"({rate(response.prompt_eval_count, response.prompt_eval_duration):.0f} tok/s) | "
        f"gen={response.eval_count or 0} tok "
        f"decode={secs(response.eval_duration):.2f}s "
        f"({rate(response.eval_count, response.eval_duration):.0f} tok/s) | "
        f"load={secs(response.load_duration):.2f}s"
    )


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
            segments.append(_make_segment(current_pages, confidences))
            current_pages = [pages[i + 1]]
            confidences = []
        else:
            current_pages.append(pages[i + 1])
            if decision.result is not None:
                confidences.append(decision.result.confidence)

    segments.append(_make_segment(current_pages, confidences))
    return segments


def _make_segment(
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
