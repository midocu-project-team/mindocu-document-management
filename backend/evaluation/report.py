"""Rendering of evaluation results: rich tables for the console + a JSON dump.

Kept separate from the harness so the scoring logic stays free of presentation
concerns. The JSON dump is the machine-readable record (diffable across runs);
the tables are for eyeballing a strategy comparison.
"""

import json
from dataclasses import asdict
from pathlib import Path

from rich.console import Console
from rich.markup import escape
from rich.table import Table

from evaluation.harness import (
    EnrichmentPrediction,
    SegmentationEvaluation,
    SegmentationPrediction,
    SummaryReferenceRow,
)
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


def render_prediction_table(rows: list[SegmentationPrediction]) -> Table:
    """Summary of unscored runs: output size, speed and cost per (strategy, PDF)."""
    table = Table(title="Segmentation predictions (unscored)")
    for col in ("strategy", "PDF", "segments", "wall s", "s/pg", "calls", "tokens", "err"):
        table.add_column(col)
    for r in rows:
        table.add_row(
            r.strategy_name,
            r.pdf_name,
            str(len(r.segments)),
            f"{r.wall_seconds:.1f}",
            f"{r.wall_seconds / r.n_pages if r.n_pages else 0.0:.2f}",
            str(r.usage.calls),
            str(r.usage.prompt_tokens + r.usage.completion_tokens),
            str(r.errors),
        )
    return table


def render_segments_table(
    rows: list[SegmentationEvaluation | SegmentationPrediction],
) -> Table:
    """Per-segment detail: one row per predicted segment of every run.

    ``match`` compares against the ground truth ('-' when the run was unscored).
    """
    table = Table(title="Predicted segments (detail)")
    for col in ("strategy", "PDF", "#", "pages", "n", "conf", "match"):
        table.add_column(col)
    for r in rows:
        for index, segment in enumerate(r.segments, start=1):
            table.add_row(
                r.strategy_name,
                r.pdf_name,
                str(index),
                f"{segment.start_page}-{segment.end_page}",
                str(segment.end_page - segment.start_page + 1),
                _fmt_opt(segment.confidence),
                _fmt_match(segment.exact_match),
            )
    return table


def render_enrichment_table(rows: list[EnrichmentPrediction]) -> Table:
    """Summary per (enrichment run, PDF): relevance split, speed and cost."""
    table = Table(title="Enrichment (unscored)")
    for col in (
        "strategy", "PDF", "segments src", "segs", "irrelevant",
        "wall s", "calls", "tokens", "err",
    ):
        table.add_column(col)
    for r in rows:
        table.add_row(
            r.strategy_name,
            r.pdf_name,
            r.segments_source,
            str(r.n_segments),
            str(r.n_irrelevant),
            f"{r.wall_seconds:.1f}",
            str(r.usage.calls),
            str(r.usage.prompt_tokens + r.usage.completion_tokens),
            str(r.errors),
        )
    return table


def render_enriched_segments_table(rows: list[EnrichmentPrediction]) -> Table:
    """Per-segment detail: relevance, fired keywords, title and the grounded
    summary references (one ``fragment [#block_ids]`` line per reference)."""
    table = Table(title="Enriched segments (detail)")
    for col in ("strategy", "PDF", "#", "pages", "rel", "keywords", "title", "references"):
        table.add_column(col)
    for r in rows:
        for index, seg in enumerate(r.segments, start=1):
            table.add_row(
                r.strategy_name,
                r.pdf_name,
                str(index),
                f"{seg.start_page}-{seg.end_page}",
                _fmt_match(seg.relevance),
                ", ".join(seg.matched_keywords) or "-",
                seg.title or "-",
                _fmt_references(seg.references),
            )
    return table


def print_report(
    reader_rows: list[tuple[str, ReaderQuality]],
    segmentation_rows: list[SegmentationEvaluation],
    prediction_rows: list[SegmentationPrediction] | None = None,
    enrichment_rows: list[EnrichmentPrediction] | None = None,
    *,
    show_segments: bool = False,
    console: Console | None = None,
) -> None:
    """Prints all requested tables to the console."""
    console = console or Console()
    prediction_rows = prediction_rows or []
    enrichment_rows = enrichment_rows or []
    if reader_rows:
        console.print(render_reader_table(reader_rows))
    if segmentation_rows:
        console.print(render_segmentation_table(segmentation_rows))
    if prediction_rows:
        console.print(render_prediction_table(prediction_rows))
    if show_segments and (segmentation_rows or prediction_rows):
        console.print(render_segments_table([*segmentation_rows, *prediction_rows]))
    if enrichment_rows:
        # Unscored by design: the per-segment detail IS the deliverable.
        console.print(render_enrichment_table(enrichment_rows))
        console.print(render_enriched_segments_table(enrichment_rows))


def dump_json(
    reader_rows: list[tuple[str, ReaderQuality]],
    segmentation_rows: list[SegmentationEvaluation],
    prediction_rows: list[SegmentationPrediction],
    enrichment_rows: list[EnrichmentPrediction],
    path: Path,
) -> None:
    """Writes a machine-readable record of one evaluation run."""
    payload = {
        "reader": {name: asdict(q) for name, q in reader_rows},
        "segmentation": [asdict(r) for r in segmentation_rows],
        "predictions": [asdict(r) for r in prediction_rows],
        "enrichment": [asdict(r) for r in enrichment_rows],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


# ============================================================================
#  Pure helpers
# ============================================================================


def _fmt_opt(value: float | None) -> str:
    """Formats an optional score; '-' when unknown."""
    return f"{value:.2f}" if value is not None else "-"


def _fmt_match(value: bool | None) -> str:
    """Formats a boolean flag (exact match / relevance); '-' when unknown."""
    if value is None:
        return "-"
    return "[green]✓[/green]" if value else "[red]✗[/red]"


def _shorten(text: str | None, limit: int = 80) -> str:
    """First ``limit`` characters of an optional text; '-' when unset.

    The console table stays readable this way; the JSON dump keeps the full text.
    """
    if not text:
        return "-"
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _fmt_references(references: list[SummaryReferenceRow]) -> str:
    """One line per reference: the (shortened) summary fragment and its blocks.

    Lets the block grounding be eyeballed against the text; '-' when the segment
    has no references (irrelevant, or generation failed). The JSON dump keeps the
    full, untruncated references.
    """
    if not references:
        return "-"
    lines = "\n".join(
        f"{_shorten(ref.text, 60)} {_fmt_block_ids(ref.block_ids)}"
        for ref in references
    )
    # Escape so the [#id] brackets (and any brackets in the LLM text) render
    # literally instead of being eaten as Rich markup tags.
    return escape(lines)


def _fmt_block_ids(block_ids: list[int]) -> str:
    """The cited block ids as ``[#3, #5]``; ``[–]`` when a reference cites none."""
    return "[" + ", ".join(f"#{b}" for b in block_ids) + "]" if block_ids else "[–]"
