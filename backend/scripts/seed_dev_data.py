"""Seed one finished demo case so the frontend can be built without LLM/OCR.

Builds a small but well-formed ``Document`` in code, writes a case + a `done`
document row through the repositories and drops a tiny real PDF on disk. Run
after the migrations:

    uv run python -m scripts.seed_dev_data

Imports only from ``api``/``pipeline`` (never from tests). Idempotency is not a
goal -- each run creates a fresh demo case.
"""

import itertools
import uuid
from datetime import datetime

from api import storage
from api.db.base import SessionLocal
from api.repositories import CaseRepository, DocumentRepository
from api.settings import get_settings
from pipeline import Document, make_segment
from pipeline.datatypes import (
    BlockType,
    ContentBlock,
    EnrichedSegment,
    PageContent,
    SummaryReference,
)

_block_ids = itertools.count()


def main() -> None:
    settings = get_settings()
    pdf_bytes = _minimal_pdf("mindocu demo")
    document = _build_demo_document(file_size_bytes=len(pdf_bytes))

    with SessionLocal() as session:
        case = CaseRepository(session).create("Demo-Akte (Seed)")
        session.flush()  # need case.id for the storage path

        documents = DocumentRepository(session)
        pdf_path = storage.save_pdf(
            case.id, document.document_id, pdf_bytes, settings.storage_dir
        )
        documents.create_pending(
            document_id=document.document_id,
            case_id=case.id,
            file_name=document.file_name,
            file_size_bytes=document.file_size_bytes,
            pdf_path=str(pdf_path),
        )
        documents.save_document(document.document_id, document)
        session.commit()

        print(f"seeded case {case.id} with document {document.document_id}")


# Demo Document builder


def _build_demo_document(*, file_size_bytes: int) -> Document:
    """A 4-page demo: one relevant 'Verfügung', one irrelevant 'Prüfvermerk'."""
    pages = [
        _page(1, "Verfügung", "Die Unterbringung wird angeordnet."),
        _page(2, "Verfügung", "Begründung und weitere Hinweise."),
        _page(3, "Prüfvermerk", "Eingangsstempel und Aktenzeichen."),
        _page(4, "Prüfvermerk", "Formale Prüfung abgeschlossen."),
    ]
    relevant = EnrichedSegment.from_segment(
        make_segment(pages[0:2], [0.95]),
        title="Verfügung des Gerichts",
        references=[
            SummaryReference(
                text="Anordnung der Unterbringung mit Begründung.",
                block_ids=[pages[0].blocks[0].block_id],
            )
        ],
        relevance=True,
        matched_keywords=["Verfügung"],
    )
    irrelevant = EnrichedSegment.from_segment(
        make_segment(pages[2:4], [0.9]),
        title=None,
        references=None,
        relevance=False,
        matched_keywords=["Prüfvermerk"],
    )
    now = datetime.now()
    return Document(
        document_id=uuid.uuid4(),
        file_name="Demo-Akte.pdf",
        file_size_bytes=file_size_bytes,
        total_pages=len(pages),
        ocr_engine="tesseract:deu+eng",
        pages=pages,
        segments=[relevant, irrelevant],
        enrichment_method="llm+keyword",
        extracted_at=now,
        enriched_at=now,
    )


def _page(number: int, heading: str, body: str) -> PageContent:
    return PageContent(
        page_number=number,
        raw_text=f"{heading}\n{body}",
        blocks=[
            ContentBlock(block_id=next(_block_ids), text=heading, block_type=BlockType.HEADING, bbox=(72, 700, 540, 740)),
            ContentBlock(block_id=next(_block_ids), text=body, block_type=BlockType.PARAGRAPH, bbox=(72, 600, 540, 690)),
        ],
        was_ocr_applied=False,
        confidence=0.95,
        width_pt=612,
        height_pt=792,
    )


# Minimal valid PDF (xref offsets computed, so the preview can render it)


def _minimal_pdf(text: str) -> bytes:
    content = f"BT /F1 24 Tf 72 700 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{index} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_offset = len(pdf)
    size = len(objects) + 1
    pdf += f"xref\n0 {size}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode()
    pdf += b"trailer\n" + f"<< /Size {size} /Root 1 0 R >>\n".encode()
    pdf += b"startxref\n" + f"{xref_offset}\n".encode() + b"%%EOF"
    return bytes(pdf)


if __name__ == "__main__":
    main()
