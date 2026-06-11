from abc import ABC, abstractmethod

from datatypes import CaseFileDocument, SegmentationResult


class SegmentationStrategy(ABC):
    """Interface for a stage-2 segmentation strategy.

    A strategy turns a read case file into a SegmentationResult. Concrete
    strategies carry their own configuration (model, thresholds, ...) as
    instance state and are passed around polymorphically.
    """

    @abstractmethod
    def segment_document(self, doc: CaseFileDocument) -> SegmentationResult: ...
