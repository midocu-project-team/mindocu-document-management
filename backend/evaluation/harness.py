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

from datatypes import CaseFileDocument, DocumentSegment
from llm import LLMProvider
from reader import read_document
from segmentation.strategy import SegmentationStrategy

from evaluation import metrics
from evaluation.ground_truth import GroundTruth
from evaluation.metered_provider import LLMUsage, MeteredProvider

_TESTS_DIR = Path(__file__).resolve().parents[1] / "tests"
ASSETS_DIR = _TESTS_DIR / "assets"  # the test PDFs
CACHE_DIR = _TESTS_DIR / "cached"  # <stem>.cached.json read-once caches
TRUTH_DIR = _TESTS_DIR / "truth"  # <stem>.truth.json ground truths

# A strategy is built per run so it binds to the metered provider.
StrategyFactory = Callable[[LLMProvider], SegmentationStrategy]


@dataclass(frozen=True)
class PredictedSegment:
    """One predicted segment, reduced to what manual inspection needs."""

    start_page: int
    end_page: int
    confidence: float | None
    exact_match: bool | None = None  # None when there is no ground truth


@dataclass(frozen=True)
class SegmentationPrediction:
    """One unscored (strategy, PDF) run, for eyeballing the raw output."""

    strategy_name: str
    pdf_name: str
    n_pages: int
    segments: list[PredictedSegment]
    wall_seconds: float
    usage: LLMUsage
    errors: int


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
    segments: list[PredictedSegment]
    usage: LLMUsage
    errors: int


def load_cached_document(
    pdf_name: str,
    *,
    assets_dir: Path = ASSETS_DIR,
    cache_dir: Path = CACHE_DIR,
    refresh: bool = False,
) -> CaseFileDocument:
    """Loads a read case file from cache, OCR'ing once on a cache miss.

    ``refresh`` forces a re-read (e.g. after reader changes) and rewrites the
    cache file afterwards.
    """
    cache = cache_dir / f"{Path(pdf_name).stem}.cached.json"
    if cache.exists() and not refresh:
        return CaseFileDocument.model_validate_json(cache.read_text())
    pdf_bytes = io.BytesIO((assets_dir / pdf_name).read_bytes())
    doc = read_document(pdf_bytes, pdf_name)
    cache.parent.mkdir(parents=True, exist_ok=True)
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
    true_ranges = {(s.start_page, s.end_page) for s in truth.segments}
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
        segments=_predicted_segments(result.segments, expected=true_ranges),
        usage=metered.usage,
        errors=len(result.errors),
    )


def predict_segmentation(
    *,
    strategy_name: str,
    factory: StrategyFactory,
    doc: CaseFileDocument,
    pdf_name: str,
    provider: LLMProvider,
) -> SegmentationPrediction:
    """Runs a strategy without a ground truth and returns the raw segments.

    The unscored sibling of ``evaluate_segmentation`` — used to inspect what a
    strategy actually predicts before a ground-truth file exists.
    """
    metered = MeteredProvider(provider)
    strategy = factory(metered)

    started = time.perf_counter()
    result = strategy.segment_document(doc)
    wall_seconds = time.perf_counter() - started

    return SegmentationPrediction(
        strategy_name=strategy_name,
        pdf_name=pdf_name,
        n_pages=len(doc.pages),
        segments=_predicted_segments(result.segments),
        wall_seconds=wall_seconds,
        usage=metered.usage,
        errors=len(result.errors),
    )


# ============================================================================
#  Pure helpers (no harness state)
# ============================================================================


def _predicted_segments(
    segments: list[DocumentSegment], expected: set[tuple[int, int]] | None = None
) -> list[PredictedSegment]:
    """Reduces strategy output to inspectable rows, flagging exact truth hits."""
    return [
        PredictedSegment(
            start_page=s.start_page,
            end_page=s.end_page,
            confidence=s.confidence,
            exact_match=(
                None if expected is None else (s.start_page, s.end_page) in expected
            ),
        )
        for s in segments
    ]
