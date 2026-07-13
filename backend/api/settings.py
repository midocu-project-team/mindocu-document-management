"""Application settings (Pydantic Settings).

One ``Settings`` object configures the whole API: the database, PDF storage,
upload limits and how the pipeline is wired (each stage's provider backend and
model, segmentation/enrichment options and the relevance keywords). Values come
from the environment (prefix ``MINDOCU_``) or a ``.env`` file; nested fields use
a double-underscore delimiter, e.g. ``MINDOCU_SEGMENTATION__PROVIDER__MODEL=...``.

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
    relevant=["Verfügung", "Gesprächsprotokoll"],
    irrelevant=[
        "Prüfvermerk",
        "Vermerk",
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
        "Fehlblatt",
        "Kontrollbeleg",
        "Zahlungsanzeige",
        "Vermerk",
        "Aktendeckel"
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
    # This stage's own LLM backend (defaults to a standalone ProviderSettings).
    provider: ProviderSettings = Field(default_factory=ProviderSettings)


class EnrichmentSettings(BaseModel):
    """Stage-3 keyword-relevance options (the keyword set lives on Settings)."""

    temperature: float = 0.0
    max_input_chars: int | None = 24_000
    enrich_irrelevant: bool = False
    # This stage's own LLM backend (defaults to a standalone ProviderSettings).
    provider: ProviderSettings = Field(default_factory=ProviderSettings)


class ChatSettings(BaseModel):
    """Document-chat options (query-time, not a pipeline stage)."""

    temperature: float = 0.0
    max_segments: int = 5
    max_input_chars_per_segment: int | None = 12_000
    max_history_turns: int = 6
    # The chat's own LLM backend (defaults to a standalone ProviderSettings).
    provider: ProviderSettings = Field(default_factory=ProviderSettings)


class Settings(BaseSettings):
    """Top-level application configuration."""

    model_config = SettingsConfigDict(
        env_prefix="MINDOCU_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    database_url: str
    storage_dir: Path = Path("data/pdfs")
    max_pdfs_per_case: int = 3
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    segmentation: SegmentationSettings = Field(default_factory=SegmentationSettings)
    enrichment: EnrichmentSettings = Field(default_factory=EnrichmentSettings)
    chat: ChatSettings = Field(default_factory=ChatSettings)
    keywords: RelevanceKeywords = Field(
        default_factory=lambda: DEFAULT_KEYWORDS.model_copy(deep=True)
    )

    @model_validator(mode="after")
    def _check_full_context_num_ctx(self) -> "Settings":
        """full_context on Ollama needs num_ctx (the default silently truncates).

        Checks the segmentation stage's own provider.
        """
        if self.segmentation.strategy != "full_context":
            return self
        provider = self.segmentation.provider
        if provider.backend == "ollama" and provider.num_ctx is None:
            raise ValueError(
                "full_context on Ollama requires provider.num_ctx: the default "
                "context (~2-4K tokens) silently truncates the whole-document prompt"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (one per process)."""
    # Required fields (e.g. database_url) are populated from the environment /
    # .env at runtime, which the type checker cannot see -- hence call-arg.
    return Settings()  # type: ignore[call-arg]
