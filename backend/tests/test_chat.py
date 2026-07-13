"""Unit tests for the segment-retrieval chat strategy.

Covers the two-stage flow (segment selection -> grounded answer), the
"nothing found" / call-failure fallbacks, history handling and the
max_segments cap. The LLM side runs against a canned fake provider that
returns one response per call, never a real backend.
"""

import itertools
import json
import uuid
from datetime import datetime

from pydantic import BaseModel

from llm import LLMProvider, LLMResponse
from pipeline.chat.segment_retrieval.chat import (
    GENERATION_FAILED_TEXT,
    NOT_FOUND_TEXT,
    ChatOptions,
    SegmentRetrievalChatStrategy,
)
from pipeline.datatypes import (
    BlockType,
    ChatTurn,
    ContentBlock,
    DocumentSegment,
    EnrichedSegment,
    PageContent,
)
from pipeline.document import Document

# --------------------------------------------------------------------------
# Test doubles
# --------------------------------------------------------------------------


class QueueProvider(LLMProvider):
    """Returns each of `responses` in order (one per `generate()` call).

    An entry may be an `Exception` to simulate a failed call. Records every
    prompt/system so tests can assert on payload content and call count.
    """

    def __init__(self, responses: list[str | Exception]):
        self.responses = list(responses)
        self.prompts: list[str] = []
        self.systems: list[str | None] = []

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        schema: type[BaseModel] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        self.prompts.append(prompt)
        self.systems.append(system)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return LLMResponse(text=response)


def selection_response(indices: list[int]) -> str:
    return json.dumps({"segment_indices": indices})


def answer_response(references: list[dict]) -> str:
    return json.dumps({"references": references})


_block_ids = itertools.count()


def make_block(text: str, block_type: BlockType = BlockType.PARAGRAPH) -> ContentBlock:
    return ContentBlock(
        block_id=next(_block_ids), text=text, block_type=block_type, bbox=None
    )


def make_page(page_number: int, blocks: list[ContentBlock]) -> PageContent:
    return PageContent(
        page_number=page_number,
        raw_text=" ".join(block.text for block in blocks),
        blocks=blocks,
        was_ocr_applied=False,
        confidence=None,
        width_pt=595.0,
        height_pt=842.0,
    )


def make_enriched_segment(
    page_number: int,
    text: str,
    *,
    title: str | None,
    summary: str | None,
) -> EnrichedSegment:
    page = make_page(page_number, [make_block(text)])
    segment = DocumentSegment(
        start_page=page_number,
        end_page=page_number,
        raw_text=page.raw_text,
        pages=[page],
        confidence=None,
    )
    references = (
        [{"text": summary, "block_ids": [b.block_id for b in segment.blocks]}]
        if summary is not None
        else None
    )
    return EnrichedSegment.from_segment(
        segment,
        title=title,
        references=references,
        relevance=True,
        matched_keywords=[],
    )


DOC_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def make_document(segments: list[EnrichedSegment]) -> Document:
    now = datetime.now()
    return Document(
        document_id=DOC_ID,
        file_name="akte.pdf",
        file_size_bytes=1,
        total_pages=max((s.end_page for s in segments), default=0),
        ocr_engine="tesseract:deu+eng",
        pages=[page for segment in segments for page in segment.pages],
        segments=segments,
        enrichment_method="llm+keyword",
        extracted_at=now,
        enriched_at=now,
    )


# --------------------------------------------------------------------------
# No-context short circuits (never call the model without something to ground in)
# --------------------------------------------------------------------------


def test_document_with_no_segments_returns_not_found_without_any_call():
    provider = QueueProvider([])
    strategy = SegmentRetrievalChatStrategy(provider)

    answer = strategy.answer(make_document([]), "Wer ist der Vater?", [])

    assert len(answer) == 1
    assert answer[0].text == NOT_FOUND_TEXT
    assert answer[0].block_ids == []
    assert provider.prompts == []


def test_empty_selection_returns_not_found_without_a_second_call():
    segment = make_enriched_segment(1, "Antrag", title="Antrag", summary="Ein Antrag.")
    provider = QueueProvider([selection_response([])])
    strategy = SegmentRetrievalChatStrategy(provider)

    answer = strategy.answer(make_document([segment]), "Wie ist das Wetter?", [])

    assert len(answer) == 1
    assert answer[0].text == NOT_FOUND_TEXT
    assert answer[0].block_ids == []
    assert len(provider.prompts) == 1  # no answer call spent


# --------------------------------------------------------------------------
# Happy path: selection -> grounded answer
# --------------------------------------------------------------------------


def test_selects_relevant_segment_and_grounds_the_answer():
    irrelevant = make_enriched_segment(
        1, "Zustellungsurkunde", title="Zustellungsurkunde", summary="Zugestellt."
    )
    relevant = make_enriched_segment(
        2, "Der Vater heißt Herr Meier.", title="Anschreiben", summary="Vorstellung."
    )
    target_block_id = relevant.blocks[0].block_id
    provider = QueueProvider(
        [
            selection_response([2]),
            answer_response(
                [{"text": "Der Vater heißt Herr Meier.", "block_ids": [target_block_id]}]
            ),
        ]
    )
    strategy = SegmentRetrievalChatStrategy(provider)

    answer = strategy.answer(
        make_document([irrelevant, relevant]), "Wie heißt der Vater?", []
    )

    assert len(answer) == 1
    assert answer[0].text == "Der Vater heißt Herr Meier."
    assert answer[0].block_ids == [target_block_id]

    # The answer payload only carries the selected segment's blocks.
    answer_payload = provider.prompts[1]
    assert f"[#{target_block_id}]" in answer_payload
    irrelevant_block_id = irrelevant.blocks[0].block_id
    assert f"[#{irrelevant_block_id}]" not in answer_payload


def test_untitled_segment_renders_fallback_placeholders_in_selection_payload():
    segment = make_enriched_segment(1, "Text", title=None, summary=None)
    provider = QueueProvider([selection_response([])])
    strategy = SegmentRetrievalChatStrategy(provider)

    strategy.answer(make_document([segment]), "Frage?", [])

    assert "(kein Titel)" in provider.prompts[0]
    assert "(keine Zusammenfassung verfügbar)" in provider.prompts[0]


# --------------------------------------------------------------------------
# Failure degradation: never raise, always return a fallback reference
# --------------------------------------------------------------------------


def test_selection_call_failure_falls_back_to_not_found():
    segment = make_enriched_segment(1, "Text", title="T", summary="S")
    provider = QueueProvider([RuntimeError("connection refused")])
    strategy = SegmentRetrievalChatStrategy(provider)

    answer = strategy.answer(make_document([segment]), "Frage?", [])

    assert answer[0].text == NOT_FOUND_TEXT
    assert len(provider.prompts) == 1  # no answer call after a failed selection


def test_unparseable_selection_output_falls_back_to_not_found():
    segment = make_enriched_segment(1, "Text", title="T", summary="S")
    provider = QueueProvider(["not json"])
    strategy = SegmentRetrievalChatStrategy(provider)

    answer = strategy.answer(make_document([segment]), "Frage?", [])

    assert answer[0].text == NOT_FOUND_TEXT


def test_answer_call_failure_falls_back_to_generation_failed_text():
    segment = make_enriched_segment(1, "Text", title="T", summary="S")
    provider = QueueProvider(
        [selection_response([1]), RuntimeError("connection refused")]
    )
    strategy = SegmentRetrievalChatStrategy(provider)

    answer = strategy.answer(make_document([segment]), "Frage?", [])

    assert answer[0].text == GENERATION_FAILED_TEXT
    assert answer[0].block_ids == []


# --------------------------------------------------------------------------
# max_segments cap + de-duplication
# --------------------------------------------------------------------------


def test_max_segments_caps_which_segments_reach_the_answer_call():
    segments = [
        make_enriched_segment(i, f"Text {i}", title=f"T{i}", summary=f"S{i}")
        for i in (1, 2, 3)
    ]
    provider = QueueProvider(
        [
            selection_response([1, 2, 3]),
            answer_response([{"text": "Antwort.", "block_ids": []}]),
        ]
    )
    strategy = SegmentRetrievalChatStrategy(provider, ChatOptions(max_segments=2))

    strategy.answer(make_document(segments), "Frage?", [])

    answer_payload = provider.prompts[1]
    assert f"[#{segments[0].blocks[0].block_id}]" in answer_payload
    assert f"[#{segments[1].blocks[0].block_id}]" in answer_payload
    assert f"[#{segments[2].blocks[0].block_id}]" not in answer_payload


def test_duplicate_selected_indices_are_not_sent_twice():
    segment = make_enriched_segment(1, "Text", title="T", summary="S")
    block_id = segment.blocks[0].block_id
    provider = QueueProvider(
        [
            selection_response([1, 1]),
            answer_response([{"text": "Antwort.", "block_ids": [block_id]}]),
        ]
    )
    strategy = SegmentRetrievalChatStrategy(provider)

    strategy.answer(make_document([segment]), "Frage?", [])

    assert provider.prompts[1].count(f"[#{block_id}]") == 1


# --------------------------------------------------------------------------
# History
# --------------------------------------------------------------------------


def test_history_is_included_in_both_prompts():
    segment = make_enriched_segment(1, "Text", title="T", summary="S")
    history = [
        ChatTurn(role="user", text="Wie heißt der Vater?"),
        ChatTurn(role="assistant", text="Herr Meier."),
    ]
    provider = QueueProvider([selection_response([])])
    strategy = SegmentRetrievalChatStrategy(provider)

    strategy.answer(make_document([segment]), "Und wann war das?", history)

    assert "Wie heißt der Vater?" in provider.prompts[0]
    assert "Herr Meier." in provider.prompts[0]


def test_history_is_truncated_to_max_history_turns():
    segment = make_enriched_segment(1, "Text", title="T", summary="S")
    history = [ChatTurn(role="user", text=f"Frage {i}") for i in range(10)]
    provider = QueueProvider([selection_response([])])
    strategy = SegmentRetrievalChatStrategy(provider, ChatOptions(max_history_turns=2))

    strategy.answer(make_document([segment]), "Letzte Frage?", history)

    assert "Frage 9" in provider.prompts[0]
    assert "Frage 8" in provider.prompts[0]
    assert "Frage 7" not in provider.prompts[0]
