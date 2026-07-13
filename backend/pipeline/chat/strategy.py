from abc import ABC, abstractmethod

from pipeline.datatypes import ChatTurn, SummaryReference
from pipeline.document import Document


class ChatStrategy(ABC):
    """Interface for a document-chat strategy.

    A strategy answers one question about an already-processed `Document`,
    grounding the answer in the document's blocks -- the same shape as a
    segment summary's `SummaryReference`, so the frontend's click-to-highlight
    mechanism works unchanged for chat answers. Concrete strategies carry
    their own configuration (an LLM provider, retrieval knobs, ...) as
    instance state.
    """

    @abstractmethod
    def answer(
        self, document: Document, question: str, history: list[ChatTurn]
    ) -> list[SummaryReference]:
        """Answers `question` about `document`, given prior turns of `history`."""
