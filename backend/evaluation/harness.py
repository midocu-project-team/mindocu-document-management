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

from pipeline.datatypes import (
    CaseFileDocument,
    DocumentSegment,
    EnrichedSegment,
    SegmentationResult,
)
from llm import LLMProvider
from pipeline import (
    EnrichmentStrategy,
    ReaderStrategy,
    SegmentationStrategy,
    make_segment,
)

from evaluation import metrics
from evaluation.ground_truth import GroundTruth
from evaluation.metered_provider import LLMUsage, MeteredProvider

_TESTS_DIR = Path(__file__).resolve().parents[1] / "tests"
ASSETS_DIR = _TESTS_DIR / "assets"  # the test PDFs
CACHE_DIR = _TESTS_DIR / "cached"  # <stem>.cached.json read-once caches
TRUTH_DIR = _TESTS_DIR / "truth"  # <stem>.truth.json ground truths

# A strategy is built per run so it binds to the metered provider.
StrategyFactory = Callable[[LLMProvider], SegmentationStrategy]
EnrichmentStrategyFactory = Callable[[LLMProvider], EnrichmentStrategy]


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


@dataclass(frozen=True)
class SummaryReferenceRow:
    """One block-grounded summary fragment: its text and the blocks it cites."""

    text: str
    block_ids: list[int]


@dataclass(frozen=True)
class EnrichedSegmentRow:
    """One enriched segment, reduced to what manual inspection needs."""

    start_page: int
    end_page: int
    relevance: bool
    matched_keywords: list[str]
    title: str | None
    summary: str | None  # the references' texts joined; full record kept in JSON
    references: list[SummaryReferenceRow]  # per-fragment text + cited block_ids


@dataclass(frozen=True)
class EnrichmentPrediction:
    """One unscored (enrichment run, PDF) result, for eyeballing the output."""

    strategy_name: str
    pdf_name: str
    segments_source: str  # precursor display name or "ground-truth"
    n_segments: int
    n_irrelevant: int
    segments: list[EnrichedSegmentRow]
    wall_seconds: float
    usage: LLMUsage
    errors: int


def load_cached_document(
    pdf_name: str,
    *,
    reader: ReaderStrategy,
    assets_dir: Path = ASSETS_DIR,
    cache_dir: Path = CACHE_DIR,
    refresh: bool = False,
) -> CaseFileDocument:
    """Loads a read case file from cache, reading once on a cache miss.

    ``refresh`` forces a re-read and rewrites the cache file afterwards; the
    cache does not record which reader produced it, so set ``refresh`` after
    changing the reader strategy or its options.
    """
    cache = cache_dir / f"{Path(pdf_name).stem}.cached.json"
    if cache.exists() and not refresh:
        return CaseFileDocument.model_validate_json(cache.read_text())
    pdf_bytes = io.BytesIO((assets_dir / pdf_name).read_bytes())
    doc = reader.read_document(pdf_bytes, pdf_name)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(doc.model_dump_json())
    return doc


def load_cached_segmentation(
    pdf_name: str,
    doc: CaseFileDocument,
    *,
    factory: StrategyFactory,
    provider: LLMProvider,
    cache_dir: Path = CACHE_DIR,
    refresh: bool = False,
) -> SegmentationResult:
    """Loads a PDF's segments from cache, segmenting once on a cache miss.

    The stage-2 sibling of ``load_cached_document``: the enrichment precursor
    run segments each PDF once and stores the SegmentationResult as
    ``<stem>.segments.json``; later runs deserialize that instead of re-running
    the LLM. The cache does not record which run produced it — ``refresh``
    forces a re-segmentation after precursor changes.
    """
    cache = cache_dir / f"{Path(pdf_name).stem}.segments.json"
    if cache.exists() and not refresh:
        return SegmentationResult.model_validate_json(cache.read_text())
    result = factory(provider).segment_document(doc)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(result.model_dump_json())
    return result


def truth_segmentation(
    doc: CaseFileDocument, truth: GroundTruth
) -> SegmentationResult:
    """Builds the ground-truth SegmentationResult for a read case file.

    Used when the enrichment section has no segmentation precursor: enrichment
    then runs on the true segments, isolating stage-3 quality from stage-2
    boundary errors.
    """
    pages = {p.page_number: p for p in doc.pages}
    segments = [
        make_segment(
            [pages[n] for n in range(s.start_page, s.end_page + 1) if n in pages], []
        )
        for s in truth.segments
    ]
    return SegmentationResult(
        document_id=doc.document_id,
        segments=segments,
        segmentation_method="ground-truth",
        errors=[],
    )


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


def predict_enrichment(
    *,
    strategy_name: str,
    factory: EnrichmentStrategyFactory,
    segmentation: SegmentationResult,
    segments_source: str,
    pdf_name: str,
    provider: LLMProvider,
) -> EnrichmentPrediction:
    """Runs an enrichment strategy without scoring and returns the raw output.

    The stage-3 sibling of ``predict_segmentation``: there is no enrichment
    ground truth yet, so the result is reduced to rows for manual inspection.
    """
    metered = MeteredProvider(provider)
    strategy = factory(metered)

    started = time.perf_counter()
    result = strategy.enrich_segments(segmentation)
    wall_seconds = time.perf_counter() - started

    return EnrichmentPrediction(
        strategy_name=strategy_name,
        pdf_name=pdf_name,
        segments_source=segments_source,
        n_segments=len(result.segments),
        n_irrelevant=sum(1 for s in result.segments if not s.relevance),
        segments=[_enriched_row(s) for s in result.segments],
        wall_seconds=wall_seconds,
        usage=metered.usage,
        errors=len(result.errors),
    )


# ============================================================================
#  Pure helpers (no harness state)
# ============================================================================


def _enriched_row(segment: EnrichedSegment) -> EnrichedSegmentRow:
    """Reduces one enriched segment to its inspectable row."""
    return EnrichedSegmentRow(
        start_page=segment.start_page,
        end_page=segment.end_page,
        relevance=segment.relevance,
        matched_keywords=list(segment.matched_keywords),
        title=segment.title,
        summary=segment.summary,
        references=[
            SummaryReferenceRow(text=r.text, block_ids=list(r.block_ids))
            for r in (segment.references or [])
        ],
    )


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
