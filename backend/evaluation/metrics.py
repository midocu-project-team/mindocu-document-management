"""Pure evaluation metrics for the mindocu pipeline.

These functions are deliberately free of I/O, LLM and OCR side effects so they
can be unit-tested deterministically with synthetic inputs. The segmentation
metrics operate on plain page-number sets / any object exposing
``start_page``/``end_page`` (both ``DocumentSegment`` and ``TrueSegment`` qualify),
so they never import a concrete strategy. The reader metric reads a
``CaseFileDocument`` and reports only *intrinsic* signals (no reference text).
"""

from dataclasses import dataclass
from typing import Protocol

from datatypes import CaseFileDocument


class _HasPageRange(Protocol):
    """Structural type for anything with an inclusive 1-based page range."""

    start_page: int
    end_page: int


# ============================================================================
#  Segmentation quality
# ============================================================================


@dataclass(frozen=True)
class BoundaryScore:
    """Precision/recall/F1 over document-boundary cut positions."""

    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int
    predicted: int
    expected: int
    tolerance: int


def cut_positions(segments: list[_HasPageRange]) -> set[int]:
    """The set of "cut after page N" positions implied by contiguous segments.

    A segment ending at page e implies a boundary after e, except for the
    segment ending at the document's last page (that is the document end, not an
    internal cut). For gap-/overlap-free coverage this equals all segment ends
    minus the maximum end.
    """
    ends = {s.end_page for s in segments}
    if not ends:
        return set()
    return ends - {max(ends)}


def boundary_score(
    predicted: set[int], expected: set[int], *, tolerance: int = 0
) -> BoundaryScore:
    """Scores predicted boundary cuts against the ground-truth cuts.

    ``tolerance`` allows an off-by-N page slack: a predicted cut counts as a hit
    if some unmatched ground-truth cut lies within ``tolerance`` pages. Each cut
    is matched at most once (greedy nearest-first), so neither side is
    double-counted.
    """
    true_positives = _match_count(predicted, expected, tolerance)
    false_positives = len(predicted) - true_positives
    false_negatives = len(expected) - true_positives

    precision = 1.0 if not predicted else true_positives / len(predicted)
    recall = 1.0 if not expected else true_positives / len(expected)
    f1 = _harmonic_mean(precision, recall)

    return BoundaryScore(
        precision=precision,
        recall=recall,
        f1=f1,
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        predicted=len(predicted),
        expected=len(expected),
        tolerance=tolerance,
    )


def exact_segment_matches(
    predicted: list[_HasPageRange], expected: list[_HasPageRange]
) -> int:
    """How many predicted segments match a ground-truth segment exactly.

    A match means identical (start_page, end_page); the title/label is ignored.
    """
    expected_ranges = {(s.start_page, s.end_page) for s in expected}
    return sum(
        1 for s in predicted if (s.start_page, s.end_page) in expected_ranges
    )


# ============================================================================
#  Reader quality (intrinsic — no reference text)
# ============================================================================


@dataclass(frozen=True)
class ReaderQuality:
    """Intrinsic quality signals for a read ``CaseFileDocument``."""

    pages_read: int
    total_pages: int
    coverage: float  # pages_read / total_pages
    mean_confidence: float | None
    min_confidence: float | None
    ocr_page_ratio: float  # share of pages where OCR was applied
    empty_page_ratio: float  # share of pages with no extracted text
    mean_blocks_per_page: float


def reader_quality(doc: CaseFileDocument) -> ReaderQuality:
    """Derives intrinsic reader-quality metrics from a read case file."""
    pages = doc.pages
    n = len(pages)
    confidences = [p.confidence for p in pages if p.confidence is not None]
    empty = sum(1 for p in pages if not p.raw_text.strip())
    ocr = sum(1 for p in pages if p.was_ocr_applied)
    blocks = sum(len(p.blocks) for p in pages)

    return ReaderQuality(
        pages_read=n,
        total_pages=doc.total_pages,
        coverage=_ratio(n, doc.total_pages),
        mean_confidence=(sum(confidences) / len(confidences)) if confidences else None,
        min_confidence=min(confidences) if confidences else None,
        ocr_page_ratio=_ratio(ocr, n),
        empty_page_ratio=_ratio(empty, n),
        mean_blocks_per_page=_ratio(blocks, n),
    )


# ============================================================================
#  Pure helpers (no state)
# ============================================================================


def _match_count(predicted: set[int], expected: set[int], tolerance: int) -> int:
    """Greedy one-to-one matches between two cut sets within ``tolerance``."""
    if tolerance == 0:
        return len(predicted & expected)

    predicted_sorted = sorted(predicted)
    consumed = [False] * len(predicted_sorted)
    matches = 0
    for target in sorted(expected):
        index = _nearest_unused(predicted_sorted, consumed, target, tolerance)
        if index is not None:
            consumed[index] = True
            matches += 1
    return matches


def _nearest_unused(
    candidates: list[int], consumed: list[bool], target: int, tolerance: int
) -> int | None:
    """Index of the closest unconsumed candidate within tolerance, else None."""
    best_index: int | None = None
    best_distance: int | None = None
    for i, value in enumerate(candidates):
        if consumed[i]:
            continue
        distance = abs(value - target)
        if distance <= tolerance and (best_distance is None or distance < best_distance):
            best_index, best_distance = i, distance
    return best_index


def _harmonic_mean(a: float, b: float) -> float:
    """F1-style harmonic mean; 0.0 when both inputs are 0."""
    return (2 * a * b / (a + b)) if (a + b) else 0.0


def _ratio(numerator: float, denominator: float) -> float:
    """Safe division; 0.0 when the denominator is 0."""
    return numerator / denominator if denominator else 0.0
