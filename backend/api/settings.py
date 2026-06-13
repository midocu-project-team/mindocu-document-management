"""Application settings (Pydantic Settings).

One ``Settings`` object configures the whole API: the database, PDF storage,
upload limits and how the pipeline is wired (provider backend, model,
segmentation/enrichment options and the relevance keywords). Values come from
the environment (prefix ``MINDOCU_``) or a ``.env`` file; nested fields use a
double-underscore delimiter, e.g. ``MINDOCU_PROVIDER__MODEL=...``.

The provider/strategy *config* lives here; the actual construction is done in
``api.factory`` (mirrors how ``evaluation/config.py`` separates config from the
``build`` calls).
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from pipeline import RelevanceKeywords

# Default relevance keyword set, mirroring tests/evaluation/default.yaml:
# "Verfügung" marks a segment relevant; the rest mark it irrelevant.
DEFAULT_KEYWORDS = RelevanceKeywords(
    relevant=["Verfügung"],
    irrelevant=[
        "Prüfvermerk",
        "Zählblatt",
        "Herkunftsnachweis",
        "Übermittlung",
        "Protokoll",
        "Empfangsbekenntnis",
        "Transferlog",
        "Zustellungsurkunde",
        "Übertragungsnachweis",
        "Erledigungsvermerk",
        "Transfervermerk",
    ],
)


class ProviderSettings(BaseModel):
    """The injected LLM backend; endpoint knobs are provider-constructor state."""

    backend: Literal["ollama", "mlx"] = "mlx"
    model: str = "mlx-community/Qwen3.6-35B-A3B-4bit"
    # Ollama-only knobs (None keeps the provider default):
    num_ctx: int | None = None
    keep_alive: int | None = None
    think: bool = False
    # MLX-only knob:
    default_max_tokens: int | None = None

    @model_validator(mode="after")
    def _check_backend_knobs(self) -> "ProviderSettings":
        """Rejects knobs the chosen backend would silently ignore."""
        ollama_knobs = self.num_ctx is not None or self.keep_alive is not None
        if self.backend == "mlx" and (ollama_knobs or self.think):
            raise ValueError("num_ctx/keep_alive/think are Ollama-only options")
        if self.backend == "ollama" and self.default_max_tokens is not None:
            raise ValueError("default_max_tokens is an MLX-only option")
        return self


class SegmentationSettings(BaseModel):
    """Stage-2 strategy selection and its extra options."""

    strategy: Literal["full_context", "pairwise_boundary"] = "full_context"
    temperature: float = 0.0
    # Extra FullContextOptions fields (window_pages, max_input_tokens, ...).
    options: dict[str, Any] = Field(default_factory=dict)


class EnrichmentSettings(BaseModel):
    """Stage-3 keyword-relevance options (the keyword set lives on Settings)."""

    temperature: float = 0.0
    max_input_chars: int | None = 24_000
    enrich_irrelevant: bool = False


class Settings(BaseSettings):
    """Top-level application configuration."""

    model_config = SettingsConfigDict(
        env_prefix="MINDOCU_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://mindocu:mindocu@localhost:5432/mindocu"
    storage_dir: Path = Path("data/pdfs")
    max_pdfs_per_case: int = 3
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    provider: ProviderSettings = Field(default_factory=ProviderSettings)
    segmentation: SegmentationSettings = Field(default_factory=SegmentationSettings)
    enrichment: EnrichmentSettings = Field(default_factory=EnrichmentSettings)
    keywords: RelevanceKeywords = Field(
        default_factory=lambda: DEFAULT_KEYWORDS.model_copy(deep=True)
    )

    @model_validator(mode="after")
    def _check_full_context_num_ctx(self) -> "Settings":
        """full_context on Ollama needs num_ctx (the default silently truncates)."""
        on_ollama = self.provider.backend == "ollama"
        full_context = self.segmentation.strategy == "full_context"
        if on_ollama and full_context and self.provider.num_ctx is None:
            raise ValueError(
                "full_context on Ollama requires provider.num_ctx: the default "
                "context (~2-4K tokens) silently truncates the whole-document prompt"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (one per process)."""
    return Settings()
