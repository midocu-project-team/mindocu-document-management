import os

from docling.datamodel.pipeline_options import (
    TableFormerMode,
    TesseractCliOcrOptions,
    ThreadedPdfPipelineOptions,
)
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.document_converter import PdfFormatOption
from docling.pipeline.threaded_standard_pdf_pipeline import ThreadedStandardPdfPipeline


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

    # Tesseract CLI (German + English): ~60x faster than the RapidOCR default on
    # CPU at comparable quality. Trade-off: the Tesseract CLI does not report
    # per-cell OCR confidence, so the confidence report's ocr_score stays NaN and
    # PageContent.was_ocr_applied can no longer be derived (see _was_ocr_applied).
    pipeline_options.ocr_options = TesseractCliOcrOptions(lang=["deu", "eng"])

    return pipeline_options


def default_pdf_format_options() -> PdfFormatOption:
    # Wires the default (threaded, CPU, Tesseract) pipeline options to the
    # threaded pipeline and the pypdfium backend. Callers that want to experiment
    # with a different OCR engine, pipeline class or backend can build their own
    # PdfFormatOption and pass it to read_document / ocr_convert_pdf instead.
    return PdfFormatOption(
        pipeline_options=_default_pipeline_options(),
        pipeline_cls=ThreadedStandardPdfPipeline,
        backend=PyPdfiumDocumentBackend,
    )
