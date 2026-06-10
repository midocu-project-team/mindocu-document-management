import time
from functools import lru_cache

from pydantic import BaseModel

from llm.provider import LLMProvider, LLMResponse

DEFAULT_MAX_TOKENS = 4096


class MLXProvider(LLMProvider):
    """mlx-lm backend: in-process generation on Apple Silicon via MLX.

    The model is downloaded from the Hugging Face hub on first use (e.g.
    "mlx-community/Qwen2.5-14B-Instruct-4bit") and stays resident in unified
    memory for the provider's lifetime — there is no keep_alive concept.
    Structured output uses outlines' constrained decoding on top of mlx-lm,
    so a schema call always yields parseable JSON (mlx-lm alone has none).

    outlines drops mlx-lm's per-call metrics, so token counts are re-derived
    via the tokenizer (without chat-template overhead) and the whole call's
    wall-clock is reported as generation_duration (prefill stays 0.0).
    """

    def __init__(
        self,
        model: str,
        *,
        # mlx-lm's own default is 256 — far too small for a structured plan,
        # so the provider always passes an explicit output budget.
        default_max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self.model = model
        self.default_max_tokens = default_max_tokens

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        schema: type[BaseModel] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        from mlx_lm.sample_utils import make_sampler

        model, tokenizer = _load_model(self.model)
        start_time = time.perf_counter()
        # outlines builds its own logits processor for the schema constraint;
        # passing logits_processors here would collide with it.
        text = model(
            _chat_input(prompt, system),
            output_type=schema,
            sampler=make_sampler(temp=temperature),
            max_tokens=max_tokens or self.default_max_tokens,
        )
        return LLMResponse(
            text=text,
            prompt_tokens=len(tokenizer.encode((system or "") + prompt)),
            completion_tokens=len(tokenizer.encode(text)),
            generation_duration=time.perf_counter() - start_time,
        )


# ============================================================================
#  Pure helpers (no provider state)
# ============================================================================


@lru_cache(maxsize=1)
def _load_model(model_id: str) -> tuple:
    """Loads (outlines model, tokenizer) once per model id.

    Module-level cache: provider instances sharing a model don't double-load
    multi-GB weights; maxsize=1 evicts the old model when switching. mlx/
    outlines are imported here (not module-level) so the provider class stays
    importable on machines without Apple Silicon.
    """
    import mlx_lm
    import outlines

    model, tokenizer = mlx_lm.load(model_id)
    return outlines.from_mlxlm(model, tokenizer), tokenizer


def _chat_input(prompt: str, system: str | None):
    """Wraps system+user into an outlines Chat so the model's own chat
    template is applied internally; a bare prompt stays a plain string."""
    if system is None:
        return prompt
    from outlines.inputs import Chat

    return Chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
    )
