"""Builds the pipeline from ``Settings`` -- the composition root.

Mirrors the build pattern of ``evaluation/config.py`` (provider then strategies
bound to it) but deliberately does not import from ``evaluation`` (that package
is eval-specific). The pipeline is only composed here, never modified.
"""

from typing import Any

from llm import LLMProvider, MLXProvider, OllamaProvider
from pipeline import (
    DoclingReaderStrategy,
    EnrichmentStrategy,
    FullContextOptions,
    FullContextSegmentationStrategy,
    KeywordRelevanceEnrichmentStrategy,
    KeywordRelevanceOptions,
    PairwiseBoundarySegmentationStrategy,
    PipelineRunner,
    ReaderStrategy,
    SegmentationStrategy,
)

from api.settings import Settings


def build_provider(settings: Settings) -> LLMProvider:
    """Instantiates the configured LLM backend."""
    provider = settings.provider
    if provider.backend == "mlx":
        return MLXProvider(
            provider.model,
            **_drop_none(default_max_tokens=provider.default_max_tokens),
        )
    return OllamaProvider(
        provider.model,
        think=provider.think,
        **_drop_none(num_ctx=provider.num_ctx, keep_alive=provider.keep_alive),
    )


def build_reader(settings: Settings) -> ReaderStrategy:
    """Builds the stage-1 reader (docling defaults: threaded, CPU, Tesseract)."""
    return DoclingReaderStrategy()


def build_segmenter(provider: LLMProvider, settings: Settings) -> SegmentationStrategy:
    """Builds the stage-2 strategy bound to ``provider``."""
    seg = settings.segmentation
    if seg.strategy == "pairwise_boundary":
        return PairwiseBoundarySegmentationStrategy(provider, temperature=seg.temperature)
    options = FullContextOptions(temperature=seg.temperature, **seg.options)
    return FullContextSegmentationStrategy(provider, options)


def build_enricher(provider: LLMProvider, settings: Settings) -> EnrichmentStrategy:
    """Builds the stage-3 strategy bound to ``provider``."""
    enr = settings.enrichment
    options = KeywordRelevanceOptions(
        temperature=enr.temperature,
        max_input_chars=enr.max_input_chars,
        enrich_irrelevant=enr.enrich_irrelevant,
    )
    return KeywordRelevanceEnrichmentStrategy(provider, settings.keywords, options)


def build_runner(settings: Settings) -> PipelineRunner:
    """Assembles the full ``PipelineRunner`` (one provider shared by stages 2/3)."""
    provider = build_provider(settings)
    return PipelineRunner(
        reader=build_reader(settings),
        segmenter=build_segmenter(provider, settings),
        enricher=build_enricher(provider, settings),
    )


# Pure helpers (no settings state)


def _drop_none(**kwargs: Any) -> dict[str, Any]:
    """Filters out None values so the provider constructor defaults apply."""
    return {key: value for key, value in kwargs.items() if value is not None}
