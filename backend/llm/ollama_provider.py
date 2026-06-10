import ollama
from pydantic import BaseModel

from llm.provider import LLMProvider, LLMResponse


class OllamaProvider(LLMProvider):
    """Ollama backend: generation via the local Ollama server's HTTP API.

    Structured output uses Ollama's native grammar-constrained decoding
    (`format=<json schema>`), so a schema call always yields parseable JSON.
    """

    def __init__(
        self,
        model: str,
        *,
        # num_ctx is REQUIRED for long prompts: Ollama's default (~2-4K)
        # silently truncates, so the model would only ever see the first pages.
        # 128K is the trained context ceiling of current local models; Ollama
        # clamps it down to the model's trained max.
        num_ctx: int | None = None,
        keep_alive: int = 45 * 60,  # keep the model loaded for 45 min
        think: bool = False,
    ) -> None:
        self.model = model
        self.num_ctx = num_ctx
        self.keep_alive = keep_alive
        self.think = think

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        schema: type[BaseModel] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        options: dict = {"temperature": temperature}
        if self.num_ctx is not None:
            options["num_ctx"] = self.num_ctx
        if max_tokens is not None:
            options["num_predict"] = max_tokens

        response = ollama.generate(
            model=self.model,
            prompt=prompt,
            system=system,
            format=schema.model_json_schema() if schema else None,
            think=self.think,
            options=options,
            keep_alive=self.keep_alive,
        )
        return _to_response(response)


# ============================================================================
#  Pure helpers (no provider state)
# ============================================================================


def _to_response(response: ollama.GenerateResponse) -> LLMResponse:
    """Normalizes Ollama's per-call counters (nanoseconds, any field may be
    None) into the backend-agnostic LLMResponse."""

    def secs(ns: int | None) -> float:
        return (ns or 0) / 1e9

    return LLMResponse(
        text=response.response,
        prompt_tokens=response.prompt_eval_count or 0,
        completion_tokens=response.eval_count or 0,
        prompt_duration=secs(response.prompt_eval_duration),
        generation_duration=secs(response.eval_duration),
        load_duration=secs(response.load_duration),
    )
