"""Builds the pipeline from ``Settings`` -- the composition root.

Mirrors the build pattern of ``evaluation/config.py`` (provider then strategies
bound to it) but deliberately does not import from ``evaluation`` (that package
is eval-specific). The pipeline is only composed here, never modified.

Each ``build_*`` takes only the settings slice it needs; stages 2/3 carry their
own provider. The provider is built inside the strategy branch that needs one,
so a provider-less strategy never triggers a build.
"""

from typing import Any, assert_never

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
    RelevanceKeywords,
    SegmentationStrategy,
)

from api.settings import (
    EnrichmentSettings,
    ProviderSettings,
    SegmentationSettings,
    Settings,
)


def build_provider(provider: ProviderSettings) -> LLMProvider:
    """Instantiates the configured LLM backend."""
    match provider.backend:
        case "mlx":
            return MLXProvider(
                provider.model,
                **_drop_none(default_max_tokens=provider.default_max_tokens),
            )
        case "ollama":
            return OllamaProvider(
                provider.model,
                think=provider.think,
                **_drop_none(num_ctx=provider.num_ctx, keep_alive=provider.keep_alive),
            )
        case _:
            assert_never(provider.backend)


def build_reader() -> ReaderStrategy:
    """Builds the stage-1 reader (docling defaults: threaded, CPU, Tesseract)."""
    return DoclingReaderStrategy()


def build_segmenter(seg: SegmentationSettings) -> SegmentationStrategy:
    """Builds the stage-2 strategy bound to its own provider.

    Only the chosen strategy's branch builds a provider, so a future
    provider-less strategy simply does not, and no provider is built.
    """
    match seg.strategy:
        case "pairwise_boundary":
            return PairwiseBoundarySegmentationStrategy(
                build_provider(seg.provider), temperature=seg.temperature
            )
        case "full_context":
            options = FullContextOptions(temperature=seg.temperature, **seg.options)
            return FullContextSegmentationStrategy(build_provider(seg.provider), options)
        case _:
            assert_never(seg.strategy)


def build_enricher(
    enr: EnrichmentSettings, keywords: RelevanceKeywords
) -> EnrichmentStrategy:
    """Builds the stage-3 strategy bound to its own provider."""
    options = KeywordRelevanceOptions(
        temperature=enr.temperature,
        max_input_chars=enr.max_input_chars,
        enrich_irrelevant=enr.enrich_irrelevant,
    )
    return KeywordRelevanceEnrichmentStrategy(
        build_provider(enr.provider), keywords, options
    )


def build_runner(settings: Settings) -> PipelineRunner:
    """Assembles the full ``PipelineRunner`` -- each stage uses its own provider."""
    return PipelineRunner(
        reader=build_reader(),
        segmenter=build_segmenter(settings.segmentation),
        enricher=build_enricher(settings.enrichment, settings.keywords),
    )


# Pure helpers (no settings state)


def _drop_none(**kwargs: Any) -> dict[str, Any]:
    """Filters out None values so the provider constructor defaults apply."""
    return {key: value for key, value in kwargs.items() if value is not None}
