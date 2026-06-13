"""``PipelineRunner`` -- runs the three stages end to end into a ``Document``.

Pure composition in the same dependency-injection style as the stages: the
reader, segmenter and enricher are passed in, the runner only chains them.
It carries no status or persistence knowledge; the optional ``on_stage``
callback lets a caller (e.g. a background job) report progress without the
runner depending on the app layer.
"""

import io
from collections.abc import Callable

from pipeline.document import Document
from pipeline.enrichment.strategy import EnrichmentStrategy
from pipeline.reader.strategy import ReaderStrategy
from pipeline.segmentation.strategy import SegmentationStrategy

# Stage labels handed to the on_stage callback as each stage begins.
StageCallback = Callable[[str], None]


class PipelineRunner:
    """Chains read -> segment -> enrich and aggregates into a ``Document``."""

    def __init__(
        self,
        reader: ReaderStrategy,
        segmenter: SegmentationStrategy,
        enricher: EnrichmentStrategy,
    ) -> None:
        self.reader = reader
        self.segmenter = segmenter
        self.enricher = enricher

    def run(
        self,
        file: io.BytesIO,
        file_name: str,
        on_stage: StageCallback | None = None,
    ) -> Document:
        """Runs the full pipeline on ``file`` and returns the merged ``Document``."""
        _emit(on_stage, "extracting")
        doc = self.reader.read_document(file, file_name)

        _emit(on_stage, "segmenting")
        seg = self.segmenter.segment_document(doc)

        _emit(on_stage, "enriching")
        enr = self.enricher.enrich_segments(seg)

        return Document.from_pipeline(doc, seg, enr)


# Pure helpers (no runner state)


def _emit(on_stage: StageCallback | None, stage: str) -> None:
    """Invokes the progress callback if one was supplied."""
    if on_stage is not None:
        on_stage(stage)
