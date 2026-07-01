"""FastAPI dependencies: session, settings, job queue and the services.

The job queue lives on ``app.state`` (started/stopped by the lifespan), so it
is shared process-wide; everything else is request-scoped.
"""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from api.db.base import get_session
from api.services import (
    BlockService,
    CaseService,
    DocumentService,
    JobQueue,
    SegmentService,
)
from api.settings import Settings

SessionDep = Annotated[Session, Depends(get_session)]


def get_app_settings(request: Request) -> Settings:
    """The settings the app was built with (set on app state in create_app)."""
    return request.app.state.settings


SettingsDep = Annotated[Settings, Depends(get_app_settings)]


def get_job_queue(request: Request) -> JobQueue:
    """The process-wide job queue stored on app state."""
    return request.app.state.job_queue


JobQueueDep = Annotated[JobQueue, Depends(get_job_queue)]


def get_case_service(session: SessionDep, settings: SettingsDep) -> CaseService:
    return CaseService(session, settings)


def get_document_service(
    session: SessionDep, settings: SettingsDep, job_queue: JobQueueDep
) -> DocumentService:
    return DocumentService(session, job_queue, settings)


def get_segment_service(session: SessionDep) -> SegmentService:
    return SegmentService(session)


def get_block_service(session: SessionDep) -> BlockService:
    return BlockService(session)


CaseServiceDep = Annotated[CaseService, Depends(get_case_service)]
DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
SegmentServiceDep = Annotated[SegmentService, Depends(get_segment_service)]
BlockServiceDep = Annotated[BlockService, Depends(get_block_service)]
