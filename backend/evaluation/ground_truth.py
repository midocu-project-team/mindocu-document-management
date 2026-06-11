"""Ground-truth schema and loading for segmentation evaluation.

A ground-truth file (``tests/assets/<stem>.truth.json``) records the *true*
document boundaries of a test PDF as a contiguous list of segments, hand-derived
from the human-marked ``markiert`` PDFs. The schema mirrors the relevant part of
``DocumentSegment`` (a 1-based inclusive page range plus an optional label), so
the same boundary metrics apply to predicted and true segments alike.
"""

import json
from pathlib import Path

from pydantic import BaseModel, model_validator


class TrueSegment(BaseModel):
    """One ground-truth document, by inclusive 1-based page range."""

    start_page: int
    end_page: int
    label: str | None = None  # human-readable document name; not scored


class GroundTruth(BaseModel):
    """The annotated true segmentation of one test PDF."""

    file_name: str
    total_pages: int
    segments: list[TrueSegment]

    @model_validator(mode="after")
    def _check_contiguous_coverage(self) -> "GroundTruth":
        """Segments must tile pages 1..total_pages with no gaps or overlaps.

        This catches half-filled templates early with a clear message instead of
        silently producing wrong boundary metrics.
        """
        ordered = sorted(self.segments, key=lambda s: s.start_page)
        expected_start = 1
        for seg in ordered:
            if seg.start_page != expected_start:
                raise ValueError(
                    f"{self.file_name}: gap/overlap at page {expected_start} "
                    f"(segment starts at {seg.start_page})"
                )
            if seg.end_page < seg.start_page:
                raise ValueError(
                    f"{self.file_name}: segment {seg.start_page}-{seg.end_page} "
                    "ends before it starts"
                )
            expected_start = seg.end_page + 1
        if self.segments and expected_start != self.total_pages + 1:
            raise ValueError(
                f"{self.file_name}: segments cover up to page {expected_start - 1}, "
                f"expected {self.total_pages}"
            )
        return self

    @property
    def is_template(self) -> bool:
        """True while the file is still an unfilled placeholder (one segment
        spanning the whole document) — such files are skipped by the evaluators."""
        return len(self.segments) <= 1


def load_ground_truth(path: Path) -> GroundTruth:
    """Loads and validates a single ground-truth JSON file."""
    return GroundTruth.model_validate_json(path.read_text(encoding="utf-8"))


def ground_truth_path(assets_dir: Path, pdf_name: str) -> Path:
    """The conventional ``<stem>.truth.json`` path next to a test PDF."""
    return assets_dir / f"{Path(pdf_name).stem}.truth.json"


def make_template(pdf_name: str, total_pages: int) -> str:
    """A pretty-printed placeholder ground-truth file for a PDF.

    Emits a single whole-document segment the team then splits into the real
    documents. Kept as a string (not written) so callers control the I/O.
    """
    payload = {
        "_comment": (
            "Replace the single placeholder segment with the real documents from "
            "the marked PDF. Segments must tile pages 1..total_pages with no gaps."
        ),
        "file_name": pdf_name,
        "total_pages": total_pages,
        "segments": [
            {"start_page": 1, "end_page": total_pages, "label": "REPLACE_ME"}
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
