"""Filesystem storage for the original PDFs.

Layout: ``{storage_dir}/{case_id}/{document_id}.pdf``. The DB only keeps the
path; the bytes never go into Postgres. ``storage_dir`` is passed in from
``Settings`` rather than read globally, so the functions stay pure/testable.
"""

import shutil
import uuid
from pathlib import Path


def save_pdf(
    case_id: uuid.UUID, document_id: str, data: bytes, storage_dir: Path
) -> Path:
    """Writes ``data`` to the document's PDF path, creating the case dir."""
    destination = pdf_path(case_id, document_id, storage_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return destination


def pdf_path(case_id: uuid.UUID, document_id: str, storage_dir: Path) -> Path:
    """The on-disk path for a document's PDF (no I/O)."""
    return storage_dir / str(case_id) / f"{document_id}.pdf"


def delete_case_dir(case_id: uuid.UUID, storage_dir: Path) -> None:
    """Removes a case's PDF directory and everything in it (idempotent)."""
    shutil.rmtree(storage_dir / str(case_id), ignore_errors=True)
