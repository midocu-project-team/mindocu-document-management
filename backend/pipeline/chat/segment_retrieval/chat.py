"""Two-stage document chat: pick relevant segments, then answer grounded in their blocks.

Stage 1 is cheap (segment titles/summaries only, already computed by stage 3);
stage 2 pays for raw block text only for the segments stage 1 picked. Both
calls degrade to a fixed fallback answer on failure rather than raising, so
one bad LLM call never surfaces as a 500 to the chat UI.
"""

import enum
import time

from pydantic import BaseModel, ValidationError, create_model

from llm import LLMProvider
from logging_config import get_logger
from pipeline.chat.segment_retrieval.prompts import (
    ANSWER_SYSTEM_PROMPT,
    SELECTION_SYSTEM_PROMPT,
)
from pipeline.chat.strategy import ChatStrategy
from pipeline.datatypes import ChatTurn, EnrichedSegment, SummaryReference
from pipeline.document import Document
from pipeline.grounding import build_grounded_references_schema

logger = get_logger(__name__)

NOT_FOUND_TEXT = "Dazu konnte ich in diesem Dokument keine Information finden."
GENERATION_FAILED_TEXT = "Die Antwort konnte nicht generiert werden."


class ChatOptions(BaseModel):
    """Configuration for SegmentRetrievalChatStrategy."""

    temperature: float = 0.0
    # Cap on how many segments the selection call may hand to the answer call.
    max_segments: int = 5
    # Head-biased cap per segment (same rationale as stage 3's max_input_chars).
    max_input_chars_per_segment: int | None = 12_000
    # Most recent turns kept in both prompts (bounds prompt growth over a session).
    max_history_turns: int = 6


class SegmentRetrievalChatStrategy(ChatStrategy):
    """Segment-summary retrieval, then a grounded answer over the selected blocks.

    Selecting zero segments (or a document with none) skips the answer call
    entirely and returns a canned "not found" reference instead of risking an
    ungrounded guess.
    """

    def __init__(self, provider: LLMProvider, options: ChatOptions | None = None) -> None:
        self.provider = provider
        self.options = options or ChatOptions()

    def answer(
        self, document: Document, question: str, history: list[ChatTurn]
    ) -> list[SummaryReference]:
        recent_history = history[-self.options.max_history_turns :]
        if not document.segments:
            return [SummaryReference(text=NOT_FOUND_TEXT, block_ids=[])]

        selected = self._select_segments(document.segments, question, recent_history)
        if not selected:
            return [SummaryReference(text=NOT_FOUND_TEXT, block_ids=[])]

        return self._generate_answer(selected, question, recent_history)

    def _select_segments(
        self,
        segments: list[EnrichedSegment],
        question: str,
        history: list[ChatTurn],
    ) -> list[EnrichedSegment]:
        """One constrained call picking up to `max_segments` relevant segments."""
        payload = _selection_payload(segments, question, history)
        schema = _build_segment_selection_schema(len(segments))
        start_time = time.perf_counter()
        try:
            response = self.provider.generate(
                payload,
                system=SELECTION_SYSTEM_PROMPT,
                schema=schema,
                temperature=self.options.temperature,
            )
            selection = _SegmentSelection.model_validate_json(response.text)
        except Exception:  # noqa: BLE001 - degrade to "no segments", never raise
            logger.exception("Segment selection failed; answering with no context")
            return []
        logger.debug(
            "Chat segment selection: wall=%.2fs | %s",
            time.perf_counter() - start_time,
            response.timing_summary(),
        )
        indices = selection.segment_indices[: self.options.max_segments]
        return [segments[index - 1] for index in dict.fromkeys(indices)]

    def _generate_answer(
        self,
        selected: list[EnrichedSegment],
        question: str,
        history: list[ChatTurn],
    ) -> list[SummaryReference]:
        """One constrained call answering the question from the selected segments."""
        block_ids = [block.block_id for segment in selected for block in segment.blocks]
        if not block_ids:
            return [SummaryReference(text=NOT_FOUND_TEXT, block_ids=[])]

        payload = _answer_payload(
            selected, question, history, self.options.max_input_chars_per_segment
        )
        schema = build_grounded_references_schema(block_ids, model_name="ChatAnswer")
        start_time = time.perf_counter()
        try:
            response = self.provider.generate(
                payload,
                system=ANSWER_SYSTEM_PROMPT,
                schema=schema,
                temperature=self.options.temperature,
            )
            answer = _ChatAnswerPayload.model_validate_json(response.text)
        except Exception:  # noqa: BLE001 - degrade to a fixed fallback, never raise
            logger.exception("Chat answer generation failed")
            return [SummaryReference(text=GENERATION_FAILED_TEXT, block_ids=[])]
        logger.debug(
            "Chat answer call: wall=%.2fs | %s",
            time.perf_counter() - start_time,
            response.timing_summary(),
        )
        return answer.references


class _SegmentSelection(BaseModel):
    segment_indices: list[int]


class _ChatAnswerPayload(BaseModel):
    references: list[SummaryReference]


# ============================================================================
#  Pure helpers (no strategy state)
# ============================================================================


def _build_segment_selection_schema(segment_count: int) -> type[BaseModel]:
    """Output schema with segment_indices constrained to 1..segment_count."""
    ValidIndex = enum.IntEnum(
        "ValidSegmentIndex", {f"i_{i}": i for i in range(1, segment_count + 1)}
    )
    return create_model("SegmentSelection", segment_indices=(list[ValidIndex], ...))


def _format_history(history: list[ChatTurn]) -> str:
    """Renders prior turns as a small transcript, or "" if there is none."""
    if not history:
        return ""
    lines = [f"{'Nutzer' if turn.role == 'user' else 'Assistent'}: {turn.text}" for turn in history]
    return "Bisheriger Gesprächsverlauf:\n" + "\n".join(lines) + "\n\n"


def _selection_payload(
    segments: list[EnrichedSegment], question: str, history: list[ChatTurn]
) -> str:
    """The segment-selection user prompt: every segment as "[#i] title: summary"."""
    lines = [
        f"[#{index}] {segment.title or '(kein Titel)'}: "
        f"{segment.summary or '(keine Zusammenfassung verfügbar)'}"
        for index, segment in enumerate(segments, start=1)
    ]
    segment_list = "\n".join(lines)
    return f"{_format_history(history)}Frage: {question}\n\nSegmente:\n{segment_list}"


def _answer_payload(
    selected: list[EnrichedSegment],
    question: str,
    history: list[ChatTurn],
    max_chars_per_segment: int | None,
) -> str:
    """The answer user prompt: id-tagged blocks of every selected segment."""
    block_text = "\n".join(
        _segment_blocks_payload(segment, max_chars_per_segment) for segment in selected
    )
    return f"{_format_history(history)}Frage: {question}\n\nAktenauszug:\n{block_text}"


def _segment_blocks_payload(segment: EnrichedSegment, max_chars: int | None) -> str:
    """One segment's blocks as "[#id] text", head-truncated like stage 3's payload."""
    lines: list[str] = []
    used = 0
    for block in segment.blocks:
        line = f"[#{block.block_id}] {block.text}"
        if max_chars is not None and lines and used + len(line) > max_chars:
            break
        lines.append(line)
        used += len(line) + 1  # +1 for the joining newline
    return "\n".join(lines)
