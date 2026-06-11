from abc import ABC, abstractmethod

from pipeline.datatypes import EnrichmentResult, SegmentationResult


class EnrichmentStrategy(ABC):
    """Interface for a stage-3 enrichment strategy.

    A strategy turns a segmented case file into an EnrichmentResult. Concrete
    strategies carry their own configuration (keyword rules, an LLM provider,
    ...) as instance state and are passed around polymorphically.
    """

    @abstractmethod
    def enrich_segments(self, segmentation: SegmentationResult) -> EnrichmentResult: ...
