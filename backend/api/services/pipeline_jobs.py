"""Background processing of uploaded PDFs.

A single daemon worker drains a FIFO queue, so jobs run strictly sequentially
-- stages 2/3 share one local LLM and must never run concurrently. The
``JobQueue`` protocol keeps the call site agnostic so a broker-backed backend
(RabbitMQ, Redis, ...) can replace the in-process queue later: the producer
side only ever calls ``submit``. The actual per-job work lives in the
module-level ``process_job`` so a synchronous test queue -- and a future
out-of-process consumer/worker -- can reuse it verbatim.
"""

import io
import queue
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sqlalchemy.orm import Session

from api.db.models import ProcessingStatus
from api.repositories import DocumentRepository
from logging_config import get_logger
from pipeline import PipelineRunner

logger = get_logger(__name__)

SessionFactory = Callable[[], Session]

# Runner stage label -> persisted status (the row's status doubles as "stage").
_STAGE_STATUS = {
    "extracting": ProcessingStatus.EXTRACTING,
    "segmenting": ProcessingStatus.SEGMENTING,
    "enriching": ProcessingStatus.ENRICHING,
}


@dataclass(frozen=True)
class PipelineJob:
    """A unit of work: process one uploaded PDF into a stored ``Document``."""

    document_id: uuid.UUID
    pdf_path: str
    file_name: str


class Lifecycle(Protocol):
    """Start/stop hooks for a backend that owns a resource (worker thread,
    broker connection, ...). Kept separate from ``JobQueue`` because the
    submit side is broker-agnostic while the lifecycle is implementation
    detail -- a future RabbitMQ producer opens/closes its connection here."""

    def start(self) -> None: ...
    def stop(self) -> None: ...


class JobQueue(Lifecycle, Protocol):
    """Submit + lifecycle interface; implementations decide how/when the job
    runs. ``submit`` is the stable, broker-agnostic core (in-process queue
    today, ``basic_publish`` to a RabbitMQ exchange later)."""

    def submit(self, job: PipelineJob) -> None: ...


def process_job(
    runner: PipelineRunner, session_factory: SessionFactory, job: PipelineJob
) -> None:
    """Runs one job in its own session: status updates, persist, or fail."""
    with session_factory() as session:
        repo = DocumentRepository(session)
        try:
            document = runner.run(
                io.BytesIO(Path(job.pdf_path).read_bytes()),
                job.file_name,
                on_stage=lambda stage: _record_stage(
                    session, repo, job.document_id, stage
                ),
            )
            # The app owns document_id (assigned at upload); override the
            # pipeline's internally generated one so it matches the row PK.
            document = document.model_copy(update={"document_id": job.document_id})
            repo.save_document(job.document_id, document)
            session.commit()
        except Exception as exc:  # degrade this job; keep the worker alive
            logger.exception("pipeline job failed for document %s", job.document_id)
            session.rollback()
            repo.set_status(
                job.document_id, ProcessingStatus.FAILED, error_message=str(exc)
            )
            session.commit()


class PipelineJobQueue:
    """In-process sequential job queue backed by one daemon worker thread."""

    def __init__(self, runner: PipelineRunner, session_factory: SessionFactory) -> None:
        self._runner = runner
        self._session_factory = session_factory
        self._queue: queue.Queue[PipelineJob | None] = queue.Queue()
        self._worker: threading.Thread | None = None

    def start(self) -> None:
        if self._worker is not None:
            return
        self._worker = threading.Thread(
            target=self._run_loop, name="pipeline-worker", daemon=True
        )
        self._worker.start()

    def stop(self) -> None:
        if self._worker is None:
            return
        self._queue.put(None)  # sentinel ends the loop
        self._worker.join()
        self._worker = None

    def submit(self, job: PipelineJob) -> None:
        self._queue.put(job)

    def _run_loop(self) -> None:
        while (job := self._queue.get()) is not None:
            try:
                process_job(self._runner, self._session_factory, job)
            finally:
                self._queue.task_done()


# Pure helpers (no queue state)


def _record_stage(
    session: Session, repo: DocumentRepository, document_id: uuid.UUID, stage: str
) -> None:
    """Commits a stage status update so pollers see progress immediately."""
    repo.set_status(document_id, _STAGE_STATUS[stage])
    session.commit()
