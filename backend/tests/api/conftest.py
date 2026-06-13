"""API test fixtures: a real Postgres, the FastAPI app with a stubbed pipeline.

The database is a throwaway Postgres -- a running ``TEST_DATABASE_URL`` if set,
otherwise a ``testcontainers`` Postgres (needs Docker). The pipeline is always
faked and the job queue runs inline (synchronously on submit), so uploads reach
``done`` deterministically with no LLM/OCR and no background threads.
"""

import os

import pytest
from fakes import FakeEnricher, FakeReader, FakeSegmenter
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from api.db import models  # noqa: F401 -- registers tables on Base.metadata
from api.db.base import Base, get_session
from api.main import create_app
from api.services import PipelineJob, process_job
from api.settings import Settings
from pipeline import PipelineRunner

# A small upload payload: only the %PDF- magic matters (the reader is faked).
PDF_BYTES = b"%PDF-1.4\n%mindocu test pdf\n"


class InlineJobQueue:
    """Synchronous JobQueue used in tests: processes each job on submit()."""

    def __init__(self, runner: PipelineRunner, session_factory) -> None:
        self._runner = runner
        self._session_factory = session_factory

    def submit(self, job: PipelineJob) -> None:
        process_job(self._runner, self._session_factory, job)

    def start(self) -> None: ...

    def stop(self) -> None: ...


@pytest.fixture(scope="session")
def database_url():
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        yield url
        return
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:17", driver="psycopg") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
def engine(database_url):
    eng = create_engine(database_url)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _clean_db(engine):
    """Each test starts from empty tables."""
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE cases, documents RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def settings(database_url, tmp_path) -> Settings:
    return Settings(database_url=database_url, storage_dir=tmp_path / "pdfs")


@pytest.fixture
def client(settings, session_factory):
    runner = PipelineRunner(FakeReader(), FakeSegmenter(), FakeEnricher())
    app = create_app(settings=settings, job_queue=InlineJobQueue(runner, session_factory))

    def _override_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = _override_session
    with TestClient(app) as test_client:
        yield test_client
