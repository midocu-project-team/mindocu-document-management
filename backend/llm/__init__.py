"""Interchangeable LLM backends behind one LLMProvider interface.

Strategies depend only on LLMProvider/LLMResponse; concrete providers
(Ollama, MLX, future backends) are injected at construction time.
"""

from llm.mlx_provider import MLXProvider
from llm.ollama_provider import OllamaProvider
from llm.provider import LLMProvider, LLMResponse

__all__ = ["LLMProvider", "LLMResponse", "MLXProvider", "OllamaProvider"]
