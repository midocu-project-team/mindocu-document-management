import time

from pydantic import BaseModel, ValidationError

from pipeline.datatypes import (
    DocumentSegment,
    EnrichedSegment,
    EnrichmentError,
    EnrichmentErrorType,
    EnrichmentResult,
    SegmentationResult,
    SummaryReference,
)
from llm import LLMProvider
from logging_config import get_logger
from pipeline.enrichment.keyword_relevance.prompt import TITLE_SUMMARY_SYSTEM_PROMPT
from pipeline.enrichment.strategy import EnrichmentStrategy
from pipeline.enrichment.utils import RelevanceKeywords, decide_relevance
from pipeline.grounding import build_grounded_references_schema


logger = get_logger(__name__)
logger.setLevel(level="DEBUG")


class KeywordRelevanceOptions(BaseModel):
    """Configuration for KeywordRelevanceEnrichmentStrategy.

    Bundled into one object so the strategy constructor stays small (mirrors
    FullContextOptions). Endpoint properties (model name, context size, ...)
    live on the injected LLMProvider, not here.
    """

    temperature: float = 0.0

    # Head-biased input cap per segment: type/title cues (letterhead, heading,
    # subject line) sit at the top of a document, so the payload keeps the
    # first N characters of the segment text. None means "no cap" -- mind the
    # provider's context window (Ollama silently truncates beyond num_ctx).
    max_input_chars: int | None = 24_000

    # Whether to spend LLM calls on segments the keyword decision already
    # marked irrelevant. Off by default: summarizing a Signaturprüfprotokoll
    # is wasted wall-clock/cost.
    enrich_irrelevant: bool = False


def build_title_reference_schema(valid_block_ids: list[int]) -> type[BaseModel]:
    """LLM-output schema with block_ids constrained to this segment's blocks.

    `title` comes first (see `build_grounded_references_schema`'s `extra_fields`)
    so the model fixes the document type before summarizing.
    """
    return build_grounded_references_schema(
        valid_block_ids,
        extra_fields={"title": (str, ...)},
        model_name="ValidTitleReference",
    )


class TitleReference(BaseModel):
    """Title + grounded references, parsed back from the (constrained) output."""

    title: str
    references: list[SummaryReference]



# ============================================================================
#  Enrichment strategy
# ============================================================================


class KeywordRelevanceEnrichmentStrategy(EnrichmentStrategy):
    """Keyword relevance plus per-segment LLM title/summary generation.

    Relevance is the shared deterministic heading-keyword decision
    (enrichment/utils.py) and is computed first; the injected LLM is then
    asked for a title and a summary -- by default only for relevant segments.
    A failed call degrades that one segment to title/summary=None plus a
    segment-scoped EnrichmentError instead of aborting the run.
    """

    def __init__(
        self,
        provider: LLMProvider,
        keywords: RelevanceKeywords,
        options: KeywordRelevanceOptions | None = None,
    ) -> None:
        self.provider = provider
        self.keywords = keywords
        self.options = options or KeywordRelevanceOptions()

    def enrich_segments(self, segmentation: SegmentationResult) -> EnrichmentResult:
        """Enriches every stage-2 segment with relevance, title and summary."""
        start_time = time.perf_counter()
        segments: list[EnrichedSegment] = []
        errors: list[EnrichmentError] = []

        for segment in segmentation.segments:
            enriched, error = self._enrich(segment)
            segments.append(enriched)
            if error is not None:
                errors.append(error)

        logger.debug("Enrichment time: %.2f s", time.perf_counter() - start_time)

        return EnrichmentResult(
            document_id=segmentation.document_id,
            segments=segments,
            enrichment_method="llm+keyword",
            relevance_keywords=self.keywords.all_keywords(),
            errors=errors,
        )

    def _enrich(
        self, segment: DocumentSegment
    ) -> tuple[EnrichedSegment, EnrichmentError | None]:
        """One segment: deterministic relevance first, then gated generation."""
        relevance, matched = decide_relevance(segment, self.keywords)
        generated: TitleReference | None = None
        error: EnrichmentError | None = None
        if relevance or self.options.enrich_irrelevant:
            generated, error = self._generate(segment)

        enriched = EnrichedSegment.from_segment(
            segment,
            title=generated.title if generated else None,
            references=generated.references if generated else None,
            relevance=relevance,
            matched_keywords=matched,
        )
        return enriched, error

    def _generate(
        self, segment: DocumentSegment
    ) -> tuple[TitleReference | None, EnrichmentError | None]:
        """One title/summary call; failures degrade to (None, scoped error)."""

        block_ids = [block.block_id for block in segment.blocks]
        if not block_ids:
            return None, None

        payload = _segment_payload(segment, self.options.max_input_chars)
        # Constrain block_ids to this segment's blocks (see builder docstring).
        schema = build_title_reference_schema(block_ids)
        try:
            return self._call_llm(segment, payload, schema), None
        except ValidationError as exc:
            logger.exception("Unusable title/summary for segment %s", segment.segment_id)
            return None, _segment_error(EnrichmentErrorType.INVALID_OUTPUT, exc, segment)
        except Exception as exc:  # noqa: BLE001 - one bad segment must not abort all
            logger.exception("Title/summary call failed for segment %s", segment.segment_id)
            return None, _segment_error(EnrichmentErrorType.LLM_CALL_FAILED, exc, segment)

    def _call_llm(
        self, segment: DocumentSegment, payload: str, schema: type[BaseModel]
    ) -> TitleReference:
        """One schema-constrained provider call returning a title + references."""
        start_time = time.perf_counter()
        response = self.provider.generate(
            payload,
            system=TITLE_SUMMARY_SYSTEM_PROMPT,
            schema=schema,
            temperature=self.options.temperature,
        )
        logger.debug(
            "LLM title/summary call (segment pages %d-%d): wall=%.2fs | %s",
            segment.start_page,
            segment.end_page,
            time.perf_counter() - start_time,
            response.timing_summary(),
        )
        return TitleReference.model_validate_json(response.text)


# ============================================================================
#  Pure helpers (no strategy state)
# ============================================================================


def _segment_payload(segment: DocumentSegment, max_chars: int | None) -> str:
    """The user prompt: the segment's blocks, each tagged with its block_id.

    Every block is rendered as `[#<block_id>] <text>` so the model can ground
    each reference's block_ids in the input (the `[#id]` markers). Type/title
    cues sit at the top of a document, so truncation keeps the leading blocks
    until `max_chars` is reached -- block-wise, never mid-block, but always at
    least the first block. A None cap keeps every block.
    """
    lines: list[str] = []
    used = 0
    for block in segment.blocks:
        line = f"[#{block.block_id}] {block.text}"
        if max_chars is not None and lines and used + len(line) > max_chars:
            break
        lines.append(line)
        used += len(line) + 1  # +1 for the joining newline
    text = "\n".join(lines)
    return text[:max_chars] if max_chars is not None else text


def _segment_error(
    error_type: EnrichmentErrorType, exc: Exception, segment: DocumentSegment
) -> EnrichmentError:
    """A segment-scoped stage-3 error for one failed title/summary call."""
    return EnrichmentError(
        error_type=error_type,
        message=f"title/summary generation failed: {exc}",
        segment_id=segment.segment_id,
    )
