from abc import ABC, abstractmethod
from dataclasses import dataclass

from pydantic import BaseModel


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Backend-agnostic result of one generation call (durations in seconds).

    Token counts and durations are best-effort: backends that cannot measure a
    field report the 0 default ("unknown") rather than guessing.
    """

    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    prompt_duration: float = 0.0  # prefill; 0.0 if the backend cannot split
    generation_duration: float = 0.0  # decode
    load_duration: float = 0.0  # model (re)load; 0.0 for in-process backends

    def timing_summary(self) -> str:
        """Breaks the call's wall-clock into load / prefill / decode.

        Splitting these tells whether a slow call is prefill-bound (large
        prompt), decode-bound (long output) or just a model reload.
        """
        return (
            f"prompt={self.prompt_tokens} tok "
            f"prefill={self.prompt_duration:.2f}s "
            f"({_rate(self.prompt_tokens, self.prompt_duration):.0f} tok/s) | "
            f"gen={self.completion_tokens} tok "
            f"decode={self.generation_duration:.2f}s "
            f"({_rate(self.completion_tokens, self.generation_duration):.0f} tok/s) | "
            f"load={self.load_duration:.2f}s"
        )


class LLMProvider(ABC):
    """A configured LLM endpoint (model + backend) with a uniform generate().

    A provider instance bundles everything endpoint-specific (model name,
    backend tuning knobs) as constructor state; generate() only takes what
    varies per call and exists in every backend. Strategies receive a provider
    via injection and stay agnostic of the underlying LLM library.
    """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        schema: type[BaseModel] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Runs one generation and returns the normalized response.

        With `schema` set, the backend constrains decoding to that Pydantic
        model's JSON schema; `text` is then a JSON string the caller parses
        via `schema.model_validate_json`. `max_tokens=None` means the
        provider's own default output budget.
        """


def _rate(count: int, duration: float) -> float:
    """Tokens per second; 0.0 when either side is unknown."""
    return count / duration if count and duration else 0.0
