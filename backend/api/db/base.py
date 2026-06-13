"""SQLAlchemy engine, session factory and the declarative base.

Synchronous SQLAlchemy 2.0: the pipeline and the background worker are
blocking, so a sync stack keeps sessions usable from both request handlers
(via the ``get_session`` dependency) and the worker thread (via
``SessionLocal`` directly).
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from api.settings import get_settings


class Base(DeclarativeBase):
    """Declarative base; ``Base.metadata`` is what Alembic autogenerates from."""


# Engine is created eagerly but connects lazily, so importing this module
# (e.g. in Alembic or tests) does not require a reachable database.
engine = create_engine(get_settings().database_url, pool_pre_ping=True)

# expire_on_commit=False: services return ORM rows after commit, so their
# attributes must stay accessible without an extra query.
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
