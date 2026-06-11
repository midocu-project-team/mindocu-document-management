"""CLI entry point: run an evaluation described by a YAML config.

Usage (from ``backend/``)::

    uv run python -m evaluation [tests/evaluation/<run>.yaml]

Without an argument the default config ``tests/evaluation/default.yaml`` is
used. The heavy lifting lives in ``harness``/``metrics``/``report``; this
module only wires the validated config into them.
"""

from pathlib import Path

from datatypes import CaseFileDocument
from logging_config import get_logger

from evaluation.config import EvaluationConfig, load_config
from evaluation.ground_truth import (
    GroundTruth,
    ground_truth_path,
    load_ground_truth,
    make_template,
)
from evaluation.harness import (
    SegmentationEvaluation,
    SegmentationPrediction,
    evaluate_segmentation,
    load_cached_document,
    predict_segmentation,
)
from evaluation.metrics import ReaderQuality, reader_quality
from evaluation.report import dump_json, print_report

logger = get_logger(__name__)

DEFAULT_CONFIG = (
    Path(__file__).resolve().parents[1] / "tests" / "evaluation" / "default.yaml"
)


def main(argv: list[str]) -> None:
    """Runs one evaluation as described by the YAML config in ``argv[1]``."""
    config_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_CONFIG
    config = load_config(config_path)
    logger.info("Evaluation run configured by %s", config_path)

    docs = {
        pdf: load_cached_document(
            pdf, assets_dir=config.assets_dir, refresh=config.reader.refresh_cache
        )
        for pdf in config.pdfs
    }
    reader_rows = _reader_rows(config, docs)
    segmentation_rows, prediction_rows = _segmentation_outputs(config, docs)

    # predict_only without the segment list would show nothing worth checking.
    show_segments = config.segmentation.show_segments or config.segmentation.predict_only
    print_report(
        reader_rows, segmentation_rows, prediction_rows, show_segments=show_segments
    )
    if config.output_json is not None:
        config.output_json.parent.mkdir(parents=True, exist_ok=True)
        dump_json(reader_rows, segmentation_rows, prediction_rows, config.output_json)
        logger.info("Wrote JSON report to %s", config.output_json)


def _reader_rows(
    config: EvaluationConfig, docs: dict[str, CaseFileDocument]
) -> list[tuple[str, ReaderQuality]]:
    """Intrinsic reader metrics for every loaded PDF (if enabled)."""
    if not config.reader.enabled:
        return []
    return [(pdf, reader_quality(doc)) for pdf, doc in docs.items()]


def _segmentation_outputs(
    config: EvaluationConfig, docs: dict[str, CaseFileDocument]
) -> tuple[list[SegmentationEvaluation], list[SegmentationPrediction]]:
    """Scored evaluations, or unscored predictions in predict_only mode."""
    if not config.segmentation.enabled:
        return [], []
    if config.segmentation.predict_only:
        return [], _prediction_rows(config, docs)
    return _segmentation_rows(config, docs), []


def _segmentation_rows(
    config: EvaluationConfig, docs: dict[str, CaseFileDocument]
) -> list[SegmentationEvaluation]:
    """Scores every configured (run, PDF) pair that has a usable ground truth."""
    truths = _usable_truths(config.assets_dir, docs)
    rows: list[SegmentationEvaluation] = []
    for run in config.segmentation.runs:
        # One provider per run: MLX caches the loaded model in memory and
        # Ollama keeps it warm via keep_alive — rebuilding per PDF wastes both.
        provider = run.provider.build()
        for pdf, truth in truths.items():
            logger.info("Evaluating %s on %s", run.display_name, pdf)
            rows.append(
                evaluate_segmentation(
                    strategy_name=run.display_name,
                    factory=run.build_strategy,
                    doc=docs[pdf],
                    truth=truth,
                    provider=provider,
                    tolerance=config.segmentation.tolerance,
                )
            )
    return rows


def _prediction_rows(
    config: EvaluationConfig, docs: dict[str, CaseFileDocument]
) -> list[SegmentationPrediction]:
    """Runs every configured run on every PDF without scoring (no truth needed)."""
    rows: list[SegmentationPrediction] = []
    for run in config.segmentation.runs:
        # One provider per run, reused across PDFs (see _segmentation_rows).
        provider = run.provider.build()
        for pdf, doc in docs.items():
            logger.info("Predicting with %s on %s", run.display_name, pdf)
            rows.append(
                predict_segmentation(
                    strategy_name=run.display_name,
                    factory=run.build_strategy,
                    doc=doc,
                    pdf_name=pdf,
                    provider=provider,
                )
            )
    return rows


def _usable_truths(
    assets_dir: Path, docs: dict[str, CaseFileDocument]
) -> dict[str, GroundTruth]:
    """The loaded ground truths of all PDFs that have a filled-in one."""
    return {
        pdf: truth
        for pdf, doc in docs.items()
        if (truth := _load_or_template_truth(assets_dir, pdf, doc)) is not None
    }


def _load_or_template_truth(
    assets_dir: Path, pdf_name: str, doc: CaseFileDocument
) -> GroundTruth | None:
    """Loads a PDF's ground truth; writes a template and skips when absent."""
    path = ground_truth_path(assets_dir, pdf_name)
    if not path.exists():
        path.write_text(make_template(pdf_name, len(doc.pages)), encoding="utf-8")
        logger.warning(
            "No ground truth for %s — wrote template %s; fill it in and rerun.",
            pdf_name,
            path,
        )
        return None
    truth = load_ground_truth(path)
    if truth.is_template:
        logger.warning("Ground truth %s is still an unfilled template — skipping.", path)
        return None
    return truth
