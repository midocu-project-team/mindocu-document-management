"""FastAPI application package: HTTP API, persistence and pipeline composition.

Layered as routers -> services -> repositories over the SQLAlchemy models in
``api.db``. The pipeline itself is composed (never modified) via ``api.factory``,
which builds a ``pipeline.PipelineRunner`` from ``api.settings.Settings``.
"""
