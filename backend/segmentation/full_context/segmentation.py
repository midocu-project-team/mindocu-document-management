import json
import time

import ollama
from pydantic import BaseModel, Field

from datatypes import (
    CaseFileDocument,
    DocumentSegment,
    PageContent,
    SegmentationError,
    SegmentationErrorType,
    SegmentationResult,
)
from logging_config import get_logger
from segmentation.full_context.prompt import FULL_CONTEXT_SYSTEM_PROMPT
from segmentation.strategy import SegmentationStrategy
from segmentation.utils import make_segment

logger = get_logger(__name__)
logger.setLevel(level="DEBUG")

DEFAULT_MODEL = "qwen2.5:14b"


class FullContextOptions(BaseModel):
    """Configuration for FullContextSegmentationStrategy.

    Bundled into one object so the strategy constructor stays a single argument
    instead of a long parameter list (mirrors reader/options.py).
    """

    model: str = DEFAULT_MODEL
    temperature: float = 0.0
    keep_alive: int = 45 * 60  # keep the model loaded for 45 min

    # 128K is the trained context ceiling of current local models (Llama 3.x /
    # Gemma 3 / Mistral Nemo / Qwen2.5-128K). Far above the ~20-35K-token max real
    # doc -> pure headroom. Ollama clamps this down to the model's trained max.
    num_ctx: int = 131072
    # Windowing trigger: if the estimated input exceeds this, fall back to
    # sliding windows. Kept below num_ctx to leave room for the system prompt and
    # the generated segment list.
    max_input_tokens: int = 100_000

    # Per-block text cap and how many leading blocks to keep in a page
    # fingerprint -- boundary cues sit at the top of a page (letterhead/heading).
    # None means "no cap": keep every block / each block's full text. Default is
    # None (full text of all blocks); set ints to trim for very large documents.
    max_chars_per_block: int | None = None
    head_blocks: int | None = None

    # Sliding-window parameters for the large-document fallback.
    window_pages: int = 80
    window_overlap: int = 10


class _LLMSegment(BaseModel):
    """One segment as emitted by the LLM (page numbers, not page objects)."""

    start_page: int
    end_page: int
    confidence: float = Field(ge=0, le=1)


class _SegmentationPlan(BaseModel):
    """The full set of segments the LLM proposes for a (window of a) document."""

    segments: list[_LLMSegment]


# ============================================================================
#  Segmentation strategy
# ============================================================================


class FullContextSegmentationStrategy(SegmentationStrategy):
    """Single-pass whole-document boundary classification via an LLM.

    The entire case file is sent in one call as an ordered list of compact page
    fingerprints; the model returns the complete segment list directly. This
    sees global structure (running senders/page numbers, resuming documents)
    that the pairwise strategy cannot, and -- because each page is sent once and
    the system prompt is prefilled once -- does far less total prefill work.

    The model output is never trusted blindly: a deterministic repair step turns
    it into gap-/overlap-free segments covering every page exactly once.
    """

    def __init__(self, options: FullContextOptions | None = None) -> None:
        self.options = options or FullContextOptions()

    def segment_document(self, doc: CaseFileDocument) -> SegmentationResult:
        """Splits a case file into per-document segments in a single pass."""
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
            llm_segments, call_errors = self._plan_segments(pages)
            errors.extend(call_errors)
            segments = _repair_segments(pages, llm_segments)

        logger.debug("Segmentation time: %.2f s", time.perf_counter() - start_time)

        return SegmentationResult(
            document_id=doc.document_id,
            segments=segments,
            segmentation_method="llm",
            errors=errors,
        )

    def _plan_segments(
        self, pages: list[PageContent]
    ) -> tuple[list[_LLMSegment], list[SegmentationError]]:
        """Returns the raw (unrepaired) LLM segments plus any call errors.

        Single-shot when the compact payload fits the budget; otherwise the
        document is processed in overlapping windows and their boundaries are
        stitched back together.
        """
        payload = _document_payload(pages, self.options)
        est_tokens = len(payload) // 4  # rough chars->tokens estimate

        if est_tokens <= self.options.max_input_tokens:
            try:
                plan = self._call_llm(payload)
                return list(plan.segments), []
            except Exception as exc:  # noqa: BLE001 - degrade instead of aborting
                logger.exception("Full-context segmentation call failed")
                # No scope: the failure concerns the whole-document call.
                return [], [
                    SegmentationError(
                        error_type=SegmentationErrorType.LLM_CALL_FAILED,
                        message=f"full-context segmentation failed: {exc}",
                    )
                ]

        logger.debug(
            "Payload ~%d tok > budget %d -> windowing (%d pages, %d overlap)",
            est_tokens,
            self.options.max_input_tokens,
            self.options.window_pages,
            self.options.window_overlap,
        )
        return self._plan_windowed(pages)

    def _plan_windowed(
        self, pages: list[PageContent]
    ) -> tuple[list[_LLMSegment], list[SegmentationError]]:
        """Large-document fallback: per-window plans stitched into boundaries.

        Each window is segmented independently; a page that any window reports as
        a segment start -- without being that window's own first page -- is a true
        boundary. Boundaries are deduplicated across the window overlaps and then
        turned into contiguous segments. Confidence is dropped here (it is not
        meaningful across stitched windows); _repair_segments fills None.
        """
        errors: list[SegmentationError] = []
        boundary_pages: set[int] = set()

        for window in _windows(
            pages, self.options.window_pages, self.options.window_overlap
        ):
            window_start = window[0].page_number
            window_end = window[-1].page_number
            try:
                plan = self._call_llm(_document_payload(window, self.options))
            except Exception as exc:  # noqa: BLE001 - one window must not abort all
                logger.exception(
                    "Windowed segmentation call failed at page %d", window_start
                )
                # Scope is the failed window's page range.
                errors.append(
                    SegmentationError(
                        error_type=SegmentationErrorType.LLM_CALL_FAILED,
                        message=f"windowed segmentation failed: {exc}",
                        start_page=window_start,
                        end_page=window_end,
                    )
                )
                continue
            for seg in plan.segments:
                # A segment that starts at the window's first page is an artefact
                # of where the window happens to begin, not a real boundary.
                if seg.start_page > window_start:
                    boundary_pages.add(seg.start_page)

        page_numbers = [p.page_number for p in pages]
        segments = _boundaries_to_segments(page_numbers, boundary_pages)
        return segments, errors

    def _call_llm(self, payload: str) -> _SegmentationPlan:
        """One grammar-constrained Ollama call returning a _SegmentationPlan."""
        opts = self.options
        start_time = time.perf_counter()
        response = ollama.generate(
            model=opts.model,
            prompt=payload,
            system=FULL_CONTEXT_SYSTEM_PROMPT,
            format=_SegmentationPlan.model_json_schema(),
            think=False,
            # num_ctx is REQUIRED: Ollama's default (~2-4K) silently truncates the
            # prompt, so without it the model would only ever see the first pages.
            options={"temperature": opts.temperature, "num_ctx": opts.num_ctx},
            keep_alive=opts.keep_alive,
        )
        logger.debug(
            "LLM full-context call: wall=%.2fs | %s",
            time.perf_counter() - start_time,
            _format_ollama_timing(response),
        )
        return _SegmentationPlan.model_validate_json(response.response)


# ============================================================================
#  Pure helpers (no strategy state)
# ============================================================================


def _page_fingerprint(page: PageContent, options: FullContextOptions) -> dict:
    """Compact page representation: leading blocks, capped text, no bbox.

    Only the first `head_blocks` blocks are kept -- boundary cues (letterhead,
    heading, sender) sit at the top of a page -- and each block's text is capped
    at `max_chars_per_block`. Either limit may be None ("no cap"): a None upper
    slice bound keeps all blocks / each block's full text. Anchored on
    `page_number`, the key the model references in its output.
    """
    blocks = page.blocks[: options.head_blocks]
    return {
        "page_number": page.page_number,
        "blocks": [
            {"text": b.text[: options.max_chars_per_block], "type": b.block_type}
            for b in blocks
        ],
    }


def _document_payload(pages: list[PageContent], options: FullContextOptions) -> str:
    """The full user prompt: every page as a fingerprint, under "pages"."""
    return json.dumps(
        {"pages": [_page_fingerprint(p, options) for p in pages]},
        ensure_ascii=False,
    )


def _windows(
    pages: list[PageContent], size: int, overlap: int
) -> list[list[PageContent]]:
    """Splits pages into overlapping windows of `size` (step = size - overlap)."""
    step = max(1, size - overlap)
    return [pages[i : i + size] for i in range(0, len(pages), step)]


def _boundaries_to_segments(
    page_numbers: list[int], boundary_pages: set[int]
) -> list[_LLMSegment]:
    """Turns a set of boundary-start pages into contiguous _LLMSegments.

    A boundary page opens a new segment; everything before the next boundary (or
    the document end) belongs to it. Confidence is unknown here -> 0.0 placeholder.
    """
    segments: list[_LLMSegment] = []
    start = page_numbers[0]
    prev = page_numbers[0]
    for pn in page_numbers[1:]:
        if pn in boundary_pages:
            segments.append(
                _LLMSegment(start_page=start, end_page=prev, confidence=0.0)
            )
            start = pn
        prev = pn
    segments.append(_LLMSegment(start_page=start, end_page=prev, confidence=0.0))
    return segments


def _repair_segments(
    pages: list[PageContent], llm_segments: list[_LLMSegment]
) -> list[DocumentSegment]:
    """Deterministically turns raw LLM segments into valid DocumentSegments.

    Guarantees the coverage invariant regardless of model output: segments are
    ordered, contiguous, gap-/overlap-free and cover every page exactly once.
    Walks the document's actual page numbers; each LLM start_page that lands on a
    not-yet-consumed page opens a new segment, everything else continues the open
    one. An unusable plan (no valid starts) collapses to one whole-doc segment.
    """
    page_by_number = {p.page_number: p for p in pages}
    ordered_numbers = [p.page_number for p in pages]

    # Pages the LLM marked as a segment start, restricted to real pages.
    starts = {
        seg.start_page for seg in llm_segments if seg.start_page in page_by_number
    }
    # Confidence keyed by start page, for segments we keep.
    confidence_by_start = {
        seg.start_page: seg.confidence
        for seg in llm_segments
        if seg.start_page in page_by_number
    }

    segments: list[DocumentSegment] = []
    current: list[PageContent] = []
    current_confidence: float | None = None

    for i, pn in enumerate(ordered_numbers):
        # The very first page always opens the first segment; later pages open a
        # new one only when the LLM marked them as a start.
        if i == 0 or pn in starts:
            if current:
                segments.append(_build(current, current_confidence))
            current = [page_by_number[pn]]
            current_confidence = confidence_by_start.get(pn)
        else:
            current.append(page_by_number[pn])

    if current:
        segments.append(_build(current, current_confidence))

    return segments


def _build(pages: list[PageContent], confidence: float | None) -> DocumentSegment:
    """make_segment with a single explicit confidence (vs. averaged pair scores)."""
    return make_segment(pages, [confidence] if confidence is not None else [])


def _format_ollama_timing(response: ollama.GenerateResponse) -> str:
    """Breaks an Ollama call's wall-clock into load / prefill / decode.

    Durations come back in nanoseconds and any field may be None.
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
