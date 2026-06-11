import os
from typing import Literal

from docling.datamodel.pipeline_options import (
    OcrOptions,
    RapidOcrOptions,
    TableFormerMode,
    TesseractCliOcrOptions,
    ThreadedPdfPipelineOptions,
)
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.document_converter import PdfFormatOption
from docling.pipeline.threaded_standard_pdf_pipeline import ThreadedStandardPdfPipeline

type OcrEngine = Literal["tesseract", "rapidocr"]


# Apple Silicon (MPS) does not support float64, which is required by the RT-DETR-Layout model.
# Therefore, models should be run on the CPU; otherwise, the layout stage will crash.
# This is needed because the backend will likely run on a Silicon Mac Studio
def _default_pipeline_options() -> ThreadedPdfPipelineOptions:
    num_cores = os.cpu_count() or 1

    accelerator_options = AcceleratorOptions(
        device=AcceleratorDevice.CPU, num_threads=num_cores
    )
    pipeline_options = ThreadedPdfPipelineOptions(
        do_ocr=True,
        do_table_structure=True,
        generate_page_images=False,
        generate_picture_images=False,
        images_scale=1.0,
        accelerator_options=accelerator_options,
        ocr_batch_size=4,
        layout_batch_size=4,
        table_batch_size=4,
        document_timeout=60 * 60,  # reading may not take longer than 60 minutes
    )

    pipeline_options.table_structure_options.mode = TableFormerMode.FAST

    return pipeline_options


def default_pdf_format_options(
    ocr_engine: OcrEngine = "tesseract",
    ocr_languages: list[str] | None = None,
) -> PdfFormatOption:
    """The standard reading options (threaded pipeline, CPU), selectable OCR engine.

    The parameters cover the YAML-configurable knobs of the evaluation runs;
    callers that need more (pipeline class, backend, ...) build their own
    PdfFormatOption and inject it into DoclingReaderStrategy instead.
    """
    pipeline_options = _default_pipeline_options()
    pipeline_options.ocr_options = _ocr_options(ocr_engine, ocr_languages)
    return PdfFormatOption(
        pipeline_options=pipeline_options,
        pipeline_cls=ThreadedStandardPdfPipeline,
        backend=PyPdfiumDocumentBackend,
    )


def _ocr_options(engine: OcrEngine, languages: list[str] | None) -> OcrOptions:
    """OCR engine selection; ``languages`` defaults to deu+eng (Tesseract-only).

    Tesseract CLI is the default: ~60x faster than RapidOCR on CPU at
    comparable quality. Trade-off: it reports no per-cell OCR confidence, so
    the confidence report's ocr_score stays NaN and
    PageContent.was_ocr_applied cannot be derived (see _was_ocr_applied);
    RapidOCR restores that signal.
    """
    if engine == "rapidocr":
        if languages:
            raise ValueError(
                "ocr_languages is Tesseract-only (RapidOCR binds languages to its models)"
            )
        return RapidOcrOptions()
    if engine != "tesseract":
        raise ValueError(f"unknown OCR engine: {engine!r}")
    return TesseractCliOcrOptions(lang=languages or ["deu", "eng"])
