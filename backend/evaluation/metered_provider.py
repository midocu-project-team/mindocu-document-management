"""A metering wrapper around any LLMProvider.

Strategies call ``provider.generate(...)`` internally and never surface their
per-call cost. Wrapping the injected provider in a ``MeteredProvider`` lets the
evaluation harness accumulate call count, token totals and prefill/decode time
across a whole run without touching the strategies — it forwards every call
unchanged and only records the returned ``LLMResponse`` stats.
"""

from dataclasses import dataclass

from pydantic import BaseModel

from llm import LLMProvider, LLMResponse


@dataclass
class LLMUsage:
    """Aggregated LLM cost over one evaluation run (durations in seconds)."""

    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    prompt_duration: float = 0.0  # summed prefill
    generation_duration: float = 0.0  # summed decode
    load_duration: float = 0.0

    def record(self, response: LLMResponse) -> None:
        """Folds one response's stats into the running totals."""
        self.calls += 1
        self.prompt_tokens += response.prompt_tokens
        self.completion_tokens += response.completion_tokens
        self.prompt_duration += response.prompt_duration
        self.generation_duration += response.generation_duration
        self.load_duration += response.load_duration


class MeteredProvider(LLMProvider):
    """Forwards generate() to a wrapped provider and tallies usage."""

    def __init__(self, inner: LLMProvider) -> None:
        self.inner = inner
        self.usage = LLMUsage()

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        schema: type[BaseModel] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        response = self.inner.generate(
            prompt,
            system=system,
            schema=schema,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self.usage.record(response)
        return response
