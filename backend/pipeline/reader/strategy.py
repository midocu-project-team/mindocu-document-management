import io
from abc import ABC, abstractmethod

from pipeline.datatypes import CaseFileDocument


class ReaderStrategy(ABC):
    """Interface for a stage-1 reader strategy.

    A strategy turns a PDF byte stream into a CaseFileDocument. Concrete
    strategies carry their backend configuration (OCR engine, pipeline
    options, ...) as instance state and are passed around polymorphically.

    Every implementation must honor the stage-1 contract pinned on the
    dataclasses in ``pipeline.datatypes``: page numbers are 1-based and
    bounding boxes are in PDF points with a bottom-left origin (y grows
    upward) — see ``BoundingBox`` there.
    """

    @abstractmethod
    def read_document(
        self, file: io.BytesIO, file_name: str | None = None
    ) -> CaseFileDocument: ...
