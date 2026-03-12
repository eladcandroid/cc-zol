"""Generic provider settings (plain dataclass, no pydantic/env magic)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GenericProviderSettings:
    """Provider-specific parameters for any OpenAI-compatible API.

    Defaults match config/settings.py so that omitted values produce
    no extra payload keys.
    """

    # Core sampling parameters
    temperature: float = 1.0
    top_p: float = 1.0
    top_k: int = -1
    max_tokens: int = 81920
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0

    # Advanced sampling parameters
    min_p: float = 0.0
    repetition_penalty: float = 1.0
    seed: int | None = None
    stop: str | None = None

    # Flag parameters
    parallel_tool_calls: bool = True
    return_tokens_as_token_ids: bool = False
    include_stop_str_in_output: bool = False
    ignore_eos: bool = False

    # Misc parameters
    min_tokens: int = 0
    chat_template: str | None = None
    request_id: str | None = None

    # Thinking / reasoning parameters
    reasoning_effort: str = "high"
    include_reasoning: bool = True
