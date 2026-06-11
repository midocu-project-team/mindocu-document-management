"""Evaluation orchestration: load a case file, run a strategy, score it.

This is the side-effecting layer (file I/O, OCR fallback, the LLM call); the
scoring itself is delegated to the pure functions in ``metrics``. Document
loading is cached the same way the explore benchmarks do it: the first run OCRs
the PDF once and writes ``<stem>.cached.json`` next to it, later runs load that.
"""

import io
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from datatypes import CaseFileDocument
from llm import LLMProvider
from reader import read_document
from segmentation.strategy import SegmentationStrategy

from evaluation import metrics
from evaluation.ground_truth import GroundTruth
from evaluation.metered_provider import LLMUsage, MeteredProvider

ASSETS_DIR = Path(__file__).resolve().parents[1] / "tests" / "assets"

# A strategy is built per run so it binds to the metered provider.
StrategyFactory = Callable[[LLMProvider], SegmentationStrategy]


@dataclass(frozen=True)
class SegmentationEvaluation:
    """All metrics for one (strategy, PDF) segmentation run."""

    strategy_name: str
    pdf_name: str
    n_pages: int
    n_predicted_segments: int
    n_true_segments: int
    wall_seconds: float
    seconds_per_page: float
    exact_boundary: metrics.BoundaryScore
    tolerant_boundary: metrics.BoundaryScore
    exact_segment_matches: int
    usage: LLMUsage
    errors: int


def load_cached_document(
    pdf_name: str, *, assets_dir: Path = ASSETS_DIR
) -> CaseFileDocument:
    """Loads a read case file from cache, OCR'ing once on a cache miss."""
    cache = assets_dir / f"{Path(pdf_name).stem}.cached.json"
    if cache.exists():
        return CaseFileDocument.model_validate_json(cache.read_text())
    pdf_bytes = io.BytesIO((assets_dir / pdf_name).read_bytes())
    doc = read_document(pdf_bytes, pdf_name)
    cache.write_text(doc.model_dump_json())
    return doc


def evaluate_segmentation(
    *,
    strategy_name: str,
    factory: StrategyFactory,
    doc: CaseFileDocument,
    truth: GroundTruth,
    provider: LLMProvider,
    tolerance: int = 1,
) -> SegmentationEvaluation:
    """Runs a strategy on one document and scores it against the ground truth."""
    metered = MeteredProvider(provider)
    strategy = factory(metered)

    started = time.perf_counter()
    result = strategy.segment_document(doc)
    wall_seconds = time.perf_counter() - started

    predicted_cuts = metrics.cut_positions(result.segments)
    true_cuts = metrics.cut_positions(truth.segments)
    n_pages = len(doc.pages)

    return SegmentationEvaluation(
        strategy_name=strategy_name,
        pdf_name=truth.file_name,
        n_pages=n_pages,
        n_predicted_segments=len(result.segments),
        n_true_segments=len(truth.segments),
        wall_seconds=wall_seconds,
        seconds_per_page=wall_seconds / n_pages if n_pages else 0.0,
        exact_boundary=metrics.boundary_score(predicted_cuts, true_cuts, tolerance=0),
        tolerant_boundary=metrics.boundary_score(
            predicted_cuts, true_cuts, tolerance=tolerance
        ),
        exact_segment_matches=metrics.exact_segment_matches(
            result.segments, truth.segments
        ),
        usage=metered.usage,
        errors=len(result.errors),
    )
