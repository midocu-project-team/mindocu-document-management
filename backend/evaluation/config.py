"""YAML-driven configuration for evaluation runs.

One YAML file describes one full evaluation run: which test PDFs to score, a
``reader:`` section for the intrinsic reader metrics and a ``segmentation:``
section listing the (strategy, provider) combinations to benchmark. Pydantic
validates the schema with ``extra="forbid"`` so a typo in the YAML fails fast
with a clear message instead of silently configuring nothing.

Run configs are data, not code: they live in ``tests/evaluation/*.yaml`` next
to the test assets, and relative paths inside a config resolve against the
config file's directory (not the current working directory).
"""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from llm import LLMProvider, MLXProvider, OllamaProvider
from segmentation import (
    FullContextOptions,
    FullContextSegmentationStrategy,
    PairwiseBoundarySegmentationStrategy,
)
from segmentation.strategy import SegmentationStrategy

from evaluation.harness import ASSETS_DIR


class ProviderConfig(BaseModel):
    """One LLM backend; endpoint properties are constructor state (see llm/)."""

    model_config = ConfigDict(extra="forbid")

    backend: Literal["ollama", "mlx"]
    model: str
    # Ollama-only knobs (None keeps the provider's default):
    num_ctx: int | None = None
    keep_alive: int | None = None
    think: bool = False
    # MLX-only knob:
    default_max_tokens: int | None = None

    @model_validator(mode="after")
    def _check_backend_knobs(self) -> "ProviderConfig":
        """Rejects knobs that the chosen backend would silently ignore."""
        ollama_knobs = self.num_ctx is not None or self.keep_alive is not None
        if self.backend == "mlx" and (ollama_knobs or self.think):
            raise ValueError("num_ctx/keep_alive/think are Ollama-only options")
        if self.backend == "ollama" and self.default_max_tokens is not None:
            raise ValueError("default_max_tokens is an MLX-only option")
        return self

    def build(self) -> LLMProvider:
        """Instantiates the configured backend."""
        if self.backend == "mlx":
            return MLXProvider(
                self.model, **_drop_none(default_max_tokens=self.default_max_tokens)
            )
        return OllamaProvider(
            self.model,
            think=self.think,
            **_drop_none(num_ctx=self.num_ctx, keep_alive=self.keep_alive),
        )


class SegmentationRunConfig(BaseModel):
    """One benchmark row: a segmentation strategy bound to an LLM provider."""

    model_config = ConfigDict(extra="forbid")

    strategy: Literal["pairwise_boundary", "full_context"]
    provider: ProviderConfig
    name: str | None = None  # display name; defaults to "<strategy>@<model>"
    temperature: float = 0.0
    # Extra FullContextOptions fields (window_pages, max_input_tokens, ...).
    options: dict[str, Any] = {}

    @model_validator(mode="after")
    def _check_strategy_options(self) -> "SegmentationRunConfig":
        """Fails fast on combinations that would silently misbehave."""
        if self.strategy == "pairwise_boundary" and self.options:
            raise ValueError("options are only supported by full_context")
        if self.strategy == "full_context":
            _check_full_context_options(self.options)
            _check_full_context_num_ctx(self.provider)
        return self

    @property
    def display_name(self) -> str:
        """The strategy name shown in the report tables."""
        return self.name or f"{self.strategy}@{self.provider.model}"

    def build_strategy(self, provider: LLMProvider) -> SegmentationStrategy:
        """Builds the configured strategy bound to ``provider``.

        Matches the harness's ``StrategyFactory`` signature, so a config's
        bound ``build_strategy`` can be passed as the factory directly.
        """
        if self.strategy == "pairwise_boundary":
            return PairwiseBoundarySegmentationStrategy(
                provider, temperature=self.temperature
            )
        options = FullContextOptions(temperature=self.temperature, **self.options)
        return FullContextSegmentationStrategy(provider, options)


class ReaderConfig(BaseModel):
    """The ``reader:`` section — intrinsic reader-quality metrics."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    refresh_cache: bool = False  # ignore <stem>.cached.json and OCR again


class SegmentationConfig(BaseModel):
    """The ``segmentation:`` section — the (strategy, provider) runs to score."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    predict_only: bool = False  # run without ground truth; just output segments
    show_segments: bool = False  # per-segment detail table (always on in predict_only)
    tolerance: int = 1  # off-by-N page slack for the tolerant boundary score
    runs: list[SegmentationRunConfig] = []


class EvaluationConfig(BaseModel):
    """One full evaluation run as described by a YAML file."""

    model_config = ConfigDict(extra="forbid")

    pdfs: list[str]
    assets_dir: Path = ASSETS_DIR
    output_json: Path | None = None
    reader: ReaderConfig = ReaderConfig()
    segmentation: SegmentationConfig = SegmentationConfig()


def load_config(path: Path) -> EvaluationConfig:
    """Loads and validates a YAML run config.

    Relative ``assets_dir``/``output_json`` paths resolve against the config
    file's directory, so a config works regardless of the caller's CWD.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    config = EvaluationConfig.model_validate(raw)
    return _resolve_paths(config, base=path.resolve().parent)


# ============================================================================
#  Pure helpers (no config state)
# ============================================================================


def _check_full_context_options(options: dict[str, Any]) -> None:
    """Rejects option keys that FullContextOptions would silently drop."""
    if "temperature" in options:
        raise ValueError("set temperature at the run level, not in options")
    unknown = set(options) - set(FullContextOptions.model_fields)
    if unknown:
        raise ValueError(f"unknown full_context options: {sorted(unknown)}")


def _check_full_context_num_ctx(provider: ProviderConfig) -> None:
    """full_context on Ollama must set num_ctx (the default silently truncates)."""
    if provider.backend == "ollama" and provider.num_ctx is None:
        raise ValueError(
            "full_context on Ollama requires num_ctx: the default context "
            "(~2-4K tokens) silently truncates the whole-document prompt"
        )


def _resolve_paths(config: EvaluationConfig, *, base: Path) -> EvaluationConfig:
    """Returns a copy with relative paths anchored at ``base``."""
    output = config.output_json
    return config.model_copy(
        update={
            "assets_dir": _anchor(config.assets_dir, base),
            "output_json": _anchor(output, base) if output is not None else None,
        }
    )


def _anchor(path: Path, base: Path) -> Path:
    """Anchors a relative path at ``base``; absolute paths pass through."""
    return path if path.is_absolute() else (base / path).resolve()


def _drop_none(**kwargs: Any) -> dict[str, Any]:
    """Filters out None values so the provider constructor defaults apply."""
    return {key: value for key, value in kwargs.items() if value is not None}
