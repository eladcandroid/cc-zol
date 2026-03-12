"""Request builder for generic OpenAI-compatible provider."""

import logging
from typing import Any

from providers.common.message_converter import build_base_request_body
from providers.common.utils import set_if_not_none

from .settings import GenericProviderSettings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default values -- used to decide whether a setting should be sent.
# We compare against the dataclass defaults so we never send parameters
# that the user hasn't explicitly changed.
# ---------------------------------------------------------------------------
_DEFAULTS = GenericProviderSettings()


def _set_extra(
    extra_body: dict[str, Any], key: str, value: Any, ignore_value: Any = None
) -> None:
    """Set *key* in *extra_body* only when the value is meaningful.

    Skips the key if it is already present, if *value* is ``None``, or if
    *value* equals *ignore_value*.
    """
    if key in extra_body:
        return
    if value is None:
        return
    if ignore_value is not None and value == ignore_value:
        return
    extra_body[key] = value


def build_request_body(request_data: Any, settings: GenericProviderSettings) -> dict:
    """Build OpenAI-format request body from an Anthropic request.

    Only provider parameters that differ from their defaults are included
    in the outgoing payload so that providers that don't recognise a
    parameter are not disturbed by unexpected keys.
    """
    logger.debug(
        "GENERIC_REQUEST: conversion start model=%s msgs=%s",
        getattr(request_data, "model", "?"),
        len(getattr(request_data, "messages", [])),
    )

    body = build_base_request_body(request_data)

    # ------------------------------------------------------------------
    # max_tokens: honour the request value but cap against settings
    # ------------------------------------------------------------------
    max_tokens = body.get("max_tokens") or getattr(request_data, "max_tokens", None)
    if max_tokens is None:
        max_tokens = settings.max_tokens
    elif settings.max_tokens:
        max_tokens = min(max_tokens, settings.max_tokens)
    set_if_not_none(body, "max_tokens", max_tokens)

    # ------------------------------------------------------------------
    # temperature / top_p: fall back to settings when the request didn't
    # set a value, but only if the setting differs from the default.
    # ------------------------------------------------------------------
    if body.get("temperature") is None and settings.temperature != _DEFAULTS.temperature:
        body["temperature"] = settings.temperature
    if body.get("top_p") is None and settings.top_p != _DEFAULTS.top_p:
        body["top_p"] = settings.top_p

    # ------------------------------------------------------------------
    # stop sequences: fall back to settings when the request didn't set
    # ------------------------------------------------------------------
    if "stop" not in body and settings.stop:
        body["stop"] = settings.stop

    # ------------------------------------------------------------------
    # Penalties -- only send when they differ from the default (0.0)
    # ------------------------------------------------------------------
    if settings.presence_penalty != _DEFAULTS.presence_penalty:
        body["presence_penalty"] = settings.presence_penalty
    if settings.frequency_penalty != _DEFAULTS.frequency_penalty:
        body["frequency_penalty"] = settings.frequency_penalty

    # ------------------------------------------------------------------
    # seed
    # ------------------------------------------------------------------
    if settings.seed is not None:
        body["seed"] = settings.seed

    # ------------------------------------------------------------------
    # parallel_tool_calls -- only send when explicitly disabled
    # ------------------------------------------------------------------
    if settings.parallel_tool_calls != _DEFAULTS.parallel_tool_calls:
        body["parallel_tool_calls"] = settings.parallel_tool_calls

    # ------------------------------------------------------------------
    # extra_body: non-standard parameters that the provider may support
    # ------------------------------------------------------------------
    extra_body: dict[str, Any] = {}
    request_extra = getattr(request_data, "extra_body", None)
    if request_extra:
        extra_body.update(request_extra)

    # Thinking / reasoning hints
    extra_body.setdefault("thinking", {"type": "enabled"})
    extra_body.setdefault("reasoning_split", True)
    extra_body.setdefault(
        "chat_template_kwargs",
        {
            "thinking": True,
            "enable_thinking": True,
            "reasoning_split": True,
            "clear_thinking": False,
        },
    )

    # top_k from request takes precedence, then settings
    req_top_k = getattr(request_data, "top_k", None)
    top_k = req_top_k if req_top_k is not None else settings.top_k
    _set_extra(extra_body, "top_k", top_k, ignore_value=-1)

    _set_extra(extra_body, "min_p", settings.min_p, ignore_value=_DEFAULTS.min_p)
    _set_extra(
        extra_body,
        "repetition_penalty",
        settings.repetition_penalty,
        ignore_value=_DEFAULTS.repetition_penalty,
    )
    _set_extra(extra_body, "min_tokens", settings.min_tokens, ignore_value=_DEFAULTS.min_tokens)
    _set_extra(extra_body, "chat_template", settings.chat_template)
    _set_extra(extra_body, "request_id", settings.request_id)
    _set_extra(
        extra_body,
        "return_tokens_as_token_ids",
        settings.return_tokens_as_token_ids,
        ignore_value=_DEFAULTS.return_tokens_as_token_ids,
    )
    _set_extra(
        extra_body,
        "include_stop_str_in_output",
        settings.include_stop_str_in_output,
        ignore_value=_DEFAULTS.include_stop_str_in_output,
    )
    _set_extra(
        extra_body, "ignore_eos", settings.ignore_eos, ignore_value=_DEFAULTS.ignore_eos
    )
    _set_extra(
        extra_body,
        "reasoning_effort",
        settings.reasoning_effort,
        ignore_value=_DEFAULTS.reasoning_effort,
    )
    _set_extra(
        extra_body,
        "include_reasoning",
        settings.include_reasoning,
        ignore_value=_DEFAULTS.include_reasoning,
    )

    if extra_body:
        body["extra_body"] = extra_body

    logger.debug(
        "GENERIC_REQUEST: conversion done model=%s msgs=%s tools=%s",
        body.get("model"),
        len(body.get("messages", [])),
        len(body.get("tools", [])),
    )
    return body
