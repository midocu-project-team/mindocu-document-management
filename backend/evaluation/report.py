"""Rendering of evaluation results: rich tables for the console + a JSON dump.

Kept separate from the harness so the scoring logic stays free of presentation
concerns. The JSON dump is the machine-readable record (diffable across runs);
the tables are for eyeballing a strategy comparison.
"""

import json
from dataclasses import asdict
from pathlib import Path

from rich.console import Console
from rich.table import Table

from evaluation.harness import SegmentationEvaluation
from evaluation.metrics import ReaderQuality


def render_reader_table(rows: list[tuple[str, ReaderQuality]]) -> Table:
    """Intrinsic reader-quality table, one row per PDF."""
    table = Table(title="Reader quality (intrinsic)")
    for col in (
        "PDF", "pages", "coverage", "mean_conf",
        "min_conf", "ocr%", "empty%", "blocks/pg",
    ):
        table.add_column(col)
    for pdf_name, q in rows:
        table.add_row(
            pdf_name,
            f"{q.pages_read}/{q.total_pages}",
            f"{q.coverage:.2f}",
            _fmt_opt(q.mean_confidence),
            _fmt_opt(q.min_confidence),
            f"{q.ocr_page_ratio:.0%}",
            f"{q.empty_page_ratio:.0%}",
            f"{q.mean_blocks_per_page:.1f}",
        )
    return table


def render_segmentation_table(rows: list[SegmentationEvaluation]) -> Table:
    """Segmentation quality + speed + cost, one row per (strategy, PDF)."""
    table = Table(title="Segmentation (quality / speed / cost)")
    for col in (
        "strategy", "PDF", "F1", "F1±tol", "prec", "rec",
        "seg pred/true", "wall s", "s/pg", "calls", "tokens", "err",
    ):
        table.add_column(col)
    for r in rows:
        table.add_row(
            r.strategy_name,
            r.pdf_name,
            f"{r.exact_boundary.f1:.2f}",
            f"{r.tolerant_boundary.f1:.2f}",
            f"{r.exact_boundary.precision:.2f}",
            f"{r.exact_boundary.recall:.2f}",
            f"{r.n_predicted_segments}/{r.n_true_segments}",
            f"{r.wall_seconds:.1f}",
            f"{r.seconds_per_page:.2f}",
            str(r.usage.calls),
            str(r.usage.prompt_tokens + r.usage.completion_tokens),
            str(r.errors),
        )
    return table


def print_report(
    reader_rows: list[tuple[str, ReaderQuality]],
    segmentation_rows: list[SegmentationEvaluation],
    *,
    console: Console | None = None,
) -> None:
    """Prints both tables to the console."""
    console = console or Console()
    if reader_rows:
        console.print(render_reader_table(reader_rows))
    if segmentation_rows:
        console.print(render_segmentation_table(segmentation_rows))


def dump_json(
    reader_rows: list[tuple[str, ReaderQuality]],
    segmentation_rows: list[SegmentationEvaluation],
    path: Path,
) -> None:
    """Writes a machine-readable record of one evaluation run."""
    payload = {
        "reader": {name: asdict(q) for name, q in reader_rows},
        "segmentation": [asdict(r) for r in segmentation_rows],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


# ============================================================================
#  Pure helpers
# ============================================================================


def _fmt_opt(value: float | None) -> str:
    """Formats an optional score; '-' when unknown."""
    return f"{value:.2f}" if value is not None else "-"
